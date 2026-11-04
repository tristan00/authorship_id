import re

from .common import BOT_TEXT, FOR, I, SELF_HEDGE, TAG, TAGGED, group, rule
from .config import YEAR

DISTANCE = re.compile(r"\s*(?:away|ago|long|deep|high|wide|tall|run|race|views|subs|followers|people|users|members|miles)")
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
GENDER_WORDS = r"(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|girl|female|lady|gal|chick)"
ADJECTIVES = (r"(?:(?:\d{2}[- ]?(?:years?|yrs?|y/?o)[- ]?(?:old )?|single|married|straight|gay|bi|bisexual|white|black|asian|latino|latina|hispanic|indian|young|old|older|middle[- ]aged|"
              r"tall|short|fat|chubby|skinny|fit|average|normal|regular|grown|cis|cisgender|divorced|disabled|autistic|working|stay[- ]at[- ]home|new|first[- ]time|"
              r"american|british|canadian|australian|christian|muslim|jewish|catholic|retired|lonely|horny|shy|curvy|petite|busy|proud) ){0,3}")
ORIENTATIONS = {"gay": "gay", "lesbian": "lesbian", "bisexual": "bisexual", "bi": "bisexual", "pansexual": "pansexual", "pan": "pansexual", "asexual": "asexual", "ace": "asexual",
                "queer": "queer, unspecified", "straight": "straight", "heterosexual": "straight", "hetero": "straight", "homosexual": "gay"}
ETHNICITIES = {"white": "white", "caucasian": "white", "black": "black", "african american": "black", "asian": "east asian", "east asian": "east asian", "chinese": "east asian",
               "korean": "east asian", "japanese": "east asian", "taiwanese": "east asian", "south asian": "south asian", "indian": "south asian", "desi": "south asian",
               "pakistani": "south asian", "bangladeshi": "south asian", "southeast asian": "southeast asian", "filipino": "southeast asian", "filipina": "southeast asian",
               "vietnamese": "southeast asian", "thai": "southeast asian", "latino": "hispanic or latino", "latina": "hispanic or latino", "latinx": "hispanic or latino",
               "hispanic": "hispanic or latino", "mexican": "hispanic or latino", "arab": "middle eastern or north african", "middle eastern": "middle eastern or north african",
               "persian": "middle eastern or north african", "native american": "indigenous", "indigenous": "indigenous", "aboriginal": "indigenous",
               "pacific islander": "pacific islander", "mixed": "mixed", "mixed race": "mixed", "biracial": "mixed", "multiracial": "mixed"}
BODIES = {"skinny": "very thin", "very thin": "very thin", "underweight": "very thin", "thin": "slim", "slim": "slim", "slender": "slim", "lean": "slim", "athletic": "athletic or muscular",
          "muscular": "athletic or muscular", "fit": "athletic or muscular", "buff": "athletic or muscular", "jacked": "athletic or muscular", "toned": "athletic or muscular",
          "average": "average", "average build": "average", "curvy": "curvy", "thick": "curvy", "chubby": "chubby or overweight", "overweight": "chubby or overweight",
          "fat": "chubby or overweight", "heavy": "chubby or overweight", "bbw": "chubby or overweight", "plus size": "chubby or overweight", "plus-size": "chubby or overweight",
          "big": "chubby or overweight", "obese": "obese", "morbidly obese": "obese", "petite": "slim"}
HAIRS = {"blonde": "blonde", "blond": "blonde", "brown": "brown", "brunette": "brown", "black": "black", "red": "red", "ginger": "red", "auburn": "red", "a redhead": "red",
         "redhead": "red", "a ginger": "red", "grey": "grey or white", "gray": "grey or white", "white": "grey or white", "silver": "grey or white", "pink": "dyed unusual color",
         "blue": "dyed unusual color", "purple": "dyed unusual color", "green": "dyed unusual color", "bald": "bald", "balding": "bald", "a blonde": "blonde"}
START = rf"^\W{{0,3}}(\d{{2}})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)"
SHAPES = {"thicc": "curvy", "chub": "chubby or overweight", "chunky": "chubby or overweight", "dadbod": "average", "dad bod": "average", "beefy": "athletic or muscular", "stocky": "chubby or overweight",
          "hourglass": "curvy", "rellenita": "chubby or overweight", "gordita": "chubby or overweight", "flaca": "very thin", "tiny": "very thin", "ripped": "athletic or muscular", "toned": "athletic or muscular"}
DESCRIBED = re.compile(r"(?:^|[\s,.!/(|+-])(thick|thicc|curvy|chubby|chub|chunky|bbw|slim|slender|skinny|athletic|fit|muscular|fat|overweight|obese|petite|tiny|average|dadbod|dad bod|stocky|beefy|ripped|toned|hourglass|rellenita|gordita|flaca|plus[- ]size)"
                       r"(?= (?:build|built|body|frame|figure|shape|and |but |af\b|asf\b|girl|guy|woman|man|bottom|top|bear|daddy|milf|wife|mom|dad|f\b|m\b|here|latina|black|white|asian|blonde|brunette|\d)|[\s,.!/)|]*$|\s*[,/|])")
COUPLE = re.compile(r"(?:nb|[mf])[mf]\s*4|couple")
PARTNERED = re.compile(r"\b(?:my|our) (?:wife|husband|hubby|gf|bf|girlfriend|boyfriend|partner)\b|\bmarried\b|\bhotwife\b|\bcouple\b|\bcuck")
SEEKING = re.compile(r"\blooking for\b|\bseeking\b|\banyone\b|\bhmu\b|\bdm me\b|\bhost(?:ing)?\b|\bwanna\b|\bwant(?:s)? (?:a|to|some)\b|\bneed(?:s)? (?:a|some)\b|\bavailable\b|\bsnap\b|\bkik\b|\btonight\b")


def owned(lowered, start):
    before = lowered[max(0, start - 24):start]
    return bool(SELF.search(before)) or (start < 60 and not OTHERS.search(before))


def tags(text, lowered, found):
    if BOT_TEXT.search(lowered):
        return
    for match in re.finditer(FOR, lowered):
        if owned(lowered, match.start()):
            found.setdefault(("gender", GENDERS[match.group(2)]), match.start())
            if age := match.group(1) or match.group(3):
                found.setdefault(("age", age), match.start())
            tag = lowered[match.start():match.end()]
            if not COUPLE.search(tag) and not PARTNERED.search(lowered) and SEEKING.search(lowered):
                found.setdefault(("relationship_status", "single"), match.start())
            if (pair := re.search(r"([mf])\s*4\s*([mf])(?![a-z])", tag)) and pair.group(1) == pair.group(2):
                found.setdefault(("sexual_orientation", "gay" if pair.group(1) == "m" else "lesbian"), match.start())
    for match in re.finditer(TAG, lowered):
        if match.group(1) and (re.match(rf"\s*{UNITS}", lowered[match.end():]) or DISTANCE.match(lowered, match.end())):
            continue
        age, letter = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
        bracketed = lowered[match.start() - 1:match.start()] in ("(", "[")
        if not (owned(lowered, match.start() - bracketed) or (bracketed and not OTHERS.search(lowered[max(0, match.start() - 25):match.start() - 1]) and match.start() < 60)):
            continue
        found.setdefault(("gender", GENDERS[letter]), match.start())
        found.setdefault(("age", age), match.start())
    if match := re.match(START, lowered):
        found.setdefault(("age", match.group(1)), 0)
    if re.search(FOR, lowered[:120]) or re.search(TAG, lowered[:60]) or re.match(r"\W*(?:i'm|im|i am)\b", lowered):
        for match in DESCRIBED.finditer(lowered[:400]):
            if not OTHERS.search(lowered[max(0, match.start() - 20):match.start()]):
                found.setdefault(("body_type", BODIES.get(match.group(1)) or SHAPES[match.group(1)]), match.start())


def ages(value):
    return value if 13 <= int(value) <= 99 else None


RULES = [
    rule("age", rf"\b{I} (?:only |almost |nearly |just |now |about |turning |currently |a |an )?(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?(?=$|[\s.,!;:)])(?!\s*{UNITS}|\s*(?:and|or|-)\s*\d)", lambda match: ages(match.group(1))),
    rule("age", r"\bas an? (\d{2})[- ]?(?:years?|yr)[- ]?old\b", lambda match: ages(match.group(1))),
    rule("age", r"(?:\bi(?:'ve| have)? |^|[.!?] )(?:just |recently |finally )?turned (\d{2})\b(?! (?:years|minutes|weeks|percent|%))", lambda match: ages(match.group(1))),
    rule("age", r"\bi'?m (?:a |an )?(\d{2})\s?(?:yo|y/o|y\.o\.?|years? old|yr old|year-old)\b", lambda match: ages(match.group(1))),
    rule("age", r"(?:^|[.!?\n] *)(\d{2}) (?:years? old|yo|y/o) (?:here|male|female|guy|girl|man|woman|m|f)\b", lambda match: ages(match.group(1))),
    rule("age", r"\bmy age is (\d{2})\b|\bage\s*[:=]\s*(\d{2})\b", lambda match: ages(match.group(1) or match.group(2))),
    rule("age", r"\bi was born in ((?:19[3-9]\d)|(?:200\d)|(?:201[0-3]))\b", lambda match: str(YEAR - int(match.group(1)))),
    rule("age", rf"^\W{{0,2}}[\[\(]?(\d{{2}})[\]\)]?(?=[\s,.!:\]]|$)(?!\s*{UNITS}|[.,:/]\d|\s*[-–/x+]\s*\d|\s*(?:and|or|to|-)\s+\d|\.\s*\d|\s+(?:of|out|times|people|years? ago|is|was|more|minutes|seconds|percent|k)\b)", lambda match: ages(match.group(1)), TAGGED),
    rule("age", r"\b(?:i|me|i'm|im|i am|myself|ich)\b[^.!?\n()]{0,25}\((\d{2})\)", lambda match: ages(match.group(1)), SELF_HEDGE),
    rule("age", r"(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(?:^|(?<=[\s(\[,]))(\d{2})\s?(?:yo|y/o|y\.o\.?|yr old|year old|years old|yrs old)\b(?! (?:son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat|car|house|man|woman|guy|male|female|friend|wife|husband)\b)", lambda match: ages(match.group(1)), SELF_HEDGE),
    rule("age", r"\b(?:tengo|tenho|j'ai) (\d{2})(?: (?:años|anos|ans))?\b|\bya[sş] ?:? ?(\d{2})\b|\b(\d{2}) jahre alt\b|\bich bin (\d{2})\b", lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("age", r"(?:^\W*|\b(?:i|me|ich|myself|moi|yo)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*(\d{2})\s*[\]\)]|[\[\(]\s*(\d{2})\s*[,/]\s*([mfw])\s*[\]\)])", lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    rule("gender", r"(?:^\W*|\b(?:i|me|ich|myself|moi|yo)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*\d{2}\s*[\]\)]|[\[\(]\s*\d{2}\s*[,/]\s*([mfw])\s*[\]\)])", lambda match: {"m": "male", "f": "female", "w": "female"}[match.group(1) or match.group(2)], TAGGED),
    rule("gender", rf"\b{I} (?:an? |the |also an? |just an? |only an? |still an? |actually an? |literally an? )?{ADJECTIVES}{GENDER_WORDS}\b(?! (?:friend|friends|of|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff)\b)(?!'s)", group(GENDERS)),
    rule("gender", rf"(?<!\byou )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bme )\bas an? (?:fully )?{ADJECTIVES}{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    rule("gender", r"\bmy (?:\w+ ){0,3}?(cock|dick|penis|balls|bbc|bwc|foreskin|beard)\b|\bmy (?:\w+ ){0,3}?(pussy|boobs|tits|breasts|vagina|clit|period|cervix|uterus|bra|nipples)\b",
         lambda match: "male" if match.group(1) else "female", SELF_HEDGE),
    rule("gender", r"(?:^|[\s,(\]])(milf|hotwife|daddy|dilf|bull|twink|femboy|sissy|bimbo)(?: here| looking| seeking| loves| needs| wants| for| 4\b)", group({"milf": "female", "hotwife": "female", "bimbo": "female", "daddy": "male", "dilf": "male", "bull": "male", "twink": "male", "femboy": "male", "sissy": "male"}), SELF_HEDGE),
    rule("gender", rf"(?:^|[.!?,;] *)(?:a )?{ADJECTIVES}{GENDER_WORDS} here\b", group(GENDERS)),
    rule("gender", rf"\b{I} (?:a |an )?(non-binary|nonbinary|enby|genderfluid|agender|genderqueer|trans woman|transwoman|trans girl|trans man|transman|trans guy|mtf|ftm|transgender|trans)\b(?! (?:people|rights|friend|kids))", group(GENDERS)),
    rule("gender", r"\b(she|he|they)\s?/\s?(?:her|hers|him|his|them|they)\b", group({"she": "female", "he": "male", "they": "non-binary"}), SELF_HEDGE),
    rule("gender", r"(?:^|(?<=[\s,(\]]))[\(\[]\s*([mf])\s*[\)\]]", group(GENDERS), TAGGED),
    rule("gender", r"\b(?:makes|made|got|gets|getting) me (?:so )?(hard|wet)\b|\b(?:i'm|im|i am) (?:so |already |rock )?(hard|wet|dripping) (?:for|thinking|right now)\b|\bi'?m your (girl|boy|man|woman|princess|slut|goddess)\b",
         lambda match: {"hard": "male", "wet": "female", "dripping": "female", "girl": "female", "princess": "female", "slut": "female", "goddess": "female", "boy": "male", "man": "male", "woman": "female"}[next(filter(None, match.groups()))], SELF_HEDGE),
    rule("gender", r"(?<![\w'])[\(\[]?(female|male|guy|girl|woman|man|dude|lady|f|m)(?: in(?:my |her |his )?(?:early |mid |late )?\d0'?s)? here\b|\bfellow (?:\w+ )?(dude|guy|woman|man|lady|girl|mom|dad) here\b",
         lambda match: GENDERS[match.group(1) or match.group(2)], TAGGED),
    rule("gender", rf"^\W*\d{{2}}\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy)\b",
         lambda match: {"queen": "female", "king": "male", "bbw": "female", "milf": "female", "stud": "male", "bull": "male", "twink": "male", "femboy": "male", "daddy": "male"}.get(match.group(1)) or GENDERS[match.group(1)], TAGGED),
    rule("gender", r"(?:^|[\s,(\[])(t4[mfat]|ts girl|tgirl|trans girl|transgirl|mtf|ftm|trans guy|transman|transwoman)\b|^\W*(agender|non-?binary|enby|genderfluid|genderqueer)\b|\b(domme|dominatrix|mistress)\b(?= (?:here|looking|seeking|available|for)\b)",
         lambda match: GENDERS.get(match.group(1), "trans woman") if match.group(1) and not match.group(1).startswith("t4") else "trans woman" if match.group(1) else GENDERS[match.group(2).replace("nonbinary", "non-binary")] if match.group(2) else "female", TAGGED),
    rule("gender", r"(?:^|[\s.!?])([mf])\s?(\d{2})\W*$|(?:^|[\s.!?])(\d{2})(?:\s?(f)| (m))\W*$", lambda match: GENDERS[match.group(1) or match.group(4) or match.group(5)], TAGGED),
    rule("age", r"(?:^|[\s.!?])([mf])\s?(\d{2})\W*$|(?:^|[\s.!?])(\d{2})(?:\s?f| m)\W*$", lambda match: ages(match.group(2) or match.group(3)), TAGGED),
    rule("age", rf"^\W*(\d{{2}})\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(?:male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bottom|top|sub|dom|cuck|virgin|couple)\b", lambda match: ages(match.group(1)), TAGGED),
    rule("gender", r"\b(?:soy|sou) (?:un |una |uma |um )?(hombre|mujer|chica|chico|homem|mulher)\b|\bje suis une? (homme|femme)\b|\bich bin (?:ein |eine )?(mann|frau)\b",
         lambda match: {"hombre": "male", "chico": "male", "homem": "male", "homme": "male", "mann": "male"}.get(next(filter(None, match.groups())), "female")),
    rule("sexual_orientation", rf"\b{I} (?:a |an )?(?:(?:\d{{2}}[- ]?(?:years?|yr)[- ]old|cis|single|married|black|white|asian|trans|young|old|older|proud|openly|also|both|totally|fully) )*(gay|lesbian|bisexual|bi|pansexual|asexual|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|men|women|guys|people|porn|marriage|ally|rights|shooter|a)\b)", group(ORIENTATIONS)),
    rule("sexual_orientation", r"\bas an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude|couple|boy)\b", group(ORIENTATIONS)),
    rule("sexual_orientation", r"(?:^|[.!?,;] *)(gay|lesbian|bi|bisexual|straight|pansexual) (?:\w+ )?(?:male|female|guy|girl|man|woman|dude|couple) here\b", group(ORIENTATIONS)),
    rule("ethnicity", rf"\b{I} (?:a |an |half |half-|also )?({'|'.join(map(re.escape, ETHNICITIES))})(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself|lady))?(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family)\b)", group(ETHNICITIES)),
    rule("ethnicity", rf"\bas an? ({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|mom|dad|mother|father|lady|kid)\b", group(ETHNICITIES)),
    rule("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just |a )?([4-7])\s*(?:'|ft|foot|feet)\s*(?:and )?(\d{{1,2}})?\s*(?:\"|''|in\b|inches)?(?![\d.])(?! (?:away|from|deep|long|wide)\b)",
         lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None),
    rule("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just )?(1[4-9]\d|2[01]\d)\s*cm\b", lambda match: match.group(1)),
    rule("weight", rf"\bi (?:weigh|weight|'m at|am at|'m currently at|'m currently)\s+(?:about |around |roughly |almost |like |just under |over |under )?(\d{{2,3}}(?:\.\d)?)\s*(lbs?|pounds|kg|kgs|kilos)\b|\b{I} (\d{{2,3}})\s*(lbs?|pounds|kg|kgs)\b",
         lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))))(float(match.group(1) or match.group(3)), match.group(2) or match.group(4))),
    rule("body_type", rf"\b{I} (?:very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |a |an )?({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman)\b)", group(BODIES)),
    rule("body_type", r"(?:^|[\s,|/])(bbw|curvy|petite|chubby|athletic|muscular|slim)\s*(?:f|female|woman|girl|m|male|guy|here)\b", group(BODIES), SELF_HEDGE),
    rule("hair_color", r"\bmy (?:natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b|\bi have (?:long |short |curly |natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)]),
    rule("hair_color", rf"\b{I} (?:a |an |naturally |going )?(blonde|blond|brunette|redhead|a redhead|ginger|a ginger|bald|balding)\b(?! (?:joke|moment|people)\b)", group(HAIRS)),
    rule("hair_color", r"(?:^|[\s,|/(])(blonde?|brunette|redhead|ginger)\s*(?:f|female|woman|girl|m|male|guy|here|milf|babe|beauty|bombshell|teen)\b|\bwith (?:long |short |curly |dark |light |natural |highlighted |dyed )*(blonde?|brown|black|red|ginger|auburn|grey|gray|silver|pink|blue|purple|green)(?: highlighted)? hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("body_type", rf"\b{I} (?:a |an |very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |naturally |extra |also )*({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman|mood|chance|mess|game|difference|problem|issue|plus|day|week|month|year)\b)", group(BODIES), SELF_HEDGE),
    rule("body_type", r"\b(?:my|this|with a|with my) (?:\w+ )?(curvy|chubby|thick|thicc|petite|fat|skinny|slim|athletic|muscular|fit|tiny|bbw|plus[- ]size|average|toned|slender|dad) (?:body|build|frame|figure|bod|self)\b|\b(slim|athletic|average|slender|muscular|stocky|heavy|thin|fit|curvy|chubby|thick|thicc|petite|tiny)(?: and (?:fit|toned|athletic|slim))? build\b|\bbuilt like an hourglass\b|\bextra (thicc|thick)\b",
         lambda match: (lambda word: "curvy" if word in ("thicc", "thick", None) else {"tiny": "very thin", "dad": "average", "stocky": "chubby or overweight", "heavy": "chubby or overweight"}.get(word, BODIES.get(word)))(match.group(1) or match.group(2) or match.group(3)), SELF_HEDGE),
    rule("height", r"(?:^|[\s,|/(])([4-7])\s?(?:'|’|ft)\s?(\d{1,2})?\s?(?:\"|”|''|in\b)?(?=\s*[,|/]?\s*(?:\d{2,3}\s?(?:lbs?|kg|pounds)|tall|and\b|[,|/]|$))", lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None, SELF_HEDGE),
    rule("weight", r"(?:^|[\s,|/(])(\d{2,3})(?:ish)?\s?(lbs?|pounds|kg|kgs)\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain|gained|more|less|bag|bags|box|dumbbells?|plates?|bench|squat|deadlift))", lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))) if 35 <= amount * (1 if unit.startswith("k") else .4536) <= 250 else None)(float(match.group(1)), match.group(2)), SELF_HEDGE),
    rule("ethnicity", rf"(?:^|[\s,(\]])({'|'.join(map(re.escape, ETHNICITIES))}) (?:guy|girl|male|female|man|woman|dude|queen|king|couple|bottom|top|daddy|milf|bbw|twink|stud|bull|wife|hubby|baddie|boy|lady|mom|dad|chick|babe|beauty|femboy|sub|dom)\b(?= (?:here|looking|seeking|for|with|in|4|from|wants|needs|who|ready)\b)", group(ETHNICITIES), SELF_HEDGE),
    rule("ethnicity", rf"\b(?:i'm|im|i am|as) (?:a |an )?(?:proud |young |old |single |married |tall |short |\d{{2}}[- ]?(?:years?[- ]old|yo|y/o)[- ]?)?({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|lady|mom|dad|mother|father|kid|teen|boy|immigrant|canadian|british|australian)\b", group(ETHNICITIES), SELF_HEDGE),
    rule("hair_color", r"\b(?:i'm|im|i am|i m) (?:a |an )?(?:\w+ )?(red ?head|redhead|ginger|blonde|blond|brunette)\b|(?:^|[\s,|/(])(red ?head|redhead|brunette)\b(?= (?:\w+ )?(?:here|bitch|boy|girl|guy|babe|milf|wife|mom|looking|f\b|m\b))|\b(?:i have|i've got|my|with) (?:long |short |thick |thin |curly |straight |wavy |natural |graying |greying |dark |light |bright )*(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green)(?: buzz cut| curly| wavy)? hair\b",
         lambda match: HAIRS.get((match.group(1) or match.group(2) or match.group(3)).replace(" ", "")) or "red", SELF_HEDGE),
    rule("ethnicity", rf"(?:^|[\s,(\]])((?:spicy |hot |sexy |thick |young |cute |mature |shy )?(?:latina|latino|black|white|asian|indian|desi|arab|ebony|mixed)) (?:mami|papi|queen|king|domme|dom|sub|bottom|top|bull|stud|baddie|goddess|princess|daddy|milf|bbw|twink|boy|girl|guy|man|woman|male|female|couple|wife|hubby)\b",
         lambda match: ETHNICITIES.get(match.group(1).split()[-1]) or ("black" if match.group(1).split()[-1] == "ebony" else None), SELF_HEDGE),
    rule("ethnicity", r"\bwe (black|white|asian|latina|latino|hispanic|indian|desi|arab|indigenous|native) (?:women|men|people|folks|girls|guys)\b|\bsoy (latino|latina|mexicano|mexicana|negro|negra|blanco|blanca)\b|\bwhite ?boi\b|\b(?:i'm|im|i am|i m) (black|white|asian|latina|latino|hispanic|mixed|biracial|desi)(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|and \w+ing)\b)",
         lambda match: (lambda word: {"mexicano": "hispanic or latino", "mexicana": "hispanic or latino", "negro": "black", "negra": "black", "blanco": "white", "blanca": "white", "native": "indigenous"}.get(word) or ETHNICITIES.get(word) or "white")(next(filter(None, match.groups()), "white")), SELF_HEDGE),
]
