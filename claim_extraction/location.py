import re

from .common import FOR, I, SELF_HEDGE, TAG, TAGGED, clause, fixed, hedged, question, rule
from .places import CODES, DEMONYMS, MORE_DEMONYMS, PLACES

NATIONS = {**DEMONYMS, **MORE_DEMONYMS}
STATES = {code.lower(): name for code, name in CODES.items()}
LOOKUP = {**{code: PLACES[name] for code, name in STATES.items()}, **PLACES}
LANGUAGES = frozenset("english spanish french german italian portuguese dutch swedish norwegian danish finnish polish czech slovak hungarian romanian bulgarian greek croatian serbian "
                      "russian ukrainian turkish arabic hebrew persian farsi hindi urdu bengali punjabi tamil telugu marathi gujarati malayalam kannada chinese mandarin cantonese japanese "
                      "korean vietnamese thai tagalog filipino indonesian malay swahili afrikaans catalan basque welsh irish icelandic estonian latvian lithuanian albanian".split())
LANGUAGE_NAMES = {"farsi": "persian", "mandarin": "chinese", "filipino": "tagalog"}
NAMES = "|".join(sorted(map(re.escape, LOOKUP), key=len, reverse=True))
PLACE = rf"(?:the )?({NAMES})(?![\w-])"
NATION = "|".join(sorted(map(re.escape, NATIONS), key=len, reverse=True))
HEDGE = re.compile(r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|wants to|trying to|going to|gonna|might|maybe|should|could|plan to|planning to|"
                   r"thinking (?:about|of)|considering|used to|not|never|no longer|anymore|when i was|back when|before)\b|n't\b")
ADVERB = r"(?:(?:currently|now|still|also|just|actually|already|really|basically|technically|originally|both|all)\s+)*"
LIVE = rf"\b(?:i|we|and|but|me and my \w+|my (?:wife|husband|partner|family|girlfriend|boyfriend|fiance|fiancee) and i)\s+{ADVERB}(?:live|reside|stay|'m living|am living|'re living|are living|'ve been living|have been living|'ve lived|have lived|'m based|am based|'re based|'m located|am located|moved|relocated|just moved|recently moved)\s+{ADVERB}(?:here\s+)?(?:in|near|outside(?: of)?|around|to)\s+{PLACE}"
BEING = rf"\b(?:i'm|im|i am|we're|we are|i\s+{ADVERB}(?:am|'m)|(?:currently|now) living)\s+{ADVERB}(?:in|near|outside(?: of)?|based in|located in|living in|here in)\s+{PLACE}(?!\s+(?:for|on|until|till|next|this|last|right now)\b)"
HERE = rf"\bhere in {PLACE}|\b(?:live|living|lives|life) (?:here )?in {PLACE}(?= too| as well)|(?:^|[\n.!?] *)(?:also |fellow )?{PLACE},? here\b"
NATIVE = rf"\b(?:i'm|im|i am|as)\s+an?\s+{ADVERB}(?:{PLACE}) (?:native|local|resident)\b|\b(?:i'm|im|i am) {ADVERB}(?:a )?native (?:of|to) {PLACE}"
FROM = rf"\b(?:i'm|im|i am|we're|we are|i come|we come|i'm originally|im originally|i am originally|originally)\s+{ADVERB}from\s+{PLACE}"
ORIGIN = rf"\b(?:i|we|who)\s+{ADVERB}(?:grew up|was raised|were raised|was born|were born|got raised)\s+(?:and raised\s+)?(?:in|on|near|outside(?: of)?)\s+{PLACE}|\bborn and raised (?:in|on) {PLACE}|(?:^|[\n.!?] *)(?:grew up|born|raised) in {PLACE}|\b{PLACE}[- ]born\b|\bmy (?:hometown|home town|home country|homeland) (?:is|was) {PLACE}"
TITLE = rf"(?<![\w-])(?:{FOR}|{TAG}|\[\d{{2}}\]\s*\[[mf]\]|\b[mft]4[mfatr]\w*)"


RULES = [
    rule("nationality", rf"\b{I} (?:an? |also |proudly |a proud |a born and raised )?({NATION})(?: citizen| national)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|too|myself|citizen|national|here|living|who|born|by|from|in|as|lol|haha|though|btw)\b)[a-z])", lambda match: NATIONS.get(match.group(1))),
    rule("nationality", rf"\bas (?:an?|another|a fellow) ({NATION})(?:[- ]born)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|myself|citizen|national|person|man|woman|guy|girl|dude|male|female|living|who|born|raised|here|in|from|i|we|it|there|that|by|expat|immigrant|veteran|mom|mother|dad|father|parent|voter|taxpayer|kid|child|adult|student|resident|native|lol)\b)[a-z])", lambda match: NATIONS.get(match.group(1))),
    rule("native_language", r"\b(?:my )?(?:first|native|mother) (?:language|tongue) is (\w+)\b|\b(\w+) is my (?:first|native|mother) (?:language|tongue)\b|\b(?:i'm|im|i am|as) an? native (\w+) speaker\b|\bnative (\w+) speaker here\b",
         lambda match: (lambda word: LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None)(next(filter(None, match.groups())))),
    rule("native_language", r"\benglish (?:is not|isn't|is no|ain't|isnt) my (?:native|first|mother|main) (?:language|tongue)\b|\b(?:i'm|im|i am) not (?:a )?native (?:english )?speaker\b|\bnon[- ]native (?:english )?speaker\b|\bmy english (?:is|isn't) (?:not )?(?:bad|good|great|perfect)\b(?=.{0,40}(?:sorry|excuse|forgive|native))", fixed("not english"), TAGGED),
    rule("native_language", r"\b(\w+) is the only language i (?:speak|know)\b|\bas (?:a )?native (\w+ )?speakers?\b", lambda match: (lambda word: (LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None) if word else "english")((match.group(1) or (match.group(2) or "").strip())), SELF_HEDGE),
]


def doubtful(lowered, start, end):
    return bool(HEDGE.search(lowered, max(clause(lowered, start), start - 30), start)) or question(lowered, end)


def places(text, lowered, found):
    stated = {}
    for pattern in (LIVE, BEING, NATIVE):
        for match in re.finditer(pattern, lowered):
            name = next(filter(None, match.groups()))
            if not doubtful(lowered, match.start(), match.end()) and genuine(name, match, text):
                stated.setdefault(name, match.end())
    for match in re.finditer(HERE, lowered):
        name = next(filter(None, match.groups()))
        if not question(lowered, match.end()) and genuine(name, match, text):
            stated.setdefault(name, match.end())
    for match in re.finditer(FROM, lowered):
        name = match.group(1)
        if not doubtful(lowered, match.start(), match.end()) and genuine(name, match, text):
            placed("origin", name, lowered, match.end(), text, found)
            if LOOKUP[name][0] == "country":
                found.setdefault(("nationality", LOOKUP[name][3]), match.start())
            if not stated:
                stated.setdefault(name, match.end())
    for match in re.finditer(ORIGIN, lowered):
        name = next(filter(None, match.groups()))
        if not doubtful(lowered, match.start(), match.end()) and genuine(name, match, text):
            placed("origin", name, lowered, match.end(), text, found)
    for match in re.finditer(rf"\b({NATION})[- ]born\b", lowered):
        found.setdefault(("origin_country", NATIONS[match.group(1)]), match.start())
        found.setdefault(("nationality", NATIONS[match.group(1)]), match.start())
    for match in re.finditer(rf"(?:^|[.!?,;(] *)({NATION}) here\b", lowered):
        found.setdefault(("nationality", NATIONS[match.group(1)]), match.start())
        found.setdefault(("residence_country", NATIONS[match.group(1)]), match.start())
    for match in re.finditer(rf"(?<!far )(?<!away )(?<!different )(?<!apart )(?<!miles )(?<!flight )(?<!flights )(?<!imported )(?<!shipped )\bfrom {PLACE}", lowered):
        if LOOKUP[match.group(1)][0] == "country" and re.search(r"\b(?:i|i'm|im|me|my|we|we're|us|our)\b", lowered[clause(lowered, match.start()):match.start()]) and not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            found.setdefault(("origin_country", LOOKUP[match.group(1)][3]), match.end())
            found.setdefault(("nationality", LOOKUP[match.group(1)][3]), match.end())
    for match in re.finditer(rf"{PLACE}[ -]based\b|{PLACE} (?:area|resident|local)\b|\b(?:my city|my town|my hometown)[\s.,:(-]+(?:is |of )?{PLACE}", lowered):
        kind, value, region, _ = LOOKUP[name := next(filter(None, match.groups()))]
        if kind == "city" and genuine(name, match, text):
            found.setdefault(("residence_city", value), match.end())
            if region:
                found.setdefault(("residence_region", region), match.end())
    titled(text, lowered, stated)
    for match in re.finditer(rf"#({NAMES})(?![\w-])", lowered):
        if genuine(match.group(1), match, text):
            stated.setdefault(match.group(1), match.end())
    for name, end in stated.items():
        placed("residence", name, lowered, end, text, found)


def titled(text, lowered, stated):
    first = lowered.split("\n", 1)[0]
    if re.search(TITLE, first):
        for match in re.finditer(rf"(?<![\w-]){PLACE}", first):
            name = match.group(1)
            if text[match.start(1)].isupper() and name in PLACES or name in ("uk", "usa", "nyc"):
                stated.setdefault(name, match.end())
    for match in re.finditer(rf"(?<![\w-])(?:\d{{2}}\s?[mf]|[mf]\s?\d{{2}}|[mft]4[mfatr]\w*)\s+(?:in|from|near|around)\s+{PLACE}", lowered):
        if genuine(match.group(1), match, text):
            stated.setdefault(match.group(1), match.end())


def genuine(name, match, text):
    if name in STATES and name not in PLACES:
        start = next(match.start(index) for index, value in enumerate(match.groups(), 1) if value == name)
        return text[start:start + len(name)].isupper()
    return True


def placed(prefix, name, lowered, end, text, found):
    kind, value, region, country = LOOKUP[name]
    if kind == "city":
        found.setdefault((f"{prefix}_city", value), end)
        if not region and (code := re.match(r",?\s*([A-Z]{2})\b", text[end:end + 5])) and code.group(1) in CODES:
            region = CODES[code.group(1)]
    if kind in ("city", "region") and region and country != "united kingdom":
        found.setdefault((f"{prefix}_region", region), end)
    found.setdefault((f"{prefix}_country", country), end)
