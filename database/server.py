import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg

from . import DATA, LOG, LOGS, PG, PORT, timed

SCHEMA = """
CREATE TABLE IF NOT EXISTS texts (
    record_id text NOT NULL,
    subreddit text NOT NULL,
    record_type text NOT NULL,
    author text NOT NULL,
    author_fullname text,
    created_utc bigint NOT NULL,
    link_id text NOT NULL,
    parent_id text,
    is_submitter boolean,
    author_flair_text text,
    link_flair_text text,
    over_18 boolean,
    is_self boolean,
    post_hint text,
    crosspost_parent text,
    text_status text NOT NULL,
    text_sha256 text NOT NULL,
    text text NOT NULL
) WITH (autovacuum_enabled = false);
CREATE TABLE IF NOT EXISTS months (
    month text PRIMARY KEY,
    loaded_at timestamptz NOT NULL DEFAULT now()
);
"""
INDEXES = ("ALTER TABLE texts ADD PRIMARY KEY (record_id)", "CREATE INDEX texts_subreddit ON texts (subreddit, created_utc)",
           "CREATE INDEX texts_author ON texts (author)", "CREATE INDEX texts_link ON texts (link_id)")


@timed
def init():
    subprocess.run([PG / "initdb.exe", "-D", DATA, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--locale=C"], check=True)
    start()
    with psycopg.connect(f"host=localhost port={PORT} dbname=postgres user=postgres", autocommit=True) as conn:
        conn.execute("CREATE DATABASE reddit")
    from . import DSN
    with psycopg.connect(DSN) as conn:
        schema(conn)
    LOG.info("initialized %s", DATA)


@timed
def schema(conn):
    conn.execute(SCHEMA)


@timed
def indexes():
    from . import DSN
    with psycopg.connect(DSN) as conn:
        existing = conn.execute("SELECT count(*) FROM pg_indexes WHERE tablename = 'texts'").fetchone()[0]
    if existing:
        return
    with ThreadPoolExecutor(len(INDEXES)) as pool:
        list(pool.map(build_index, INDEXES))


@timed
def build_index(statement):
    from . import DSN
    started = time.perf_counter()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(statement)
    LOG.info("built %s in %.0fs", statement, time.perf_counter() - started)


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
