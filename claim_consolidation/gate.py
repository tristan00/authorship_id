from collections import Counter, defaultdict
from functools import lru_cache

from . import LOG, timed
from .config import GATE_COMPARISONS, GATE_SKILL, WIDE


def near(attribute, left, right):
    if attribute not in WIDE:
        return left == right
    kind, amount = WIDE[attribute]
    left, right = float(left), float(right)
    return abs(left - right) <= (amount if kind == "absolute" else amount * max(left, right))


@timed
def blocked(stats, base):
    totals = {attribute: sum(counted.values()) for attribute, counted in base.items()}

    @lru_cache(maxsize=None)
    def chance(attribute, value):
        return sum(count for other, count in base[attribute].items() if near(attribute, value, other)) / totals[attribute]

    scopes = defaultdict(lambda: [0, 0, 0.])
    for (subreddit, attribute, value), (count, hits) in stats.items():
        entry = scopes[subreddit, attribute]
        entry[0], entry[1], entry[2] = entry[0] + count, entry[1] + hits, entry[2] + chance(attribute, value) * count
    found = set()
    for scope, (count, hits, expected) in scopes.items():
        random = expected / count
        if count >= GATE_COMPARISONS and (hits / count - random) / max(1 - random, 1e-6) < GATE_SKILL:
            found.add(scope)
    LOG.info("flair gate scopes=%d judged=%d blocked=%d", len(scopes), sum(entry[0] >= GATE_COMPARISONS for entry in scopes.values()), len(found))
    return found


def tallied(pairs, decided, stats, base):
    for attribute, value in decided.items():
        base[attribute][value] += 1
    for subreddit, attribute, stated, written in pairs:
        entry = stats.setdefault((subreddit, attribute, stated), [0, 0])
        entry[0] += 1
        entry[1] += near(attribute, stated, written)


def merged(results):
    stats, base = {}, defaultdict(Counter)
    for found, counted in results:
        for key, (count, hits) in found.items():
            entry = stats.setdefault(key, [0, 0])
            entry[0] += count
            entry[1] += hits
        for attribute, values in counted.items():
            base[attribute].update(values)
    return stats, base
