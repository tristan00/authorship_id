import json
import re
from pathlib import Path

from .normalize import value

CITIES = json.loads(Path(__file__).with_name("cities.json").read_text(encoding="utf-8"))

I = r"(?:i'm|i’m|im|i am)"
A = r"(?:an? )?"
END = r"(?=$|[\s.,!?;:)\]]|'s)"
TAG = r"[\(\[]?\s*(?:(\d{2})\s*/?\s*([mf])|([mf])\s*/?\s*(\d{2}))\s*[\)\]]?"
TAG_SELF = re.compile(r"(?:^|\b(?:i'm|i’m|im|i am|i|me|myself)\b\s*)" + TAG + r"(?![a-z0-9])", re.M)
TAG_ANY = re.compile(r"(?<![\w$.,'’#/])" + TAG + r"(?![a-z0-9'’])")
AGE_START = re.compile(r"^\W{0,3}(\d{2})(?![\d.,:/%x'’-]|\s*(?:%|percent|years? ago|yrs? ago|minutes|mins?\b|hours|hrs?\b|days|weeks|months|times|seconds|secs?\b|th\b|st\b|nd\b|rd\b|k\b|mph|kph|km|miles|cm|mm|inch|lbs?\b|kg|people|of\b|out\b|to\b|or\b|-\d|\+))")
AGE_BRACKET = re.compile(r"[\[\(]\s*(\d{2})\s*[\]\)]")
HEIGHT_ANY = re.compile(r"(?<![\w.$/-])([4-7]\s*(?:'|’|ft\.?|foot|feet)\s*(?:1[01]|\d)?(?:\.\d)?\s*(?:\"|”|''|’’|in\b|inches)?)(?![\w'’])")
WEIGHT_ANY = re.compile(r"(?<![\w.$/-])(\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kgs?|kilos))\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain))")
OTHER = re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|they|they're|husband|wife|bf|gf|boyfriend|girlfriend|son|daughter|brother|sister|dad|mom|guy is|girl is|you|you're|ur|lost|from|down|goal|want|wants)\b")
TAG_FOR = re.compile(r"(?:^|[\s\[\(])(\d{2})?\s*[\[\(]?\s*([mf])\s*4\s*[mfat]\w*(?:[\]\)]?\s*[-–|:]?\s*(\d{2})\b)?", re.M)

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

PLACE = r"([a-z][a-z.'-]*(?:,? [a-z][a-z.'-]*){0,3})"

PHRASES = {
    "age": (rf"\b{I} (?:only |almost |nearly |just |now |about |turning |currently )?(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?{END}(?! (?:years? ago|minutes|hours|days|weeks|months|times|percent|%|lbs?|kg|pounds))",
            rf"\b{I} {A}(\d{{2}})[- ]?(?:years?|yr)[- ]old\b", r"\bas an? (\d{2})[- ]?(?:years?|yr)[- ]old\b", r"\bi(?: just)? turned (\d{2})\b(?! (?:years|minutes|percent|%))",
            r"\bmy age is (\d{2})\b", r"\bi'?m (\d{2}) now\b"),
    "birth_year": (r"\bi was born in (\d{4})\b",),
    "generation": (rf"\b{I} {A}(millennial|boomer|baby boomer|gen ?z|gen ?x|zoomer|gen alpha)\b", r"\bas an? (millennial|boomer|gen ?z(?:er)?|gen ?x(?:er)?|zoomer)\b",
                   r"\bfellow (millennial|boomer|gen ?z|gen ?x|zoomer)s?\b"),
    "gender": (rf"\b{I} {A}(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who))",
               r"\bas an? (?:\d{2}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|mom|mother|dad|father|wife|husband)\b",
               rf"\b{I} {A}(non-?binary|nonbinary|enby|trans (?:man|woman|guy|girl))\b"),
    "sexual_orientation": (r"(?:^|\W)[\-|/]\s*(straight|gay|bi|bisexual)\s*[\-|/]",
                           r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(straight|gay|bi|bisexual|lesbian)\b(?! (?:couples?|guys|men|women|porn|friends?|people|bar|club|scene|content|stuff))",
                           r"\b(straight|gay|bi|bisexual|lesbian|pansexual)\s+(?:[a-z]+\s+)?(?:male|female|guy|girl|boy|man|woman|dude|bottom|top|m|f)\s+here\b",
                           rf"\b{I} {A}(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:[a-z]+ ){{0,2}}?(straight|gay|bi|bisexual|lesbian|pansexual|asexual|queer|heterosexual|homosexual)\b(?! (?:friend|couple|bar|club|marriage|people|men|women|guys))",
                           r"\bas an? (?:\d{2}[- ]?(?:years?|yr)[- ]old )?(?:(?:white|black|asian|trans|young|old|older) )*(straight|gay|bi|bisexual|lesbian|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude)\b"),
    "race_ethnicity": (rf"\b{I} {A}(?:[a-z]+ ){{0,3}}?(white|black|asian|hispanic|latino|latina|mixed|biracial|mixed race|native american|middle eastern|arab|caucasian)(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself))?{END}(?! (?:people|folks|neighborhood|area|community|friends|culture))",
                       r"\b(?<!his )(?<!her )(?<!she )(?<!he )(?<!the )(?<!your )(?<!my )(white|black|asian|latino|latina|hispanic) (?:male|female|man|woman|guy|girl|boi|boy|dude|bottom|top|teen|mom|dad|milf|twink|bro)\b(?! (?:who|that|with|and (?:a|an) ))",
                       r"\bas an? (white|black|asian|hispanic|latino|latina|mixed|biracial|mixed race|native american|middle eastern|arab) (?:man|woman|guy|girl|person|male|female|dude|american|mom|dad|mother|father)\b"),
    "nationality": (rf"\b{I} {A}(american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swedish|norwegian|danish|finnish|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|chinese|japanese|korean|filipino|filipina|turkish|greek|portuguese|scottish|welsh|english|kiwi|aussie|brit|swiss|austrian|belgian|romanian|hungarian|czech|israeli|egyptian|nigerian|south african|argentinian|colombian|vietnamese|iranian|new zealander)(?: citizen)?{END}(?! (?:food|people|culture|company|government|accent|guy|girl|man|woman|friend))",
                    r"\bas an? (american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swede|norwegian|dane|finn|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|filipino|filipina|brit|aussie|kiwi|israeli|scot|new zealander)(?: citizen| person| myself)?\b(?! (?:company|government|food))",
                    r"\bi(?:'m| am) an? ([a-z]+(?: [a-z]+)?) citizen\b",
                    r"\b(?:fellow|another|proud) (american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican|scot)\b",
                    r"(?:^|[.!,;] )(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican) here\b",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican|italian|french|polish|brazilian|turkish)\b(?! (?:women|men|girls|guys|food|people))",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\b(?:male|female|guy|girl|man|woman))\s+from (?:the )?(usa|us|uk|england|scotland|canada|australia|india|poland|italy|germany|france|spain|ireland|mexico|brazil|philippines|pakistan|turkey|netherlands|sweden|norway|denmark|portugal|greece|romania|egypt|nigeria|south africa|new zealand)\b"),
    "language": (r"\bmy (?:native|first|mother) (?:language|tongue) is ([a-z]+)\b", r"\b([a-z]+) is my (?:native|first|mother) (?:language|tongue)\b",
                 rf"\b{I} {A}native ([a-z]+) speaker\b"),
    "religion": (rf"\b{I} {A}(christian|catholic|muslim|jewish|jew|hindu|buddhist|sikh|atheist|agnostic|mormon|protestant|pagan|baptist|evangelical|orthodox christian|not religious|non-religious)\b(?! (?:school|church|family|friend|parents|household))",
                 r"\bas an? (christian|catholic|muslim|jew|hindu|buddhist|sikh|atheist|agnostic|mormon|protestant|pagan|baptist|evangelical)\b(?! (?:school|church|family|friend|parents|household))"),
    "residence_country": (rf"\b(?:{I}|me|i live|i'm living|im living|living|based|located|i stay|staying|currently|here|i reside)\s+(?:\w+\s+)?(?:in|near|around|outside(?: of)?|out of)\s+(?:the\s+)?{PLACE}",
                          rf"#\s?{PLACE}", rf"\[?[mf]4[mfa]\w*\]?\W{{0,4}}{PLACE}"),
    "origin_country": (rf"\b{I} (?:originally )?from (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which | originally)",
                       r"\bi (?:was )?(?:born and raised|grew up|was born|was raised) in (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which )"),
    "height": (rf"\b{I} (?:only |about |around |like )?(\d\s*(?:'|’|ft|foot|feet)\s*\d{{0,2}}(?:\"|”|in)?|\d\s*(?:'|’)\s*\d{{1,2}}|1[4-9]\d\s*cm|2[0-2]\d\s*cm|1[.,]\d\d\s*m)(?=$|[\s.,!?;)])(?! (?:away|from|deep|wide|long|tall [a-z]+ (?:fence|wall|tree)))",
               r"\bmy height is (\d\s*(?:'|’|ft|foot|feet)\s*\d{0,2}(?:\"|”)?|1[4-9]\d\s*cm|2[0-2]\d\s*cm)\b"),
    "weight": (r"\bi (?:currently )?weigh (?:about |around |like )?(\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos|st|stone)?)\b",
               rf"\b{I} (?:currently |now )?(?:at )?(\d{{2,3}}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos))\b(?! (?:of|down|lost|heavier|lighter|more|less|weight))",
               r"\bmy (?:current )?weight is (\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos)?)\b"),
    "income": (r"\bi (?:make|earn|gross) (?:about |around |roughly |like |over )?(\$\s?\d[\d,]*(?:\.\d+)?\s*k?)(?: (?:a|per) year|/yr|/year| annually| yearly| salary)?(?! (?:a|per) (?:month|week|hour|day)|/(?:mo|month|hr|hour|wk|week))",
               r"\bmy (?:annual |yearly )?salary is (?:about |around )?(\$\s?\d[\d,]*(?:\.\d+)?\s*k?)\b"),
    "education": (rf"\bi (?:have|hold|got|earned|finished) (?:a |an |my )?(bachelor'?s|bachelors|master'?s|masters|phd|ph\.d|doctorate|associate'?s|bsc|msc|mba|ba|bs|ma|ms|jd|md)(?: degree)?\b",),
    "education_subject": (rf"\bi(?:'m| am)? (?:currently )?(?:studying|majoring in|a student of) ([a-z][a-z ]+?)(?=$|[.,!?;)]| at | in | and | but | so | with | because)",
                          r"\bi (?:study|major in) ([a-z][a-z ]+?)(?=$|[.,!?;)]| at | in | and | but | so | with | because)",
                          r"\bmy (?:degree|major) is (?:in )?([a-z][a-z ]+?)(?=$|[.,!?;)]| and | but | so | from)"),
    "occupation": (rf"\b{I} an? (?:{JOB_MODIFIERS} )*((?:[a-z]+ ){{0,2}}{JOB_HEADS})s?{END}(?! (?:friend|wife|husband|mom|dad|fan))",
                   rf"\bi work as an? (?:{JOB_MODIFIERS} )*((?:[a-z]+ ){{0,2}}{JOB_HEADS}){END}"),
    "employment_status": (rf"\b{I} (?:currently |now |happily |fully )?(retired|unemployed|self[- ]employed|a student|a full[- ]time student|a college student|a university student|a stay[- ]at[- ]home (?:mom|mum|dad|parent)|a homemaker|a housewife|on disability|disabled|a freelancer|freelance|jobless|between jobs|laid off|out of work)\b",),
    "marital_status": (r"\bmy (husband|wife|hubby|spouse)\b(?! (?:and i (?:are|were) divorced|left|died|passed))", rf"\b{I} (?:happily |newly )?(married|divorced|widowed|a widow|a widower|separated)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career))"),
    "relationship_status": (rf"\b{I} (?:happily |newly |currently |still )?(engaged|single|in a relationship)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career)|(?: and)? (?:ready|looking) to mingle)",),
    "parental_status": (r"\b(?:single |new |first[- ]time |proud )?(mom|mum|mother|dad|father) (?:of|to) (?:a |an |one\b|two|three|four|five|\d|my |twins)",
                        r"(?<!your )(?<!her )(?<!his )(?<!my )\bsingle (mom|mum|dad|mother|father)\b",
                        rf"\b{I} (?:also |now )?{A}(?:single |new |first[- ]time |proud |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b(?! (?:of|to) (?:a|an|my|the|two) (?:dog|cat|pet|puppy|kitten|plant|fur))",
                        r"\bas an? (?:single |new |first[- ]time |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b",
                        rf"\b{I} (?:currently )?(pregnant)\b"),
    "mental_health": (r"\bi (?:have|was diagnosed with|got diagnosed with|suffer from|struggle with|live with|deal with|have been diagnosed with) (?:severe |chronic |diagnosed |mild |moderate |clinical |major |pretty |really |bad |terrible |crippling |a |an )*(adhd|add|autism|asd|depression|anxiety|ocd|ptsd|cptsd|c-ptsd|bipolar(?: disorder)?|bpd|borderline personality disorder|schizophrenia|anorexia|bulimia|an eating disorder|social anxiety|generalized anxiety disorder|gad|mdd|major depressive disorder)\b",
                      rf"\b{I} (?:also )?(autistic|bipolar|schizophrenic|an alcoholic|an addict)\b",
                      r"\bas (?:someone|a person|an adult|a woman|a man|a guy|a girl) with (adhd|autism|depression|anxiety|ocd|ptsd|bipolar(?: disorder)?|bpd)\b"),
    "political_ideology": (rf"\b{I} {A}(?:proud |lifelong |life-long |staunch |die[- ]hard )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|nationalist|marxist|moderate|democratic socialist)\b(?! (?:party|government|state|country|city|state|area|parents|family|friends|media))",
                           r"\bas an? (?:proud |lifelong |staunch )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|marxist|democratic socialist)\b(?! (?:party|government|state|country|city|media))"),
    "political_compass": (rf"\b{I} {A}(auth ?left|auth ?right|lib ?left|lib ?right|authleft|authright|libleft|libright)\b",),
}
COMPILED = {field: [re.compile(pattern) for pattern in patterns] for field, patterns in PHRASES.items()}
PLACE_FIELDS = {"residence_country": ("residence_country", "residence_state", "residence_city"),
                "origin_country": ("origin_country", "origin_state", "origin_city")}
SKIP = re.compile(r"^\s*>.*$|\"[^\"\n]{0,300}\"|“[^”\n]{0,300}”|https?://\S+|\(/?r/\S+\)|\b/?[ru]/\S+", re.M)
WORD_CODES = {"on", "in", "me", "hi", "ma", "or", "ok", "oh", "de", "la", "co", "id", "al", "ne", "mo", "ms", "ar", "ab", "ns", "nb", "sk", "mb"}
HYPOTHETICAL = re.compile(r"\b(?:if|when|unless|whether|imagine|pretend|suppose|wish|would|hope|want to be|wanna be|used to be|was)\W+(?:\w+\W+){0,3}$")
DIAGNOSES = {"add": "adhd", "asd": "autism", "an eating disorder": "eating disorder", "an alcoholic": "addiction", "an addict": "addiction", "cptsd": "ptsd",
             "c-ptsd": "ptsd", "autistic": "autism", "schizophrenic": "schizophrenia", "bipolar": "bipolar disorder"}
MARRIED = {"husband": "married", "wife": "married", "hubby": "married", "spouse": "married", "a widow": "widowed", "a widower": "widowed"}
CHILDREN = {"pregnant": "expecting"}
EMPLOYMENT = {"a full-time student": "student", "a full time student": "student", "a college student": "student",
              "a university student": "student", "a student": "student", "a freelancer": "self-employed", "freelance": "self-employed",
              "self employed": "self-employed", "jobless": "unemployed", "between jobs": "unemployed", "laid off": "unemployed",
              "out of work": "unemployed", "disabled": "unable to work", "on disability": "unable to work", "a homemaker": "homemaker",
              "a housewife": "homemaker"}
GENDERED = {"mom": "female", "mother": "female", "mum": "female", "wife": "female", "dad": "male", "father": "male", "husband": "male"}


def search(field, text):
    for pattern in COMPILED[field]:
        for match in pattern.finditer(text):
            if not HYPOTHETICAL.search(re.split(r"[.!?\n]", text[max(0, match.start() - 40):match.start()])[-1]):
                yield next(group for group in match.groups() if group is not None)


def resolve(field, raw):
    if field == "mental_health":
        return value(field, DIAGNOSES.get(raw, raw))
    if field == "marital_status":
        return MARRIED.get(raw) or value(field, raw)
    if field == "parental_status":
        return CHILDREN.get(raw, "parent")
    if field == "employment_status":
        return EMPLOYMENT.get(raw.replace("self-employed", "self employed"), None) or value(field, raw)
    if field == "gender":
        return GENDERED.get(raw) or value(field, raw)
    if field == "generation":
        return value(field, re.sub(r"(?<=[zx])er$", "", raw))
    return value(field, raw)


def peel(field, words):
    for size in range(min(4, len(words)), 0, -1):
        if (size > 1 or words[-1] not in WORD_CODES) and (result := value(field, " ".join(words[-size:]))) is not None:
            return result, words[:-size]
    return None, words


def places(kind, raw):
    words = raw.replace(",", " ").split()
    for end in range(len(words), 0, -1):
        if found := place(kind, " ".join(words[:end])):
            return found
    return {}


def place(kind, raw):
    found = {}
    country_field, state_field, city_field = PLACE_FIELDS[kind]
    words = raw.replace(",", " ").split()
    country, words = peel(country_field, words)
    region, words = peel(state_field, words)
    if words and len(words) <= 3 and (town := value(city_field, " ".join(words))) in CITIES:
        found[city_field] = town
    elif words:
        return {}
    if region is not None:
        found[state_field] = region
    if country is not None:
        found[country_field] = country
    return found


def tags(text, found):
    for match in (*TAG_SELF.finditer(text), *TAG_ANY.finditer(text)):
        age, sex = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
        if (age := value("age", age)) is not None:
            found.setdefault("age", age)
            found.setdefault("gender", value("gender", sex))
            break
    if match := TAG_FOR.search(text):
        found.setdefault("gender", value("gender", match.group(2)))
        if match.group(1) or match.group(3):
            found.setdefault("age", value("age", match.group(1) or match.group(3)))
    if match := AGE_START.search(text) or AGE_BRACKET.search(text):
        found.setdefault("age", value("age", match.group(1)))


def stats(text, found):
    for match in HEIGHT_ANY.finditer(text):
        if not OTHER.search(text[max(0, match.start() - 25):match.start()]) and (height := value("height", match.group(1))) is not None:
            found["height"] = height
            break
    if "height" in found or "age" in found:
        for match in WEIGHT_ANY.finditer(text):
            if not OTHER.search(text[max(0, match.start() - 25):match.start()]) and (weight := value("weight", match.group(1))) is not None:
                found["weight"] = weight
                break


def extract(text):
    text = SKIP.sub(" ", text.lower())
    found = {}
    tags(text, found)
    stats(text, found)
    for field in PHRASES:
        for raw in search(field, text):
            if field in PLACE_FIELDS:
                for key, result in places(field, raw.strip()).items():
                    found.setdefault(key, result)
                if any(key in found for key in PLACE_FIELDS[field]):
                    break
                continue
            if (result := resolve(field, raw.strip())) is not None:
                found.setdefault(field, result)
                break
    return {field: result for field, result in found.items() if result is not None}
