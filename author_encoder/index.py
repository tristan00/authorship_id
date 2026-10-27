import hashlib
import json
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import psycopg
import torch

from database import DSN, NOT_PEOPLE
from reddit_dumps import setup_logging
from . import LOG, clean, timed
from .config import BATCH_USERS, LUAR, MAX_LENGTH, PREPARE_WORKERS, SOURCE_WORKERS, VECTOR_STORE
from .lock import index_lock
from .model import load_model, load_tokenizer


SOURCE = r"""
    SELECT author, count(*) AS usable_texts,
           (array_agg(record_id ORDER BY md5('luar-user-vector-64-v1:' || record_id), record_id))[1:64] AS sample_ids
    FROM texts
    WHERE author !~* %(not_people)s
      AND text_status IN ('available', 'title_only')
      AND regexp_replace(normalize(text, NFKC), '^[\s\u001c-\u001f\u0085\u1680\u2028\u2029]*>.*$', '', 'gn') ~ '[^\s\u001c-\u001f\u0085\u1680\u2028\u2029]'
    GROUP BY author HAVING count(*) >= 64
    ORDER BY author
"""

TOKENIZER = None


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save_state(conn, state):
    conn.execute("INSERT INTO metadata VALUES ('state', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [json.dumps(state)])
    conn.commit()


@timed
def source(conn, state):
    conn.execute("DELETE FROM users")
    state.update(status="sampling", users=0, encoded=0, updated_at=timestamp())
    save_state(conn, state)
    started = time.perf_counter()
    with psycopg.connect(DSN) as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        database.execute("SET LOCAL work_mem='256MB'")
        database.execute(f"SET LOCAL max_parallel_workers_per_gather={SOURCE_WORKERS}")
        state["source_snapshot_at"] = str(database.execute("SELECT transaction_timestamp()").fetchone()[0])
        with database.cursor().copy(f"COPY ({SOURCE}) TO STDOUT", {"not_people": NOT_PEOPLE}) as copy:
            copy.set_types(["text", "int8", "text[]"])
            for author, count, ids in copy.rows():
                if len(ids) != 64 or len(set(ids)) != 64:
                    raise ValueError("Each user needs 64 distinct sampled records")
                conn.execute("INSERT INTO users(author, usable_texts, sample_ids) VALUES (?, ?, ?)", [author, count, json.dumps(ids)])
                state["users"] += 1
                if state["users"] % 4096 == 0:
                    state["updated_at"] = timestamp()
                    save_state(conn, state)
                    LOG.info("vector sampling users=%d seconds=%.1f", state["users"], time.perf_counter() - started)
    state.update(status="encoding", sampling_seconds=time.perf_counter() - started, updated_at=timestamp())
    save_state(conn, state)


def start_worker(log):
    global TOKENIZER
    setup_logging(log)
    TOKENIZER = load_tokenizer()


@timed
def prepare(batch):
    samples = [json.loads(row[1]) for row in batch]
    ids = [record for sample in samples for record in sample]
    with psycopg.connect(DSN) as database:
        rows = database.execute("SELECT record_id, author, text FROM texts WHERE record_id=ANY(%s)", [ids]).fetchall()
    records = {record: (author, text) for record, author, text in rows}
    texts = []
    for (author, _), sample in zip(batch, samples):
        for record in sample:
            owner, text = records[record]
            if owner != author:
                raise ValueError("Sampled record belongs to a different author")
            text = clean(text)
            if not text:
                raise ValueError(f"Sampled record has no usable text: {record}")
            texts.append(text)
    tokens = TOKENIZER(texts, padding="max_length", truncation=True, max_length=MAX_LENGTH, return_tensors="np")
    return batch, tokens


@timed
def build(path=VECTOR_STORE, device="cuda"):
    path.parent.mkdir(parents=True, exist_ok=True)
    protocol = {"model": LUAR, "source": "current database", "minimum_usable_texts": 64, "sampled_texts": 64, "dimensions": 512, "max_tokens_per_text": 192, "sampling": "64 distinct records per user with the smallest deterministic seeded MD5 priorities; uniform pseudorandom sampling", "preprocessing": "author_encoder.clean", "source_sql_sha256": hashlib.sha256(SOURCE.encode()).hexdigest()}
    protocol = json.loads(json.dumps(protocol))
    with index_lock(path), sqlite3.connect(path, timeout=30) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (author TEXT PRIMARY KEY, usable_texts INTEGER NOT NULL CHECK(usable_texts>=64), sample_ids TEXT NOT NULL, vector BLOB CHECK(vector IS NULL OR length(vector)=2048))")
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
        if state["status"] == "sampling":
            source(conn, state)
        model = load_model(device)
        pending = conn.execute("SELECT author, sample_ids FROM users WHERE vector IS NULL ORDER BY author").fetchall()
        state["encoded"] = state["users"] - len(pending)
        started = time.perf_counter()
        previous_seconds = state.get("encoding_seconds", 0.)
        with ProcessPoolExecutor(max_workers=PREPARE_WORKERS, initializer=start_worker, initargs=(path.parent / "index.log",)) as pool:
            futures = [pool.submit(prepare, pending[start:start + BATCH_USERS]) for start in range(0, min(PREPARE_WORKERS * BATCH_USERS, len(pending)), BATCH_USERS)]
            for start in range(0, len(pending), BATCH_USERS):
                batch, tokens = futures.pop(0).result()
                next_batch = pending[start + PREPARE_WORKERS * BATCH_USERS:start + (PREPARE_WORKERS + 1) * BATCH_USERS]
                if next_batch:
                    futures.append(pool.submit(prepare, next_batch))
                vectors = model({key: torch.from_numpy(value) for key, value in tokens.items()})
                conn.executemany("UPDATE users SET vector=? WHERE author=?", [(vector.astype("<f4").tobytes(), author) for (author, _), vector in zip(batch, vectors)])
                state.update(encoded=state["encoded"] + len(batch), encoding_seconds=previous_seconds + time.perf_counter() - started, updated_at=timestamp())
                save_state(conn, state)
                LOG.info("vector encoding users=%d/%d seconds=%.1f", state["encoded"], state["users"], state["encoding_seconds"])
        if conn.execute("SELECT count(*) FROM users WHERE vector IS NULL").fetchone()[0]:
            raise ValueError("Vector store is incomplete")
        state.update(status="ready", completed_at=timestamp(), updated_at=timestamp())
        save_state(conn, state)
