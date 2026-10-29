import hashlib
import json
import shutil
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import lance
import numpy as np
import psycopg
import pyarrow as pa
from psycopg import sql

from database import DSN, NO_AUTHOR
from . import LOG, timed
from .config import DIMENSIONS, FETCH_ROWS, FETCH_THREADS, HASH_PARTS, HEAD_USERS, LUAR, MAX_LENGTH, SOURCE_WORKERS, TEXT_STORE, TEXTS_PER_USER, USER_SEARCH, VECTOR_STORE
from .lock import index_lock
from .texts import DIGEST, bounds, raw, scales, span

SOURCE = r"""
    SELECT author,
           array_agg(record_id ORDER BY md5('luar-user-vector-64-v1:' || record_id), record_id),
           array_agg(text_sha256 ORDER BY md5('luar-user-vector-64-v1:' || record_id), record_id)
    FROM records
    WHERE author <> ALL(%(no_author)s)
      AND text_status IN ('available', 'title_only')
    GROUP BY author HAVING count(*) >= 64
    ORDER BY author
"""
PROTOCOL = json.dumps({"model": LUAR, "source": "records joined to stored text vectors by text_sha256", "minimum_usable_texts": TEXTS_PER_USER,
                       "sampled_texts": TEXTS_PER_USER, "dimensions": DIMENSIONS, "max_tokens_per_text": MAX_LENGTH, "preprocessing": "author_encoder.clean",
                       "text_features": "768-dimensional mean-pooled LUAR transformer output stored by author_encoder texts as int8, dequantized with the store's per-dimension int8_scales",
                       "usable": "text_sha256 present in the text vector store, which holds every body that author_encoder.clean leaves nonempty",
                       "sampling": "64 distinct usable records per user with the smallest deterministic seeded MD5 priorities; uniform pseudorandom sampling",
                       "source_sql_sha256": hashlib.sha256(SOURCE.encode()).hexdigest()}, sort_keys=True)
SCHEMA = pa.schema([pa.field("author", pa.string()), pa.field("usable_texts", pa.int32()), pa.field("sample_ids", pa.list_(pa.string())),
                    pa.field("vector", pa.list_(pa.float32(), DIMENSIONS))], metadata={"protocol": PROTOCOL})
SAMPLES = pa.schema([pa.field("author", pa.string()), pa.field("usable_texts", pa.int32()), pa.field("sample_ids", pa.list_(pa.string())),
                     pa.field("sample_sha256", pa.binary(DIGEST * TEXTS_PER_USER))])
SAMPLE_ROWS = 65536


def prefixes(hashes):
    return (hashes[:, 0].astype(np.int32) << 8) | hashes[:, 1]


def keys(hashes):
    words = hashes.view(">u4")
    return (words[:, 0].astype(np.uint64) << np.uint64(32)) | words[:, 1].astype(np.uint64), words[:, 2].astype(np.uint32)


def matches(high, low, stored_high, stored_low):
    found = np.full(len(high), -1, dtype=np.int64)
    left, right = np.searchsorted(stored_high, high, "left"), np.searchsorted(stored_high, high, "right")
    for offset in range(int((right - left).max(initial=0))):
        hit = np.flatnonzero((left + offset < right) & (found < 0))
        rows = left[hit] + offset
        equal = stored_low[rows] == low[hit]
        found[hit[equal]] = rows[equal]
    return found


class TextStore:
    @timed
    def __init__(self, path=TEXT_STORE):
        self.dataset = lance.dataset(path)
        self.scales = scales(self.dataset)
        self.pool = ThreadPoolExecutor(FETCH_THREADS)
        self.cache, self.fragments, start = OrderedDict(), [], 0
        for fragment in self.dataset.get_fragments():
            rows = fragment.count_rows()
            ends = prefixes(raw(fragment.take([0, rows - 1], columns=["text_sha256"]).column(0).combine_chunks()).reshape(2, DIGEST))
            self.fragments.append((fragment, start, int(ends[0]), int(ends[1])))
            start += rows
        LOG.info("text store opened rows=%d fragments=%d version=%d", start, len(self.fragments), self.dataset.version)

    def hashes(self, fragment):
        if fragment.fragment_id not in self.cache:
            self.cache[fragment.fragment_id] = raw(fragment.to_table(columns=["text_sha256"]).column(0).combine_chunks()).reshape(-1, DIGEST)
            if len(self.cache) > 4:
                self.cache.popitem(last=False)
        self.cache.move_to_end(fragment.fragment_id)
        return self.cache[fragment.fragment_id]

    def part(self, index):
        low, high = span(index)
        found, positions = [np.empty((0, DIGEST), dtype=np.uint8)], [np.empty(0, dtype=np.int64)]
        for fragment, start, first, last in self.fragments:
            if first < high and last >= low:
                hashes = self.hashes(fragment)
                rows = np.flatnonzero((prefixes(hashes) >= low) & (prefixes(hashes) < high))
                found.append(hashes[rows])
                positions.append(start + rows)
        stored_high, stored_low = keys(np.concatenate(found))
        order = np.lexsort((stored_low, stored_high))
        return stored_high[order], stored_low[order], np.concatenate(positions)[order]

    @timed
    def fetch(self, positions, digests):
        unique, first, inverse = np.unique(positions, return_index=True, return_inverse=True)
        tables = self.pool.map(lambda rows: self.dataset.take(rows.tolist(), columns=["text_sha256", "vector"]),
                               [unique[start:start + FETCH_ROWS] for start in range(0, len(unique), FETCH_ROWS)])
        stored, vectors = [], []
        for table in tables:
            stored.append(raw(table.column("text_sha256").combine_chunks()))
            values = table.column("vector").combine_chunks()
            vectors.append(values.flatten().to_numpy().reshape(-1, values.type.list_size).astype(np.float32) * self.scales)
        if not np.array_equal(np.concatenate(stored), np.frombuffer(digests, dtype=np.uint8).reshape(-1, DIGEST)[first].reshape(-1)):
            raise ValueError("Fetched text vectors do not match the requested hashes")
        return np.concatenate(vectors)[inverse]


@timed
def unusable(store):
    missing, started = set(), time.perf_counter()
    with psycopg.connect(DSN) as conn:
        for index in range(HASH_PARTS):
            low, high = bounds(index)
            query = sql.SQL("COPY (SELECT text_sha256 FROM bodies WHERE text_sha256 >= {}{} ORDER BY text_sha256) TO STDOUT (FORMAT BINARY)").format(
                sql.Literal(low), sql.SQL(" AND text_sha256 < {}").format(sql.Literal(high)) if high is not None else sql.SQL(""))
            with conn.cursor().copy(query) as copy:
                data = b"".join(bytes(block) for block in copy)
            rows = np.frombuffer(data, dtype=np.uint8, offset=19, count=len(data) - 21).reshape(-1, 6 + DIGEST)
            if not (rows[:, :6] == (0, 1, 0, 0, 0, DIGEST)).all():
                raise ValueError("Unexpected body hash in COPY output")
            hashes = np.ascontiguousarray(rows[:, 6:])
            absent = matches(*keys(hashes), *store.part(index)[:2]) < 0
            missing.update(row.tobytes() for row in hashes[absent])
    LOG.info("unusable bodies=%d seconds=%.1f", len(missing), time.perf_counter() - started)
    return missing


@timed
def sample(samples, missing):
    started, authors, users, pending = time.perf_counter(), 0, 0, []

    def flush():
        table = pa.table([pa.array([author for author, *_ in pending]), pa.array([count for _, count, *_ in pending], pa.int32()),
                          pa.array([ids for _, _, ids, _ in pending], pa.list_(pa.string())),
                          pa.array([digests for *_, digests in pending], pa.binary(DIGEST * TEXTS_PER_USER))], schema=SAMPLES)
        lance.write_dataset(table, samples, mode="append" if samples.exists() else "create")

    with psycopg.connect(DSN) as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        database.execute("SET LOCAL work_mem='256MB'")
        database.execute(f"SET LOCAL max_parallel_workers_per_gather={SOURCE_WORKERS}")
        with database.cursor().copy(f"COPY ({SOURCE}) TO STDOUT (FORMAT BINARY)", {"no_author": NO_AUTHOR}) as copy:
            copy.set_types(["text", "text[]", "bytea[]"])
            for author, records, digests in copy.rows():
                authors += 1
                usable = [index for index, digest in enumerate(digests) if digest not in missing]
                if len(usable) < TEXTS_PER_USER:
                    continue
                chosen = usable[:TEXTS_PER_USER]
                ids = [records[index] for index in chosen]
                if len(set(ids)) != TEXTS_PER_USER:
                    raise ValueError("Each user needs 64 distinct sampled records")
                pending.append((author, len(usable), ids, b"".join(digests[index] for index in chosen)))
                if len(pending) == SAMPLE_ROWS:
                    flush()
                    users, pending = users + len(pending), []
                    LOG.info("user samples authors=%d users=%d last=%s seconds=%.1f", authors, users, author, time.perf_counter() - started)
    if pending:
        flush()
        users += len(pending)
    return {"authors_with_64_records": authors, "users": users, "sample_seconds": time.perf_counter() - started}


@timed
def locate(store, samples):
    dataset = lance.dataset(samples)
    count = dataset.count_rows() * TEXTS_PER_USER
    high, low, filled = np.empty(count, dtype=np.uint64), np.empty(count, dtype=np.uint32), 0
    for batch in dataset.to_batches(columns=["sample_sha256"], batch_size=SAMPLE_ROWS):
        part_high, part_low = keys(np.ascontiguousarray(raw(batch.column(0), DIGEST * TEXTS_PER_USER).reshape(-1, DIGEST)))
        high[filled:filled + len(part_high)], low[filled:filled + len(part_high)] = part_high, part_low
        filled += len(part_high)
    order = np.lexsort((low, high))
    first = (high[order] >> np.uint64(48)).astype(np.int32)
    positions = np.full(count, -1, dtype=np.int64)
    for index in range(HASH_PARTS):
        begin, end = np.searchsorted(first, span(index))
        if begin == end:
            continue
        stored_high, stored_low, stored_positions = store.part(index)
        selected = order[begin:end]
        found = matches(high[selected], low[selected], stored_high, stored_low)
        positions[selected[found >= 0]] = stored_positions[found[found >= 0]]
    if (positions < 0).any():
        raise ValueError("Sampled text hashes are missing from the text vector store")
    return positions


@timed
def vectors(staging, samples, positions, store, model):
    started, offset = time.perf_counter(), 0
    for batch in lance.dataset(samples).to_batches(batch_size=HEAD_USERS):
        count = batch.num_rows
        digests = raw(batch.column("sample_sha256"), DIGEST * TEXTS_PER_USER).tobytes()
        features = store.fetch(positions[offset * TEXTS_PER_USER:(offset + count) * TEXTS_PER_USER], digests)
        users = model.users(features.reshape(count, TEXTS_PER_USER, -1))
        table = pa.table([batch.column("author"), batch.column("usable_texts"), batch.column("sample_ids"),
                          pa.FixedSizeListArray.from_arrays(pa.array(users.reshape(-1)), DIMENSIONS)], schema=SCHEMA)
        lance.write_dataset(table, staging, mode="append" if staging.exists() else "create")
        offset += count
        if offset % (16 * HEAD_USERS) < count:
            LOG.info("user vectors users=%d seconds=%.1f", offset, time.perf_counter() - started)
    return {"vector_seconds": time.perf_counter() - started}


@timed
def build(signature, path=VECTOR_STORE, texts_path=TEXT_STORE):
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = json.dumps({"source": signature, "text_version": lance.dataset(texts_path).version})
    staging, samples, previous = (path.with_name(path.stem + suffix) for suffix in (".building.lance", ".samples.lance", ".previous.lance"))
    with index_lock(path):
        try:
            if previous.exists() and not path.exists():
                previous.rename(path)
            for leftover in (previous, staging, samples):
                shutil.rmtree(leftover, ignore_errors=True)
            if path.exists() and lance.dataset(path).schema.metadata.get(b"source") == stamp.encode():
                LOG.info("user vectors current path=%s source=%s", path, stamp)
                return {"skipped": True}
            from .model import load_model
            store = TextStore(texts_path)
            result = sample(samples, unusable(store))
            result |= vectors(staging, samples, locate(store, samples), store, load_model("cpu"))
            dataset = lance.dataset(staging)
            dataset.optimize.compact_files()
            dataset = lance.dataset(staging)
            rows = dataset.count_rows()
            dataset.create_index("vector", index_type="IVF_RQ", metric="cosine", num_partitions=int(np.sqrt(rows)))
            dataset.create_scalar_index("author", index_type="BTREE")
            dataset.update_schema_metadata({"source": stamp})
            if path.exists():
                path.rename(previous)
            staging.rename(path)
            return result | {"path": str(path), "total_users": rows}
        finally:
            if previous.exists() and not path.exists():
                previous.rename(path)
            for leftover in (previous, staging, samples):
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
    return {"author": author, "usable_texts": rows[0]["usable_texts"], "sampled_texts": TEXTS_PER_USER, "sample_ids": rows[0]["sample_ids"], "dimensions": DIMENSIONS,
            "vector": rows[0]["vector"]}


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
