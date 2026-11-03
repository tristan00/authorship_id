import re

from .config import YEAR

FREE = ("age", "birth_year", "height", "weight", "income", "nationality", "residence_country", "residence_region", "residence_city", "origin_country", "origin_region", "origin_city", "native_language")
CHOICES = {'gender': ['male', 'female', 'non-binary', 'trans woman', 'trans man', 'transgender, unspecified'],
 'sexual_orientation': ['straight', 'gay', 'lesbian', 'bisexual', 'pansexual', 'asexual', 'queer, unspecified'],
 'ethnicity': ['white',
               'black',
               'east asian',
               'south asian',
               'southeast asian',
               'hispanic or latino',
               'middle eastern or north african',
               'indigenous',
               'pacific islander',
               'mixed'],
 'religion': ['christian', 'muslim', 'jewish', 'hindu', 'buddhist', 'sikh', 'pagan or other religion', 'spiritual, no religion', 'agnostic', 'atheist'],
 'political_identity': ['communist or far left',
                        'socialist or left',
                        'progressive or liberal',
                        'centrist or moderate',
                        'conservative or right',
                        'nationalist or far right',
                        'libertarian',
                        'anarchist',
                        'apolitical'],
 'relationship_status': ['single', 'dating or in a relationship', 'engaged', 'married', 'separated', 'divorced', 'widowed'],
 'parental_status': ['has children', 'expecting a child', 'no children'],
 'education': ['no high school diploma',
               'high school student',
               'high school diploma',
               'college student',
               'some college, no degree',
               'trade school or associate degree',
               "bachelor's degree",
               'graduate student',
               "master's degree",
               'doctorate',
               'professional degree such as law or medicine'],
 'field_of_study': ['computer science or IT',
                    'engineering',
                    'mathematics or statistics',
                    'natural sciences',
                    'medicine or health',
                    'psychology',
                    'social sciences',
                    'business or finance',
                    'law',
                    'education',
                    'humanities',
                    'arts or design',
                    'other subject'],
 'employment_status': ['employed', 'self-employed or business owner', 'unemployed', 'student', 'retired', 'homemaker', 'unable to work'],
 'occupation': ['software or IT',
                'engineering',
                'science or research',
                'doctor, nurse or clinical health',
                'health support or care work',
                'teaching or education',
                'law',
                'finance or accounting',
                'business, management or consulting',
                'marketing, media or communications',
                'arts, design or entertainment',
                'sales or retail',
                'food service or hospitality',
                'skilled trade or construction',
                'manufacturing or warehouse',
                'transport or delivery',
                'police, fire or security',
                'military',
                'government or public service',
                'social work or religious work',
                'office or administrative',
                'cleaning, maintenance or personal service',
                'farming or outdoor work',
                'sex work or adult content',
                'other job'],
 'body_type': ['very thin', 'slim', 'athletic or muscular', 'average', 'curvy', 'chubby or overweight', 'obese'],
 'hair_color': ['black', 'brown', 'blonde', 'red', 'grey or white', 'dyed unusual color', 'bald'],
 'physical_condition': ['diabetes',
                        'autoimmune disease',
                        'chronic pain or fibromyalgia',
                        'cancer',
                        'heart or blood condition',
                        'digestive condition',
                        'hormonal or reproductive condition',
                        'neurological condition',
                        'skin condition',
                        'respiratory condition or allergy',
                        'vision or hearing impairment',
                        'physical disability',
                        'other physical condition'],
 'mental_condition': ['adhd',
                      'autism',
                      'both adhd and autism',
                      'depression',
                      'anxiety',
                      'bipolar disorder',
                      'ptsd',
                      'ocd',
                      'eating disorder',
                      'personality disorder',
                      'schizophrenia or psychosis',
                      'addiction',
                      'neurodivergent, unspecified',
                      'other mental health condition'],
 'diet': ['vegan', 'vegetarian', 'pescatarian', 'keto or low carb', 'halal or kosher', 'gluten free', 'eats everything'],
 'smoking': ['smoker or vaper', 'non-smoker'],
 'drinking': ['drinks alcohol', 'does not drink'],
 'living_with': ['alone', 'parents', 'partner or family', 'roommates'],
 'housing': ['homeowner', 'renter', 'homeless'],
 'pets': ['dog', 'cat', 'dog and cat', 'other pet', 'no pets'],
 'military_status': ['serving in the military', 'military veteran'],
 'automated_account': ['bot']}
SYNONYMS = {"sexual_orientation": {"heterosexual": "straight", "homosexual": "gay", "bi": "bisexual", "hetero": "straight"},
            "gender": {"transgender": "transgender, unspecified", "trans": "transgender, unspecified", "man": "male", "woman": "female"},
            "ethnicity": {"hispanic": "hispanic or latino", "latina": "hispanic or latino", "latino": "hispanic or latino", "caucasian": "white"}}
NEURO = frozenset({"adhd", "autism", "both adhd and autism", "neurodivergent, unspecified"})
DROPPED = frozenset({"drinking"})
BOT = "automated_account"
FLAIR_ONLY = {"political_compass": ["auth-left", "auth-center", "auth-right", "left", "centrist", "right", "lib-left", "lib-center", "lib-right"],
              "personality_type": ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"],
              "generation": ["silent generation", "baby boomer", "gen x", "millennial", "gen z", "gen alpha"]}
FANDOM = ("sports_team", "athlete", "artist", "author", "character", "franchise", "video_game", "creator", "celebrity")
FAN_PREFIX = "fan_"
FAN_FIELDS = tuple(FAN_PREFIX + name for name in FANDOM)
EVIDENCE_FIELDS = tuple(name for name in (*FREE, *CHOICES) if name not in DROPPED | {BOT, "birth_year"}) + ("neurotype", *FLAIR_ONLY, *FAN_FIELDS)
YES, NO = "yes", "no"
CONDITIONS = {"anxiety": "anxiety", "depression": "depression", "addiction": "addiction", "ocd": "ocd", "ptsd": "ptsd", "eating disorder": "eating_disorder", "bipolar disorder": "bipolar_disorder",
              "schizophrenia or psychosis": "psychosis", "personality disorder": "personality_disorder", "adhd": "adhd", "autism": "autism", "diabetes": "diabetes", "autoimmune disease": "autoimmune_disease",
              "chronic pain or fibromyalgia": "chronic_pain", "cancer": "cancer", "heart or blood condition": "heart_condition", "digestive condition": "digestive_condition",
              "hormonal or reproductive condition": "hormonal_condition", "skin condition": "skin_condition", "respiratory condition or allergy": "respiratory_condition",
              "vision or hearing impairment": "sensory_impairment", "physical disability": "physical_disability"}
MBTI = (("mbti_ie", {"I": "introvert", "E": "extravert"}), ("mbti_ns", {"N": "intuitive", "S": "sensing"}), ("mbti_tf", {"T": "thinking", "F": "feeling"}), ("mbti_jp", {"J": "judging", "P": "perceiving"}))
DECOMPOSED = {("gender", "trans woman"): (("gender", "female"), ("transgender", YES)), ("gender", "trans man"): (("gender", "male"), ("transgender", YES)),
              ("gender", "transgender, unspecified"): (("transgender", YES),), ("sexual_orientation", "gay"): (("sexual_orientation", "gay or lesbian"),),
              ("sexual_orientation", "lesbian"): (("sexual_orientation", "gay or lesbian"),), ("sexual_orientation", "queer, unspecified"): (("sexual_orientation", "queer"),),
              ("education", "high school student"): (("education", "no high school diploma"),), ("education", "college student"): (("education", "some college, no degree"),),
              ("education", "graduate student"): (("education", "bachelor's degree"),), ("education", "professional degree such as law or medicine"): (("education", "professional degree"),),
              ("hair_color", "bald"): (("bald", YES),), ("diet", "eats everything"): (("diet", "eats meat"),), ("diet", "keto or low carb"): (), ("diet", "halal or kosher"): (), ("diet", "gluten free"): (),
              ("pets", "dog"): (("pet_dog", YES),), ("pets", "cat"): (("pet_cat", YES),), ("pets", "dog and cat"): (("pet_dog", YES), ("pet_cat", YES)),
              ("pets", "no pets"): (("pet_dog", NO), ("pet_cat", NO)), ("pets", "other pet"): ()}
DECOMPOSED |= {(field, value): ((CONDITIONS[value], YES),) if value in CONDITIONS else (("adhd", YES), ("autism", YES)) if value == "both adhd and autism" else ()
               for field in ("physical_condition", "mental_condition", "neurotype") for value in (*CHOICES["physical_condition"], *CHOICES["mental_condition"])}
DECOMPOSED |= {("personality_type", value): tuple((name, letters[letter]) for (name, letters), letter in zip(MBTI, value)) for value in FLAIR_ONLY["personality_type"]}
DECOMPOSED |= {("generation", value): () for value in FLAIR_ONLY["generation"]}
CLOSED_VALUES = {**CHOICES, **FLAIR_ONLY, "neurotype": sorted(NEURO)}


def decomposed(field, value):
    return DECOMPOSED.get((field, value), ((field, value),))


def attribute_values():
    found = {}
    for field in EVIDENCE_FIELDS:
        for value in CLOSED_VALUES.get(field, (None,)):
            for attribute, result in decomposed(field, value):
                values = found.setdefault(attribute, [])
                if result is not None and result not in values:
                    values.append(result)
    return {attribute: values + [NO] if YES in values and NO not in values else values for attribute, values in found.items()}


ATTRIBUTE_VALUES = attribute_values()
ALL_FIELDS = tuple(ATTRIBUTE_VALUES)
BINARY = tuple(attribute for attribute, values in ATTRIBUTE_VALUES.items() if YES in values)
FLAIR_ATTRIBUTES = frozenset(attribute for field in FLAIR_ONLY for value in FLAIR_ONLY[field] for attribute, _ in decomposed(field, value))
CLUB = re.compile(r"\s+(?:football club|f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?)$")
BRACKETED = re.compile(r"\s+[(\[][^)\]]*[)\]]?\s*$")
VAGUE = frozenset("this that the these those my our his her their him them it its he she they one game games movie movies film films show shows book books series song songs album albums character characters team teams player players author authors artist artists band bands music".split())
NUMBERS = frozenset({"age", "birth_year", "height", "weight", "income"})
BOUNDS = {"age": (1, 120), "birth_year": (1900, YEAR), "height": (120, 230), "weight": (30, 300), "income": (1000, 100_000_000)}
EMPTY = frozenset({"unknown", "none", "n/a", "unspecified", "other"})
LOWERED = {name: {value.lower(): value for value in values} for name, values in {**CHOICES, **FLAIR_ONLY}.items()}
DIGITS = re.compile(r"[\d,]*\d(?:\.\d+)?")
SQUEEZE = re.compile(r"[\W_]+")
LETTERS = re.compile(r"[^\W\d_]")
THOUSANDS = re.compile(r"\d\s*k\b")
FIELD_TYPE = "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_type WHERE typname = 'claim_field') THEN CREATE TYPE claim_field AS ENUM ('" + BOT + "'); END IF; END $$;\n" + "".join(
    f"ALTER TYPE claim_field ADD VALUE IF NOT EXISTS '{name}';\n" for name in dict.fromkeys((*EVIDENCE_FIELDS, *ALL_FIELDS, BOT)))


def squeeze(text):
    return SQUEEZE.sub("", text.lower())


def chosen(attribute, text):
    table = LOWERED[attribute]
    if exact := table.get(text) or SYNONYMS.get(attribute, {}).get(text):
        return exact
    if not text or text in EMPTY:
        return None
    word = re.compile(rf"\b{re.escape(text)}\b")
    matches = [value for lowered, value in table.items() if word.search(lowered)]
    return matches[0] if len(matches) == 1 else None


def number(attribute, text):
    match = DIGITS.search(text)
    if not match:
        return None
    amount = float(match.group().replace(",", ""))
    if attribute == "income" and THOUSANDS.search(text):
        amount *= 1000
    low, high = BOUNDS[attribute]
    return amount if low <= amount <= high else None


def fan_value(attribute, text):
    text = BRACKETED.sub("", text).removeprefix("the ")
    if attribute == "sports_team":
        text = CLUB.sub("", text)
    return text if set(text.split()) - VAGUE else None


def cleaned(raw):
    return raw.strip().strip("*_`\"'").lower()


def spelled(attribute, raw):
    text = cleaned(raw)
    if not LETTERS.search(text) or len(text) > 40 or text in EMPTY:
        return None
    return fan_value(attribute, text) if attribute in FANDOM else text


def stored_field(attribute):
    return FAN_PREFIX + attribute if attribute in FANDOM else attribute


def normalized(attribute, raw):
    if attribute in LOWERED:
        return chosen(attribute, cleaned(raw))
    if attribute in NUMBERS:
        return number(attribute, cleaned(raw))
    return spelled(attribute, raw)


def canonical(attribute, value):
    if attribute in DROPPED:
        return None
    if attribute == "birth_year":
        return "age", YEAR - value
    if attribute == "mental_condition" and value in NEURO:
        return "neurotype", value
    return attribute, value
