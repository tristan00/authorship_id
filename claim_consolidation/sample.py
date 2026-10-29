import hashlib
import json
import random
from collections import Counter, defaultdict

import psycopg

from claim_extraction.config import ANNOTATIONS
from claim_extraction.labels import split
from database import DSN

from . import LOG, timed
from .config import CLAIM_LINES, SAMPLE_SEED
from .consolidate import PARALLEL

ELIGIBLE = "SELECT author FROM claim_evidence GROUP BY author HAVING count(*) >= %(least)s"
CLAIMS = "SELECT e.author, e.source, e.subreddit, e.field, e.value FROM claim_evidence e JOIN sampled s USING (author)"


def lines(author, claims):
    found = [f"r/{subreddit} {source} {field}: {value}" for source, subreddit, field, value in claims]
    random.Random(int.from_bytes(hashlib.sha256(author.encode("utf-8")).digest()[:8], "big")).shuffle(found)
    return found[:CLAIM_LINES]


@timed
def eligible(conn, least):
    for setting in PARALLEL:
        conn.execute(setting)
    authors = [author for author, in conn.execute(ELIGIBLE, {"least": least})]
    LOG.info("eligible authors=%s min_claims=%s", len(authors), least)
    return authors


@timed
def claims(conn, authors):
    conn.execute("CREATE TEMP TABLE sampled (author text PRIMARY KEY) ON COMMIT DROP")
    with conn.cursor().copy("COPY sampled (author) FROM STDIN") as copy:
        for author in authors:
            copy.write_row((author,))
    found = defaultdict(list)
    for author, *claim in conn.execute(CLAIMS):
        found[author].append(claim)
    LOG.info("claims authors=%s claims=%s", len(authors), sum(map(len, found.values())))
    return {author: sorted(found[author]) for author in authors}


@timed
def sample(month, dataset, least, limit):
    taken = {json.loads(line)["id"] for path in (ANNOTATIONS / month).glob("*/records.jsonl") for line in open(path, encoding="utf-8")}
    with psycopg.connect(DSN) as conn:
        run = conn.execute("SELECT months FROM consolidation").fetchone()
        if run is None or run[0] != [month]:
            raise ValueError(f"claim_evidence covers months {run and run[0]}, not only {month}; consolidate {month} alone before sampling it")
        pool = sorted(set(eligible(conn, least)) - taken)
        authors = random.Random(SAMPLE_SEED).sample(pool, min(limit, len(pool)))
        evidence = claims(conn, authors)
    root = ANNOTATIONS / month / dataset
    root.mkdir(parents=True)
    with open(root / "records.jsonl", "w", encoding="utf-8") as records, open(root / "claims.jsonl", "w", encoding="utf-8") as claimed:
        for author in authors:
            records.write(json.dumps({"id": author, "text": "\n".join(lines(author, evidence[author]))}, ensure_ascii=False) + "\n")
            claimed.write(json.dumps({"id": author, "claims": evidence[author]}, ensure_ascii=False) + "\n")
    lengths = [len(evidence[author]) for author in authors]
    LOG.info("sampled dataset=%s pool=%s authors=%s excluded=%s splits=%s mean_claims=%.1f capped=%s", dataset, len(pool), len(authors), len(taken),
             dict(Counter(split(author) for author in authors)), sum(lengths) / len(lengths), sum(length > CLAIM_LINES for length in lengths))
