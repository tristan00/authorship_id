import multiprocessing
import time

from database import client, in_range, sha_ranges

from . import LOG, timed
from .config import CHUNK_TEXTS, INSERT_ROWS, PARTS, WORKERS

TABLES = (
    "CREATE TABLE IF NOT EXISTS text_claims (text_sha256 FixedString(32), attribute LowCardinality(String), value String, position UInt32) "
    "ENGINE = MergeTree ORDER BY (text_sha256, attribute)",
    "CREATE TABLE IF NOT EXISTS flair_claims (subreddit String, flair String, attribute LowCardinality(String), value String) ENGINE = MergeTree ORDER BY (subreddit, flair)",
    "CREATE TABLE IF NOT EXISTS extracted_parts (part UInt16, texts UInt64, claims UInt64, seconds Float32, finished_at DateTime('UTC') DEFAULT now()) ENGINE = MergeTree ORDER BY part",
)
COLUMNS = ("text_sha256", "attribute", "value", "position")


def work(batch):
    from .patterns import positioned
    return len(batch), [(digest, attribute, str(value), position) for digest, text in batch for (attribute, value), position in positioned(text).items()]


def flair_work(batch):
    from .flairs import flair_claims
    return len(batch), [(subreddit, flair, attribute, str(value)) for subreddit, flair in batch for attribute, value in flair_claims(subreddit, flair)]


def flair_chunks():
    batch = []
    with client().query_row_block_stream("SELECT DISTINCT subreddit, author_flair_text FROM records WHERE author_flair_text != ''") as stream:
        for block in stream:
            for row in block:
                batch.append(row)
                if len(batch) == CHUNK_TEXTS:
                    yield batch
                    batch = []
    if batch:
        yield batch


@timed
def extract_flairs():
    db = client()
    for statement in TABLES:
        db.command(statement)
    db.command("TRUNCATE TABLE flair_claims")
    started, flairs, pending, claims = time.perf_counter(), 0, [], 0
    with multiprocessing.Pool(WORKERS) as pool:
        for done, found in pool.imap_unordered(flair_work, flair_chunks()):
            flairs += done
            pending += found
            if len(pending) >= INSERT_ROWS:
                db.insert("flair_claims", pending, column_names=("subreddit", "flair", "attribute", "value"))
                claims, pending = claims + len(pending), []
    if pending:
        db.insert("flair_claims", pending, column_names=("subreddit", "flair", "attribute", "value"))
        claims += len(pending)
    LOG.info("flairs=%d claims=%d seconds=%.0f", flairs, claims, time.perf_counter() - started)


def chunks(low, high):
    batch = []
    with client().query_row_block_stream(f"SELECT text_sha256, text FROM bodies WHERE {in_range('text_sha256', low, high)}") as stream:
        for block in stream:
            for row in block:
                batch.append(row)
                if len(batch) == CHUNK_TEXTS:
                    yield batch
                    batch = []
    if batch:
        yield batch


@timed
def extract_part(db, pool, part, low, high):
    started = time.perf_counter()
    if db.command(f"SELECT count() FROM text_claims WHERE {in_range('text_sha256', low, high)}"):
        db.command(f"DELETE FROM text_claims WHERE {in_range('text_sha256', low, high)}")
    texts = claims = 0
    pending = []
    for done, found in pool.imap_unordered(work, chunks(low, high)):
        texts += done
        pending += found
        if len(pending) >= INSERT_ROWS:
            db.insert("text_claims", pending, column_names=COLUMNS)
            claims += len(pending)
            pending = []
    if pending:
        db.insert("text_claims", pending, column_names=COLUMNS)
        claims += len(pending)
    seconds = time.perf_counter() - started
    db.insert("extracted_parts", [(part, texts, claims, seconds)], column_names=("part", "texts", "claims", "seconds"))
    LOG.info("part=%d texts=%d claims=%d seconds=%.0f rate=%.0f", part, texts, claims, seconds, texts / max(seconds, 1e-9))
    return texts


@timed
def extract(reset=False):
    db = client()
    if reset:
        db.command("DROP TABLE IF EXISTS text_claims")
        db.command("DROP TABLE IF EXISTS extracted_parts")
    for statement in TABLES:
        db.command(statement)
    done = {row[0] for row in db.query("SELECT part FROM extracted_parts").result_rows}
    todo = [(part, low, high) for part, (low, high) in enumerate(sha_ranges(PARTS)) if part not in done]
    LOG.info("extract parts=%d done=%d todo=%d workers=%d", PARTS, len(done), len(todo), WORKERS)
    started, texts = time.perf_counter(), 0
    with multiprocessing.Pool(WORKERS) as pool:
        for index, (part, low, high) in enumerate(todo, 1):
            texts += extract_part(db, pool, part, low, high)
            elapsed = time.perf_counter() - started
            LOG.info("progress parts=%d/%d texts=%d rate=%.0f eta_hours=%.1f", index, len(todo), texts, texts / elapsed, elapsed / index * (len(todo) - index) / 3600)
