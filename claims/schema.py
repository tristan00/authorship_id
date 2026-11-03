import json
import re

from .config import NAMES_FILE, YEAR

FREE = {'age': 'their age now, whole years',
 'birth_year': 'the year they were born, four digits',
 'height': 'their height, whole centimeters',
 'weight': 'their body weight now, whole kilograms',
 'income': 'their own yearly income, whole US dollars (hourly pay times 2080, monthly pay times 12)',
 'nationality': 'the country they are a citizen or national of',
 'residence_country': 'the country they live in now',
 'residence_region': 'the state, province or region they live in now, full English name',
 'residence_city': 'the city or town they live in or next to now, English name',
 'origin_country': 'the country they were born or raised in',
 'origin_region': 'the state, province or region they were born or raised in, full English name',
 'origin_city': 'the city or town they were born or raised in, English name',
 'native_language': 'their first language, one word'}
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
DESCRIBE = {'relationship_status': 'right now',
 'education': 'highest reached, or level they are at now',
 'employment_status': 'main activity now',
 'occupation': 'field of their current job, only when the text says what the job is',
 'physical_condition': 'a physical health condition they have now',
 'mental_condition': 'a mental or neurodevelopmental condition they have now',
 'automated_account': 'the writer says this account is a bot'}
CLAIMS = {'neurotype': 'the writer has {value}',
          'political_compass': 'the writer places themselves at {value} on the political compass',
          'personality_type': "the writer's personality type: {value}",
          'generation': 'the writer belongs to the generation: {value}',
          'sports_team': 'the writer supports the sports team {value}',
          'athlete': 'the writer is a fan of the athlete {value}',
          'artist': 'the writer is a fan of the artist {value}',
          'author': 'the writer is a fan of the author {value}',
          'character': 'the writer is a fan of the character {value}',
          'franchise': 'the writer is a fan of {value}',
          'video_game': 'the writer is a fan of the video game {value}',
          'creator': 'the writer is a fan of the online creator {value}',
          'celebrity': 'the writer is a fan of {value}',
          'age': 'the writer is {value} years old',
 'birth_year': 'the writer was born in {value}',
 'height': 'the writer is about {value} cm tall',
 'weight': 'the writer weighs about {value} kg now',
 'income': 'the writer earns about {value} US dollars a year',
 'nationality': 'the writer is a citizen or national of {value}',
 'residence_country': 'the writer lives in {value}',
 'residence_region': 'the writer lives in {value}',
 'residence_city': 'the writer lives in or next to {value}',
 'origin_country': 'the writer was born or raised in {value}',
 'origin_region': 'the writer was born or raised in {value}',
 'origin_city': 'the writer was born or raised in {value}',
 'gender': "the writer's gender: {value}",
 'sexual_orientation': "the writer's sexual orientation: {value}",
 'ethnicity': "the writer's race or ethnicity: {value}",
 'native_language': "the writer's first language: {value}",
 'religion': "the writer's religion or belief: {value}",
 'political_identity': "the writer's political identity: {value}",
 'relationship_status': "the writer's relationship status now: {value}",
 'parental_status': "the writer's children: {value}",
 'education': "the writer's education, highest reached or current level: {value}",
 'field_of_study': "the writer's subject of study: {value}",
 'employment_status': "the writer's main activity now: {value}",
 'occupation': "the writer's current job field: {value}",
 'financial_status': "the writer's financial situation: {value}",
 'body_type': "the writer's body type: {value}",
 'hair_color': "the writer's hair color: {value}",
 'physical_condition': 'a physical condition the writer has now: {value}',
 'mental_condition': 'a mental or neurodevelopmental condition the writer has now: {value}',
 'diet': "the writer's diet: {value}",
 'smoking': "the writer's smoking: {value}",
 'drinking': "the writer's drinking: {value}",
 'living_with': 'who the writer lives with: {value}',
 'housing': "the writer's housing: {value}",
 'pets': "the writer's pets: {value}",
 'military_status': "the writer's military status: {value}",
 'automated_account': 'the writer says this account is a bot'}
VERIFY = 'A system read a Reddit text and made a claim about the person who wrote it. Decide whether the claim is right.\n\nAnswer Y only if the writer states this about themselves, or it necessarily follows from what they state, it is true of them now, and the text gives this value. Tags such as 28F or [M4F] at the start of a post describe the writer.\n\nAnswer N if the text is about someone else, is a question, hypothetical, wish, plan, joke, role-play, fiction or quotation, if it was true only in the past, if the writer denies it, if the text gives a different value, or if the text does not settle it.\n\nClaim: {claim}\nThe system pointed at these words: {quote}\n\nText:\n{text}\n\nAnswer with one letter, Y or N.'
OPENING = 'Read this text written by a Reddit user. Report what the writer states about themselves, using only the attributes below.\n\nReport a fact only if the writer states it about themselves, or it necessarily follows from what they state: "my wife" means married, "my kids" means has children, "here in Ohio we" means lives in Ohio. Post tags such as 28F or [M4F] at the start of a post describe the writer. Include a fact only if it is true of them now.\n\nDo not report facts about anyone else, questions, hypotheticals, wishes, plans, jokes, role-play, fiction, words quoted from someone else, or past facts that no longer hold. Do not guess from topic or writing style. Skip an attribute unless the text settles it.\n\nWrite one line per fact in this format:\nattribute | value | the writer\'s exact words, copied from the text\n\nAttributes with a free value:\n'
SYNONYMS = {"sexual_orientation": {"heterosexual": "straight", "homosexual": "gay", "bi": "bisexual", "hetero": "straight"},
            "gender": {"transgender": "transgender, unspecified", "trans": "transgender, unspecified", "man": "male", "woman": "female"},
            "ethnicity": {"hispanic": "hispanic or latino", "latina": "hispanic or latino", "latino": "hispanic or latino", "caucasian": "white"}}
NEURO = frozenset({"adhd", "autism", "both adhd and autism", "neurodivergent, unspecified"})
DROPPED = frozenset({"drinking"})
BOT = "automated_account"
FLAIR_ONLY = {"political_compass": ["auth-left", "auth-center", "auth-right", "left", "centrist", "right", "lib-left", "lib-center", "lib-right"],
              "personality_type": ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"],
              "generation": ["silent generation", "baby boomer", "gen x", "millennial", "gen z", "gen alpha"]}
FANDOM = {"sports_team": "the real sports team they support, full club or franchise name",
          "athlete": "the real athlete or racing driver they are a fan of",
          "artist": "the musician, band or other artist they are a fan of",
          "author": "the book author they are a fan of",
          "character": "the fictional character they are a fan of, or play as their main in a game",
          "franchise": "the TV show, film series, anime, manga, comic or book series they are a fan of",
          "video_game": "the video game they are a fan of",
          "creator": "the streamer, YouTuber, podcaster or other online creator they are a fan of",
          "celebrity": "the actor, comedian or other famous person they are a fan of"}
FAN_PREFIX = "fan_"
FAN_FIELDS = tuple(FAN_PREFIX + name for name in FANDOM)
EVIDENCE_FIELDS = tuple(name for name in (*FREE, *CHOICES) if name not in DROPPED | {BOT, "birth_year"}) + ("neurotype", *FLAIR_ONLY, *FAN_FIELDS)
YES, NO = "yes", "no"
CONDITIONS = {"anxiety": "anxiety", "depression": "depression", "addiction": "addiction", "ocd": "ocd", "ptsd": "ptsd", "eating disorder": "eating_disorder", "bipolar disorder": "bipolar_disorder",
              "schizophrenia or psychosis": "psychosis", "personality disorder": "personality_disorder", "adhd": "adhd", "autism": "autism", "diabetes": "diabetes", "autoimmune disease": "autoimmune_disease",
              "chronic pain or fibromyalgia": "chronic_pain", "cancer": "cancer", "heart or blood condition": "heart_condition", "digestive condition": "digestive_condition",
              "hormonal or reproductive condition": "hormonal_condition", "skin condition": "skin_condition", "respiratory condition or allergy": "respiratory_condition",
              "vision or hearing impairment": "sensory_impairment", "physical disability": "physical_disability"}
COMPASS = {"auth-left": ("left", "authoritarian"), "auth-center": ("center", "authoritarian"), "auth-right": ("right", "authoritarian"), "left": ("left", "center"), "centrist": ("center", "center"),
           "right": ("right", "center"), "lib-left": ("left", "libertarian"), "lib-center": ("center", "libertarian"), "lib-right": ("right", "libertarian")}
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
DECOMPOSED |= {("political_compass", value): (("compass_economic", economic), ("compass_social", social)) for value, (economic, social) in COMPASS.items()}
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
FAN_WORDS = re.compile(r"\b(?:fans?|fandom|favou?rites?|favs?|faves?|lov(?:e|ed|es|ing)|adored?|obsessed|supporters?|stan|stans|rooting|die-?hard|lifelong|goat|authors?|writers?|novels?|streamers?|twitch|youtubers?|youtube|podcasts?|comedians?|actors?|actress|mains?|maining)\b", re.I)
CLUB = re.compile(r"\s+(?:football club|f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?)$")
VAGUE = frozenset("this that the these those my our his her their him them it its he she they one game games movie movies film films show shows book books series song songs album albums character characters team teams player players author authors artist artists band bands music".split())
NUMBERS = frozenset({"age", "birth_year", "height", "weight", "income"})
BOUNDS = {"age": (1, 120), "birth_year": (1900, YEAR), "height": (120, 230), "weight": (30, 300), "income": (1000, 100_000_000)}
COUNTRY_FIELDS = frozenset({"nationality", "residence_country", "origin_country"})
REGION_FIELDS = frozenset({"residence_region", "origin_region"})
CITY_FIELDS = frozenset({"residence_city", "origin_city"})
KINDS = {**dict.fromkeys(COUNTRY_FIELDS, "country"), **dict.fromkeys(REGION_FIELDS, "state or region"), **dict.fromkeys(CITY_FIELDS, "city"),
         "sports_team": "sports team", "athlete": "athlete", "artist": "musician or band", "author": "book author", "character": "fictional character",
         "franchise": "show, film series, anime, manga, comic or book series", "video_game": "video game", "creator": "online creator", "celebrity": "famous person"}
KINDS |= {FAN_PREFIX + name: KINDS[name] for name in FANDOM}
STORED_KINDS = {field: kind for field, kind in KINDS.items() if field not in FANDOM}
FIELD_TYPE = "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_type WHERE typname = 'claim_field') THEN CREATE TYPE claim_field AS ENUM ('" + BOT + "'); END IF; END $$;\n" + "".join(
    f"ALTER TYPE claim_field ADD VALUE IF NOT EXISTS '{name}';\n" for name in dict.fromkeys((*EVIDENCE_FIELDS, *ALL_FIELDS, BOT)))
NAMES = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
EMPTY = frozenset({"unknown", "none", "n/a", "unspecified", "other"})
LOWERED = {name: {value.lower(): value for value in values} for name, values in {**CHOICES, **FLAIR_ONLY}.items()}
DIGITS = re.compile(r"[\d,]*\d(?:\.\d+)?")
SQUEEZE = re.compile(r"[\W_]+")
LETTERS = re.compile(r"[^\W\d_]")
THOUSANDS = re.compile(r"\d\s*k\b")
CLOSED = OPENING + "\n".join(f"- {name}: {text}" for name, text in FREE.items()) + "\n\nAttributes where the value must be exactly one of these:\n" + "\n".join(
    f"- {name}{' (' + DESCRIBE[name] + ')' if name in DESCRIBE else ''}: {' | '.join(values)}" for name, values in CHOICES.items()) + "\n\nIf the text states none of these about the writer, write only: none\n\nText:\n{text}\n\nAnswer:"


FANDOM_PROMPT = """Read this text written by a Reddit user. Report what the writer says they are personally a fan of, using only the attributes below.

Report a fact only if the writer says about themselves, now, that they are a fan or supporter of it, love it, follow it devotedly or name it as a favorite, and the text names it. Do not report anyone else's fandom, questions, hypotheticals, jokes, role-play, or things the writer only mentions, discusses, reviews, criticizes, owns or uses. Skip anything the text does not name, such as "this game" or "that show".

Write one line per fact in this format:
attribute | value | the writer's exact words, copied from the text

Attributes:
""" + "\n".join(f"- {name}: {text}" for name, text in FANDOM.items()) + """

If the text states none of these, write only: none

Text:
{text}

Answer:"""
FLAIR_LINES = {name: f"- {name}: {text}" for name, text in {**FREE, **FANDOM}.items()} | {name: f"- {name}{' (' + DESCRIBE[name] + ')' if name in DESCRIBE else ''}: {' | '.join(values)}" for name, values in {**CHOICES, **FLAIR_ONLY}.items() if name not in DROPPED | {BOT}}
FLAIR_INTRO = "A flair is a short label a Reddit user shows next to their name in a subreddit. Words between colons such as :Arsenal: are emoji names and count as part of the flair. "
FLAIR_SCHEMA = FLAIR_INTRO + """In some subreddits users pick a flair that says something true about themselves. In others flairs are ranks, trade counts, game items, in-jokes or labels handed out by the subreddit, which say nothing about the person.

Below are a subreddit and its most common flairs, with how many users wear each. Decide which of these attributes the flairs of this subreddit are used to tell about the person who wears them. List an attribute only if many of these flairs settle it.

Attributes:
""" + "\n".join(FLAIR_LINES.values()) + """

Write one attribute name per line. If these flairs tell nothing about the person, write only: none

Subreddit: r/{subreddit}
Flairs:
{flairs}

Answer:"""
FLAIR = FLAIR_INTRO + """Report what this flair says about the person who wears it, using only the attributes below. Skip an attribute unless the flair settles it, given how the subreddit uses flairs. If the flair gives an age range such as 20s or 25-30, give the middle of the range.

Write one line per fact in this format:
attribute | value

If the flair settles none of these, write only: none

Attributes:
{attributes}

Subreddit: r/{subreddit}
Flair: {flair}

Answer:"""
NAME_PROMPT = """Someone wrote a name. Write the one standard English name of the thing they meant, in lower case, with no explanation. Expand abbreviations, nicknames, misspellings and names in other languages to the full standard name. A word for the people of a country means that country. If you do not recognize it, or it could mean several different things of this kind, such as a first name alone, write it back unchanged. Only if it is clearly not that kind of thing at all, write: none

country: usa = united states
country: united states of america = united states
country: french = france
country: canadian = canada
country: filipino = philippines
country: scottish = united kingdom
country: england = united kingdom
country: wales = united kingdom
country: deutschland = germany
country: ireland = ireland
country: my house = none
state or region: cali = california
state or region: nsw = new south wales
state or region: bayern = bavaria
state or region: scotland = scotland
state or region: england = england
state or region: downtown = none
city: nyc = new york city
city: münchen = munich
city: new delhi = delhi
city: springfield = springfield
city: germany = none
sports team: knicks = new york knicks
sports team: man utd = manchester united
sports team: bayern = bayern munich
sports team: rangers = rangers
sports team: new york giants = new york giants
athlete: lebron = lebron james
athlete: alonso = fernando alonso
athlete: james = james
musician or band: taytay = taylor swift
musician or band: nin = nine inch nails
musician or band: olivia = olivia
book author: tolkien = j. r. r. tolkien
book author: sjm = sarah j. maas
fictional character: spidey = spider-man
fictional character: gandalf = gandalf
fictional character: luna = luna
fictional character: my mom = none
show, film series, anime, manga, comic or book series: lotr = the lord of the rings
show, film series, anime, manga, comic or book series: jjk = jujutsu kaisen
show, film series, anime, manga, comic or book series: marvel = marvel
video game: rdr2 = red dead redemption 2
video game: peak = peak
online creator: pewdiepie = pewdiepie
famous person: arnie = arnold schwarzenegger
famous person: michael = michael

{kind}: {name} ="""

NAME_SAME = """Someone wrote a name for a kind of thing. A full name is proposed for it. Would most people who write that name, when naming that kind of thing, mean exactly the full name given? If several different things of that kind are commonly called that, or the full name is a different thing, answer N. Answer only Y or N.

athlete: lebron -> lebron james = Y
athlete: cr7 -> cristiano ronaldo = Y
athlete: messi -> fernando alonso = N
athlete: david -> david beckham = N
musician or band: nin -> nine inch nails = Y
musician or band: oasis -> coldplay = N
musician or band: john -> john lennon = N
book author: tolkien -> j. r. r. tolkien = Y
book author: dan -> dan brown = N
show, film series, anime, manga, comic or book series: got -> game of thrones = Y
show, film series, anime, manga, comic or book series: thrones -> game of thrones = Y
show, film series, anime, manga, comic or book series: batman -> lord of the rings = N
video game: gta -> grand theft auto = Y
video game: dragon -> dragon age = N
video game: dune -> doom = N
sports team: knicks -> new york knicks = Y
sports team: giants -> new york giants = N
sports team: lakers -> boston celtics = N
fictional character: geralt -> geralt of rivia = Y
fictional character: naruto -> batman = N
fictional character: mike -> mike wazowski = N
online creator: pewds -> pewdiepie = Y
online creator: pewdiepie -> markiplier = N
famous person: dicaprio -> leonardo dicaprio = Y
famous person: jennifer -> jennifer lawrence = N
country: usa -> united states = Y
state or region: cali -> california = Y
city: nyc -> new york city = Y
city: paris -> london = N

{kind}: {name} -> {target} ="""

NAME_CHECK = """Someone named a thing of a given kind as something they are a fan of. Judge the name by itself. Answer with only one letter.
A: it is a real thing of that kind and the name points to one specific one
B: it is only a first name, a surname or a common word, so it does not say which one is meant
C: it is clearly not that kind of thing at all
D: you do not recognize it

musician or band: taylor swift = A
musician or band: radiohead = A
musician or band: amy = B
musician or band: supermarket = C
musician or band: zqvart = D
athlete: lionel messi = A
athlete: paul = B
athlete: pickleball = C
book author: stephen king = A
book author: robert = B
book author: cookbook = C
fictional character: batman = A
fictional character: tom = B
fictional character: star wars = C
fictional character: keanu reeves = C
video game: minecraft = A
video game: board = C
video game: team deathmatch = C
show, film series, anime, manga, comic or book series: breaking bad = A
show, film series, anime, manga, comic or book series: classroom = C
sports team: arsenal = A
sports team: tennis = C
online creator: pewdiepie = A
online creator: chris = B
online creator: youtube = C
online creator: netflix = C
famous person: zendaya = A
famous person: smith = B
famous person: beer = C

{kind}: {name} ="""

NAME_GENERIC = """Someone named a fictional character they are a fan of. Is this a name that some well known fictional character actually goes by, or only a generic word, role, class or title? Answer with only one letter.
A: some well known fictional character goes by this name
B: only a generic word, role, class or title

geralt = A
hermione = A
neo = A
ellie = A
link = A
joker = A
master chief = A
wizard = B
warrior = B
teacher = B
villain = B
sir = B
main = B
friend = B

{name} ="""
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
    text = text.removeprefix("the ")
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


def renamed(attribute, text):
    return NAMES.get(KINDS[attribute], {}).get(text, text) if attribute in KINDS else text


def normalized(attribute, raw):
    if attribute in LOWERED:
        return chosen(attribute, cleaned(raw))
    if attribute in NUMBERS:
        return number(attribute, cleaned(raw))
    text = spelled(attribute, raw)
    return text and renamed(attribute, text)


def canonical(attribute, value):
    if attribute in DROPPED:
        return None
    if attribute == "birth_year":
        return "age", YEAR - value
    if attribute == "mental_condition" and value in NEURO:
        return "neurotype", value
    return attribute, value


def parse(answer, text):
    found, kept = {}, squeeze(text)
    for line in (answer or "").splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 3:
            continue
        attribute = parts[0].strip("-*\u2022 ").lower()
        if attribute not in FREE and attribute not in CHOICES and attribute not in FANDOM:
            continue
        value = normalized(attribute, parts[1])
        quote = parts[2].strip().strip("\"'")
        if value is None or not squeeze(quote) or squeeze(quote) not in kept:
            continue
        pair = canonical(attribute, value)
        if pair:
            found.setdefault(pair, quote)
    return found


def flair_attributes(answer):
    found = []
    for line in (answer or "").splitlines():
        name = line.partition("|")[0].partition(":")[0].strip("-*\u2022 `").lower()
        if name in FLAIR_LINES and name not in found:
            found.append(name)
    return found


def flair_facts(answer):
    found = {}
    for line in (answer or "").splitlines():
        parts = [part.strip() for part in (line.split("|") if "|" in line else line.split(":", 1))]
        if len(parts) < 2:
            continue
        attribute = parts[0].strip("-*\u2022 ").lower()
        if attribute not in FREE and attribute not in FANDOM and attribute not in LOWERED:
            continue
        value = normalized(attribute, parts[1])
        if value is None:
            continue
        pair = canonical(attribute, value)
        if pair and pair[0] != BOT:
            found.setdefault(*pair)
    return found


def claim_text(attribute, value):
    shown = str(int(value)) if isinstance(value, float) else str(value)
    return CLAIMS[attribute].format(value=shown)
