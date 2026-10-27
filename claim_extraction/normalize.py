import json
import re
from pathlib import Path

from .config import NUMERIC

FIELDS = json.loads((Path(__file__).with_name("annotation.json")).read_text(encoding="utf-8"))["fields"]
CLOSED = {field: set(spec["values"]) for field, spec in FIELDS.items() if "values" in spec}
COUNTRIES = CLOSED["nationality"]
LANGUAGES = CLOSED["language"]

KEYS = {"age_years": "age", "native_language": "language", "residence_state_or_province": "residence_state",
        "origin_state_or_province": "origin_state", "highest_degree": "education", "field_of_study": "education_subject",
        "job_title": "occupation", "political_compass_quadrant": "political_compass", "racial_ethnicity": "race_ethnicity",
        "height_cm": "height", "height_metric": "height", "height_inches": "height", "height_imperial": "height",
        "weight_kg": "weight", "weight_lbs": "weight", "yearly_income_usd": "income", "monthly_income_usd": "income",
        "hourly_wage_usd": "income"}
INCOME_SCALE = {"monthly_income_usd": 12, "hourly_wage_usd": 2080}
EMPTY = re.compile(r"^(none|n/?a|null|unknown|unspecified|not .*|none .*|no .* stated|-|\\-|)$")
DROP = re.compile(r"[\[\]():?~]|implied|inferred|former|previous|\bex\b|\bpast\b|planned|planning|want|hoping|looking|maybe|\bor\b")

COUNTRY_ALIASES = {
    "us": "united states", "u.s.": "united states", "usa": "united states", "u.s.a.": "united states", "america": "united states",
    "united states of america": "united states", "the us": "united states", "the usa": "united states", "states": "united states",
    "uk": "united kingdom", "u.k.": "united kingdom", "britain": "united kingdom", "great britain": "united kingdom",
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
STATES = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas", "ca": "california", "co": "colorado", "ct": "connecticut",
    "de": "delaware", "dc": "district of columbia", "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho", "il": "illinois",
    "in": "indiana", "ia": "iowa", "ks": "kansas", "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi", "mo": "missouri", "mt": "montana", "ne": "nebraska",
    "nv": "nevada", "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico", "ny": "new york", "nc": "north carolina",
    "nd": "north dakota", "oh": "ohio", "ok": "oklahoma", "or": "oregon", "pa": "pennsylvania", "ri": "rhode island",
    "sc": "south carolina", "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah", "vt": "vermont", "va": "virginia",
    "wa": "washington", "wv": "west virginia", "wi": "wisconsin", "wy": "wyoming", "on": "ontario", "qc": "quebec", "bc": "british columbia",
    "ab": "alberta", "mb": "manitoba", "sk": "saskatchewan", "ns": "nova scotia", "nb": "new brunswick", "nl": "newfoundland and labrador",
    "pei": "prince edward island", "nsw": "new south wales", "vic": "victoria", "qld": "queensland", "wa.": "western australia",
    "washington dc": "district of columbia", "washington d.c.": "district of columbia", "d.c.": "district of columbia", "cali": "california",
    "socal": "california", "norcal": "california", "southern california": "california", "northern california": "california", "jersey": "new jersey",
}
REGIONS = {
    "united states": ("alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "district of columbia", "florida",
                      "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts",
                      "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
                      "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
                      "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming"),
    "canada": ("ontario", "quebec", "british columbia", "alberta", "manitoba", "saskatchewan", "nova scotia", "new brunswick", "newfoundland and labrador",
               "prince edward island", "yukon", "northwest territories", "nunavut"),
    "australia": ("new south wales", "victoria", "queensland", "western australia", "tasmania", "south australia", "northern territory",
                  "australian capital territory"),
    "united kingdom": ("england", "scotland", "wales", "northern ireland"),
    "india": ("maharashtra", "karnataka", "tamil nadu", "kerala", "goa", "west bengal", "punjab", "gujarat", "rajasthan", "uttar pradesh", "delhi",
              "telangana", "andhra pradesh", "bihar", "haryana", "madhya pradesh", "odisha", "assam"),
    "germany": ("bavaria", "berlin", "hamburg", "hesse", "saxony", "north rhine-westphalia", "baden-württemberg", "lower saxony"),
    "brazil": ("são paulo", "sao paulo", "rio de janeiro", "minas gerais"),
    "mexico": ("jalisco", "puebla", "nuevo león", "nuevo leon", "yucatan", "yucatán", "mexico city"),
    "philippines": ("metro manila", "cebu", "luzon"),
    "pakistan": ("sindh",),
    "nigeria": ("lagos",),
    "new zealand": ("auckland",),
    "spain": ("catalonia", "andalusia"),
    "italy": ("lombardy", "sicily"),
    "france": ("île-de-france",),
}
STATE_NAMES = {region for regions in REGIONS.values() for region in regions}
CITIES = {"nyc": "new york", "new york city": "new york", "la": "los angeles", "l.a.": "los angeles", "sf": "san francisco",
          "philly": "philadelphia", "chi": "chicago", "vegas": "las vegas", "dc": "washington", "d.c.": "washington", "washington dc": "washington",
          "washington d.c.": "washington", "cdmx": "mexico city", "nola": "new orleans", "atl": "atlanta", "indy": "indianapolis",
          "bombay": "mumbai", "new delhi": "delhi", "roma": "rome", "münchen": "munich", "köln": "cologne", "wien": "vienna",
          "praha": "prague", "lisboa": "lisbon", "bucurești": "bucharest", "kyiv": "kyiv", "kiev": "kyiv"}
CITY_SUFFIX = re.compile(r"\s+(area|suburbs|metro|city area)$")

WORDS = {
    "generation": {"silent generation": ("silent", "silent generation"), "baby boomer": ("boomer", "boomers", "baby boomer", "baby boomers"),
                   "gen x": ("gen x", "genx", "generation x", "gen-x"), "millennial": ("millennial", "millennials", "millenial", "gen y", "generation y"),
                   "gen z": ("gen z", "genz", "gen-z", "generation z", "zoomer", "zoomers"), "gen alpha": ("gen alpha", "generation alpha")},
    "gender": {"male": ("m", "male", "man", "men", "guy", "boy", "dude", "mann", "hombre", "homme", "trans man", "transman", "ftm", "trans male", "masc male"),
               "female": ("f", "female", "woman", "women", "girl", "gal", "lady", "trans woman", "transwoman", "trans girl", "mtf", "trans female", "frau", "mujer", "femme female"),
               "non-binary": ("non-binary", "nonbinary", "non binary", "nb", "enby", "genderqueer", "agender", "genderfluid")},
    "sexual_orientation": {"straight": ("straight", "heterosexual", "hetero"), "gay": ("gay", "homosexual"), "lesbian": ("lesbian",),
                           "bisexual": ("bi", "bisexual", "bi-sexual"), "pansexual": ("pan", "pansexual"), "asexual": ("asexual", "ace"),
                           "queer": ("queer",)},
    "race_ethnicity": {"white": ("white", "caucasian", "european", "white european", "white american"),
                       "black or african american": ("black", "african american", "african-american", "black american", "african descent"),
                       "asian": ("asian", "east asian", "south asian", "southeast asian", "chinese", "korean", "japanese", "vietnamese", "filipino",
                                 "filipina", "indian", "desi", "pakistani", "bangladeshi", "asian american", "taiwanese", "thai"),
                       "hispanic or latino": ("hispanic", "latino", "latina", "latinx", "latine", "mexican", "mexican american", "chicano", "chicana",
                                              "puerto rican", "mestizo"),
                       "middle eastern or north african": ("middle eastern", "arab", "arabic", "persian", "iranian", "north african", "moroccan", "mena",
                                                          "egyptian", "lebanese", "turkish"),
                       "american indian or alaska native": ("native american", "american indian", "indigenous american", "alaska native", "first nations"),
                       "native hawaiian or pacific islander": ("pacific islander", "native hawaiian", "samoan", "tongan", "polynesian"),
                       "multiracial": ("mixed", "mixed race", "biracial", "multiracial", "mixed-race", "half black", "half asian", "half white")},
    "religion": {"christian": ("christian", "christianity", "catholic", "roman catholic", "protestant", "baptist", "evangelical", "evangelical christian",
                               "mormon", "mormonism", "lds", "orthodox", "orthodox christian", "lutheran", "methodist", "presbyterian", "pentecostal",
                               "anglican", "episcopalian", "western christian", "born again christian"),
                 "muslim": ("muslim", "islam", "sunni", "shia", "moslem"), "jewish": ("jewish", "jew", "judaism"), "hindu": ("hindu", "hinduism"),
                 "buddhist": ("buddhist", "buddhism", "tibetan buddhist", "zen buddhist"), "sikh": ("sikh", "sikhism"),
                 "other religion": ("pagan", "neo pagan", "neopagan", "wiccan", "wicca", "heathen", "satanist", "taoist", "shinto", "jain", "bahai", "baha'i"),
                 "atheist": ("atheist", "atheism", "атеист"), "agnostic": ("agnostic", "agnosticism"),
                 "no religion": ("not religious", "non-religious", "nonreligious", "irreligious", "no religion", "secular", "nonbeliever")},
    "education": {"less than high school": ("high school dropout", "no high school", "no diploma"),
                  "high school": ("high school", "high school diploma", "hs diploma", "ged", "high school graduate"),
                  "some college": ("some college", "college student", "university student", "undergrad", "undergraduate", "undergrad student", "college dropout"),
                  "associate degree": ("associate degree", "associate's degree", "associates degree", "associates", "associate's", "aa", "as degree"),
                  "bachelor's degree": ("bachelor's degree", "bachelors degree", "bachelor degree", "bachelor's", "bachelors", "bachelor", "bsc", "bs", "ba",
                                        "b.a.", "b.s.", "college degree", "university degree", "undergraduate degree", "college graduate", "bcom", "beng"),
                  "master's degree": ("master's degree", "masters degree", "master degree", "master's", "masters", "master", "msc", "ms", "ma", "mba",
                                      "m.s.", "m.a.", "meng", "mph", "msw"),
                  "professional degree": ("professional degree", "md", "m.d.", "jd", "j.d.", "law degree", "medical degree", "dds", "pharmd", "dvm"),
                  "doctorate": ("doctorate", "phd", "ph.d.", "ph.d", "doctoral degree", "edd")},
    "employment_status": {"employed": ("employed", "working", "full time", "full-time", "part time", "part-time", "full time job", "employee",
                                       "working full time", "working part time", "work", "job"),
                          "self-employed": ("self-employed", "self employed", "freelance", "freelancer", "business owner", "contractor", "independent contractor"),
                          "unemployed": ("unemployed", "no job", "jobless", "out of work", "between jobs", "laid off", "fired"),
                          "student": ("student", "college student", "university student", "in college", "in school", "high school student",
                                      "grad student", "phd student", "undergrad"),
                          "retired": ("retired", "retiree"),
                          "homemaker": ("homemaker", "stay at home mom", "stay at home mum", "stay-at-home mom", "stay at home dad", "sahm", "sahd", "housewife",
                                        "househusband", "stay at home parent"),
                          "unable to work": ("unable to work", "disabled", "on disability", "disability")},
    "marital_status": {"never married": ("never married", "unmarried", "not married"), "married": ("married", "husband", "wife", "happily married", "recently married", "newlywed"),
                       "separated": ("separated",), "divorced": ("divorced", "divorcee"), "widowed": ("widowed", "widow", "widower")},
    "relationship_status": {"single": ("single", "unattached"),
                            "in a relationship": ("in a relationship", "relationship", "partner", "partnered", "boyfriend", "girlfriend", "dating",
                                                  "committed relationship", "in a committed relationship", "taken", "couple", "in a long distance relationship",
                                                  "long distance relationship", "in a healthy relationship", "healthy relationship"),
                            "engaged": ("engaged", "fiance", "fiancé", "fiancee", "fiancée"),
                            "married": ("married", "husband", "wife", "happily married", "recently married", "newlywed")},
    "mental_health": {"adhd": ("adhd", "add", "adhd-pi", "adhd-c"), "autism": ("autism", "autistic", "asd", "asperger's", "aspergers", "asperger", "autism spectrum disorder"),
                      "depression": ("depression", "major depression", "mdd", "major depressive disorder", "clinical depression", "treatment resistant depression"),
                      "anxiety disorder": ("anxiety", "anxiety disorder", "gad", "generalized anxiety disorder", "social anxiety", "panic disorder", "social anxiety disorder"),
                      "bipolar disorder": ("bipolar", "bipolar disorder", "bipolar 1", "bipolar 2", "bipolar i", "bipolar ii"),
                      "ptsd": ("ptsd", "cptsd", "c-ptsd", "complex ptsd"), "ocd": ("ocd", "obsessive compulsive disorder"),
                      "eating disorder": ("eating disorder", "anorexia", "bulimia", "binge eating disorder", "arfid", "ed"),
                      "schizophrenia": ("schizophrenia", "schizophrenic", "schizoaffective", "schizoaffective disorder"),
                      "personality disorder": ("bpd", "borderline personality disorder", "borderline", "npd", "personality disorder", "narcissistic personality disorder"),
                      "substance use disorder": ("addiction", "alcoholism", "alcoholic", "addict", "substance use disorder", "substance abuse")},
    "parental_status": {"parent": ("parent", "dad", "mom", "mum", "mother", "father", "has kids", "has children", "has a child", "have kids", "with kids",
                                   "single dad", "single mom", "single mum", "new mom", "new dad", "first time mom", "stepdad", "stepmom", "yes"),
                        "expecting": ("expecting", "pregnant", "expecting a child", "expecting a baby"),
                        "no children": ("no children", "no kids", "child free", "childfree", "child-free", "not parent", "not a parent", "childless")},
    "political_compass": {"authoritarian left": ("authoritarian left", "auth left", "authleft", "auth-left"),
                          "authoritarian right": ("authoritarian right", "auth right", "authright", "auth-right"),
                          "libertarian left": ("libertarian left", "lib left", "libleft", "lib-left"),
                          "libertarian right": ("libertarian right", "lib right", "libright", "lib-right"), "centrist": ("centrist", "center", "centre")},
    "political_ideology": {"anarchist": ("anarchist", "anarchism"), "communist": ("communist", "communism", "marxist", "marxist-leninist"),
                           "socialist": ("socialist", "socialism", "democratic socialist"), "progressive": ("progressive",), "liberal": ("liberal",),
                           "centrist": ("centrist", "moderate"), "conservative": ("conservative",), "libertarian": ("libertarian",),
                           "nationalist": ("nationalist",)},
}
LANGUAGE_ALIASES = {"mandarin": "chinese", "cantonese": "chinese", "filipino": "tagalog", "farsi": "persian", "español": "spanish", "français": "french",
                    "deutsch": "german", "português": "portuguese", "italiano": "italian", "nederlands": "dutch", "русский": "russian", "punjabi": "panjabi"}

KEYWORDS = {
    "education_subject": (
        ("computer and information sciences", r"computer science|\bcs\b|informatics|information technology|\bit\b|\bict\b|software|data science|cyber ?security|computing"),
        ("engineering", r"engineering"),
        ("psychology", r"psych"),
        ("biological and biomedical sciences", r"biolog|biochem|zoology|microbio|genetics|neuroscience|ecology|botany|biotech|biomedical"),
        ("physical sciences", r"physics|chemistry|astronomy|geology|astrophysics"),
        ("mathematics and statistics", r"\bmath|statistic"),
        ("health professions", r"nursing|medicine|medical|pharmac|\bbsn\b|dentist|public health|health science|kinesiology|physiotherapy|physical therapy|\bpre-?med"),
        ("business, management, and marketing", r"business|accounting|finance|marketing|\bmba\b|management|economics and business|commerce"),
        ("social sciences", r"economics|sociology|political science|anthropology|international relations|\bppe\b|geography|criminology"),
        ("history", r"history"),
        ("law", r"\blaw\b|legal studies"),
        ("education", r"^education$|teaching|pedagogy"),
        ("english language and literature", r"english|literature|creative writing"),
        ("foreign languages, literatures, and linguistics", r"linguistics|languages|japanese|spanish|french|german"),
        ("philosophy and religious studies", r"philosophy|religious studies"),
        ("visual and performing arts", r"\bart\b|fine arts|music|film|theater|theatre|dance|graphic design|animation|photography"),
        ("communication and journalism", r"journalism|communications?$|media studies"),
        ("architecture", r"architecture"),
        ("agriculture and veterinary science", r"veterinar|\bvet\b|agricultur|animal science"),
    ),
    "occupation": (
        ("military specific", r"\bsoldier|\barmy\b|\bnavy\b|air force|military|\bmarines?\b(?! bio)|veteran"),
        ("computer and mathematical", r"software|developer|programmer|\bdev\b|data scien|data analyst|web dev|sysadmin|system administrator|\bit\b|devops|coder|statistician|actuary|cyber"),
        ("healthcare practitioners and technical", r"\bnurse|\brn\b|doctor|physician|surgeon|pharmacist|dentist|paramedic|\bemt\b|veterinarian|\bvet\b|radiolog|therapist|resident|dietitian|optometrist|anesthesi|pathologist|\bmedic\b"),
        ("healthcare support", r"\bcna\b|medical assistant|caregiver|home health|dental assistant|phlebotom"),
        ("educational instruction and library", r"teacher|professor|lecturer|tutor|librarian|educator|instructor|\bta\b"),
        ("legal", r"lawyer|attorney|paralegal|judge|solicitor|barrister"),
        ("protective service", r"police|\bcop\b|firefighter|security guard|sheriff|correctional|detective|lifeguard"),
        ("food preparation and serving related", r"\bcook\b|\bchef\b|server|waiter|waitress|bartender|barista|dishwasher|line cook|prep cook"),
        ("building and grounds cleaning and maintenance", r"janitor|cleaner|housekeep|landscap|gardener|custodian"),
        ("personal care and service", r"hairdress|barber|nanny|childcare|babysit|stylist|personal trainer|fitness instructor|flight attendant"),
        ("life, physical, and social science", r"scientist|biologist|chemist|physicist|researcher|psychologist|economist|geologist|historian|lab tech"),
        ("community and social service", r"social worker|counselor|counsellor|pastor|priest|minister|chaplain"),
        ("architecture and engineering", r"engineer|architect|drafter|surveyor"),
        ("arts, design, entertainment, sports, and media", r"artist|writer|author|designer|musician|content creator|streamer|journalist|photographer|actor|actress|editor|youtuber|cam model|illustrator|animator|dj\b|athlete|coach|reporter"),
        ("business and financial operations", r"accountant|financial|analyst|consultant|auditor|recruiter|\bhr\b|underwriter|bookkeep|project manager"),
        ("management", r"manager|\bceo\b|\bcto\b|founder|director|executive|business owner|owner of|entrepreneur|supervisor|administrator"),
        ("sales and related", r"sales|cashier|retail|realtor|real estate agent|insurance agent"),
        ("office and administrative support", r"receptionist|secretary|clerk|admin|customer service|call center|data entry|office assistant"),
        ("farming, fishing, and forestry", r"farmer|rancher|fisherman|logger"),
        ("construction and extraction", r"construction|electrician|plumber|carpenter|roofer|laborer|miner|welder"),
        ("installation, maintenance, and repair", r"mechanic|technician|hvac|repair|maintenance"),
        ("production", r"machinist|factory|assembly|manufactur|baker|butcher"),
        ("transportation and material moving", r"driver|trucker|pilot|warehouse|delivery|forklift|courier|bus driver"),
    ),
}
LOOKUP = {field: {word: value for value, words in groups.items() for word in words} for field, groups in WORDS.items()}
PARENT = re.compile(r"(?:single |new |first time |proud |step-?)?(?:mom|mum|mother|dad|father|parent)(?: of (?:a |an |one|two|three|four|five|\d+|my).*)?"
                    r"|(?:has|have|with) (?:a |an |one |two |three |four |five |\d+ |young |grown |adult )*(?:kids?|child(?:ren)?|sons?|daughters?|toddlers?|babies|baby)"
                    r"|(?:one|two|three|four|five|\d+) (?:kids|children|sons|daughters)")
HEIGHT_IMPERIAL = re.compile(r"^(\d)\s*(?:'|’|ft\.?|feet|foot)\s*(?:(\d{1,2}(?:\.\d)?)\s*(?:\"|”|''|’’|in\.?|inches)?)?$")
HEIGHT_METRIC = re.compile(r"^(\d(?:[.,]\d{1,2})?)\s*m$|^(\d(?:[.,]\d{1,2}))$|^(\d{3}(?:\.\d+)?)\s*(?:cm)?$")
NUMBER = re.compile(r"^\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|m|thousand|million)?\s*(kg|kgs|kilos?|lbs?|pounds?|st|stone|usd|dollars|/yr|/year|a year|per year|gross|gross/year)?$")


def clean(raw):
    value = raw.strip().strip("*_`").strip().lower().rstrip(".")
    if value.startswith(("\"", "'")):
        value = value.strip("\"'")
    if EMPTY.match(value) or DROP.search(value) or len(value) > 60:
        return None
    return value


def number(value):
    match = NUMBER.match(value)
    if not match:
        return None, None
    amount = float(match.group(1).replace(",", ""))
    scale = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}.get(match.group(2), 1)
    return amount * scale, match.group(3)


def bounded(field, amount):
    low, high = NUMERIC[field]
    return str(round(amount)) if amount is not None and low <= round(amount) <= high else None


def height(value):
    if match := HEIGHT_IMPERIAL.match(value):
        return bounded("height", (int(match.group(1)) * 12 + float(match.group(2) or 0)) * 2.54)
    if match := HEIGHT_METRIC.match(value):
        if match.group(3):
            return bounded("height", float(match.group(3)))
        return bounded("height", float((match.group(1) or match.group(2)).replace(",", ".")) * 100)
    return None


def weight(key, value):
    amount, unit = number(value)
    if amount is None:
        return None
    if unit in ("st", "stone"):
        amount *= 6.35
    elif unit in ("lb", "lbs", "pound", "pounds") or (key == "weight_lbs" and unit is None):
        amount *= 0.4536
    return bounded("weight", amount)


def income(key, value):
    amount, unit = number(value)
    if amount is None or unit in ("kg", "kgs", "kilo", "kilos", "lb", "lbs", "pound", "pounds", "st", "stone"):
        return None
    return bounded("income", amount * INCOME_SCALE.get(key, 1))


def country(value, demonyms=False):
    value = COUNTRY_ALIASES.get(value, value)
    if demonyms:
        value = DEMONYMS.get(value, value)
    return value if value in COUNTRIES else None


def state(value):
    value = STATES.get(value, value)
    return value if value in STATE_NAMES else None


def city(value):
    value = CITIES.get(value, CITY_SUFFIX.sub("", value))
    if not re.fullmatch(r"[a-z][a-z .'-]{0,39}", value) or value in COUNTRIES or value in COUNTRY_ALIASES or value in STATES:
        return None
    return value


def keyword(field, value):
    for result, pattern in KEYWORDS[field]:
        if re.search(pattern, value):
            return result
    return None


def first(value):
    return re.split(r"\s*(?:,|/|;|&|\band\b|\+)\s*", value)[0]


def several(value):
    return [part for part in re.split(r"\s*(?:,|/|;|&|\band\b|\+)\s*", value) if part]


def race(value):
    parts = {LOOKUP["race_ethnicity"].get(part) for part in several(value)}
    if None in parts:
        return None
    return parts.pop() if len(parts) == 1 else "multiracial"


def gender(value):
    if match := re.fullmatch(r"(?:\d{2})?\s*([mf])\s*(?:4|for)\s*[mfa]\w*(?:\s*\d{2})?|(?:\d{2})\s*([mf])", value):
        return "male" if (match.group(1) or match.group(2)) == "m" else "female"
    return LOOKUP["gender"].get(value)


def value(field, raw, key=None):
    text = clean(raw)
    if text is None:
        return None
    if field == "age":
        match = re.fullmatch(r"(\d{1,3})(?:\s*(?:years?|yrs?|y/?o)(?:\s*old)?)?", text)
        return bounded("age", int(match.group(1))) if match else None
    if field == "birth_year":
        return bounded("birth_year", int(text)) if re.fullmatch(r"\d{4}", text) else None
    if field == "height":
        return height(text)
    if field == "weight":
        return weight(key, text)
    if field == "income":
        return income(key, text)
    if field == "gender":
        return gender(text)
    if field == "race_ethnicity":
        return race(text)
    if field == "nationality":
        return country(text, demonyms=True)
    if field in ("residence_country", "origin_country"):
        return country(text)
    if field in ("residence_state", "origin_state"):
        return state(text)
    if field in ("residence_city", "origin_city"):
        return city(text)
    if field == "language":
        text = LANGUAGE_ALIASES.get(text, text)
        return text if text in LANGUAGES else None
    if field in KEYWORDS:
        return None if text in ("student", "unemployed", "retired", "employed") else keyword(field, text)
    if field == "parental_status" and PARENT.fullmatch(text):
        return "parent"
    if field == "mental_health":
        return LOOKUP[field].get(first(text))
    return LOOKUP[field].get(text)


def parse(answer):
    values = {}
    for line in (answer or "").splitlines():
        key, _, raw = line.strip().lstrip("-*• ").partition(":")
        key = key.strip().strip("*").strip().lower()
        field = KEYS.get(key, key)
        if field not in FIELDS or ":" in raw or field in values:
            continue
        if (result := value(field, raw, key)) is not None:
            values[field] = result
    return values if len(values) <= 12 else {}
