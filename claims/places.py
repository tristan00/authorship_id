import json
from collections import Counter

import psycopg

from database import DSN

from . import LOG, timed
from .annotate import generate, next_round, votes
from .config import ANNOTATIONS, PLACE_LEVELS, PLACES_FILE, TEACHER, VERIFIERS
from .schema import CITY_FIELDS, COUNTRY_FIELDS, REGION_FIELDS, renamed

RUN = "places"
CHECK_RUN = "places.check"
FIELDS = dict(zip(PLACE_LEVELS, (COUNTRY_FIELDS, REGION_FIELDS, CITY_FIELDS)))
TEXTS = "SELECT field, value FROM text_claims WHERE field = ANY(%s) GROUP BY 1, 2"
FLAIRS = "SELECT DISTINCT field, value FROM flair_claims WHERE field = ANY(%s)"
PROMPT = """Say where a place named by a Reddit user is. You get the name and whether the user gave it as a country, a region or a city.

Write one line for each real place this name commonly refers to, most likely first, at most three lines, in this format:
country | region | city

country is the full English name of the sovereign country. region is the full English name of the state, province or similar first-level division, or - if the name is a country or the place has no such division. city is the city or town, or - if the name is a region or a country.

If the name is not one real place, for example a continent, a group of countries, a neighborhood type or something that is not a place at all, write only: none

Always write all three parts, separated by |. Examples:
Given as: city, Name: austin. Answer: United States | Texas | Austin
Given as: city, Name: vienna. Answer: Austria | Vienna | Vienna
Given as: region, Name: ontario. Answer: Canada | Ontario | -
Given as: country, Name: germany. Answer: Germany | - | -
Given as: region, Name: new england. Answer: none

Given as: {level}
Name: {name}

Answer:"""
CHECK = """A system claims this place exists: {path}.

Is that a real place, and does the part before each comma lie inside the part after it? Answer with exactly one letter: Y or N."""


def stored():
    level_of = {field: level for level, fields in FIELDS.items() for field in fields}
    found = {level: set() for level in PLACE_LEVELS}
    with psycopg.connect(DSN) as conn:
        written = conn.execute(TEXTS, [list(level_of)]).fetchall()
        flairs = conn.execute(FLAIRS, [list(level_of)]).fetchall()
    for field, value in written + flairs:
        found[level_of[field]].add(value)
    LOG.info("place names %s", {level: len(values) for level, values in found.items()})
    return found, {value for field, value in written if level_of[field] == "country"}


def parsed(answer):
    paths = []
    for line in (answer or "").splitlines():
        parts = [part.strip().strip("*_`\"'").lower() for part in line.split("|")]
        if len(parts) == 1:
            parts += ["-", "-"]
        if len(parts) != 3 or parts[0] in ("", "-", "none"):
            continue
        country = renamed("residence_country", parts[0])
        region = None if parts[1] in ("", "-", "none") else renamed("residence_region", parts[1])
        city = None if parts[2] in ("", "-", "none") else renamed("residence_city", parts[2])
        region = None if region == country else region
        if country and (country, region, city) not in paths:
            paths.append((country, region, city))
    return paths[:3]


def shown(path):
    return ", ".join(part for part in reversed(path) if part)


def confirmed(ballots, key):
    return sum((ballot.get(key) or "").strip().upper().startswith("Y") for ballot in ballots) >= 2


def asked(run, items, tokens, models):
    known = votes(run, models[0])
    fresh = [(key, text) for key, text in items if key not in known]
    LOG.info("places run=%s new=%d", run, len(fresh))
    if fresh:
        name = next_round(run, models[0])
        records = ANNOTATIONS / f"{name}.prompts.jsonl"
        with open(records, "w", encoding="utf-8") as out:
            for key, text in fresh:
                out.write(json.dumps({"id": key, "text": text}, ensure_ascii=False) + "\n")
        for model in models:
            generate(model, records, name, tokens)
    return [votes(run, model) for model in models]


@timed
def annotate():
    found, countries = stored()
    items = [(f"{level}|{name}", PROMPT.format(level=level, name=name)) for level, values in found.items() for name in sorted(values)]
    proposed = {key: parsed(answer) for key, answer in asked(RUN, items, 60, (TEACHER,))[0].items()}
    proposed = {key: [path for path in paths if path[0] in countries] for key, paths in proposed.items()}
    wanted = sorted({shown(path) for key, _ in items for path in proposed.get(key, ())})
    ballots = asked(CHECK_RUN, [(path, CHECK.format(path=path)) for path in wanted], 4, VERIFIERS)
    table = {level: {} for level in PLACE_LEVELS}
    kept = Counter()
    for level, values in found.items():
        for name in values:
            paths = [path for path in proposed.get(f"{level}|{name}", ()) if confirmed(ballots, shown(path))]
            table[level][name] = paths
            kept[level, bool(paths)] += 1
    PLACES_FILE.write_text(json.dumps(table, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    LOG.info("places written %s", sorted(kept.items()))
