import json
import multiprocessing
import time
from collections import Counter, defaultdict
from itertools import groupby
from operator import itemgetter

from claim_extraction.config import PARTS
from database import LOGS, NO_AUTHOR, client
from reddit_dumps import setup_logging

from . import LOG, timed
from .config import BOT_AUTHORS, INSERT_ROWS, NEED, PARTS_PER_WORKER, WORKERS
from .gate import blocked, merged, tallied
from .rules import FLAIR, audit
from .rules import consolidate as rules

EVIDENCE = (
    "CREATE TABLE author_evidence (author String, attribute LowCardinality(String), value String, created_utc DateTime('UTC'), subreddit String, "
    "text_sha256 FixedString(32), position UInt32, source LowCardinality(String)) ENGINE = MergeTree ORDER BY (author, attribute)"
)
FILL = (
    "INSERT INTO author_evidence SELECT r.author, c.attribute, c.value, r.created_utc, r.subreddit, c.text_sha256, c.position, 'text' "
    "FROM records AS r INNER JOIN text_claims AS c ON r.text_sha256 = c.text_sha256 WHERE r.author NOT IN {excluded} "
    "SETTINGS join_algorithm = 'grace_hash', grace_hash_join_initial_buckets = 64"
)
FILL_FLAIRS = (
    "INSERT INTO author_evidence SELECT r.author, f.attribute, f.value, r.created_utc, r.subreddit, SHA256(concat('flair:', r.subreddit, '/', r.flair)), 0, '" + FLAIR + "' "
    "FROM (SELECT author, subreddit, author_flair_text AS flair, max(created_utc) AS created_utc FROM records WHERE author_flair_text != '' AND author NOT IN {excluded} "
    "GROUP BY author, subreddit, flair) AS r INNER JOIN flair_claims AS f ON r.subreddit = f.subreddit AND r.flair = f.flair"
)
CLAIMS = (
    "CREATE TABLE author_claims_next (author String, attribute LowCardinality(String), value String, support Float32, share Float32, candidates String) "
    "ENGINE = MergeTree ORDER BY (author, attribute)"
)
COLUMNS = ("author", "attribute", "value", "support", "share", "candidates")
READ = "SELECT author, attribute, value, text_sha256, created_utc, subreddit, source FROM author_evidence WHERE author >= {low:String} AND author < {high:String} ORDER BY author"
LAST_AUTHOR = "\U0010FFFF"


def ranges(db, parts):
    authors = sorted(row[0] for row in db.query("SELECT DISTINCT author FROM author_evidence WHERE cityHash64(author) % 1000 = 0").result_rows)
    edges = sorted({authors[len(authors) * part // parts] for part in range(1, parts)})
    return list(zip(["", *edges], [*edges, LAST_AUTHOR]))


def authors(low, high):
    with client().query_row_block_stream(READ, parameters={"low": low, "high": high}) as stream:
        for author, group in groupby((row for block in stream for row in block), key=itemgetter(0)):
            yield author, [row[1:] for row in group]


def inspect(low, high, need=NEED):
    setup_logging(LOGS / "consolidation.log")
    started = time.perf_counter()
    stats, base = {}, defaultdict(Counter)
    for author, rows in authors(low, high):
        if any(row[-1] == FLAIR for row in rows):
            decided, pairs = audit(rows, need)
            tallied(pairs, decided, stats, base)
    LOG.info("inspected from=%r scopes=%d seconds=%.1f", low, len(stats), time.perf_counter() - started)
    return stats, {attribute: dict(counted) for attribute, counted in base.items()}


def work(low, high, gated, need=NEED):
    setup_logging(LOGS / "consolidation.log")
    started = time.perf_counter()
    db = client()
    rows, count, decided = [], 0, 0
    for author, found in authors(low, high):
        count += 1
        for attribute, (value, support, share, candidates) in rules(found, need, gated).items():
            ranked = sorted(candidates.items(), key=lambda item: (-item[1], item[0]))
            rows.append((author, attribute, value, support, share, json.dumps([[item, amount] for item, amount in ranked], ensure_ascii=False)))
            decided += 1
        if len(rows) >= INSERT_ROWS:
            db.insert("author_claims_next", rows, column_names=COLUMNS)
            rows = []
    if rows:
        db.insert("author_claims_next", rows, column_names=COLUMNS)
    LOG.info("consolidated from=%r authors=%d attributes=%d seconds=%.1f", low, count, decided, time.perf_counter() - started)
    return decided


@timed
def evidence(db):
    excluded = tuple([*NO_AUTHOR, *BOT_AUTHORS])
    db.command("DROP TABLE IF EXISTS author_evidence")
    db.command(EVIDENCE)
    db.command(FILL.format(excluded=excluded))
    db.command(FILL_FLAIRS.format(excluded=excluded))
    LOG.info("evidence rows=%s", db.query("SELECT source, count() FROM author_evidence GROUP BY source").result_rows)


@timed
def decide(db):
    db.command("DROP TABLE IF EXISTS author_claims_next")
    db.command(CLAIMS)
    parts = ranges(db, WORKERS * PARTS_PER_WORKER)
    with multiprocessing.Pool(WORKERS) as pool:
        gated = blocked(*merged(pool.starmap(inspect, parts)))
        decided = sum(pool.starmap(work, [(low, high, gated) for low, high in parts]))
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
