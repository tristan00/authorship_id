import json
import shutil
import time
from pathlib import Path

import lance
import numpy as np
import psycopg
import pyarrow as pa
import pyarrow.compute as pc
from psycopg.rows import dict_row
from pyarrow import csv

from author_encoder.config import DIMENSIONS, VECTOR_STORE
from author_encoder.index import PROTOCOL
from author_encoder.lock import index_lock
from claim_consolidation.config import NUMERIC
from claim_extraction.schema import FLAIR_ATTRIBUTES
from database import DSN

from . import LOG, timed, write_json
from .config import DEFAULTS, SPLITS, STRICT_SHARE, STRICT_SUPPORT, VALUE_AUTHORS, check_targets, partition, validate

CLAIMS = "COPY (SELECT author, attribute, value, support, share FROM author_claims WHERE attribute = ANY(%s::claim_field[])) TO STDOUT (FORMAT CSV)"
ARRAYS = ("users", "labels", "splits")
SPREAD_ROWS = 1 << 20


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
    if name in DEFAULTS and DEFAULTS[name] not in catalog:
        catalog.append(DEFAULTS[name])
    return pc.index_in(values, value_set=pa.array(catalog)).to_numpy().astype(np.float64), catalog


@timed
def served(users, labeled, path):
    names = users.to_table(columns=["author"], scan_in_order=True)["author"]
    found = pc.fill_null(pc.index_in(names, value_set=labeled), -1).to_numpy()
    places = np.flatnonzero(found >= 0)
    position = np.full(len(labeled), -1, dtype=np.int64)
    position[found[places]] = np.arange(len(places))
    vectors = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(len(places), DIMENSIONS))
    rows = np.empty(len(places), dtype=np.uint64)
    scanned = kept = 0
    started = time.perf_counter()
    for batch in users.to_batches(columns=["vector", "sample_rows"], batch_size=65536, scan_in_order=True):
        chosen = pa.array(np.flatnonzero(found[scanned:scanned + batch.num_rows] >= 0))
        if len(chosen):
            vectors[kept:kept + len(chosen)] = batch["vector"].take(chosen).flatten().to_numpy().reshape(-1, DIMENSIONS)
            rows[kept:kept + len(chosen)] = pc.list_element(batch["sample_rows"].take(chosen), 0).to_numpy()
            kept += len(chosen)
        scanned += batch.num_rows
        if scanned % (64 * 65536) < batch.num_rows:
            LOG.info("served vectors scanned=%d kept_authors=%d seconds=%.1f", scanned, kept, time.perf_counter() - started)
    if scanned != len(names) or kept != len(places):
        raise ValueError("User store rows changed between the author and vector scans")
    vectors.flush()
    return vectors, rows, position, names.take(pa.array(places)).to_pylist()


@timed
def prepare(directory, targets):
    targets = validate(targets)
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        expected = source(conn)
    with index_lock(VECTOR_STORE), psycopg.connect(DSN) as conn:
        users = lance.dataset(VECTOR_STORE)
        metadata = users.schema.metadata
        if metadata.get(b"protocol") != PROTOCOL.encode() or json.loads(metadata[b"source"])["months"] != expected["months"]:
            raise ValueError("User vectors do not match the completed source months")
        claims = read_claims(conn, targets)
        names = pc.unique(claims["author"])
        buckets = np.fromiter(map(partition, names.to_pylist()), dtype=np.uint8, count=len(names))
        owner = pc.index_in(claims["author"], value_set=names).to_numpy()
        evaluated = np.isin(buckets[owner], [bucket for name in ("validation", "calibration", "test") for bucket in SPLITS[name]])
        judged = pc.and_(pc.greater_equal(claims["support"], STRICT_SUPPORT), pc.greater_equal(claims["share"], STRICT_SHARE))
        strict = pc.or_(judged, pc.is_in(claims["attribute"], value_set=pa.array(list(FLAIR_ATTRIBUTES)))).to_numpy(zero_copy_only=False)
        keep = ~evaluated | strict
        stated = {name: owner[pc.equal(claims["attribute"], name).to_numpy(zero_copy_only=False)] for name in targets if name in DEFAULTS}
        claims = claims.filter(pa.array(keep))
        owner = owner[keep]
        chosen = np.flatnonzero(np.bincount(owner, minlength=len(names)) > 0)
        labeled = names.take(pa.array(chosen))
        del names
        remap = np.full(len(buckets), -1, dtype=np.int64)
        remap[chosen] = np.arange(len(chosen))
        owner = remap[owner]
        stated = {name: remap[found][remap[found] >= 0] for name, found in stated.items()}
        LOG.info("labeled authors=%d rows=%d", len(labeled), claims.num_rows)
        staging.mkdir(parents=True)
        vectors, rows, position, authors = served(users, labeled, staging / "users.npy")
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
        if name in DEFAULTS:
            silent = np.ones(len(authors), dtype=bool)
            spoken = position[stated[name]]
            silent[spoken[spoken >= 0]] = False
            labels[silent, column] = catalog.index(DEFAULTS[name])
    splits = np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors))
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(vectors[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": DIMENSIONS, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    np.save(staging / "labels.npy", labels)
    np.save(staging / "splits.npy", splits)
    np.save(staging / "rows.npy", rows)
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
