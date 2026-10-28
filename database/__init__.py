import logging
from datetime import datetime, timezone

from reddit_dumps import timed

from .config import DATA, DSN, DUMPS, LOGS, NOT_PEOPLE, PG, PORT, SCAN_WORKERS

MONTH = "to_char(to_timestamp(created_utc) AT TIME ZONE 'UTC', 'YYYY-MM')"
LOG = logging.getLogger("database")


def bounds(month):
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    end = start.replace(year=start.year + start.month // 12, month=start.month % 12 + 1)
    return int(start.timestamp()), int(end.timestamp())


__all__ = ["DATA", "DSN", "DUMPS", "LOG", "LOGS", "MONTH", "NOT_PEOPLE", "PG", "PORT", "SCAN_WORKERS", "bounds", "timed"]
