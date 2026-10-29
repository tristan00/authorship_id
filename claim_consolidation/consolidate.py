import multiprocessing
import time
import uuid
from collections import Counter, defaultdict
from itertools import groupby
from operator import itemgetter

import psycopg
from psycopg.types.json import Jsonb

from database import DSN, LOGS, NO_AUTHOR, SCAN_WORKERS, vacuum
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
    finished_at timestamptz NOT NULL DEFAULT now()
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
FROM text_claims c JOIN records t USING (text_sha256) WHERE t.author <> ALL(%(no_author)s)
UNION ALL
SELECT DISTINCT t.author, 'flair', t.subreddit || '/' || t.author_flair_text, t.subreddit, f.field, f.value
FROM records t JOIN flair_claims f ON f.subreddit = t.subreddit AND f.flair = t.author_flair_text WHERE t.author <> ALL(%(no_author)s)
"""
CLAIMS = """
SELECT author, source, subreddit, field, value FROM claim_evidence WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author
"""
PARTS_PER_WORKER = 2
PARALLEL = (f"SET max_parallel_workers_per_gather = {SCAN_WORKERS}", "SET parallel_setup_cost = 0", "SET parallel_tuple_cost = 0")


def work(part, parts):
    setup_logging(LOGS / "claim_consolidation.log")
    started = time.perf_counter()
    decided = undecided = 0
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(CLAIMS, {"parts": parts, "part": part})
        with conn.cursor().copy("COPY author_claims FROM STDIN") as copy:
            for author, group in groupby(rows, key=itemgetter(0)):
                evidence = [row[1:] for row in group]
                support = defaultdict(Counter)
                for _, _, field, value in evidence:
                    support[field][value] += 1
                result = rules(evidence)
                for attribute, value in result.items():
                    ranked = support[attribute].most_common()
                    copy.write_row((author, attribute, value, Jsonb([{"value": item, "support": count} for item, count in ranked])))
                decided += len(result)
                undecided += len(support.keys() - result.keys())
    LOG.info("consolidated part %s/%s attributes=%s undecided=%s seconds=%.1f", part + 1, parts, decided, undecided, time.perf_counter() - started)
    return decided


@timed
def evidence(conn):
    for setting in PARALLEL:
        conn.execute(setting)
    rows = conn.execute(f"CREATE TABLE claim_evidence AS {EVIDENCE}", {"no_author": NO_AUTHOR}).rowcount
    conn.execute("CREATE INDEX claim_evidence_source ON claim_evidence (source_key)")
    conn.execute("CREATE INDEX claim_evidence_author ON claim_evidence (author, field)")
    conn.execute(f"ALTER TABLE claim_evidence SET (parallel_workers = {SCAN_WORKERS})")
    conn.commit()
    vacuum("claim_evidence")
    LOG.info("evidence rows=%s", rows)


@timed
def consolidate():
    run_id = str(uuid.uuid4())
    with psycopg.connect(DSN) as conn:
        started = conn.execute("SELECT now()").fetchone()[0]
        loaded = conn.execute("SELECT month, extracted_at FROM months ORDER BY month").fetchall()
        if unextracted := [month for month, extracted in loaded if extracted is None]:
            raise ValueError(f"months {unextracted} have no claim extraction yet")
        months = [month for month, _ in loaded]
        conn.execute(SCHEMA)
        conn.commit()
        evidence(conn)
        parts = WORKERS * PARTS_PER_WORKER
        with multiprocessing.Pool(WORKERS) as pool:
            attributes = sum(pool.starmap(work, [(part, parts) for part in range(parts)]))
        conn.execute("INSERT INTO consolidation (run_id, months, started_at) VALUES (%s, %s, %s)", [run_id, months, started])
        conn.execute("ALTER TABLE author_claims ADD PRIMARY KEY (author, attribute)")
    vacuum("author_claims")
    LOG.info("consolidated run=%s months=%s attributes=%s", run_id, months, attributes)
