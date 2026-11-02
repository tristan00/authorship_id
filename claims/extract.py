import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from itertools import islice
from queue import Queue
from threading import Thread

import psycopg

from database import DSN, vacuum

from . import LOG, timed
from .config import EXTRACT_READERS, EXTRACTOR, PART_PAGES
from .schema import stored_field
from .extractor import load_extractor, predict, splitter, windows

SCHEMA = """
CREATE TABLE IF NOT EXISTS text_claims (text_sha256 bytea NOT NULL, field text NOT NULL, value text NOT NULL, start_char integer NOT NULL, end_char integer NOT NULL, probability real NOT NULL);
"""
PARTS = """
CREATE TABLE IF NOT EXISTS text_claims_parts (partition text NOT NULL, first_page bigint NOT NULL, texts bigint, claims bigint, read_seconds double precision, gpu_seconds double precision, finished_at timestamptz, PRIMARY KEY (partition, first_page));
"""
FILL = "INSERT INTO text_claims_parts (partition, first_page) SELECT %s, generate_series(0, %s, %s) ON CONFLICT DO NOTHING"
HOLDER = "SELECT tableoid::regclass::text FROM bodies WHERE month = %s LIMIT 1"
TEXTS = "COPY (SELECT text_sha256, text FROM {partition} WHERE ctid >= '({low},0)'::tid AND ctid < '({high},0)'::tid AND month = ANY(%s) AND text <> '') TO STDOUT"
INDEX = "CREATE INDEX IF NOT EXISTS text_claims_hash ON text_claims (text_sha256)"


@lru_cache(maxsize=1)
def reader_tokenizer(name):
    return splitter(name)


def prepare(job):
    partition, first, months, encoder = job
    started = time.perf_counter()
    digests, texts = [], []
    with psycopg.connect(DSN) as conn, conn.cursor().copy(TEXTS.format(partition=partition, low=first, high=first + PART_PAGES), [months]) as copy:
        copy.set_types(["bytea", "text"])
        for digest, text in copy.rows():
            digests.append(bytes(digest))
            texts.append(text)
    tokens = windows(reader_tokenizer(encoder), texts) if texts else None
    return partition, first, digests, texts, tokens, time.perf_counter() - started


class Writer(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.items, self.error, self.conn = Queue(maxsize=8), None, psycopg.connect(DSN, autocommit=True)

    def run(self):
        while (item := self.items.get()) is not None:
            if self.error is None:
                try:
                    self.write(*item)
                except BaseException as error:
                    self.error = error

    def write(self, partition, first, rows, count, read, gpu):
        with self.conn.transaction():
            with self.conn.cursor().copy("COPY text_claims (text_sha256, field, value, start_char, end_char, probability) FROM STDIN") as copy:
                for row in rows:
                    copy.write_row(row)
            self.conn.execute("UPDATE text_claims_parts SET texts = %s, claims = %s, read_seconds = %s, gpu_seconds = %s, finished_at = now() WHERE partition = %s AND first_page = %s", [count, len(rows), read, gpu, partition, first])

    def put(self, *item):
        if self.error is not None:
            raise self.error
        self.items.put(item)

    def close(self):
        self.items.put(None)
        self.join()
        if self.error is not None:
            raise self.error


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
        conn.execute("DROP INDEX IF EXISTS text_claims_hash")
        conn.execute(PARTS)
        partitions = sorted({conn.execute(HOLDER, [month]).fetchone()[0] for month in months})
        for name in partitions:
            pages = conn.execute("SELECT pg_relation_size(%s) / current_setting('block_size')::bigint", [name]).fetchone()[0]
            conn.execute(FILL, [name, pages, PART_PAGES])
        jobs = conn.execute("SELECT partition, first_page FROM text_claims_parts WHERE finished_at IS NULL ORDER BY partition, first_page").fetchall()
    LOG.info("pending months=%s partitions=%s parts=%s", months, partitions, len(jobs))
    return months, jobs


def rows_of(digests, found):
    for owner, facts in found.items():
        for (attribute, value), (score, low, high) in facts.items():
            yield digests[owner], stored_field(attribute), value, low, high, round(score, 4)


@timed
def run(reset=False):
    months, jobs = pending(reset)
    if not months:
        return
    model, pad = load_extractor(EXTRACTOR)
    encoder = model.encoder.config.name_or_path
    writer = Writer()
    writer.start()
    started, texts_done, found_total, gpu_total, read_total = time.perf_counter(), 0, 0, 0., 0.
    with ProcessPoolExecutor(EXTRACT_READERS) as pool:
        upcoming = ((partition, first, months, encoder) for partition, first in jobs)
        waiting = deque(pool.submit(prepare, job) for job in islice(upcoming, 2 * EXTRACT_READERS))
        done = 0
        while waiting:
            partition, first, digests, texts, tokens, read = waiting.popleft().result()
            if (following := next(upcoming, None)) is not None:
                waiting.append(pool.submit(prepare, following))
            tick = time.perf_counter()
            found = predict(model, pad, *tokens, texts) if texts else {}
            gpu = time.perf_counter() - tick
            rows = list(rows_of(digests, found))
            writer.put(partition, first, rows, len(texts), read, gpu)
            texts_done, found_total, done, gpu_total, read_total = texts_done + len(texts), found_total + len(rows), done + 1, gpu_total + gpu, read_total + read
            if done % 32 == 0 or done == len(jobs):
                seconds = time.perf_counter() - started
                LOG.info("extract parts=%d/%d texts=%d claims=%d texts_per_second=%.0f gpu_share=%.2f read_seconds_per_part=%.1f eta_hours=%.1f", done, len(jobs), texts_done, found_total, texts_done / seconds, gpu_total / seconds, read_total / done, seconds / done * (len(jobs) - done) / 3600)
    writer.close()
    finish(months)


@timed
def finish(months):
    with psycopg.connect(DSN) as conn:
        conn.execute("SET maintenance_work_mem = '8GB'")
        conn.execute(INDEX)
        conn.execute("UPDATE months SET extracted_at = now() WHERE month = ANY(%s)", [months])
        conn.execute("DROP TABLE text_claims_parts")
        LOG.info("extracted months=%s text_claims rows=%s", months, conn.execute("SELECT count(*) FROM text_claims").fetchone()[0])
    vacuum("text_claims")
