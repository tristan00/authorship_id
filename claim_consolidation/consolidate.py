import json
import multiprocessing
import time
from itertools import groupby
from operator import itemgetter

from claim_extraction.config import PARTS
from database import NO_AUTHOR, client
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import BOT_AUTHORS, INSERT_ROWS, NEED, PARTS_PER_WORKER, WORKERS
from .rules import consolidate as rules

EVIDENCE = (
    "CREATE TABLE author_evidence (author String, attribute LowCardinality(String), value String, created_utc DateTime('UTC'), subreddit String, "
    "text_sha256 FixedString(32), position UInt32) ENGINE = MergeTree ORDER BY (author, attribute)"
)
FILL = (
    "INSERT INTO author_evidence SELECT r.author, c.attribute, c.value, r.created_utc, r.subreddit, c.text_sha256, c.position "
    "FROM records AS r INNER JOIN text_claims AS c ON r.text_sha256 = c.text_sha256 WHERE r.author NOT IN {excluded} "
    "SETTINGS join_algorithm = 'grace_hash', grace_hash_join_initial_buckets = 64"
)
CLAIMS = (
    "CREATE TABLE author_claims_next (author String, attribute LowCardinality(String), value String, support Float32, share Float32, candidates String) "
    "ENGINE = MergeTree ORDER BY (author, attribute)"
)
COLUMNS = ("author", "attribute", "value", "support", "share", "candidates")
READ = "SELECT author, attribute, value, text_sha256, created_utc, subreddit FROM author_evidence WHERE author >= {low:String} AND author < {high:String} ORDER BY author"
LAST_AUTHOR = "\U0010FFFF"


def ranges(db, parts):
    authors = sorted(row[0] for row in db.query("SELECT DISTINCT author FROM author_evidence WHERE cityHash64(author) % 1000 = 0").result_rows)
    edges = sorted({authors[len(authors) * part // parts] for part in range(1, parts)})
    return list(zip(["", *edges], [*edges, LAST_AUTHOR]))


def work(low, high, need=NEED):
    from database import LOGS
    setup_logging(LOGS / "consolidation.log")
    started = time.perf_counter()
    db = client()
    rows, authors, decided = [], 0, 0
    with db.query_row_block_stream(READ, parameters={"low": low, "high": high}) as stream:
        flat = (row for block in stream for row in block)
        for author, group in groupby(flat, key=itemgetter(0)):
            authors += 1
            for attribute, (value, support, share, candidates) in rules([row[1:] for row in group], need).items():
                ranked = sorted(candidates.items(), key=lambda item: (-item[1], item[0]))
                rows.append((author, attribute, value, support, share, json.dumps([[item, amount] for item, amount in ranked], ensure_ascii=False)))
                decided += 1
            if len(rows) >= INSERT_ROWS:
                db.insert("author_claims_next", rows, column_names=COLUMNS)
                rows = []
    if rows:
        db.insert("author_claims_next", rows, column_names=COLUMNS)
    LOG.info("consolidated from=%r authors=%d attributes=%d seconds=%.1f", low, authors, decided, time.perf_counter() - started)
    return decided


@timed
def evidence(db):
    db.command("DROP TABLE IF EXISTS author_evidence")
    db.command(EVIDENCE)
    db.command(FILL.format(excluded=tuple([*NO_AUTHOR, *BOT_AUTHORS])))
    LOG.info("evidence rows=%d", db.command("SELECT count() FROM author_evidence"))


@timed
def decide(db):
    db.command("DROP TABLE IF EXISTS author_claims_next")
    db.command(CLAIMS)
    parts = ranges(db, WORKERS * PARTS_PER_WORKER)
    with multiprocessing.Pool(WORKERS) as pool:
        decided = sum(pool.starmap(work, parts))
    db.command("CREATE TABLE IF NOT EXISTS author_claims AS author_claims_next")
    db.command("EXCHANGE TABLES author_claims_next AND author_claims")
    db.command("DROP TABLE author_claims_next")
    LOG.info("author claims rows=%d", decided)


@timed
def consolidate():
    db = client()
    if db.command("SELECT count() FROM extracted_parts") < PARTS:
        raise ValueError("claim extraction has not finished every part")
    evidence(db)
    decide(db)


@timed
def redecide():
    decide(client())
