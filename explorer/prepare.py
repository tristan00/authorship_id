import psycopg

from database import DSN, NOT_PEOPLE

from . import timed
from .config import TEXT_SORTS


@timed
def activity(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_activity")
    conn.execute("""
        CREATE UNLOGGED TABLE explorer_activity AS
        SELECT author, subreddit, count(*) AS texts, count(*) FILTER (WHERE record_type = 'post') AS posts,
               min(created_utc) AS first_utc, max(created_utc) AS last_utc
        FROM texts GROUP BY author, subreddit""")
    conn.execute("ALTER TABLE explorer_activity ADD COLUMN person boolean")
    conn.execute("UPDATE explorer_activity SET person = author !~* %s", [NOT_PEOPLE])


@timed
def authors(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_authors")
    conn.execute("""
        CREATE TABLE explorer_authors AS
        SELECT author, sum(texts)::int AS texts, sum(posts)::int AS posts, min(first_utc) AS first_utc, max(last_utc) AS last_utc,
               array_agg(subreddit ORDER BY texts DESC, subreddit) AS subs
        FROM explorer_activity WHERE person GROUP BY author""")
    conn.execute("ALTER TABLE explorer_authors ADD PRIMARY KEY (author)")


@timed
def subreddits(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_subreddits")
    conn.execute("""
        CREATE TABLE explorer_subreddits AS
        SELECT subreddit, sum(texts)::int AS texts, sum(posts)::int AS posts, count(*) FILTER (WHERE person)::int AS authors,
               min(first_utc) AS first_utc, max(last_utc) AS last_utc
        FROM explorer_activity GROUP BY subreddit""")
    conn.execute("ALTER TABLE explorer_subreddits ADD PRIMARY KEY (subreddit)")


@timed
def texts(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_texts")
    conn.execute("""
        CREATE TABLE explorer_texts AS
        WITH evidence AS (
            SELECT c.source_key AS record_id, c.author, c.field, a.value IS DISTINCT FROM c.value AS outvoted
            FROM claim_evidence c LEFT JOIN author_claims a ON a.author = c.author AND a.attribute = c.field
            WHERE c.source = 'text'),
        incohesive AS (
            SELECT DISTINCT author, field FROM evidence WHERE outvoted),
        flagged AS (
            SELECT e.record_id, i.author IS NOT NULL AS incohesive, e.outvoted
            FROM evidence e LEFT JOIN incohesive i USING (author, field)),
        counts AS (
            SELECT record_id, count(*)::int AS claims, count(*) FILTER (WHERE incohesive)::int AS incohesive,
                   count(*) FILTER (WHERE outvoted)::int AS outvoted
            FROM flagged GROUP BY record_id)
        SELECT t.record_id, t.author, t.subreddit, t.record_type, t.created_utc, regexp_count(t.text, '\\S+') AS words,
               c.claims, c.incohesive, c.outvoted
        FROM counts c JOIN texts t USING (record_id)""")
    conn.execute("ALTER TABLE explorer_texts ADD PRIMARY KEY (record_id)")
    for column in TEXT_SORTS:
        conn.execute(f"CREATE INDEX ON explorer_texts ({column}, record_id)")


@timed
def suspects(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS suspect_claim_texts (
        record_id text NOT NULL, attribute text NOT NULL, value text NOT NULL, flagged_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (record_id, attribute, value))""")


@timed
def prepare():
    with psycopg.connect(DSN) as conn:
        activity(conn)
        authors(conn)
        subreddits(conn)
        texts(conn)
        suspects(conn)
        conn.execute("DROP TABLE explorer_activity")
