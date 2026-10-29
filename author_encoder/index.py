import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import lance
import numpy as np
import psycopg

from database import DSN, NO_AUTHOR
from . import LOG, timed
from .config import FETCH_ROWS, FETCH_THREADS, HEAD_USERS, LUAR, SOURCE_WORKERS, TEXT_STORE, TEXTS_PER_USER, VECTOR_STORE
from .lock import index_lock
from .model import load_model

DIGEST = 32
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


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save_state(conn, state):
    conn.execute("INSERT INTO metadata VALUES ('state', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [json.dumps(state)])
    conn.commit()


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
            vectors.append(values.flatten().to_numpy(zero_copy_only=False).reshape(-1, values.type.list_size))
        if not np.array_equal(np.concatenate(stored), np.frombuffer(digests, dtype=np.uint8).reshape(-1, DIGEST)[first].reshape(-1)):
            raise ValueError("Fetched text vectors do not match the requested hashes")
        return np.concatenate(vectors)[inverse]


@timed
def source(conn, state, texts):
    conn.execute("DELETE FROM users")
    state.update(status="sampling", users=0, encoded=0, updated_at=timestamp())
    save_state(conn, state)
    started = time.perf_counter()
    authors = 0
    with psycopg.connect(DSN) as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        database.execute("SET LOCAL work_mem='256MB'")
        database.execute(f"SET LOCAL max_parallel_workers_per_gather={SOURCE_WORKERS}")
        state["source_snapshot_at"] = str(database.execute("SELECT transaction_timestamp()").fetchone()[0])
        with database.cursor().copy(f"COPY ({SOURCE}) TO STDOUT (FORMAT BINARY)", {"no_author": NO_AUTHOR}) as copy:
            copy.set_types(["text", "text[]", "bytea[]"])
            for author, records, digests in copy.rows():
                authors += 1
                usable = np.flatnonzero(texts.locate(b"".join(digests)) >= 0)
                if len(usable) >= TEXTS_PER_USER:
                    chosen = usable[:TEXTS_PER_USER]
                    ids = [records[index] for index in chosen]
                    if len(set(ids)) != TEXTS_PER_USER:
                        raise ValueError("Each user needs 64 distinct sampled records")
                    conn.execute("INSERT INTO users(author, usable_texts, sample_ids, sample_sha256) VALUES (?, ?, ?, ?)",
                                 [author, len(usable), json.dumps(ids), b"".join(digests[index] for index in chosen)])
                    state["users"] += 1
                if authors % 65536 == 0:
                    state["updated_at"] = timestamp()
                    save_state(conn, state)
                    LOG.info("vector sampling authors=%d users=%d seconds=%.1f", authors, state["users"], time.perf_counter() - started)
    state.update(status="encoding", authors_with_64_records=authors, sampling_seconds=time.perf_counter() - started, updated_at=timestamp())
    save_state(conn, state)


@timed
def encode(conn, state, texts, model):
    started, previous_seconds, last = time.perf_counter(), state.get("encoding_seconds", 0.), ""
    state["encoded"] = conn.execute("SELECT count(*) FROM users WHERE vector IS NOT NULL").fetchone()[0]
    while batch := conn.execute("SELECT author, sample_sha256 FROM users WHERE vector IS NULL AND author > ? ORDER BY author LIMIT ?", [last, HEAD_USERS]).fetchall():
        digests = b"".join(blob for _, blob in batch)
        positions = texts.locate(digests)
        if (positions < 0).any():
            raise ValueError("Sampled text hashes are missing from the text vector store")
        vectors = model.users(texts.fetch(positions, digests).reshape(len(batch), TEXTS_PER_USER, -1))
        conn.executemany("UPDATE users SET vector=? WHERE author=?", [(vector.astype("<f4").tobytes(), author) for (author, _), vector in zip(batch, vectors)])
        last = batch[-1][0]
        state.update(encoded=state["encoded"] + len(batch), encoding_seconds=previous_seconds + time.perf_counter() - started, updated_at=timestamp())
        save_state(conn, state)
        LOG.info("vector encoding users=%d/%d seconds=%.1f", state["encoded"], state["users"], state["encoding_seconds"])


@timed
def build(path=VECTOR_STORE, texts_path=TEXT_STORE):
    path.parent.mkdir(parents=True, exist_ok=True)
    protocol = {"model": LUAR, "source": "records joined to stored text vectors by text_sha256", "minimum_usable_texts": 64, "sampled_texts": 64,
                "dimensions": 512, "max_tokens_per_text": 192, "text_features": "768-dimensional mean-pooled LUAR transformer output stored by author_encoder texts",
                "usable": "text_sha256 present in the text vector store, which holds every body that author_encoder.clean leaves nonempty",
                "sampling": "64 distinct usable records per user with the smallest deterministic seeded MD5 priorities; uniform pseudorandom sampling",
                "source_sql_sha256": hashlib.sha256(SOURCE.encode()).hexdigest()}
    protocol = json.loads(json.dumps(protocol))
    with index_lock(path), sqlite3.connect(path, timeout=30) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (author TEXT PRIMARY KEY, usable_texts INTEGER NOT NULL CHECK(usable_texts>=64), sample_ids TEXT NOT NULL, "
                     "sample_sha256 BLOB NOT NULL CHECK(length(sample_sha256)=2048), vector BLOB CHECK(vector IS NULL OR length(vector)=2048))")
        previous = conn.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
        if previous is not None and json.loads(previous[0]) != protocol:
            raise ValueError("Existing vector store uses a different protocol")
        if previous is None:
            conn.execute("INSERT INTO metadata VALUES ('protocol', ?)", [json.dumps(protocol)])
            state = {"status": "sampling", "users": 0, "encoded": 0, "created_at": timestamp()}
            save_state(conn, state)
        else:
            state = json.loads(conn.execute("SELECT value FROM metadata WHERE key='state'").fetchone()[0])
        if state["status"] == "ready":
            LOG.info("vector store already complete users=%d", state["users"])
            return
        texts = TextVectors(texts_path)
        if state["status"] == "sampling":
            source(conn, state, texts)
        encode(conn, state, texts, load_model("cpu"))
        if conn.execute("SELECT count(*) FROM users WHERE vector IS NULL").fetchone()[0]:
            raise ValueError("Vector store is incomplete")
        state.update(status="ready", completed_at=timestamp(), updated_at=timestamp())
        save_state(conn, state)
