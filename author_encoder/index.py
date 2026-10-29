import hashlib
import json
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
from .texts import scales

DIGEST = 32
SOURCE = r"""
    SELECT author,
           array_agg(record_id ORDER BY md5('luar-user-vector-64-v1:' || record_id), record_id),
           array_agg(text_sha256 ORDER BY md5('luar-user-vector-64-v1:' || record_id), record_id)
    FROM records
    WHERE author <> ALL(%(no_author)s)
      AND author > %(after)s
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


def prefixes(digests):
    if len(digests) % DIGEST:
        raise ValueError("Text hashes must be 32 bytes")
    return np.frombuffer(digests, dtype="<u8").reshape(-1, DIGEST // 8)[:, 0]


def raw(column):
    return np.frombuffer(column.buffers()[1], dtype=np.uint8)[column.offset * DIGEST:(column.offset + len(column)) * DIGEST]


class TextVectors:
    @timed
    def __init__(self, path=TEXT_STORE):
        self.dataset = lance.dataset(path)
        self.scales = scales(self.dataset)
        count = self.dataset.count_rows()
        if count >= 2**31:
            raise ValueError("Text vector store exceeds int32 row positions")
        keys, filled = np.empty(count, dtype=np.uint64), 0
        for batch in self.dataset.to_batches(columns=["text_sha256"], batch_size=1 << 20):
            column = batch.column(0)
            keys[filled:filled + len(column)] = prefixes(raw(column))
            filled += len(column)
        if filled != count:
            raise ValueError("Text vector store changed while it was read")
        order = np.argsort(keys)
        self.keys, self.positions = keys[order], order.astype(np.int32)
        del keys, order
        if (self.keys[1:] == self.keys[:-1]).any():
            raise ValueError("Text vector store has colliding 8-byte hash prefixes")
        self.pool = ThreadPoolExecutor(FETCH_THREADS)
        LOG.info("text vectors opened rows=%d version=%d", count, self.dataset.version)

    def locate(self, digests):
        keys = prefixes(digests)
        index = np.minimum(np.searchsorted(self.keys, keys), len(self.keys) - 1)
        return np.where(self.keys[index] == keys, self.positions[index], -1)

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
def stream(staging, after, texts, model):
    started, authors, users, pending = time.perf_counter(), 0, 0, []
    with psycopg.connect(DSN) as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        database.execute("SET LOCAL work_mem='256MB'")
        database.execute(f"SET LOCAL max_parallel_workers_per_gather={SOURCE_WORKERS}")
        with database.cursor().copy(f"COPY ({SOURCE}) TO STDOUT (FORMAT BINARY)", {"no_author": NO_AUTHOR, "after": after}) as copy:
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
def build(path=VECTOR_STORE, texts_path=TEXT_STORE):
    path.parent.mkdir(parents=True, exist_ok=True)
    with index_lock(path):
        if path.exists():
            return {"path": str(path), "total_users": lance.dataset(path).count_rows()}
        staging, after = path.with_name(path.stem + ".building.lance"), ""
        if staging.exists():
            dataset = lance.dataset(staging)
            if dataset.schema.metadata[b"protocol"].decode() != PROTOCOL:
                raise ValueError("Partial user vector store uses a different protocol")
            after = dataset.take([dataset.count_rows() - 1], columns=["author"]).column(0)[0].as_py()
            LOG.info("user vectors resuming after=%s users=%d", after, dataset.count_rows())
        from .model import load_model
        result = stream(staging, after, TextVectors(texts_path), load_model("cpu"))
        dataset = lance.dataset(staging)
        dataset.optimize.compact_files()
        dataset = lance.dataset(staging)
        rows = dataset.count_rows()
        dataset.create_index("vector", index_type="IVF_RQ", metric="cosine", num_partitions=int(np.sqrt(rows)))
        dataset.create_scalar_index("author", index_type="BTREE")
        staging.rename(path)
        return result | {"path": str(path), "total_users": rows}


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
