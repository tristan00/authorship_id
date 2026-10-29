from collections import Counter, defaultdict

from claim_extraction.normalize import REGIONS

YEAR = 2026
ADULT = 18
GENERATIONS = {"gen alpha": (2013, 2025), "gen z": (1997, 2012), "millennial": (1981, 1996), "gen x": (1965, 1980),
               "baby boomer": (1946, 1964), "silent generation": (1928, 1945)}
HIGHEST = ("height", "weight", "income")
TIERS = {
    "education": (("doctorate",), ("professional degree",), ("master's degree",), ("bachelor's degree",), ("associate degree",),
                  ("some college",), ("high school",), ("less than high school",)),
    "employment_status": (("self-employed",), ("student",), ("employed",), ("retired",), ("homemaker",), ("unemployed",)),
    "relationship_status": (("married", "engaged"), ("in a relationship",), ("single",)),
    "marital_status": (("single",), ("married",), ("divorced",), ("widowed",)),
    "parental_status": (("expecting", "parent"), ("no children",)),
    "gender": (("non-binary",), ("male", "female")),
    "generation": (("millennial",), ("gen z",), ("gen x",), ("baby boomer",)),
    "religion": (("jewish",), ("agnostic", "atheist"), ("christian",), ("muslim",), ("hindu",), ("other religion",), ("no religion",)),
    "sexual_orientation": (("bisexual",), ("queer",), ("lesbian",), ("gay", "asexual"), ("straight",)),
    "race_ethnicity": (("multiracial",),),
}
PLACES = (("residence_country", "residence_state"), ("origin_country", "origin_state"))


def claims(lines):
    for line in lines:
        source, _, claim = line.partition(" ")
        field, _, value = claim.partition(": ")
        yield source, field, value


def leaders(counts):
    top = max(counts.values())
    return sorted(value for value, count in counts.items() if count == top)


def only(values):
    return values[0] if len(values) == 1 else None


def tiered(field, values):
    for tier in TIERS.get(field, ()):
        if found := [value for value in values if value in tier]:
            return only(found)
    return None


def born(age, years):
    return any(abs(YEAR - year - age) <= 1 for year in years)


def age(values, result):
    ages = [float(value) for value in values]
    if (year := result.get("birth_year")) and (match := [value for value, number in zip(values, ages) if born(number, [int(year)])]):
        if len(match) == 1:
            return match[0]
    if (span := GENERATIONS.get(result.get("generation"))) and (match := [value for value in values if span[0] - 1 <= YEAR - float(value) <= span[1] + 1]):
        if len(match) == 1:
            return match[0]
        values = match
    values = [value for value in values if float(value) >= ADULT] or values
    return max(values, key=float) if len(values) <= 2 else None


def birth_year(values, result):
    return only([value for value in values if "age" in result and born(float(result["age"]), [int(value)])])


def generation(values, result):
    years = [int(result["birth_year"])] if "birth_year" in result else [YEAR - int(float(result["age"]))] if "age" in result else []
    match = [value for value in values if value in GENERATIONS and any(GENERATIONS[value][0] - 1 <= year <= GENERATIONS[value][1] + 1 for year in years)]
    return only(match) if match else tiered("generation", values)


def place(country, state, tied, result):
    if country in tied and (region := result.get(state)) and (value := only([item for item in tied[country] if region in REGIONS.get(item, ())])):
        result[country] = value
    if state in tied and (regions := REGIONS.get(result.get(country))) and (value := only([item for item in tied[state] if item in regions])):
        result[state] = value


def consolidate(evidence):
    counts = defaultdict(Counter)
    for _, field, value in evidence:
        counts[field][value] += 1
    tied = {field: leaders(found) for field, found in counts.items()}
    result = {field: values[0] for field, values in tied.items() if len(values) == 1}
    tied = {field: values for field, values in tied.items() if len(values) > 1}
    for field, pick in (("age", age), ("birth_year", birth_year), ("generation", generation)):
        if field in tied and (value := pick(tied[field], result)) is not None:
            result[field] = value
    for country, state in PLACES:
        place(country, state, tied, result)
    for field, values in tied.items():
        if field in HIGHEST:
            result[field] = max(values, key=float)
        elif field not in result:
            result[field] = tiered(field, values)
    return {field: value for field, value in result.items() if value is not None}
