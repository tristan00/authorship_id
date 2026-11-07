from collections import defaultdict

from claim_extraction.schema import BOT, decomposed, stored_field

from .config import BOT_SHARE, BOT_TEXTS, CHILD_AGE, NOT_A_CHILD, NUMERIC, SHARE, TOLERANCE

FLAIR = "flair"


def close(attribute, left, right):
    kind, amount = TOLERANCE[attribute]
    left, right = float(left), float(right)
    return abs(left - right) <= (amount if kind == "absolute" else amount * max(left, right))


def plausible(attribute, value):
    if attribute not in NUMERIC:
        return True
    low, high = NUMERIC[attribute]
    return low <= float(value) <= high


def tally(attribute, texts):
    support = {value: len(found) for value, found in texts.items() if plausible(attribute, value)}
    if not support:
        return None
    scores = {value: sum(amount for other, amount in support.items() if close(attribute, value, other)) for value in support} if attribute in TOLERANCE else support
    best = max(sorted(scores), key=lambda value: (scores[value], support[value]))
    return best, scores[best], scores[best] / sum(support.values()), support


def plurality(best, support):
    return all(amount < support[best] for value, amount in support.items() if value != best)


def evidence(rows, blocked=frozenset(), flairs=True):
    texts, flagged, found = set(), set(), defaultdict(lambda: defaultdict(set))
    for attribute, value, digest, created, subreddit, source in rows:
        flair = source == FLAIR
        if flair and not flairs:
            continue
        if attribute == BOT:
            if not flair:
                texts.add(digest)
                flagged.add(digest)
            continue
        if not flair:
            texts.add(digest)
        for name, stated in decomposed(stored_field(attribute), value):
            if not (flair and (subreddit, name) in blocked):
                found[name][stated].add(digest)
    return texts, flagged, found


def decide(found, need):
    decided = {}
    for attribute, values in found.items():
        result = tally(attribute, values)
        if result and result[1] >= need and (result[2] > SHARE or plurality(result[0], result[3])):
            decided[attribute] = result
    if "age" in decided and float(decided["age"][0]) < CHILD_AGE and any(field in decided and decided[field][0] in values for field, values in NOT_A_CHILD.items()):
        del decided["age"]
    return decided


def consolidate(rows, need, blocked=frozenset()):
    texts, flagged, found = evidence(rows, blocked)
    if len(flagged) >= BOT_TEXTS and len(flagged) >= BOT_SHARE * len(texts):
        return {}
    return decide(found, need)


def audit(rows, need):
    decided = {attribute: result[0] for attribute, result in decide(evidence(rows, flairs=False)[2], need).items()}
    pairs = {(subreddit, name, stated) for attribute, value, digest, created, subreddit, source in rows if source == FLAIR
             for name, stated in decomposed(stored_field(attribute), value) if name in decided}
    return decided, [(subreddit, name, stated, decided[name]) for subreddit, name, stated in pairs]
