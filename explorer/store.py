from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from database import DSN, NO_AUTHOR
from reddit_dumps import timed

OPTIONS = "-c statement_timeout=5000 -c default_transaction_read_only=on"
PATTERN_TIMEOUT_MS = 30000
TOP = 12
POOL = ConnectionPool(DSN, min_size=1, max_size=8, open=False, kwargs={"autocommit": True, "row_factory": dict_row, "options": OPTIONS})

SPLIT = """created_utc / 3600 %% 24 AS hour, (created_utc / 86400 + 3) %% 7 + 1 AS weekday,
           to_char(to_timestamp(created_utc) AT TIME ZONE 'UTC', 'YYYY-MM') AS month"""

AUTHOR_PATTERNS = f"""
SELECT CASE WHEN GROUPING(subreddit) = 0 THEN 'where' WHEN GROUPING(hour) = 0 THEN 'hour'
            WHEN GROUPING(weekday) = 0 THEN 'weekday' WHEN GROUPING(month) = 0 THEN 'month' ELSE 'total' END AS dimension,
       subreddit, hour, weekday, month, count(*) AS texts, count(*) FILTER (WHERE record_type = 'post') AS posts,
       count(DISTINCT subreddit) AS spread, min(created_utc) AS first_seen, max(created_utc) AS last_seen
FROM (SELECT subreddit, record_type, created_utc, {SPLIT} FROM records WHERE author = %s) r
GROUP BY GROUPING SETS ((), (subreddit), (hour), (weekday), (month))
"""

SUBREDDIT_PATTERNS = "SELECT created_utc / 3600 AS bucket, count(*) AS texts FROM records WHERE subreddit = %s GROUP BY 1"

AUTHOR_BRANCH = "SELECT author, texts FROM author_counts WHERE author >= {v} AND author < {v} || chr(1114111) AND author ILIKE {pattern}"


@timed
def top_subreddits():
    with POOL.connection() as conn:
        return conn.execute("SELECT subreddit, texts FROM subreddit_counts ORDER BY texts DESC, subreddit LIMIT %s", (TOP,)).fetchall()


@timed
def top_authors():
    with POOL.connection() as conn:
        return conn.execute("SELECT author, texts FROM author_counts WHERE author <> ALL(%s) ORDER BY texts DESC, author LIMIT %s", (NO_AUTHOR, TOP)).fetchall()


@timed
def find_subreddits(prefix):
    with POOL.connection() as conn:
        return conn.execute("""SELECT subreddit, texts FROM subreddit_counts WHERE subreddit >= %(p)s AND subreddit < %(p)s || chr(1114111)
                               ORDER BY subreddit = %(p)s DESC, texts DESC, subreddit LIMIT %(top)s""", {"p": prefix, "top": TOP}).fetchall()


@timed
def find_authors(query, variants, pattern):
    branches = sql.SQL(" UNION ALL ").join(sql.SQL(AUTHOR_BRANCH).format(v=sql.Placeholder(f"v{i}"), pattern=sql.Placeholder("pattern")) for i in range(len(variants)))
    statement = sql.SQL("SELECT author, texts FROM ({branches}) found WHERE author <> ALL(%(placeholders)s) "
                        "ORDER BY author = %(query)s DESC, texts DESC, author LIMIT %(top)s").format(branches=branches)
    params = {f"v{i}": variant for i, variant in enumerate(variants)} | {"pattern": pattern, "placeholders": NO_AUTHOR, "query": query, "top": TOP}
    with POOL.connection() as conn:
        return conn.execute(statement, params).fetchall()


@timed
def author_counts(name):
    with POOL.connection() as conn:
        return conn.execute("SELECT author, texts, posts, first_seen, last_seen FROM author_counts WHERE author = %s", (name,)).fetchone()


@timed
def subreddit_counts(name):
    with POOL.connection() as conn:
        return conn.execute("SELECT subreddit, texts, posts, first_seen, last_seen FROM subreddit_counts WHERE subreddit = %s", (name,)).fetchone()


@timed
def stated(name):
    with POOL.connection() as conn:
        return {row["attribute"]: row["value"] for row in conn.execute("SELECT attribute::text AS attribute, value FROM author_claims WHERE author = %s", (name,))}


@timed
def prediction_targets():
    with POOL.connection() as conn:
        row = conn.execute("SELECT targets FROM prediction").fetchone()
    return None if row is None else row["targets"]


@timed
def predicted(name, attributes):
    statement = sql.SQL("SELECT {columns} FROM author_predictions WHERE account = %s").format(columns=sql.SQL(", ").join(map(sql.Identifier, attributes)))
    with POOL.connection() as conn:
        return conn.execute(statement, (name,)).fetchone()


@timed
def author_patterns(name):
    return slow(AUTHOR_PATTERNS, (name,))


@timed
def subreddit_patterns(name):
    return slow(SUBREDDIT_PATTERNS, (name,))


def slow(statement, params):
    with POOL.connection() as conn, conn.transaction():
        conn.execute(f"SET LOCAL statement_timeout = {PATTERN_TIMEOUT_MS}")
        return conn.execute(statement, params).fetchall()
