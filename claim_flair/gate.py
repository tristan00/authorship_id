from collections import defaultdict
from functools import lru_cache

from claim_extraction.schema import FAN_FIELDS, FIELD_TYPE

from . import LOG
from .config import GATE_COMPARISONS, GATE_SKILL, WIDE

GATE = """
DROP TABLE IF EXISTS flair_gate;
CREATE TABLE flair_gate (subreddit text NOT NULL, flair text, field claim_field NOT NULL, comparisons integer NOT NULL, agreement real NOT NULL, chance real NOT NULL, skill real NOT NULL, kept boolean NOT NULL);
"""


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
        if field in FAN_FIELDS:
            continue
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
    conn.execute(FIELD_TYPE)
    conn.execute(GATE)
    with conn.cursor().copy("COPY flair_gate FROM STDIN") as copy:
        for row in rows_out:
            copy.write_row(row)
    conn.commit()
    LOG.info("flair gate scopes=%d blocked=%d blocked_subreddit_fields=%d", len(rows_out), len(blocked), sum(item[1] is None for item in blocked))
    return blocked


def blocked_scopes(conn):
    return {(subreddit, flair, field) for subreddit, flair, field in conn.execute("SELECT subreddit, flair, field FROM flair_gate WHERE NOT kept")}
