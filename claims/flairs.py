import json
import re
from collections import Counter, defaultdict
from functools import lru_cache

import psycopg

from database import DSN, NO_AUTHOR

from . import LOG, timed
from .annotate import answers, generate, rows
from .config import ANNOTATIONS, COMPASS_SUBREDDIT, FLAIR_ADULT_SHARE, FLAIR_AUTHORS, FLAIR_LENGTH, FLAIR_SHOWN, FLAIR_SUBREDDIT_AUTHORS, FLAIR_VOTERS, GATE_COMPARISONS, GATE_SKILL, TEACHER, WIDE
from .sample import MINOR
from .schema import FLAIR, FLAIR_LINES, FLAIR_SCHEMA, FLAIR_VERIFY, claim_text, flair_attributes, flair_facts

COUNTS = """COPY (SELECT subreddit, flair, count(*) FROM (SELECT DISTINCT subreddit, author_flair_text AS flair, author FROM records
            WHERE author_flair_text <> '' AND author <> ALL(%s)) pairs GROUP BY 1, 2 HAVING count(*) >= %s) TO STDOUT"""
ORDINARY = "SELECT subreddit FROM records WHERE record_type = 'post' AND over_18 IS NOT NULL GROUP BY 1 HAVING avg(over_18::int) < %s"
YOUNG = re.compile(r"\s*1[0-7]\s*")
TABLE = """
DROP TABLE IF EXISTS flair_claims;
CREATE TABLE flair_claims (subreddit text NOT NULL, flair text NOT NULL, field text NOT NULL, value text NOT NULL, PRIMARY KEY (subreddit, flair, field));
"""
GATE = """
DROP TABLE IF EXISTS flair_gate;
CREATE TABLE flair_gate (subreddit text NOT NULL, flair text, field text NOT NULL, comparisons integer NOT NULL, agreement real NOT NULL, chance real NOT NULL, skill real NOT NULL, kept boolean NOT NULL);
"""


@timed
def candidates(minimum):
    written = blocked = 0
    with psycopg.connect(DSN) as conn, open(ANNOTATIONS / "flairs.jsonl", "w", encoding="utf-8") as out:
        conn.execute("SET max_parallel_workers_per_gather = 8")
        conn.execute("SET work_mem = '1GB'")
        ordinary = {name for name, in conn.execute(ORDINARY, [FLAIR_ADULT_SHARE])}
        with conn.cursor().copy(COUNTS, [NO_AUTHOR, minimum]) as copy:
            copy.set_types(["text", "text", "int8"])
            for subreddit, flair, authors in copy.rows():
                if len(flair) > FLAIR_LENGTH:
                    continue
                safe = subreddit in ordinary
                if not safe and (MINOR.search(flair) or YOUNG.fullmatch(flair)):
                    blocked += 1
                    continue
                out.write(json.dumps({"id": f"{subreddit}|{flair}", "subreddit": subreddit, "flair": flair, "authors": authors, "ordinary": safe}, ensure_ascii=False) + "\n")
                written += 1
    LOG.info("flair candidates pairs=%d blocked=%d minimum_authors=%d", written, blocked, minimum)


def proposed(model=TEACHER):
    found = answers("flairs", model)
    for row in rows(ANNOTATIONS / "flairs.jsonl"):
        if row["id"] in found:
            for attribute, value in flair_facts(found[row["id"]]).items():
                yield row, attribute, value


def claim_key(row, attribute, value):
    return f"{row['id']}|{attribute}|{value}"


def grouped():
    found = defaultdict(list)
    for row in rows(ANNOTATIONS / "flairs.jsonl"):
        found[row["subreddit"]].append(row)
    return {subreddit: sorted(items, key=lambda row: -row["authors"]) for subreddit, items in sorted(found.items())}


@timed
def schemas(groups):
    records = ANNOTATIONS / "flairs.schema.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as out:
        for subreddit, items in groups.items():
            if sum(row["authors"] for row in items) >= FLAIR_SUBREDDIT_AUTHORS:
                flairs = "\n".join(f"{row['flair']} ({row['authors']} users)" for row in items[:FLAIR_SHOWN])
                out.write(json.dumps({"id": subreddit, "text": FLAIR_SCHEMA.format(subreddit=subreddit, flairs=flairs)}, ensure_ascii=False) + "\n")
    generate(TEACHER, records, "flairs.schema", 60)
    found = {subreddit: flair_attributes(answer) for subreddit, answer in answers("flairs.schema", TEACHER).items()}
    LOG.info("flair schemas subreddits=%d informative=%d attributes=%s", len(found), sum(map(bool, found.values())), Counter(name for names in found.values() for name in names).most_common())
    return found


@timed
def annotate(minimum=FLAIR_AUTHORS):
    if not (ANNOTATIONS / "flairs.jsonl").exists():
        candidates(minimum)
    groups = grouped()
    found = schemas(groups)
    records = ANNOTATIONS / "flairs.prompts.jsonl"
    written = 0
    with open(records, "w", encoding="utf-8") as out:
        for subreddit, items in groups.items():
            if names := found.get(subreddit):
                attributes = "\n".join(FLAIR_LINES[name] for name in names)
                for row in items:
                    out.write(json.dumps({"id": row["id"], "text": FLAIR.format(attributes=attributes, subreddit=subreddit, flair=row["flair"])}, ensure_ascii=False) + "\n")
                    written += 1
    LOG.info("flair value prompts=%d", written)
    generate(TEACHER, records, "flairs", 60)
    records = ANNOTATIONS / "flairs.verify.prompts.jsonl"
    count = 0
    with open(records, "w", encoding="utf-8") as out:
        for row, attribute, value in proposed():
            out.write(json.dumps({"id": claim_key(row, attribute, value), "text": FLAIR_VERIFY.format(subreddit=row["subreddit"], flair=row["flair"], claim=claim_text(attribute, value))}, ensure_ascii=False) + "\n")
            count += 1
    LOG.info("flair proposals=%d", count)
    for model in FLAIR_VOTERS:
        generate(model, records, "flairs.verify", 4)


def confirmed(votes, key):
    ballots = [(table.get(key) or "").strip().upper().startswith("Y") for table in votes]
    return ballots[0] and any(ballots[1:])


@timed
def load():
    votes = [answers("flairs.verify", model) for model in FLAIR_VOTERS]
    kept = {}
    proposals = 0
    for row, attribute, value in proposed():
        proposals += 1
        key = claim_key(row, attribute, value)
        if attribute == "age" and value < 18 and not row["ordinary"]:
            continue
        if attribute == "political_compass" and row["subreddit"] != COMPASS_SUBREDDIT:
            continue
        if attribute == "political_compass" or confirmed(votes, key):
            kept[row["subreddit"], row["flair"], attribute] = value
    with psycopg.connect(DSN) as conn:
        conn.execute(TABLE)
        with conn.cursor().copy("COPY flair_claims (subreddit, flair, field, value) FROM STDIN") as copy:
            for (subreddit, flair, attribute), value in kept.items():
                value = str(int(value)) if isinstance(value, float) else value
                copy.write_row((subreddit, flair, attribute, value))
        conn.execute("ANALYZE flair_claims")
    LOG.info("flair claims proposals=%d confirmed=%d subreddits=%d fields=%s", proposals, len(kept), len({key[0] for key in kept}), Counter(key[2] for key in kept).most_common())


def near(field, left, right):
    if field not in WIDE:
        return left == right
    kind, amount = WIDE[field]
    left, right = float(left), float(right)
    return abs(left - right) <= (amount if kind == "absolute" else amount * max(left, right))


def gate(conn, stats, base):
    totals = {field: sum(counted.values()) for field, counted in base.items()}

    @lru_cache(maxsize=None)
    def chance(field, value):
        return sum(count for other, count in base[field].items() if near(field, value, other)) / totals[field]

    scopes = defaultdict(lambda: [0, 0, 0.])
    for (subreddit, flair, field, value), (count, hits) in stats.items():
        expected = chance(field, value) * count
        for scope in ((subreddit, None, field), (subreddit, flair, field)):
            entry = scopes[scope]
            entry[0], entry[1], entry[2] = entry[0] + count, entry[1] + hits, entry[2] + expected
    blocked, rows_out = set(), []
    for (subreddit, flair, field), (count, hits, expected) in scopes.items():
        if count < GATE_COMPARISONS:
            continue
        agreement, random = hits / count, expected / count
        skill = (agreement - random) / max(1 - random, 1e-6)
        kept = skill >= GATE_SKILL
        rows_out.append((subreddit, flair, field, count, agreement, random, skill, kept))
        if not kept:
            blocked.add((subreddit, flair, field))
    conn.execute(GATE)
    with conn.cursor().copy("COPY flair_gate FROM STDIN") as copy:
        for row in rows_out:
            copy.write_row(row)
    conn.commit()
    LOG.info("flair gate scopes=%d blocked=%d blocked_subreddit_fields=%d", len(rows_out), len(blocked), sum(item[1] is None for item in blocked))
    return blocked


def blocked_scopes(conn):
    return {(subreddit, flair, field) for subreddit, flair, field in conn.execute("SELECT subreddit, flair, field FROM flair_gate WHERE NOT kept")}
