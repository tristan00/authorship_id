from collections import Counter, defaultdict

from claim_extraction.normalize import CLOSED, REGIONS

YEAR = 2026
ADULT = 18
OLDER = 25
GAP = 10
GENERATIONS = {"gen alpha": (2013, 2025), "gen z": (1997, 2012), "millennial": (1981, 1996), "gen x": (1965, 1980),
               "baby boomer": (1946, 1964), "silent generation": (1928, 1945)}
HIGHEST = ("height", "weight", "income")
DEGREES = ("doctorate", "professional degree", "master's degree", "bachelor's degree", "associate degree", "some college", "high school",
           "less than high school")
RACES = ("american indian or alaska native", "asian", "black or african american", "hispanic or latino", "middle eastern or north african",
         "native hawaiian or pacific islander", "white")
FAITHS = ("christian", "muslim", "jewish", "hindu", "buddhist", "sikh", "other religion")
PLACES = (("residence_country", "residence_state"), ("origin_country", "origin_state"))
MATCHES = (("nationality", "origin_country"), ("origin_country", "nationality"))
IMPLIED = {("sexual_orientation", "lesbian"): ("gender", "female")}


def above(winners, losers):
    return {(winner, loser) for winner in winners for loser in losers if winner != loser}


PREFER = {
    "education": {(DEGREES[high], DEGREES[low]) for high in range(len(DEGREES)) for low in range(high + 1, len(DEGREES))},
    "gender": above(("non-binary",), ("male", "female")),
    "sexual_orientation": above(("bisexual",), ("gay", "lesbian", "straight")) | above(("queer",), ("gay", "lesbian")),
    "religion": above(("atheist", "agnostic"), (*FAITHS, "no religion")),
    "race_ethnicity": above(("multiracial",), RACES),
    "employment_status": above(("self-employed",), ("employed",)) | above(("employed",), ("unemployed", "retired")),
    "relationship_status": above(("married",), ("single",)) | above(("in a relationship",), ("single",))
                           | above(("married", "engaged"), ("in a relationship",)),
    "marital_status": above(("married",), ("divorced",)),
    "parental_status": above(("parent",), ("no children",)),
    "occupation": above(CLOSED["occupation"], ("management",)),
}


def leaders(counts):
    top = max(counts.values())
    return sorted(value for value, count in counts.items() if count == top)


def only(values):
    return values[0] if len(values) == 1 else None


def preferred(field, values):
    pairs = PREFER.get(field, ())
    return only([value for value in values if all((value, other) in pairs for other in values if other != value)])


def born(age, year):
    return abs(YEAR - year - age) <= 1


def age(values, result):
    if year := result.get("birth_year"):
        if match := only([value for value in values if born(float(value), int(year))]):
            return match
    if (span := GENERATIONS.get(result.get("generation"))) and (match := [value for value in values if span[0] - 1 <= YEAR - float(value) <= span[1] + 1]):
        if len(match) == 1:
            return match[0]
        values = match
    values = sorted([value for value in values if float(value) >= ADULT] or values, key=float)
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        low, high = values
        return low if float(low) >= OLDER and float(high) - float(low) >= GAP else high
    return None


def birth_year(values, result):
    return only([value for value in values if "age" in result and born(float(result["age"]), int(value))]) if "age" in result else None


def generation(values, result):
    years = [int(result["birth_year"])] if "birth_year" in result else [YEAR - int(float(result["age"]))] if "age" in result else []
    return only([value for value in values if value in GENERATIONS and any(GENERATIONS[value][0] - 1 <= year <= GENERATIONS[value][1] + 1 for year in years)])


def place(country, state, tied, result):
    if country in tied and (region := result.get(state)) and (value := only([item for item in tied[country] if region in REGIONS.get(item, ())])):
        result[country] = value
    if state in tied and (regions := REGIONS.get(result.get(country))) and (value := only([item for item in tied[state] if item in regions])):
        result[state] = value


def consolidate(evidence):
    counts = defaultdict(Counter)
    for _, _, field, value in evidence:
        counts[field][value] += 1
    tied = {field: leaders(found) for field, found in counts.items()}
    result = {field: values[0] for field, values in tied.items() if len(values) == 1}
    tied = {field: values for field, values in tied.items() if len(values) > 1}
    for field, pick in (("age", age), ("birth_year", birth_year), ("generation", generation)):
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
        if field in HIGHEST:
            result[field] = max(values, key=float)
        elif field not in result and (value := preferred(field, values)) is not None:
            result[field] = value
    return result
