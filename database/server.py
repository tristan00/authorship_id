import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg

from . import DATA, DSN, LOG, LOGS, PG, PORT, timed
from .config import INDEX_BUILDS, INDEX_MEMORY, SCAN_WORKERS, SORT_MEMORY, SORT_WORKERS

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    created_utc bigint NOT NULL,
    is_submitter boolean,
    over_18 boolean,
    is_self boolean,
    record_id text NOT NULL,
    subreddit text NOT NULL,
    record_type text NOT NULL,
    author text NOT NULL,
    author_fullname text,
    link_id text NOT NULL,
    parent_id text,
    author_flair_text text,
    link_flair_text text,
    post_hint text,
    crosspost_parent text,
    text_status text NOT NULL,
    text_sha256 bytea NOT NULL
) WITH (autovacuum_enabled = false);
CREATE INDEX IF NOT EXISTS records_created ON records USING brin (created_utc);
CREATE TABLE IF NOT EXISTS bodies (
    text_sha256 bytea PRIMARY KEY,
    text text NOT NULL,
    words integer NOT NULL,
    month text NOT NULL
) WITH (autovacuum_enabled = false);
CREATE TABLE IF NOT EXISTS months (
    month text PRIMARY KEY,
    records bigint NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    extracted_at timestamptz
);
"""
STAGE = """
DROP TABLE IF EXISTS bodies_stage;
CREATE UNLOGGED TABLE bodies_stage (text_sha256 bytea NOT NULL, text text NOT NULL, words integer NOT NULL, month text NOT NULL);
"""
INDEXES = {"records_pkey": "ALTER TABLE records ADD PRIMARY KEY (record_id)", "records_subreddit": "CREATE INDEX records_subreddit ON records (subreddit, created_utc)",
           "records_author": "CREATE INDEX records_author ON records (author, created_utc) INCLUDE (record_type, record_id)",
           "records_link": "CREATE INDEX records_link ON records (link_id)"}
MERGE = """
CREATE TABLE bodies_next WITH (autovacuum_enabled = false) AS
SELECT DISTINCT ON (text_sha256) text_sha256, text, words, month
FROM (SELECT *, false AS staged FROM bodies UNION ALL SELECT *, true FROM bodies_stage) merged ORDER BY text_sha256, staged, month
"""
SWAP = """
DROP TABLE bodies;
ALTER TABLE bodies_next RENAME TO bodies;
ALTER INDEX bodies_next_pkey RENAME TO bodies_pkey;
DROP TABLE bodies_stage;
"""


@timed
def init():
    subprocess.run([PG / "initdb.exe", "-D", DATA, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--locale=C"], check=True)
    start()
    with psycopg.connect(f"host=localhost port={PORT} dbname=postgres user=postgres", autocommit=True) as conn:
        conn.execute("CREATE DATABASE reddit")
    with psycopg.connect(DSN) as conn:
        schema(conn)
    LOG.info("initialized %s", DATA)


@timed
def schema(conn):
    conn.execute(SCHEMA)


@timed
def bodies():
    with psycopg.connect(DSN) as conn:
        conn.execute(f"SET work_mem = '{SORT_MEMORY}'")
        conn.execute(f"SET max_parallel_workers_per_gather = {SORT_WORKERS}")
        conn.execute(f"SET maintenance_work_mem = '{INDEX_MEMORY}'")
        conn.execute("DROP TABLE IF EXISTS bodies_next")
        rows = conn.execute(MERGE).rowcount
        conn.execute("ALTER TABLE bodies_next ADD CONSTRAINT bodies_next_pkey PRIMARY KEY (text_sha256)")
        conn.execute(SWAP)
    LOG.info("bodies rows=%s", rows)


def existing(conn):
    return {name for name, in conn.execute("SELECT relname FROM pg_class WHERE oid IN (SELECT indexrelid FROM pg_index WHERE indrelid = 'records'::regclass)")}


@timed
def drop_indexes(conn):
    conn.execute("SET lock_timeout = '10s'")
    conn.execute("ALTER TABLE records DROP CONSTRAINT IF EXISTS records_pkey")
    for name in INDEXES.keys() & existing(conn):
        conn.execute(f"DROP INDEX {name}")


@timed
def indexes():
    with psycopg.connect(DSN) as conn:
        built = existing(conn)
    with ThreadPoolExecutor(INDEX_BUILDS) as pool:
        list(pool.map(build_index, [statement for name, statement in INDEXES.items() if name not in built]))


@timed
def build_index(statement):
    started = time.perf_counter()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"SET maintenance_work_mem = '{INDEX_MEMORY}'")
        conn.execute(statement)
    LOG.info("built %s in %.0fs", statement, time.perf_counter() - started)


@timed
def finish():
    with psycopg.connect(DSN, autocommit=True) as conn:
        for table in ("records", "bodies"):
            conn.execute(f"ALTER TABLE {table} SET (parallel_workers = {SCAN_WORKERS})")
            conn.execute(f"VACUUM (FREEZE, ANALYZE) {table}")


@timed
def start():
    shutil.copy(Path(__file__).with_name("postgresql.conf"), DATA / "postgresql.conf")
    subprocess.run([PG / "pg_ctl.exe", "-D", DATA, "-l", LOGS / "postgres.log", "-w", "start"], check=True, stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


@timed
def stop():
    subprocess.run([PG / "pg_ctl.exe", "-D", DATA, "-w", "stop", "-m", "fast"], check=True)


if __name__ == "__main__":
    import sys

    from reddit_dumps import setup_logging

    from . import LOGS
    setup_logging(LOGS / "database.log")
    {"start": start, "stop": stop}[sys.argv[1]]()
