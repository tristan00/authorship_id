import time
from functools import cache
from multiprocessing import Pool

import psycopg

from database import DSN, LOGS, vacuum
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import EXTRACT_PARTS, SAMPLE_MAX_BYTES
from .rules import claims, vocabulary, weights

SCHEMA = """
CREATE TABLE IF NOT EXISTS text_claims (text_sha256 bytea NOT NULL, field text NOT NULL, value text NOT NULL, start_char integer NOT NULL, end_char integer NOT NULL);
CREATE INDEX IF NOT EXISTS text_claims_hash ON text_claims (text_sha256);
"""
PARTS = """
CREATE TABLE IF NOT EXISTS text_claims_parts (month text NOT NULL, part integer NOT NULL, texts bigint, long_texts bigint, claims bigint,
    read_seconds double precision, extract_seconds double precision, long_seconds double precision, write_seconds double precision,
    cpu_seconds double precision, finished_at timestamptz, PRIMARY KEY (month, part));
"""
FILL = "INSERT INTO text_claims_parts (month, part) SELECT month, part FROM unnest(%s::text[]) month, generate_series(0, %s - 1) part ON CONFLICT DO NOTHING"
CLEAR = """DELETE FROM text_claims WHERE text_sha256 BETWEEN %(low)s AND %(high)s
    AND text_sha256 IN (SELECT text_sha256 FROM bodies WHERE month = %(month)s AND text_sha256 BETWEEN %(low)s AND %(high)s)"""
TEXTS = "COPY (SELECT text_sha256, text FROM bodies WHERE month = %(month)s AND text_sha256 BETWEEN %(low)s AND %(high)s AND text <> '') TO STDOUT"
STEP = 2**256 // EXTRACT_PARTS


def start():
    setup_logging(LOGS / "claim_extraction.log")
    weights()
    vocabulary()
    connection()


@cache
def connection():
    return psycopg.connect(DSN, autocommit=True)


def work(job):
    month, part = job
    started, cpu = time.perf_counter(), time.process_time()
    rows, texts, long_texts, read, spent, long_spent = [], 0, 0, 0.0, 0.0, 0.0
    selected = {"month": month, "low": (part * STEP).to_bytes(32, "big"), "high": ((part + 1) * STEP - 1).to_bytes(32, "big")}
    conn = connection()
    with conn.transaction():
        conn.execute(CLEAR, selected)
        with conn.cursor().copy(TEXTS, selected) as copy:
            copy.set_types(["bytea", "text"])
            mark = time.perf_counter()
            for text_sha256, text in copy.rows():
                now = time.perf_counter()
                read += now - mark
                rows += [(text_sha256, *claim) for claim in claims(text)]
                mark = time.perf_counter()
                spent += mark - now
                texts += 1
                if len(text) > SAMPLE_MAX_BYTES // 4 and len(text.encode()) > SAMPLE_MAX_BYTES:
                    long_texts += 1
                    long_spent += mark - now
        mark = time.perf_counter()
        with conn.cursor().copy("COPY text_claims (text_sha256, field, value, start_char, end_char) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        written = time.perf_counter() - mark
        cpu = time.process_time() - cpu
        conn.execute("UPDATE text_claims_parts SET texts = %s, long_texts = %s, claims = %s, read_seconds = %s, extract_seconds = %s, long_seconds = %s, "
                     "write_seconds = %s, cpu_seconds = %s, finished_at = now() WHERE month = %s AND part = %s",
                     [texts, long_texts, len(rows), read, spent, long_spent, written, cpu, month, part])
    LOG.info("extracted %s part %s texts=%s long=%s claims=%s read=%.1f extract=%.1f long_extract=%.1f write=%.1f cpu=%.1f seconds=%.1f",
             month, part, texts, long_texts, len(rows), read, spent, long_spent, written, cpu, time.perf_counter() - started)
    return texts, len(rows)


@timed
def pending(reset):
    with psycopg.connect(DSN) as conn:
        conn.execute(SCHEMA)
        if reset:
            conn.execute("TRUNCATE text_claims")
            conn.execute("DROP TABLE IF EXISTS text_claims_parts")
            conn.execute("UPDATE months SET extracted_at = NULL")
        months = [month for month, in conn.execute("SELECT month FROM months WHERE extracted_at IS NULL ORDER BY month")]
        if not months:
            return months, []
        conn.execute(PARTS)
        conn.execute(FILL, [months, EXTRACT_PARTS])
        jobs = conn.execute("SELECT month, part FROM text_claims_parts WHERE finished_at IS NULL ORDER BY month, part").fetchall()
    LOG.info("pending months=%s parts=%s", months, len(jobs))
    return months, jobs


@timed
def run(workers, reset=False):
    months, jobs = pending(reset)
    if not months:
        return
    started, texts, found = time.perf_counter(), 0, 0
    with Pool(workers, initializer=start) as pool:
        for done, (count, claimed) in enumerate(pool.imap_unordered(work, jobs), 1):
            texts, found = texts + count, found + claimed
            if done % workers == 0 or done == len(jobs):
                seconds = time.perf_counter() - started
                LOG.info("progress parts=%s/%s texts=%s claims=%s texts_per_second=%.0f eta_minutes=%.1f", done, len(jobs), texts, found, texts / seconds,
                         seconds / done * (len(jobs) - done) / 60)
    finish(months)


@timed
def finish(months):
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE months SET extracted_at = now() WHERE month = ANY(%s)", [months])
        conn.execute("DROP TABLE text_claims_parts")
        LOG.info("extracted months=%s text_claims rows=%s", months, conn.execute("SELECT count(*) FROM text_claims").fetchone()[0])
    vacuum("text_claims")
