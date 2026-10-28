import hashlib
import json
import random
from collections import Counter, defaultdict

import psycopg

from claim_extraction.config import ANNOTATIONS
from claim_extraction.labels import split
from database import DSN, NOT_PEOPLE, SCAN_WORKERS, bounds

from . import LOG, timed
from .config import CLAIM_LINES, MIN_CLAIMS, SAMPLE_SEED

FILTER = "t.author !~* %(people)s AND t.created_utc >= %(low)s AND t.created_utc < %(high)s"
TEXT_CLAIMS = f"SELECT t.author, c.record_id, c.field, c.value FROM text_claims c JOIN texts t USING (record_id) {{join}} WHERE {FILTER}"
FLAIR_CLAIMS = (f"SELECT DISTINCT t.author, t.subreddit, t.author_flair_text, f.field, f.value FROM texts t "
                f"JOIN flair_claims f ON f.subreddit = t.subreddit AND f.flair = t.author_flair_text {{join}} WHERE {FILTER}")
ELIGIBLE = (f"SELECT author FROM (SELECT author FROM ({TEXT_CLAIMS.format(join='')}) text_claims "
            f"UNION ALL SELECT author FROM ({FLAIR_CLAIMS.format(join='')}) flair_claims) claims GROUP BY author HAVING count(*) >= %(least)s")
SAMPLED = "JOIN sampled s ON s.author = t.author"


def block(author, texts, flairs):
    lines = [f"text {field}: {value}" for _, field, value in sorted(texts)] + [f"flair {field}: {value}" for *_, field, value in sorted(flairs)]
    random.Random(int.from_bytes(hashlib.sha256(author.encode("utf-8")).digest()[:8], "big")).shuffle(lines)
    return lines[:CLAIM_LINES], len(lines)


@timed
def eligible(conn, month):
    low, high = bounds(month)
    conn.execute(f"SET max_parallel_workers_per_gather = {SCAN_WORKERS}")
    authors = [author for author, in conn.execute(ELIGIBLE, {"people": NOT_PEOPLE, "low": low, "high": high, "least": MIN_CLAIMS})]
    LOG.info("eligible authors=%s min_claims=%s", len(authors), MIN_CLAIMS)
    return authors


@timed
def claims(conn, authors, month):
    conn.execute("CREATE TEMP TABLE sampled (author text PRIMARY KEY) ON COMMIT DROP")
    with conn.cursor().copy("COPY sampled (author) FROM STDIN") as copy:
        for author in authors:
            copy.write_row((author,))
    texts, flairs, (low, high) = defaultdict(list), defaultdict(list), bounds(month)
    for author, *claim in conn.execute(TEXT_CLAIMS.format(join=SAMPLED), {"people": NOT_PEOPLE, "low": low, "high": high}):
        texts[author].append(claim)
    for author, *claim in conn.execute(FLAIR_CLAIMS.format(join=SAMPLED), {"people": NOT_PEOPLE, "low": low, "high": high}):
        flairs[author].append(claim)
    LOG.info("claims authors=%s text=%s flair=%s", len(authors), sum(map(len, texts.values())), sum(map(len, flairs.values())))
    return texts, flairs


@timed
def sample(month, dataset, count):
    taken = {json.loads(line)["id"] for path in (ANNOTATIONS / month).glob("*/records.jsonl") for line in open(path, encoding="utf-8")}
    with psycopg.connect(DSN) as conn:
        pool = sorted(set(eligible(conn, month)) - taken)
        if len(pool) < count:
            raise ValueError(f"only {len(pool)} eligible authors outside other datasets, {count} wanted")
        authors = random.Random(SAMPLE_SEED).sample(pool, count)
        texts, flairs = claims(conn, authors, month)
    rows, lengths = [], []
    for author in authors:
        lines, total = block(author, texts[author], flairs[author])
        rows.append({"id": author, "text": "\n".join(lines)})
        lengths.append(total)
    (ANNOTATIONS / month / dataset).mkdir(parents=True)
    (ANNOTATIONS / month / dataset / "records.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    LOG.info("sampled dataset=%s authors=%s taken=%s splits=%s mean_claims=%.1f capped=%s", dataset, len(rows), len(taken),
             dict(Counter(split(author) for author in authors)), sum(lengths) / len(lengths), sum(total > CLAIM_LINES for total in lengths))
