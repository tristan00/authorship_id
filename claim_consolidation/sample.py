import hashlib
import json
import random
from collections import Counter, defaultdict

import psycopg

from claim_extraction.config import ANNOTATIONS
from claim_extraction.labels import split
from database import DSN, NOT_PEOPLE, SCAN_WORKERS, bounds

from . import LOG, timed
from .config import CLAIM_LINES, SAMPLE_SEED
from .consolidate import EVIDENCE

MONTH = "AND t.created_utc >= %(low)s AND t.created_utc < %(high)s"
ELIGIBLE = f"SELECT author FROM ({EVIDENCE.format(join='', where=MONTH)}) evidence GROUP BY author HAVING count(*) >= %(least)s"
CLAIMS = f"SELECT author, source, subreddit, field, value FROM ({EVIDENCE.format(join='JOIN sampled s ON s.author = t.author', where=MONTH)}) evidence"


def lines(author, claims):
    found = [f"r/{subreddit} {source} {field}: {value}" for source, subreddit, field, value in claims]
    random.Random(int.from_bytes(hashlib.sha256(author.encode("utf-8")).digest()[:8], "big")).shuffle(found)
    return found[:CLAIM_LINES]


@timed
def eligible(conn, month, least):
    low, high = bounds(month)
    conn.execute(f"SET max_parallel_workers_per_gather = {SCAN_WORKERS}")
    authors = [author for author, in conn.execute(ELIGIBLE, {"people": NOT_PEOPLE, "low": low, "high": high, "least": least})]
    LOG.info("eligible authors=%s min_claims=%s", len(authors), least)
    return authors


@timed
def claims(conn, authors, month):
    conn.execute("CREATE TEMP TABLE sampled (author text PRIMARY KEY) ON COMMIT DROP")
    with conn.cursor().copy("COPY sampled (author) FROM STDIN") as copy:
        for author in authors:
            copy.write_row((author,))
    found, (low, high) = defaultdict(list), bounds(month)
    for author, *claim in conn.execute(CLAIMS, {"people": NOT_PEOPLE, "low": low, "high": high}):
        found[author].append(claim)
    LOG.info("claims authors=%s claims=%s", len(authors), sum(map(len, found.values())))
    return {author: sorted(found[author]) for author in authors}


@timed
def sample(month, dataset, least, limit):
    taken = {json.loads(line)["id"] for path in (ANNOTATIONS / month).glob("*/records.jsonl") for line in open(path, encoding="utf-8")}
    with psycopg.connect(DSN) as conn:
        pool = sorted(set(eligible(conn, month, least)) - taken)
        authors = random.Random(SAMPLE_SEED).sample(pool, min(limit, len(pool)))
        evidence = claims(conn, authors, month)
    root = ANNOTATIONS / month / dataset
    root.mkdir(parents=True)
    with open(root / "records.jsonl", "w", encoding="utf-8") as records, open(root / "claims.jsonl", "w", encoding="utf-8") as claimed:
        for author in authors:
            records.write(json.dumps({"id": author, "text": "\n".join(lines(author, evidence[author]))}, ensure_ascii=False) + "\n")
            claimed.write(json.dumps({"id": author, "claims": evidence[author]}, ensure_ascii=False) + "\n")
    lengths = [len(evidence[author]) for author in authors]
    LOG.info("sampled dataset=%s pool=%s authors=%s excluded=%s splits=%s mean_claims=%.1f capped=%s", dataset, len(pool), len(authors), len(taken),
             dict(Counter(split(author) for author in authors)), sum(lengths) / len(lengths), sum(length > CLAIM_LINES for length in lengths))
