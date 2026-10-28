import json
import math
import re
from collections import Counter, defaultdict
from functools import cache
from itertools import islice
from pathlib import Path
from re import _constants as sre
from re import _parser as sre_parse

from .config import NUMERIC, WEIGHTS
from .normalize import CITIES as CITY_ALIASES
from .normalize import COUNTRIES, COUNTRY_ALIASES, DEMONYMS, LANGUAGE_ALIASES, LANGUAGES, LOOKUP, REGIONS, STATE_NAMES, STATES, country, number, state, value

CITIES = json.loads(Path(__file__).with_name("cities.json").read_text(encoding="utf-8"))
VALUES = json.loads(Path(__file__).with_name("values.json").read_text(encoding="utf-8"))

I = r"(?:i'm|im|i am|i \([^)\n]{1,12}\) am|i \([^)\n]{1,12}\)'m)"
A = r"(?:an? )?"
END = r"(?=$|[\s.,!?;:)\]/]|'s)"
STRICT_TAG = r"(?:\b\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?"


def words(field):
    return "(?:" + "|".join(re.escape(word) for word in sorted(LOOKUP[field], key=len, reverse=True) if len(word) > 3) + ")"


RELIGIONS = words("religion")
CONDITIONS = "(?:" + "|".join(re.escape(word) for word in sorted(set(LOOKUP["mental_health"]) - {"add", "ed", "borderline"}, key=len, reverse=True)) + "|an eating disorder)"
SEVERITY = r"(?:(?:severe|chronic|diagnosed|mild|moderate|clinical|major|pretty|really|bad|terrible|crippling|unmedicated|untreated|official|some|a|an|both|combined|inattentive|high functioning|level \d) )*"
AMOUNT = (r"(?:\$\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|mil|million)?|\d[\d,]*(?:\.\d+)?\s?(?:k|m|mil|million)\b|\d{2,3},\d{3}\b"
          r"|\d{1,3}(?:\.\d{1,2})?(?=\s*(?:an|a|per|/)\s*(?:hour|hr)\b))")
PERIOD = (r"(?:\s*(?:a|an|per|/|every)\s*(?:year|yr|annum|month|mo|hour|hr|week|wk)\b|\s*(?:annually|yearly|monthly|hourly|weekly|/h)\b"
          r"|\s+(?:tc|base|salary|gross|pre[- ]tax|before tax|after tax|take home|ote)\b)?")
ROUGHLY = r"(?:about |around |roughly |like |over |under |almost |nearly |~|just |only |a little over |close to |approximately |a bit over |upwards of )?"
INCOME_ANY = re.compile(rf"(?<![\w.,])({AMOUNT}{PERIOD})")
NOT_SAVINGS =r"(?! (?:together|combined|between us|in (?:savings|debt|loans?)))"
DEGREES = r"(?:bachelor'?s|bachelors|bachelor|master'?s|masters|master|phd|ph\.d\.?|doctorate|associate'?s|associates|bsc|msc|mba|ba|bs|ma|ms|jd|md|bcom|beng|meng|mph|msw|edd|pharmd|dvm)"
SUBJECT_END = r"(?=$|[.,!?;:)\]/]| at | from | and | but | so | with | because | which | where | in \d| in the | i | while | before | after | for | to )"
NOT_DEMONYM = r"(?!(?:french|german|spanish|japanese|chinese|korean|italian|international|exchange|foreign|indian|asian)\b)"
GENERATIONS = words("generation")
IDEOLOGIES = words("political_ideology")
LANGUAGE_NAMES = "(?:" + "|".join(sorted((*LANGUAGES, *LANGUAGE_ALIASES), key=len, reverse=True)) + ")"
COUNTRY_NAMES = "(?:" + "|".join(re.escape(name) for name in sorted((*COUNTRIES, *COUNTRY_ALIASES), key=len, reverse=True) if len(name) > 2) + ")"
ORIENTATIONS = "(?:" + "|".join(re.escape(word) for word in sorted(LOOKUP["sexual_orientation"], key=len, reverse=True) if len(word) > 2) + "|bi)"
RACES = words("race_ethnicity")
DEMONYM_NAMES = "(?:" + "|".join(re.escape(name) for name in sorted(DEMONYMS, key=len, reverse=True)) + ")"
NOT_INSTITUTION = r"(?! (?:school|church|family|friends?|parents|household|university|college|majority|country|state))"
TAG = r"[\(\[]?\s*(?:(\d{2})\s*/?\s*([mf])|([mf])\s*/?\s*(\d{2}))\s*[\)\]]?"
TAG_SELF = re.compile(r"(?:^|\b(?:i'm|im|i am|i|me|myself)\b\s*)" + TAG + r"(?![a-z0-9])", re.M)
TAG_ANY = re.compile(r"(?<![\w$.,'#/])" + TAG + r"(?![a-z0-9'])")
TAG_DASH = re.compile(r"(?<![\w$.,'#/-])(?:(\d{2})y?\s?[-_]\s?([mf])|([mf])\s?[-_]\s?(\d{2}))(?![a-z0-9'-])")
AGE_START = re.compile(r"^[^\w$€£~]{0,3}(?:an? )?(\d{2})(?![\d.:%x'-]|/\s*\d|\s*(?:%|percent|years? ago|yrs? ago|minutes|mins?\b|hours|hrs?\b|days|weeks|months|times|seconds|secs?\b|th\b|st\b|nd\b|rd\b|k\b|mph|kph|km|miles|cm|mm|inch|lbs?\b|kg|people|of\b|out\b|to\b|or\b|-\d|\+)|,(?!\s+\D)|(?![mfty]\b|nb|[mf]{1,3}4|yo\b|y/o|yrs?\b|ftm|mtf)[a-z]|\s*[?!€\"”]|\s+years?\?|\s*(?:and|&|//?|–)\s*\d|\s+(?:is|in|plus|bucks|dollars|volts?|million|mil|hp|pro|hours?|more|was|march|euros?|karma|ways|fps|milliarden)\b)")
AGE_BRACKET = re.compile(r"[\[\(]\s*(\d{2})\s*[\]\)]")
HEIGHT_ANY = re.compile(r"(?<![\w.$/-])(?<!over )(?<!under )(?<!than )([4-7]\s*(?:'|ft\.?|foot|feet)\s*(?:1[01]|0?\d)(?:\.\d)?\s*(?:\"|”|''|in\b|inches)?|[4-7]\s*[\"”]\s*(?:1[01]|\d)(?!\d|\.\d)|[4-7]\s*(?:ft\.?|foot|feet)\b|[4-7]\s*(?:')(?=\s*(?:tall|height|hung|,|\d|with\b|and\b|[.!)|/]|$)))(?![\w']|\s*\?)")
WEIGHT_AFTER = re.compile(r"(?:[4-7]\s*(?:'|ft\.?|foot|feet)\s*(?:1[01]|\d)?\s*(?:\"|”|''|in\b|inches)?|1[4-9]\d\s?cm|1[.,][4-9]\d\s?m?)\s*[,/|;-]?\s*(\d{2,3})(?![\d.]|\s*(?:cm|in\b|inch|%|years?|yo\b|y/o|yrs?))")
WEIGHT_ANY = re.compile(r"(?<![\w.$/-])(\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kgs?|kilos))\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain))")
HEIGHT_METRIC = re.compile(r"(?<![\w.,$])(1[4-9]\d\s?cm|2[0-2]\d\s?cm|1[.,][4-9]\d\s?m\b|1[.,][4-9]\d(?![\d,%]|\.\d|\s*(?:€|eur|usd|dollars?|bucks|km|miles?|mi\b|hours?|h\b)))")
PEOPLE = re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|they|they're|husband|wife|bf|gf|boyfriend|girlfriend|son|daughter|brother|sister|dad|mom|guy is|girl is|you|you're|ur)\b")
PRIMES = str.maketrans({"‘": "'", "’": "'", "´": "'", "′": "'", "″": '"', "ʻ": "'", "ʼ": "'", "​": None, "‌": None, "‍": None, "⁠": None, "﻿": None})
OTHER = re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|they|they're|husband|wife|bf|gf|boyfriend|girlfriend|son|daughter|brother|sister|dad|mom|guy is|girl is|you|you're|ur|lost|from|down|goal|want|wants)\b")
ADJECTIVES = r"(?:straight|gay|bi|white|black|asian|single|married|cis|trans|latino|hispanic|indian|fit|tall|short|chubby|fat|hot|horny|lonely|bored|average|older|young)"
AGE_GENDER = re.compile(r"(?<!\ba )(?<!\ban )(?<!\bmy )(?<!\byour )(?<!\bthe )(?<!\bher )(?<!\bhis )(?<![\w$#.-])(\d{2})\s*(?:yo|y/o|y\.o\.|yrs?|years?[- ]old|yrs?[- ]old)?\s*,?\s*(?:(?:" + ADJECTIVES + r"|(?!years?\b|ago\b|of\b|and\b|or\b|the\b|a\b|an\b|to\b|for\b|with\b|people\b|times?\b|minutes?\b|hours?\b|days?\b|weeks?\b|months?\b)[a-z]+)\s+){0,2}(male|female|man|woman|guy|girl|dude|lady|boy)\b(?! (?:squads?|groups?|teams?|content|raids?|hours?))")
GENDER_AGE = re.compile(r"(?<!\ba )(?<!\bthe )(?<!\bthis )(?<!\bhey )(?<!\bmy )\b(male|female|guy|girl|man|woman|dude|lady),?\s*(\d{2})\b(?!\s*(?:%|years? ago)|[a-z])")
GENDER_BRACKET = re.compile(r"(?:^|(?<=[\s\d]))[\(\[]\s*([mf])\s*[\)\],]")
GENDER_PAREN = re.compile(r"\b(male|female|guy|girl|man|woman|dude|lady|boy|[mf])\s*\(\s*(\d{2})\s*\)")
TOKEN = re.compile(r"[a-z0-9](?:[a-z0-9']|-(?=[a-z0-9]))*|[^\sa-z0-9]")
NUMBER = re.compile(r"(?<![\w.,$/:#-])(\d{2})(?:\s?(?:yo|y/o|y\.o|yrs?|years?|y)|-(?:years?|yrs?|yo|y)(?:[- ]old)?)?(?![\w:/%-]|[.,]\d|\s*%)")
BARE_NUMBER = re.compile(r"^\W*(\d{1,3})\W*$")
YEAR = re.compile(r"(?<![\w$#.,/:-])((?:19[2-9]|200)\d|201[0-3])(?![\w%/:-]|[.,]\d)")
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
TEENS = {"thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
WORD_NUMBER = re.compile(rf"\b(?:({'|'.join(TENS)})(?:[- ]({'|'.join(UNITS)}))?|({'|'.join(TEENS)}))\b")
MATCHES = 3
BROAD = ("vocab", "number", "from_city", "from_state", "from_nationality", "amount", "year")
SELF = {"i", "i'm", "im", "me", "my", "myself"}
VOCAB_MATCHES = 4
VOCAB_FIELDS = ("race_ethnicity", "sexual_orientation", "religion", "marital_status", "relationship_status", "mental_health", "political_ideology",
                "generation", "employment_status")
GENDER_WORDS = {"male", "female", "man", "woman", "guy", "girl", "dude", "lady", "boy", "gal", "mom", "dad", "wife", "husband", "mother", "father",
                "non-binary", "nonbinary", "enby", "trans woman", "trans man", "femboy", "milf", "bloke", "lad", "girlie", "girly", "wifey", "hubby",
                "mtf", "ftm", "transgirl", "transguy", "trans girl", "trans guy", "homme", "mann", "mec", "hombre", "mujer", "chica", "chico", "frau",
                "homem", "mulher", "ragazzo", "ragazza"}
PARENT_WORDS = {f"{owner} {child}" for owner in ("my", "our") for child in ("son", "daughter", "kids", "kid", "children", "child", "baby", "toddler", "boys", "girls",
                                                                  "newborn", "stepson", "stepdaughter", "sons", "daughters", "twins", "grandkids",
                                                                  "son's", "daughter's", "kid's", "kids'", "baby's", "children's")} | {"pregnant"}
SUBJECT_WORDS = {"computer science", "engineering", "psychology", "biology", "chemistry", "physics", "mathematics", "math", "nursing", "medicine", "business",
                 "accounting", "finance", "marketing", "economics", "sociology", "political science", "history", "law", "education", "english", "philosophy",
                 "art", "music", "film", "journalism", "architecture", "statistics", "neuroscience", "biochemistry", "linguistics", "anthropology"}
BARE_TAG = re.compile(r"^\W*(?:[mf]\s*\d{2}|\d{2}\s*[mf])\W*$")
LEAD = re.compile(r"\W*(?:\d{2}\s?[mf]\b|[mf]\s?\d{2}\b|\[?[mf]4)")
DIGIT = re.compile(r"\d")
LEAD_WORD = re.compile(r"\W*([a-z0-9][a-z0-9'-]*)")
PRONOUN_TAG = re.compile(r"\b(she|he|they)\s*/\s*(?:her|hers|him|his|them|they|she|he)\b")
PRONOUN_GENDER = {"she": "female", "he": "male", "they": "non-binary"}
BARE_GENDER = re.compile(r"^\W*([mf])\W*$")
RACE_GENDER = re.compile(r"(?<![\w$#.,'/])\d{2}\s?[wbh]([mf])\b")
TAG_FOR = re.compile(r"(?<![a-z0-9])(\d{2})?\s*[\[\(]?\s*([mf])\s*4\s*[mfatr][a-z]*(?:\s*[\]\)]?\s*[-–|:]?\s*(\d{2})\b)?", re.M)

JOBS = json.loads(Path(__file__).with_name("jobs.json").read_text(encoding="utf-8"))
JOB_TITLES = "(?:" + "|".join(re.escape(title) for title in sorted(JOBS, key=len, reverse=True)) + ")"
JOB_HEADS = (r"(?:nurse|rn|teacher|professor|lecturer|tutor|librarian|doctor|physician|surgeon|dentist|pharmacist|paramedic|emt|therapist|psychologist|"
             r"engineer|developer|programmer|dev|architect|scientist|biologist|chemist|physicist|researcher|economist|lawyer|attorney|paralegal|"
             r"electrician|plumber|carpenter|welder|mechanic|technician|firefighter|cop|police officer|officer|soldier|veteran|vet|veterinarian|"
             r"chef|cook|bartender|barista|server|waiter|waitress|cashier|accountant|analyst|consultant|manager|director|ceo|founder|"
             r"designer|artist|writer|author|journalist|photographer|musician|editor|streamer|youtuber|content creator|illustrator|animator|"
             r"driver|trucker|truck driver|pilot|flight attendant|social worker|counselor|counsellor|pastor|priest|realtor|farmer|"
             r"janitor|cleaner|landscaper|hairdresser|barber|nanny|caregiver|cna|receptionist|secretary|clerk|recruiter|"
             r"machinist|baker|butcher|contractor|sysadmin|data scientist|actuary|auditor|banker|broker|salesman|sales rep|lifeguard|coach)")
JOB_MODIFIERS = (r"(?:registered|licensed|certified|senior|junior|full[- ]time|part[- ]time|high school|middle school|elementary school|elementary|"
                 r"special ed|professional|freelance|self[- ]employed|practicing|working|qualified|trained|practising|new|young|lead|head|staff|"
                 r"\d{2}[- ]?(?:years?|yr)[- ]old|\d{2}(?: ?[mf])?|male|female|woman|man|black|white|gay|straight|trans)")

JOB = rf"(?:{JOB_MODIFIERS} )*((?:[a-z]+ ){{0,2}}(?:{JOB_TITLES}|{JOB_HEADS})){END}"
PLACE = r"([a-z][a-z.'-]*(?:,? [a-z][a-z.'-]*){0,3})"

PHRASES = {
    "age": (rf"\b{I} (?:only |almost |nearly |just |now |about |turning |currently )?(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?{END}(?! (?:years? ago|minutes|hours|days|weeks|months|times|percent|%|lbs?|kg|pounds))",
            rf"\b{I} {A}(\d{{2}})[- ]?(?:years?|yr)[- ]old\b", r"\bas an? (\d{2})[- ]?(?:years?|yr)[- ]old\b", r"(?:\bi(?:'ve| have)? |^|[.!?,] )(?:just |recently )?turned (\d{2})\b(?! (?:years|minutes|weeks|percent|%))",
            r"\ban? (\d{2}) ?(?:yo|y/o)\b", r"\b(?:tengo|tenho|j'ai) (\d{2}) (?:años|anos|ans)\b", r"(?:\bich |^)bin (\d{2})\b",
            r"\bmy age is (\d{2})\b", r"\bi'?m (\d{2}) now\b",
            r"(?:[\[\(]\s*[mf]\s*[\]\),]|(?:^|[\s,])[mf]\s*,)\s*,?\s*(\d{2})\b(?![\d%.,:]|\s*(?:min|mins|minutes|hours|days|%|cm|kg|lbs?|inch|in\b))",
            r"\bage\s*[:=-]\s*(\d{2})\b(?!\s*[-–+]|\s*to\b)",
            r"\b(?:tengo|tenho) (\d{2})\b(?! (?:años de|anos de|meses|dias|días|horas|semanas|mil))",
            r"(?:^|[\s,(\[])(\d{2})\s+(?:milf|married|bi|uk|bbw|wife|mom|dilf|hubby|daddy|cuck|sissy|femboy|twink|bottom|top|bull|virgin|teen|petite|curvy)\b",
            r"\b(?:we're|we are|were|are) both (\d{2})\b",
            r"(?<!\bmy )(?<!\byour )(?<!\bthe )(?<!\bher )(?<!\bhis )(?<!\bour )(?<!\btheir )(?<!\bfav )(?<!\baverage )(?<!\bold )(?<!\ban )(?<!\ba )(?<!\bshe )(?<!\bhe )"
            r"(?:^|(?<=[\s,(]))(\d{2})\s?(?:yo|y/o|y\.o\.?)\b(?! (?:son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat))",
            r"(?:^|[.!?\n] *)at (\d{2}),", r"(?:^|[.!?\n] *)(?:being |now )?(\d{2}) years? old\b",
            r"\bmy (\d{2})[- ]?(?:years?|yrs?|y/?o)[- ]?(?:old )?(?:ass|body|self|pussy|cock|dick|tits|butt|bones|knees|back|brain|eyes)\b",
            r"\b(?:mam|imam|tengo|ho|har|heb|jestem|sam|tenho|j.ai|bin) (\d{2})\s*(?:lat|godin|años|anos|anni|år|jaar|ans|jahre|tuổi)",
            r"\b(?:age|aged)\s*[:\-]?\s*(\d{2})\b(?!\s*[-–+]|\s*(?:to|and|or|through|plus)\b)(?=\s*(?:$|[,.!)]|\s*[mf]\b|\s+(?:here|and|looking|woke|male|female|guy|girl|man|woman)))",
            r"\b(\d{2})\s?(?:yo|y/o|y\.o\.?)\s+(?:male|female|guy|girl|man|woman|dude|lady|m|f)\b", r"(?:^|[.!,;] )me (\d{2})\b",
            r"(?:^|[\s(\[])(\d{2})\s*(?:top|bottom|vers|hung|bwc|bbc|sub|dom|twink|daddy)\b", r"\b(\d{2})(?:st|nd|rd|th) birthday\b",
            r"\bat (\d{2}) now\b|\bnow at (\d{2})\b|\bat the age of (\d{2})\b"),
    "birth_year": (r"(?:\bi(?:'m| am|m)? (?:was )?|\(|^)born (?:in |on )?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (?:\d{1,2}(?:st|nd|rd|th)?,? )?)?((?:19|20)\d\d|'?[4-9]\d)\b",
                   rf"\b{I} (?:a |an )?((?:19|20)\d\d)\b(?! (?:model|edition|version|car|truck))", r"(?:^|[.!,;(] *)((?:19|20)\d\d) (?:baby|babies|kid|here)\b",
                   r"(?:\bbeing |, |[.!;] )born (?:in |on )?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (?:\d{1,2}(?:st|nd|rd|th)?,? )?)?((?:19|20)\d\d|'?[4-9]\d)\b",
                   r"^\W*((?:19[3-9]|200)\d|201[0-3])\W*$",
                   r"^\W*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?,? |\d{1,2}/\d{1,2}/)((?:19[3-9]|200)\d)\W*$",
                   r"\bborn (?:in |on )?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (?:\d{1,2}(?:st|nd|rd|th)?,? )?|\d{1,2}[./-]\d{1,2}[./-])?((?:19|20)\d\d|'?(?:[4-9]\d|0\d|1[0-3]))\b(?! (?:years?|yrs?|months?|weeks?|days?|hours?|minutes?|mins?)\b)",
                   r"\b(?:dob|d\.o\.b\.?|date of birth|birth ?date)\s*(?:is\s*)?[:=-]?\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?,? |\d{1,2}(?:st|nd|rd|th)? (?:of )?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*,? |\d{1,2}[./-]\d{1,2}[./-])?((?:19|20)\d\d)\b",
                   r"\bborn (?:and raised )?in (?:[a-z]+,? ){1,3}in ((?:19|20)\d\d)\b"),
    "generation": (rf"\b{I} {A}(millennial|boomer|baby boomer|gen ?z|gen ?x|zoomer|gen alpha)\b", r"\bas an? (millennial|boomer|gen ?z(?:er)?|gen ?x(?:er)?|zoomer)\b",
                   rf"(?:^|[.!,;(] *)(?:[a-z]+ )?({GENERATIONS}) here\b", rf"\b{I} (?:a |an |also a |also an |also |an old |a young |a fellow |an elder |an older |a younger |a late |an early |a geriatric )?({GENERATIONS})\b(?! (?:parents|kids|children|friends|generation))", rf"\bwe ({GENERATIONS})\b"),
    "gender": (rf"\b{I} {A}(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who))",
               r"\bas an? (?:\d{2}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|mom|mother|dad|father|wife|husband)\b",
               rf"\b{I} {A}(non-?binary|nonbinary|enby|agender|genderfluid|gender fluid|genderqueer|trans (?:man|woman|guy|girl))\b",
               r"(?<!\ba )(?<!\bthe )(?<!\bother )(?<!\bthat )(?<!\bthis )\b(male|female|guy|girl|man|woman|dude|lady)\s+here\b",
               r"(?:^|[\]\)\-|:]\s*|\d{2}\s*,?\s*)(?:[a-z]+ ){0,2}?(male|female|guy|girl|man|woman|dude|lady|boy|femboy|milf)\s+(?:here\s+)?(?:looking|seeking|searching|wanting|needing)\b",
               r"\b(?:soy|sou|je suis|ich bin|sono) (?:un |una |uma |um |une |ein |eine )?(hombre|mujer|chica|chico|homem|mulher|homme|femme|mann|frau|ragazzo|ragazza|garota|garoto|menina|menino)\b",
               rf"\b{I} (?:a |an |also a |also an )(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?:autistic|bisexual|curious|bi-curious|bicurious|lesbian|queer|divorced|christian|muslim|catholic|jewish|mexican|indian|latina|latino|black|white|asian|cis|disabled|neurodivergent|married|single|gay|straight|trans|young|old|older|tall|short|fat|chubby|petite|curvy|skinny|fit|grown|normal|regular|average) ){{1,3}}(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who))",
               rf"\b{I} (?:also |just |only |still |literally |actually )?(?:a |an )(?:\d{{2}}\s?(?:yo|y/o|years? old|yr old|year-old)\s+)?(?:(?!good\b|bad\b|big\b|real\b|lucky\b)[a-z-]+ ){{0,3}}?(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who|that|and|or|you|in|on|with|from|for|like|than))",
               rf"\b{I} (?:also )?(?:an? )?(ftm|mtf|nb|enby|non-binary|nonbinary|transmasc|transfem|trans masc|trans fem|a transman|a transwoman)\b",
               r"(?:^|[\s(\[])\d0'?s\s+(?:[a-z]+\s+){0,2}?(male|female|guy|girl|man|woman|m|f)\b",
               r"(?:^|[\s(\[])\d{2}\s*,\s*([mf])\b(?!\s*[/']\s*\d)",
               r"[\(\[]\s*(male|female)\s*[\)\]]",
               r"[\[\(]\s*\d{2}\s*[\]\)]\s*([mf]|male|female)\b(?!\s*[/']?\s*\d)",
               rf"\b{I} ([mf])(?![\w'])",
               r"(?:^|[\s,(\]])(?:(?:single|married|bi|straight|gay|white|black|horny|young|older|old|fit|hung|discreet|bored|lonely|chubby|tall|short|local|cute|shy|sub|dom)\s+){0,2}([mf])\s+(?:here|looking|seeking|searching|4\b|for\b)",
               r"\bas an? (?!if\b)(?:[a-z-]+ ){0,2}?(guy|man|woman|girl|dude|male|female|lady|boy|mom|mother|dad|father|wife|husband)\b(?!'s| of\b)",
               r"\bthis is an? (?:[a-z-]+ )?(guy|man|woman|girl|dude|male|female|lady|boy)\b",
               rf"\b{I} (?!not\b|never\b|no\b)(?:[a-z-]+ ){{0,3}}?(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who|that|and|or|you|in|on|with|from|for|like|than))",
               rf"\b{I} [^.!?\n]{{0,30}}? and an? (?:[a-z-]+ ){{0,2}}?(guy|man|woman|girl|dude|lady|male|female)\b",
               r"(?:^|[,|/•]\s*)(male|female)\s*(?=[,|/•]|$)"),
    "sexual_orientation": (r"(?:^|\W)[\-|/]\s*(straight|gay|bi|bisexual)\s*[\-|/]",
                           r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:(?!not\b|seconds|minutes|mins|hours|days)[a-z]+\W+){0,2}?(straight|gay|bi|bisexual|lesbian)\b(?![-'])(?! (?:up\b|away\b|out\b|to\b|couples?|guys|men|women|porn|friends?|people|bar|club|scene|content|stuff))",
                           r"\b(straight|gay|bi|bisexual|lesbian|pansexual)\s+(?:[a-z]+\s+)?(?:male|female|guy|girl|boy|man|woman|dude|bottom|top|m|f)\s+here\b",
                           rf"\b{I} (?!not\b|never\b|no\b)(?:an? )?(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?!not\b|be\b|paid\b)[a-z]+ ){{0,2}}?(straight|gay|bi|bisexual|lesbian|pansexual|asexual|queer|heterosexual|homosexual)\b(?![-'])(?! (?:friend|couple|bar|club|marriage|people|men|women|guys|up\b|forward|away|out\b|from|to\b|with you|edge|talking|a\b))",
                           r"\bas an? (?:\d{2}[- ]?(?:years?|yr)[- ]old )?(?:(?:white|black|asian|trans|young|old|older) )*(straight|gay|bi|bisexual|lesbian|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude)\b",
                           rf"\bas an? (?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?({ORIENTATIONS})\b(?! (?:couple|bar|club|man's|woman's|ally|friend|show|character|porn|film|movie|icon|rights))",
                           r"\b(?:soy|sou|je suis|ich bin|bin|sono) (?:\w+ )?(gay|bi|bisexual|hetero|heterosexual|homosexual|lesbiana|lésbica|bissexual|bisexuel|bisexuelle|lesbienne)\b",
                           rf"(?:^|[.!,;] )(?:[a-z]+ )?({ORIENTATIONS}) here\b"),
    "race_ethnicity": (r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(white|black|asian|latino|latina|hispanic|indian|desi|arab|mixed|biracial|caucasian|chinese|filipina|filipino|korean|japanese|mexican|pakistani)\b(?! (?:women|men|girls|guys|people|couples?|cock|bull|dick))",
                       r"(?:^|[.!,;] )(white|black|asian|latino|latina|hispanic|desi|arab|caucasian|filipina|filipino|mexican) (?:[a-z]+ )?here\b",
                       rf"\b{I} {A}(?:[a-z]+ ){{0,3}}?(white|black|asian|hispanic|latino|latina|mixed|biracial|mixed race|native american|middle eastern|arab|caucasian)(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself))?{END}(?! (?:people|folks|neighborhood|area|community|friends|culture))",
                       r"\bas an? (white|black|asian|hispanic|latino|latina|mixed|biracial|mixed race|native american|middle eastern|arab) (?:man|woman|guy|girl|person|male|female|dude|american|mom|dad|mother|father)\b",
                       r"\bas an? (mexican|indian|chinese|korean|japanese|filipino|filipina|pakistani|desi|caucasian|african american|asian american)\b",
                       rf"\b({RACES}) (?:guy|girl|male|female|man|woman|couple|baddie|dude|bottom|top|bbw|milf|daddy|boy|twink|stud|bull|wife|hubby) (?:looking|with|here|seeking|wanting|needs|needing|in|from|for)\b",
                       rf"(?:lbs|kg|\d'\d{{1,2}}\"?|\d{{2}}\s?[mf]?)\s*,\s*({RACES})\s*[,./]"),
    "nationality": (rf"\b{I} (?:also )?{A}(american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swedish|norwegian|danish|finnish|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|chinese|japanese|korean|filipino|filipina|turkish|greek|portuguese|scottish|welsh|english|kiwi|aussie|brit|swiss|austrian|belgian|romanian|hungarian|czech|israeli|egyptian|nigerian|south african|argentinian|colombian|vietnamese|iranian|new zealander)(?: citizen)?{END}(?! (?:food|people|culture|company|government|accent|guy|girl|man|woman|friend))",
                    r"\bas an? (american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swede|norwegian|dane|finn|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|filipino|filipina|brit|aussie|kiwi|israeli|scot|new zealander)(?: citizen| person| myself)?\b(?! (?:company|government|food))",
                    r"(?:^|[.!,;] )(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican) here\b",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican|italian|french|polish|brazilian|turkish)\b(?! (?:women|men|girls|guys|food|people))",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\b(?:male|female|guy|girl|man|woman))\s+from (?:the )?(usa|us|uk|england|scotland|canada|australia|india|poland|italy|germany|france|spain|ireland|mexico|brazil|philippines|pakistan|turkey|netherlands|sweden|norway|denmark|portugal|greece|romania|egypt|nigeria|south africa|new zealand)\b",
                    rf"(?:\[\s?[mf]{{1,2}}4[mfa]\w*\s?\]|\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b|/\s?m\s?/)\W{{0,4}}({COUNTRY_NAMES}|{DEMONYM_NAMES})\b(?! (?:women|men|girls|guys|food|people|couples?))",
                    rf"\b{I} (?!not\b)(?:also |a |an |half |proudly )?({DEMONYM_NAMES})\b(?! (?:food|people|culture|company|government|accent|friend|girlfriend|boyfriend|wife|husband|music))"),
    "language": (r"\bmy (?:native|first|mother) (?:language|tongue) is ([a-z]+)\b",
                 rf"\b{I} {A}native ([a-z]+) speaker\b",
                 rf"\b(?:i|we) (?:only |also |can |do |mainly |mostly |natively |fluently |still )?(?:speak|talk in|grew up speaking) (?:fluent |native |only |some |basic |a little |good )?({LANGUAGE_NAMES})\b"),
    "religion": (rf"\b{I} (?!not\b|now\b)(?:also |a |an )?(?:[a-z]+ ){{0,2}}?(jew|{RELIGIONS}|not religious)\b{NOT_INSTITUTION}",
                 rf"\bas an? (jew|{RELIGIONS})\b{NOT_INSTITUTION}", rf"(?:^|[.!,;] )(?:[a-z]+ )?({RELIGIONS}) here\b",
                 rf"{STRICT_TAG}({RELIGIONS})\b(?! (?:women|men|girls|guys|people|wife|husband))"),
    "residence_country": (rf"\b(?:{I}|i live|we live|living|based|located|i stay|currently|i reside)\s+(?:(?:currently|still|now|actually|also|just|living|based|located|residing)\s+)?(?:in|near|around|outside(?: of)?)\s+(?:the\s+)?{PLACE}",
                          rf"#\s?{PLACE}", rf"\[?[mf]4[mfa]\w*\]?\W{{0,4}}{PLACE}",
                          rf"(?:\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b|[mf]4[mfa]\w*\]?|\b\d{{2}})\s+(?:\w+\s+)?(?:in|from)\s+(?:the\s+)?{PLACE}",
                          rf"\b(?:hello|hi|greetings|hey|hallo|hola) from (?:the )?{PLACE}",
                          rf"\b(?:and|but|also|who|still|we|currently) live in (?:the )?{PLACE}",
                          rf"\bi (?:just |recently |finally )?(?:moved|relocated) to (?:the )?{PLACE}",
                          rf"\b(?:location|loc|based|area)\s*[:\-]\s*{PLACE}",
                          rf"\b(?:male|female|guy|girl|man|woman|couple|bull|dom|sub|top|bottom|dude|lady)\s+(?:here\s+)?(?:in|near|around) (?:the )?{PLACE}",
                          rf"(?:^|[\s(\[,|-])({COUNTRY_NAMES})[- ]based\b(?! (?:company|companies|firm|business|brand|startup|clients?|team|server|bank|agency))",
                          rf"\bmy (?:country|home country|nation)\s*\(\s*({COUNTRY_NAMES})\s*\)",
                          rf"\b(?:who|that) (?:lives|resides|is based|is living) in (?:the )?{PLACE}",
                          rf"\b{I} (?:a |an )?[a-z]+ (?:living |based |located )?in (?:the )?({COUNTRY_NAMES})\b",
                          rf"(?:\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b|\[\s?[mf]4\w+\s?\])\s*[-|,]\s*([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?)\s*(?:[-|,(]|$)",
                          r"\b(?:in|from|near) (?:the )?([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?)\s*\(\s*([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?) area\s*\)",
                          r"(?:^|[.!,;(\]|-]\s*)([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?)[- ]based\b(?! (?:company|companies|firm|business|brand|startup|clients?|team|server|bank|agency|band|artist|rapper))",
                          r"(?:^|[\s,(])([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?) (?:resident|local)\b(?! (?:evil|news|police|business|government|election|elections))",
                          rf"\b(?:i(?:'ve| have|ve)|we(?:'ve| have)) (?:always |only |now |just |mostly )?(?:lived|been living|been) in (?:the )?{PLACE}",
                          rf"\b(?:i|we) live (?:on|in) the (?:[a-z]+ )?[a-z]*(?:side|part|outskirts|suburbs|edge|area|middle) of (?:the )?{PLACE}",
                          rf"\b{I} (?:in |from )?([a-z][a-z.'-]*(?: [a-z][a-z.'-]*)?)[- ]based\b",
                          rf"\b(?:vivo|moro|resido|estoy|estou|je vis|j'habite|ich wohne|ik woon|abito) (?:en|em|in|à|a|au|aux|no|na|nel|nella|dans)\s+(?:le |la |les |l'|el |o |a )?([^\W\d_]+(?:[ -][^\W\d_]+){{0,2}})",
                          rf"\bmy (?:home )?(?:state|city|town|country)(?: is|,|:)? (?:of )?{PLACE}"),
    "origin_country": (rf"\b{I} (?:originally )?from (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which | originally)",
                       r"\bi (?:was )?(?:born and raised|grew up|was born|was raised) in (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which )",
                       rf"\b(?:i|we) (?:just |recently |originally )?(?:moved|immigrated|emigrated|came|relocated) (?:here |over |to [a-z]+ |to the [a-z]+ )?from (?:the )?{PLACE}",
                       rf"(?:, |\b(?:guy|girl|man|woman|male|female|year old|years old|yo|y/o|graduate|dude|student|lady|boy|couple|[mf]|\d{{2}}[mf]|i'm|im|i am|originally)\s+)from (?:the )?({COUNTRY_NAMES})\b",
                       rf"\b([a-z][a-z.'-]*(?: [a-z][a-z.'-]*){{0,2}}) born and (?:raised|bred)\b|\bborn and (?:raised|bred) in (?:the )?{PLACE}",
                       rf"\bas (?:someone|a person|a guy|a girl|somebody) (?:originally )?from (?:the )?{PLACE}",
                       rf"\b(?:{I}|i come|i came) (?:originally |also )?from (?:the )?({COUNTRY_NAMES})\b(?!\s+(?:to|and back))"),
    "height": (rf"\b{I} (?:an? |only |about |around |like |also )?(\d\s*(?:'|ft|foot|feet)\s*\d{{0,2}}(?:\"|”|in)?|\d\s*(?:')\s*\d{{1,2}}|1[4-9]\d\s*cm|2[0-2]\d\s*cm|1[.,]\d\d\s*m)(?=$|[\s.,!?;)])(?! (?:away|from|deep|wide|long|tall [a-z]+ (?:fence|wall|tree)))",),
    "weight": (r"\b(?:i |and |i currently |currently |my )?(?:weigh|weight|weighing|current weight)\s*(?:is|of|:|=|-|in at)?\s*(?:about |around |like |roughly |~)?(\d{2,3}(?:\.\d)?(?:\s?(?:lbs?|pounds|kgs?|kilos|kilograms|st|stone))?)\b(?!\s*(?:%|lbs? (?:of|more|less)|ago))",
               rf"\b{I} (?:currently |now )?(?:at )?(\d{{2,3}}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos))\b(?! (?:of|down|lost|heavier|lighter|more|less|weight))"),
    "income": (rf"\b(?:i|and|currently) (?:currently |only |still |now |also |probably |actually |personally |usually |typically )?(?:make|made|earn|earned|gross|grossed|net|netted|clear|take home|bring in|brought in)\s+{ROUGHLY}({AMOUNT}{PERIOD}){NOT_SAVINGS}",
               rf"\b{I} (?:currently |now |only |still )?(?:making|earning|grossing|netting|clearing|paid)\s+{ROUGHLY}({AMOUNT}{PERIOD}){NOT_SAVINGS}",
               rf"\bmy (?:annual |yearly |base |current |gross |net |total )?(?:salary|income|pay|wage|comp|compensation|tc|take home)(?: is| was|:| of| =)?\s*{ROUGHLY}({AMOUNT}{PERIOD})",
               rf"\bwe (?:make|earn|bring in|gross|take home)\s+{ROUGHLY}({AMOUNT}{PERIOD})",
               rf"\bi (?:currently |usually |only )?(?:bring home|take home|clear|pull in|pull)\s+{ROUGHLY}({AMOUNT}{PERIOD}){NOT_SAVINGS}",
               rf"\b(?:income|salary|annual income|yearly income)\s*[:=-]\s*{ROUGHLY}({AMOUNT}{PERIOD})"),
    "education": (rf"\bi (?:have|hold|got|earned|finished|did|completed|received|just got|just finished|am finishing|'m finishing|am doing|'m doing|am pursuing|'m pursuing|have done|also have|only have|already have) (?:a |an |my |a literal |only a |two |both )?({DEGREES}|college degree|university degree|law degree|medical degree)(?: degree| degrees)?\b",
                  rf"\bmy ({DEGREES})(?: degree)? (?:is |was )?in\b"),
    "education_subject": (rf"\bi(?:'m| am)? (?:currently )?(?:study|studied|studying|majored in|major in|majoring in|minored in|a student of|went to (?:college|school|uni|university) for) ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b(?:i (?:have|hold|got|earned|did|finished|completed|received|am doing|'m doing|am finishing|'m finishing|am pursuing|'m pursuing)|my) (?:a |an |my )?(?:{DEGREES}|degree|diploma|major|minor)(?: degree)? in ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b{I} (?:a |an )?(?:\d+[a-z]* year |first year |second year |third year |final year |senior |junior |freshman |sophomore |current |recent |grad |graduate |college |university |uni |phd |masters? |undergrad )*{NOT_DEMONYM}([a-z-]+(?: [a-z-]+)?) (?:student|major|grad|graduate|minor)\b",
                          rf"(?:\b\d{{2}}\s?[mf]?\b|\b[mf]\s?\d{{2}}\b)[ ,]+(?:[a-z]+ )?{NOT_DEMONYM}([a-z-]+(?: [a-z-]+)?) (?:student|major)\b",
                          rf"\b(?:i (?:have|hold|got|earned|did|finished|completed|received|graduated with)|my) (?:an? |my |a whole )?([a-z]+(?: [a-z]+)?) (?:degree|diploma|b\.?a\b|b\.?s\.?c?\b|m\.?a\b|msc\b|phd\b)",
                          rf"\b(?:with|got|received|earned|have|hold|did|completed|finished) (?:an? |my |a whole )?(?:{DEGREES}|degree|diploma|bachelor's degree|master's degree)(?: degree)? in ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b(?:majoring|majored|minoring|minored|double majoring|double majored) in ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b(?:student|junior|senior|freshman|sophomore|undergrad|year|i am currently|i'm currently|currently) studying ([a-z][a-z -]+?){SUBJECT_END}"),
    "occupation": (rf"\b{I} an? (?:{JOB_MODIFIERS} )*((?:[a-z]+ ){{0,2}}(?:{JOB_TITLES}|{JOB_HEADS}))s?{END}(?! (?:friend|wife|husband|mom|dad|fan))",
                   rf"\b(?:i|{I}|i've been|i have been|currently|now) (?:currently |now )?(?:work|working) as an? {JOB}",
                   rf"\bi(?:'ve| have) been an? {JOB}", rf"(?:^|[.!?] )as an? {JOB}(?:,| who| myself| i\b)",
                   rf"(?:^|[.!,;] )(?:{JOB_MODIFIERS} )*({JOB_TITLES}) here\b",
                   r"\bi (?:currently |now |also |still )?work (?:in|at a|in a|for a) ([a-z]+(?: [a-z]+)?)(?= (?:and|as|for|at|so|but|which|company|firm|office|industry|field|department|setting)\b|[.,!?;)]|$)",
                   r"\b(?:and|also|but|currently|now) (?:currently |now |also |still )?work (?:in|at a|in a|for a) ([a-z]+(?: [a-z]+)?)(?= (?:and|as|for|at|so|but|which|company|firm|office|industry|field|department|setting)\b|[.,!?;)]|$)",
                   rf"(?:\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b)[^.\n]{{0,40}}?(?:[,|/•-]\s*|\s+)((?:[a-z]+ ){{0,2}}(?:{JOB_TITLES}|{JOB_HEADS})){END}",
                   rf"\b{I} [a-z]+(?: [a-z]+)?, an? ((?:[a-z]+ ){{0,3}}(?:{JOB_TITLES}|{JOB_HEADS})){END}"),
    "employment_status": (rf"\b(?:i|{I}|i've been|i have been) (?:currently |now |also |still )?(?:work|working) (full[- ]time|part[- ]time)\b", r"\bi (?:currently|now) (work)\b(?! (?:on|out|through))",
                          rf"\b(?:{I}|i've been|i have been) (?:currently |now |happily |fully )?(retired|unemployed|self[- ]employed|a student|a full[- ]time student|a college student|a university student|a stay[- ]at[- ]home (?:mom|mum|dad|parent)|a homemaker|a housewife|on disability|disabled|a freelancer|freelance|jobless|between jobs|laid off|out of work)\b",
                          r"\b(?:i(?:'m| am|m)?|i've been|i have been|i got|i was just|i just got|recently|currently|still) (?:currently |still |now |recently |just |been )?(unemployed|laid off|jobless|between jobs|out of work|job hunting|looking for (?:a )?(?:job|work)|job searching|without a job)\b(?! (?:people|folks|friends?|guy|men|women))",
                          rf"\bi (work for myself|run my own business|own my own business|do freelance|freelance)\b|\b{I} (?:a |an )?(self[- ]employed|a freelancer|freelancing|an independent contractor|a business owner|my own boss)\b",
                          r"(?:\b\d{2}\s?(?:yo|y/o)?\s?[mf]?\b|\b[mf]\s?\d{2}\b|\[?[mf]4\w+\]?)[ ,/-]+(?:[a-z]+ ){0,2}?(retired)\b",
                          rf"\b(?:{I}|i've been|i have been|now|currently) (?:currently |now |still )?(working) as an?\b",
                          rf"\b(?:{I}|i've been) (?:currently |now |gainfully |fully |also )?(employed)\b(?! (?:by|at|as|with))",
                          r"\bi (?:already |currently |still |also |now )?(?:have|got|hold|held|took|started|landed) (?:a |my |two |multiple |a full[- ]time |a part[- ]time |a new |a good |a decent |a stable )?(job|jobs)\b",
                          r"\b(?:i|we) (?:both |currently |still |also )?(?:work|working) (full[- ]time|part[- ]time)\b",
                          r"\bi(?:'m| am) (?:on )?(salary|salaried|hourly)\b",
                          r"\b(?:at|from|to|after|before|leaving|left) (work|my job)\b",
                          r"\bmy (boss|coworkers?|co-workers?|shift|manager|employer)\b",
                          r"\bi (don'?t have a job|do not have a job|can'?t find a job|can'?t find work|lost my job|got fired|was fired|got laid off|was laid off|haven'?t worked)\b",
                          r"\bi (?:[a-z]+ ){1,4}(for a living)\b"),
    "marital_status": (r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(married)\b",
                       r"\b(?:i've|i have|we've|we have) been (married) (?:for )?", r"\b(married) (?:man|woman|guy|male|female|dad|mom|couple) here\b",
                       r"\bmy (husband)\b(?! (?:and i (?:are|were) divorced|left|died|passed))", r"\bmy (wife) and i\b(?! (?:are|were) divorced)", rf"\b{I} (?:happily |newly )?(married|divorced|widowed|a widow|a widower|separated)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career))",
                       r"\b(?:with|and|told|love|tell|let|asked) my (husband|wife)\b(?!'s (?:friend|brother|sister))",
                       r"\b(?:happily|newly|recently|just got|i got|i'm|im|i am|i've been|i have been|we got|we've been) (married)\b(?! (?:to (?:my|a)? ?(?:job|work|career)|people|couples?|men|women|man|woman))",
                       r"(?:\b\d{2}\s?(?:yo|y/o)?\s?[mf]?\b|\b[mf]\s?\d{2}\b|\b[mf]\b|\[?[mf]4\w+\]?)[ ,/-]+(?:[a-z]+ ){0,2}?(married)\b",
                       r"\b(married) (?:man|woman|guy|male|female|dad|mom|mother|father|bi|white|black|straight|hispanic|asian|couple|mf|m|f)\b",
                       r"\b(?:my|the) (wife|husband|hubby) (?:is out|is away|is gone|is asleep|is at work|went|left for|travels|is travelling|is traveling|works|is working)\b",
                       r"\b(?:soy|estoy|sou|estou|je suis|ich bin|sono|ik ben) (casad[oa]|mariée?|verheiratet|sposat[oa]|getrouwd|divorciad[oa]|divorcée?|geschieden|separad[oa]|viud[oa]|veuf|veuve|verwitwet)\b",
                       r"\b(?:mi|meu|minha|mon|ma|mein|meine|mio|mia|mijn) (marido|esposo|esposa|mari|femme|mann|frau|marito|moglie|man|vrouw)\b"),
    "relationship_status": (rf"\b{I} (?:happily |newly |currently |still )?(engaged|single|in a relationship)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career)|(?: and)? (?:ready|looking) to mingle)",
                            r"\bi(?:'ve| have) been (single|in a relationship|engaged|dating)\b",
                            r"(?:\b\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\b[mf]\b)\s*,\s*(single|engaged|taken)\b",
                            rf"\b(?:{I}|i've been|i have been|i got|we got|we're|we are|we just got|i just got|recently|newly) (?:happily |newly |currently |still |recently |just |finally |now |also |completely |very |totally )?(single|engaged|dating someone|seeing someone|in a (?:committed |serious |long[- ]term |long[- ]distance |happy |new |monogamous |open |poly(?:amorous)? )?relationship|taken|unattached)\b(?! (?:to (?:my|a)? ?(?:job|work|career)|people|folks|moms?|dads?|parents?|men|women|guys|girls|friends?|ladies)|(?: and)? (?:ready|looking) to mingle)",
                            r"\b(?:being|been|happily|still|and still|whos been|who's been|i stay|staying) (single)\b(?! (?:mom|dad|parent|mother|father|moms|dads|women|men|ladies|people))",
                            r"\b(?:and|but|now|happily|currently|still) (in a (?:[a-z-]+ ){0,2}?relationship)\b",
                            rf"\b{I} (?:happily |currently |still |now )?(in a (?:[a-z-]+ ){{0,2}}?relationship)\b(?! with (?:food|money|work|my body|alcohol))",
                            r"\b(?:soy|estoy|sou|estou|je suis|ich bin|sono|ik ben) (solter[oa]|solteir[oa]|célibataire|single|singolo|vrijgezel|en couple|in einer beziehung|fidanzat[oa]|namorando|en una relación|in een relatie)\b"),
    "parental_status": (r"\bi have (?:a |an |one |two |three |four |five |\d+ |young |grown |adult |little )*(kids|children|sons?|daughters?|toddlers?)\b",
                        r"\bi (gave birth)\b", r"\bas an? (?:\w+ )?(parent|mom|mum|dad|mother|father) (?:of|to)\b",
                        r"(?:^|[.!,;] )(?:(?!would|ftm|first)[a-z]+ ){0,3}(mom|dad|parent|mum|mother|father) here\b",
                        r"\b(?:single |new |first[- ]time |proud )?(mom|mum|mother|dad|father) (?:of|to) (?:a |an |one\b|two|three|four|five|\d|my |twins)",
                        r"(?<!your )(?<!her )(?<!his )(?<!my )\bsingle (mom|mum|dad|mother|father)\b",
                        rf"\b{I} (?:also |now )?{A}(?:single |new |first[- ]time |proud |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b(?! (?:of|to) (?:a|an|my|the|two) (?:dog|cat|pet|puppy|kitten|plant|fur))",
                        r"\bas an? (?:single |new |first[- ]time |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b",
                        rf"\b{I} (?:currently )?(pregnant)\b",
                        r"\b(?:married|single|divorced|horny|lonely|bi|bi-curious|bicurious|straight|white|black|fit|hot|busy|working|hung|naughty|curious|bored|fun|young|older|chubby|dilf|hairy|daddy|discreet|local) (dad|mom|mum|father|mother)\b(?! (?:of (?:a |my )?friend|'s|jokes?|bod|body|vibes?|energy|friend))",
                        r"(?:^|[\s\]\)])(dad|mom|mum) (?:looking|seeking|wanting|needs|needing|here|of \d|of two|of three|with)\b",
                        r"\b(?:i|we) (?:have|got|had) (?:a |an |one |two |three |four |five |\d+ )?(?:(?:little|young|grown|adult|teenage|beautiful|amazing|wonderful|new|newborn|\d{1,2}[- ]?(?:yo|year[- ]old|month[- ]old|yr[- ]old)) )*(kids?|children|sons?|daughters?|toddlers?|babies|baby|twins|newborn|teenagers?|boys|girls)\b(?! (?:friend|in (?:my|the) class|at school))",
                        r"(?:^|[\s,.(])(?:one|two|three|four|five|\d) (kids|children|sons|daughters)\b",
                        r"\b(?:tengo|tenemos|tenho|temos|j'ai|nous avons|ich habe|wir haben|ho|abbiamo|ik heb|wij hebben) (?:\w+ )?(hijos|hijas|filhos|filhas|enfants|kinder|figli|figlie|kinderen)\b",
                        r"\b(no tengo hijos|não tenho filhos|je n'ai pas d'enfants|ich habe keine kinder|non ho figli)\b",
                        rf"\b{I} (?:also |now |just )?{A}(?:[\w-]+ ){{0,2}}?(mom|mother|dad|father|mum|parent)\b(?! (?:of|to) (?:a|an|my|the|two) (?:dog|cat|pet|puppy|kitten|plant|fur))",
                        r"(?:^|[\s,(\[])\d{2}\s*[mf]?\s+(?:[a-z]+ ){0,2}?(dad|mom|mum|father|mother)\b",
                        r"\b(?:married |now |am |i'm |im )?with ((?:a |an |one |two |three |four |\d )?(?:young |little |small |grown |adult |teenage )?(?:kids|children|kid|child|sons|daughters))\b",
                        r"(?:\b(?:i|we) |(?:^|[.!?]) *)(?:just |recently |finally |also )?(?:had|welcomed|adopted) (?:a |an |our |my )?(?:first |second |third |new |beautiful |baby )?(baby|child|kid|son|daughter|twins|babies)\b(?! (?:brother|sister|cousin|of|in|at|with you|over))",
                        r"\bmy (?:first |little |\d |two |three )?(kiddos?|little ones?|firstborn|first born)\b",
                        r"\b(?:my|our|i have an?|we have an?) (?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)[- ](?:year|yr|month|week)s?[- ](old)\b"),
    "mental_health": (rf"\bi (?:also |do |still |actually |definitely |both )?(?:have|suffer from|struggle with|live with|deal with|am dealing with|'m dealing with) {SEVERITY}({CONDITIONS})\b",
                      rf"\bi(?:'ve| have| was| got| am|'m)? (?:been )?(?:officially |formally |recently |finally |also )?diagnosed (?:with |as )?(?:having )?{SEVERITY}({CONDITIONS})\b",
                      rf"\b{I} (?:an? )?(?:[a-z]+ ){{1,3}}with (?:my |unmedicated |severe |diagnosed )?({CONDITIONS})\b",
                      rf"\b{I} (?:also )?(autistic|bipolar|schizophrenic|an alcoholic|an addict)\b",
                      r"\bas (?:someone|a person|an adult|a woman|a man|a guy|a girl) with (adhd|autism|depression|anxiety|ocd|ptsd|bipolar(?: disorder)?|bpd)\b"),
    "political_ideology": (rf"\b{I} {A}(?:proud |lifelong |life-long |staunch |die[- ]hard )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|nationalist|marxist|moderate|democratic socialist)\b(?! (?:party|government|state|country|city|state|area|parents|family|friends|media))",
                           r"\bas an? (?:proud |lifelong |staunch )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|marxist|democratic socialist)\b(?! (?:party|government|state|country|city|media))",
                           rf"\b{I} (?!not\b)(?:a |an |also a |also |pretty |very |extremely |fairly |generally |openly |still |basically |raging |self[- ]described |proud |lifelong |staunch )*({IDEOLOGIES})\b(?! (?:party|government|state|country|city|area|parents|family|friends|media|news|policies|politicians|people|men|women))", rf"(?:^|[.!,;] )(?:[a-z]+ )?({IDEOLOGIES}) here\b"),
}


def spelled(op, av):
    if op is sre.LITERAL:
        return {chr(av)}
    if op is sre.IN and len(av) <= 8 and all(kind is sre.LITERAL for kind, _ in av):
        return {chr(code) for _, code in av}
    if op is sre.SUBPATTERN:
        return spelling(av[3])
    if op is sre.BRANCH:
        branches = [spelling(branch) for branch in av[1]]
        return None if None in branches else set().union(*branches)
    if op is sre.MAX_REPEAT and av[0] == 0 and av[1] == 1 and (part := spelling(av[2])) is not None:
        return {"", *part}
    return None


def spelling(items):
    strings = {""}
    for op, av in items:
        part = spelled(op, av)
        if part is None or len(strings) * len(part) > SPELLINGS:
            return None
        strings = {left + right for left in strings for right in part}
    return strings


def needed(items):
    options, strings = [], {""}
    for op, av in [*items, (None, None)]:
        part = spelled(op, av)
        if part is not None and len(strings) * len(part) <= SPELLINGS:
            strings = {left + right for left in strings for right in part}
            continue
        if "" not in strings:
            options.append(strings)
        strings = part if part is not None else {""}
        if part is not None:
            continue
        if op is sre.SUBPATTERN:
            found = needed(av[3])
        elif op is sre.BRANCH:
            branches = [needed(branch) for branch in av[1]]
            found = None if None in branches else set().union(*branches)
        elif op in (sre.MAX_REPEAT, sre.MIN_REPEAT, sre.POSSESSIVE_REPEAT) and av[0] >= 1:
            found = needed(av[2])
        else:
            found = None
        if found:
            options.append(found)
    return max(options, key=lambda strings: min(map(len, strings)), default=None)


def trie(words):
    root = {}
    for word in words:
        node = root
        for ch in word:
            node = node.setdefault(ch, {})
        node[""] = {}
    return arms(root)


def arms(node):
    branches = [re.escape(ch) + arms(child) for ch, child in sorted(node.items()) if ch]
    body = branches[0] if len(branches) == 1 else "(?:" + "|".join(branches) + ")" if branches else ""
    return f"(?:{body})?" if "" in node and branches else body


SPELLINGS = 64
COMPILED = [(field, index, re.compile(pattern), needed(sre_parse.parse(pattern))) for field, patterns in PHRASES.items() for index, pattern in enumerate(patterns)]
ALWAYS = {position for position, (_, _, _, gate) in enumerate(COMPILED) if gate is None}
ENABLES = defaultdict(list)
for position, (_, _, _, gate) in enumerate(COMPILED):
    for literal in gate or ():
        ENABLES[literal].append(position)
REACH = {literal: set().union(*(ENABLES.get(literal[:size], ()) for size in range(1, len(literal) + 1))) for literal in ENABLES}
FINDER = re.compile(f"(?=({trie(sorted(ENABLES))}))")
COMPACT = {name.replace(" ", ""): name for name in (*STATE_NAMES, *CITIES) if " " in name}
FILLER = {"online", "north", "south", "east", "west", "ne", "nw", "se", "sw", "central", "northern", "southern", "eastern", "western", "upstate",
          "downtown", "greater", "rural", "northeast", "northwest", "southeast", "southwest", "far", "midwest"}
CITY_FIRST = {"delhi", "auckland", "berlin", "mexico city", "hamburg", "metro manila", "rio de janeiro", "sao paulo", "new york"}
PLACE_FIELDS = {"residence_country": ("residence_country", "residence_state", "residence_city"),
                "origin_country": ("origin_country", "origin_state", "origin_city")}
SKIP = re.compile(r"^\s*>(?!!).*$|(?<![\d'’])\"[^\"\n]{6,300}\"|“[^”\n]{6,300}”|https?://\S+|\(/?r/\S+\)|\b/?[ru]/\S+", re.M)
WORD_CODES = {"on", "in", "me", "hi", "ma", "or", "ok", "oh", "de", "la", "co", "id", "al", "ne", "mo", "ms", "ar", "ab", "ns", "nb", "sk", "mb"}
SHORT_WORDS = {"uk", "nz", "bi", *(code for code in STATES if len(code) == 2 and code not in WORD_CODES)}
FLAGS = {"🇺🇸": "united states", "🇬🇧": "united kingdom", "🇨🇦": "canada", "🇦🇺": "australia", "🇮🇳": "india", "🇵🇭": "philippines", "🇩🇪": "germany",
         "🇫🇷": "france", "🇧🇷": "brazil", "🇲🇽": "mexico", "🇳🇱": "netherlands", "🇮🇹": "italy", "🇪🇸": "spain", "🇮🇪": "ireland", "🇳🇿": "new zealand",
         "🇵🇰": "pakistan", "🇳🇬": "nigeria", "🇿🇦": "south africa", "🇷🇺": "russia", "🇺🇦": "ukraine", "🇵🇱": "poland", "🇹🇷": "turkey", "🇯🇵": "japan",
         "🇰🇷": "south korea", "🇨🇳": "china", "🇸🇪": "sweden", "🇳🇴": "norway", "🇩🇰": "denmark", "🇫🇮": "finland", "🇵🇹": "portugal", "🇬🇷": "greece",
         "🇷🇴": "romania", "🇮🇱": "israel", "🇦🇪": "united arab emirates", "🇦🇷": "argentina", "🇨🇴": "colombia", "🇧🇪": "belgium", "🇨🇭": "switzerland",
         "🇦🇹": "austria", "🇱🇻": "latvia", "🇱🇹": "lithuania", "🇪🇪": "estonia", "🇧🇩": "bangladesh", "🇮🇩": "indonesia", "🇲🇾": "malaysia",
         "🇸🇬": "singapore", "🇻🇳": "vietnam", "🇹🇭": "thailand"}
US_UPPER = re.compile(r"\bUS\b")
REGION_COUNTRY = {region: name for name, regions in REGIONS.items() for region in regions}
HYPOTHETICAL = re.compile(r"\b(?:if|when|unless|whether|imagine|pretend|suppose|wish|would|hope|want to be|wanna be|used to be|was|think|thinks|assume|assumes|assumed)\W+(?:\w+\W+){0,3}$")
TAIL = r"\b(?:\W+[\w']+){0,3}\W*$"
CUES = {"other": re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|him|they|they're|their|them|you|you're|your|ur|u|my (?:wife|husband|son|daughter|kids?|mom|dad|mother|father|brother|sister|bf|gf|boyfriend|girlfriend|partner|friend|cousin|grandma|grandpa|ex|baby|child|children))" + TAIL),
        "negated": re.compile(r"\b(?:not|never|no longer|isn't|aren't|wasn't|ain't|don't|dont|doesn't|nor|neither|no)" + TAIL),
        "we": re.compile(r"\b(?:we|we're|us|our|both)" + TAIL),
        "past": re.compile(r"\b(?:used to|when i was|back when|back in|as a kid|growing up|at the time|formerly|former|previously|was|were|had been|turned|became)" + TAIL),
        "if": HYPOTHETICAL,
        "generic": re.compile(r"\b(?:people|everyone|everybody|anyone|anybody|guys|men|women|folks|someone|somebody|nobody|most|many|all|americans|those|these)" + TAIL),
        "compare": re.compile(r"\b(?:than|over|under|above|below|between|from|in their|in our|in your|at least|at most)\W*$")}
QUESTION = re.compile(r"\W*(?:are|is|am|any|anyone|anybody|who|what|where|how|do|does|did|can|could|would|should|will)\b")
SUBJECT_AFTER = re.compile(r"\W{0,3}(?:she|he|they|she's|he's|they're|his|her|their)\b")
RANGE = re.compile(r"\s*(?:-|to)\s*\d")
MEASURES = {"usd", "dollars", "dollar", "bucks", "euros", "k", "mins", "min", "minutes", "hours", "hrs", "hr", "days", "weeks", "months", "times", "percent", "%",
         "matches", "games", "points", "pts", "people", "miles", "km", "meters", "metres", "feet", "ft", "inches", "lbs", "lb", "kg", "kgs", "pounds", "seconds",
         "secs", "sec", "episodes", "pages", "levels", "rounds", "sets", "reps", "mph", "kph", "degrees", "grams", "mg", "ml", "oz", "cm", "mm", "views", "likes",
         "followers", "subs", "votes", "comments", "posts", "items", "words", "div", "hp", "gb", "tb", "fps"}
DIAGNOSES = {"add": "adhd", "asd": "autism", "an eating disorder": "eating disorder", "an alcoholic": "addiction", "an addict": "addiction", "cptsd": "ptsd",
             "c-ptsd": "ptsd", "autistic": "autism", "schizophrenic": "schizophrenia", "bipolar": "bipolar disorder"}
MARRIED = {"husband": "married", "wife": "married", "hubby": "married", "spouse": "married", "a widow": "widowed", "a widower": "widowed",
           **dict.fromkeys(("casado", "casada", "marié", "mariée", "verheiratet", "sposato", "sposata", "getrouwd", "marido", "esposo", "esposa", "mari",
                            "femme", "mann", "frau", "marito", "moglie", "man", "vrouw"), "married"),
           **dict.fromkeys(("divorciado", "divorciada", "divorcé", "divorcée", "geschieden"), "divorced"),
           **dict.fromkeys(("separado", "separada"), "separated"), **dict.fromkeys(("viudo", "viuda", "veuf", "veuve", "verwitwet"), "widowed")}
CHILDREN = {"pregnant": "expecting", **dict.fromkeys(("no kids", "no children", "childfree", "child free", "child-free", "childless", "not a parent",
                                                      "don't have kids", "dont have kids", "do not have kids", "don't have children",
                                                      "do not have children", "no tengo hijos", "não tenho filhos", "je n'ai pas d'enfants",
                                                      "ich habe keine kinder", "non ho figli"), "no children")}
PARTNERS = {"my gf": "in a relationship", "my bf": "in a relationship", "my girlfriend": "in a relationship", "my boyfriend": "in a relationship",
            "my partner": "in a relationship", "my fiance": "engaged", "my fiancé": "engaged", "my fiancee": "engaged", "my fiancée": "engaged",
            **dict.fromkeys(("soltero", "soltera", "solteiro", "solteira", "célibataire", "single", "singolo", "vrijgezel"), "single"),
            **dict.fromkeys(("en couple", "in einer beziehung", "fidanzato", "fidanzata", "namorando", "en una relación", "in een relatie"), "in a relationship")}
EMPLOYMENT = {"a full-time student": "student", "a full time student": "student", "a college student": "student",
              "a university student": "student", "a student": "student", "a freelancer": "self-employed", "freelance": "self-employed",
              "self employed": "self-employed", "jobless": "unemployed", "between jobs": "unemployed", "laid off": "unemployed",
              "out of work": "unemployed", "disabled": "unable to work", "on disability": "unable to work", "a homemaker": "homemaker",
              "a housewife": "homemaker", "job hunting": "unemployed", "looking for a job": "unemployed", "looking for work": "unemployed",
              "looking for job": "unemployed", "job searching": "unemployed", "without a job": "unemployed", "on ssdi": "unable to work",
              "on ssi": "unable to work", "on pip": "unable to work", "work for myself": "self-employed", "run my own business": "self-employed",
              "own my own business": "self-employed", "do freelance": "self-employed", "freelancing": "self-employed", "for a living": "employed",
              "an independent contractor": "self-employed", "a business owner": "self-employed", "my own boss": "self-employed",
              "in college": "student", "in uni": "student", "in university": "student", "at university": "student", "at uni": "student",
              "in grad school": "student", "in law school": "student", "in med school": "student", "in nursing school": "student",
              **dict.fromkeys(("jobs", "full-time", "part-time", "salary", "salaried", "hourly", "my job", "boss", "coworker", "coworkers", "co-worker",
                               "co-workers", "shift", "manager", "employer"), "employed"),
              **dict.fromkeys(("don't have a job", "dont have a job", "do not have a job", "can't find a job", "cant find a job", "can't find work",
                               "lost my job", "got fired", "was fired", "got laid off", "was laid off", "haven't worked", "cant find work",
                               "havent worked"), "unemployed")}
PERIODS = {"hour": 2080, "hr": 2080, "hourly": 2080, "/h": 2080, "week": 52, "wk": 52, "weekly": 52, "month": 12, "mo": 12, "monthly": 12}
EARNINGS = re.compile(r"(.+?)\s*(?:(?:a|an|per|/|every)\s*)?(year|yr|annum|month|mo|hour|hr|week|wk|annually|yearly|monthly|hourly|weekly|/h)?"
                      r"(?:\s+(?:tc|base|base salary|salary|gross|pre[- ]tax|before tax|after tax|take home|ote))?$")
ORIENTATION_WORDS = {"lesbiana": "lesbian", "lésbica": "lesbian", "lesbienne": "lesbian", "bissexual": "bisexual", "bisexuel": "bisexual", "bisexuelle": "bisexual"}
BELIEFS = {"christ": "christian", "christin": "christian", "muslimin": "muslim", "not religious": "no religion"}
GENDERED = {"mom": "female", "mother": "female", "mum": "female", "wife": "female", "dad": "male", "father": "male", "husband": "male", "milf": "female",
            "femboy": "male", "chica": "female", "chico": "male", "homem": "male", "mulher": "female", "homme": "male", "femme": "female", "mann": "male",
            "transmasc": "male", "transfem": "female", "trans masc": "male", "trans fem": "female", "a transman": "male", "a transwoman": "female",
            "ragazzo": "male", "ragazza": "female", "garota": "female", "garoto": "male", "menina": "female", "menino": "male",
            "bloke": "male", "lad": "male", "girlie": "female", "girly": "female", "wifey": "female", "hubby": "male", "transgirl": "female",
            "transguy": "male", "trans girl": "female", "trans guy": "male", "mec": "male", "hombre": "male", "mujer": "female", "frau": "female"}


def resolve(field, raw):
    if field == "occupation":
        return JOBS.get(raw) or value(field, raw)
    if field == "mental_health":
        return value(field, DIAGNOSES.get(raw, raw))
    if field == "marital_status":
        return MARRIED.get(raw) or value(field, raw)
    if field == "parental_status":
        return CHILDREN.get(raw, "parent")
    if field == "relationship_status":
        return PARTNERS.get(raw) or value(field, raw)
    if field == "employment_status":
        return EMPLOYMENT.get(raw.replace("self-employed", "self employed"), None) or value(field, raw)
    if field == "weight":
        raw = raw.replace("kilograms", "kg")
    if field == "weight" and re.fullmatch(r"\d{2,3}(?:\.\d)?", raw):
        return value(field, raw + (" lbs" if float(raw) >= 100 else " kg"))
    if field == "income":
        return earnings(raw)
    if field == "birth_year":
        raw = raw.lstrip("'")
        return value(field, "19" + raw if re.fullmatch(r"[4-9]\d", raw) else "20" + raw if re.fullmatch(r"0\d|1[0-3]", raw) else raw)
    if field == "sexual_orientation":
        return ORIENTATION_WORDS.get(raw) or value(field, raw)
    if field == "religion":
        return BELIEFS.get(raw) or value(field, raw)
    if field == "gender":
        return GENDERED.get(raw) or value(field, raw)
    if field == "generation":
        return value(field, re.sub(r"(?<=[zx])er$", "", raw))
    return value(field, raw)


def earnings(raw):
    match = EARNINGS.fullmatch(re.sub(r"\bmil\b", "million", raw))
    if not match:
        return None
    amount, unit = number(match.group(1))
    if amount is None or unit is not None:
        return None
    return value("income", str(round(amount * PERIODS.get(match.group(2), 1))))


def peel(field, words):
    for size in range(min(4, len(words)), 0, -1):
        if (size > 1 or words[-1] not in WORD_CODES) and (result := value(field, " ".join(words[-size:]))) is not None:
            return result, words[:-size]
    return None, words


def places(kind, raw):
    words = [COMPACT.get(word, word) for word in raw.replace(",", " ").split() if word not in FILLER]
    found = [place(kind, " ".join(words[:end])) for end in range(len(words), 0, -1)]
    return next((item for item in found if item[0] and not item[1]), next((item for item in found if item[0]), ({}, "")))


def place(kind, raw):
    country_field, state_field, city_field = PLACE_FIELDS[kind]
    if raw.rstrip(".") in CITY_ALIASES:
        return {city_field: CITY_ALIASES[raw.rstrip(".")]}, ""
    words = raw.replace(",", " ").split()
    country, words = peel(country_field, words)
    region, words = (None, words) if " ".join(words) in CITY_FIRST else peel(state_field, words)
    town = value(city_field, " ".join(words)) if words and len(words) <= 3 else None
    if words and town not in CITIES and (town is None or (country is None and region is None)):
        return {}, ""
    found = {key: result for key, result in ((city_field, town), (state_field, region), (country_field, country)) if result is not None}
    return found, "partial" if words and town not in CITIES else ""


def tags(text):
    for name, pattern in (("tag_self", TAG_SELF), ("tag_any", TAG_ANY), ("tag_dash", TAG_DASH)):
        for match in islice(pattern.finditer(text), MATCHES):
            age, sex, form = (match.group(1), match.group(2), "nx") if match.group(1) else (match.group(4), match.group(3), "xn")
            yield "age", value("age", age), f"{name}_{form}", match.span(), ""
            yield "gender", value("gender", sex), f"{name}_{form}", match.span(), ""
    for name, pattern, age, sex in (("age_gender", AGE_GENDER, 1, 2), ("gender_age", GENDER_AGE, 2, 1), ("gender_paren", GENDER_PAREN, 2, 1)):
        for match in islice(pattern.finditer(text), MATCHES):
            yield "age", value("age", match.group(age)), name, match.span(), ""
            yield "gender", value("gender", match.group(sex)), name, match.span(), ""
    for match in islice(PRONOUN_TAG.finditer(text), MATCHES):
        yield "gender", value("gender", PRONOUN_GENDER[match.group(1)]), "pronoun", match.span(), ""
    for name, pattern in (("gender_bare", BARE_GENDER), ("race_gender", RACE_GENDER)):
        for match in islice(pattern.finditer(text), MATCHES):
            yield "gender", value("gender", match.group(1)), name, match.span(), ""
    for match in islice(GENDER_BRACKET.finditer(text), MATCHES):
        yield "gender", value("gender", match.group(1)), "gender_bracket", match.span(), ""
    for match in islice(TAG_FOR.finditer(text), MATCHES):
        age = match.group(1) or match.group(3)
        yield "gender", value("gender", match.group(2)), "tag_for_age" if age else "tag_for", match.span(), ""
        if age:
            yield "age", value("age", age), "tag_for_age", match.span(), ""
    for name, pattern in (("age_start", AGE_START), ("age_bracket", AGE_BRACKET), ("number", NUMBER), ("age_bare", BARE_NUMBER)):
        for match in islice(pattern.finditer(text), MATCHES):
            yield "age", value("age", match.group(1)), name, match.span(), ""
    for match in islice(WORD_NUMBER.finditer(text), MATCHES):
        tens, unit, teen = match.groups()
        yield "age", value("age", str(TEENS[teen] if teen else TENS[tens] + UNITS.get(unit, 0))), "age_word", match.span(), ""


def stats(text):
    for field, name, pattern, near in (("height", "height_any", HEIGHT_ANY, PEOPLE), ("height", "height_metric", HEIGHT_METRIC, PEOPLE),
                                       ("weight", "weight_any", WEIGHT_ANY, OTHER)):
        for match in islice(pattern.finditer(text), MATCHES):
            yield field, value(field, match.group(1)), name, match.span(), "people" if near.search(text[max(0, match.start() - 25):match.start()]) else ""
    for match in islice(WEIGHT_AFTER.finditer(text), MATCHES):
        yield "weight", resolve("weight", match.group(1)), "weight_after_height", match.span(), "people" if OTHER.search(text[max(0, match.start() - 25):match.start()]) else ""
    for match in islice(INCOME_ANY.finditer(text), MATCHES):
        yield "income", earnings(match.group(1).strip()), "amount", match.span(), ""
    for match in islice(YEAR.finditer(text), MATCHES):
        yield "birth_year", value("birth_year", match.group(1)), "year", match.span(), ""


def phrases(text):
    active = ALWAYS.union(*(REACH[match.group(1)] for match in FINDER.finditer(text)))
    for position in sorted(active):
        field, index, pattern, _ = COMPILED[position]
        for match in islice(pattern.finditer(text), MATCHES):
            flag = "hypothetical" if HYPOTHETICAL.search(re.split(r"[.!?\n(]", text[max(0, match.start() - 40):match.start()])[-1]) else ""
            raw = next(group for group in match.groups() if group is not None).strip()
            if field in PLACE_FIELDS:
                found, partial = places(field, raw)
                for key, result in found.items():
                    yield key, result, f"{field}#{index}", match.span(), " ".join(filter(None, (flag, partial)))
            else:
                yield field, resolve(field, raw), f"{field}#{index}", match.span(), flag


@cache
def vocabulary():
    words = {"residence_country": {*COUNTRIES, *COUNTRY_ALIASES}, "origin_country": {*COUNTRIES, *COUNTRY_ALIASES},
             "nationality": {*DEMONYMS, *COUNTRIES, *COUNTRY_ALIASES}, "language": {*LANGUAGES, *LANGUAGE_ALIASES},
             "residence_state": {*STATE_NAMES, *STATES}, "residence_city": {*CITIES, *CITY_ALIASES}, "gender": GENDER_WORDS,
             "parental_status": PARENT_WORDS | set(CHILDREN) | {"mom", "mum", "dad", "mother", "father", "mommy", "parent"}, "occupation": set(JOBS),
             "education": set(LOOKUP["education"]), "education_subject": SUBJECT_WORDS, **{field: set(LOOKUP[field]) for field in VOCAB_FIELDS}}
    words["relationship_status"] |= set(PARTNERS)
    table = defaultdict(list)
    for field, entries in words.items():
        for word in sorted(entries):
            if (len(word) > 2 or word in SHORT_WORDS) and (result := resolve(field, word) or (field in PLACE_FIELDS and country(word)) or (field == "residence_state" and state(word))):
                table[tuple(TOKEN.findall(word))].append((field, result))
    for flag, name in FLAGS.items():
        table[tuple(TOKEN.findall(flag))].extend((field, name) for field in ("residence_country", "nationality", "origin_country"))
    for field, entries in VALUES.items():
        for word in entries:
            if (field, word) not in (found := table[tuple(TOKEN.findall(word))]):
                found.append((field, word))
    return table, max(map(len, table))


def mentions(text):
    table, longest = vocabulary()
    spans = list(TOKEN.finditer(text))
    words = [span.group(0) for span in spans]
    seen = Counter()
    index = 0
    while index < len(words):
        for size in range(min(longest, len(words) - index), 0, -1):
            if found := table.get(tuple(words[index:index + size])):
                for field, result in found:
                    if seen[field] < VOCAB_MATCHES:
                        seen[field] += 1
                        yield field, result, "vocab", (spans[index].start(), spans[index + size - 1].end()), ""
                index += size - 1
                break
        index += 1


RANGES = {"age": (13, 16, 18, 21, 25, 30, 40, 50, 65, 80, 100), "birth_year": (1940, 1960, 1975, 1985, 1995, 2005, 2010),
          "height": (140, 155, 165, 175, 185, 195, 210), "weight": (40, 55, 70, 85, 100, 120, 150, 200),
          "income": (5000, 15000, 30000, 50000, 80000, 120000, 200000, 500000)}
TOP_EDGES = (0.1, 0.25, 0.4, 0.6, 0.8)
SYNONYM_FIELDS = {"language", "generation", "education_subject"}


def bucket(number, edges):
    return next((f"<{edge}" for edge in edges if number < edge), f">={edges[-1]}")


def cues(text, start, end, numeric):
    opening = max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1
    closing = min((index for index in (text.find(mark, end) for mark in ".!?\n") if index >= 0), default=len(text))
    before = text[max(opening, start - 40):start]
    after = TOKEN.findall(text[end:end + 30])[:2]
    found = {name for name, pattern in CUES.items() if pattern.search(before)}
    if text[closing:closing + 1] == "?" or QUESTION.match(text[opening:start]):
        found.add("question")
    if SUBJECT_AFTER.match(text, end):
        found.add("other")
    if numeric and after and (after[0] in MEASURES or (after[0] in ("years", "year", "yrs", "yr") and after[1:] != ["old"]) or after[0] in ("-", "to") and RANGE.match(text[end:end + 8])):
        found.add("unit")
    return found


def placed(text, end):
    table, _ = vocabulary()
    words = TOKEN.findall(text[end:end + 40])
    words = words[1:] if words[:1] == [","] else words
    return any(field in ("residence_state", "residence_country") for size in (1, 2, 3) for field, _ in table.get(tuple(words[:size]), ()))


def lead(text, start):
    word = LEAD_WORD.match(text, start)
    word = word.group(1) if word else ""
    return "tag" if LEAD.match(text, start) else "num" if word[:1].isdigit() else "self" if word in SELF else "other"


def line(text, start, end):
    closing = text.find("\n", end)
    return text[text.rfind("\n", 0, start) + 1:closing if closing >= 0 else len(text)]


def blank(value, spans):
    pieces, last = [], 0
    for start, end in spans:
        pieces += [value[last:start], " "]
        last = end
    return "".join(pieces) + value[last:]


def features(raw):
    base = US_UPPER.sub("USA", raw)
    lowered = base.lower()
    spans = [match.span() for match in SKIP.finditer(lowered)]
    text = blank(lowered, spans).translate(PRIMES)
    cased = blank(base, spans).translate(PRIMES) if len(lowered) == len(base) else text
    lines = "multi" if "\n" in text.strip() else "one"
    first = sum(token in SELF for token in TOKEN.findall(text))
    letters = sum(ch.isalpha() for ch in cased)
    capitals = sum(ch.isupper() for ch in cased)
    shape = {f"lines={lines}", f"length={bucket(len(text.strip()), (8, 20, 60, 200, 1000))}", f"bare={bool(BARE_TAG.match(text))}", f"first={bucket(first, (1, 3, 8))}",
             f"caps={'none' if not capitals else 'most' if capitals * 2 > letters else 'some'}"}
    found = defaultdict(list)
    for field, result, source, (start, end), flag in (*tags(text), *stats(text), *phrases(text), *mentions(text)):
        if result is not None:
            found[field].append((result, source, start, end, flag))
    for kind in ("residence", "origin"):
        for result, _, start, end, flag in [*found[f"{kind}_city"]]:
            for field, derived in zip(("country", "state"), CITIES.get(result, ("", ""))):
                if derived:
                    found[f"{kind}_{field}"].append((derived, "from_city", start, end, flag))
        for result, _, start, end, flag in [*found[f"{kind}_state"]]:
            if result in REGION_COUNTRY:
                found[f"{kind}_country"].append((REGION_COUNTRY[result], "from_state", start, end, flag))
    for result, _, start, end, flag in [*found["nationality"]]:
        found["residence_country"].append((result, "from_nationality", start, end, flag))
    found = {field: candidates for field, candidates in found.items() if candidates}
    context = {f"has_{field}" for field in found}
    for field, candidates in found.items():
        counts = Counter(result for result, *_ in candidates)
        pick = next((index for index, (_, source, _, _, flag) in enumerate(candidates) if not flag and source not in BROAD), None)
        seen = set()
        for rank, (result, source, start, end, flag) in enumerate(candidates):
            if (result, source) in seen:
                continue
            seen.add((result, source))
            before = TOKEN.findall(text[max(0, start - 60):start])[-4:]
            after = TOKEN.findall(text[end:end + 60])[:4]
            left = before[-2:] or ["^"]
            right = after[:1] or ["$"]
            kind = "phrase" if "#" in source else source if source in BROAD else "pattern"
            general = {f"kind={kind}", f"pick={rank == pick}", f"position={bucket(start, (3, 40, 200))}", f"same={min(counts[result], 3)}",
                       f"values={min(len(counts), 3)}", f"rank={min(rank, 3)}", *shape, *flag.split(), *(f"cue={cue}" for cue in cues(text, start, end, field in NUMERIC))}
            general |= {f"kind={kind}|{feature}" for feature in general if not feature.startswith("kind=")}
            general.add(f"self={bool(SELF.intersection(before))}")
            general.add(f"line={bucket(len(TOKEN.findall(line(text, start, end))), (3, 6, 12, 30))}")
            general.add(f"upper={any(ch.isupper() for ch in cased[start:end])}")
            span = cased[start:end]
            form = ("U" if any(ch.isupper() for ch in span) else "l" if any(ch.isalpha() for ch in span) else "n") + ("s" if start < 3 else "e") + \
                   ("p" if text[max(0, start - 1):start + 1].strip()[:1] in ("(", "[") else "")
            own = {f"source={source}", f"source={source}|form={form}", f"left={left[-1]}", f"left2={' '.join(left)}", f"right={right[0]}", *context,
                   *(f"near={word}" for word in (*before, *after)),
                   f"value={result}" if field not in NUMERIC else f"range={bucket(int(result), RANGES[field])}"}
            if field.startswith("residence_"):
                own.add(f"placed={placed(text, end)}")
            if kind == "vocab" and field not in SYNONYM_FIELDS and text[start:end] != result:
                own.add(f"word={text[start:end]}")
            if kind == "phrase":
                own.add(f"lead={lead(text, start)}")
            elif kind in ("pattern", "number", "amount"):
                own.add(f"shape={DIGIT.sub('0', text[start:end]) if end - start <= 16 else 'long'}")
            own |= {f"source={source}|{feature}" for feature in (*general, *own) if not feature.startswith(("source=", "left2=", "has_", "kind=", "near="))}
            yield field, result, general | {f"{field}|{feature}" for feature in (*general, *own)}


@cache
def weights():
    return json.loads(WEIGHTS.read_text(encoding="utf-8"))


def cross(field, tops):
    return {f"{field}|top_{other}={bucket(probability, TOP_EDGES)}" for other, probability in tops.items() if other != field}


def extract(text):
    model, best, tops = weights(), {}, {}
    candidates = list(features(text))
    for field, result, found in candidates:
        score = model["first"]["bias"] + sum(model["first"]["weights"].get(feature, 0.0) for feature in found)
        tops[field] = max(tops.get(field, 0.0), 1 / (1 + math.exp(-score)))
    for field, result, found in candidates:
        score = model["bias"] + sum(model["weights"].get(feature, 0.0) for feature in (*found, *cross(field, tops)))
        if score > model["cutoffs"][field] and score > best.get(field, (float("-inf"),))[0]:
            best[field] = (score, result)
    return {field: result for field, (_, result) in best.items()}
