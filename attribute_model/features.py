import time

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from author_encoder.store import EXCLUDED, parts, span
from database import client

from . import LOG, timed
from .config import SUBREDDIT_AUTHORS, SUBREDDITS_PER_AUTHOR

HOURS = 24
WEEKDAYS = 7
ACTIVITY = HOURS + WEEKDAYS + 2
TABLE = ("CREATE TABLE author_subreddits_next (author String CODEC(ZSTD(1)), subreddits Array(String) CODEC(ZSTD(1)), counts Array(UInt32) CODEC(ZSTD(1)), "
         "hours Array(UInt32) CODEC(ZSTD(1)), weekdays Array(UInt32) CODEC(ZSTD(1)), posts UInt32 CODEC(ZSTD(1))) ENGINE = MergeTree ORDER BY author")
FILL = ("INSERT INTO author_subreddits_next SELECT author, arrayMap(pair -> pair.1, picked), arrayMap(pair -> pair.2, picked), hours, weekdays, posts FROM "
        f"(SELECT author, arraySlice(arraySort(pair -> (-pair.2, pair.1), groupArray((subreddit, toUInt32(texts)))), 1, {SUBREDDITS_PER_AUTHOR}) AS picked FROM "
        f"(SELECT author, subreddit, count() AS texts FROM records WHERE {{where}} AND author NOT IN {EXCLUDED} GROUP BY author, subreddit) GROUP BY author) AS s INNER JOIN "
        f"(SELECT author, sumForEach(arrayMap(h -> toUInt32(toHour(created_utc) = h), range({HOURS}))) AS hours, "
        f"sumForEach(arrayMap(d -> toUInt32(toDayOfWeek(created_utc) = d), range(1, {WEEKDAYS + 1}))) AS weekdays, toUInt32(countIf(record_type = 'post')) AS posts "
        f"FROM records WHERE {{where}} AND author NOT IN {EXCLUDED} GROUP BY author) AS a USING author")


@timed
def build():
    db = client()
    ranges = parts(db)
    db.command("DROP TABLE IF EXISTS author_subreddits_next")
    db.command(TABLE)
    started, authors = time.perf_counter(), 0
    for part, (low, high) in enumerate(ranges, 1):
        where, parameters = span(low, high)
        authors += db.command(FILL.format(where=where), parameters=parameters).written_rows
        if part % 32 == 0:
            elapsed = time.perf_counter() - started
            LOG.info("subreddits parts=%d/%d authors=%d eta_minutes=%.1f", part, len(ranges), authors, elapsed / part * (len(ranges) - part) / 60)
    db.command("CREATE TABLE IF NOT EXISTS author_subreddits AS author_subreddits_next")
    db.command("EXCHANGE TABLES author_subreddits_next AND author_subreddits")
    db.command("DROP TABLE author_subreddits_next")
    return {"author_parts": len(ranges), "authors": authors}


def vocabulary(names):
    counted = pc.value_counts(pc.list_flatten(names)).to_pylist()
    return [item["values"] for item in sorted(counted, key=lambda item: (-item["counts"], item["values"])) if item["counts"] >= SUBREDDIT_AUTHORS]


def bags(names, counts, known):
    lengths = pc.list_value_length(names).to_numpy(zero_copy_only=False)
    parent = np.repeat(np.arange(len(names)), lengths)
    slot = np.arange(len(parent)) - np.repeat(np.cumsum(lengths) - lengths, lengths)
    found = pc.fill_null(pc.index_in(pc.list_flatten(names), value_set=known), -1).to_numpy()
    seen = found >= 0
    ids = np.zeros((len(names), SUBREDDITS_PER_AUTHOR), dtype=np.int32)
    weights = np.zeros((len(names), SUBREDDITS_PER_AUTHOR), dtype=np.float16)
    ids[parent[seen], slot[seen]] = found[seen] + 1
    weights[parent[seen], slot[seen]] = np.log1p(pc.list_flatten(counts).to_numpy()[seen])
    return ids, weights


def matrix(values, width):
    return pc.list_flatten(values).to_numpy(zero_copy_only=False).reshape(-1, width).astype(np.float32)


def activity(hours, weekdays, posts):
    hours, weekdays = matrix(hours, HOURS), matrix(weekdays, WEEKDAYS)
    total = hours.sum(1, keepdims=True)
    if (total < 1).any():
        raise ValueError("Every author needs at least one counted text")
    return np.hstack([hours / total, weekdays / total, np.log1p(total), np.asarray(posts, dtype=np.float32)[:, None] / total])
