import json
import random
import re
from collections import Counter
from multiprocessing import Pool

import psycopg

from database import DSN, NO_AUTHOR

from . import LOG, timed
from .config import ANNOTATIONS, READABLE, SAMPLE_BYTES, SAMPLE_PER_AUTHOR, SAMPLE_READERS

UNIFORM = """COPY (SELECT r.record_id, r.author, r.subreddit, r.record_type, b.text_sha256, b.text
             FROM (SELECT record_id, author, subreddit, record_type, text_sha256 FROM records TABLESAMPLE SYSTEM (%s) REPEATABLE (%s) WHERE text_status = ANY(%s)) r
             JOIN bodies b USING (text_sha256) WHERE octet_length(b.text) <= %s) TO STDOUT"""
BY_AUTHOR = """SELECT r.record_id, r.author, r.subreddit, r.record_type, b.text_sha256, b.text
               FROM records r JOIN bodies b USING (text_sha256) WHERE r.author = ANY(%s) AND r.text_status = ANY(%s) AND octet_length(b.text) BETWEEN 20 AND %s"""
ADULT = "CREATE TABLE IF NOT EXISTS adult_subreddits AS SELECT DISTINCT subreddit FROM records WHERE over_18"
MINORS = "SELECT author FROM author_claims WHERE attribute = 'age' AND value::numeric < 18"
MINOR = re.compile(r"(?<![\d.,$])(?:1[0-7]\s?/?\s?[mf]|[mf]\s?/?\s?1[0-7]|1[0-7]\s?(?:yo|y/o|y\.o|yrs?\b|years?\b|-year)|(?:i'?m|i am|im|age[d:]?)\s*1[0-7])(?![\d.,])", re.I)
GUARD = None


def safety():
    with psycopg.connect(DSN) as conn:
        conn.execute(ADULT)
        conn.commit()
        return {name for name, in conn.execute("SELECT subreddit FROM adult_subreddits")}, {name for name, in conn.execute(MINORS)}


def begin(adult, minors):
    global GUARD
    GUARD = adult, minors


def allowed(row):
    adult, minors = GUARD
    return row[2] not in adult or (row[1] not in minors and not MINOR.search(row[5]))


def read_uniform(job):
    percent, seed = job
    rows = []
    with psycopg.connect(DSN) as conn, conn.cursor().copy(UNIFORM, [percent, seed, list(READABLE), SAMPLE_BYTES]) as copy:
        copy.set_types(["text", "text", "text", "text", "bytea", "text"])
        rows += [row for row in copy.rows() if allowed(row)]
    return rows


def read_authors(chunk):
    with psycopg.connect(DSN) as conn:
        return [row for row in conn.execute(BY_AUTHOR, [chunk, list(READABLE), SAMPLE_BYTES]).fetchall() if allowed(row)]


def write(path, rows):
    with open(path, "w", encoding="utf-8") as stream:
        for record, author, subreddit, kind, digest, text in rows:
            stream.write(json.dumps({"id": bytes(digest).hex(), "record": record, "author": author, "subreddit": subreddit, "record_type": kind, "text": text}, ensure_ascii=False) + "\n")


@timed
def sample(uniform, authors):
    ANNOTATIONS.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(DSN) as conn:
        records = conn.execute("SELECT sum(reltuples)::bigint FROM pg_class c JOIN pg_inherits i ON i.inhrelid = c.oid WHERE i.inhparent = 'records'::regclass").fetchone()[0]
    percent = uniform * 2.2 / records * 100 / SAMPLE_READERS
    rows, seen = [], set()
    with Pool(SAMPLE_READERS, initializer=begin, initargs=safety()) as pool:
        for found in pool.imap_unordered(read_uniform, [(percent, 9000 + index) for index in range(SAMPLE_READERS)]):
            for row in found:
                if bytes(row[4]) not in seen:
                    seen.add(bytes(row[4]))
                    rows.append(row)
        rows.sort(key=lambda row: bytes(row[4]))
        random.Random(1).shuffle(rows)
        write(ANNOTATIONS / "uniform.jsonl", rows[:uniform])
        active = sorted({row[1] for row in rows} - set(NO_AUTHOR))
        random.Random(2).shuffle(active)
        kept, counts, rng = [], Counter(), random.Random(3)
        for found in pool.imap_unordered(read_authors, [active[start:start + 100] for start in range(0, authors, 100)]):
            rng.shuffle(found)
            for row in found:
                if counts[row[1]] < SAMPLE_PER_AUTHOR:
                    counts[row[1]] += 1
                    kept.append(row)
    write(ANNOTATIONS / "authors.jsonl", kept)
    LOG.info("sampled uniform=%d author_texts=%d authors=%d", min(uniform, len(rows)), len(kept), len(counts))
