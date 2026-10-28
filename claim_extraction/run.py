import time
from functools import cache
from multiprocessing import Pool

import psycopg

from database import DSN, LOGS, bounds
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import EXTRACT_PAGES, READABLE, SAMPLE_MAX_BYTES
from .rules import claims, vocabulary, weights

SCHEMA = """
CREATE UNLOGGED TABLE text_claims_stage (record_id text NOT NULL, field text NOT NULL, value text NOT NULL, start_char integer NOT NULL, end_char integer NOT NULL);
CREATE TABLE text_claims_parts (part integer PRIMARY KEY, first_page bigint NOT NULL, last_page bigint NOT NULL, texts bigint, long_texts bigint, claims bigint,
    read_seconds double precision, extract_seconds double precision, long_seconds double precision, write_seconds double precision,
    cpu_seconds double precision, finished_at timestamptz);
"""
TEXTS = ("COPY (SELECT record_id, text FROM texts WHERE ctid >= '({},0)'::tid AND ctid < '({},0)'::tid "
         "AND text_status = ANY(%s) AND text IS NOT NULL AND created_utc >= %s AND created_utc < %s) TO STDOUT")
FINISH = """
ALTER TABLE text_claims_stage SET LOGGED;
CREATE INDEX text_claims_record ON text_claims_stage (record_id);
DROP TABLE IF EXISTS text_claims;
ALTER TABLE text_claims_stage RENAME TO text_claims;
ANALYZE text_claims;
DROP TABLE text_claims_parts;
"""


def start():
    setup_logging(LOGS / "claim_extraction.log")
    weights()
    vocabulary()
    connection()


@cache
def connection():
    return psycopg.connect(DSN, autocommit=True)


def work(job):
    part, first, last, low, high = job
    started, cpu = time.perf_counter(), time.process_time()
    rows, texts, long_texts, read, spent, long_spent = [], 0, 0, 0.0, 0.0, 0.0
    conn = connection()
    with conn.transaction():
        with conn.cursor().copy(TEXTS.format(first, last), [list(READABLE), low, high]) as copy:
            mark = time.perf_counter()
            for record_id, text in copy.rows():
                now = time.perf_counter()
                read += now - mark
                rows += [(record_id, *claim) for claim in claims(text)]
                mark = time.perf_counter()
                spent += mark - now
                texts += 1
                if len(text) > SAMPLE_MAX_BYTES // 4 and len(text.encode()) > SAMPLE_MAX_BYTES:
                    long_texts += 1
                    long_spent += mark - now
        mark = time.perf_counter()
        with conn.cursor().copy("COPY text_claims_stage (record_id, field, value, start_char, end_char) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        written = time.perf_counter() - mark
        cpu = time.process_time() - cpu
        conn.execute("UPDATE text_claims_parts SET texts = %s, long_texts = %s, claims = %s, read_seconds = %s, extract_seconds = %s, long_seconds = %s, "
                     "write_seconds = %s, cpu_seconds = %s, finished_at = now() WHERE part = %s",
                     [texts, long_texts, len(rows), read, spent, long_spent, written, cpu, part])
    LOG.info("extracted part %s pages=%s-%s texts=%s long=%s claims=%s read=%.1f extract=%.1f long_extract=%.1f write=%.1f cpu=%.1f seconds=%.1f",
             part, first, last, texts, long_texts, len(rows), read, spent, long_spent, written, cpu, time.perf_counter() - started)
    return texts, len(rows)


@timed
def pending(month, pages, reset):
    low, high = bounds(month)
    with psycopg.connect(DSN) as conn:
        if reset:
            conn.execute("DROP TABLE IF EXISTS text_claims_stage, text_claims_parts")
        first, last = pages or conn.execute("SELECT 0, pg_relation_size('texts') / current_setting('block_size')::int").fetchone()
        if conn.execute("SELECT to_regclass('text_claims_parts')").fetchone()[0] is None:
            conn.execute(SCHEMA)
            with conn.cursor().copy("COPY text_claims_parts (part, first_page, last_page) FROM STDIN") as copy:
                for part, page in enumerate(range(first, last, EXTRACT_PAGES)):
                    copy.write_row((part, page, min(page + EXTRACT_PAGES, last)))
        lowest, highest, finished, claimed = conn.execute("SELECT min(first_page), max(last_page), count(finished_at), coalesce(sum(claims), 0) FROM text_claims_parts").fetchone()
        if (lowest, highest) != (first, last):
            raise ValueError(f"text_claims_parts covers pages {lowest}-{highest}, not {first}-{last}; rerun with --reset")
        if claimed and conn.execute("SELECT NOT EXISTS (SELECT 1 FROM text_claims_stage)").fetchone()[0]:
            raise ValueError(f"text_claims_stage lost the rows of {finished} finished parts after a server restart; rerun with --reset")
        jobs = [(part, start, end, low, high) for part, start, end in conn.execute("SELECT part, first_page, last_page FROM text_claims_parts WHERE finished_at IS NULL ORDER BY part")]
    LOG.info("pending month=%s pages=%s-%s parts=%s finished=%s", month, first, last, len(jobs), finished)
    return jobs


@timed
def run(month, workers, pages, reset):
    jobs = pending(month, pages, reset)
    started, texts, found = time.perf_counter(), 0, 0
    with Pool(workers, initializer=start) as pool:
        for done, (count, claimed) in enumerate(pool.imap_unordered(work, jobs), 1):
            texts, found = texts + count, found + claimed
            if done % workers == 0 or done == len(jobs):
                seconds = time.perf_counter() - started
                LOG.info("progress parts=%s/%s texts=%s claims=%s texts_per_second=%.0f eta_minutes=%.1f", done, len(jobs), texts, found, texts / seconds,
                         seconds / done * (len(jobs) - done) / 60)
    if pages is None:
        finish()


@timed
def finish():
    with psycopg.connect(DSN) as conn:
        conn.execute(FINISH)
        LOG.info("text_claims rows=%s", conn.execute("SELECT count(*) FROM text_claims").fetchone()[0])
