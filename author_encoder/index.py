import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import lance
import numpy as np
import psycopg
import pyarrow as pa

from database import DSN, NO_AUTHOR
from . import LOG, timed
from .config import DIMENSIONS, FETCH_ROWS, FETCH_THREADS, HEAD_USERS, LUAR, MAX_LENGTH, SOURCE_WORKERS, TEXT_STORE, TEXTS_PER_USER, USER_SEARCH, VECTOR_STORE
from .lock import index_lock
from .texts import DIGEST, raw, scales

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


def keys(digests):
    words = np.frombuffer(digests, dtype=">u4").reshape(-1, DIGEST // 4)
    return (words[:, 0].astype(np.uint64) << np.uint64(32)) | words[:, 1].astype(np.uint64), words[:, 2].astype(np.uint32)


def ordered(high, low):
    return bool(np.all((high[1:] > high[:-1]) | ((high[1:] == high[:-1]) & (low[1:] >= low[:-1]))))


class TextVectors:
    @timed
    def __init__(self, path=TEXT_STORE):
        self.dataset = lance.dataset(path)
        self.scales = scales(self.dataset)
        count = self.dataset.count_rows()
        if count >= 2**31:
            raise ValueError("Text vector store exceeds int32 row positions")
        self.high, self.low, self.runs, filled = np.empty(count, dtype=np.uint64), np.empty(count, dtype=np.uint32), [], 0
        for fragment in self.dataset.get_fragments():
            high, low = keys(raw(fragment.to_table(columns=["text_sha256"]).column(0).combine_chunks()))
            if not ordered(high, low):
                raise ValueError(f"Text vector fragment {fragment.fragment_id} is not sorted by text_sha256")
            if self.runs and ordered(np.array([self.high[filled - 1], high[0]]), np.array([self.low[filled - 1], low[0]])):
                self.runs[-1][1] = filled + len(high)
            else:
                self.runs.append([filled, filled + len(high)])
            self.high[filled:filled + len(high)], self.low[filled:filled + len(high)] = high, low
            filled += len(high)
        if filled != count:
            raise ValueError("Text vector store changed while it was read")
        self.pool = ThreadPoolExecutor(FETCH_THREADS)
        LOG.info("text vectors opened rows=%d runs=%d version=%d", count, len(self.runs), self.dataset.version)

    def locate(self, digests):
        high, low = keys(digests)
        positions = np.full(len(high), -1, dtype=np.int64)
        for start, end in self.runs:
            left, right = np.searchsorted(self.high[start:end], high, "left"), np.searchsorted(self.high[start:end], high, "right")
            for offset in range(int((right - left).max(initial=0))):
                hit = (left + offset < right) & (positions < 0)
                rows = start + left[hit] + offset
                matched = self.low[rows] == low[hit]
                positions[np.flatnonzero(hit)[matched]] = rows[matched]
        return positions

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


def append(staging, pending, texts, model):
    digests = b"".join(digest for *_, digest in pending)
    features = texts.fetch(np.concatenate([positions for _, _, _, positions, _ in pending]), digests)
    vectors = model.users(features.reshape(len(pending), TEXTS_PER_USER, -1))
    table = pa.table([pa.array([author for author, *_ in pending]), pa.array([count for _, count, *_ in pending], pa.int32()),
                      pa.array([ids for _, _, ids, *_ in pending], pa.list_(pa.string())),
                      pa.FixedSizeListArray.from_arrays(pa.array(vectors.reshape(-1)), DIMENSIONS)], schema=SCHEMA)
    lance.write_dataset(table, staging, mode="append" if staging.exists() else "create")


@timed
def stream(staging, texts, model):
    started, authors, users, pending = time.perf_counter(), 0, 0, []
    with psycopg.connect(DSN) as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        database.execute("SET LOCAL work_mem='256MB'")
        database.execute(f"SET LOCAL max_parallel_workers_per_gather={SOURCE_WORKERS}")
        with database.cursor().copy(f"COPY ({SOURCE}) TO STDOUT (FORMAT BINARY)", {"no_author": NO_AUTHOR}) as copy:
            copy.set_types(["text", "text[]", "bytea[]"])
            for author, records, digests in copy.rows():
                authors += 1
                positions = texts.locate(b"".join(digests))
                usable = np.flatnonzero(positions >= 0)
                if len(usable) < TEXTS_PER_USER:
                    continue
                chosen = usable[:TEXTS_PER_USER]
                ids = [records[index] for index in chosen]
                if len(set(ids)) != TEXTS_PER_USER:
                    raise ValueError("Each user needs 64 distinct sampled records")
                pending.append((author, len(usable), ids, positions[chosen], b"".join(digests[index] for index in chosen)))
                if len(pending) == HEAD_USERS:
                    append(staging, pending, texts, model)
                    users, pending = users + len(pending), []
                    LOG.info("user vectors authors=%d users=%d last=%s seconds=%.1f", authors, users, author, time.perf_counter() - started)
    if pending:
        append(staging, pending, texts, model)
        users += len(pending)
    return {"authors_with_64_records": authors, "users": users, "seconds": time.perf_counter() - started}


@timed
def build(signature, path=VECTOR_STORE, texts_path=TEXT_STORE):
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = json.dumps({"source": signature, "text_version": lance.dataset(texts_path).version})
    staging, previous = path.with_name(path.stem + ".building.lance"), path.with_name(path.stem + ".previous.lance")
    with index_lock(path):
        try:
            if previous.exists() and not path.exists():
                previous.rename(path)
            shutil.rmtree(previous, ignore_errors=True)
            shutil.rmtree(staging, ignore_errors=True)
            if path.exists() and lance.dataset(path).schema.metadata.get(b"source") == stamp.encode():
                LOG.info("user vectors current path=%s source=%s", path, stamp)
                return {"skipped": True}
            from .model import load_model
            result = stream(staging, TextVectors(texts_path), load_model("cpu"))
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
            shutil.rmtree(previous, ignore_errors=True)
            shutil.rmtree(staging, ignore_errors=True)


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
    matches = zip(table.column("author").to_pylist(), table.column("_distance").to_pylist())
    return [{"author": name, "similarity": float(np.clip(1 - distance, -1, 1))} for name, distance in matches if name != author][:limit]
