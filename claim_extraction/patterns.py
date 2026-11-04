from . import characters, demographics, fandom, health, life, lifestyle, location, timed, work
from .common import BOT_TEXT, hedged, prepared
from .schema import canonical

SINGLE = frozenset({"age", "gender"})
RULES = [*demographics.RULES, *location.RULES, *life.RULES, *lifestyle.RULES, *work.RULES, *health.RULES, *fandom.RULES]
DEMOGRAPHIC = frozenset(attribute for attribute, *_ in demographics.RULES) | {"automated_account"}


def positioned(raw):
    text = prepared(raw)
    lowered = text.lower()
    found = {}
    automatic = bool(BOT_TEXT.search(lowered))
    demographics.tags(text, lowered, found)
    for attribute, pattern, value, hedge in RULES:
        if automatic and attribute not in DEMOGRAPHIC:
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
