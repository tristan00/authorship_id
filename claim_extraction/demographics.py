import re

from .common import BOT_TEXT, HEDGE, I, SELF_HEDGE, TAGGED, clause, group, rule
from .config import YEAR

UNITS = r"(?:years? ago|yrs? ago|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|times|percent|%|lbs?|kgs?|pounds|miles|km|cm|dollars|bucks|k\b|grand|hp|mph|degrees|feet|ft|inches|in\b|seconds|secs?|euros?|points|pts|ounces|oz|inch)"
OTHERS = re.compile(r"\b(?:my|his|her|their|our|your|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|ex|friend|son|daughter|brother|sister|mom|dad|mother|"
                    r"father|dom|sub|guy|girl|man|woman|someone|somebody|with|e\.g|eg|example|like|for|to|and|older|younger|current|new|another|this|that)\W*$")
SELF = re.compile(r"(?:\b(?:i|me|myself|i'm|im|i am|ich|moi|yo)|^)\W*$")

GENDERS = {"guy": "male", "man": "male", "dude": "male", "male": "male", "boy": "male", "bloke": "male", "lad": "male", "gentleman": "male", "dad": "male", "father": "male",
           "husband": "male", "hubby": "male", "mum": "female", "mom": "female", "mother": "female", "wife": "female", "woman": "female", "girl": "female", "female": "female",
           "lady": "female", "gal": "female", "chick": "female", "girlie": "female", "milf": "female", "dilf": "male", "m": "male", "f": "female", "nb": "non-binary", "non-binary": "non-binary",
           "nonbinary": "non-binary", "enby": "non-binary", "nb": "non-binary", "genderfluid": "non-binary", "agender": "non-binary", "genderqueer": "non-binary",
           "trans woman": "trans woman", "transwoman": "trans woman", "trans girl": "trans woman", "mtf": "trans woman", "trans man": "trans man", "transman": "trans man",
           "trans guy": "trans man", "ftm": "trans man", "trans": "transgender, unspecified", "transgender": "transgender, unspecified"}
KINSHIP = {"son": "male", "brother": "male", "uncle": "male", "nephew": "male", "grandpa": "male", "grandfather": "male", "granddad": "male", "grandad": "male", "stepdad": "male", "widower": "male",
           "boyfriend": "male", "daughter": "female", "sister": "female", "aunt": "female", "niece": "female", "grandma": "female", "grandmother": "female", "granny": "female",
           "stepmom": "female", "widow": "female", "girlfriend": "female", "housewife": "female", "mommy": "female", "bro": "male", "twink": "male", "femboy": "male",
           "daddy": "male", "milf": "female", "hotwife": "female"}
GENDERS |= KINSHIP
GENDER_WORDS = rf"(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|girl|female|lady|gal|chick|{'|'.join(KINSHIP)})"
ADJECTIVES = (r"(?:(?:\d{2}[- ]?(?:years?|yrs?|y/?o)[- ]?(?:old )?|single|married|straight|gay|bi|bisexual|white|black|asian|latino|latina|hispanic|indian|young|old|older|middle[- ]aged|"
              r"tall|short|fat|chubby|skinny|fit|average|normal|regular|grown|cis|cisgender|divorced|disabled|autistic|working|stay[- ]at[- ]home|new|first[- ]time|"
              r"american|british|canadian|australian|christian|muslim|jewish|catholic|retired|lonely|horny|shy|curvy|petite|busy|proud) ){0,3}")
ORIENTATIONS = {"gay": "gay", "lesbian": "lesbian", "bisexual": "bisexual", "bi": "bisexual", "pansexual": "pansexual", "pan": "pansexual", "asexual": "asexual", "ace": "asexual",
                "queer": "queer, unspecified", "straight": "straight", "heterosexual": "straight", "hetero": "straight", "homosexual": "gay", "aroace": "asexual", "aro-ace": "asexual", "str8": "straight"}
ETHNICITIES = {"white": "white", "caucasian": "white", "black": "black", "african american": "black", "asian": "east asian", "east asian": "east asian", "chinese": "east asian",
               "korean": "east asian", "japanese": "east asian", "taiwanese": "east asian", "south asian": "south asian", "indian": "south asian", "desi": "south asian",
               "pakistani": "south asian", "bangladeshi": "south asian", "southeast asian": "southeast asian", "filipino": "southeast asian", "filipina": "southeast asian",
               "vietnamese": "southeast asian", "thai": "southeast asian", "latino": "hispanic or latino", "latina": "hispanic or latino", "latinx": "hispanic or latino",
               "hispanic": "hispanic or latino", "mexican": "hispanic or latino", "arab": "middle eastern or north african", "middle eastern": "middle eastern or north african",
               "persian": "middle eastern or north african", "native american": "indigenous", "indigenous": "indigenous", "aboriginal": "indigenous",
               "pacific islander": "pacific islander", "mixed": "mixed", "mixed race": "mixed", "biracial": "mixed", "multiracial": "mixed", "african": "black"}
SPANISH_SPEAKING_AMERICA = ["argentine", "argentinian", "bolivian", "chilean", "colombian", "costa rican", "cuban", "dominican", "ecuadorian", "guatemalan", "honduran", "mexican", "nicaraguan", "panamanian", "paraguayan", "peruvian", "puerto rican", "salvadoran", "uruguayan", "venezuelan"]
ARAB_LEAGUE_AND_IRAN = ["algerian", "bahraini", "comorian", "djiboutian", "egyptian", "emirati", "iranian", "iraqi", "jordanian", "kuwaiti", "lebanese", "libyan", "mauritanian", "moroccan", "omani", "palestinian", "qatari", "saudi", "somali", "sudanese", "syrian", "tunisian", "yemeni"]
ETHNICITIES |= {name: "hispanic or latino" for name in SPANISH_SPEAKING_AMERICA} | {name: "middle eastern or north african" for name in ARAB_LEAGUE_AND_IRAN}
BODIES = {"skinny": "very thin", "very thin": "very thin", "underweight": "very thin", "thin": "slim", "slim": "slim", "slender": "slim", "lean": "slim", "athletic": "athletic or muscular",
          "muscular": "athletic or muscular", "fit": "athletic or muscular", "buff": "athletic or muscular", "jacked": "athletic or muscular", "toned": "athletic or muscular",
          "average": "average", "average build": "average", "curvy": "curvy", "thick": "curvy", "chubby": "chubby or overweight", "overweight": "chubby or overweight",
          "fat": "chubby or overweight", "heavy": "chubby or overweight", "bbw": "chubby or overweight", "plus size": "chubby or overweight", "plus-size": "chubby or overweight",
          "obese": "obese", "morbidly obese": "obese", "petite": "slim"}
HAIRS = {"blonde": "blonde", "blond": "blonde", "brown": "brown", "brunette": "brown", "black": "black", "red": "red", "ginger": "red", "auburn": "red", "a redhead": "red",
         "redhead": "red", "a ginger": "red", "grey": "grey or white", "gray": "grey or white", "white": "grey or white", "silver": "grey or white", "pink": "dyed unusual color",
         "blue": "dyed unusual color", "purple": "dyed unusual color", "green": "dyed unusual color", "bald": "bald", "balding": "bald", "a blonde": "blonde"}
FREE = r"(?:(?!(?:not|never|no|with|for|to|than|like|and|or|that|who|this|the|my|his|her|your|their|our|a|an|in|on|at|from|about|by|into|fan|friend|friends)\b)[\w'-]+ )"
PLURALS = {"men": "male", "guys": "male", "dudes": "male", "males": "male", "dads": "male", "fathers": "male", "husbands": "male",
           "women": "female", "girls": "female", "ladies": "female", "females": "female", "moms": "female", "mothers": "female", "wives": "female"}
COLORS = {"ebony": "black", "wasian": "mixed"}
OTHER_ETHNIC = "|".join(sorted(map(re.escape, {*ETHNICITIES, *COLORS} - {"white", "black", "mixed"}), key=len, reverse=True))
PERSON = r"(?:m|f|male|female|guy|girl|man|woman|dude|bro|boy|top|bottom|bull|daddy|dad|mom|milf|wife|hubby|couple|here|stud|twink|bear|femboy|sub|dom|\d{2})\b"
ETHNIC = re.compile(rf"(?<![\w-])(?:(white|black|mixed)(?=\s*(?:[,.!/|)]|$|{PERSON}))|({OTHER_ETHNIC}))(?![\w-])")
SEEKING = re.compile(r"\b(?:looking|seeking|seeks|searching|wants?|needs?|craving|into|for|who|with|hmu)\b")
STATURE = re.compile(r"(?<![\w.$'])([4-7])(?:\s?(?:'|ft|foot|feet)\s?(\d{1,2})?|[\"”](?=\d)(\d{1,2}))\s?(?:\"|”|''|in\b|inches)?(?![\d'\"”])")
GIRTH = re.compile(r"(?:hung|cock|dick|bbc|bwc|length|inch\w*|\d\s?[\"”+]+)\W*(?:\w+\W+)?$")
PARTY = re.compile(r"\b(?:my|his|her|their|our|your|you|you're|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|for|with|like|seeking|looking|want|wants|someone|be)\W+(?:\w+\W+)?$")
HAIRED = re.compile(r"(?<![\w-])(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bperfect )(blonde?|brunette|redhead|ginger|bald)(?![\w-])")
ORIENTED = re.compile(r"(?<![\w-])(?<!\bbe )(?<!\bfor )(?<!\bsome )(?<!\bwith )(?<!\binto )(?<!\bother )(?<!\bhosting )(?<!\bfrom )(bi|bisexual|straight|str8|gay|lesbian|pansexual|hetero)(?![\w-])(?! (?:men|women|guys|girls|porn|couples?|friendly|curious|or|and|to|up|talk|ahead|away|forward|out|ones)\b)")
METRIC = re.compile(r"(?<![\w.])(1[4-9]\d|2[01]\d)\s?cm\b")
SHAPED = re.compile(r"(?<![\w-])(slim|slender|skinny|athletic|muscular|chubby|chub|chunky|curvy|thick|thicc|petite|bbw|stocky|beefy|ripped|toned|dadbod|dad bod|plus[- ]size|obese|overweight|jock|abs|fit(?=\s*(?:[,.!/|)]|$|{PERSON})))(?![\w-])(?! (?:\w+ )?(?:cock|dick|penis|bwc|bbc|shaft|uncut|load|meat)\b)")
MONTHS = "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december"
YEARS_OLD = re.compile(r"(?<![\w$])\d{2}\s?(?:yo|y/o)\b")
THIRD = re.compile(r"\b(?:she|he|her|his|they|their|him|them)\b")
WANTED = re.compile(r"\b(?:you|your|be|in|for|not|no|if|want|wants|like|love|seeking|looking|lover|into)\W+(?:\w+\W+)?$")
FOREIGN = re.compile(r"\b(?:looking for|seeking|want|wants|you|your|under|over|than|at least|taller|shorter|between|she|he|her|his|wife|husband|gf|bf)\b")
CLOSING = re.compile(r"[\(\[](\d{2})[\)\]][^\w\n]*(?:\n|$)")
START = rf"^\W{{0,3}}(\d{{2}})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)"
SHAPES = {"thicc": "curvy", "chub": "chubby or overweight", "chunky": "chubby or overweight", "dadbod": "average", "dad bod": "average", "beefy": "athletic or muscular", "stocky": "chubby or overweight",
          "hourglass": "curvy", "rellenita": "chubby or overweight", "gordita": "chubby or overweight", "flaca": "very thin", "tiny": "very thin", "ripped": "athletic or muscular", "toned": "athletic or muscular", "jock": "athletic or muscular", "abs": "athletic or muscular"}
DESCRIBED = re.compile(r"(?:^|[\s,.!/(|+-])(thick|thicc|curvy|chubby|chub|chunky|bbw|slim|slender|skinny|athletic|fit|muscular|fat|overweight|obese|petite|tiny|average|dadbod|dad bod|stocky|beefy|ripped|toned|hourglass|rellenita|gordita|flaca|plus[- ]size)(?! (?:\w+ )?(?:cock|dick|penis|bwc|bbc|shaft|uncut|load|meat)\b)"
                       r"(?= (?:build|built|body|frame|figure|shape|and |but |af\b|asf\b|girl|guy|woman|man|boy|bro|bull|stud|jock|twink|femboy|sub|dom|cub|otter|bottom|top|bear|daddy|milf|hotwife|wife|husband|hubby|mom|dad|f\b|m\b|here|latina|latino|black|white|asian|blonde|brunette|\d)|[\s,.!/)|]*$|\s*[,/|.!])")


POSTERS = {"m": "male", "f": "female", "w": "female", "fb": "female", "fu": "female", "futa": "female", "tf": "trans woman", "mtf": "trans woman", "tm": "trans man",
           "ftm": "trans man", "nb": "non-binary", "wm": "male", "mwm": "male", "swm": "male", "dwm": "male", "bm": "male", "wf": "female"}
LOOKING = re.compile(r"(?<![a-z0-9])(?:(\d{2})\s*)?[\[\(]?\s*(nb|mtf|ftm|tf|tm|futa|fb|fu|[mf])((?:[mf]|/\w+)*)\s*4\s*((?:[mfatr]|me|nb)\w*)\s*[\]\)]?(?:\s*[-–|:#]?\s*(\d{2})(?!\d))?")
AGED = re.compile(r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?((?:[smd]?w|b)m|wf|mtf|ftm|tf|tm|fb|[mf])|((?:[smd]?w|b)m|tf|tm|[mfw])\s?(\d{2}))(?![\w'%]|[-/]\d)")
SENTENCE = re.compile(r"[.!?\n]")
SPEAKER = re.compile(r"\b(?:i|i'm|im|i am|me|my name is)\b")
WORDED = re.compile(r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?(?:yo|y/o|yrs?|years?(?: old)?)?[\s,]*\(?(male|female)\)?|(male|female)[\s,]*(\d{2}))(?![\w'%])")
BRACKETED = re.compile(r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?[\(\[]\s*([mf])\s*[\)\]]|[\(\[](\d{2})[\)\]]\s?(m|f|male|female)\b|([mf])\s?[\(\[](\d{2})[\)\]]|[\(\[]([mf])[\)\]]\s?(\d{2})\b)")
ROLES = {"bro": "male", "bwc": "male", "bbc": "male", "bull": "male", "twink": "male", "femboy": "male", "daddy": "male", "stud": "male", "milf": "female", "hotwife": "female", "mommy": "female"}
OPENING = re.compile(r"(?:^|\n)\W*(?:(\d{2})\s?(?:yo|y/o|yrs?|years? old)?[\s,]+(?:[a-z]+\s){0,2}?(m|f|male|female|guy|girl|man|woman|dude|bro|wife|mom|milf|hotwife|dad|daddy|bwc|bbc|bull|twink|femboy|stud)\b(?!')|(?:a\s)?(?:[a-z]+\s)?(wife|milf|hotwife|mom|mum|mommy|daddy|dad|bro|guy|girl|woman|man|lady)(?:\s+of\s+\d|[\s,]*(\d{2}))\b(?=[\s,.!]|$))")


def owned(lowered, start):
    before = SENTENCE.split(lowered[max(0, start - 24):start])[-1]
    return bool(SELF.search(before)) or (start < 60 and not OTHERS.search(before)) or not re.search(r"\w", before)


def tags(text, lowered, found):
    automatic = BOT_TEXT.search(lowered)
    for match in LOOKING.finditer(lowered):
        if owned(lowered, match.start()):
            found.setdefault(("gender", POSTERS[match.group(2)]), match.start())
            if age := match.group(1) or match.group(5):
                found.setdefault(("age", age), match.start())
            if not automatic and match.group(2) == "m" and not match.group(3) and match.group(4) == "m":
                found.setdefault(("sexual_orientation", "gay"), match.start())
    for match in AGED.finditer(lowered):
        if match.group(2) == "m" and (re.match(rf"\s*{UNITS}", lowered[match.end():])):
            continue
        age, letter = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
        bracketed = lowered[match.start() - 1:match.start()] in ("(", "[")
        if not (owned(lowered, match.start() - bracketed) or (bracketed and not OTHERS.search(lowered[max(0, match.start() - 25):match.start() - 1]) and (match.start() < 60 or SPEAKER.search(SENTENCE.split(lowered[max(0, match.start() - 80):match.start()])[-1]))) or re.search(r"\bmy\s?[\(\[]$", lowered[:match.start()])):
            continue
        found.setdefault(("gender", POSTERS[letter]), match.start())
        found.setdefault(("age", age), match.start())
    for match in WORDED.finditer(lowered):
        if owned(lowered, match.start()) and not re.match(rf"\s*{UNITS}", lowered[match.end():]):
            found.setdefault(("gender", match.group(2) or match.group(3)), match.start())
            found.setdefault(("age", match.group(1) or match.group(4)), match.start())
    for match in BRACKETED.finditer(lowered):
        if owned(lowered, match.start()):
            found.setdefault(("gender", GENDERS[match.group(2) or match.group(4) or match.group(5) or match.group(7)]), match.start())
            found.setdefault(("age", match.group(1) or match.group(3) or match.group(6) or match.group(8)), match.start())
    for match in OPENING.finditer(lowered):
        found.setdefault(("gender", GENDERS.get(match.group(2) or match.group(3)) or ROLES[match.group(2) or match.group(3)]), match.start())
    for match in CLOSING.finditer(lowered):
        if owned(lowered, match.start()):
            found.setdefault(("age", match.group(1)), match.start())
    if match := re.match(START, lowered):
        found.setdefault(("age", match.group(1)), 0)
    tagged = LOOKING.search(lowered, 0, 300) or AGED.search(lowered, 0, 120) or WORDED.search(lowered, 0, 120) or re.match(r"\W*\d{2},?\s", lowered) or YEARS_OLD.search(lowered, 0, 80)
    if tagged or re.match(r"\W*(?:i'm|im|i am)\b", lowered):
        for match in DESCRIBED.finditer(lowered[:400]):
            if not PARTY.search(lowered[max(0, match.start(1) - 24):match.start(1)]) and not GIRTH.search(lowered[max(0, match.start(1) - 24):match.start(1)]):
                found.setdefault(("body_type", BODIES.get(match.group(1)) or SHAPES[match.group(1)]), match.start())
        own = SEEKING.split(lowered[:200], 1)[0]
        if tagged and not automatic:
            for match in ORIENTED.finditer(own):
                found.setdefault(("sexual_orientation", ORIENTATIONS[match.group(1)]), match.start())
        for match in SHAPED.finditer(own):
            if not WANTED.search(lowered, max(0, match.start() - 20), match.start()):
                found.setdefault(("body_type", BODIES.get(match.group(1)) or SHAPES[match.group(1)]), match.start())
        for match in ETHNIC.finditer(own if tagged else ""):
            found.setdefault(("ethnicity", ETHNICITIES.get(match.group(1) or match.group(2)) or COLORS[match.group(2)]), match.start())
        for match in HAIRED.finditer(lowered, 0, 300):
            if not FOREIGN.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]):
                found.setdefault(("hair_color", HAIRS[match.group(1)]), match.start())
        for match in METRIC.finditer(lowered):
            if not FOREIGN.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]):
                found.setdefault(("height", match.group(1)), match.start())
        for match in STATURE.finditer(lowered):
            if int(match.group(2) or match.group(3) or 0) < 12 and not FOREIGN.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]):
                found.setdefault(("height", str(round((int(match.group(1)) * 12 + int(match.group(2) or match.group(3) or 0)) * 2.54))), match.start())


BOUNDARY = r"\b(?:because|cause|cuz|coz|cos|bc|since|and|but|so|although|though|as)\b"
ASKED = re.compile(r"[^.!?\n,;]{0,40}\?")


def said(attribute, pattern, value, hedge=HEDGE):
    if hedge is TAGGED:
        return rule(attribute, pattern, value, TAGGED)
    limit = re.compile(rf"(?:{hedge.pattern})(?!.*{BOUNDARY})", re.S)
    asked = attribute not in ("age", "gender", "height", "weight")

    def stated(match):
        text, start = match.string, match.start()
        if limit.search(text, max(clause(text, start), start - 40), start) or (asked and ASKED.match(text, match.end())):
            return None
        return value(match)
    return rule(attribute, pattern, stated, TAGGED)


def mine(value):
    return lambda match: value(match) if owned(match.string, match.start()) else None


def spoken(value):
    def known(match):
        prefix = SENTENCE.split(match.string[max(0, match.start() - 80):match.start()])[-1]
        if THIRD.search(prefix) or re.search(r"\b(?:that|it|which|this)(?:'s| is| was)\s*$", prefix) or not (owned(match.string, match.start()) or SPEAKER.search(prefix)):
            return None
        return value(match)
    return known


def listed(value):
    return lambda match: None if ASIDE.search(match.string, match.start() + 2, match.start(match.lastindex)) else value(match)


def alone(value):
    return lambda match: None if THIRD.search(SENTENCE.split(match.string[max(0, match.start() - 80):match.start()])[-1]) else value(match)


def ages(value):
    return value if 13 <= int(value) <= 99 else None


LISTED = rf"\b{I} [^.!?\n;]{{0,40}}?"
ASIDE = re.compile(r"\b(?:looking|seeking|want|wants|than|taller|shorter|you|he|she|his|her|my|like|into|for)\b")
AGE = [
    said("age", rf"\b{I} (?:only |almost |nearly |just |now |about |turning |currently |a |an )?(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?(?![\w%'/+-]|[.,:]\d)(?!\s*{UNITS}|\s*(?:and|or|-)\s*\d)", lambda match: ages(match.group(1))),
    said("age", r"\bas an? (\d{2})[- ]?(?:years?|yr)[- ]?old\b", lambda match: ages(match.group(1))),
    said("age", r"(?:\bi(?:'ve| have)? |^|[.!?] )(?:just |recently |finally )?turned (\d{2})\b(?! (?:years|minutes|weeks|percent|%))", lambda match: ages(match.group(1))),
    said("age", r"\bi'?m (?:a |an )?(\d{2})[\s-]?(?:yo|y/o|y\.o\.?|years? old|yr old|year-old)\b", lambda match: ages(match.group(1))),
    said("age", r"(?:^|[.!?\n] *)(\d{2}) (?:years? old|yo|y/o) (?:here|male|female|guy|girl|man|woman|m|f)\b", lambda match: ages(match.group(1))),
    said("age", r"(?:^|[.!?\n] *)at (\d{2}),? (?:i|i'm|im)\b|\bfreshly (\d{2})\b", lambda match: ages(match.group(1) or match.group(2))),
    said("age", r"\bmy age is (\d{2})\b|\bage\s*[:=]\s*(\d{2})\b|(?=age )(?<!\bof )(?<!\bover )(?<!\bunder )(?<!\blegal )(?<!\bsame )(?<!\bthe )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\btheir )\bage \(?(\d{2})\)?\b(?!\s*(?:and|or|to|-|\+|/)\s*\d|\+|\s*(?:and|or) (?:up|older|over|above|under|below)\b)", lambda match: ages(match.group(1) or match.group(2) or match.group(3))),
    said("age", r"\bi was born in ((?:19[3-9]\d)|(?:200\d)|(?:201[0-3]))\b", lambda match: str(YEAR - int(match.group(1)))),
    said("age", rf"^(?:(?![$#+£€])\W){{0,2}}[\[\(]?(\d{{2}})[\]\)]?(?=[\s,.!\]…]|$)(?!\s+(?!yrs?\b|years?\b)[a-z]{{2,}}s\b|\s*{UNITS}|[.,:/]\d|\s*[-–/x+]\s*\d|\s*(?:and|or|to|-)\s+\d|\.\s*\d|\s+(?:of|out|times|people|years? (?:ago|of)|is|was|isn't|wasn't|would|will|more|minutes|seconds|percent|k|point|points|roll|eur|euros?|usd|tl|rs|kr|pln|kilo|кило|лет|{MONTHS})\b)", lambda match: ages(match.group(1)), TAGGED),
    said("age", r"\b(?:i|me|i'm|im|i am|myself|ich)\b[^.!?\n()]{0,25}\((\d{2})\)", lambda match: ages(match.group(1)), SELF_HEDGE),
    said("age", r"(?=\d\d)(?<!\bis )(?<!\bwas )(?<!\bare )(?<!\bwere )(?<!\bof )(?<!\bthan )(?<!\bunder )(?<!\bover )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(?:^|(?<=[\s(\[,]))(\d{2})\s?(?:yo|y/o|y\.o\.?|yr old|year old|years old|yrs old)\b(?! (?:son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat|car|house|man|woman|guy|male|female|friend|wife|husband)\b)", spoken(lambda match: ages(match.group(1))), SELF_HEDGE),
    said("age", r"(?:^|\n|\bme\s*[:=-])[^\S\n]*[>*•\\-]{0,2}[^\S\n]*(\d{2})\s*,\s*(?:[mf]\b|male\b|female\b|[4-7]\s?['’]\s?\d|\d{2,3}\s?(?:lbs?|kg|cm)\b)|\bme\s*[-:=]\s*(\d{2})\b(?!\s*(?:%|[-/:.]\d))|^\W*(\d{2})[- ]?(?:jährige[rn]?|jähriger)\b|\bmit (\d{2}) jahren\b|\b(\d{2}) éves (?:vagyok|leszek)\b|\ba mis (\d{2}) años\b",
         lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    said("age", r"\b(?:tengo|tenho|j'ai) (\d{2})(?: (?:años|anos|ans))?\b|\bya[sş] ?:? ?(\d{2})\b|\b(\d{2}) jahre alt\b|\bich bin (\d{2})\b", lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    said("age", r"(?:^\W*|\b(?:i|me|ich|myself|moi|yo)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*(\d{2})\s*[\]\)]|[\[\(]\s*(\d{2})\s*[,/]\s*([mfw])\s*[\]\)])", lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    said("age", r"(?:^|[\s.!?])([mf])\s?(\d{2})\W*$|(?:^|[\s.!?])(\d{2})(?:\s?f| m)\W*$", lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    said("age", rf"^\W*(\d{{2}})\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(?:male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bottom|top|sub|dom|cuck|virgin|couple)\b", lambda match: ages(match.group(1)), TAGGED),
    said("age", r"\b(?:ho|imam|mam|j'ai|tengo|tenho|jestem|tinc|heb) (\d{2}) ?(?:anni|godina|godine|lat|lata|ans|años|anos|jaar|anys)\b|(?:^|[.!?,\n] *)(?:homme|femme) de (\d{2}) ans\b|^\W*(\d{2}) ?(?:lat|lata|anni|ans|años|anos|godina|jahre)\b", lambda match: ages(next(filter(None, match.groups()))), TAGGED),
]

GENDER = [
    said("gender", r"(?:^\W*|\b(?:i|me|ich|myself|moi|yo)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*\d{2}\s*[\]\)]|[\[\(]\s*\d{2}\s*[,/]\s*([mfw])\s*[\]\)])", lambda match: {"m": "male", "f": "female", "w": "female"}[match.group(1) or match.group(2)], TAGGED),
    said("gender", rf"\b{I} (?:(?:also|just|only|still|actually|literally|already|genuinely|honestly|proudly|really|definitely|obviously|basically|simply) )?(?:an? |the )?{ADJECTIVES}{GENDER_WORDS}\b(?! (?:friend|friends|of|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent)\b)(?!'s)", group(GENDERS)),
    said("gender", rf"\b{I} (?:just |only |also |still |actually |literally |really |definitely |obviously |simply |basically )?(?:an? |the |one ){FREE}{{0,3}}?{GENDER_WORDS}\b(?! (?:friend|friends|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent|energy|moment|problem)\b)(?!'s)", group(GENDERS)),
    said("gender", rf"^\W*(?!(?:the|this|that|any|every|a|an|my|your|his|her|our|their)\b)(?:[a-z]+ ){{0,3}}?{GENDER_WORDS}\b(?= (?:here|looking|seeking|searching|for|4)\b)", group(GENDERS), TAGGED),
    said("gender", rf"\b{I} (?:an? )?{FREE}{{0,3}}?in (his|her) (?:early |mid |late )?(?:\d0'?s|teens|twenties|thirties|forties|fifties|sixties|seventies)\b", group({"his": "male", "her": "female"})),
    said("gender", r"\b(?:an? |for an? )?(?:[\w'-]+ )?(girl|guy|woman|man|lady|gal|dude|bloke|women|men|ladies|girls|guys|dudes) like (?:me|myself|us)\b|\bhelp an? (?:\w+ )?(girl|gal|guy|dude|lady|bro|sister|sis) out\b", lambda match: GENDERS.get(match.group(1) or match.group(2)) or PLURALS.get(match.group(1) or "") or {"bro": "male", "sister": "female", "sis": "female"}.get(match.group(2)), TAGGED),
    said("gender", rf"(?=as )(?<!\byou )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bme )\bas an? (?:fully )?{ADJECTIVES}{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    said("gender", rf"(?:(?:^|[.!?,;:(\n]) *|\b(?:i|me|myself|and|but|so|even)\s+)as an? {FREE}{{1,3}}?{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    said("gender", rf"\bbeing an? {FREE}{{0,2}}?{GENDER_WORDS},? (?:i|i'm|im|myself)\b|(?:^|[.!?\n] *)just (?:an?|your|ur|another|some) {FREE}{{0,3}}?{GENDER_WORDS} (?:with|who|from|in|trying|looking|that|next|doing|living)\b", lambda match: GENDERS[match.group(1) or match.group(2)]),
    said("gender", r"\b(?:i'm|im|i am) ([mf])(?=[\s,.!)/]|$)(?!\s*\*)|^\W*([mf])\W*$", lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    said("gender", r"(?:^|[\s,(\]])(milf|hotwife|daddy|dilf|bull|twink|femboy|sissy|bimbo)(?: here| looking| seeking| loves| needs| wants| for| 4\b)", group({"milf": "female", "hotwife": "female", "bimbo": "female", "daddy": "male", "dilf": "male", "bull": "male", "twink": "male", "femboy": "male", "sissy": "male"}), SELF_HEDGE),
    said("gender", rf"(?:^|[.!?,;] *)(?:an? )?{FREE}{{0,2}}?{GENDER_WORDS} here\b", group(GENDERS)),
    said("gender", rf"\b{I} (?:a |an )?(non-binary|nonbinary|enby|genderfluid|agender|genderqueer|trans woman|transwoman|trans girl|trans man|transman|trans guy|mtf|ftm)\b(?! (?:people|rights|friend|kids))", group(GENDERS)),
    said("gender", r"(?:^|(?<=[\s,(\]]))[\(\[]\s*([mf])\s*[\)\]]", group(GENDERS), TAGGED),
    said("gender", r"\b(?:makes|made|got|gets|getting) me (?:so )?(hard|wet)\b|\b(?:i'm|im|i am) (?:so |already |rock )?(hard|wet|dripping) (?:for|thinking|right now)\b|\bi'?m your (girl|boy|man|woman|princess|slut|goddess)\b",
         lambda match: {"hard": "male", "wet": "female", "dripping": "female", "girl": "female", "princess": "female", "slut": "female", "goddess": "female", "boy": "male", "man": "male", "woman": "female"}[next(filter(None, match.groups()))], SELF_HEDGE),
    said("gender", r"(?<![\w'])[\(\[]?(female|male|guy|girl|woman|man|dude|lady|f|m)(?: in(?:my |her |his )?(?:early |mid |late )?\d0'?s)? here\b|\bfellow (?:\w+ )?(dude|guy|woman|man|lady|girl|mom|dad) here\b",
         lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    said("gender", rf"^\W*\d{{2}}\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy)\b",
         lambda match: {"queen": "female", "king": "male", "bbw": "female", "milf": "female", "stud": "male", "bull": "male", "twink": "male", "femboy": "male", "daddy": "male"}.get(match.group(1)) or GENDERS[match.group(1)], TAGGED),
    said("gender", r"(?:^|[\s,(\[])(t4[mfat]|ts girl|tgirl|trans girl|transgirl|mtf|ftm|trans guy|transman|transwoman)\b|^\W*(agender|non-?binary|enby|genderfluid|genderqueer)\b|\b(domme|dominatrix|mistress)\b(?= (?:here|looking|seeking|available|for)\b)",
         mine(lambda match: GENDERS.get(match.group(1), "trans woman") if match.group(1) and not match.group(1).startswith("t4") else "trans woman" if match.group(1) else GENDERS[match.group(2).replace("nonbinary", "non-binary")] if match.group(2) else "female"), TAGGED),
    said("gender", r"(?:^|[\s.!?])([mf])\s?(\d{2})\W*$|(?:^|[\s.!?])(\d{2})(?:\s?(f)| (m))\W*$", lambda match: GENDERS[match.group(1) or match.group(4) or match.group(5)], TAGGED),
    said("gender", r"\b(?:soy|sou) (?:un |una |uma |um )?(hombre|mujer|chica|chico|homem|mulher)\b|\bje suis une? (homme|femme)\b|\bich bin (?:ein |eine )?(mann|frau)\b",
         lambda match: {"hombre": "male", "chico": "male", "homem": "male", "homme": "male", "mann": "male"}.get(next(filter(None, match.groups())), "female")),
    said("gender", r"\b(?:we|us|we're|we are) (?:as |fellow |other |older |younger |black |white |gay |straight |trans |single |married |tall |short )?(men|women|guys|girls|ladies|dudes|females|males|moms|dads|mothers|fathers|wives|husbands)\b", group(PLURALS)),
]

SEXUAL_ORIENTATION = [
    said("sexual_orientation", r"\b(gay|lesbian|bi|bisexual|pansexual|asexual|aroace|aro-ace|ace|straight|str8|queer)(?: (?:guy|girl|man|woman|male|female|dude|bro|boy|couple|bottom|top|bear|twink|femboy|wife|husband|dad|mom))? here\b|\b(?:i'm|im|i am) (?:a |an )?(?:\w+ )?bi[- ]?curious\b|\bcurious(?<!\bfor curious)(?<!\bfor a curious)(?<!\bseeking curious)(?<!\bseeking a curious)(?<!\bany curious) (?:guy|male|man|dude|bro|boy|here)\b",
         lambda match: ORIENTATIONS.get(match.group(1)) or "queer, unspecified", SELF_HEDGE),
    said("sexual_orientation", rf"\b{I} (?:a |an )?(?:(?:\d{{2}}[- ]?(?:years?|yr)[- ]old|cis|single|married|black|white|asian|trans|young|old|older|proud|openly|also|both|totally|fully) )*(gay|lesbian|bisexual|bi|pansexual|asexual|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|men|women|guys|people|porn|marriage|ally|rights|shooter|a)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", rf"\b{I} (?:an? )?(?:(?!\w+ing\b|gonna\b|be\b|go\b|get\b|setting\b){FREE}){{0,3}}?(gay|lesbian|bisexual|bi|pansexual|asexual|aroace|aro-ace|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|friends|men|women|guys|girls|people|porn|marriage|ally|rights|shooter|a|content|stuff|scene|community|culture|sex)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", r"^\W*(?:[a-z]+ ){0,2}?(gay|bi|bisexual|straight|str8|lesbian|pansexual) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|husband|dad|daddy|bear|bro|boy|woman|man|male|female|twink|femboy|bottom|top|chub|stud|dude|couple)\b(?! (?:friend|friends|porn)\b)", group(ORIENTATIONS), TAGGED),
    said("sexual_orientation", r"\bas an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer)\b(?! (?:up|out|forward|away|from|to|into|after|back|down|ahead|through|off|on|in|at|for|with|couple|people|community|friend|friends|ally|rights|men|women|guys|porn|bar|club|marriage|man|woman|guy|girl|person|male|female|dude|boy)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", r"(?:^|\n)\W*(?:\d{2}\s*(?:[mf]|yo|y/o)?|[mf]\s?\d{2}|[\(\[]\d{2}[\)\]])[\s,]+(?:(?!(?:i|was|not|never|used)\b)[a-z]+[\s,]+){0,2}?(straight|str8|bi|bisexual|gay|lesbian|hetero|pan)\b(?! (?:men|women|guys|girls|porn|couple|friend))|(?:^|[,|/] ?)(str8|hetero|bi|straight)\s*(?:[,|/]|here\b)", lambda match: ORIENTATIONS.get(match.group(1) or match.group(2)) or "straight", TAGGED),
    said("sexual_orientation", r"\bas an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude|couple|boy)\b", group(ORIENTATIONS)),
    said("sexual_orientation", r"(?:^|[.!?,;] *)(gay|lesbian|bi|bisexual|straight|pansexual) (?:\w+ )?(?:male|female|guy|girl|man|woman|dude|couple) here\b", group(ORIENTATIONS)),
]

ETHNICITY = [
    said("ethnicity", rf"{LISTED},\s*(?:and\s+)?({'|'.join(map(re.escape, ETHNICITIES))})(?=\s*(?:[,.!;&/)]|and\b|$))", listed(group(ETHNICITIES)), SELF_HEDGE),
    said("ethnicity", rf"\b{I} (?:a |an |half |half-|also |\d{{2}},? )?({'|'.join(map(re.escape, ETHNICITIES))})(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself|lady))?(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family)\b)", group(ETHNICITIES)),
    said("ethnicity", rf"(?=as )(?<!\bsuch )(?<!\bsame )(?<!\bdressed )(?<!\btreated )(?<!\bseen )\bas an? ({'|'.join(map(re.escape, ETHNICITIES))})\b(?! (?:people|folks|community|communities|culture|food|neighborhood|area|country|family|friend|friends|men|women|guys|girls|kids|person's)\b)(?!'s)", group(ETHNICITIES)),
    said("ethnicity", rf"(?:^|[\s,(\]])(?<!\ba )(?<!\ban )(?<!\bthe )(?<!\bevery )(?<!\bany )(?<!\ball )(?<!\bseeking )(?<!\bfor )(?<!\bwant )(?<!\bwants )(?<!\blike )(?<!\bof )({'|'.join(map(re.escape, ETHNICITIES))}) (?:guy|girl|male|female|man|woman|dude|queen|king|couple|bottom|top|daddy|milf|bbw|twink|stud|bull|wife|hubby|baddie|boy|lady|mom|dad|chick|babe|beauty|femboy|sub|dom)\b(?= (?:here|looking|seeking|for|with|in|4|from|wants|needs|who|ready)\b)", mine(group(ETHNICITIES)), SELF_HEDGE),
    said("ethnicity", rf"\b(?:i'm|im|i am|as) (?:just |also |only )?(?:a |an )?(?:(?!\w+ing\b){FREE}|an? ){{0,4}}?({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|lady|mom|dad|mother|father|kid|teen|boy|bro|immigrant|canadian|british|australian|bottom|top|chub|bear|daddy|stud|bull|twink|femboy)\b", group(ETHNICITIES), SELF_HEDGE),
    said("ethnicity", rf"(?:^|[\s,(\]])(?<!\ba )(?<!\ban )(?<!\bthe )(?<!\bevery )(?<!\bany )(?<!\ball )(?<!\bseeking )(?<!\bfor )(?<!\bwant )(?<!\bwants )(?<!\blike )(?<!\bof )((?:spicy |hot |sexy |thick |young |cute |mature |shy )?(?:latina|latino|black|white|asian|indian|desi|arab|ebony|mixed)) (?:mami|papi|queen|king|domme|dom|sub|bottom|top|bull|stud|baddie|goddess|princess|daddy|milf|bbw|twink|boy|girl|guy|man|woman|male|female|couple|wife|hubby)\b",
         mine(alone(lambda match: ETHNICITIES.get(match.group(1).split()[-1]) or ("black" if match.group(1).split()[-1] == "ebony" else None))), SELF_HEDGE),
    said("ethnicity", rf"\b(?:i'm|im|i am|as an?|a)? ?half[- ]({'|'.join(map(re.escape, ETHNICITIES))})[,/ ]+(?:and )?half[- ]({'|'.join(map(re.escape, ETHNICITIES))})\b|\bethnically (?:{'|'.join(map(re.escape, ETHNICITIES))}) ?(?:/|and|&) ?(?:{'|'.join(map(re.escape, ETHNICITIES))})\b", lambda match: "mixed"),
    said("ethnicity", r"\bwe (black|white|asian|latina|latino|hispanic|indian|desi|arab|indigenous|native) (?:women|men|people|folks|girls|guys)\b|\bsoy (latino|latina|mexicano|mexicana|negro|negra|blanco|blanca)\b|\bwhite ?boi\b|\b(?:i'm|im|i am|i m) (black|white|asian|latina|latino|hispanic|mixed|biracial|desi)(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|and \w+ing)\b)",
         lambda match: (lambda word: {"mexicano": "hispanic or latino", "mexicana": "hispanic or latino", "negro": "black", "negra": "black", "blanco": "white", "blanca": "white", "native": "indigenous"}.get(word) or ETHNICITIES.get(word) or "white")(next(filter(None, match.groups()), "white")), SELF_HEDGE),
]

HEIGHT = [
    said("height", rf"{LISTED}(?<=[\s,/])([4-7])\s?(?:'|ft|foot|feet)\s?(?:and )?(\d{{1,2}})?\s?(?:\"|''|in\b|inches)?(?!\d|\.\d|')(?! (?:away|from|deep|long|wide)\b)",
         listed(lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None)),
    said("height", r"\bheight\s*[:=-]\s*(?:(1[4-9]\d|2[01]\d)\s?cm|([4-7])\s?(?:'|ft|foot|feet)\s?(\d{1,2})?)|\b(?:for me|me|i'm|im|i am) at ([4-7])\s?(?:'|ft)\s?(\d{1,2})?(?!\d|\.\d)|(?<![\w.])([4-7])\s?,\s?(\d{1,2})\s?(?:\"|”|'')?\s*tall\b",
         lambda match: match.group(1) or (lambda feet, inches: str(round((int(feet) * 12 + int(inches or 0)) * 2.54)) if int(inches or 0) < 12 else None)(match.group(2) or match.group(4) or match.group(6), match.group(3) or match.group(5) or match.group(7))),
    said("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just |a )?([4-7])\s*(?:'|ft|foot|feet)\s*(?:and )?(\d{{1,2}})?\s*(?:\"|''|in\b|inches)?(?!\d|\.\d)(?! (?:away|from|deep|long|wide)\b)",
         lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None),
    said("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just )?(1[4-9]\d|2[01]\d)\s*cm\b", lambda match: match.group(1)),
    said("height", r"(?=(?:^|[\s,|/(])[4-7])(?<!\bhe's)(?<!\bshe's)(?<!\bhe is)(?<!\bshe is)(?<!\bwho's)(?<!\bwho is)(?<!\bthey're)(?<!\bis)(?<!\bwas)(?<!\bare)(?<!\bbe)(?<!\bover)(?<!\bunder)(?<!\bthan)(?<!\ba)(?<!\ban)(?<!\bthe)(?:^|[\s,|/(])([4-7])\s?(?:'|’|ft)(?!s\b)\s?(\d{1,2})?\s?(?:\"|”|''|in\b)?(?=\s*[,|/]?\s*(?:\d{2,3}\s?(?:lbs?|kg|pounds)|tall|and\b|[,|/]|$|(?:man|woman|guy|girl|male|female|m|f)\b))", lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None, SELF_HEDGE),
]

LOAD = re.compile(r"(?:\b(?:under|over|than|lose|losing|lost|gain|gained|gaining|by|of|an?|the|another|extra|to|from|bench|squat|lift|lifting|carry|carrying)\s*|[-–/\d]\s*)\W?$")

WEIGHT = [
    said("weight", rf"\bi (?:weigh|weight|'m at|am at|'m currently at|'m currently)\s+(?:about |around |roughly |almost |like |just under |over |under )?(\d{{2,3}}(?:\.\d)?)\s*(lbs?|pounds|kg|kgs|kilos)\b|\b{I} (\d{{2,3}})\s*(lbs?|pounds|kg|kgs)\b",
         lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))))(float(match.group(1) or match.group(3)), match.group(2) or match.group(4))),
    said("weight", r"(?:^|[\s,|/(])(\d{2,3})(?:ish)?\s?(lbs?|pounds|kg|kgs)\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain|gained|more|less|bag|bags|box|dumbbells?|plates?|bench|squat|deadlift))", lambda match: None if LOAD.search(match.string, max(0, match.start() - 16), match.start() + 1) or re.match(r"\s*-+>", match.string[match.end():]) else (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))) if 35 <= amount * (1 if unit.startswith("k") else .4536) <= 250 else None)(float(match.group(1)), match.group(2)), SELF_HEDGE),
]

BODY_TYPE = [
    said("body_type", rf"{LISTED},\s*(?:and\s+)?(?:very |pretty |quite |kinda |kind of |a bit |a little |fairly |super )?({'|'.join(map(re.escape, BODIES))}|toned|ripped|stocky|chubby|chub)(?=\s*(?:[,.!;&/)]|and\b|but\b|$|\n))", listed(lambda match: BODIES.get(match.group(1)) or SHAPES[match.group(1)]), SELF_HEDGE),
    said("body_type", r"^\W*(?:[a-z]+ )?(chubby|chub|curvy|thick|thicc|petite|slim|skinny|fat|bbw|ssbbw|athletic|muscular|fit|stocky|toned) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|milf|mom|dad|daddy|bear|bro|boy|woman|man|hotwife|latina|latino|twink|femboy|bottom|top)\b(?! (?:\w+ )?(?:cock|dick))", lambda match: BODIES.get(match.group(1)) or SHAPES.get(match.group(1)) or "chubby or overweight", TAGGED),
    said("body_type", r"\b(?:an? )?(slim|slender|skinny|athletic|muscular|fit|chubby|chub|chunky|curvy|thick|thicc|petite|bbw|ssbbw|stocky|beefy|ripped|toned|fat|tiny|average|obese|overweight) (?:\w+ )?(?:girl|guy|woman|man|lady|boy|dude|bro|wife|mom|milf|dad|daddy|bear|hotwife|chick|gal)(?: like me\b| here\b)", lambda match: BODIES.get(match.group(1)) or SHAPES.get(match.group(1)) or "chubby or overweight", TAGGED),
    said("body_type", r"\b(?:\d{2}\s?[mf]|i'm|im|i am|i'?ve been|i keep) (?:myself )?in (?:good|great|decent|excellent|amazing|top|pretty good|really good) shape\b", lambda match: "athletic or muscular"),
    said("body_type", r"\bmy (?:\w+ )?curves\b", lambda match: "curvy", SELF_HEDGE),
    said("body_type", rf"\b{I} (?:very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |a |an )?({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman)\b)", group(BODIES)),
    said("body_type", r"(?:^|[\s,|/])(bbw|curvy|petite|chubby|athletic|muscular|slim)\s*(?:f|female|woman|girl|m|male|guy|here)\b", group(BODIES), SELF_HEDGE),
    said("body_type", rf"\b{I} (?:a |an |very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |naturally |extra |also )*({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman|mood|chance|mess|game|difference|problem|issue|plus|day|week|month|year)\b)", group(BODIES), SELF_HEDGE),
    said("body_type", r"\b(?:my|this|with a|with my) (?:\w+ )?(curvy|chubby|thick|thicc|petite|fat|skinny|slim|athletic|muscular|fit|tiny|bbw|plus[- ]size|average|toned|slender|dad) (?:body|build|frame|figure|bod|self)\b|\b(slim|athletic|average|slender|muscular|stocky|heavy|thin|fit|curvy|chubby|thick|thicc|petite|tiny)(?: and (?:fit|toned|athletic|slim))? build\b|\bbuilt like an hourglass\b|\bextra (thicc|thick)\b",
         lambda match: (lambda word: "curvy" if word in ("thicc", "thick", None) else {"tiny": "very thin", "dad": "average", "stocky": "chubby or overweight", "heavy": "chubby or overweight"}.get(word, BODIES.get(word)))(match.group(1) or match.group(2) or match.group(3)), TAGGED),
]

HAIR_COLOR = [
    said("hair_color", r"\b(?:i'?ve been|been|being|i went|went|i'm going|im going|going) bald\b", lambda match: "bald"),
    said("hair_color", r"\bmy (?:natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b|\bi have (?:long |short |curly |natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)]),
    said("hair_color", rf"\b{I} (?:a |an |naturally |going )?(blonde|blond|brunette|redhead|a redhead|ginger|a ginger|bald|balding)\b(?! (?:joke|moment|people)\b)", group(HAIRS)),
    said("hair_color", r"(?:^|[\s,|/(])(blonde?|brunette|redhead|ginger)\s*(?:f|female|woman|girl|m|male|guy|here|milf|babe|beauty|bombshell|teen|bimbo|slut|wife|mom|mommy|cutie|princess|queen)\b|\bwith (?:long |short |curly |dark |light |natural |highlighted |dyed )*(blonde?|brown|black|red|ginger|auburn|grey|gray|silver|pink|blue|purple|green)(?: highlighted)? hair\b",
         alone(lambda match: HAIRS[match.group(1) or match.group(2)]), SELF_HEDGE),
    said("hair_color", r"\b(?:i'm|im|i am|i m) (?:still |also |just |actually |really |naturally )?(?:a |an )?(?:(?!not\b|never\b|no\b)\w+ ){0,2}?(red ?head|redhead|ginger|blonde|blond|brunette)\b|(?:^|[\s,|/(])(red ?head|redhead|brunette)\b(?= (?:\w+ )?(?:here|bitch|boy|girl|guy|babe|milf|wife|mom|looking|f\b|m\b))|\b(?:i (?:actually |also |still |now )?have|i've got|my|with) (?:long |short |thick |thin |curly |straight |wavy |natural |graying |greying |dark |light |bright )*(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green)(?: buzz cut| curly| wavy)? hair\b",
         alone(lambda match: HAIRS.get((match.group(1) or match.group(2) or match.group(3)).replace(" ", "")) or "red"), SELF_HEDGE),
]

RULES = [*AGE, *GENDER, *SEXUAL_ORIENTATION, *ETHNICITY, *HEIGHT, *WEIGHT, *BODY_TYPE, *HAIR_COLOR]
