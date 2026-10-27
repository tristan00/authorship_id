import multiprocessing
import time
import uuid
from collections import Counter
from itertools import groupby

import psycopg
from psycopg.types.json import Jsonb

from database import DSN, LOGS, NOT_PEOPLE, SCAN_WORKERS
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import WORKERS

SCHEMA = """
DROP TABLE IF EXISTS claim_evidence;
CREATE TABLE claim_evidence (
    author text NOT NULL,
    source text NOT NULL,
    source_key text NOT NULL,
    field text NOT NULL,
    value text NOT NULL
);
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
TEXT_EVIDENCE = """
INSERT INTO claim_evidence SELECT t.author, 'text', c.record_id, c.field, c.value
FROM text_claims c JOIN texts t USING (record_id) WHERE t.author !~* %s
"""
FLAIR_EVIDENCE = """
INSERT INTO claim_evidence SELECT DISTINCT t.author, 'flair', t.author_flair_text, f.field, f.value
FROM texts t JOIN flair_claims f ON f.flair = t.author_flair_text WHERE t.author !~* %s
"""
CLAIMS = """
SELECT author, field, value FROM claim_evidence WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author, field
"""
PARTS_PER_WORKER = 2


def decide(values):
    ranked = Counter(values).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0], Jsonb([{"value": value, "support": count} for value, count in ranked])


def work(part, parts):
    setup_logging(LOGS / "claim_consolidation.log")
    started = time.perf_counter()
    decided = tied = 0
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(CLAIMS, {"parts": parts, "part": part})
        with conn.cursor().copy("COPY author_claims FROM STDIN") as copy:
            for (author, attribute), group in groupby(rows, key=lambda row: row[:2]):
                result = decide([row[2] for row in group])
                if result is None:
                    tied += 1
                    continue
                copy.write_row((author, attribute, *result))
                decided += 1
    LOG.info("consolidated part %s/%s attributes=%s tied=%s seconds=%.1f", part + 1, parts, decided, tied, time.perf_counter() - started)
    return decided


@timed
def evidence(conn):
    texts = conn.execute(TEXT_EVIDENCE, [NOT_PEOPLE]).rowcount
    flairs = conn.execute(FLAIR_EVIDENCE, [NOT_PEOPLE]).rowcount
    conn.execute("CREATE INDEX claim_evidence_source ON claim_evidence (source_key)")
    conn.execute("CREATE INDEX claim_evidence_author ON claim_evidence (author, field)")
    conn.execute(f"ALTER TABLE claim_evidence SET (parallel_workers = {SCAN_WORKERS})")
    conn.execute("ANALYZE claim_evidence")
    conn.commit()
    LOG.info("evidence text=%s flair=%s", texts, flairs)


@timed
def consolidate():
    run_id = str(uuid.uuid4())
    with psycopg.connect(DSN) as conn:
        started = conn.execute("SELECT now()").fetchone()[0]
        months = [month for month, in conn.execute("SELECT month FROM months ORDER BY 1")]
        conn.execute(SCHEMA)
        conn.commit()
        evidence(conn)
        parts = WORKERS * PARTS_PER_WORKER
        with multiprocessing.Pool(WORKERS) as pool:
            attributes = sum(pool.starmap(work, [(part, parts) for part in range(parts)]))
        conn.execute("INSERT INTO consolidation (run_id, months, started_at) VALUES (%s, %s, %s)", [run_id, months, started])
        conn.execute("ALTER TABLE author_claims ADD PRIMARY KEY (author, attribute)")
        conn.execute("ANALYZE author_claims")
    LOG.info("consolidated run=%s months=%s attributes=%s", run_id, months, attributes)
