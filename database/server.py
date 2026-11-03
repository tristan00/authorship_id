import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg import sql

from . import DATA, DSN, LOG, LOGS, NO_AUTHOR, PG, PORT, bounds, timed
from .config import COUNT_WORKERS, INDEX_BUILDS, INDEX_MEMORY, SCAN_WORKERS, SORT_MEMORY, SORT_WORKERS

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
) PARTITION BY RANGE (created_utc);
CREATE TABLE IF NOT EXISTS bodies (
    text_sha256 bytea NOT NULL,
    text text NOT NULL,
    words integer NOT NULL,
    month text NOT NULL
) PARTITION BY LIST (month);
CREATE TABLE IF NOT EXISTS months (
    month text PRIMARY KEY,
    records bigint NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    extracted_at timestamptz
);
CREATE TABLE IF NOT EXISTS empty_bodies (
    month text NOT NULL,
    text_sha256 bytea NOT NULL
);
"""
STORAGE = f"autovacuum_enabled = false, parallel_workers = {SCAN_WORKERS}"
PARTITION = """
DROP TABLE IF EXISTS records_{name}, bodies_{name}, bodies_stage;
CREATE TABLE records_{name} (LIKE records, CHECK (created_utc >= {start} AND created_utc < {end})) WITH ({storage});
CREATE UNLOGGED TABLE bodies_stage (text_sha256 bytea NOT NULL, text text NOT NULL, words integer NOT NULL, month text NOT NULL);
"""
INDEXES = ("ALTER TABLE records_{name} ADD PRIMARY KEY (record_id)", "CREATE INDEX records_{name}_subreddit ON records_{name} (subreddit, created_utc)",
           "CREATE INDEX records_{name}_author ON records_{name} (author, created_utc) INCLUDE (record_type, record_id)")
NEW_BODIES = """
COPY (SELECT DISTINCT ON (text_sha256) text_sha256, text, words, month FROM bodies_stage s
      WHERE NOT EXISTS (SELECT FROM bodies b WHERE b.text_sha256 = s.text_sha256) ORDER BY text_sha256) TO STDOUT (FORMAT binary)
"""
ATTACH = """
SET lock_timeout = '10s';
ALTER TABLE records ATTACH PARTITION records_{name} FOR VALUES FROM ({start}) TO ({end});
ALTER TABLE bodies ATTACH PARTITION bodies_{name} FOR VALUES IN ('{month}');
DROP TABLE bodies_stage;
"""
COUNTS = {
    "author": sql.SQL("""SELECT author, count(*) AS texts, count(*) FILTER (WHERE record_type = 'post') AS posts, min(created_utc) AS first_seen,
        max(created_utc) AS last_seen FROM records WHERE author <> ALL({}) GROUP BY author""").format(sql.Literal(NO_AUTHOR)),
    "subreddit": sql.SQL("SELECT subreddit, count(*) AS texts, min(created_utc) AS first_seen, max(created_utc) AS last_seen FROM records GROUP BY subreddit"),
}
SWAP = """
DROP TABLE IF EXISTS {key}_counts;
ALTER TABLE {key}_counts_stage RENAME TO {key}_counts;
ALTER INDEX {key}_counts_stage_pkey RENAME TO {key}_counts_pkey;
ALTER INDEX {key}_counts_stage_texts RENAME TO {key}_counts_texts;
"""


def partition(month):
    start, end = bounds(month)
    return {"name": month.replace("-", "_"), "month": month, "start": start, "end": end, "storage": STORAGE}


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


def reloadable(conn, month):
    found = conn.execute("SELECT tableoid::regclass::text FROM records WHERE created_utc >= %s AND created_utc < %s LIMIT 1", bounds(month)).fetchone()
    if found and found[0] != "records_" + partition(month)["name"]:
        raise ValueError(f"{month} lies in partition {found[0]} with other months and cannot be reloaded alone")


@timed
def create(month):
    with psycopg.connect(DSN) as conn:
        conn.execute("SET lock_timeout = '10s'")
        conn.execute(PARTITION.format(**partition(month)))


@timed
def bodies(month):
    names = partition(month)
    with psycopg.connect(DSN) as source, psycopg.connect(DSN) as target, target.cursor() as cursor:
        source.execute(f"SET work_mem = '{SORT_MEMORY}'")
        source.execute(f"SET max_parallel_workers_per_gather = {SORT_WORKERS}")
        source.execute("SET enable_hashjoin = off")
        source.execute("SET enable_nestloop = off")
        target.execute(f"SET maintenance_work_mem = '{INDEX_MEMORY}'")
        cursor.execute("CREATE TABLE bodies_{name} (LIKE bodies, CHECK (month = '{month}')) WITH ({storage})".format(**names))
        with source.cursor().copy(NEW_BODIES) as out, cursor.copy(f"COPY bodies_{names['name']} FROM STDIN (FORMAT binary, FREEZE)") as into:
            for block in out:
                into.write(block)
        rows = cursor.rowcount
        cursor.execute(f"ALTER TABLE bodies_{names['name']} ADD PRIMARY KEY (text_sha256)")
    analyze(f"bodies_{names['name']}")
    LOG.info("%s new bodies rows=%s", month, rows)


@timed
def records(month):
    name = partition(month)["name"]
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"VACUUM (FREEZE, ANALYZE) records_{name}")
    with ThreadPoolExecutor(INDEX_BUILDS) as pool:
        list(pool.map(build_index, [statement.format(name=name) for statement in INDEXES]))


@timed
def analyze(table):
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"ANALYZE {table}")


@timed
def build_index(statement):
    started = time.perf_counter()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"SET maintenance_work_mem = '{INDEX_MEMORY}'")
        conn.execute(statement)
    LOG.info("built %s in %.0fs", statement, time.perf_counter() - started)


@timed
def finish(month):
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda step: step(month), (bodies, records)))
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(ATTACH.format(**partition(month)))
        conn.execute("ANALYZE ONLY records, ONLY bodies")


@timed
def count(key):
    stage = f"{key}_counts_stage"
    with psycopg.connect(DSN, autocommit=True) as conn:
        for setting in (f"max_parallel_workers_per_gather = {COUNT_WORKERS}", f"work_mem = '{SORT_MEMORY}'", "enable_partitionwise_aggregate = on", "enable_seqscan = off"):
            conn.execute(f"SET {setting}")
        conn.execute(f"DROP TABLE IF EXISTS {stage}")
        rows = conn.execute(sql.SQL("CREATE TABLE {} AS ").format(sql.Identifier(stage)) + COUNTS[key]).rowcount
        conn.execute(f"ALTER TABLE {stage} ADD CONSTRAINT {stage}_pkey PRIMARY KEY ({key})")
        conn.execute(f"CREATE INDEX {stage}_texts ON {stage} (texts DESC, {key})")
        conn.execute(f"VACUUM (ANALYZE) {stage}")
        with conn.transaction():
            conn.execute("SET LOCAL lock_timeout = '10s'")
            conn.execute(SWAP.format(key=key))
    LOG.info("%s counts rows=%s", key, rows)


@timed
def counts():
    with ThreadPoolExecutor(len(COUNTS)) as pool:
        list(pool.map(count, COUNTS))
    with psycopg.connect(DSN) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS counted (months text[] NOT NULL)")
        conn.execute("DELETE FROM counted")
        conn.execute("INSERT INTO counted SELECT array_agg(month ORDER BY month) FROM months")


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
