import json
from pathlib import Path

import psycopg

from database import DSN

from . import LOG, timed

FLAIRS = Path(__file__).with_name("flairs.json")
SCHEMA = """
DROP TABLE IF EXISTS flair_claims;
CREATE TABLE flair_claims (
    subreddit text NOT NULL,
    flair text NOT NULL,
    field text NOT NULL,
    value text NOT NULL,
    PRIMARY KEY (subreddit, flair, field)
);
"""


@timed
def load():
    entries = json.loads(FLAIRS.read_text(encoding="utf-8"))
    with psycopg.connect(DSN) as conn:
        conn.execute(SCHEMA)
        with conn.cursor().copy("COPY flair_claims (subreddit, flair, field, value) FROM STDIN") as copy:
            for entry in entries:
                copy.write_row((entry["subreddit"], entry["flair"], entry["field"], entry["value"]))
        conn.execute("ANALYZE flair_claims")
    LOG.info("loaded flair_claims rows=%s subreddits=%s", len(entries), len({entry["subreddit"] for entry in entries}))
