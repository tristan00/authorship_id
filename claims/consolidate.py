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
from .config import EVIDENCE_MEMORY, PARTS_PER_WORKER, WORKERS
from .flairs import blocked_scopes, gate, near
from .rules import audit, needs
from .rules import consolidate as rules

SCHEMA = """
DROP TABLE IF EXISTS claim_evidence;
DROP TABLE IF EXISTS consolidation;
CREATE TABLE consolidation (run_id uuid PRIMARY KEY, months text[] NOT NULL, started_at timestamptz NOT NULL, finished_at timestamptz NOT NULL DEFAULT now(), base uuid, added text[]);
"""
CLAIMS = """
DROP TABLE IF EXISTS author_claims;
CREATE TABLE author_claims (author text NOT NULL, attribute text NOT NULL, value text NOT NULL, support real NOT NULL, share real NOT NULL, candidates jsonb NOT NULL);
"""
EVIDENCE = """
SELECT t.author, 'text' AS source, t.record_id AS source_key, t.subreddit, c.field, c.value, c.probability, c.text_sha256
FROM text_claims c JOIN records t USING (text_sha256) WHERE t.author <> ALL(%(no_author)s) AND {months}
UNION ALL
SELECT DISTINCT t.author, 'flair', t.subreddit || '/' || t.author_flair_text, t.subreddit, f.field, f.value, 1::real, NULL::bytea
FROM records t JOIN flair_claims f ON f.subreddit = t.subreddit AND f.flair = t.author_flair_text WHERE t.author <> ALL(%(no_author)s) AND {months}
"""
ADDED = """
ANALYZE claim_evidence_added;
DELETE FROM claim_evidence_added n WHERE source = 'flair' AND EXISTS (SELECT FROM claim_evidence e
    WHERE e.author = n.author AND e.field = n.field AND e.source = 'flair' AND e.source_key = n.source_key AND e.value = n.value);
INSERT INTO claim_evidence SELECT * FROM claim_evidence_added;
SET LOCAL enable_hashagg = off;
CREATE UNLOGGED TABLE claim_authors AS SELECT DISTINCT author FROM claim_evidence_added;
ANALYZE claim_authors;
DELETE FROM author_claims WHERE author IN (SELECT author FROM claim_authors);
"""
READ = {False: "SELECT author, source, source_key, subreddit, field, value, probability, text_sha256 FROM claim_evidence WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author",
        True: """SELECT author, e.source, e.source_key, e.subreddit, e.field, e.value, e.probability, e.text_sha256 FROM claim_authors a JOIN claim_evidence e USING (author)
                 WHERE abs(hashtext(author)) %% %(parts)s = %(part)s ORDER BY author"""}
PARALLEL = (f"SET max_parallel_workers_per_gather = {SCAN_WORKERS}", "SET parallel_setup_cost = 0", "SET parallel_tuple_cost = 0", f"SET work_mem = '{EVIDENCE_MEMORY}'")


def inspect(part, parts, required):
    setup_logging(LOGS / "claims.log")
    stats, base = {}, defaultdict(Counter)
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(READ[False], {"parts": parts, "part": part})
        for _, group in groupby(rows, key=itemgetter(0)):
            decided, pairs = audit([row[1:] for row in group], required)
            for field, value in decided.items():
                base[field][value] += 1
            for subreddit, flair, field, value, written in pairs:
                entry = stats.setdefault((subreddit, flair, field, value), [0, 0])
                entry[0] += 1
                entry[1] += near(field, value, written)
    return stats, {field: dict(counted) for field, counted in base.items()}


def work(part, parts, touched, required, blocked):
    setup_logging(LOGS / "claims.log")
    started = time.perf_counter()
    decided = authors = 0
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(READ[touched], {"parts": parts, "part": part})
        with conn.cursor().copy("COPY author_claims FROM STDIN") as copy:
            for author, group in groupby(rows, key=itemgetter(0)):
                authors += 1
                for attribute, (value, support, share, candidates) in rules([row[1:] for row in group], required, blocked).items():
                    ranked = sorted(candidates.items(), key=lambda item: (-item[1], item[0]))
                    copy.write_row((author, attribute, value, support, share, Jsonb([{"value": item, "support": round(amount, 3)} for item, amount in ranked])))
                    decided += 1
    LOG.info("consolidated part %s/%s authors=%s attributes=%s seconds=%.1f", part + 1, parts, authors, decided, time.perf_counter() - started)
    return decided


@timed
def evidence(conn):
    for setting in PARALLEL:
        conn.execute(setting)
    rows = conn.execute(f"CREATE TABLE claim_evidence AS {EVIDENCE.format(months='true')}", {"no_author": NO_AUTHOR}).rowcount
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
def inspected(conn):
    parts = WORKERS * PARTS_PER_WORKER
    required = needs()
    stats, base = {}, defaultdict(Counter)
    with multiprocessing.Pool(WORKERS) as pool:
        for found, counted in pool.starmap(inspect, [(part, parts, required) for part in range(parts)]):
            for key, (count, hits) in found.items():
                entry = stats.setdefault(key, [0, 0])
                entry[0] += count
                entry[1] += hits
            for field, values in counted.items():
                base[field].update(values)
    return gate(conn, stats, base)


@timed
def decide(touched, blocked):
    parts = WORKERS * PARTS_PER_WORKER
    required = needs()
    with multiprocessing.Pool(WORKERS) as pool:
        return sum(pool.starmap(work, [(part, parts, touched, required, blocked) for part in range(parts)]))


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
            conn.execute(CLAIMS)
            conn.commit()
            evidence(conn)
        else:
            append(conn, added)
        attributes = decide(previous is not None, inspected(conn) if previous is None else blocked_scopes(conn))
        conn.execute("INSERT INTO consolidation (run_id, months, started_at, base, added) VALUES (%s, %s, %s, %s, %s)", [run_id, months, started, previous, added])
        if previous is None:
            conn.execute("ALTER TABLE author_claims ADD PRIMARY KEY (author, attribute)")
        else:
            conn.execute("DROP TABLE claim_evidence_added, claim_authors")
    vacuum("claim_evidence", "author_claims")
    LOG.info("consolidated run=%s months=%s attributes=%s", run_id, months, attributes)


@timed
def redecide():
    run_id = str(uuid.uuid4())
    with psycopg.connect(DSN) as conn:
        started = conn.execute("SELECT now()").fetchone()[0]
        months = conn.execute("SELECT months FROM consolidation").fetchone()[0]
        conn.execute(CLAIMS)
        conn.commit()
        attributes = decide(False, inspected(conn))
        conn.execute("DELETE FROM consolidation")
        conn.execute("INSERT INTO consolidation (run_id, months, started_at) VALUES (%s, %s, %s)", [run_id, months, started])
        conn.execute("ALTER TABLE author_claims ADD PRIMARY KEY (author, attribute)")
    vacuum("author_claims")
    LOG.info("redecided run=%s attributes=%s", run_id, attributes)
