import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import lance
import numpy as np
import psycopg
import pyarrow as pa
import pyarrow.compute as pc
from psycopg.rows import dict_row
from pyarrow import csv

from author_encoder.config import DIMENSIONS, TEXT_STORE, VECTOR_STORE, VECTOR_WORK
from author_encoder.index import FEATURES, PROTOCOL, Spill, head, read, vectors_at
from author_encoder.lock import index_lock
from author_encoder.model import load_model
from author_encoder.texts import raw, scales
from claims.config import NAMES_FILE, NUMERIC
from claims.schema import BOT, FLAIR_ONLY
from database import DSN

from . import LOG, timed, write_json
from .config import BEARING_MASK, BEARING_STAMP, CLEAN_BUCKETS, CLEAN_TEXTS, ENCODERS, SPLITS, STRICT_SHARE, STRICT_SUPPORT, VALUE_AUTHORS, VECTOR_CHUNK, check_targets, partition, validate

CLAIMS = "COPY (SELECT author, attribute, value, support, share FROM author_claims WHERE attribute = ANY(%s::claim_field[])) TO STDOUT (FORMAT CSV)"
BEARING = "COPY (SELECT substring(text_sha256 for 8) FROM text_claims WHERE field <> %s) TO STDOUT (FORMAT CSV)"
ARRAYS = ("users", "labels", "splits")
SPREAD_ROWS = 1 << 20
FETCHED = pa.schema([pa.field("slot", pa.uint64()), pa.field("vector", pa.list_(pa.int8(), FEATURES))])


def source(conn):
    months = {row["month"]: str(row["loaded_at"]) for row in conn.execute("SELECT month, loaded_at FROM months ORDER BY month")}
    run = conn.execute("SELECT run_id::text FROM consolidation").fetchone()
    if not run:
        raise ValueError("Consolidation must finish before preparing model targets")
    return {"months": months, "consolidation": run["run_id"], "protocol": json.loads(PROTOCOL)}


@timed
def read_claims(conn, targets):
    chunks = bytearray()
    with conn.cursor().copy(CLAIMS, [list(targets)]) as copy:
        for chunk in copy:
            chunks += chunk
    types = {"author": pa.string(), "attribute": pa.string(), "value": pa.string(), "support": pa.float32(), "share": pa.float32()}
    table = csv.read_csv(pa.BufferReader(chunks), read_options=csv.ReadOptions(column_names=list(types)), convert_options=csv.ConvertOptions(column_types=types, strings_can_be_null=False))
    LOG.info("attribute claims rows=%d", table.num_rows)
    return table


def encode(values, name, kind):
    if kind == "numeric":
        numbers = pc.cast(values, pa.float64()).to_numpy()
        low, high = NUMERIC[name]
        return np.where((numbers >= low) & (numbers <= high), numbers, np.nan), None
    counts = pc.value_counts(values).to_pylist()
    catalog = [item["values"] for item in sorted(counts, key=lambda item: (-item["counts"], item["values"])) if kind != "embedding" or item["counts"] >= VALUE_AUTHORS]
    return pc.index_in(values, value_set=pa.array(catalog)).to_numpy().astype(np.float64), catalog


@timed
def bearing_rows(conn, texts):
    fragments = sorted(texts.get_fragments(), key=lambda fragment: fragment.fragment_id)
    counts = np.array([fragment.count_rows() for fragment in fragments], dtype=np.int64)
    starts = np.zeros(fragments[-1].fragment_id + 1, dtype=np.int64)
    starts[[fragment.fragment_id for fragment in fragments]] = np.cumsum(counts) - counts
    stamp = json.dumps([texts.version, str(conn.execute("SELECT max(extracted_at) FROM months").fetchone()[0]), hashlib.sha256(NAMES_FILE.read_bytes()).hexdigest()])
    if BEARING_STAMP.exists() and BEARING_STAMP.read_text(encoding="utf-8") == stamp:
        LOG.info("fact bearing rows reused")
        return np.unpackbits(np.load(BEARING_MASK), count=int(counts.sum())).astype(bool), starts
    data = bytearray()
    with conn.cursor().copy(BEARING, [BOT]) as copy:
        for chunk in copy:
            data += chunk
    LOG.info("fact bearing copied bytes=%d", len(data))
    known = np.unique(np.frombuffer(bytes.fromhex(np.frombuffer(data, dtype=np.uint8).reshape(-1, 19)[:, 2:18].tobytes().decode("ascii")), dtype=">u8").astype(np.uint64))
    del data
    LOG.info("fact bearing digests=%d", len(known))
    mask = np.zeros(int(counts.sum()), dtype=bool)

    def mark(fragment):
        digests = raw(fragment.to_table(columns=["text_sha256"]).column(0).combine_chunks()).reshape(-1, 32)
        keys = np.ascontiguousarray(digests[:, :8]).view(">u8").ravel().astype(np.uint64)
        places = np.minimum(np.searchsorted(known, keys), len(known) - 1)
        mask[starts[fragment.fragment_id]:starts[fragment.fragment_id] + len(keys)] = known[places] == keys

    with ThreadPoolExecutor(ENCODERS) as pool:
        list(pool.map(mark, fragments))
    LOG.info("fact bearing rows=%d of %d", int(mask.sum()), len(mask))
    np.save(BEARING_MASK, np.packbits(mask))
    BEARING_STAMP.write_text(stamp, encoding="utf-8")
    return mask, starts


@timed
def clean_rows(users, labeled, mask, starts):
    names = users.to_table(columns=["author"], scan_in_order=True)["author"]
    labels = pc.fill_null(pc.index_in(names, value_set=labeled), -1).to_numpy()
    rows_of, owners_of, places, position = [], [], [], np.full(len(labeled), -1, dtype=np.int64)
    scanned = kept = 0
    for batch in users.to_batches(columns=["sample_rows"], batch_size=65536, scan_in_order=True):
        who = labels[scanned:scanned + batch.num_rows]
        chosen = np.flatnonzero(who >= 0)
        if len(chosen):
            column = batch["sample_rows"].take(pa.array(chosen))
            sizes = column.value_lengths().to_numpy(zero_copy_only=False).astype(np.int64)
            flat = column.flatten().to_numpy()
            owner = np.repeat(np.arange(len(chosen)), sizes)
            clean = ~mask[starts[(flat >> np.uint64(32)).astype(np.int64)] + (flat & np.uint64(0xFFFFFFFF)).astype(np.int64)]
            owner, flat = owner[clean], flat[clean]
            limit = np.arange(len(owner)) - np.searchsorted(owner, np.arange(len(chosen)))[owner] < CLEAN_TEXTS
            owner, flat = owner[limit], flat[limit]
            present = np.bincount(owner, minlength=len(chosen)) > 0
            rows_of.append(flat)
            owners_of.append((np.cumsum(present) - 1)[owner] + kept)
            places.append(chosen[present] + scanned)
            position[who[chosen[present]]] = np.arange(kept, kept + int(present.sum()))
            kept += int(present.sum())
        scanned += batch.num_rows
        if scanned % (64 * 65536) < batch.num_rows:
            LOG.info("clean rows scanned=%d kept_authors=%d", scanned, kept)
    if scanned != len(names):
        raise ValueError("User store rows changed between the author and sample scans")
    return np.concatenate(rows_of), np.concatenate(owners_of), position, np.concatenate(places)


@timed
def reusable(directory, authors, rows, owners, expected):
    missing = np.full(len(authors), -1, dtype=np.int64)
    if not (directory / "clean_rows.npy").exists():
        return missing
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source"]["months"] != expected["months"] or manifest["source"]["protocol"] != expected["protocol"]:
        return missing
    known = pa.array(json.loads((directory / "authors.json").read_text(encoding="utf-8")))
    earlier = pc.fill_null(pc.index_in(pa.array(authors), value_set=known), -1).to_numpy().astype(np.int64)
    old_rows, old_owners = np.load(directory / "clean_rows.npy"), np.load(directory / "clean_owners.npy")
    old_sizes, sizes = np.bincount(old_owners, minlength=len(known)), np.bincount(owners, minlength=len(authors))
    old_starts, starts = np.cumsum(old_sizes) - old_sizes, np.cumsum(sizes) - sizes
    candidates = np.flatnonzero((earlier >= 0) & (sizes == old_sizes[earlier]))
    lengths = sizes[candidates]
    slot = np.repeat(np.arange(len(candidates)), lengths)
    offset = np.arange(len(slot)) - (np.cumsum(lengths) - lengths)[slot]
    differs = rows[starts[candidates][slot] + offset] != old_rows[old_starts[earlier[candidates]][slot] + offset]
    keep = np.full(len(authors), -1, dtype=np.int64)
    same = candidates[np.bincount(slot, weights=differs, minlength=len(candidates)) == 0]
    keep[same] = earlier[same]
    LOG.info("clean vectors reusable=%d of %d", len(same), len(authors))
    return keep


@timed
def clean_vectors(texts, rows, owners, count, path, previous, earlier):
    vectors = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(count, DIMENSIONS))
    reused = np.flatnonzero(earlier >= 0)
    if len(reused):
        stored = np.load(previous / "users.npy", mmap_mode="r")
        for start in range(0, len(reused), VECTOR_CHUNK):
            chosen = reused[start:start + VECTOR_CHUNK]
            vectors[chosen] = stored[earlier[chosen], :DIMENSIONS]
        del stored
    changed = earlier[owners] < 0
    if not changed.any():
        return vectors
    rows, owners = rows[changed], owners[changed]
    work = VECTOR_WORK / "clean"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    order = np.argsort(rows)
    rows_sorted = rows[order]
    fragments, begins = np.unique(rows_sorted >> np.uint64(32), return_index=True)
    ends = np.append(begins[1:], len(rows_sorted))
    bucket = owners % CLEAN_BUCKETS
    spill = Spill(work, "codes", FETCHED)
    started = time.perf_counter()

    def fetch(index):
        return index, vectors_at(texts, fragments[index], (rows_sorted[begins[index]:ends[index]] & np.uint64(0xFFFFFFFF)).astype(np.int64))

    with ThreadPoolExecutor(ENCODERS) as pool:
        for done, (index, codes) in enumerate(pool.map(fetch, range(len(fragments))), 1):
            slots = order[begins[index]:ends[index]]
            spill.write(bucket[slots], pa.record_batch([pa.array(slots.astype(np.uint64)), pa.FixedSizeListArray.from_arrays(pa.array(codes.ravel()), FEATURES)], schema=FETCHED))
            if done % 256 == 0:
                LOG.info("clean codes fragments=%d/%d seconds=%.1f", done, len(fragments), time.perf_counter() - started)
    spill.close()
    model, scale = load_model("cuda"), scales(texts)
    for part in range(CLEAN_BUCKETS):
        file = work / f"codes_{part}.arrow"
        table = read(file, FETCHED)
        slots = table.column("slot").to_numpy()
        codes = table.column("vector").combine_chunks().flatten().to_numpy().reshape(-1, FEATURES)
        arrangement = np.argsort(owners[slots], kind="stable")
        people, first, sizes = np.unique(owners[slots][arrangement], return_index=True, return_counts=True)
        vectors[people] = head(model, codes[arrangement], scale, first, sizes).astype(np.float16)
        del table, codes
        file.unlink()
        if part % 8 == 7:
            LOG.info("clean vectors buckets=%d/%d seconds=%.1f", part + 1, CLEAN_BUCKETS, time.perf_counter() - started)
    vectors.flush()
    shutil.rmtree(work)
    return vectors


@timed
def prepare(directory, targets):
    targets = validate(targets)
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        expected = source(conn)
    with index_lock(TEXT_STORE), index_lock(VECTOR_STORE), psycopg.connect(DSN) as conn:
        users, texts = lance.dataset(VECTOR_STORE), lance.dataset(TEXT_STORE)
        metadata = users.schema.metadata
        if metadata.get(b"protocol") != PROTOCOL.encode() or json.loads(metadata[b"source"])["months"] != expected["months"]:
            raise ValueError("User vectors do not match the completed source months")
        claims = read_claims(conn, targets)
        names = pc.unique(claims["author"])
        buckets = np.fromiter(map(partition, names.to_pylist()), dtype=np.uint8, count=len(names))
        owner = pc.index_in(claims["author"], value_set=names).to_numpy()
        evaluated = np.isin(buckets[owner], [bucket for name in ("validation", "calibration", "test") for bucket in SPLITS[name]])
        judged = pc.and_(pc.greater_equal(claims["support"], STRICT_SUPPORT), pc.greater_equal(claims["share"], STRICT_SHARE))
        strict = pc.or_(judged, pc.is_in(claims["attribute"], value_set=pa.array(list(FLAIR_ONLY)))).to_numpy(zero_copy_only=False)
        keep = ~evaluated | strict
        claims = claims.filter(pa.array(keep))
        owner = owner[keep]
        chosen = np.flatnonzero(np.bincount(owner, minlength=len(names)) > 0)
        labeled = names.take(pa.array(chosen))
        del names
        remap = np.full(len(buckets), -1, dtype=np.int64)
        remap[chosen] = np.arange(len(chosen))
        owner = remap[owner]
        LOG.info("labeled authors=%d rows=%d", len(labeled), claims.num_rows)
        mask, starts = bearing_rows(conn, texts)
        rows, row_owners, position, places = clean_rows(users, labeled, mask, starts)
        authors = users.to_table(columns=["author"], scan_in_order=True)["author"].take(pa.array(places)).to_pylist()
        del mask, starts
        staging.mkdir(parents=True)
        vectors = clean_vectors(texts, rows, row_owners, len(authors), staging / "users.npy", directory, reusable(directory, authors, rows, row_owners, expected))
    placed = position[owner]
    present = placed >= 0
    labels = np.full((len(authors), len(targets)), np.nan, dtype=np.float32)
    catalogs, excluded = {}, {}
    attributes = claims["attribute"]
    for column, (name, kind) in enumerate(targets.items()):
        selected = np.flatnonzero(present & pc.equal(attributes, name).to_numpy(zero_copy_only=False))
        if not len(selected):
            raise ValueError(f"No observed labels for configured field {name}")
        labels[placed[selected], column], catalog = encode(claims["value"].take(pa.array(selected)), name, kind)
        excluded[name] = int(len(selected) - np.isfinite(labels[placed[selected], column]).sum())
        if catalog is not None:
            catalogs[name] = catalog
    splits = np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors))
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(vectors[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": DIMENSIONS, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    np.save(staging / "labels.npy", labels)
    np.save(staging / "splits.npy", splits)
    np.save(staging / "clean_rows.npy", rows)
    np.save(staging / "clean_owners.npy", row_owners)
    write_json(staging / "authors.json", authors)
    counts = np.isfinite(labels).sum(0)
    manifest = {"targets": targets, "catalogs": catalogs, "authors": len(authors), "source": expected, "features": features, "target_counts": {name: int(count) for name, count in zip(targets, counts)},
                "excluded_out_of_range": excluded, "numeric_ranges": {name: NUMERIC[name] for name, kind in targets.items() if kind == "numeric"}}
    write_json(staging / "manifest.json", manifest)
    del vectors
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"authors": len(authors), "directory": str(directory), "target_counts": manifest["target_counts"], "excluded_out_of_range": excluded}


def load(directory, targets):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    check_targets(targets, manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or arrays["labels"].shape != (manifest["authors"], len(targets)) or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    return manifest, arrays
