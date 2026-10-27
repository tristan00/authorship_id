import json
import re
from pathlib import Path

from .normalize import COUNTRIES, COUNTRY_ALIASES, DEMONYMS, LANGUAGE_ALIASES, LANGUAGES, LOOKUP, STATE_NAMES, number, value

CITIES = set(json.loads(Path(__file__).with_name("cities.json").read_text(encoding="utf-8")))

I = r"(?:i'm|i’m|im|i am)"
A = r"(?:an? )?"
END = r"(?=$|[\s.,!?;:)\]]|'s)"
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
NOT_SAVINGS = r"(?! (?:together|combined|between us|in (?:savings|debt|loans?)))"
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
TAG_SELF = re.compile(r"(?:^|\b(?:i'm|i’m|im|i am|i|me|myself)\b\s*)" + TAG + r"(?![a-z0-9])", re.M)
TAG_ANY = re.compile(r"(?<![\w$.,'’#/])" + TAG + r"(?![a-z0-9'’])")
AGE_START = re.compile(r"^[^\w$€£~]{0,3}(?:an? )?(\d{2})(?![\d.:/%x'’-]|\s*(?:%|percent|years? ago|yrs? ago|minutes|mins?\b|hours|hrs?\b|days|weeks|months|times|seconds|secs?\b|th\b|st\b|nd\b|rd\b|k\b|mph|kph|km|miles|cm|mm|inch|lbs?\b|kg|people|of\b|out\b|to\b|or\b|-\d|\+)|,(?!\s+\D)|(?![mft]\b|nb|[mf]{1,3}4|yo\b|y/o|yrs?\b|ftm|mtf)[a-z]|\s*[?!€\"”]|\s+years?\?|\s*(?:and|&|//?|–)\s*\d|\s+(?:is|in|plus|bucks|dollars|volts?)\b)")
AGE_BRACKET = re.compile(r"[\[\(]\s*(\d{2})\s*[\]\)]")
HEIGHT_ANY = re.compile(r"(?<![\w.$/-])(?<!\ba )(?<!\ban )(?<!over )(?<!under )(?<!than )([4-7]\s*(?:'|’|ft\.?|foot|feet)\s*(?:1[01]|\d)(?:\.\d)?\s*(?:\"|”|''|’’|in\b|inches)?|[4-7]\s*(?:'|’|ft\.?|foot|feet)(?=\s*(?:tall|height|hung|,|\d|with\b|and\b|[.!)|/]|$)))(?![\w'’]|\s*\?)")
WEIGHT_ANY = re.compile(r"(?<![\w.$/-])(\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kgs?|kilos))\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain))")
HEIGHT_METRIC = re.compile(r"(?<![\w.,$])(1[4-9]\d\s?cm|2[0-2]\d\s?cm|1[.,][4-9]\d\s?m\b|1[.,][4-9]\d(?=\s*(?:,|/|\||e\b|y\b|and\b|tall\b|\d{2,3}\s?kgs?\b|$)))")
PEOPLE = re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|they|they're|husband|wife|bf|gf|boyfriend|girlfriend|son|daughter|brother|sister|dad|mom|guy is|girl is|you|you're|ur)\b")
PRIMES = str.maketrans({"‘": "'", "´": "'", "′": "'", "″": '"'})
OTHER = re.compile(r"\b(?:he|she|he's|she's|hes|shes|his|her|they|they're|husband|wife|bf|gf|boyfriend|girlfriend|son|daughter|brother|sister|dad|mom|guy is|girl is|you|you're|ur|lost|from|down|goal|want|wants)\b")
ADJECTIVES = r"(?:straight|gay|bi|white|black|asian|single|married|cis|trans|latino|hispanic|indian|fit|tall|short|chubby|fat|hot|horny|lonely|bored|average|older|young)"
AGE_GENDER = re.compile(r"(?<!\ba )(?<!\ban )(?<!\bmy )(?<!\byour )(?<!\bthe )(?<!\bher )(?<!\bhis )(?<![\w$#.-])(\d{2})\s*(?:yo|y/o|y\.o\.|yrs?|years?[- ]old|yrs?[- ]old)?\s*,?\s*(?:" + ADJECTIVES + r"\s+){0,2}(male|female|man|woman|guy|girl|dude|lady|boy)\b(?! (?:squads?|groups?|teams?|content|raids?|hours?))")
GENDER_AGE = re.compile(r"(?<!\ba )(?<!\bthe )(?<!\bthis )(?<!\bhey )(?<!\bmy )\b(male|female|guy|girl|man|woman|dude|lady),?\s*(\d{2})\b(?!\s*(?:%|years? ago)|[a-z])")
GENDER_BRACKET = re.compile(r"(?:^|(?<=[\s\d]))[\(\[]\s*([mf])\s*[\)\],]")
TAG_FOR = re.compile(r"(?:^|[\s\[\(])(\d{2})?\s*[\[\(]?\s*([mf])\s*4\s*[mfatr]\w*(?:\s*[\]\)]?\s*[-–|:]?\s*(\d{2})\b)?", re.M)

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
            r"\ban? (\d{2}) ?(?:yo|y/o)\b", r"\b(?:tengo|tenho|j'ai|j’ai) (\d{2}) (?:años|anos|ans)\b", r"(?:\bich |^)bin (\d{2})\b",
            r"\bmy age is (\d{2})\b", r"\bi'?m (\d{2}) now\b",
            r"(?:[\[\(]\s*[mf]\s*[\]\),]|(?:^|[\s,])[mf]\s*,)\s*,?\s*(\d{2})\b(?![\d%.,:]|\s*(?:min|mins|minutes|hours|days|%|cm|kg|lbs?|inch|in\b))",
            r"\bage\s*[:=-]\s*(\d{2})\b(?!\s*[-–+]|\s*to\b)",
            r"\b(?:tengo|tenho) (\d{2})\b(?! (?:años de|anos de|meses|dias|días|horas|semanas|mil))",
            r"(?:^|[\s,(\[])(\d{2})\s+(?:milf|married|bi|uk|bbw|wife|mom|dilf|hubby|daddy|cuck|sissy|femboy|twink|bottom|top|bull|virgin|teen|petite|curvy)\b",
            r"\b(?:we're|we are|were|are) both (\d{2})\b"),
    "birth_year": (r"(?:\bi(?:'m| am|’m|m)? (?:was )?|\(|^)born (?:in |on )?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (?:\d{1,2}(?:st|nd|rd|th)?,? )?)?((?:19|20)\d\d|'?[4-9]\d)\b",
                   rf"\b{I} (?:a |an )?((?:19|20)\d\d)\b(?! (?:model|edition|version|car|truck))", r"(?:^|[.!,;(] *)((?:19|20)\d\d) (?:baby|babies|kid|here)\b",
                   r"(?:\bbeing |, |[.!;] )born (?:in |on )?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (?:\d{1,2}(?:st|nd|rd|th)?,? )?)?((?:19|20)\d\d|'?[4-9]\d)\b",
                   r"\b(?:dob|d\.o\.b\.?|date of birth|birth ?year|year of birth|birthdate|birth date|born)\s*[:\-]\s*(?:[\w/ .,-]{0,20}?)((?:19|20)\d\d)\b",
                   r"^\W*((?:19[3-9]|200)\d|201[0-3])\W*$",
                   r"^\W*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?,? |\d{1,2}/\d{1,2}/)((?:19[3-9]|200)\d)\W*$"),
    "generation": (rf"\b{I} {A}(millennial|boomer|baby boomer|gen ?z|gen ?x|zoomer|gen alpha)\b", r"\bas an? (millennial|boomer|gen ?z(?:er)?|gen ?x(?:er)?|zoomer)\b",
                   r"\bfellow (millennial|boomer|gen ?z|gen ?x|zoomer)s?\b",
                   rf"(?:^|[.!,;(] *)(?:[a-z]+ )?({GENERATIONS}) here\b", rf"\b{I} (?:a |an |also a |also an |also |an old |a young |a fellow |an elder |an older |a younger |a late |an early |a geriatric )?({GENERATIONS})\b(?! (?:parents|kids|children|friends|generation))", rf"\(\s*({GENERATIONS}) (?:male|female|man|woman|guy|girl|here|myself|mom|dad)\b", rf"\bwe ({GENERATIONS})\b"),
    "gender": (rf"\b{I} {A}(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who))",
               r"\bas an? (?:\d{2}[- ]?(?:years?|yr)[- ]old )?(?:(?:straight|gay|bi|single|married|white|black|asian|trans|young|old|older|tall|short|fat|average) )*(guy|man|woman|girl|dude|male|female|lady|mom|mother|dad|father|wife|husband)\b",
               rf"\b{I} {A}(non-?binary|nonbinary|enby|trans (?:man|woman|guy|girl))\b",
               r"(?<!\ba )(?<!\bthe )(?<!\bother )(?<!\bthat )(?<!\bthis )\b(male|female|guy|girl|man|woman|dude|lady)\s+here\b",
               r"(?:^|[\]\)\-|:]\s*|\d{2}\s*,?\s*)(?:[a-z]+ ){0,2}?(male|female|guy|girl|man|woman|dude|lady|boy|femboy|milf)\s+(?:here\s+)?(?:looking|seeking|searching|wanting|needing)\b",
               r"\b(?:soy|sou|je suis|ich bin|sono) (?:un |una |uma |um |une |ein |eine )?(hombre|mujer|chica|chico|homem|mulher|homme|femme|mann|frau|ragazzo|ragazza|garota|garoto|menina|menino)\b",
               rf"\b{I} (?:a |an |also a |also an )(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?:autistic|bisexual|curious|bi-curious|bicurious|lesbian|queer|divorced|christian|muslim|catholic|jewish|mexican|indian|latina|latino|black|white|asian|cis|disabled|neurodivergent|married|single|gay|straight|trans|young|old|older|tall|short|fat|chubby|petite|curvy|skinny|fit|grown|normal|regular|average) ){1,3}(guy|man|woman|girl|dude|male|female|lady|boy)\b(?! (?:friend|here|of|who))"),
    "sexual_orientation": (r"(?:^|\W)[\-|/]\s*(straight|gay|bi|bisexual)\s*[\-|/]",
                           r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:(?!not\b|seconds|minutes|hours|days)[a-z]+\W+){0,2}?(straight|gay|bi|bisexual|lesbian)\b(?! (?:up\b|away\b|out\b|to\b|couples?|guys|men|women|porn|friends?|people|bar|club|scene|content|stuff))",
                           r"\b(straight|gay|bi|bisexual|lesbian|pansexual)\s+(?:[a-z]+\s+)?(?:male|female|guy|girl|boy|man|woman|dude|bottom|top|m|f)\s+here\b",
                           rf"\b{I} (?!not\b|never\b|no\b)(?:an? )?(?:\d{{2}}[- ]?(?:years?|yr)[- ]old )?(?:(?!not\b)[a-z]+ ){{0,2}}?(straight|gay|bi|bisexual|lesbian|pansexual|asexual|queer|heterosexual|homosexual)\b(?! (?:friend|couple|bar|club|marriage|people|men|women|guys))",
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
                       rf"(?:lbs|kg|\d['’]\d{{1,2}}\"?|\d{{2}}\s?[mf]?)\s*,\s*({RACES})\s*[,./]"),
    "nationality": (rf"\b{I} (?:also )?{A}(american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swedish|norwegian|danish|finnish|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|chinese|japanese|korean|filipino|filipina|turkish|greek|portuguese|scottish|welsh|english|kiwi|aussie|brit|swiss|austrian|belgian|romanian|hungarian|czech|israeli|egyptian|nigerian|south african|argentinian|colombian|vietnamese|iranian|new zealander)(?: citizen)?{END}(?! (?:food|people|culture|company|government|accent|guy|girl|man|woman|friend))",
                    r"\bas an? (american|british|canadian|australian|irish|german|french|italian|spanish|dutch|swede|norwegian|dane|finn|polish|russian|ukrainian|mexican|brazilian|indian|pakistani|filipino|filipina|brit|aussie|kiwi|israeli|scot|new zealander)(?: citizen| person| myself)?\b(?! (?:company|government|food))",
                    r"(?:^|[.!,;] )(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican) here\b",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(american|brit|british|canadian|aussie|australian|kiwi|irish|german|dutch|swede|indian|filipino|filipina|mexican|italian|french|polish|brazilian|turkish)\b(?! (?:women|men|girls|guys|food|people))",
                    r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\b(?:male|female|guy|girl|man|woman))\s+from (?:the )?(usa|us|uk|england|scotland|canada|australia|india|poland|italy|germany|france|spain|ireland|mexico|brazil|philippines|pakistan|turkey|netherlands|sweden|norway|denmark|portugal|greece|romania|egypt|nigeria|south africa|new zealand)\b",
                    rf"(?:\[\s?[mf]{{1,2}}4[mfa]\w*\s?\]|\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b|/\s?m\s?/)\W{{0,4}}({COUNTRY_NAMES}|{DEMONYM_NAMES})\b(?! (?:women|men|girls|guys|food|people|couples?))",
                    rf"\b{I} (?!not\b)(?:also |a |an |half |proudly )?({DEMONYM_NAMES})\b(?! (?:food|people|culture|company|government|accent|friend|girlfriend|boyfriend|wife|husband|music))"),
    "language": (r"\bmy (?:native|first|mother) (?:language|tongue) is ([a-z]+)\b", r"\b([a-z]+) is my (?:native|first|mother) (?:language|tongue)\b",
                 rf"\b{I} {A}native ([a-z]+) speaker\b",
                 rf"\b(?:i|we) (?:only |also |can |do |mainly |mostly |natively |fluently |still )?(?:speak|talk in|grew up speaking) (?:fluent |native |only |some |basic |a little |good )?({LANGUAGE_NAMES})\b"),
    "religion": (rf"\b{I} (?!not\b|now\b)(?:also |a |an )?(?:[a-z]+ ){{0,2}}?(jew|{RELIGIONS}|not religious)\b{NOT_INSTITUTION}",
                 rf"\bas an? (jew|{RELIGIONS})\b{NOT_INSTITUTION}", rf"(?:^|[.!,;] )(?:[a-z]+ )?({RELIGIONS}) here\b",
                 rf"{STRICT_TAG}({RELIGIONS})\b(?! (?:women|men|girls|guys|people|wife|husband))",
                 r"\b(?:ich bin|bin) (?:auch |selber )?(atheist|christ|christin|muslim|muslimin)\b"),
    "residence_country": (rf"\b(?:{I}|i live|we live|living|based|located|i stay|currently|i reside)\s+(?:(?:currently|still|now|actually|also|just|living|based|located|residing)\s+)?(?:in|near|around|outside(?: of)?)\s+(?:the\s+)?{PLACE}",
                          rf"#\s?{PLACE}", rf"\[?[mf]4[mfa]\w*\]?\W{{0,4}}{PLACE}",
                          rf"(?:\b\d{{2}}\s?[mf]\b|\b[mf]\s?\d{{2}}\b|[mf]4[mfa]\w*\]?|\b\d{{2}})\s+(?:\w+\s+)?(?:in|from)\s+(?:the\s+)?{PLACE}",
                          rf"\b(?:hello|hi|greetings|hey|hallo|hola) from (?:the )?{PLACE}",
                          rf"\b(?:and|but|also|who|still|we|currently) live in (?:the )?{PLACE}",
                          rf"\bi (?:just |recently |finally )?(?:moved|relocated) to (?:the )?{PLACE}",
                          rf"\b(?:location|loc|based|area)\s*[:\-]\s*{PLACE}",
                          rf"\b(?:male|female|guy|girl|man|woman|couple|bull|dom|sub|top|bottom|dude|lady)\s+(?:here\s+)?(?:in|near|around) (?:the )?{PLACE}"),
    "origin_country": (rf"\b{I} (?:originally )?from (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which | originally)",
                       r"\bi (?:was )?(?:born and raised|grew up|was born|was raised) in (?:the )?([a-z][a-z .'-]+?)(?=$|[.,!?;)]| and | but | so | where | which )",
                       rf"\b(?:i|we) (?:just |recently |originally )?(?:moved|immigrated|emigrated|came|relocated) (?:here |over |to [a-z]+ |to the [a-z]+ )?from (?:the )?{PLACE}",
                       rf"\bmy (?:home ?country|homeland|home town|hometown|country of origin|motherland|native country) is (?:the )?{PLACE}",
                       rf"(?:, |\b(?:guy|girl|man|woman|male|female|year old|years old|yo|y/o|graduate|dude|student|lady|boy|couple|[mf]|\d{{2}}[mf]|i'm|i’m|im|i am|originally)\s+)from (?:the )?({COUNTRY_NAMES})\b"),
    "height": (rf"\b{I} (?:an? |only |about |around |like |also )?(\d\s*(?:'|’|ft|foot|feet)\s*\d{{0,2}}(?:\"|”|in)?|\d\s*(?:'|’)\s*\d{{1,2}}|1[4-9]\d\s*cm|2[0-2]\d\s*cm|1[.,]\d\d\s*m)(?=$|[\s.,!?;)])(?! (?:away|from|deep|wide|long|tall [a-z]+ (?:fence|wall|tree)))",
               r"\bmy height is (\d\s*(?:'|’|ft|foot|feet)\s*\d{0,2}(?:\"|”)?|1[4-9]\d\s*cm|2[0-2]\d\s*cm)\b"),
    "weight": (r"\b(?:i |and |i currently |currently |my )?(?:weigh|weight|weighing|current weight)\s*(?:is|of|:|=|-|in at)?\s*(?:about |around |like |roughly |~)?(\d{2,3}(?:\.\d)?(?:\s?(?:lbs?|pounds|kgs?|kilos|kilograms|st|stone))?)\b(?!\s*(?:%|lbs? (?:of|more|less)|ago))",
               rf"\b{I} (?:currently |now )?(?:at )?(\d{{2,3}}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos))\b(?! (?:of|down|lost|heavier|lighter|more|less|weight))",
               r"\bmy (?:current )?weight is (\d{2,3}(?:\.\d)?\s*(?:lbs?|pounds|kg|kgs|kilos)?)\b"),
    "income": (rf"\b(?:i|and|currently) (?:currently |only |still |now |also |probably |actually |personally |usually |typically )?(?:make|made|earn|earned|gross|grossed|net|netted|clear|take home|bring in|brought in)\s+{ROUGHLY}({AMOUNT}{PERIOD}){NOT_SAVINGS}",
               rf"\b{I} (?:currently |now |only |still )?(?:making|earning|grossing|netting|clearing|paid)\s+{ROUGHLY}({AMOUNT}{PERIOD}){NOT_SAVINGS}",
               rf"\bi (?:get|got) paid\s+{ROUGHLY}({AMOUNT}{PERIOD})", rf"\bi (?:charge|bill)\s+{ROUGHLY}({AMOUNT}{PERIOD})",
               rf"\bmy (?:annual |yearly |base |current |gross |net |total )?(?:salary|income|pay|wage|comp|compensation|tc|take home)(?: is| was|:| of| =)?\s*{ROUGHLY}({AMOUNT}{PERIOD})"),
    "education": (rf"\bi (?:have|hold|got|earned|finished|did|completed|received|just got|just finished|am finishing|'m finishing|’m finishing|am doing|'m doing|’m doing|am pursuing|'m pursuing|’m pursuing|have done|also have|only have|already have) (?:a |an |my |a literal |only a |two |both )?({DEGREES}|college degree|university degree|law degree|medical degree)(?: degree| degrees)?\b",
                  rf"\bmy ({DEGREES})(?: degree)? (?:is |was )?in\b", rf"\bas someone with an? ({DEGREES}|college degree)\b"),
    "education_subject": (rf"\bi(?:'m| am|’m)? (?:currently )?(?:study|studied|studying|majored in|major in|majoring in|minored in|a student of|went to (?:college|school|uni|university) for) ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b(?:i (?:have|hold|got|earned|did|finished|completed|received|am doing|'m doing|’m doing|am finishing|'m finishing|’m finishing|am pursuing|'m pursuing|’m pursuing)|my) (?:a |an |my )?(?:{DEGREES}|degree|diploma|major|minor)(?: degree)? in ([a-z][a-z -]+?){SUBJECT_END}",
                          rf"\b{I} (?:a |an )?(?:\d+[a-z]* year |first year |second year |third year |final year |senior |junior |freshman |sophomore |current |recent |grad |graduate |college |university |uni |phd |masters? |undergrad )*{NOT_DEMONYM}([a-z-]+(?: [a-z-]+)?) (?:student|major|grad|graduate|minor)\b",
                          rf"(?:\b\d{{2}}\s?[mf]?\b|\b[mf]\s?\d{{2}}\b)[ ,]+(?:[a-z]+ )?{NOT_DEMONYM}([a-z-]+(?: [a-z-]+)?) (?:student|major)\b",
                          r"\bmy (?:degree|major) is (?:in )?([a-z][a-z ]+?)(?=$|[.,!?;)]| and | but | so | from)"),
    "occupation": (rf"\b{I} an? (?:{JOB_MODIFIERS} )*((?:[a-z]+ ){{0,2}}(?:{JOB_TITLES}|{JOB_HEADS}))s?{END}(?! (?:friend|wife|husband|mom|dad|fan))",
                   rf"\b(?:i|{I}|i've been|i’ve been|i have been|currently|now) (?:currently |now )?(?:work|working) as an? {JOB}",
                   rf"\bi(?:'ve|’ve| have) been an? {JOB}", rf"(?:^|[.!?] )as an? {JOB}(?:,| who| myself| i\b)",
                   rf"(?:^|[.!,;] )(?:{JOB_MODIFIERS} )*({JOB_TITLES}) here\b",
                   r"\bi (?:currently |now |also |still )?work (?:in|at a|in a|for a) ([a-z]+(?: [a-z]+)?)(?= (?:and|as|for|at|so|but|which|company|firm|office|industry|field|department|setting)\b|[.,!?;)]|$)",
                   rf"(?<!left )(?<!quit )(?<!lost )\b(?:my (?:job|work|career|role) as|my day job is|i got a job as|i took a job as|i'm employed as|i am employed as|i’m employed as) an? {JOB}"),
    "employment_status": (rf"\b(?:i|{I}|i've been|i’ve been|i have been) (?:currently |now |also |still )?(?:work|working) (full[- ]time|part[- ]time)\b", r"\bi (?:currently|now) (work)\b(?! (?:on|out|through))",
                          rf"\b(?:{I}|i've been|i’ve been|i have been) (?:currently |now |happily |fully )?(retired|unemployed|self[- ]employed|a student|a full[- ]time student|a college student|a university student|a stay[- ]at[- ]home (?:mom|mum|dad|parent)|a homemaker|a housewife|on disability|disabled|a freelancer|freelance|jobless|between jobs|laid off|out of work)\b",
                          r"\b(?:i(?:'m|’m| am|m)?|i've been|i’ve been|i have been|i got|i was just|i just got|recently|currently|still) (?:currently |still |now |recently |just |been )?(unemployed|laid off|jobless|between jobs|out of work|job hunting|looking for (?:a )?(?:job|work)|job searching|without a job)\b(?! (?:people|folks|friends?|guy|men|women))",
                          rf"\bi (work for myself|run my own business|own my own business|do freelance)\b|\b{I} (?:a |an )?(self[- ]employed|a freelancer|freelancing|an independent contractor|a business owner|my own boss)\b",
                          r"(?:\b\d{2}\s?(?:yo|y/o)?\s?[mf]?\b|\b[mf]\s?\d{2}\b|\[?[mf]4\w+\]?)[ ,/-]+(?:[a-z]+ ){0,2}?(retired)\b"),
    "marital_status": (r"(?:\b\d{2}\s?[mf]?|\b[mf]\s?\d{2}|\[?[mf]4\w+\]?)\W+(?:[a-z]+\W+){0,2}?(married)\b",
                       r"\b(?:i've|i have|we've|we have) been (married) (?:for )?", r"\b(married) (?:man|woman|guy|male|female|dad|mom|couple) here\b",
                       r"\b(?:we are|we're) an? (?:\w+ )?(married) couple\b",
                       r"\bmy (husband)\b(?! (?:and i (?:are|were) divorced|left|died|passed))", r"\bmy (wife) and i\b(?! (?:are|were) divorced)", rf"\b{I} (?:happily |newly )?(married|divorced|widowed|a widow|a widower|separated)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career))",
                       r"\b(?:with|and|told|love|tell|let|asked) my (husband|wife)\b(?!'s (?:friend|brother|sister))",
                       r"\b(?:happily|newly|recently|just got|i got|i'm|i’m|im|i am|i've been|i’ve been|i have been|we got|we've been|we’ve been) (married)\b(?! (?:to (?:my|a)? ?(?:job|work|career)|people|couples?|men|women|man|woman))",
                       r"(?:\b\d{2}\s?(?:yo|y/o)?\s?[mf]?\b|\b[mf]\s?\d{2}\b|\b[mf]\b|\[?[mf]4\w+\]?)[ ,/-]+(?:[a-z]+ ){0,2}?(married)\b",
                       r"\b(married) (?:man|woman|guy|male|female|dad|mom|mother|father|bi|white|black|straight|hispanic|asian|couple|mf|m|f)\b",
                       r"\b(?:my|the) (wife|husband|hubby) (?:is out|is away|is gone|is asleep|is at work|went|left for|travels|is travelling|is traveling|works|is working)\b"),
    "relationship_status": (rf"\b{I} (?:happily |newly |currently |still )?(engaged|single|in a relationship)\b(?! (?:to|for) (?:my|a)? ?(?:job|work|career)|(?: and)? (?:ready|looking) to mingle)",
                            r"\bi(?:'ve|’ve| have) been (single|in a relationship|engaged|dating)\b",
                            r"(?:\b\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\b[mf]\b)\s*,\s*(single|engaged|taken)\b",
                            rf"\b(?:{I}|i've been|i’ve been|i have been|i got|we got|we're|we’re|we are|we just got|i just got|recently|newly) (?:happily |newly |currently |still |recently |just |finally |now |also |completely |very |totally )?(single|engaged|dating someone|seeing someone|in a (?:committed |serious |long[- ]term |long[- ]distance |happy |new |monogamous |open |poly(?:amorous)? )?relationship|taken|unattached)\b(?! (?:to (?:my|a)? ?(?:job|work|career)|people|folks|moms?|dads?|parents?|men|women|guys|girls|friends?|ladies)|(?: and)? (?:ready|looking) to mingle)"),
    "parental_status": (r"\bi have (?:a |an |one |two |three |four |five |\d+ |young |grown |adult |little )*(kids|children|sons?|daughters?|toddlers?)\b",
                        r"\bi (gave birth)\b", r"\bas an? (?:\w+ )?(parent|mom|mum|dad|mother|father) (?:of|to)\b",
                        r"(?:^|[.!,;] )(?:(?!would|ftm|first)[a-z]+ ){0,3}(mom|dad|parent|mum|mother|father) here\b",
                        r"\b(?:single |new |first[- ]time |proud )?(mom|mum|mother|dad|father) (?:of|to) (?:a |an |one\b|two|three|four|five|\d|my |twins)",
                        r"(?<!your )(?<!her )(?<!his )(?<!my )\bsingle (mom|mum|dad|mother|father)\b",
                        rf"\b{I} (?:also |now )?{A}(?:single |new |first[- ]time |proud |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b(?! (?:of|to) (?:a|an|my|the|two) (?:dog|cat|pet|puppy|kitten|plant|fur))",
                        r"\bas an? (?:single |new |first[- ]time |working |stay[- ]at[- ]home )?(mom|mother|dad|father|mum|parent)\b",
                        rf"\b{I} (?:currently )?(pregnant)\b",
                        r"\b(?:married|single|divorced|horny|lonely|bi|bi-curious|bicurious|straight|white|black|fit|hot|busy|working|hung|naughty|curious|bored|fun|young|older|chubby|dilf|hairy|daddy|discreet|local) (dad|mom|mum|father|mother)\b(?! (?:of (?:a |my )?friend|'s|’s|jokes?|bod|body|vibes?|energy|friend))",
                        r"(?:^|[\s\]\)])(dad|mom|mum) (?:looking|seeking|wanting|needs|needing|here|of \d|of two|of three|with)\b"),
    "mental_health": (rf"\bi (?:also |do |still |actually |definitely |both )?(?:have|suffer from|struggle with|live with|deal with|am dealing with|'m dealing with|’m dealing with) {SEVERITY}({CONDITIONS})\b",
                      rf"\bi(?:'ve|’ve| have| was| got| am|'m|’m)? (?:been )?(?:officially |formally |recently |finally |also )?diagnosed (?:with |as )?(?:having )?{SEVERITY}({CONDITIONS})\b",
                      rf"\b{I} (?:an? )?(?:[a-z]+ ){{1,3}}with (?:my |unmedicated |severe |diagnosed )?({CONDITIONS})\b",
                      rf"\b{I} (?:also )?(autistic|bipolar|schizophrenic|an alcoholic|an addict)\b",
                      r"\bas (?:someone|a person|an adult|a woman|a man|a guy|a girl) with (adhd|autism|depression|anxiety|ocd|ptsd|bipolar(?: disorder)?|bpd)\b"),
    "political_ideology": (rf"\b{I} {A}(?:proud |lifelong |life-long |staunch |die[- ]hard )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|nationalist|marxist|moderate|democratic socialist)\b(?! (?:party|government|state|country|city|state|area|parents|family|friends|media))",
                           r"\bas an? (?:proud |lifelong |staunch )?(liberal|conservative|socialist|communist|anarchist|libertarian|progressive|centrist|marxist|democratic socialist)\b(?! (?:party|government|state|country|city|media))",
                           rf"\b{I} (?!not\b)(?:a |an |also a |also |pretty |very |extremely |fairly |generally |openly |still |basically |raging |self[- ]described |proud |lifelong |staunch )*({IDEOLOGIES})\b(?! (?:party|government|state|country|city|area|parents|family|friends|media|news|policies|politicians|people|men|women))", rf"(?:^|[.!,;] )(?:[a-z]+ )?({IDEOLOGIES}) here\b", rf"\bmy (?:politics|views|political views|political leanings) (?:are|is) (?:pretty |very |mostly |generally )?({IDEOLOGIES})\b", rf"\b(?:am|{I}) (?:an? )?({IDEOLOGIES}) myself\b"),
    "political_compass": (rf"\b{I} {A}(auth ?left|auth ?right|lib ?left|lib ?right|authleft|authright|libleft|libright)\b",),
}
COMPILED = {field: [re.compile(pattern) for pattern in patterns] for field, patterns in PHRASES.items()}
COMPACT = {name.replace(" ", ""): name for name in (*STATE_NAMES, *CITIES) if " " in name}
FILLER = {"online", "north", "south", "east", "west", "ne", "nw", "se", "sw", "central", "northern", "southern", "eastern", "western", "upstate",
          "downtown", "greater", "rural", "northeast", "northwest", "southeast", "southwest", "far", "midwest"}
PLACE_FIELDS = {"residence_country": ("residence_country", "residence_state", "residence_city"),
                "origin_country": ("origin_country", "origin_state", "origin_city")}
SKIP = re.compile(r"^\s*>.*$|\"[^\"\n]{0,300}\"|“[^”\n]{0,300}”|https?://\S+|\(/?r/\S+\)|\b/?[ru]/\S+", re.M)
WORD_CODES = {"on", "in", "me", "hi", "ma", "or", "ok", "oh", "de", "la", "co", "id", "al", "ne", "mo", "ms", "ar", "ab", "ns", "nb", "sk", "mb"}
HYPOTHETICAL = re.compile(r"\b(?:if|when|unless|whether|imagine|pretend|suppose|wish|would|hope|want to be|wanna be|used to be|was|think|thinks|assume|assumes|assumed)\W+(?:\w+\W+){0,3}$")
DIAGNOSES = {"add": "adhd", "asd": "autism", "an eating disorder": "eating disorder", "an alcoholic": "addiction", "an addict": "addiction", "cptsd": "ptsd",
             "c-ptsd": "ptsd", "autistic": "autism", "schizophrenic": "schizophrenia", "bipolar": "bipolar disorder"}
MARRIED = {"husband": "married", "wife": "married", "hubby": "married", "spouse": "married", "a widow": "widowed", "a widower": "widowed"}
CHILDREN = {"pregnant": "expecting"}
EMPLOYMENT = {"a full-time student": "student", "a full time student": "student", "a college student": "student",
              "a university student": "student", "a student": "student", "a freelancer": "self-employed", "freelance": "self-employed",
              "self employed": "self-employed", "jobless": "unemployed", "between jobs": "unemployed", "laid off": "unemployed",
              "out of work": "unemployed", "disabled": "unable to work", "on disability": "unable to work", "a homemaker": "homemaker",
              "a housewife": "homemaker", "job hunting": "unemployed", "looking for a job": "unemployed", "looking for work": "unemployed",
              "looking for job": "unemployed", "job searching": "unemployed", "without a job": "unemployed", "on ssdi": "unable to work",
              "on ssi": "unable to work", "on pip": "unable to work", "work for myself": "self-employed", "run my own business": "self-employed",
              "own my own business": "self-employed", "do freelance": "self-employed", "freelancing": "self-employed",
              "an independent contractor": "self-employed", "a business owner": "self-employed", "my own boss": "self-employed",
              "in college": "student", "in uni": "student", "in university": "student", "at university": "student", "at uni": "student",
              "in grad school": "student", "in law school": "student", "in med school": "student", "in nursing school": "student"}
PERIODS = {"hour": 2080, "hr": 2080, "hourly": 2080, "/h": 2080, "week": 52, "wk": 52, "weekly": 52, "month": 12, "mo": 12, "monthly": 12}
EARNINGS = re.compile(r"(.+?)\s*(?:(?:a|an|per|/|every)\s*)?(year|yr|annum|month|mo|hour|hr|week|wk|annually|yearly|monthly|hourly|weekly|/h)?"
                      r"(?:\s+(?:tc|base|base salary|salary|gross|pre[- ]tax|before tax|after tax|take home|ote))?$")
ORIENTATION_WORDS = {"lesbiana": "lesbian", "lésbica": "lesbian", "lesbienne": "lesbian", "bissexual": "bisexual", "bisexuel": "bisexual", "bisexuelle": "bisexual"}
BELIEFS = {"christ": "christian", "christin": "christian", "muslimin": "muslim", "not religious": "no religion"}
GENDERED = {"mom": "female", "mother": "female", "mum": "female", "wife": "female", "dad": "male", "father": "male", "husband": "male", "milf": "female",
            "femboy": "male", "chica": "female", "chico": "male", "homem": "male", "mulher": "female", "homme": "male", "femme": "female", "mann": "male",
            "ragazzo": "male", "ragazza": "female", "garota": "female", "garoto": "male", "menina": "female", "menino": "male"}


def search(field, text):
    for pattern in COMPILED[field]:
        for match in pattern.finditer(text):
            if not HYPOTHETICAL.search(re.split(r"[.!?\n(]", text[max(0, match.start() - 40):match.start()])[-1]):
                yield next(group for group in match.groups() if group is not None)


def resolve(field, raw):
    if field == "occupation":
        return JOBS.get(raw) or value(field, raw)
    if field == "mental_health":
        return value(field, DIAGNOSES.get(raw, raw))
    if field == "marital_status":
        return MARRIED.get(raw) or value(field, raw)
    if field == "parental_status":
        return CHILDREN.get(raw, "parent")
    if field == "employment_status":
        return EMPLOYMENT.get(raw.replace("self-employed", "self employed"), None) or value(field, raw)
    if field == "weight":
        raw = raw.replace("kilograms", "kg")
    if field == "weight" and re.fullmatch(r"\d{2,3}(?:\.\d)?", raw):
        return value(field, raw + (" lbs" if float(raw) >= 100 else " kg"))
    if field == "income":
        return earnings(raw)
    if field == "birth_year":
        raw = raw.lstrip("'’")
        return value(field, "19" + raw if re.fullmatch(r"[4-9]\d", raw) else raw)
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
    if match := AGE_GENDER.search(text):
        found.setdefault("age", value("age", match.group(1)))
        found.setdefault("gender", value("gender", match.group(2)))
    if match := GENDER_AGE.search(text):
        found.setdefault("gender", value("gender", match.group(1)))
        found.setdefault("age", value("age", match.group(2)))
    if match := GENDER_BRACKET.search(text):
        found.setdefault("gender", value("gender", match.group(1)))
    if match := TAG_FOR.search(text):
        found.setdefault("gender", value("gender", match.group(2)))
        if match.group(1) or match.group(3):
            found.setdefault("age", value("age", match.group(1) or match.group(3)))
    if match := AGE_START.search(text) or AGE_BRACKET.search(text):
        found.setdefault("age", value("age", match.group(1)))


def stats(text, found):
    for match in (*HEIGHT_ANY.finditer(text), *HEIGHT_METRIC.finditer(text)):
        if not PEOPLE.search(text[max(0, match.start() - 25):match.start()]) and (height := value("height", match.group(1))) is not None:
            found["height"] = height
            break
    if "height" in found or "age" in found:
        for match in WEIGHT_ANY.finditer(text):
            if not OTHER.search(text[max(0, match.start() - 25):match.start()]) and (weight := value("weight", match.group(1))) is not None:
                found["weight"] = weight
                break


def extract(text):
    text = SKIP.sub(" ", text.lower()).translate(PRIMES)
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
