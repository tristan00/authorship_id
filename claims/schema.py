import re

from .config import YEAR

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
COUNTRY_ALIASES = {
    "us": "united states", "u.s": "united states", "usa": "united states", "u.s.a": "united states", "america": "united states",
    "united states of america": "united states", "the us": "united states", "the usa": "united states", "states": "united states",
    "uk": "united kingdom", "u.k": "united kingdom", "britain": "united kingdom", "great britain": "united kingdom",
    "england": "united kingdom", "scotland": "united kingdom", "wales": "united kingdom", "northern ireland": "united kingdom",
    "aus": "australia", "oz": "australia", "nz": "new zealand", "holland": "netherlands", "the netherlands": "netherlands",
    "uae": "united arab emirates", "czechia": "czech republic", "korea": "south korea", "méxico": "mexico", "brasil": "brazil",
    "deutschland": "germany", "españa": "spain", "türkiye": "turkey", "drc": "democratic republic of the congo", "phillipines": "philippines",
    "the philippines": "philippines", "republic of ireland": "ireland", "côte d'ivoire": "ivory coast", "burma": "myanmar",
}
DEMONYMS = {
    "american": "united states", "british": "united kingdom", "english": "united kingdom", "scottish": "united kingdom", "welsh": "united kingdom",
    "brit": "united kingdom", "englishman": "united kingdom", "canadian": "canada", "australian": "australia", "aussie": "australia",
    "kiwi": "new zealand", "new zealander": "new zealand", "irish": "ireland", "german": "germany", "french": "france", "italian": "italy",
    "spanish": "spain", "portuguese": "portugal", "dutch": "netherlands", "belgian": "belgium", "swiss": "switzerland", "austrian": "austria",
    "swedish": "sweden", "swede": "sweden", "norwegian": "norway", "danish": "denmark", "dane": "denmark", "finnish": "finland", "finn": "finland",
    "icelandic": "iceland", "polish": "poland", "czech": "czech republic", "slovak": "slovakia", "hungarian": "hungary", "romanian": "romania",
    "bulgarian": "bulgaria", "greek": "greece", "turkish": "turkey", "russian": "russia", "ukrainian": "ukraine", "belarusian": "belarus",
    "serbian": "serbia", "croatian": "croatia", "bosnian": "bosnia and herzegovina", "slovenian": "slovenia", "albanian": "albania",
    "lithuanian": "lithuania", "latvian": "latvia", "estonian": "estonia", "mexican": "mexico", "mexicano": "mexico", "brazilian": "brazil",
    "argentinian": "argentina", "argentine": "argentina", "chilean": "chile", "colombian": "colombia", "peruvian": "peru",
    "venezuelan": "venezuela", "cuban": "cuba", "dominican": "dominican republic", "puerto rican": "puerto rico", "jamaican": "jamaica",
    "haitian": "haiti", "salvadoran": "el salvador", "guatemalan": "guatemala", "honduran": "honduras", "ecuadorian": "ecuador",
    "chinese": "china", "japanese": "japan", "korean": "south korea", "south korean": "south korea", "taiwanese": "taiwan",
    "vietnamese": "vietnam", "thai": "thailand", "filipino": "philippines", "filipina": "philippines", "indonesian": "indonesia",
    "malaysian": "malaysia", "singaporean": "singapore", "indian": "india", "pakistani": "pakistan", "bangladeshi": "bangladesh",
    "sri lankan": "sri lanka", "nepali": "nepal", "nepalese": "nepal", "afghan": "afghanistan", "iranian": "iran", "persian": "iran",
    "iraqi": "iraq", "syrian": "syria", "lebanese": "lebanon", "jordanian": "jordan", "israeli": "israel", "palestinian": "palestine",
    "saudi": "saudi arabia", "emirati": "united arab emirates", "egyptian": "egypt", "moroccan": "morocco", "algerian": "algeria",
    "tunisian": "tunisia", "libyan": "libya", "nigerian": "nigeria", "ghanaian": "ghana", "kenyan": "kenya", "ethiopian": "ethiopia",
    "somali": "somalia", "ugandan": "uganda", "tanzanian": "tanzania", "south african": "south africa", "zimbabwean": "zimbabwe",
    "cameroonian": "cameroon", "senegalese": "senegal", "kazakh": "kazakhstan", "uzbek": "uzbekistan", "georgian": "georgia",
    "armenian": "armenia", "azerbaijani": "azerbaijan", "mongolian": "mongolia", "hong konger": "hong kong",
}
REGION_ALIASES = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas", "ca": "california", "co": "colorado", "ct": "connecticut",
    "de": "delaware", "dc": "district of columbia", "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho", "il": "illinois",
    "in": "indiana", "ia": "iowa", "ks": "kansas", "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi", "mo": "missouri", "mt": "montana", "ne": "nebraska",
    "nv": "nevada", "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico", "ny": "new york", "nc": "north carolina",
    "nd": "north dakota", "oh": "ohio", "ok": "oklahoma", "or": "oregon", "pa": "pennsylvania", "ri": "rhode island",
    "sc": "south carolina", "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah", "vt": "vermont", "va": "virginia",
    "wa": "washington", "wv": "west virginia", "wi": "wisconsin", "wy": "wyoming", "on": "ontario", "qc": "quebec", "bc": "british columbia",
    "ab": "alberta", "mb": "manitoba", "sk": "saskatchewan", "ns": "nova scotia", "nb": "new brunswick", "nl": "newfoundland and labrador",
    "pei": "prince edward island", "nsw": "new south wales", "vic": "victoria", "qld": "queensland",
    "washington dc": "district of columbia", "washington d.c": "district of columbia", "d.c": "district of columbia", "cali": "california",
    "socal": "california", "norcal": "california", "southern california": "california", "northern california": "california", "jersey": "new jersey",
}
CITY_ALIASES = {"nyc": "new york city", "new york": "new york city", "la": "los angeles", "l.a": "los angeles", "sf": "san francisco",
          "philly": "philadelphia", "chi": "chicago", "vegas": "las vegas", "dc": "washington", "d.c": "washington", "washington dc": "washington",
          "washington d.c": "washington", "cdmx": "mexico city", "nola": "new orleans", "atl": "atlanta", "indy": "indianapolis",
          "bombay": "mumbai", "new delhi": "delhi", "roma": "rome", "münchen": "munich", "köln": "cologne", "wien": "vienna",
          "praha": "prague", "lisboa": "lisbon", "bucurești": "bucharest", "kyiv": "kyiv", "kiev": "kyiv"}
VERIFY = 'A system read a Reddit text and made a claim about the person who wrote it. Decide whether the claim is right.\n\nAnswer Y only if the writer states this about themselves, or it necessarily follows from what they state, it is true of them now, and the text gives this value. Tags such as 28F or [M4F] at the start of a post describe the writer.\n\nAnswer N if the text is about someone else, is a question, hypothetical, wish, plan, joke, role-play, fiction or quotation, if it was true only in the past, if the writer denies it, if the text gives a different value, or if the text does not settle it.\n\nClaim: {claim}\nThe system pointed at these words: {quote}\n\nText:\n{text}\n\nAnswer with one letter, Y or N.'
OPENING = 'Read this text written by a Reddit user. Report what the writer states about themselves, using only the attributes below.\n\nReport a fact only if the writer states it about themselves, or it necessarily follows from what they state: "my wife" means married, "my kids" means has children, "here in Ohio we" means lives in Ohio. Post tags such as 28F or [M4F] at the start of a post describe the writer. Include a fact only if it is true of them now.\n\nDo not report facts about anyone else, questions, hypotheticals, wishes, plans, jokes, role-play, fiction, words quoted from someone else, or past facts that no longer hold. Do not guess from topic or writing style. Skip an attribute unless the text settles it.\n\nWrite one line per fact in this format:\nattribute | value | the writer\'s exact words, copied from the text\n\nAttributes with a free value:\n'
SYNONYMS = {"sexual_orientation": {"heterosexual": "straight", "homosexual": "gay", "bi": "bisexual", "hetero": "straight"},
            "gender": {"transgender": "transgender, unspecified", "trans": "transgender, unspecified", "man": "male", "woman": "female"},
            "ethnicity": {"hispanic": "hispanic or latino", "latina": "hispanic or latino", "latino": "hispanic or latino", "caucasian": "white"},
            "education": {"student": "college student"}}
NEURO = frozenset({"adhd", "autism", "both adhd and autism", "neurodivergent, unspecified"})
DROPPED = frozenset({"drinking"})
BOT = "automated_account"
ALL_FIELDS = tuple(name for name in (*FREE, *CHOICES) if name not in DROPPED | {BOT, "birth_year"}) + ("neurotype",)
NUMBERS = frozenset({"age", "birth_year", "height", "weight", "income"})
BOUNDS = {"age": (1, 120), "birth_year": (1900, YEAR), "height": (120, 230), "weight": (30, 300), "income": (1000, 100_000_000)}
COUNTRY_FIELDS = frozenset({"nationality", "residence_country", "origin_country"})
REGION_FIELDS = frozenset({"residence_region", "origin_region"})
CITY_FIELDS = frozenset({"residence_city", "origin_city"})
EMPTY = frozenset({"unknown", "none", "n/a", "unspecified", "other"})
LOWERED = {name: {value.lower(): value for value in values} for name, values in CHOICES.items()}
DIGITS = re.compile(r"[\d,]*\d(?:\.\d+)?")
SQUEEZE = re.compile(r"[\W_]+")
LETTERS = re.compile(r"[^\W\d_]")
THOUSANDS = re.compile(r"\d\s*k\b")
CLOSED = OPENING + "\n".join(f"- {name}: {text}" for name, text in FREE.items()) + "\n\nAttributes where the value must be exactly one of these:\n" + "\n".join(
    f"- {name}{' (' + DESCRIBE[name] + ')' if name in DESCRIBE else ''}: {' | '.join(values)}" for name, values in CHOICES.items()) + "\n\nIf the text states none of these about the writer, write only: none\n\nText:\n{text}\n\nAnswer:"


def squeeze(text):
    return SQUEEZE.sub("", text.lower())


def chosen(attribute, text):
    table = LOWERED[attribute]
    if exact := table.get(text):
        return exact
    word = re.compile(rf"\b{re.escape(text)}\b")
    matches = [value for lowered, value in table.items() if word.search(lowered)] if text else []
    return matches[0] if len(matches) == 1 else SYNONYMS.get(attribute, {}).get(text)


def number(attribute, text):
    match = DIGITS.search(text)
    if not match:
        return None
    amount = float(match.group().replace(",", ""))
    if attribute == "income" and THOUSANDS.search(text):
        amount *= 1000
    low, high = BOUNDS[attribute]
    return amount if low <= amount <= high else None


def place(attribute, text):
    if attribute in COUNTRY_FIELDS:
        text = DEMONYMS.get(text, COUNTRY_ALIASES.get(text, text))
    elif attribute in REGION_FIELDS:
        text = REGION_ALIASES.get(text, text)
    elif attribute in CITY_FIELDS:
        text = CITY_ALIASES.get(text, text)
    return text


def normalized(attribute, raw):
    text = raw.strip().strip("*_`\"'").lower()
    if attribute in LOWERED:
        return chosen(attribute, text)
    if attribute in NUMBERS:
        return number(attribute, text)
    if not LETTERS.search(text) or len(text) > 40 or text in EMPTY:
        return None
    return place(attribute, text)


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
        if attribute not in FREE and attribute not in CHOICES:
            continue
        value = normalized(attribute, parts[1])
        quote = parts[2].strip().strip("\"'")
        if value is None or not squeeze(quote) or squeeze(quote) not in kept:
            continue
        pair = canonical(attribute, value)
        if pair:
            found.setdefault(pair, quote)
    return found


def claim_text(attribute, value):
    shown = str(int(value)) if isinstance(value, float) else str(value)
    return CLAIMS[attribute].format(value=shown)
