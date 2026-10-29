import json
from collections import Counter, defaultdict
from functools import cache

from claim_extraction.normalize import REGIONS

from .config import STRENGTHS

YEAR = 2026
ADULT = 18
OLDER = 25
GAP = 10
NUMERIC = ("age", "birth_year", "height", "weight", "income")
HIGHEST = ("height", "weight", "income")
PLACES = (("residence_country", "residence_state"), ("origin_country", "origin_state"))
MATCHES = (("nationality", "origin_country"), ("origin_country", "nationality"))
IMPLIED = {("sexual_orientation", "lesbian"): ("gender", "female")}


@cache
def strengths():
    return json.loads(STRENGTHS.read_text(encoding="utf-8"))


def leaders(counts):
    top = max(counts.values())
    return sorted(value for value, count in counts.items() if count == top)


def only(values):
    return values[0] if len(values) == 1 else None


def strongest(field, values, sources):
    table, local = strengths()["values"].get(field, {}), strengths()["subreddits"].get(field, {})
    scored = sorted(((sum(local.get(subreddit, {}).get(value, table.get(value, 0.5)) for subreddit in sources[field, value]) / len(sources[field, value]), value)
                     for value in values), reverse=True)
    return scored[0][1] if scored[0][0] > scored[1][0] else None


def born(age, year):
    return abs(YEAR - year - age) <= 1


def age(values, result):
    values = sorted([value for value in values if float(value) >= ADULT] or values, key=float)
    if len(values) == 2:
        low, high = values
        return low if float(low) >= OLDER and float(high) - float(low) >= GAP else high
    return values[len(values) // 2] if len(values) % 2 else None


def birth_year(values, result):
    return only([value for value in values if "age" in result and born(float(result["age"]), int(value))]) if "age" in result else None


def place(country, state, tied, result):
    if country in tied and (region := result.get(state)) and (value := only([item for item in tied[country] if region in REGIONS.get(item, ())])):
        result[country] = value
    if state in tied and (regions := REGIONS.get(result.get(country))) and (value := only([item for item in tied[state] if item in regions])):
        result[state] = value


def consolidate(evidence):
    counts, sources = defaultdict(Counter), defaultdict(set)
    for _, subreddit, field, value in evidence:
        counts[field][value] += 1
        sources[field, value].add(subreddit)
    tied = {field: leaders(found) for field, found in counts.items()}
    result = {field: values[0] for field, values in tied.items() if len(values) == 1}
    tied = {field: values for field, values in tied.items() if len(values) > 1}
    for field, pick in (("age", age), ("birth_year", birth_year)):
        if field in tied and (value := pick(tied[field], result)) is not None:
            result[field] = value
    for country, state in PLACES:
        place(country, state, tied, result)
    for field, other in MATCHES:
        if field in tied and field not in result and (value := only([item for item in tied[field] if item == result.get(other)])):
            result[field] = value
    for (field, value), (target, implied) in IMPLIED.items():
        if result.get(field) == value and implied in tied.get(target, ()) and target not in result:
            result[target] = implied
    for field, values in tied.items():
        if field not in result and field in HIGHEST and len(values) == 2:
            result[field] = max(values, key=float)
        elif field not in result and field not in NUMERIC and (value := strongest(field, values, sources)) is not None:
            result[field] = value
    return result
