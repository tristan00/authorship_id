import json
import threading

from database import NO_AUTHOR, client
from reddit_dumps import timed

ARROW = " › "
QUICK = {"readonly": 2, "max_execution_time": 5}
SLOW = {"readonly": 2, "max_execution_time": 30}
TOP = 12
SKIP = [*NO_AUTHOR, "AutoModerator"]
LOCAL = threading.local()

TIMES = "toHour(created_utc) AS hour, toDayOfWeek(created_utc) AS weekday, toString(toDate(created_utc)) AS day"
SPANS = "count() AS texts, countIf(record_type = 'post') AS posts, toUnixTimestamp(min(created_utc)) AS first_seen, toUnixTimestamp(max(created_utc)) AS last_seen"
AUTHOR_PATTERNS = f"""
SELECT multiIf(grouping(subreddit) = 0, 'where', grouping(hour) = 0, 'hour', grouping(weekday) = 0, 'weekday', grouping(day) = 0, 'day', 'total') AS dimension,
       subreddit, hour, weekday, day, {SPANS}, uniqExact(subreddit) AS spread
FROM (SELECT subreddit, record_type, created_utc, {TIMES} FROM records WHERE author = {{name:String}})
GROUP BY GROUPING SETS ((), (subreddit), (hour), (weekday), (day))
"""
SUBREDDIT_PATTERNS = f"""
SELECT multiIf(grouping(hour) = 0, 'hour', grouping(weekday) = 0, 'weekday', grouping(day) = 0, 'day', 'total') AS dimension, hour, weekday, day, {SPANS}
FROM (SELECT record_type, created_utc, {TIMES} FROM records_by_subreddit WHERE subreddit = {{name:String}})
GROUP BY GROUPING SETS ((), (hour), (weekday), (day))
"""


def connection():
    if not hasattr(LOCAL, "db"):
        LOCAL.db = client()
    return LOCAL.db


def rows(statement, parameters=None, settings=QUICK):
    result = connection().query(statement, parameters=parameters or {}, settings=settings)
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def first(statement, parameters=None):
    found = rows(statement, parameters)
    return found[0] if found else None


@timed
def top_subreddits():
    return rows("SELECT subreddit, texts FROM subreddit_counts ORDER BY texts DESC, subreddit LIMIT {top:UInt32}", {"top": TOP})


@timed
def top_authors():
    return rows("SELECT author, texts FROM author_counts WHERE author NOT IN {skip:Array(String)} ORDER BY texts DESC, author LIMIT {top:UInt32}", {"skip": SKIP, "top": TOP})


@timed
def find_subreddits(prefix):
    return rows("SELECT subreddit, texts FROM subreddit_counts WHERE startsWith(subreddit, {prefix:String}) "
                "ORDER BY subreddit = {prefix:String} DESC, texts DESC, subreddit LIMIT {top:UInt32}", {"prefix": prefix, "top": TOP})


@timed
def find_authors(query, variants, pattern):
    starts = " OR ".join(f"startsWith(author, {{v{index}:String}})" for index in range(len(variants)))
    parameters = {f"v{index}": variant for index, variant in enumerate(variants)} | {"pattern": pattern, "skip": list(NO_AUTHOR), "query": query, "top": TOP}
    return rows(f"SELECT author, texts FROM author_counts WHERE ({starts}) AND author ILIKE {{pattern:String}} AND author NOT IN {{skip:Array(String)}} "
                "ORDER BY author = {query:String} DESC, texts DESC, author LIMIT {top:UInt32}", parameters)


@timed
def author_counts(name):
    return first("SELECT author, texts, posts, toUnixTimestamp(first_seen) AS first_seen, toUnixTimestamp(last_seen) AS last_seen FROM author_counts WHERE author = {name:String}", {"name": name})


@timed
def subreddit_counts(name):
    return first("SELECT subreddit, texts, posts, toUnixTimestamp(first_seen) AS first_seen, toUnixTimestamp(last_seen) AS last_seen FROM subreddit_counts WHERE subreddit = {name:String}", {"name": name})


@timed
def stated(name):
    return {row["attribute"]: ", ".join(sorted(row["claimed"])) for row in rows("SELECT attribute, groupArray(value) AS claimed FROM author_claims WHERE author = {name:String} GROUP BY attribute", {"name": name})}


@timed
def prediction_targets():
    row = first("SELECT comment FROM system.tables WHERE database = currentDatabase() AND name = 'author_predictions'")
    return None if row is None else json.loads(row["comment"])["targets"]


@timed
def predicted(name, targets):
    fields = {"number": ("", "_low", "_high"), "window": ("", "_low", "_high", "_confidence"), "ranked": ("", "_confidence")}
    columns = ", ".join(f"`{target}{field}`" for target, kind in targets.items() for field in fields[kind])
    row = first(f"SELECT {columns} FROM author_predictions WHERE author = {{name:String}}", {"name": name})
    if row is None:
        return None
    return {target: shown({"value": row[target], "low": row[target + "_low"], "high": row[target + "_high"]} | ({"confidence": row[target + "_confidence"]} if kind == "window" else {})
                          if kind != "ranked" else [{"value": value, "confidence": chance} for value, chance in zip(row[target], row[target + "_confidence"])]) for target, kind in targets.items()}


def shown(prediction):
    if isinstance(prediction, dict):
        return f"{prediction['value']:.0f} ({prediction['low']:.0f}–{prediction['high']:.0f})" + (f" {prediction['confidence']:.0%}" if "confidence" in prediction else "")
    chance = {item["value"]: item["confidence"] for item in prediction}
    leaves = [path for path in chance if not any(other.startswith(path + ARROW) for other in chance)]
    chains = []
    for path in leaves:
        parts = path.split(ARROW)
        chains.append(ARROW.join(f"{part} {chance[ARROW.join(parts[:depth + 1])]:.0%}" if ARROW.join(parts[:depth + 1]) in chance else part for depth, part in enumerate(parts)))
    return "; ".join(chains)


@timed
def author_patterns(name):
    return rows(AUTHOR_PATTERNS, {"name": name}, SLOW)


@timed
def subreddit_patterns(name):
    return rows(SUBREDDIT_PATTERNS, {"name": name}, SLOW)


PAGE = 40
TEXT_LIMIT = 6000
RECORD = ("toUnixTimestamp(created_utc) AS at, record_id, record_type, author, subreddit, link_id, author_flair_text AS author_flair, link_flair_text AS link_flair, "
          "over_18, text_status, text_sha256")
BODIES = (f"SELECT text_sha256, substring(text, 1, {TEXT_LIMIT}) AS text, lengthUTF8(text) > {TEXT_LIMIT} AS cut FROM bodies "
          "WHERE text_sha256 IN (SELECT text_sha256 FROM page)")


def scope(filters, names):
    clauses = [clause for name, clause in (("type", "record_type = {type:String}"), ("subreddit", "subreddit = {subreddit:String}"), ("author", "author = {author:String}"),
                                           ("start", "created_utc >= toDateTime({start:UInt32})"), ("end", "created_utc < toDateTime({end:UInt32})"),
                                           ("before_at", "(created_utc, record_id) < (toDateTime({before_at:UInt32}), {before_id:String})")) if name in filters and name.split("_")[0] in names]
    return " AND ".join(["1", *clauses])


def with_bodies(page, parameters):
    return rows(f"WITH page AS ({page}) SELECT page.* EXCEPT text_sha256, bodies.text AS text, bodies.cut AS cut FROM page LEFT JOIN ({BODIES}) AS bodies USING text_sha256 "
                 "ORDER BY at DESC, record_id DESC", parameters, SLOW)


@timed
def author_records(name, filters):
    where = scope(filters, ("type", "subreddit", "start", "end", "before"))
    page = f"SELECT {RECORD} FROM records WHERE author = {{name:String}} AND {where} ORDER BY created_utc DESC, record_id DESC LIMIT {PAGE}"
    return with_bodies(page, {"name": name} | filters)


@timed
def subreddit_records(name, filters):
    where = scope(filters, ("type", "author", "start", "end", "before"))
    keys = (f"SELECT author, created_utc, record_id FROM records_by_subreddit WHERE subreddit = {{name:String}} AND {where} "
            f"ORDER BY created_utc DESC, record_id DESC LIMIT {PAGE}")
    page = (f"SELECT {RECORD} FROM records WHERE author IN (SELECT author FROM keys) AND record_id IN (SELECT record_id FROM keys) "
            "AND created_utc >= (SELECT min(created_utc) FROM keys) AND created_utc <= (SELECT max(created_utc) FROM keys)")
    return with_bodies(f"WITH keys AS ({keys}) {page}", {"name": name} | filters)


@timed
def subreddit_authors(name, filters):
    where = scope(filters, ("type", "start", "end"))
    return rows(f"SELECT author, count() AS texts, countIf(record_type = 'post') AS posts FROM records_by_subreddit WHERE subreddit = {{name:String}} AND {where} "
                "AND author NOT IN {skip:Array(String)} GROUP BY author ORDER BY texts DESC, author LIMIT 50", {"name": name, "skip": SKIP} | filters, SLOW)


@timed
def author_subreddits(name):
    return first("SELECT uniqExact(subreddit) AS subreddits FROM records WHERE author = {name:String}", {"name": name})["subreddits"]


@timed
def overview():
    totals = {row["name"]: row["total_rows"] for row in rows("SELECT name, total_rows FROM system.tables WHERE database = currentDatabase() AND name IN ('author_counts', 'subreddit_counts')")}
    return {"months": rows("SELECT month, records FROM months ORDER BY month"), "author_total": totals.get("author_counts", 0), "subreddit_total": totals.get("subreddit_counts", 0)}
