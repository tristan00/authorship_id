import hashlib
import time
from pathlib import Path

from database import NO_AUTHOR, client, in_range, sha_ranges

from . import LOG, timed
from .config import AUTHOR_PARTS, DIMENSIONS, TEXT_PARTS, TEXTS_PER_USER

EXCLUDED = (*NO_AUTHOR, "AutoModerator")
READABLE = ("available", "title_only")
SPACE = r"\t\n\x{0b}\f\r \x{1c}-\x{1f}\x{85}\x{a0}\x{1680}\x{2000}-\x{200a}\x{2028}\x{2029}\x{202f}\x{205f}\x{3000}"
QUOTE = "(?m)^[" + SPACE + r"]*>[^\n]*$"
LINK = "(?i)https?://[^" + SPACE + "]+|www[.][^" + SPACE + "]+"
MENTION = r"(?i)(^|[^\p{L}\p{N}_])/?[ur]/[\p{L}\p{N}_-]+"
TABLES = (
    "CREATE TABLE IF NOT EXISTS author_texts (author String CODEC(ZSTD(1)), text String CODEC(ZSTD(3))) ENGINE = MergeTree ORDER BY author",
    "CREATE TABLE IF NOT EXISTS author_vectors (author String CODEC(ZSTD(1)), texts UInt16, vector Array(Float32)) ENGINE = MergeTree ORDER BY author",
    "CREATE TABLE IF NOT EXISTS encoded_parts (part UInt16, low String, high String, authors UInt64, texts UInt64, seconds Float32, source String, finished_at DateTime('UTC') DEFAULT now()) "
    "ENGINE = MergeTree ORDER BY part",
    "CREATE TABLE IF NOT EXISTS author_texts_source (fingerprint String, built_at DateTime('UTC') DEFAULT now()) ENGINE = MergeTree ORDER BY tuple()",
)


def fingerprint(*parts):
    return hashlib.sha256(repr(parts).encode()).hexdigest()[:16]


@timed
def texts_source(db):
    months = db.query("SELECT month, records, toString(loaded_at) FROM months ORDER BY month").result_rows
    return fingerprint(months, TEXTS_PER_USER, AUTHOR_PARTS, TEXT_PARTS, Path(__file__).read_text(encoding="utf-8"))


@timed
def built_source(db):
    for statement in TABLES:
        db.command(statement)
    rows = db.query("SELECT fingerprint FROM author_texts_source").result_rows
    return rows[0][0] if rows else None


@timed
def parts(db):
    lows = [row[0] for row in db.query(
        f"SELECT min(author) FROM (SELECT author, sum(least(texts, {TEXTS_PER_USER})) OVER (ORDER BY author ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS before "
        f"FROM author_counts WHERE author NOT IN {EXCLUDED}) "
        f"GROUP BY intDiv(before * {AUTHOR_PARTS}, (SELECT sum(least(texts, {TEXTS_PER_USER})) FROM author_counts WHERE author NOT IN {EXCLUDED})) ORDER BY 1").result_rows]
    return list(zip(lows, [*lows[1:], ""]))


def literal(pattern):
    return "'" + pattern.replace("\\", "\\\\").replace("'", "\\'") + "'"


CLEAN = (f"trimBoth(replaceRegexpAll(replaceRegexpAll(replaceRegexpAll(replaceRegexpAll(normalizeUTF8NFKC(bodies.text), {literal(QUOTE)}, ''), {literal(LINK)}, ' URL '), "
         f"{literal(MENTION)}, {literal(r'\1 MENTION ')}), {literal('[' + SPACE + ']+')}, ' '))")


def span(low, high):
    return "author >= {low:String}" + (" AND author < {high:String}" if high else ""), {"low": low, "high": high}


@timed
def build():
    db = client()
    source = texts_source(db)
    if built_source(db) == source:
        LOG.info("author_texts current source=%s", source)
        return {"source": source, "built": False}
    ranges = parts(db)
    db.command("DROP TABLE IF EXISTS author_picks")
    db.command("CREATE TABLE author_picks (text_sha256 FixedString(32), author String) ENGINE = MergeTree ORDER BY text_sha256")
    started, picks = time.perf_counter(), 0
    for part, (low, high) in enumerate(ranges, 1):
        where, parameters = span(low, high)
        picks += db.command(f"INSERT INTO author_picks SELECT text_sha256, author FROM (SELECT author, arraySlice(arraySort(sha -> (cityHash64(sha), sha), groupUniqArray(text_sha256)), 1, {TEXTS_PER_USER}) AS picked "
                            f"FROM records WHERE {where} AND author NOT IN {EXCLUDED} AND text_status IN {READABLE} GROUP BY author) ARRAY JOIN picked AS text_sha256 "
                            "SETTINGS optimize_aggregation_in_order = 1", parameters=parameters).written_rows
        elapsed = time.perf_counter() - started
        LOG.info("picks parts=%d/%d rows=%d rate=%.0f eta_minutes=%.1f", part, len(ranges), picks, picks / elapsed, elapsed / part * (len(ranges) - part) / 60)
    db.command("DROP TABLE IF EXISTS author_texts_next")
    db.command(TABLES[0].replace("IF NOT EXISTS author_texts", "author_texts_next"))
    started, texts = time.perf_counter(), 0
    for part, (low, high) in enumerate(sha_ranges(TEXT_PARTS), 1):
        picked = f"SELECT text_sha256, author FROM author_picks WHERE {in_range('text_sha256', low, high)}"
        texts += db.command(f"INSERT INTO author_texts_next (author, text) SELECT author, cleaned FROM (SELECT picks.author AS author, {CLEAN} AS cleaned FROM bodies "
                            f"INNER JOIN ({picked}) AS picks USING text_sha256 WHERE {in_range('bodies.text_sha256', low, high)} "
                            f"AND bodies.text_sha256 IN (SELECT text_sha256 FROM ({picked}))) WHERE cleaned != ''").written_rows
        elapsed = time.perf_counter() - started
        LOG.info("texts parts=%d/%d rows=%d rate=%.0f eta_minutes=%.1f", part, TEXT_PARTS, texts, texts / elapsed, elapsed / part * (TEXT_PARTS - part) / 60)
    db.command(TABLES[0])
    db.command("EXCHANGE TABLES author_texts_next AND author_texts")
    db.command("DROP TABLE author_texts_next")
    db.command("DROP TABLE author_picks")
    db.command("TRUNCATE TABLE author_texts_source")
    db.insert("author_texts_source", [(source,)], column_names=("fingerprint",))
    return {"source": source, "built": True, "author_parts": len(ranges), "picks": picks, "texts": texts}


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
