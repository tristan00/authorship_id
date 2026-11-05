import re

from .common import BOT_TEXT, HEDGE, I, SELF_HEDGE, TAGGED, clause, group, question, rule
from .config import YEAR

IM = r"i(?<!\wi)(?:'m|m| am|am| m|'am|'?ve been|'ve always been)"
UNITS = r"(?:years? ago|yrs? ago|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|times|percent|%|lbs?|kgs?|pounds|miles|km|cm|dollars|bucks|k\b|grand|hp|mph|degrees|feet|ft|inches|in\b(?!\s+(?!(?:a|an|the|few|couple|two|three|four|five|six|weeks?|months?|years?|days?|hours?|minutes?|length|girth|long|thick|wide|tall|cut|uncut|soft|hard|erect)\b)[a-z]{3,})|seconds|secs?|euros?|points|pts|ounces|oz|inch)"
OTHERS = re.compile(r"\b(?:my|his|her|their|our|your|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|ex|friend|son|daughter|brother|sister|mom|dad|mother|"
                    r"father|dom|sub|guy|girl|man|woman|someone|somebody|with|e\.g|eg|example|like|for|to|and|older|younger|current|new|another|this|that|the)\W*$")
SELF = re.compile(r"(?:\b(?:i|me|myself|i'm|im|i am|ich|moi|yo|as|bin)(?:\s+an?)?|^)\W*$")

GENDERS = {"guy": "male", "man": "male", "dude": "male", "male": "male", "boy": "male", "bloke": "male", "lad": "male", "gentleman": "male", "dad": "male", "father": "male",
           "husband": "male", "hubby": "male", "mum": "female", "mom": "female", "mother": "female", "wife": "female", "woman": "female", "women": "female", "girl": "female", "female": "female",
           "lady": "female", "gal": "female", "chick": "female", "girlie": "female", "dilf": "male", "m": "male", "f": "female", "nb": "non-binary", "non-binary": "non-binary",
           "nonbinary": "non-binary", "enby": "non-binary", "genderfluid": "non-binary", "agender": "non-binary", "genderqueer": "non-binary",
           "trans woman": "trans woman", "transwoman": "trans woman", "trans girl": "trans woman", "mtf": "trans woman", "trans man": "trans man", "transman": "trans man",
           "trans guy": "trans man", "ftm": "trans man", "trans": "transgender, unspecified", "transgender": "transgender, unspecified"}
KINSHIP = {"son": "male", "brother": "male", "uncle": "male", "nephew": "male", "grandpa": "male", "grandfather": "male", "granddad": "male", "grandad": "male", "stepdad": "male", "widower": "male",
           "boyfriend": "male", "daughter": "female", "sister": "female", "aunt": "female", "niece": "female", "grandma": "female", "grandmother": "female", "granny": "female",
           "stepmom": "female", "widow": "female", "girlfriend": "female", "housewife": "female", "mommy": "female", "bro": "male", "twink": "male", "femboy": "male",
           "daddy": "male", "milf": "female", "hotwife": "female"}
GENDER_WORDS = rf"(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|(?<=\ba )women|girl|female|lady|gal|chick|{'|'.join(KINSHIP)})"
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
         "blue": "dyed unusual color", "purple": "dyed unusual color", "green": "dyed unusual color", "bald": "bald", "balding": "bald", "a blonde": "blonde", "shaved head": "bald"}
FREE = r"(?:(?!(?:not|never|no|with|for|to|than|like|and|or|that|who|this|the|my|his|her|your|their|our|a|an|in|on|at|from|about|by|into|fan|friend|friends)\b)[\w'-]+ )"
PLURALS = {"men": "male", "guys": "male", "dudes": "male", "males": "male", "dads": "male", "fathers": "male", "husbands": "male",
           "women": "female", "girls": "female", "ladies": "female", "females": "female", "moms": "female", "mothers": "female", "wives": "female"}
ROLES = {"bwc": "male", "bbc": "male", "bull": "male", "stud": "male", "boi": "male", "jock": "male", "bear": "male", "cub": "male", "king": "male",
         "cougar": "female", "gilf": "female", "domme": "female", "queen": "female", "bbw": "female", "sis": "female"}
GENDERS |= KINSHIP | PLURALS | ROLES
COLORS = {"ebony": "black", "wasian": "mixed"}
OTHER_ETHNIC = "|".join(sorted(map(re.escape, {*ETHNICITIES, *COLORS} - {"white", "black", "mixed"}), key=len, reverse=True))
PERSON = r"(?:m|f|male|female|guy|girl|man|woman|dude|bro|boy|top|bottom|bull|daddy|dad|mom|milf|wife|hubby|couple|here|stud|twink|bear|femboy|sub|dom|\d{2})\b"
STATURE = re.compile(r"([4-7])(?<![\w.$'][4-7])(?:\s?(?:'|ft|foot|feet)\s?(\d{1,2})?|[\"”](?=\d)(\d{1,2}))\s?(?:\"|”|''|in\b|inches)?(?![\d'\"”])")
GIRTH = re.compile(r"(?:hung|cock|dick|bbc|bwc|length|inch\w*|uncut|cut|shaved|girthy|veiny|long|(?<!')(?<!'\d)\d\s?[\"”+]+)\W*(?:\w+\W+)?$")
PARTY = re.compile(r"\b(?:my|his|her|their|our|your|you|you're|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|for|with|like|seeking|looking|want|wants|someone|be)\W+(?:\w+\W+)?$")
HAIRED = re.compile(r"(?<![\w-])(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bperfect )(?:(blonde?|brunette|redhead|ginger|bald|shaved head)|(?:(?:long|short|thick|thin|curly|straight|wavy|natural|naturally|graying|greying|dark|light|messy|medium|shaggy|buzzed|shoulder[- ]length)\s+)*(brown|black|red|auburn|grey|gray|white|silver|pink|blue|purple|green)(?:ish)?\s+hairs?\b)(?![\w-])")
ORIENTED = re.compile(r"(?:(?<![\w-])|(?<=\s-))(?<!\bbe )(?<!\bfor )(?<!\bsome )(?<!\bwith )(?<!\binto )(?<!\bother )(?<!\bhosting )(?<!\bfrom )(bi|bisexual|straight|str8|gay|lesbian|pansexual|hetero)(?![\w-])(?! (?:men|women|guys|girls|porn|couples?|friendly|friends?|people|community|rights|marriage|bars?|clubs?|curious|or|and (?:\w+ )?(?:men|women|guys|girls|gay|straight|bi|bisexual|lesbian|trans|queer|people|couples?)|to|up|talk|ahead|away|forward|out|ones)\b)")
CURIOUS = re.compile(r"\b(?:bi|bisexual|bicurious|bi-curious|curious|straight|str8|dl|down low|married|taken|wife|girlfriend|gf|hetero)\b")
METRIC = re.compile(r"(?<![\w.])(1[4-9]\d|2[01]\d)\s?cm\b")
SHAPED = re.compile(r"(?<![\w-])(slim|slender|skinny|athletic|muscular|chubby|chub|chunky|curvy|bbw|stocky|beefy|toned|dadbod|dad bod|plus[- ]size|obese|overweight|jock|fit(?=\s*(?:[,.!/|)]|$)))(?![\w-])")
PHALLIC = re.compile(r" (?:\w+ )?(?:cock|dick|penis|bwc|bbc|shaft|uncut|load|meat|wood|ropes|creamy|cumming|girth)\b")
STURDY = {"athletic", "fit", "muscular", "muscled", "shredded", "jacked", "buff", "toned", "ripped", "stocky", "overweight", "obese", "dadbod", "dad bod", "bbw", "jock"}
MONTHS = "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december"
DIGIT = re.compile(r"\d")
COUNTED = re.compile(rf"\b(?:{MONTHS}|level|lvl|day|number|no|chapter|episode|season|page|version|room|unit|size|model|wife|husband|gf|bf|girlfriend|boyfriend|son|daughter|mom|dad)\W*$")
GAME = re.compile(r"\n[^\S\n]*\^\([^\n]*\)[^\S\n]*$")
AD = re.compile(r"\b(?:[mf]4[mfat]\w*|dms?|snap|sc|kik|tele|telegram|hmu|horny|sext|sexting|bwc|bbc|cock|dick|pussy|fwb|nsa|hookup|host|hosting|discreet|bator|goon|gooner|trade|nudes|bi|gay|str8|daddy|milf|sissy|femboy|twink|bull|cuck|hotwife|bbw|onlyfans|kinky|naughty)\b")
YEARS_OLD = re.compile(r"(?<![\w$])\d{2}\s?(?:yo|y/o)\b")
THIRD = re.compile(r"\b(?:she|he|her|his|they|their|him|them)\b|\b(?:my|our|your) (?:\w+ )?(?:wife|husband|hubby|gf|bf|girlfriend|boyfriend|partner|son|daughter|kid|baby|mom|mother|dad|father|brother|sister|friend|dog|cat|puppy)\b")
WANTED = re.compile(r"\b(?:you|your|be|in|for|not|no|if|want|wants|like|love|seeking|looking|lover|into)\W+(?:\w+\W+)?$")
FOREIGN = re.compile(r"\b(?:looking for|seeking|want|wants|you|your|under|over|than|at least|taller|shorter|between|she|he|her|his|wife|husband|gf|bf)\b")
CLOSING = re.compile(r"[\(\[](\d{2})[\)\]][^\w\n]*(?:\n|$)")
START = rf"^\W{{0,3}}(\d{{2}})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)"
SHAPES = {"muscled": "athletic or muscular", "shredded": "athletic or muscular", "thicc": "curvy", "chub": "chubby or overweight", "chunky": "chubby or overweight", "dadbod": "average", "dad bod": "average", "beefy": "athletic or muscular", "stocky": "chubby or overweight",
          "hourglass": "curvy", "rellenita": "chubby or overweight", "gordita": "chubby or overweight", "flaca": "very thin", "tiny": "very thin", "ripped": "athletic or muscular", "toned": "athletic or muscular", "jock": "athletic or muscular", "ssbbw": "chubby or overweight"}
BODY_NOUNS = r"(?:build|built|body|bod|frame|figure|shape|girl|guy|woman|man|boy|boi|bro|bull|stud|jock|twink|femboy|sub|dom|cub|otter|bottom|top|vers|bear|daddy|milf|hotwife|wife|husband|hubby|mom|mum|dad|grandpa|grandma|lady|gal|chick|dude|male|female|married|single|f|m|here|latina|latino|black|white|asian|blonde|brunette|boyfriend|girlfriend|bf|gf|breeder|slut|sissy|cuck|queen|king|baddie|babe|teen|mommy)\b"
CROWD = r"(?:guys|girls|women|men|ladies|tops|bottoms|bulls|bros|dudes|couples|people|queens|wives|moms|milfs|daddies|bears|twinks|chicks|females|males|chasers)\b"
DESIRED = re.compile(r"n't\b|\bain'?t\b|\b(?:looking|look for|seeking|thing for|searching for|prefer\w*|pref|into|love|loves|like|likes|interested in|any|bonus|must|not|isn't|no|if|you|your|you're|ur)\b")
DESCRIBED = re.compile(r"(?:^|[\s,.!/(|+-])(thin|lean|fit|muscled|shredded|jacked|buff|fat|tiny|average|ripped|hourglass|rellenita|gordita|flaca)"
                       rf"(?! (?:\w+ ){{0,2}}{CROWD})(?= (?:\w+ ){{0,2}}?{BODY_NOUNS}| (?:and |but |with |w/ |af\b|asf\b|\d)|[\s,.!/)|]*$|\s*[,/|.!&+])")
WANTING = re.compile(r"\b(?:want|wants|wish|wished|need|needs)\b|" + DESIRED.pattern)
ETHNIC = re.compile(rf"(?<![\w-])(?:(white|black|mixed)(?=\s*(?:[,.!/|)&+]|$|\d)|(?<!mixed) (?:with|w/|w) | (?:\w+ ){{0,2}}?{BODY_NOUNS}|\s*{PERSON})|({OTHER_ETHNIC}))(?![\w-])(?! (?:\w+ ){{0,2}}{CROWD})")


POSTERS = {"m": "male", "f": "female", "w": "female", "fb": "female", "fu": "female", "futa": "female", "tf": "trans woman", "mtf": "trans woman", "tm": "trans man",
           "ftm": "trans man", "nb": "non-binary", "wm": "male", "mwm": "male", "swm": "male", "dwm": "male", "bm": "male", "wf": "female"}
LOOKING = re.compile(r"(?<![a-z0-9])(?:[\[\(]?(\d{2})(?:\s*/\s*\d{2})?[\]\)]?\s*)?[\[\(]?\s*(nb|mtf|ftm|tf|tm|futa|fb|fu|[mf])((?:[mf]|/\w+)*)\s*4\s*((?:[mfatr]|me|nb)[a-z/]*)\s*[\]\)]?(?:\s*[-–|:#]?\s*[\[\(]?(\d{2})(?!\d))?")
AGED = re.compile(r"(?=[\dmfwsdbtn])(?<![\w$£€#'/:+-])(?<![\w,]\.)(?<!\d,)(?:(\d{2})\s?[/\\-]?\s?((?:[smd]?w|b)m|wf|mtf|ftm|tf|tm|fb|nb|[mf])(?:(?<=m)f(?![\w'])|(?<=f)m(?![\w']))?|((?:[smd]?w|b)m|tf|tm|fb|nb|[mfw])\s?[/'.-]?\s?(\d{2})(?:[mfa](?![\w'])|(?<=m\d\d)f\d{2}(?![\w'])|(?<=f\d\d)m\d{2}(?![\w']))?)(?!(?!_)[\w'%]|[-/]\d|-[a-z]\d)")
SENTENCE = re.compile(r"[.!?\n]")
FIRST = re.compile(r"\b(?:i|i'm|im|me|my|myself|mine)\b")
LETTERED = r"(?<![\w$£€#'/:+-])(?:\d{2}\s?[mf]|[mf]\s?\d{2})(?![\w'%])"
WEIGHED = re.compile(rf"(?<![\w.])\d{{2,3}}\s?(?:kg|kgs|kilos?|lbs?|pounds)\b|{LETTERED}")
MEASURED = re.compile(rf"(?<![\w.$'])[4-7]\s?(?:'|ft|foot|feet)|(?<![\w.])(?:1[4-9]\d|2[01]\d)\s?cm\b|{LETTERED}|\bweight\s*[:=-]")
SPEAKER = re.compile(r"\b(?:i|i'm|im|i am|me|my name is)\b")
WORDED = re.compile(rf"(?=[\dmf])(?<![\w$#.,'/:+-])(?:(\d{{2}})\s?(?:yo|y/o|yrs?|years?(?: old)?)?[\s,]*{ADJECTIVES}\(?(male|female)\)?|(male|female)[\s,]*(\d{{2}}))(?![\w'%])")
BRACKETED = re.compile(r"(?=[\d(\[mf])(?<![\w$#.,'/:+-])(?:(\d{2})\s?[\(\[]\s*([mf])\s*[\)\]]|[\(\[](\d{2})[\)\]]\s?(m|f|male|female)\b|([mf])\s?[\(\[](\d{2})[\)\]]|[\(\[]([mf])[\)\]]\s?(\d{2})\b)")
ANATOMY = {"cock": "male", "dick": "male", "penis": "male", "balls": "male", "foreskin": "male", "bwc": "male", "bbc": "male", "pussy": "female", "vagina": "female", "clit": "female", "tits": "female", "boobs": "female", "breasts": "female", "pregnant": "female"}
HUNG = re.compile(r"(b[wb]c)(?<![\w-]b[wb]c)(?![\w-])")
COMPARED = re.compile(r"\b(?:is|was|are|were|be|being|than|of|to|from|between|claims|claimed|like|avg|average|mine's|mines|u|ur|you|your|you're|she|he|her|his|they|their|wife|husband|gf|bf|under|over|at least|taller|shorter|e\.g)\b")
QUEER = re.compile(r"\b(?:bi|bisexual|bicurious|bi-curious|curious|gay|lesbian|pan|pansexual|queer|homo|trans|tgirl|ts|cd|crossdresser|sissy|femboy|twink|m4m|f4f|mm|ff|mmf|ffm|couple|couples|rp|roleplay|role-play|role play|session|story|plot|character|characters|fantasy|scenario|kik|discord)\b")
OPPOSITE = {"m": re.compile(r"\b(?:woman|women|girl|girls|female|females|lady|ladies|wife|gf|girlfriend|milf|milfs|mom|moms|pussy|boobs|tits|her|she)\b"),
            "f": re.compile(r"\b(?:man|men|guy|guys|male|males|husband|bf|boyfriend|daddy|cock|dick|him|he)\b")}
SIZED = re.compile(r"(?<![\w.$'])[4-7]\s?(?:'|ft)\s?\d{1,2}\b.{0,30}?\b\d{2,3}\s?(?:lbs?|kg|pounds)\b", re.S)
GREETED = re.compile(r"(?:^|[.!?\n,;:(] *|\b(?:hey|hi|hello|yo|sup)\W+(?:\w+\W+)?)$")
NOWADAYS = re.compile(r"\b(?:i was|i started at|started at|i got \w+ at|when i was|since i was) (?:about |around )?(?:\d{1,2}|[a-z]+)\b[^.!?\n]{0,40}?,? (?:and |but |i'm |im |i am )*$")
NAMED = re.compile(r"\b(?:i'm|im|i am|my name is|my name's) [a-z]+$")
COLORED = re.compile(r"\b(?:white|black|asian|latino|latina|hispanic|indian|arab|mixed)[,\s]+(\d{2})\b(?![\d%.,]\d|\s*(?:min|mins|minutes|hours|days|years|yrs|percent|k|m|lbs|kg|inch|inches|cm)\b)")
OPENING = re.compile(r"(?:^|\n)\W*(?:(\d{2})\s?(?:yo|y/o|yrs?|years? old)?[\s,]+(?:[a-z]+\s){0,2}?(m|f|male|female|guy|girl|man|woman|dude|bro|wife|mom|milf|hotwife|dad|daddy|bwc|bbc|bull|twink|femboy|stud)\b(?!')|(?:a\s)?(?:[a-z]+\s)?(wife|milf|hotwife|mom|mum|mommy|daddy|dad|bro|guy|girl|woman|man|lady)(?:\s+of\s+\d|[\s,]*(\d{2}))\b(?=[\s,.!]|$))")


def owned(lowered, start):
    before = SENTENCE.split(lowered[max(0, start - 24):start])[-1]
    return bool(SELF.search(before)) or (start < 60 and not OTHERS.search(before)) or not re.search(r"\w", before)


def desired(lowered, start, pattern=WANTING):
    return pattern.search(SENTENCE.split(lowered[max(0, start - 80):start])[-1])


def tags(text, lowered, found):
    if not DIGIT.search(lowered) and not re.match(r"\W*(?:i'm|im|i am)\b", lowered):
        return
    automatic = BOT_TEXT.search(lowered)
    for match in LOOKING.finditer(lowered):
        if owned(lowered, match.start()) or (("[" in match.group() or "(" in match.group()) and match.start() < 300 and not desired(lowered, match.start(), DESIRED)):
            found.setdefault(("gender", POSTERS[match.group(2)]), match.start())
            if age := ages(match.group(1) or match.group(5)):
                found.setdefault(("age", age), match.start())
            if not automatic and match.group(2) == "m" and not match.group(3) and match.group(4) == "m" and not CURIOUS.search(lowered, 0, 1500):
                found.setdefault(("sexual_orientation", "gay"), match.start())
            if not automatic and age and match.group(2) in ("m", "f") and not match.group(3) and match.group(4) == {"m": "f", "f": "m"}[match.group(2)] and not QUEER.search(lowered, 0, 1500) and (OPPOSITE[match.group(2)].search(lowered, match.end(), 1500)):
                found.setdefault(("sexual_orientation", "straight"), match.start())
    for match in AGED.finditer(lowered):
        if match.group(2) == "m" and (re.match(rf"\s*(?:(?!in\b){UNITS}\b|\d{{1,2}}\s?s\b|(?:a|per) (?:year|season|week|month)\b|away\b)", lowered[match.end():])):
            continue
        age, letter = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
        if not ages(age):
            continue
        bracketed = lowered[match.start() - 1:match.start()] in ("(", "[")
        owner = (owned(lowered, match.start() - bracketed) or re.match(r"\W{0,2}(?:here|hmu|lmk|dm me)\b", lowered[match.end():]) or re.search(r"\bthis $", lowered[max(0, match.start() - 6):match.start()]) or (bracketed and not OTHERS.search(lowered[max(0, match.start() - 25):match.start() - 1]) and (match.start() < 60 or SPEAKER.search(SENTENCE.split(lowered[max(0, match.start() - 80):match.start()])[-1]))) or re.search(r"\bmy\s?[\(\[]$", lowered[max(0, match.start() - 5):match.start()]))
        if owner or (not OTHERS.search(SENTENCE.split(lowered[max(0, match.start() - 24):match.start()])[-1]) and FIRST.search(sentence(lowered, match.start(), match.end()))):
            found.setdefault(("gender", POSTERS[letter]), match.start())
        if owner:
            found.setdefault(("age", age), match.start())
    for match in WORDED.finditer(lowered):
        if owned(lowered, match.start()) and not re.match(rf"\s*{UNITS}", lowered[match.end():]) and ages(match.group(1) or match.group(4)):
            found.setdefault(("gender", match.group(2) or match.group(3)), match.start())
            found.setdefault(("age", match.group(1) or match.group(4)), match.start())
    for match in BRACKETED.finditer(lowered):
        if owned(lowered, match.start()) and ages(match.group(1) or match.group(3) or match.group(6) or match.group(8)):
            found.setdefault(("gender", GENDERS[match.group(2) or match.group(4) or match.group(5) or match.group(7)]), match.start())
            found.setdefault(("age", match.group(1) or match.group(3) or match.group(6) or match.group(8)), match.start())
    for match in OPENING.finditer(lowered):
        found.setdefault(("gender", GENDERS[match.group(2) or match.group(3)]), match.start())
    for match in CLOSING.finditer(lowered.split("\n", 1)[0]):
        if owned(lowered, match.start()) and ages(match.group(1)) and not re.search(r"\b(?:you|your|u|ur)\b", lowered[max(0, match.start() - 120):match.start()]):
            found.setdefault(("age", match.group(1)), match.start())
    if (match := re.match(START, lowered)) and ages(match.group(1)):
        found.setdefault(("age", match.group(1)), 0)
    window = lowered[:1500]
    tagged = LOOKING.search(lowered, 0, 300) or AGED.search(lowered, 0, 120) or WORDED.search(lowered, 0, 120) or BRACKETED.search(lowered, 0, 120) or re.match(r"\W*\d{2},?\s|\W*[\[\(]\d{2}[\]\)]", lowered) or YEARS_OLD.search(lowered, 0, 80) or SIZED.search(lowered, 0, 120) or COLORED.search(lowered, 0, 120)
    signed = tagged or any(attribute == "age" for attribute, _ in found)
    speaking = signed or re.match(r"\W*(?:i'm|im|i am)\b", lowered)
    if not speaking:
        for match in METRIC.finditer(lowered):
            if (owned(lowered, match.start()) or FIRST.search(sentence(lowered, match.start(), match.end())) or WEIGHED.search(line(lowered, match.start()))) and not desired(lowered, match.start()) and not COMPARED.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]):
                found.setdefault(("height", match.group(1)), match.start())
        for match in STATURE.finditer(lowered):
            if (match.group(2) or match.group(3)) and int(match.group(2) or match.group(3)) < 12 and (owned(lowered, match.start()) or FIRST.search(sentence(lowered, match.start(), match.end())) or WEIGHED.search(line(lowered, match.start()))) and not desired(lowered, match.start()) and not COMPARED.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]) and not re.match(r"\s*(?:-|–|to|or)\s*\d", lowered[match.end():]):
                found.setdefault(("height", str(round((int(match.group(1)) * 12 + int(match.group(2) or match.group(3))) * 2.54))), match.start())
    else:
        for match in DESCRIBED.finditer(window):
            before = lowered[max(0, match.start(1) - 24):match.start(1)]
            if (match.group(1) in STURDY or not (GIRTH.search(before) or PHALLIC.match(lowered, match.end(1)))) and not PARTY.search(before) and not desired(lowered, match.start(1)):
                found.setdefault(("body_type", BODIES.get(match.group(1)) or SHAPES[match.group(1)]), match.start())
        if tagged and not automatic:
            for match in ORIENTED.finditer(window):
                if not desired(lowered, match.start()) and not PARTY.search(lowered[max(0, match.start() - 24):match.start()]) and not re.match(rf" (?:\w+ ){{0,2}}{CROWD}", lowered[match.end():]):
                    found.setdefault(("sexual_orientation", ORIENTATIONS[match.group(1)]), match.start())
        for match in SHAPED.finditer(window):
            if not WANTED.search(lowered, max(0, match.start() - 20), match.start()) and (match.group(1) in STURDY or not (GIRTH.search(lowered[max(0, match.start(1) - 24):match.start(1)]) or PHALLIC.match(lowered, match.end(1)))) and not desired(lowered, match.start(1)):
                found.setdefault(("body_type", BODIES.get(match.group(1)) or SHAPES[match.group(1)]), match.start())
        for match in ETHNIC.finditer(window if signed else ""):
            if not PARTY.search(lowered[max(0, match.start() - 24):match.start()]) and not desired(lowered, match.start()):
                found.setdefault(("ethnicity", ETHNICITIES.get(match.group(1) or match.group(2)) or COLORS[match.group(2)]), match.start())
        for match in HUNG.finditer(window if signed else ""):
            if owned(lowered, match.start()) and not PARTY.search(lowered[max(0, match.start() - 24):match.start()]) and not desired(lowered, match.start()):
                found.setdefault(("ethnicity", {"bwc": "white", "bbc": "black"}[match.group(1)]), match.start())
        for match in HAIRED.finditer(window):
            if not FOREIGN.search(SENTENCE.split(lowered[max(0, match.start() - 25):match.start()])[-1]) and not desired(lowered, match.start()):
                found.setdefault(("hair_color", HAIRS[match.group(1) or match.group(2)]), match.start())
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


def sentence(text, start, end):
    return text[max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1:min((found for found in (text.find(mark, end) for mark in ".!?\n") if found >= 0), default=len(text))]


def line(text, start):
    end = text.find("\n", start)
    return text[text.rfind("\n", 0, start) + 1:end if end >= 0 else len(text)]


def personal(value):
    def stated(match):
        text, first = match.string, line(match.string, 0)
        return value(match) if FIRST.search(sentence(text, match.start(), match.end())) or MEASURED.search(line(text, match.start())) or LOOKING.search(first) or AGED.search(first) else None
    return stated


def alone(value):
    return lambda match: None if THIRD.search(SENTENCE.split(match.string[max(0, match.start() - 80):match.start()])[-1]) else value(match)


def ages(value):
    return value if value and value.isascii() and 13 <= int(value) <= 99 else None


LISTED = rf"{IM} [^.!?\n;]{{0,40}}?"
BORN = re.compile(r"(?:(?<![^\W_])i was |(?<![^\W_])(?:^|[.!?\n]) *)$")
CONFESSED = re.compile(rf"{IM} (?:just |also |kinda |a bit |a little |a |an )?$")
CURIOUSLY = re.compile(r"\s*(?:guy|girl|man|woman|male|female|dude|bottom|top|vers|here|m\b|f\b|[,.!|/])")
ASIDE = re.compile(r"\b(?:looking|seeking|want|wants|than|taller|shorter|you|he|she|his|her|my|like|into|for)\b")
PAIRED = r"(?:^\W*|\b(?:i|me|ich|myself|moi|yo|i've|i'm|im|i am|i was)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*(\d{2})\s*[\]\)]|[\[\(]\s*(\d{2})\s*[,/]\s*([mfw])\s*[\]\)])"
TRAILING = r"(?:^|[\s.!?])([mf])\s?(\d{2})\W*$|(?:^|[\s.!?])(\d{2})(?:\s?(f)| (m))\W*$"
POINTED = rf"this(?<=\bthis) (\d{{2}}) ?(?:yo|y/o|yr old|year old|years old)? (?:[a-z]+ ){{0,2}}?{GENDER_WORDS}\b"
AGE = [
    said("age", rf"{IM} (?:(?:only|just|now|turning|currently|also|still|already|literally|actually|finally|officially|technically|basically|a|an) )*(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?(?![\w%'/+-]|[.,:]\d)(?!\s*{UNITS}|\s*(?:and|or|-)\s*\d)", lambda match: ages(match.group(1))),
    said("age", r"as(?<!\was) an? (\d{2})[- ]?(?:years?|yr)[- ]?old\b", lambda match: ages(match.group(1))),
    said("age", r"\b(?:(?:we're|we are) (?:both|only|just|now)|we both are|(?:my \w+|\w+) and i are(?: both)?|me and (?:my )?\w+ are(?: both)?) (\d{2})\b(?!\s*(?:and|or|-|&)\s*\d)(?!\s*(?:%|percent|minutes|mins|hours|days|weeks|months|years? (?:ago|in|into|of|together|married)|miles|km|feet|ft|lbs?|kg|dollars|bucks|k\b))", lambda match: ages(match.group(1))),
    said("age", r"(?:\bi(?:'ve| have)? |^|[.!?] )(?:just |recently |finally )?turned (\d{2})\b(?! (?:years|minutes|weeks|percent|%))", lambda match: ages(match.group(1))),
    said("age", r"\bi'?m (?:a |an )?(?:(?!not\b|never\b)[a-z]+ ){0,3}?(\d{2})[\s-]?(?:yo|y/o|y\.o\.?|years? old|yr old|year-old)\b", lambda match: ages(match.group(1))),
    said("age", r"(?:^|[.!?\n] *)(\d{2}) (?:years? old|yo|y/o) (?:here|male|female|guy|girl|man|woman|m|f)\b", lambda match: ages(match.group(1))),
    said("age", r"(?:^|[.!?\n] *)at (\d{2}),? (?:i|i'm|im)\b|\bfreshly (\d{2})\b", lambda match: ages(match.group(1) or match.group(2))),
    said("age", r"\bmy age is (\d{2})\b|\bage\s*[:=]\s*(\d{2})\b|(?=age\W)(?<!\bof )(?<!\bat )(?<!\bby )(?<!\buntil )(?<!\btill )(?<!\bsince )(?<!\bfrom )(?<!\bbefore )(?<!\bafter )(?<!\bto )(?<!@)(?<!\bover )(?<!\bunder )(?<!\blegal )(?<!\bsame )(?<!\bthe )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\btheir )\bage\s?[\(\[]?(\d{2})[\)\]]?(?![\w+-])(?!\s*(?:and|or|to|-|\+|/)\s*\d|\+|\s*(?:and|or) (?:up|older|over|above|under|below)\b)", lambda match: None if GAME.search(match.string) else ages(match.group(1) or match.group(2) or match.group(3))),
    said("age", r"(\d{2}) here\b(?! (?:in|at|for|since|and|or|is|are|was)\b)", lambda match: ages(match.group(1)) if GREETED.search(match.string, max(0, match.start() - 24), match.start()) else None, SELF_HEDGE),
    said("age", rf"now(?<![a-z]now) (?:i'm |im |i am |(at) )?(\d{{2}})\b(?![\d%/'-]|[.,]\d)(?!\s*{UNITS})", lambda match: ages(match.group(2)) if NOWADAYS.search(match.string, max(0, match.start() - 80), match.start()) or (match.group(1) and re.match(r",? (?:i|i'm|im)\b", match.string[match.end():])) else None, SELF_HEDGE),
    said("age", r"(\d{2}) now(?:\)|\W*$)", lambda match: ages(match.group(1)) if match.string[max(0, match.start() - 2):match.start()] in (", ", " (") or match.string[match.start() - 1:match.start()] == "(" else None, SELF_HEDGE),
    said("age", r"(?:me|myself) at (\d{2})\b(?![\d.,%/'-])", lambda match: ages(match.group(1)) if re.search(r"(?:^|[.!?\n] *)$", match.string[max(0, match.start() - 3):match.start()]) else None, SELF_HEDGE),
    said("age", r", (\d{2}),", lambda match: ages(match.group(1)) if NAMED.search(match.string, max(0, match.start() - 30), match.start()) else None, SELF_HEDGE),
    said("age", r"born in (?:((?:19[3-9]\d)|(?:200\d)|(?:201[0-3]))\b|'(\d{2})\b|([3-9]\d)\b(?![\d,.%]))", lambda match: (str(YEAR - int(match.group(1))) if match.group(1) else str(YEAR - 1900 - int(match.group(2) or match.group(3)))) if BORN.search(match.string, max(0, match.start() - 40), match.start()) else None),
    said("age", rf"^(?=[\s\S]*?[^\W\d_])(?:(?![$#+£€'])\W){{0,2}}[\[\(]?(\d{{2}})[\]\)]?(?=[\s,.!\]…]|$|(?<=\))[a-z])(?!\s+(?!yrs?\b|years?\b|[a-z]+ous\b)[a-z]{{2,}}s\b|\s+(?:years?|yrs?|yr)\b(?!\s+old\b)|(?<=\d)\s+straight\b|\s*{UNITS}|[.,:/]\d|\s*[-–/x+]\s*\d|\s*(?:and|or|to|-)\s+\d|\.\s*\d|\s+(?:of|out|times|people|years? (?:ago|of)|is|was|isn't|wasn't|would|will|more|minutes|seconds|percent|k|point|points|roll|eur|euros?|usd|tl|rs|kr|pln|kilo|кило|лет|psi|cents?|g|mg|ml|hz|fps|gb|mb|tb|mm|rpm|bpm|ppm|dpo|total|million|mill|billion|thousand|gig|gigs|new|हज़ार|{MONTHS})\b)", lambda match: None if GAME.search(match.string) else ages(match.group(1)), TAGGED),
    said("age", r"\b(?:i|me|i'm|im|i am|myself|ich)\b[^.!?\n()]{0,25}\((\d{2})\)", lambda match: ages(match.group(1)), SELF_HEDGE),
    said("age", r"(?=\d\d)(?<!\bis )(?<!\bwas )(?<!\bare )(?<!\bwere )(?<!\bof )(?<!\bthan )(?<!\bunder )(?<!\bover )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(?:^|(?<=[\s(\[,]))(\d{2})\s?(?:yo|y/o|y\.o\.?|yr old|year old|years old|yrs old)\b(?! (?:son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat|car|house|man|woman|guy|male|female|friend|wife|husband|girls|boys|guys|men|women|kids|people|and (?:above|up|over|older|under|below)|or (?:older|younger|above|over|under))\b)", spoken(lambda match: ages(match.group(1))), SELF_HEDGE),
    said("age", r"(?:^|\n)[^\S\n]*[>*•\\-]{0,2}[^\S\n]*(\d{2})\s*,\s*(?:[mf]\b|male\b|female\b|[4-7]\s?['’]\s?\d|\d{2,3}\s?(?:lbs?|kg|cm)\b)|^\W*(\d{2})[- ]?jährige[rn]?\b", lambda match: ages(match.group(1) or match.group(2)), SELF_HEDGE),
    said("age", r"me(?<!\wme)\s*[:=-][^\S\n]*[>*•\\-]{0,2}[^\S\n]*(\d{2})\s*,\s*(?:[mf]\b|male\b|female\b|[4-7]\s?['’]\s?\d|\d{2,3}\s?(?:lbs?|kg|cm)\b)|me(?<!\wme)\s*[-:=]\s*(\d{2})\b(?!\s*(?:%|[-/:.]\d))", lambda match: ages(match.group(1) or match.group(2)), SELF_HEDGE),
    said("age", r"mit(?<!\wmit) (\d{2}) jahren\b|(\d{2}) éves (?:vagyok|leszek)\b|a(?<!\wa) mis (\d{2})(?: años)?\b", lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    said("age", r"\b(?:tengo|tenho|j'ai) (\d{2})(?: (?:años|anos|ans))?\b|\bya[sş] ?:? ?(\d{2})\b|\b(\d{2}) jahre alt\b|\bich bin (\d{2})\b", lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    said("age", PAIRED, lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    said("age", TRAILING, lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    said("age", rf"^\W*(\d{{2}})\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(?:male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bottom|top|sub|dom|cuck|virgin|couple)\b", lambda match: ages(match.group(1)), TAGGED),
    said("age", r"\b(?:ho|imam|mam|j'ai|tengo|tenho|jestem|tinc|heb) (\d{2}) ?(?:anni|godina|godine|lat|lata|ans|años|anos|jaar|anys)\b|(?:^|[.!?,\n] *)(?:homme|femme) de (\d{2}) ans\b|^\W*(\d{2}) ?(?:lat|lata|anni|ans|años|anos|godina|jahre)\b", lambda match: ages(next(filter(None, match.groups()))), TAGGED),
    said("age", r"(?:soy|sou|sono|je suis|eu sou)\b[^.!?\n]{0,40}?\b(?:de|di) (\d{2}) (?:años|anos|ans|anni)\b|(?:hoje|agora|ahora|ya) (?:com|con|tengo|tenho) (\d{2}) (?:anos|años)\b|мне (\d{2})\b|(?:main|mai) (\d{2}) (?:saal |sal )?(?:ka|ki) (?:hoon|hu|hun|hoo)\b|ik ben (\d{2})(?: jaar)?\b(?! (?:kg|kilo|cm|euro|keer|minuten|uur))|(\d{2}) yaşındayım\b", lambda match: None if match.string[match.start() - 1:match.start()].isalpha() else ages(next(filter(None, match.groups()))), SELF_HEDGE),
    said("age", r"^\W*(?:vrouw|homme|femme|mujer|hombre|chica|chico|frau|mann|mulher|homem)\W{1,3}(\d{2})\b", lambda match: ages(match.group(1)), SELF_HEDGE),
    said("age", POINTED, lambda match: ages(match.group(1)), SELF_HEDGE),
    said("age", rf"^[^\n]{{0,80}}?(?=\d\d)(?<![\w$#£€.,'/:+*-])(?<!\bover )(?<!\bunder )(?<!\bfirst )(?<!\bthan )(?<!\blike )(?<!\bin )(?<!\bat )(?<!\bto )(?<!\bfor )(?<!\bwith )(?<!\bof )(?<!\bmax )(?<!\babout )(?<!\baround )(?<!\blast )(?<!\bnext )(?<!\bevery )(?<!\bonly )(?<!\btop )(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bmy )(?<!\byour )(?<!\bis )(?<!\bare )(?<!\bwas )(?<!\bby )(?<!\bfrom )(?<!\bafter )(?<!\bsince )(\d{{2}})(?![\w%'/:+*-]|[.,]\d|\s*{UNITS}|\s*(?:-|to|or|and)\s*\d|\s*(?:inch|in\b|\"|”|cm|mm|lbs?|kg|min|mins|k\b|m\b|hr|hrs|yrs? ago|guys|people|men|women|girls|hours|years|nudes|pics|videos|times|days|weeks|months|users|members|followers|upvotes|likes|million|billion|thousand|transactions|trades|dms|messages|followers|1st|2nd|3rd))", lambda match: ages(match.group(1)) if AD.search(match.string, 0, 300) and not COUNTED.search(match.string, 0, match.start(1)) and len(re.findall(r"(?<!\d)\d\d(?!\d)", match.string.split("\n", 1)[0])) == 1 and not GAME.search(match.string) else None, TAGGED),
    said("age", rf"^[^\n\d]{{0,120}}\n(?:[^\S\n]*\n)*[^\S\n]*[>*•\\-]{{0,2}}[^\S\n]*(\d{{2}})(?=[\s,.!:)]|$)(?!\s*{UNITS}|\s*(?:-|to|or|and|x)\s*\d|[.,:]\d|\s+(?:guys|people|men|women|girls|hours|years|nudes|pics|videos|times|days|weeks|months|minutes|mins|of|out|percent)\b)", lambda match: ages(match.group(1)) if AD.search(match.string, 0, 300) and not GAME.search(match.string) else None, TAGGED),
]

GENDER = [
    said("gender", rf"\b(?:{I}|as|being|just) (?:an? )?(?:{FREE}){{0,2}}?(?:trans|transgender) (woman|girl|female|lady|man|guy|boy|male|dude)\b", lambda match: "trans woman" if match.group(1) in ("woman", "girl", "female", "lady") else "trans man"),
    said("gender", PAIRED, lambda match: POSTERS[match.group(1) or match.group(4)], TAGGED),
    said("gender", rf"{IM} (?:(?:also|just|only|still|actually|literally|already|genuinely|honestly|proudly|really|definitely|obviously|basically|simply) )?(?:an? |the )?{ADJECTIVES}{GENDER_WORDS}\b(?! (?:friend|friends|of|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent)\b)(?!'s)", group(GENDERS)),
    said("gender", rf"{IM} (?:just |only |also |still |actually |literally |really |definitely |obviously |simply |basically )?(?:an? |the |one ){FREE}{{0,3}}?{GENDER_WORDS}\b(?! (?:friend|friends|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent|energy|moment|problem)\b)(?!'s)", group(GENDERS)),
    said("gender", rf"^\W*(?!(?:the|this|that|any|every|a|an|my|your|his|her|our|their)\b)(?:[a-z]+ ){{0,3}}?{GENDER_WORDS}\b(?= (?:here|looking|seeking|searching|for|4)\b)", group(GENDERS), TAGGED),
    said("gender", rf"{IM} (?:an? )?{FREE}{{0,3}}?in (his|her) (?:early |mid |late )?(?:\d0'?s|teens|twenties|thirties|forties|fifties|sixties|seventies)\b", group({"his": "male", "her": "female"})),
    said("gender", r"\b(?:an? |for an? )?(?:[\w'-]+ )?(girl|guy|woman|man|lady|gal|dude|bloke|women|men|ladies|girls|guys|dudes) like (?:me|myself|us)\b|\bhelp an? (?:\w+ )?(girl|gal|guy|dude|lady|bro|sister|sis) out\b", lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    said("gender", rf"(?=as )(?<!\byou )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bme )\bas an? (?:fully )?{ADJECTIVES}{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    said("gender", rf"(?:(?:^|[.!?,;:(\n]) *|\b(?:i|me|myself|and|but|so|even)\s+)as an? {FREE}{{1,3}}?{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    said("gender", rf"\bbeing an? {FREE}{{0,2}}?{GENDER_WORDS},? (?:i|i'm|im|myself)\b|(?:^|[.!?\n] *)just (?:an?|your|ur|another|some) {FREE}{{0,3}}?{GENDER_WORDS} (?:with|who|from|in|trying|looking|that|next|doing|living)\b", lambda match: GENDERS[match.group(1) or match.group(2)]),
    said("gender", r"i(?<!\wi)(?:'m|m| am) ([mf])(?=[\s,.!)/]|$)(?!\s*\*)|^\W*([mf]|male|female)\W*$", lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    said("gender", r"(?:^|[\s,(\]])(milf|hotwife|bull|twink|femboy|cougar|gilf|dilf|domme)(?: here| looking| seeking| loves| needs| wants| for| 4\b)", group(GENDERS), SELF_HEDGE),
    said("gender", rf"(?:^|[.!?,;] *)(?:an? )?{FREE}{{0,2}}?{GENDER_WORDS} here\b", group(GENDERS)),
    said("gender", rf"{IM} (?:a |an )?(non-binary|nonbinary|enby|genderfluid|agender|genderqueer|trans woman|transwoman|trans girl|trans man|transman|trans guy|mtf|ftm)\b(?! (?:people|rights|friend|kids))", group(GENDERS)),
    said("gender", r"(?:^|(?<=[\s,(\]]))[\(\[]\s*([mf])\s*[\)\]]", group(GENDERS), TAGGED),
    said("gender", r"[\(\[](?<![^\s,(\]][\(\[])(?<!\bthe [\(\[])(?<!\ba [\(\[])(?<!\ban [\(\[])\s*(male|female)\s*[\)\]]|i(?<!\wi) \((?:[\w ]+, )?(male|female)\)", mine(lambda match: GENDERS[match.group(1) or match.group(2)]), TAGGED),
    said("gender", r"(?<![\w'])[\(\[]?(female|male|guy|girl|woman|man|dude|lady|f|m)(?: in (?:my |her |his )?(?:early |mid |late )?\d0'?s)? here\b|\bfellow (?:\w+ )?(dude|guy|woman|man|lady|girl|mom|dad) here\b",
         lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    said("gender", rf"^\W*\d{{2}}\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot|bicurious|curious|dl|masc|fem|hairy|smooth|bearded|tattooed|inked|muscular|athletic|slim|skinny|average|kinky|naughty|lonely|bored|verbal) )*(male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bro|boy|boi|jock|bear|cub|dad)\b",
         group(GENDERS), TAGGED),
    said("gender", r"(?:^|[\s,(\[])(t4[mfat]|ts girl|tgirl|trans girl|transgirl|mtf|ftm|trans guy|transman|transwoman)\b|^\W*(agender|non-?binary|enby|genderfluid|genderqueer)\b|\b(domme|dominatrix|mistress)\b(?= (?:here|looking|seeking|available|for)\b)",
         mine(lambda match: None if question(match.string, match.end()) else GENDERS.get(match.group(1), "trans woman") if match.group(1) and not match.group(1).startswith("t4") else "trans woman" if match.group(1) else GENDERS[match.group(2).replace("nonbinary", "non-binary")] if match.group(2) else "female"), SELF_HEDGE),
    said("gender", TRAILING, lambda match: GENDERS[match.group(1) or match.group(4) or match.group(5)], TAGGED),
    said("gender", r"\b(?:soy|sou) (?:un |una |uma |um )?(hombre|mujer|chica|chico|homem|mulher)\b|\bje suis une? (homme|femme)\b|\bich bin (?:ein |eine )?(mann|frau)\b",
         lambda match: {"hombre": "male", "chico": "male", "homem": "male", "homme": "male", "mann": "male"}.get(next(filter(None, match.groups())), "female")),
    said("gender", r"\b(?:we|us|we're|we are) (?:as |fellow |other |older |younger |black |white |gay |straight |trans |single |married |tall |short )?(men|women|guys|girls|ladies|dudes|females|males|moms|dads|mothers|fathers|wives|husbands)\b", group(GENDERS)),
    said("gender", r"i(?<!\wi)(?: have| got|'ve got| ve got|'ve| have got) (?:an? )?(?:[\w-]+,? ){0,3}?(cock|dick|penis|pussy|vagina|clit|tits|boobs|breasts)\b", lambda match: ANATOMY[match.group(1)]),
    said("gender", r"my(?<!\wmy) (?:(?!(?:wife|wifes|husband|hubby|gf|bf|girlfriend|boyfriend|partner|friend|friends|sister|brother|mom|dad|son|daughter|girl|guy|man|woman|lady|ex|and|or|with|in|on|to|your|his|her)\b)[\w-]+,? ){0,3}?(cock|dick|penis|balls|foreskin|bwc|bbc|pussy|vagina|clit|tits|boobs|breasts)\b", lambda match: None if question(match.string, match.end()) else ANATOMY[match.group(1)]),
    said("gender", r"my(?<!\wmy) (?:\w+ )?(?:period|periods|hysterectomy|c-section|pregnancy|pregnancies|miscarriage|miscarriages|uterus|ovaries|cervix|ovulation|menstrual cycle|menopause|postpartum)\b|i(?<!\wi)(?: had an?| had my| got my|'ve had an?) (?:\w+ )?(?:period|periods|hysterectomy|c-section|pregnancy|pregnancies|miscarriage|miscarriages|uterus|ovaries|cervix|ovulation|menstrual cycle|menopause|postpartum)\b|i(?<!\wi) (?:gave birth|am breastfeeding|'m breastfeeding|breastfeed|am nursing my|'m nursing my|was pregnant|got pregnant|have pcos|have endometriosis)\b|i(?<!\wi)(?:'m|m| am) (?:currently |now |still )?(?:\d{1,2} (?:weeks?|months?) )?pregnant\b", lambda match: "female"),
    said("gender", r"^\W*([mf])(?:\s*[|/\\]\s*(?=\w)|\s+(?:for [mf]\b|looking|seeking))", group(GENDERS), TAGGED),
    said("gender", POINTED, lambda match: GENDERS[match.group(2)] if ages(match.group(1)) else None, SELF_HEDGE),
    said("gender", r"^\W*(?:bi|gay|str8|straight|married|single|horny|hung|young|older|mature|curious|bicurious|discreet|dl) ([mf])\b(?! ?\d)(?!')", group(GENDERS), TAGGED),
    said("gender", r"^[^\n]{0,80}?(?=[mf])(?<![\w'/+.(*-])(?<!\bfor )(?<!\bseeking )(?<!\bwant )(?<!\bany )(?<!\bthe )(?<!\ba )(?<!\b4 )(?<!\bor )(?<!\band )(?<!\bno )(?<!\bsingle )(?<!\bas )(?<!\bin )(?<!\bonly )([mf])(?![\w'/+*.)-]|\s*(?:4|for|or|and|&|only|to)\b)", lambda match: GENDERS[match.group(1)] if AD.search(match.string, 0, 300) and not re.search(r"(?<![\w'/+-])[mf](?![\w'/+-])", match.string.split("\n", 1)[0][match.end(1) - match.start():]) and not GAME.search(match.string) else None, TAGGED),
]

SEXUAL_ORIENTATION = [
    said("sexual_orientation", r"\b(gay|lesbian|bi|bisexual|pansexual|asexual|aroace|aro-ace|ace|straight|str8|queer)(?: (?:guy|girl|man|woman|male|female|dude|bro|boy|couple|bottom|top|bear|twink|femboy|wife|husband|dad|mom))? here\b", group(ORIENTATIONS), SELF_HEDGE),
    said("sexual_orientation", rf"{IM} (?:a |an )?(?:(?:\d{{2}}[- ]?(?:years?|yr)[- ]old|cis|single|married|black|white|asian|trans|young|old|older|proud|openly|also|both|totally|fully) )*(gay|lesbian|bisexual|bi|pansexual|asexual|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|men|women|guys|people|porn|marriage|ally|rights|shooter|a)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", rf"{IM} (?:an? )?(?:(?!\w+ing\b|gonna\b|be\b|go\b|get\b|setting\b){FREE}){{0,3}}?(gay|lesbian|bisexual|bi|pansexual|asexual|aroace|aro-ace|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|friends|men|women|guys|girls|people|porn|marriage|ally|rights|shooter|a|content|stuff|scene|community|culture|sex)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", r"^\W*(?:[a-z]+ ){0,2}?(gay|bi|bisexual|straight|str8|lesbian|pansexual) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|husband|dad|daddy|bear|bro|boy|woman|man|male|female|twink|femboy|bottom|top|chub|stud|dude|couple|sub|dom|jock|cub|bull|babe|teen|queen|slut|sissy|boi|bbw|milf|lady|gal|mom|vers|otter)\b(?! (?:friend|friends|porn)\b)", group(ORIENTATIONS), TAGGED),
    said("sexual_orientation", r"as(?<!\was) an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer)\b(?! (?:up|out|forward|away|from|to|into|after|back|down|ahead|through|off|on|in|at|for|with|couple|people|community|friend|friends|ally|rights|men|women|guys|porn|bar|club|marriage|man|woman|guy|girl|person|male|female|dude|boy)\b)", group(ORIENTATIONS)),
    said("sexual_orientation", r"(?:^|\n)\W*(?:\d{2}\s*(?:[mf]|yo|y/o)?|[mf]\s?\d{2}|[\(\[]\d{2}[\)\]])[\s,]+(?:(?!(?:i|was|not|never|used)\b)[a-z]+[\s,]+){0,2}?(straight|str8|bi|bisexual|gay|lesbian|hetero|pan)\b(?! (?:men|women|guys|girls|porn|couple|friend))|(?:^|[,|/] ?)(str8|hetero|bi|straight)\s*(?:[,|/]|here\b)", lambda match: ORIENTATIONS[match.group(1) or match.group(2)], TAGGED),
    said("sexual_orientation", r"as(?<!\was) an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude|couple|boy)\b", group(ORIENTATIONS)),
    said("sexual_orientation", r"(?:^|[.!?,;] *)(gay|lesbian|bi|bisexual|straight|pansexual) (?:\w+ )?(?:male|female|guy|girl|man|woman|dude|couple) here\b", group(ORIENTATIONS)),
    said("sexual_orientation", r"bi(?<![\w-]bi)[- ]?curious\b", lambda match: "queer, unspecified" if CONFESSED.search(match.string, max(0, match.start() - 30), match.start()) or (not re.match(r"[^\s,(|/]", match.string[match.start() - 1:match.start()]) and CURIOUSLY.match(match.string, match.end())) else None, SELF_HEDGE),
]

LESBIAN_FEMALE = [rule("gender", r"lesbian", lambda match: "female" if any(stated(found) == "lesbian" for _, pattern, stated, _ in SEXUAL_ORIENTATION for found in pattern.finditer(match.string)) else None, TAGGED)]

ETHNICITY = [
    said("ethnicity", rf"{LISTED},\s*(?:and\s+)?({'|'.join(map(re.escape, ETHNICITIES))})(?=\s*(?:[,.!;&/)]|and\b|$))", listed(group(ETHNICITIES)), SELF_HEDGE),
    said("ethnicity", rf"{IM} (?:an? (?:(?!(?:non|not|honorary|fan|huge|big)\b)\w+ )?|half |half-|also |\d{{2}},? )?({'|'.join(map(re.escape, ETHNICITIES))})(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself|lady))?(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family)\b)", group(ETHNICITIES)),
    said("ethnicity", rf"(?=as )(?<!\bsuch )(?<!\bsame )(?<!\bdressed )(?<!\btreated )(?<!\bseen )\bas an? (?:(?!(?:non|not|honorary)\b)\w+ )?({'|'.join(map(re.escape, ETHNICITIES))})\b(?! (?:people|folks|community|communities|culture|food|neighborhood|area|country|family|friend|friends|men|women|guys|girls|kids|person's)\b)(?!'s)", group(ETHNICITIES)),
    said("ethnicity", rf"(?:i(?<!\wi)(?:'m|m| am)|a(?<!\wa)s) (?:just |also |only )?(?:a |an )?(?:(?!\w+ing\b){FREE}|an? ){{0,4}}?({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|lady|mom|dad|mother|father|kid|teen|boy|bro|immigrant|canadian|british|australian|bottom|top|chub|bear|daddy|stud|bull|twink|femboy)\b", group(ETHNICITIES), SELF_HEDGE),
    said("ethnicity", rf"\b(?:i'm|im|i am|as an?|a)? ?half[- ]({'|'.join(map(re.escape, ETHNICITIES))})[,/ ]+(?:and )?half[- ]({'|'.join(map(re.escape, ETHNICITIES))})\b|\bethnically (?:{'|'.join(map(re.escape, ETHNICITIES))}) ?(?:/|and|&) ?(?:{'|'.join(map(re.escape, ETHNICITIES))})\b", lambda match: "mixed"),
    said("ethnicity", r"\bwe (black|white|asian|latina|latino|hispanic|indian|desi|arab|indigenous|native) (?:women|men|people|folks|girls|guys)\b|\bsoy (latino|latina|mexicano|mexicana|negro|negra|blanco|blanca)\b|\b(white) ?boi\b|\b(?:i'm|im|i am|i m) (?:(?!(?:not|so|very|too|pretty|a|an|the|all|just|also|still|really|more|less|half|like|fully|mostly|part)\b)[a-z]+ )?(black|white|asian|latina|latino|hispanic|mixed|biracial|desi)(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|and \w+ing)\b)",
         lambda match: (lambda word: {"mexicano": "hispanic or latino", "mexicana": "hispanic or latino", "negro": "black", "negra": "black", "blanco": "white", "blanca": "white", "native": "indigenous"}.get(word) or ETHNICITIES[word])(next(filter(None, match.groups()))), SELF_HEDGE),
    said("ethnicity", rf"^\W*(?:[a-z]+ ){{0,2}}?({'|'.join(map(re.escape, ETHNICITIES))}) (?:[a-z]+ ){{0,2}}?(?:girl|guy|woman|man|boy|boi|bro|lady|gal|chick|dude|male|female|milf|mom|wife|dad|daddy|bottom|top|sub|dom|twink|femboy|bull|stud|slut|babe|teen|queen|king|bbw|cuck|couple|body|bod|ass|booty|butt|tits|boobs)\b(?! (?:\w+ )?(?:cock|dick))(?=(?: \w+)? (?:here|looking|seeking|wanting|needing|for|ready|with|needs|wants|available)\b|\s*[,.!]|\s*$)", group(ETHNICITIES), TAGGED),
]

HEIGHT = [
    said("height", rf"{LISTED}(?<=[\s,/])([4-7])\s?(?:'|ft|foot|feet)\s?(?:and )?(\d{{1,2}})?\s?(?:\"|''|in\b|inches)?(?!\d|\.\d|')(?! (?:away|from|deep|long|wide)\b)",
         listed(lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None)),
    said("height", r"height(?<!\wheight)\s*[:=-]\s*(?:(1[4-9]\d|2[01]\d)\s?cm|([4-7])\s?(?:'|ft|foot|feet)\s?(\d{1,2})?)|(?:f(?<!\wf)or me|m(?<!\wm)e|i(?<!\wi)'m|i(?<!\wi)m|i(?<!\wi) am) at ([4-7])\s?(?:'|ft)\s?(\d{1,2})?(?!\d|\.\d)|([4-7])(?<![\w.][4-7])\s?,\s?(\d{1,2})\s?(?:\"|”|'')?\s*tall\b",
         lambda match: match.group(1) or (lambda feet, inches: str(round((int(feet) * 12 + int(inches or 0)) * 2.54)) if int(inches or 0) < 12 else None)(match.group(2) or match.group(4) or match.group(6), match.group(3) or match.group(5) or match.group(7))),
    said("height", rf"{IM} (?:only |about |around |almost |nearly |barely |like |just |a )?([4-7])\s*(?:'|ft|foot|feet)\s*(?:and )?(\d{{1,2}})?\s*(?:\"|''|in\b|inches)?(?!\d|\.\d)(?! (?:away|from|deep|long|wide)\b)",
         lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None),
    said("height", rf"{IM} (?:only |about |around |almost |nearly |barely |like |just )?(1[4-9]\d|2[01]\d)\s*cm\b|{IM} (?:only |about |around |almost |nearly |barely |like |just )?1[.,]([4-9]\d)\s?m\b", lambda match: match.group(1) or "1" + match.group(2)),
    said("height", r"as(?<!\was)(?<!\bsuch as) an? ([4-7])\s?(?:'|ft|foot)\s?(\d{1,2})?\s?(?:\"|''|in\b)?\s?(?:\w+ )?(?:man|woman|guy|girl|male|female|dude|lady|person|boy|bro)\b|(?:and|but)(?<!\wand)(?<!\wbut) am ([4-7])'\s?(\d{1,2})?(?![\d.'])", lambda match: (lambda feet, inches: str(round((int(feet) * 12 + int(inches or 0)) * 2.54)) if int(inches or 0) < 12 else None)(match.group(1) or match.group(3), match.group(2) or match.group(4))),
]

LOAD = re.compile(r"(?:\b(?:under|over|than|lose|losing|lost|gain|gained|gaining|by|of|an?|the|another|extra|to|from|bench|squat|lift|lifting|carry|carrying)\s*|(?<!['’\"”])(?<!['’\"”]\d)(?<![a-z]\d)[-–/\d]\s*)\W?$")

WEIGHT = [
    said("weight", rf"\bi (?:weigh|weight|'m at|am at|'m currently at|'m currently)\s+(?:about |around |roughly |almost |like |just under |over |under )?(\d{{2,3}}(?:\.\d)?)\s*(lbs?|pounds|kg|kgs|kilos)\b|{IM} (?:an? )?(\d{{2,3}})\s*(lbs?|pounds|kg|kgs)\b",
         lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))))(float(match.group(1) or match.group(3)), match.group(2) or match.group(4))),
    said("weight", r"(?:^|[\s,|/(])(\d{2,3})(?:ish)?\s?(lbs?|pounds|kg|kgs|kilos?)\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain|gained|more|less|bag|bags|box|dumbbells?|plates?|bench|squat|deadlift|worth))", personal(alone(lambda match: None if LOAD.search(match.string, max(0, match.start() - 16), match.start() + 1) or re.match(r"\s*(?:-+>|/)", match.string[match.end():]) else (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))) if 35 <= amount * (1 if unit.startswith("k") else .4536) <= 250 else None)(float(match.group(1)), match.group(2)))), SELF_HEDGE),
    said("weight", r"[4-7](?<![\w.$'][4-7])\s?(?:'|ft)\s?\d{1,2}(?:\"|”|'')?\s*[,/]?\s+(\d{3})(?:\s?(?:lbs?|pounds))?(?![\w.%/'\"”])", alone(lambda match: str(round(int(match.group(1)) * .4536)) if int(match.group(1)) * .4536 <= 250 and not WANTING.search(SENTENCE.split(match.string[max(0, match.start() - 80):match.start()])[-1]) else None), SELF_HEDGE),
]

BODY_TYPE = [
    said("body_type", rf"{LISTED},\s*(?:and\s+)?(?:very |pretty |quite |kinda |kind of |a bit |a little |fairly |super )?({'|'.join(map(re.escape, sorted({*BODIES, *SHAPES}, key=len, reverse=True)))})(?=\s*(?:[,.!;&/)]|and\b|but\b|$|\n))", listed(lambda match: BODIES.get(match.group(1)) or SHAPES[match.group(1)]), SELF_HEDGE),
    said("body_type", r"^\W*(?:[a-z]+ )?(chubby|chub|curvy|thick|thicc|petite|slim|skinny|fat|bbw|ssbbw|athletic|muscular|fit|stocky|toned|slender|tiny|ripped|jacked|buff|lean|beefy|chunky) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|milf|mom|dad|daddy|bear|bro|boy|woman|man|hotwife|latina|latino|twink|femboy|bottom|top|sub|dom|jock|cub|stud|bull|babe|teen|queen|slut|sissy|boi|baddie|mommy|lady|gal|chick|dude)\b(?! (?:\w+ )?(?:cock|dick))", lambda match: BODIES.get(match.group(1)) or SHAPES[match.group(1)], TAGGED),
    said("body_type", r"\b(?:an? )?(slim|slender|skinny|athletic|muscular|fit|chubby|chub|chunky|curvy|thick|thicc|petite|bbw|ssbbw|stocky|beefy|ripped|toned|fat|tiny|average|obese|overweight) (?:\w+ )?(?:girl|guy|woman|man|lady|boy|dude|bro|wife|mom|milf|dad|daddy|bear|hotwife|chick|gal|teen|mommy|momma|babe|slut|bottom|twink|femboy)(?: like me\b| here\b)", lambda match: BODIES.get(match.group(1)) or SHAPES[match.group(1)], TAGGED),
    said("body_type", r"\bmy (?:\w+ )?curves\b", lambda match: "curvy", SELF_HEDGE),
    said("body_type", rf"{IM} (?:(?:very|really|pretty|quite|a bit|kinda|kind of|super|too|so|a little|slightly|fairly|relatively|somewhat|reasonably|naturally|extremely|rather|extra|also|still|now|currently|a|an) )*(?:(?!average\b)({'|'.join(map(re.escape, sorted({*BODIES, *SHAPES}, key=len, reverse=True)))})|(average)(?= (?:build|body|bod|size|weight|frame|shape)\b|\s*[,.!;)]|$| and\b))\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|mood|chance|mess|game|difference|problem|issue|plus|day|week|month|year|joe|student|height|person|amount|number|smoker|drinker|sleeper|user|eater|lifter|hitter|metal)s?\b)", lambda match: BODIES.get(match.group(1) or match.group(2)) or SHAPES[match.group(1)]),
    said("body_type", r"(?:^|[\s,|/])(bbw|curvy|petite|chubby|athletic|muscular|slim)\s*(?:f|female|woman|girl|m|male|guy|here)\b", mine(lambda match: None if desired(match.string, match.start(1)) else BODIES[match.group(1)]), SELF_HEDGE),
    said("body_type", rf"\b(?:{I}|bod|body|build|frame) (?:\w+ )?on the (slim|slimmer|thin|thinner|skinny|skinnier|lean|leaner|heavy|heavier|big|bigger|large|larger|chubby|chubbier|curvy|curvier|thick|thicker) side\b", lambda match: {"slim": "slim", "slimmer": "slim", "thin": "slim", "thinner": "slim", "skinny": "slim", "skinnier": "slim", "lean": "slim", "leaner": "slim", "curvy": "curvy", "curvier": "curvy", "thick": "curvy", "thicker": "curvy"}.get(match.group(1), "chubby or overweight")),
    said("body_type", r"\b(?:my|this|with a|with my) (?:\w+ )?(curvy|chubby|thick|thicc|petite|fat|skinny|slim|athletic|muscular|fit|tiny|bbw|plus[- ]size|average|toned|slender|dad|chunky|stocky|ripped|jacked|buff|lean|beefy|muscled|shredded|thin|heavy|overweight) (?:body|build|frame|figure|bod|self)\b|\b(slim|athletic|average|slender|muscular|stocky|heavy|thin|fit|curvy|chubby|thick|thicc|petite|tiny)(?: and (?:fit|toned|athletic|slim))? build\b|\bbuilt like an hourglass\b|\bextra (thicc|thick)\b",
         lambda match: (lambda word: "curvy" if word in ("thicc", "thick", None) else {"tiny": "very thin", "dad": "average", "stocky": "chubby or overweight", "heavy": "chubby or overweight"}.get(word, BODIES.get(word) or SHAPES.get(word)))(match.group(1) or match.group(2) or match.group(3)), TAGGED),
    said("body_type", r"\b(?:my|this|these) (?:\w+ ){0,2}?(chubby|chunky|fat|curvy|thick|thicc|skinny|slim|petite|muscular|toned|athletic),? (?:(?:and |, ?)?\w+ ){0,2}?(?:ass|booty|butt|belly|tummy|thighs|tits|boobs|bod|body|self|curves|figure|frame|pussy)\b", lambda match: {"chunky": "chubby or overweight", "fat": "chubby or overweight", "thick": "curvy", "thicc": "curvy", "skinny": "very thin", "toned": "athletic or muscular"}.get(match.group(1)) or BODIES[match.group(1)], TAGGED),
]

HAIR_COLOR = [
    said("hair_color", r"\b(?:i'?ve been|been|being|i went|went|i'm going|im going|going) bald\b", lambda match: "bald"),
    said("hair_color", r"\bmy (?:(?:long|short|messy|lovely|beautiful|natural|naturally|thick|thin|fine|dark|light|bright|curly|wavy|straight|dirty|strawberry|platinum|golden|honey|sandy|dyed|bleached|new|current|real|own|frizzy|greasy|shoulder[- ]length|graying|greying|medium) ){0,3}(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b|\bi have (?:long |short |curly |natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)]),
    said("hair_color", rf"{IM} (?:a |an |naturally |going )?(blonde|blond|brunette|redhead|a redhead|ginger|a ginger|bald|balding)\b(?! (?:joke|moment|people)\b)", group(HAIRS)),
    said("hair_color", r"\b(?:i'm|im|i am|i m) (?:still |also |just |actually |really |naturally )?(?:a |an )?(?:(?!not\b|never\b|no\b)\w+ ){0,2}?(red ?head|redhead|ginger|blonde|blond|brunette)\b|(?:^|[\s,|/(])(red ?head|redhead|brunette)\b(?= (?:\w+ )?(?:here|bitch|boy|girl|guy|babe|milf|wife|mom|looking|f\b|m\b))|\b(?:i (?:actually |also |still |now )?have|i've got|my|with) (?:long |short |thick |thin |curly |straight |wavy |natural |graying |greying |dark |light |bright )*(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green)(?: buzz cut| curly| wavy)? hair\b",
         alone(lambda match: HAIRS[(match.group(1) or match.group(2) or match.group(3)).replace(" ", "")]), SELF_HEDGE),
]

RULES = [*AGE, *GENDER, *SEXUAL_ORIENTATION, *LESBIAN_FEMALE, *ETHNICITY, *HEIGHT, *WEIGHT, *BODY_TYPE, *HAIR_COLOR]
