import logging

from reddit_dumps import timed

from .config import DATA, DSN, DUMPS, LOGS, NOT_PEOPLE, PG, PORT, SCAN_WORKERS

MONTH = "to_char(to_timestamp(created_utc) AT TIME ZONE 'UTC', 'YYYY-MM')"
LOG = logging.getLogger("database")

__all__ = ["DATA", "DSN", "DUMPS", "LOG", "LOGS", "MONTH", "NOT_PEOPLE", "PG", "PORT", "SCAN_WORKERS", "timed"]
