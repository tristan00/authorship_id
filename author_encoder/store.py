import time

from database import NO_AUTHOR, client, in_range, sha_ranges

from . import LOG, timed
from .config import AUTHOR_PARTS, DIMENSIONS, TEXT_PARTS, TEXTS_PER_USER

EXCLUDED = (*NO_AUTHOR, "AutoModerator")
READABLE = ("available", "title_only")
TABLES = (
    "CREATE TABLE IF NOT EXISTS author_texts (author String CODEC(ZSTD(1)), text String CODEC(ZSTD(3))) ENGINE = MergeTree ORDER BY author",
    "CREATE TABLE IF NOT EXISTS author_vectors (author String CODEC(ZSTD(1)), texts UInt16, vector Array(Float32)) ENGINE = MergeTree ORDER BY author",
    "CREATE TABLE IF NOT EXISTS encoded_parts (part UInt16, low String, high String, authors UInt64, texts UInt64, seconds Float32, finished_at DateTime('UTC') DEFAULT now()) "
    "ENGINE = MergeTree ORDER BY part",
)


@timed
def parts(db):
    lows = [row[0] for row in db.query(
        f"SELECT min(author) FROM (SELECT author, sum(least(texts, {TEXTS_PER_USER})) OVER (ORDER BY author ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS before "
        f"FROM author_counts WHERE author NOT IN {EXCLUDED}) "
        f"GROUP BY intDiv(before * {AUTHOR_PARTS}, (SELECT sum(least(texts, {TEXTS_PER_USER})) FROM author_counts WHERE author NOT IN {EXCLUDED})) ORDER BY 1").result_rows]
    return list(zip(lows, [*lows[1:], ""]))


def span(low, high):
    return "author >= {low:String}" + (" AND author < {high:String}" if high else ""), {"low": low, "high": high}


@timed
def build():
    db = client()
    ranges = parts(db)
    db.command("DROP TABLE IF EXISTS author_picks")
    db.command("CREATE TABLE author_picks (text_sha256 FixedString(32), author String) ENGINE = MergeTree ORDER BY text_sha256")
    started, picks = time.perf_counter(), 0
    for part, (low, high) in enumerate(ranges, 1):
        where, parameters = span(low, high)
        picks += db.command(f"INSERT INTO author_picks SELECT text_sha256, author FROM records WHERE {where} AND author NOT IN {EXCLUDED} AND text_status IN {READABLE} "
                            f"GROUP BY author, text_sha256 ORDER BY author, cityHash64(text_sha256), text_sha256 LIMIT {TEXTS_PER_USER} BY author", parameters=parameters).written_rows
        elapsed = time.perf_counter() - started
        LOG.info("picks parts=%d/%d rows=%d rate=%.0f eta_minutes=%.1f", part, len(ranges), picks, picks / elapsed, elapsed / part * (len(ranges) - part) / 60)
    db.command("DROP TABLE IF EXISTS author_texts_next")
    db.command(TABLES[0].replace("IF NOT EXISTS author_texts", "author_texts_next"))
    started, texts = time.perf_counter(), 0
    for part, (low, high) in enumerate(sha_ranges(TEXT_PARTS), 1):
        picked = f"SELECT text_sha256, author FROM author_picks WHERE {in_range('text_sha256', low, high)}"
        texts += db.command(f"INSERT INTO author_texts_next SELECT picks.author, bodies.text FROM bodies INNER JOIN ({picked}) AS picks USING text_sha256 "
                            f"WHERE {in_range('bodies.text_sha256', low, high)} AND bodies.text_sha256 IN (SELECT text_sha256 FROM ({picked}))").written_rows
        elapsed = time.perf_counter() - started
        LOG.info("texts parts=%d/%d rows=%d rate=%.0f eta_minutes=%.1f", part, TEXT_PARTS, texts, texts / elapsed, elapsed / part * (TEXT_PARTS - part) / 60)
    db.command(TABLES[0])
    db.command("EXCHANGE TABLES author_texts_next AND author_texts")
    db.command("DROP TABLE author_texts_next")
    db.command("DROP TABLE author_picks")
    db.command("DROP TABLE IF EXISTS encoded_parts")
    return {"author_parts": len(ranges), "picks": picks, "texts": texts}


@timed
def vector(author):
    rows = client().query("SELECT texts, vector FROM author_vectors WHERE author = {author:String}", parameters={"author": author}).result_rows
    return {"author": author, "texts": rows[0][0], "dimensions": DIMENSIONS, "vector": list(rows[0][1])} if rows else None


@timed
def similar(author, limit):
    db = client()
    if not db.command("SELECT count() FROM author_vectors WHERE author = {author:String}", parameters={"author": author}):
        return None
    rows = db.query("WITH (SELECT vector FROM author_vectors WHERE author = {author:String}) AS target "
                    "SELECT author, texts, 1 - cosineDistance(vector, target) AS similarity FROM author_vectors WHERE author != {author:String} "
                    "ORDER BY similarity DESC LIMIT {limit:UInt32}", parameters={"author": author, "limit": limit}).result_rows
    return {"author": author, "neighbours": [{"author": name, "texts": texts, "similarity": similarity} for name, texts, similarity in rows]}
