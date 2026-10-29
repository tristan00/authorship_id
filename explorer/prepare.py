import psycopg

from database import DSN, INDEX_MEMORY, NO_AUTHOR, SCAN_WORKERS, vacuum

from . import timed
from .config import TEXT_SORTS


@timed
def activity(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_activity")
    conn.execute("""
        CREATE TABLE explorer_activity AS
        SELECT author, subreddit, count(*) AS texts, count(*) FILTER (WHERE record_type = 'post') AS posts,
               min(created_utc) AS first_utc, max(created_utc) AS last_utc, author <> ALL(%s) AS named
        FROM records GROUP BY author, subreddit""", [NO_AUTHOR])
    conn.execute("CREATE INDEX explorer_activity_subreddit ON explorer_activity (subreddit, texts DESC, author) WHERE named")


@timed
def authors(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_authors")
    conn.execute("""
        CREATE TABLE explorer_authors AS
        SELECT author, sum(texts)::int AS texts, sum(posts)::int AS posts, min(first_utc) AS first_utc, max(last_utc) AS last_utc,
               array_agg(subreddit ORDER BY texts DESC, subreddit) AS subs
        FROM explorer_activity WHERE named GROUP BY author""")
    conn.execute("ALTER TABLE explorer_authors ADD PRIMARY KEY (author)")
    conn.execute("CREATE INDEX explorer_authors_texts ON explorer_authors (texts DESC, author)")
    conn.execute("CREATE INDEX explorer_authors_name ON explorer_authors USING gin (author gin_trgm_ops)")
    conn.execute("CREATE INDEX explorer_authors_subs ON explorer_authors USING gin (subs)")


@timed
def subreddits(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_subreddits")
    conn.execute("""
        CREATE TABLE explorer_subreddits AS
        SELECT subreddit, sum(texts)::int AS texts, sum(posts)::int AS posts, count(*) FILTER (WHERE named)::int AS authors,
               min(first_utc) AS first_utc, max(last_utc) AS last_utc
        FROM explorer_activity GROUP BY subreddit""")
    conn.execute("ALTER TABLE explorer_subreddits ADD PRIMARY KEY (subreddit)")
    conn.execute("CREATE INDEX explorer_subreddits_texts ON explorer_subreddits (texts DESC, subreddit)")
    conn.execute("CREATE INDEX explorer_subreddits_name ON explorer_subreddits USING gin (subreddit gin_trgm_ops)")


@timed
def texts(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_texts, explorer_counts")
    conn.execute("""
        CREATE UNLOGGED TABLE explorer_counts AS
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
        SELECT * FROM counts""")
    conn.execute("ANALYZE explorer_counts")
    conn.execute(f"SET LOCAL max_parallel_workers_per_gather = {SCAN_WORKERS}")
    conn.execute("""
        CREATE TABLE explorer_texts AS
        SELECT t.record_id, t.author, t.subreddit, t.record_type, t.created_utc, b.words, c.claims, c.incohesive, c.outvoted
        FROM explorer_counts c JOIN records t USING (record_id) JOIN bodies b USING (text_sha256)""")
    conn.execute("DROP TABLE explorer_counts")
    conn.execute("ALTER TABLE explorer_texts ADD PRIMARY KEY (record_id)")
    for column in TEXT_SORTS:
        conn.execute(f"CREATE INDEX ON explorer_texts ({column}, record_id)")
    conn.execute("CREATE INDEX explorer_texts_author_trgm ON explorer_texts USING gin (author gin_trgm_ops)")
    conn.execute("CREATE INDEX explorer_texts_subreddit_trgm ON explorer_texts USING gin (subreddit gin_trgm_ops)")


@timed
def totals(conn):
    conn.execute("DROP TABLE IF EXISTS explorer_totals")
    conn.execute("""
        CREATE TABLE explorer_totals AS
        SELECT (SELECT count(*) FROM explorer_authors) AS authors, (SELECT count(*) FROM explorer_texts) AS texts,
               (SELECT count(*) FROM explorer_texts WHERE record_type = 'post') AS posts, count(*) AS subreddits, sum(texts) AS records,
               min(first_utc) AS first_utc, max(last_utc) AS last_utc, (SELECT run_id FROM consolidation) AS run_id
        FROM explorer_subreddits""")


@timed
def suspects(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS suspect_claim_texts (
        record_id text NOT NULL, attribute text NOT NULL, value text NOT NULL, flagged_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (record_id, attribute, value))""")


@timed
def prepare():
    with psycopg.connect(DSN) as conn:
        conn.execute(f"SET maintenance_work_mem = '{INDEX_MEMORY}'")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        activity(conn)
        authors(conn)
        subreddits(conn)
        texts(conn)
        totals(conn)
        suspects(conn)
    vacuum("explorer_activity", "explorer_authors", "explorer_subreddits", "explorer_texts")
