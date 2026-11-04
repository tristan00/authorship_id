import atexit
import functools
import logging
import subprocess
from datetime import datetime, timezone

import clickhouse_connect

from reddit_dumps import timed

from .config import BODY_RANGES, DATABASE, DISTRO, DUMPS, LOGS, NO_AUTHOR, PORT

LOG = logging.getLogger("database")


@functools.cache
def keep_alive():
    process = subprocess.Popen(["wsl.exe", "-d", DISTRO, "--", "sleep", "infinity"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    atexit.register(process.kill)
    return process


@functools.cache
def host():
    keep_alive()
    return subprocess.run(["wsl.exe", "-d", DISTRO, "--", "hostname", "-I"], capture_output=True, text=True, check=True).stdout.split()[0]


def client(database=DATABASE, **settings):
    return clickhouse_connect.get_client(host=host(), port=PORT, database=database, settings=settings, send_receive_timeout=86400, query_limit=0)


def bounds(month):
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    end = start.replace(year=start.year + start.month // 12, month=start.month % 12 + 1)
    return int(start.timestamp()), int(end.timestamp())


def sha_ranges(parts=BODY_RANGES):
    edges = [f"unhex('{index * 256 // parts:02x}{'00' * 31}')" for index in range(parts)]
    return [(edges[index], edges[index + 1] if index + 1 < parts else None) for index in range(parts)]


def in_range(column, low, high):
    return f"{column} >= {low}" + (f" AND {column} < {high}" if high else "")


__all__ = ["DATABASE", "DUMPS", "LOG", "LOGS", "NO_AUTHOR", "bounds", "client", "host", "in_range", "keep_alive", "sha_ranges", "timed"]
