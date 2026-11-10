import json
import threading

from database import NO_AUTHOR, client
from reddit_dumps import timed

QUICK = {"readonly": 2, "max_execution_time": 5}
SLOW = {"readonly": 2, "max_execution_time": 30}
TOP = 12
LOCAL = threading.local()

TIMES = "toHour(created_utc) AS hour, toDayOfWeek(created_utc) AS weekday, formatDateTime(created_utc, '%Y-%m') AS month"
SPANS = "count() AS texts, countIf(record_type = 'post') AS posts, toUnixTimestamp(min(created_utc)) AS first_seen, toUnixTimestamp(max(created_utc)) AS last_seen"
AUTHOR_PATTERNS = f"""
SELECT multiIf(grouping(subreddit) = 0, 'where', grouping(hour) = 0, 'hour', grouping(weekday) = 0, 'weekday', grouping(month) = 0, 'month', 'total') AS dimension,
       subreddit, hour, weekday, month, {SPANS}, uniqExact(subreddit) AS spread
FROM (SELECT subreddit, record_type, created_utc, {TIMES} FROM records WHERE author = {{name:String}})
GROUP BY GROUPING SETS ((), (subreddit), (hour), (weekday), (month))
"""
SUBREDDIT_PATTERNS = f"""
SELECT multiIf(grouping(hour) = 0, 'hour', grouping(weekday) = 0, 'weekday', grouping(month) = 0, 'month', 'total') AS dimension, hour, weekday, month, {SPANS}
FROM (SELECT record_type, created_utc, {TIMES} FROM records_by_subreddit WHERE subreddit = {{name:String}})
GROUP BY GROUPING SETS ((), (hour), (weekday), (month))
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
    return rows("SELECT author, texts FROM author_counts WHERE author NOT IN {skip:Array(String)} ORDER BY texts DESC, author LIMIT {top:UInt32}", {"skip": list(NO_AUTHOR), "top": TOP})


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
def predicted(name, attributes):
    columns = ", ".join(f"`{attribute}`" for attribute in attributes)
    row = first(f"SELECT {columns} FROM author_predictions WHERE author = {{name:String}}", {"name": name})
    return None if row is None else {key: shown(value) for key, value in row.items()}


def shown(value):
    if isinstance(value, list):
        return ", ".join(value)
    return round(value, 1) if isinstance(value, float) else value


@timed
def author_patterns(name):
    return rows(AUTHOR_PATTERNS, {"name": name}, SLOW)


@timed
def subreddit_patterns(name):
    return rows(SUBREDDIT_PATTERNS, {"name": name}, SLOW)
