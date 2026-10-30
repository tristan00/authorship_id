import hashlib
import json
import shutil
import time
from functools import lru_cache

import lance
import numpy as np
import psycopg
import pyarrow as pa
import pyarrow.compute as pc
from pyarrow import csv

from database import DSN, NO_AUTHOR, within
from . import LOG, timed
from .config import BUCKETS, DIMENSIONS, HEAD_TEXTS, LUAR, MAX_LENGTH, RECORD_BLOCKS, TEXT_STORE, TEXTS_PER_USER, USER_SEARCH, VECTOR_STORE, VECTOR_WORK
from .lock import index_lock
from .texts import DIGEST, raw, scales

AUTHOR_SEED, SAMPLE_SEED = 0x9E3779B97F4A7C15, 0x6C7561722D763221
PRIME = np.uint64(0x100000001B3)
SHIFT = np.uint64(56)
UNKNOWN = np.uint64(2**64 - 1)
FEATURES = 768
SOURCE = """COPY (SELECT author, record_id, text_sha256 FROM records WHERE {months} AND ctid >= '({start},0)' AND ctid < '({end},0)'
    AND author <> ALL(%(no_author)s) AND text_status IN ('available', 'title_only')) TO STDOUT (FORMAT CSV)"""
PROTOCOL = json.dumps({"model": LUAR, "source": "records joined to stored text vectors by text_sha256", "minimum_usable_texts": 1,
                       "maximum_sampled_texts": TEXTS_PER_USER, "dimensions": DIMENSIONS, "max_tokens_per_text": MAX_LENGTH, "preprocessing": "author_encoder.clean",
                       "text_features": "768-dimensional mean-pooled LUAR transformer output stored by author_encoder texts as int8, dequantized with the store's per-dimension int8_scales",
                       "usable": "text_status available or title_only, author not in database.NO_AUTHOR, text_sha256 not in empty_bodies",
                       "sampling": "up to 256 usable records per user with the smallest priority; priority is index.digest(record_id, SAMPLE_SEED), FNV-1a over the UTF-8 bytes then splitmix64",
                       "head": "LUAR attention over 1 to 256 texts with padded texts masked, maximum over texts, linear layer, normalization",
                       "order": "rows sorted by author_hash, index.digest(author, AUTHOR_SEED); its top 8 bits are the bucket",
                       "seeds": [AUTHOR_SEED, SAMPLE_SEED], "source_sql_sha256": hashlib.sha256(SOURCE.encode()).hexdigest()}, sort_keys=True)
SCHEMA = pa.schema([pa.field("author", pa.string()), pa.field("author_hash", pa.uint64()), pa.field("usable_texts", pa.int32()),
                    pa.field("sample_ids", pa.list_(pa.string())), pa.field("sample_priorities", pa.list_(pa.uint64())),
                    pa.field("sample_rows", pa.list_(pa.uint64())), pa.field("vector", pa.list_(pa.float32(), DIMENSIONS))], metadata={"protocol": PROTOCOL})
STATE = pa.schema(list(SCHEMA) + [pa.field("changed", pa.bool_())])
RECORDS = pa.schema([pa.field("author", pa.string()), pa.field("author_hash", pa.uint64()), pa.field("record_id", pa.string()),
                     pa.field("priority", pa.uint64()), pa.field("text_sha256", pa.binary(DIGEST))])
REQUESTS = pa.schema([pa.field("bucket", pa.uint16()), pa.field("slot", pa.uint32()), pa.field("row", pa.uint64()), pa.field("text_sha256", pa.binary(DIGEST))])
FETCHED = pa.schema([pa.field("slot", pa.uint32()), pa.field("row", pa.uint64()), pa.field("vector", pa.list_(pa.int8(), FEATURES))])


def mix(value):
    value = (value ^ (value >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    value = (value ^ (value >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return value ^ (value >> np.uint64(31))


def offsets(strings):
    return np.frombuffer(strings.buffers()[1], dtype=np.int32)[strings.offset:strings.offset + len(strings) + 1].astype(np.int64)


def digest(strings, seed):
    value = np.full(len(strings), seed, dtype=np.uint64)
    if not len(strings):
        return value
    bounds = offsets(strings)
    lengths = np.diff(bounds)
    if lengths.min() < 1:
        raise ValueError("Cannot hash an empty string")
    data = np.frombuffer(strings.buffers()[2], dtype=np.uint8)
    order = np.argsort(-lengths, kind="stable")
    starts, longest = bounds[:-1][order], -lengths[order]
    hashed = value[order]
    for column in range(int(-longest[0])):
        count = int(np.searchsorted(longest, -column, "left"))
        hashed[:count] = (hashed[:count] ^ data[starts[:count] + column]) * PRIME
    value[order] = hashed
    return mix(value)


def hexes(strings):
    bounds = offsets(strings)
    if not (np.diff(bounds) == 2 + 2 * DIGEST).all():
        raise ValueError("Unexpected text_sha256 in COPY output")
    text = np.frombuffer(strings.buffers()[2], dtype=np.uint8)[bounds[0]:bounds[-1]].reshape(-1, 2 + 2 * DIGEST)[:, 2:]
    return np.frombuffer(bytes.fromhex(text.tobytes().decode("ascii")), dtype=np.uint8).reshape(-1, DIGEST)


def fixed(hashes):
    return pa.FixedSizeBinaryArray.from_buffers(pa.binary(DIGEST), len(hashes), [None, pa.py_buffer(np.ascontiguousarray(hashes).tobytes())])


def prefix(hashes):
    return np.ascontiguousarray(hashes[:, :8]).view(">u8").ravel().astype(np.uint64)


def find(stored, wanted):
    keys, targets = prefix(stored), prefix(wanted)
    left, right = np.searchsorted(keys, targets, "left"), np.searchsorted(keys, targets, "right")
    found = np.full(len(wanted), -1, dtype=np.int64)
    for offset in range(int((right - left).max(initial=0))):
        hit = np.flatnonzero((left + offset < right) & (found < 0))
        equal = (stored[left[hit] + offset] == wanted[hit]).all(1)
        found[hit[equal]] = left[hit[equal]] + offset
    return found


def lists(sizes, values):
    return pa.ListArray.from_arrays(pa.array(np.concatenate([[0], np.cumsum(sizes)]).astype(np.int32)), values)


def read(path, schema):
    return pa.ipc.open_stream(str(path)).read_all() if path.exists() else schema.empty_table()


class Spill:
    def __init__(self, folder, name, schema):
        self.folder, self.name, self.schema, self.writers = folder, name, schema, {}

    def path(self, key):
        return self.folder / f"{self.name}_{key}.arrow"

    def write(self, keys, batch):
        order = np.argsort(keys, kind="stable")
        ordered = keys[order]
        batch = batch.take(pa.array(order))
        for key in np.unique(ordered):
            begin, end = np.searchsorted(ordered, key, "left"), np.searchsorted(ordered, key, "right")
            if key not in self.writers:
                self.writers[key] = pa.ipc.new_stream(str(self.path(key)), self.schema)
            self.writers[key].write_batch(batch.slice(begin, end - begin))

    def close(self):
        for writer in self.writers.values():
            writer.close()
        self.writers = {}


@timed
def text_layout(path):
    dataset = lance.dataset(path)
    fragments = []
    for fragment in dataset.get_fragments():
        rows = fragment.count_rows()
        ends = raw(fragment.take([0, rows - 1], columns=["text_sha256"]).column(0).combine_chunks()).reshape(2, DIGEST)
        fragments.append((fragment.fragment_id, rows, ends[0].tobytes().hex(), ends[1].tobytes().hex()))
    LOG.info("text store opened fragments=%d rows=%d version=%d", len(fragments), sum(rows for _, rows, _, _ in fragments), dataset.version)
    return dataset, sorted(fragments)


def layout(fragments, count):
    return hashlib.sha256(json.dumps(fragments[:count]).encode()).hexdigest()


@timed
def collect(months, work, buckets):
    spill, started, read_rows, kept = Spill(work, "records", RECORDS), time.perf_counter(), 0, 0
    with psycopg.connect(DSN, autocommit=True) as conn:
        empty = np.frombuffer(b"".join(row[0] for row in conn.execute("SELECT text_sha256 FROM empty_bodies")), dtype=np.uint8).reshape(-1, DIGEST)
        empty = empty[np.argsort(prefix(empty), kind="stable")]
        blocks = conn.execute("SELECT max(pg_relation_size(relid)) / current_setting('block_size')::bigint FROM pg_partition_tree('records') WHERE isleaf").fetchone()[0]
        LOG.info("user records months=%s blocks=%d empty_bodies=%d", months, blocks, len(empty))
        for start in range(0, blocks, RECORD_BLOCKS):
            query = SOURCE.format(months=within(months, "created_utc"), start=start, end=start + RECORD_BLOCKS)
            with conn.cursor().copy(query, {"no_author": NO_AUTHOR}) as copy:
                data = b"".join(bytes(block) for block in copy)
            if data:
                table = csv.read_csv(pa.BufferReader(data), read_options=csv.ReadOptions(column_names=["author", "record_id", "text_sha256"], use_threads=False, block_size=1 << 30),
                                     convert_options=csv.ConvertOptions(column_types=dict.fromkeys(["author", "record_id", "text_sha256"], pa.string())))
                author, record, text = (table.column(name).combine_chunks() for name in ("author", "record_id", "text_sha256"))
                hashes = hexes(text)
                authors = pc.dictionary_encode(author)
                author_hash = digest(authors.dictionary, AUTHOR_SEED)[authors.indices.to_numpy()]
                bucket = author_hash >> SHIFT
                keep = np.flatnonzero((find(empty, hashes) < 0) & (bucket < buckets))
                selected = pa.array(keep)
                spill.write(bucket[keep], pa.record_batch([author.take(selected), pa.array(author_hash[keep]), record.take(selected),
                                                           pa.array(digest(record, SAMPLE_SEED)[keep]), fixed(hashes[keep])], schema=RECORDS))
                read_rows, kept = read_rows + table.num_rows, kept + len(keep)
            if start // RECORD_BLOCKS % 16 == 15:
                LOG.info("user records blocks=%d/%d rows=%d kept=%d seconds=%.1f", start + RECORD_BLOCKS, blocks, read_rows, kept, time.perf_counter() - started)
    spill.close()
    return {"records": read_rows, "usable_records": kept}


def previous(path, buckets):
    batches = iter(lance.dataset(path).to_batches(columns=SCHEMA.names, batch_size=65536, scan_in_order=True)) if path else iter(())
    pending = next(batches, None)
    for bucket in range(buckets):
        parts = []
        while pending is not None:
            cut = int(np.searchsorted(pending.column("author_hash").to_numpy() >> SHIFT, bucket + 1))
            parts.append(pending.slice(0, cut))
            if cut < pending.num_rows:
                pending = pending.slice(cut)
                break
            pending = next(batches, None)
        yield pa.Table.from_batches(parts, SCHEMA)
    if pending is not None:
        raise ValueError("The user store holds buckets beyond the build")


def merge(new, old):
    old_hash, new_hash = old.column("author_hash").to_numpy(), new.column("author_hash").to_numpy()
    if (old_hash[1:] <= old_hash[:-1]).any():
        raise ValueError("The user store is not sorted by author_hash")
    hashes = np.union1d(old_hash, new_hash)
    count, old_user, new_user = len(hashes), np.searchsorted(hashes, old_hash), np.searchsorted(hashes, new_hash)
    known, first = np.full(count, -1, dtype=np.int64), np.zeros(count, dtype=np.int64)
    known[old_user], first[new_user] = np.arange(len(old_user)), np.arange(len(new_user))
    new_author = new.column("author").combine_chunks()
    names = pa.concat_arrays([old.column("author").combine_chunks(), new_author]).take(pa.array(np.where(known >= 0, known, len(old_user) + first)))
    if len(new) and not names.take(pa.array(new_user)).equals(new_author):
        raise ValueError("Two authors share an author_hash")
    sizes = old.column("sample_priorities").combine_chunks().value_lengths().to_numpy(zero_copy_only=False).astype(np.int64)
    old_samples = int(sizes.sum())
    user = np.concatenate([np.repeat(old_user, sizes), new_user])
    priority = np.concatenate([old.column("sample_priorities").combine_chunks().flatten().to_numpy(), new.column("priority").to_numpy()])
    rows = np.concatenate([old.column("sample_rows").combine_chunks().flatten().to_numpy(), np.full(len(new), UNKNOWN)])
    ids = pa.concat_arrays([old.column("sample_ids").combine_chunks().flatten(), new.column("record_id").combine_chunks()])
    order = np.lexsort((priority, user))
    ordered = user[order]
    if ((ordered[1:] == ordered[:-1]) & (priority[order][1:] == priority[order][:-1])).any():
        raise ValueError("Two records of one author share a sample priority")
    rank = np.arange(len(order)) - np.searchsorted(ordered, np.arange(count))[ordered]
    kept = order[rank < TEXTS_PER_USER]
    owner = user[kept]
    usable = np.bincount(new_user, minlength=count)
    usable[old_user] += old.column("usable_texts").to_numpy()
    changed = np.bincount(owner[kept >= old_samples], minlength=count) > 0
    vectors = np.zeros((count, DIMENSIONS), dtype=np.float32)
    vectors[old_user] = old.column("vector").combine_chunks().flatten().to_numpy().reshape(-1, DIMENSIONS)
    sizes = np.bincount(owner, minlength=count)
    state = pa.table([names, pa.array(hashes), pa.array(usable.astype(np.int32)), lists(sizes, ids.take(pa.array(kept))), lists(sizes, pa.array(priority[kept])),
                      lists(sizes, pa.array(rows[kept])), pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel()), DIMENSIONS), pa.array(changed)], schema=STATE)
    fetch = kept[changed[owner]]
    fresh = fetch >= old_samples
    shas = np.zeros((len(fetch), DIGEST), dtype=np.uint8)
    shas[fresh] = raw(new.column("text_sha256").combine_chunks()).reshape(-1, DIGEST)[fetch[fresh] - old_samples]
    return state, rows[fetch], shas, fresh


@timed
def sample(work, old, buckets, fragments):
    spill, started, totals = Spill(work, "requests", REQUESTS), time.perf_counter(), {"users": 0, "changed_users": 0, "fetched_texts": 0}
    parts = np.full(max((fragment for fragment, *_ in fragments), default=0) + 1, -1, dtype=np.int64)
    for fragment, _, first, _ in fragments:
        parts[fragment] = int(first[:2], 16)
    for bucket, before in enumerate(old):
        path = work / f"records_{bucket}.arrow"
        state, rows, shas, fresh = merge(read(path, RECORDS), before)
        path.unlink(missing_ok=True)
        with pa.ipc.new_stream(str(work / f"state_{bucket}.arrow"), STATE) as writer:
            writer.write_table(state)
        if len(rows):
            part = np.where(fresh, shas[:, 0], parts[np.minimum(rows >> np.uint64(32), np.uint64(len(parts) - 1)).astype(np.int64)])
            if (part < 0).any() or ((rows[~fresh] >> np.uint64(32)) >= len(parts)).any():
                raise ValueError("Sampled text rows point outside the text store")
            spill.write(part, pa.record_batch([pa.array(np.full(len(rows), bucket, dtype=np.uint16)), pa.array(np.arange(len(rows), dtype=np.uint32)), pa.array(rows),
                                               fixed(shas)], schema=REQUESTS))
        totals = {"users": totals["users"] + state.num_rows, "changed_users": totals["changed_users"] + int(np.count_nonzero(state.column("changed").to_numpy(zero_copy_only=False))),
                  "fetched_texts": totals["fetched_texts"] + len(rows)}
        if bucket % 16 == 15:
            LOG.info("user samples buckets=%d/%d %s seconds=%.1f", bucket + 1, buckets, totals, time.perf_counter() - started)
    spill.close()
    return totals


@timed
def fetch(work, dataset, fragments):
    spill, started, located = Spill(work, "features", FETCHED), time.perf_counter(), 0
    for part in range(256):
        path = work / f"requests_{part}.arrow"
        requests = read(path, REQUESTS)
        if not len(requests):
            continue
        rows = requests.column("row").to_numpy().copy()
        unknown = np.flatnonzero(rows == UNKNOWN)
        if len(unknown):
            stored, addresses = [], []
            for fragment, count, first, last in fragments:
                if int(first[:2], 16) <= part <= int(last[:2], 16):
                    stored.append(raw(dataset.get_fragment(fragment).to_table(columns=["text_sha256"]).column(0).combine_chunks()).reshape(-1, DIGEST))
                    addresses.append((np.uint64(fragment) << np.uint64(32)) + np.arange(count, dtype=np.uint64))
            if not stored:
                raise ValueError("Sampled text hashes are missing from the text vector store")
            stored, addresses = np.concatenate(stored), np.concatenate(addresses)
            order = np.argsort(prefix(stored), kind="stable")
            found = find(stored[order], raw(requests.column("text_sha256").combine_chunks()).reshape(-1, DIGEST)[unknown])
            if (found < 0).any():
                raise ValueError("Sampled text hashes are missing from the text vector store")
            rows[unknown] = addresses[order][found]
            located += len(unknown)
        owners, offsets = rows >> np.uint64(32), (rows & np.uint64(0xFFFFFFFF)).astype(np.int64)
        codes = np.empty((len(rows), FEATURES), dtype=np.int8)
        for fragment in np.unique(owners):
            selected = np.flatnonzero(owners == fragment)
            unique, inverse = np.unique(offsets[selected], return_inverse=True)
            values = dataset.get_fragment(int(fragment)).take(unique.tolist(), columns=["vector"]).column(0).combine_chunks()
            codes[selected] = values.flatten().to_numpy().reshape(-1, FEATURES)[inverse]
        spill.write(requests.column("bucket").to_numpy(), pa.record_batch([requests.column("slot").combine_chunks(), pa.array(rows),
                                                                           pa.FixedSizeListArray.from_arrays(pa.array(codes.ravel()), FEATURES)], schema=FETCHED))
        path.unlink()
        if part % 16 == 15:
            LOG.info("user features parts=%d/256 located=%d seconds=%.1f", part + 1, located, time.perf_counter() - started)
    spill.close()
    return {"located_texts": located}


def head(model, codes, scale, starts, lengths):
    vectors, order, begin = np.empty((len(lengths), DIMENSIONS), dtype=np.float32), np.argsort(lengths, kind="stable"), 0
    while begin < len(order):
        widths = lengths[order[begin:begin + HEAD_TEXTS]]
        end = begin + max(1, int(np.count_nonzero(np.arange(1, len(widths) + 1) * widths <= HEAD_TEXTS)))
        users = order[begin:end]
        width = int(lengths[users].max())
        present = np.arange(width) < lengths[users, None]
        batch = codes[np.where(present, starts[users, None] + np.arange(width), 0)].astype(np.float32) * scale * present[:, :, None]
        vectors[users] = model.users(batch, lengths[users])
        begin = end
    return vectors


@timed
def encode(work, staging, buckets, model, scale):
    started, users = time.perf_counter(), 0
    for bucket in range(buckets):
        state = read(work / f"state_{bucket}.arrow", STATE)
        fetched = read(work / f"features_{bucket}.arrow", FETCHED)
        changed = state.column("changed").to_numpy(zero_copy_only=False)
        sizes = state.column("sample_ids").combine_chunks().value_lengths().to_numpy(zero_copy_only=False).astype(np.int64)
        lengths = sizes[changed]
        slots = fetched.column("slot").to_numpy()
        if not np.array_equal(np.bincount(slots, minlength=int(lengths.sum())), np.ones(int(lengths.sum()), dtype=np.int64)):
            raise ValueError(f"Bucket {bucket} did not receive each sampled text exactly once")
        codes = np.empty((len(slots), FEATURES), dtype=np.int8)
        codes[slots] = fetched.column("vector").combine_chunks().flatten().to_numpy().reshape(-1, FEATURES)
        rows = state.column("sample_rows").combine_chunks().flatten().to_numpy().copy()
        rows[np.repeat(changed, sizes)] = fetched.column("row").to_numpy()[np.argsort(slots)]
        vectors = state.column("vector").combine_chunks().flatten().to_numpy().reshape(-1, DIMENSIONS).copy()
        vectors[changed] = head(model, codes, scale, np.concatenate([[0], np.cumsum(lengths)[:-1]]).astype(np.int64), lengths)
        table = pa.table([*state.columns[:5], lists(sizes, pa.array(rows)), pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel()), DIMENSIONS)], schema=SCHEMA)
        if table.num_rows:
            lance.write_dataset(table, staging, mode="append" if staging.exists() else "create")
        for name in ("state", "features"):
            (work / f"{name}_{bucket}.arrow").unlink(missing_ok=True)
        users += table.num_rows
        if bucket % 16 == 15:
            LOG.info("user vectors buckets=%d/%d users=%d seconds=%.1f", bucket + 1, buckets, users, time.perf_counter() - started)
    return {"stored_users": users}


def source(path):
    if not path.exists():
        return None
    metadata = lance.dataset(path).schema.metadata
    return json.loads(metadata[b"source"]) if metadata.get(b"protocol") == PROTOCOL.encode() and b"source" in metadata else None


@timed
def build(loaded, path=VECTOR_STORE, texts_path=TEXT_STORE, buckets=BUCKETS):
    path.parent.mkdir(parents=True, exist_ok=True)
    staging, prior = (path.with_name(path.stem + suffix) for suffix in (".building.lance", ".previous.lance"))
    work = VECTOR_WORK / path.stem
    with index_lock(path):
        try:
            if prior.exists() and not path.exists():
                prior.rename(path)
            for leftover in (prior, staging, work):
                shutil.rmtree(leftover, ignore_errors=True)
            current = source(path)
            if current is not None and current["months"] == loaded and current["buckets"] == buckets:
                LOG.info("user vectors current path=%s months=%s", path, loaded)
                return {"skipped": True}
            dataset, fragments = text_layout(texts_path)
            base = current is not None and current["buckets"] == buckets and all(loaded.get(month) == stamp for month, stamp in current["months"].items()) \
                and current["fragments"] <= len(fragments) and layout(fragments, current["fragments"]) == current["layout"]
            added = sorted(set(loaded) - set(current["months"] if base else ()))
            LOG.info("user vectors path=%s incremental=%s added=%s buckets=%d", path, base, added, buckets)
            work.mkdir(parents=True)
            result = {"incremental": base, "added": added} | collect(added, work, buckets)
            result |= sample(work, previous(path if base else None, buckets), buckets, fragments)
            result |= fetch(work, dataset, fragments)
            from .model import load_model
            result |= encode(work, staging, buckets, load_model("cpu"), scales(dataset))
            if not staging.exists():
                lance.write_dataset(SCHEMA.empty_table(), staging)
            stored = lance.dataset(staging)
            rows = stored.count_rows()
            stored.create_index("vector", index_type="IVF_RQ", metric="cosine", num_partitions=max(1, int(np.sqrt(rows))))
            stored.create_scalar_index("author", index_type="BTREE")
            lance.dataset(staging).update_schema_metadata({"source": json.dumps({"months": loaded, "buckets": buckets, "fragments": len(fragments),
                                                                                  "layout": layout(fragments, len(fragments))}, sort_keys=True)})
            del stored
            if path.exists():
                path.rename(prior)
            staging.rename(path)
            return result | {"path": str(path), "total_users": rows}
        finally:
            if prior.exists() and not path.exists():
                prior.rename(path)
            for leftover in (prior, staging, work):
                shutil.rmtree(leftover, ignore_errors=True)


@lru_cache(maxsize=1)
def opened(path, signature):
    return lance.dataset(path)


def users(path=VECTOR_STORE):
    return opened(path, path.stat().st_mtime_ns) if path.exists() else None


@timed
def vector(author, path=VECTOR_STORE):
    rows = users(path).to_table(columns=["usable_texts", "sample_ids", "vector"], filter="author = '" + author.replace("'", "''") + "'").to_pylist()
    if not rows:
        return None
    return {"author": author, "usable_texts": rows[0]["usable_texts"], "sampled_texts": len(rows[0]["sample_ids"]), "sample_ids": rows[0]["sample_ids"],
            "dimensions": DIMENSIONS, "vector": rows[0]["vector"]}


@timed
def similar(author, limit=50, path=VECTOR_STORE):
    if not 1 <= limit <= 200:
        raise ValueError("Similarity result limit must be between 1 and 200")
    found = vector(author, path)
    if found is None:
        return None
    table = users(path).to_table(nearest={"column": "vector", "q": np.asarray(found["vector"], dtype=np.float32), "k": limit + 1, **USER_SEARCH}, columns=["author", "_distance"])
    pairs = zip(table.column("author").to_pylist(), table.column("_distance").to_pylist())
    return [{"author": name, "similarity": float(np.clip(1 - distance, -1, 1))} for name, distance in pairs if name != author][:limit]
