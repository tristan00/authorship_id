import re

from .common import FOR, I, SELF_HEDGE, TAG, TAGGED, fixed, group, hedged, rule
from .places import CODES, DEMONYMS, PLACES

LANGUAGES = frozenset("english spanish french german italian portuguese dutch swedish norwegian danish finnish polish czech slovak hungarian romanian bulgarian greek croatian serbian "
                      "russian ukrainian turkish arabic hebrew persian farsi hindi urdu bengali punjabi tamil telugu marathi gujarati malayalam kannada chinese mandarin cantonese japanese "
                      "korean vietnamese thai tagalog filipino indonesian malay swahili afrikaans catalan basque welsh irish icelandic estonian latvian lithuanian albanian".split())
LANGUAGE_NAMES = {"farsi": "persian", "mandarin": "chinese", "filipino": "tagalog"}
PLACE_NAMES = "|".join(sorted(map(re.escape, PLACES), key=len, reverse=True))
PLACE = rf"(?:the )?({PLACE_NAMES})(?![\w-])"
RESIDE = rf"(?:i live|i've lived|i'?ve been living|i'm living|im living|living|i'm currently living|i reside|i'm based|im based|i am based|based|i'm located|located|i'm currently|i'm|im|i am|we live|we're|we are|i moved|i've moved|i just moved|i relocated|here)\s+(?:currently\s+|now\s+|still\s+|also\s+|just\s+|right\s+)?(?:in|near|outside(?: of)?|around|to)\s+{PLACE}"
ORIGIN = rf"(?:i grew up|i was raised|i was born|born and raised|born|raised|i'm originally from|im originally from|i am originally from|originally from)\s+(?:in\s+)?{PLACE}"
FROM = rf"(?:i'm|im|i am|we're|we are)\s+(?:also\s+)?from\s+{PLACE}"
RULES = [
    rule("nationality", rf"\b{I} (?:a |an |also |half |proudly |a proud )?({'|'.join(map(re.escape, DEMONYMS))})(?: citizen| national)?(?=$|[\s.,!;:)])(?! (?:food|people|culture|company|government|accent|friend|girlfriend|boyfriend|wife|husband|music|movies?|guy|girl|man|woman|stuff|style|tv|teacher|class|course|school|version|player)\b)", group(DEMONYMS)),
    rule("nationality", rf"\bas an? ({'|'.join(map(re.escape, DEMONYMS))})(?: citizen| person| myself| national)?\b(?! (?:company|government|food|man|woman|guy|girl|accent)\b)", group(DEMONYMS)),
    rule("native_language", r"\b(?:my )?(?:first|native|mother) (?:language|tongue) is (\w+)\b|\b(\w+) is my (?:first|native|mother) (?:language|tongue)\b|\b(?:i'm|im|i am|as) an? native (\w+) speaker\b|\bnative (\w+) speaker here\b",
         lambda match: (lambda word: LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None)(next(filter(None, match.groups())))),
    rule("native_language", r"\benglish (?:is not|isn't|is no|ain't|isnt) my (?:native|first|mother|main) (?:language|tongue)\b|\b(?:i'm|im|i am) not (?:a )?native (?:english )?speaker\b|\bnon[- ]native (?:english )?speaker\b|\bmy english (?:is|isn't) (?:not )?(?:bad|good|great|perfect)\b(?=.{0,40}(?:sorry|excuse|forgive|native))", fixed("not english"), TAGGED),
    rule("native_language", r"\b(\w+) is the only language i (?:speak|know)\b|\bas (?:a )?native (\w+ )?speakers?\b", lambda match: (lambda word: (LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None) if word else "english")((match.group(1) or (match.group(2) or "").strip())), SELF_HEDGE),
]


def places(text, lowered, found):
    for pattern, prefixes in ((RESIDE, ("residence",)), (FROM, ("residence", "origin")), (ORIGIN, ("origin",))):
        for match in re.finditer(pattern, lowered):
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for prefix in prefixes:
                    placed(prefix, match.group(1), lowered, match.end(), text, found)
                if pattern is FROM and PLACES[match.group(1)][0] == "country":
                    found.setdefault(("nationality", PLACES[match.group(1)][3]), match.start())
    for match in re.finditer(rf"(?:^|[.!?,;(] *)({'|'.join(map(re.escape, DEMONYMS))}) here\b", lowered):
        found.setdefault(("nationality", DEMONYMS[match.group(1)]), match.start())
    for match in re.finditer(rf"#({PLACE_NAMES})(?![\w-])", lowered):
        placed("residence", match.group(1), lowered, match.end(), text, found)
    first = lowered.split("\n", 1)[0]
    if re.search(FOR, first) or re.search(TAG, first):
        for match in re.finditer(rf"(?<![\w-]){PLACE}", first):
            if text[match.start(1)].isupper() or match.group(1) in ("uk", "usa", "nyc"):
                placed("residence", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(rf"\b(?:as an? |i'm an? |im an? )({'|'.join(map(re.escape, DEMONYMS))}) living in {PLACE}", lowered):
        placed("residence", match.group(2), lowered, match.end(), text, found)
    for match in re.finditer(rf"(?<!far )(?<!away )(?<!different )(?<!apart )(?<!miles )(?<!flight )(?<!flights )(?<!imported )(?<!shipped )\bfrom (?:the )?{PLACE}", lowered):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            placed("residence", match.group(1), lowered, match.end(), text, found)
            if PLACES[match.group(1)][0] == "country":
                placed("origin", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(rf"{PLACE}[ -]based\b|{PLACE} (?:area|resident|local)\b|\b(?:my city|my town|my country|my state|my hometown)[\s.,:(-]+(?:is |of )?{PLACE}", lowered):
        name = match.group(1) or match.group(2) or match.group(3)
        placed("residence", name, lowered, match.end(), text, found)
    for match in re.finditer(r"\bwe(?:'re| are)? (?:all )?(americans|brits|canadians|aussies|australians|kiwis|germans|irish|indians|filipinos|mexicans)\b|\bwe (americans|brits|canadians|aussies|australians|germans|indians|filipinos)\b", lowered):
        country = DEMONYMS[(match.group(1) or match.group(2)).rstrip("s").replace("filipino", "filipino")] if (match.group(1) or match.group(2)).rstrip("s") in DEMONYMS else DEMONYMS.get((match.group(1) or match.group(2))[:-1])
        if country:
            found.setdefault(("residence_country", country), match.start())
            found.setdefault(("nationality", country), match.start())
    if len(text.strip()) <= 80 and re.fullmatch(r"\W*[^\W\d][\w .'()-]*,\s*[^\W\d][\w .'()-]*\W*", text.strip()):
        for match in re.finditer(rf"(?<![\w-]){PLACE}", lowered):
            if text[match.start(1)].isupper() or match.group(1) in ("uk", "usa", "nyc"):
                placed("residence", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+)*,\s*([A-Z]{2})\b(?![a-z])", text):
        if match.group(1) in CODES and (len(text) <= 200 or match.start() < 80):
            found.setdefault(("residence_region", CODES[match.group(1)]), match.start())
            found.setdefault(("residence_country", "united states"), match.start())


def placed(prefix, name, lowered, end, text, found):
    kind, value, region, country = PLACES[name]
    if kind == "city":
        found.setdefault((f"{prefix}_city", value), end)
        if not region and (code := re.match(r",?\s*([A-Z]{2})\b", text[end:end + 5])) and code.group(1) in CODES:
            region = CODES[code.group(1)]
    if kind in ("city", "region") and region:
        found.setdefault((f"{prefix}_region", region), end)
    found.setdefault((f"{prefix}_country", country), end)
