import json
import math
from collections import defaultdict

from .config import BOT_PROBABILITY, BOT_SHARE, BOT_TEXTS, FLAIR_STRENGTH, NUMERIC, SHARE, THRESHOLDS, TOLERANCE
from .schema import BOT


def needs():
    return json.loads(THRESHOLDS.read_text(encoding="utf-8"))


def close(attribute, left, right):
    kind, amount = TOLERANCE[attribute]
    left, right = float(left), float(right)
    return abs(left - right) <= (amount if kind == "absolute" else amount * max(left, right))


def agree(attribute, left, right):
    return close(attribute, left, right) if attribute in TOLERANCE else left == right


def strength(probability):
    return -math.log(1 - min(probability, .999))


def flair_strength(need):
    return max(need, FLAIR_STRENGTH)


def plausible(attribute, value):
    if attribute not in NUMERIC:
        return True
    low, high = NUMERIC[attribute]
    return low <= float(value) <= high


def tally(attribute, mentions):
    support = defaultdict(float)
    for value, amount in mentions:
        if plausible(attribute, value):
            support[value] += amount
    if not support:
        return None
    scores = {value: sum(amount for other, amount in support.items() if close(attribute, value, other)) for value in support} if attribute in TOLERANCE else support
    best = max(sorted(scores), key=lambda value: (scores[value], support[value]))
    return best, scores[best], scores[best] / sum(support.values()), support


def decide(attribute, mentions, need):
    found = tally(attribute, mentions)
    if found is None or found[1] < need or found[2] <= SHARE:
        return None
    return found


def automated(texts, flagged):
    return len(flagged) >= BOT_TEXTS and len(flagged) >= BOT_SHARE * len(texts)


def distinct(rows):
    seen = set()
    for source, key, subreddit, field, value, probability, digest in rows:
        identity = digest or key
        if (identity, field, value) not in seen:
            seen.add((identity, field, value))
            yield source, key, subreddit, field, value, probability, identity


def consolidate(rows, required, blocked):
    mentions, texts, flagged = defaultdict(list), set(), set()
    for source, key, subreddit, field, value, probability, identity in distinct(rows):
        if source == "flair":
            flair = key.partition("/")[2]
            if (subreddit, None, field) not in blocked and (subreddit, flair, field) not in blocked:
                mentions[field].append((value, flair_strength(required[field])))
            continue
        texts.add(identity)
        if field == BOT:
            if probability >= BOT_PROBABILITY:
                flagged.add(identity)
        else:
            mentions[field].append((value, strength(probability)))
    if automated(texts, flagged):
        return {}
    decided = {}
    for field, entries in mentions.items():
        if found := decide(field, entries, required[field]):
            decided[field] = found
    return decided


def audit(rows, required):
    mentions, flairs = defaultdict(list), set()
    for source, key, subreddit, field, value, probability, _ in distinct(rows):
        if source == "flair":
            flairs.add((subreddit, key.partition("/")[2], field, value))
        elif field != BOT:
            mentions[field].append((value, strength(probability)))
    decided = {field: found[0] for field, entries in mentions.items() if (found := decide(field, entries, required[field]))}
    return decided, [(subreddit, flair, field, value, decided[field]) for subreddit, flair, field, value in flairs if field in decided]
