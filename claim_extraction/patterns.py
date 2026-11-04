from . import demographics, fandom, health, life, location, timed, work
from .common import BOT_TEXT, hedged, prepared
from .schema import canonical

SINGLE = frozenset({"age", "gender"})
RULES = [*demographics.RULES, *location.RULES, *life.RULES, *work.RULES, *health.RULES, *fandom.RULES]
DEMOGRAPHIC = frozenset(attribute for attribute, *_ in demographics.RULES) | {"automated_account"}


@timed
def extract(texts):
    result = {}
    for index, raw in enumerate(texts):
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
        if not automatic:
            health.ailments(lowered, found)
        location.places(text, lowered, found)
        if ("relationship_status", "married") in found and not any(attribute == "living_with" for attribute, _ in found):
            found[("living_with", "partner or family")] = found[("relationship_status", "married")]
        earliest = {}
        for (attribute, value), position in sorted(found.items(), key=lambda item: item[1]):
            if attribute in SINGLE:
                earliest.setdefault(attribute, value)
        if facts := {pair for attribute, value in found if (attribute not in SINGLE or earliest[attribute] == value) and (pair := canonical(attribute, value))}:
            result[index] = facts
    return result
