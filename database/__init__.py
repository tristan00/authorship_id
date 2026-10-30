import logging
from datetime import datetime, timezone

import psycopg

from reddit_dumps import timed

from .config import DATA, DSN, DUMPS, INDEX_MEMORY, LOGS, NO_AUTHOR, PG, PORT, SCAN_WORKERS

LOG = logging.getLogger("database")


def bounds(month):
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    end = start.replace(year=start.year + start.month // 12, month=start.month % 12 + 1)
    return int(start.timestamp()), int(end.timestamp())


def within(months, column):
    return "(" + " OR ".join(f"({column} >= {start} AND {column} < {end})" for start, end in map(bounds, months)) + ")"


@timed
def vacuum(*tables):
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"VACUUM (ANALYZE) {', '.join(tables)}")


__all__ = ["DATA", "DSN", "DUMPS", "INDEX_MEMORY", "LOG", "LOGS", "NO_AUTHOR", "PG", "PORT", "SCAN_WORKERS", "bounds", "timed", "vacuum", "within"]
