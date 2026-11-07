from . import characters, demographics, fandom, health, life, lifestyle, location, timed, work
from .common import BOT_TEXT, Gated, hedged, prepared
from .literals import build, prime
from .prefilter import Prefilter
from .schema import canonical

SINGLE = frozenset({"age", "gender"})
RULES = [*demographics.RULES, *location.RULES, *life.RULES, *lifestyle.RULES, *work.RULES, *health.RULES, *fandom.RULES]
BOT_SAFE = frozenset(attribute for attribute, *_ in (*demographics.RULES, *work.RULES)) | {"automated_account", "relationship_status", "parental_status"}
PREFILTER = Prefilter([pattern.compiled if isinstance(pattern, Gated) else pattern for _, pattern, *_ in RULES])
build()


def positioned(raw):
    text = prepared(raw)
    lowered = text.lower()
    prime(text, lowered)
    found = {}
    automatic = bool(BOT_TEXT.search(lowered))
    demographics.tags(text, lowered, found)
    for index in sorted(PREFILTER.flagged(lowered)):
        attribute, pattern, value, hedge = RULES[index]
        if automatic and attribute not in BOT_SAFE:
            continue
        for match in pattern.finditer(lowered):
            if (stated := value(match)) is not None and not hedged(lowered, match.start(), match.end(), hedge):
                found.setdefault((attribute, stated), match.start())
    fandom.favorites(text, found)
    fandom.fandom(text, found)
    fandom.adjacent(text, found)
    found = {key: position for key, position in found.items() if key[0] != "character"}
    characters.characters(text, found)
    if not automatic:
        health.ailments(lowered, found)
    location.places(text, lowered, found)
    if ("relationship_status", "married") in found and not any(attribute == "living_with" for attribute, _ in found):
        found[("living_with", "partner or family")] = found[("relationship_status", "married")]
    earliest = {}
    for (attribute, value), position in sorted(found.items(), key=lambda item: item[1]):
        if attribute in SINGLE:
            earliest.setdefault(attribute, value)
    picks = {}
    for (attribute, value), position in found.items():
        if (attribute not in SINGLE or earliest[attribute] == value) and (pair := canonical(attribute, value)):
            picks.setdefault(pair, position)
    return picks


@timed
def extract(texts):
    return {index: set(picks) for index, raw in enumerate(texts) if (picks := positioned(raw))}
