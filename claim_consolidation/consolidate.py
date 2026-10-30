import multiprocessing
import time
import uuid
from collections import Counter, defaultdict
from itertools import groupby
from operator import itemgetter

import psycopg
from psycopg.types.json import Jsonb

from database import DSN, LOGS, NO_AUTHOR, SCAN_WORKERS, vacuum, within
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import WORKERS
from .rules import consolidate as rules

SCHEMA = """
DROP TABLE IF EXISTS claim_evidence;
DROP TABLE IF EXISTS consolidation;
CREATE TABLE consolidation (
    run_id uuid PRIMARY KEY,
    months text[] NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz NOT NULL DEFAULT now(),
    base uuid,
    added text[]
);
DROP TABLE IF EXISTS author_claims;
CREATE TABLE author_claims (
    author text NOT NULL,
    attribute text NOT NULL,
    value text NOT NULL,
    candidates jsonb NOT NULL
);
"""
EVIDENCE = """
SELECT t.author, 'text' AS source, t.record_id AS source_key, t.subreddit, c.field, c.value
FROM text_claims c JOIN records t USING (text_sha256) WHERE t.author <> ALL(%(no_author)s) AND {months}
UNION ALL
SELECT DISTINCT t.author, 'flair', t.subreddit || '/' || t.author_flair_text, t.subreddit, f.field, f.value
FROM records t JOIN flair_claims f ON f.subreddit = t.subreddit AND f.flair = t.author_flair_text WHERE t.author <> ALL(%(no_author)s) AND {months}
"""
ADDED = """
ANALYZE claim_evidence_added;
DELETE FROM claim_evidence_added n WHERE source = 'flair' AND EXISTS (SELECT FROM claim_evidence e
    WHERE e.author = n.author AND e.field = n.field AND e.source = 'flair' AND e.source_key = n.source_key AND e.value = n.value);
INSERT INTO claim_evidence SELECT * FROM claim_evidence_added;
CREATE UNLOGGED TABLE claim_authors AS SELECT DISTINCT author FROM claim_evidence_added;
ANALYZE claim_authors;
DELETE FROM author_claims WHERE author IN (SELECT author FROM claim_authors);
"""
CLAIMS = {False: "SELECT author, source, subreddit, field, value FROM claim_evidence WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author",
          True: """SELECT author, e.source, e.subreddit, e.field, e.value FROM claim_authors a JOIN claim_evidence e USING (author)
                   WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author"""}
PARTS_PER_WORKER = 2
PARALLEL = (f"SET max_parallel_workers_per_gather = {SCAN_WORKERS}", "SET parallel_setup_cost = 0", "SET parallel_tuple_cost = 0")


def work(part, parts, touched):
    setup_logging(LOGS / "claim_consolidation.log")
    started = time.perf_counter()
    decided = undecided = 0
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(CLAIMS[touched], {"parts": parts, "part": part})
        with conn.cursor().copy("COPY author_claims FROM STDIN") as copy:
            for author, group in groupby(rows, key=itemgetter(0)):
                evidence = [row[1:] for row in group]
                support = defaultdict(Counter)
                for _, _, field, value in evidence:
                    support[field][value] += 1
                result = rules(evidence)
                for attribute, value in result.items():
                    ranked = sorted(support[attribute].items(), key=lambda item: (-item[1], item[0]))
                    copy.write_row((author, attribute, value, Jsonb([{"value": item, "support": count} for item, count in ranked])))
                decided += len(result)
                undecided += len(support.keys() - result.keys())
    LOG.info("consolidated part %s/%s attributes=%s undecided=%s seconds=%.1f", part + 1, parts, decided, undecided, time.perf_counter() - started)
    return decided


@timed
def evidence(conn):
    for setting in PARALLEL:
        conn.execute(setting)
    rows = conn.execute(f"CREATE TABLE claim_evidence AS {EVIDENCE.format(months='true')}", {"no_author": NO_AUTHOR}).rowcount
    conn.execute("CREATE INDEX claim_evidence_source ON claim_evidence (source_key)")
    conn.execute("CREATE INDEX claim_evidence_author ON claim_evidence (author, field)")
    conn.execute(f"ALTER TABLE claim_evidence SET (parallel_workers = {SCAN_WORKERS})")
    conn.commit()
    LOG.info("evidence rows=%s", rows)


@timed
def append(conn, added):
    for setting in PARALLEL:
        conn.execute(setting)
    conn.execute("DELETE FROM consolidation")
    conn.execute("DROP TABLE IF EXISTS claim_evidence_added, claim_authors")
    query = EVIDENCE.format(months=within(added, "t.created_utc"))
    rows = conn.execute(f"CREATE UNLOGGED TABLE claim_evidence_added AS {query}", {"no_author": NO_AUTHOR}).rowcount
    conn.execute(ADDED)
    authors = conn.execute("SELECT count(*) FROM claim_authors").fetchone()[0]
    conn.commit()
    LOG.info("evidence added months=%s rows=%s authors=%s", added, rows, authors)


def base(conn, loaded):
    if conn.execute("SELECT to_regclass('consolidation')").fetchone()[0] is None:
        return None
    previous = conn.execute("SELECT run_id, months, started_at FROM consolidation").fetchone()
    if previous is None:
        return None
    run_id, covered, started = previous
    stamps = {month: max(loaded_at, extracted_at) for month, loaded_at, extracted_at in loaded}
    added = sorted(stamps.keys() - set(covered))
    if not added or not set(covered) <= stamps.keys() or any(stamps[month] >= started for month in covered):
        return None
    return run_id, added


@timed
def consolidate():
    run_id = str(uuid.uuid4())
    with psycopg.connect(DSN) as conn:
        started = conn.execute("SELECT now()").fetchone()[0]
        loaded = conn.execute("SELECT month, loaded_at, extracted_at FROM months ORDER BY month").fetchall()
        if unextracted := [month for month, _, extracted in loaded if extracted is None]:
            raise ValueError(f"months {unextracted} have no claim extraction yet")
        months = [month for month, _, _ in loaded]
        previous, added = base(conn, loaded) or (None, None)
        LOG.info("consolidation months=%s base=%s added=%s", months, previous, added)
        if previous is None:
            conn.execute(SCHEMA)
            conn.commit()
            evidence(conn)
        else:
            append(conn, added)
        parts = WORKERS * PARTS_PER_WORKER
        with multiprocessing.Pool(WORKERS) as pool:
            attributes = sum(pool.starmap(work, [(part, parts, previous is not None) for part in range(parts)]))
        conn.execute("INSERT INTO consolidation (run_id, months, started_at, base, added) VALUES (%s, %s, %s, %s, %s)", [run_id, months, started, previous, added])
        if previous is None:
            conn.execute("ALTER TABLE author_claims ADD PRIMARY KEY (author, attribute)")
        else:
            conn.execute("DROP TABLE claim_evidence_added, claim_authors")
    vacuum("claim_evidence", "author_claims")
    LOG.info("consolidated run=%s months=%s attributes=%s", run_id, months, attributes)
