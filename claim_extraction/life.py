import re
from pathlib import Path

from .common import HEDGE, I, SELF_HEDGE, TAGGED, fixed, group, rule

NEAR = re.compile(r"\b(?:be|become|becoming|imagine|pretend|roleplay|rp|future|someday|dream|wish|if i (?:ever )?(?:had|have|get|got|find)|when i (?:have|get|find))[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
SCOPED = re.compile(r"\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
STATED = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once|used to|when i was|back when|no longer|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
FUTURE = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|until|once|when|someday|one day|would|want to|wanna|hope to|plan to|planning to|used to|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
CONDITIONAL = re.compile(r"\b(?:if|would|wish)\b")
AS = (r"\bas(?:(?<=^as)|(?<=[\n.!?,;:(\"*\[\]-]as)|(?<=[\n.!?,;:(\"*\[\]-] as)|(?<=[\n.!?,;:(\"*\[\]-]  as)|(?<=\band as)|(?<=\bbut as)|(?<=\bso as)|(?<=\bme as)|(?<=\bmyself as)|(?<=\bthat as)|(?<=\bthis as)"
      r"|(?<=\bspeaking as)|(?<=\beven as)|(?<=\bjust as)|(?<=\bsay as)|(?<=\bsaid as)|(?<=\bi as))")


def free(match, hedge=NEAR):
    return not hedge.search(match.string, max(0, match.start() - 40), match.start())


def spoken(match):
    line = match.string[match.string.rfind("\n", 0, match.start()) + 1:match.start()]
    return free(match) and line.count('"') % 2 == 0 and line.count("“") <= line.count("”")


def owned(table, number=1):
    return lambda match: None if not spoken(match) or table.get(match.group(number)) == MARRIED and ENDED.search(match.string) or table.get(match.group(number)) == DATING and BROKEN.search(match.string) else table.get(match.group(number))


def kept(result):
    return lambda match: result if spoken(match) else None


ENDED = re.compile(r"\b(?:i'm|i am|im|we're|we are|we got|i got) (?:now |recently |newly |legally |finally |officially )?(?:divorced|separated)\b|\b(?:my|our) divorce\b|\bmy ex[- ]?(?:wife|husband|hubby|spouse)\b|\bnow ex\b|\bmy (?:late|deceased) (?:wife|husband)\b|\bi(?:'m| am) (?:a )?widow(?:er|ed)?\b")
BROKEN = re.compile(r"\b(?:broke up with me|dumped me|(?:she|he) left me|we (?:just |recently |finally )?(?:broke up|broken up|split up)|i (?:just |finally )?broke up with (?:him|her|my)|since (?:the|our|my) break ?up|after (?:the|our|my) break ?up)\b")
FOND = (r"(?:sweet|lovely|loving|beautiful|gorgeous|pretty|hot|sexy|naughty|amazing|wonderful|awesome|dear|dearest|darling|current|new|supportive|incredible|poor|long[- ]?term|live[- ]in|beloved|own|big|"
        r"little|cute|cuck(?:old)?|kinky|horny|slutty|shy|petite|busty|curvy|thick|chubby|young|younger|older|patient|perfect|handsome|lucky|silly|sleepy|grumpy|crazy|lazy|jealous|loyal|faithful|now|second|2nd|third|3rd|"
        r"\d{2} ?[mf]?|\(\d{2} ?[mf]?\)|\d{2}[- ]?(?:yo|y/o|years?[- ]old)|(?:\w+[- ])?year[- ]old)")
WRITING = re.compile(r"\b(?:rp|roleplay|role play|role-play|writing|literate|kinks?|plot|para)\b")
SINGLE_LEAD = re.compile(r"(?<!every\. )(?<!every )(?<!my )(?<!stay )(?:^|[\n,(/|]|\b\d{2}\s*[mf]?\b|\b[mf]\s?\d{2}\b|\b[mf]4[mfat]\w*)\W*(?:[a-z]+ )?$")
MARRIED, DATING, ENGAGED = "married", "dating or in a relationship", "engaged"
SPOUSES = {"wife": MARRIED, "husband": MARRIED, "hubby": MARRIED, "wifey": MARRIED, "spouse": MARRIED, "missus": MARRIED, "mrs": MARRIED, "hubs": MARRIED, "wifes": MARRIED,
           "husbands": MARRIED, "girlfriend": DATING, "boyfriend": DATING, "gf": DATING, "bf": DATING, "partner": DATING, "significant other": DATING, "misses": MARRIED,
           "fiance": ENGAGED, "fiancé": ENGAGED, "fiancee": ENGAGED, "fiancée": ENGAGED, "jowa": DATING}
SPOUSE = r"(wife|husband|hubby|wifey|spouse|wifes|husbands|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)"
STATUSES = {"single": "single", "married": MARRIED, "engaged": ENGAGED, "divorced": "divorced", "separated": "separated", "widowed": "widowed", "a widow": "widowed",
            "a widower": "widowed", "in a relationship": DATING, "taken": DATING, "unmarried": "single", "not married": "single", "attached": DATING, "partnered": DATING}
BARE = r"(wife|wifey|hubby|husband|fianc[ée]e?|spouse|missus)"
LEAD = rf"(?:\b{I} (?:a |an )?|\bas an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*(?:[mf]|yo|y/o|years? old)?\b\W*(?:and )?|[\]\)]\s*|[-|:]\s+)"
TAIL = (r"(?! (?:to (?:the|this|that|it|my (?:job|work|career))|by|about|in terms|aback|care|seriously|advantage|in (?:a|an|the|this|that|it|some|conversation|discussion|debate|activities|activity|work)|handedly|digit|file|minded|out|away|back|off|over|up|"
        r"with (?:the|this|that|it|work))\b)")
KIN = r"(?:brother|sister|son|daughter|dad|mom|mum|father|mother|cousin|friend|friends|uncle|aunt|boss|neighbou?r|roommate|buddy|bro|sis|ex|former|future|dream|next|last|previous|first|late|dead|imaginary|fake|virtual|ai|old|then|best|own)"
FOLLOW = (r"(?=\s*(?:[.,!;:)(/\n]|$|\d|(?:and|but|with|for|since|in|here|now|again|too|af|m|f|male|female|man|woman|guy|girl|gal|lady|dude|mom|mum|mother|dad|father|parent|bbw|milf|dilf|couple)\b"
          r"|\w+ (?:with|and|from|in|looking|seeking|here|male|female|man|woman|guy|girl|mom|dad)\b))")


COUPLED = re.compile(r"\b(?:married|wife|husband|hubby|hotwife)\b")
SELF = re.compile(r"\b(?:i|me|my|we|our|us|i'm|im|i've)\b")
def stated(value, hedge=STATED):
    return lambda match: None if hedge.search(match.string, max(0, match.start() - 30), match.start()) else value(match)


def scoped_rules(rules):
    return [(attribute, pattern, stated(lambda match, value=value: value(match) if attribute == "pets" or spoken(match) else None, FUTURE), TAGGED) if hedge in (HEDGE, SELF_HEDGE) else (attribute, pattern, value, hedge) for attribute, pattern, value, hedge in rules]


def scoped(table):
    return lambda match: None if SCOPED.search(match.string, max(0, match.start() - 30), match.start()) else table.get(match.group(1))


def bounds(match):
    end = match.string.find("\n", match.end())
    return match.string.rfind("\n", 0, match.start()) + 1, end if end >= 0 else len(match.string)


def mine(match):
    return bool(SELF.search(match.string, *bounds(match)))


def couple(match):
    return None if COUPLED.search(match.string) or not spoken(match) else DATING


def partnered(match):
    return None if match.group(1) == "partner" and WRITING.search(match.string) else owned(SPOUSES)(match)

RELATIONSHIP = [
    rule("relationship_status", rf"(?:my(?<=\bmy)|our(?<=\bour))\s*(?:\(\d{{2}} ?[mf]?\) ?)?(?:{FOND}[ ,]+){{0,3}}{SPOUSE}(?:'s)?\b(?![- ]?to[- ]be|(?:'s)? (?:in crime|at the time|back then|in (?:high school|college)|died|passed)\b)", partnered, TAGGED),
    rule("relationship_status", rf"(?:^|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\b\W*|\]\s*)(?:(?:re)?post\W*|update\W*)?(?:{FOND}\s+){{0,3}}{BARE}(?:'s)?\b"
         r"(?=\s*(?:\(|\d{2}|[.,!](?!\w))|\s+(?!(?:wanted|needed|material|for|search|hunt|swap|request|appreciation|experience|goals|vibes|energy|wanna|of|or|vs|who|that|culture|beaters?|pics?|photos?|share|sharing)\b)[a-z])", lambda match: owned(SPOUSES)(match) if mine(match) else None, TAGGED),
    rule("relationship_status", rf"my (?<=\bmy )(?!{KIN}\b)(?!(?:business|lab|dance|tennis|study|writing|rp|gym|workout|sparring|accountability|training|climbing|golf|chess|duo|game|gaming|trading|research|project|work|running|hiking|language|practice|debate|doubles|play)\b)[a-z]+ (wife|husband|hubby|fianc[ée]e?|girlfriend|boyfriend|gf|bf|partner)\b(?!'s (?:friend|brother|sister|ex))", partnered, TAGGED),
    rule("relationship_status", rf"i (?<=\bi )(?:do |also |already |currently )?(?:have|got) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))", owned(SPOUSES), SELF_HEDGE),
    rule("relationship_status", r"\b(?:me and|and i|with|i and) the (wife|missus|mrs|hubby|wifey)\b|\bthe (wife|missus|mrs|hubby|wifey) and (?:i|me)\b|\bme (?:and|&) (?:my )?(hubby|wife|husband|missus|misses|mrs|wifey|hubs)\b", lambda match: SPOUSES.get(next(filter(None, match.groups()))) if free(match) else None, TAGGED),
    rule("relationship_status", r"(?<!')\b(?:mi|minha|meu|mon|ma|meine|mein|min|mijn|moja|mia|mio) (esposa|marido|esposo|mujer|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|vriendin|vriend|partner|partnerin)\b",
         group({"esposa": MARRIED, "mujer": MARRIED, "marido": MARRIED, "esposo": MARRIED, "femme": MARRIED, "mari": MARRIED, "frau": MARRIED, "mann": MARRIED, "kone": MARRIED, "mand": MARRIED,
                "vrouw": MARRIED, "man": MARRIED, "żona": MARRIED, "moglie": MARRIED, "marito": MARRIED} | dict.fromkeys(("novia", "novio", "namorada", "namorado", "copine", "copain", "freundin", "freund", "kæreste", "vriendin", "vriend", "partner", "partnerin"), DATING)), TAGGED),
    rule("relationship_status", r"\b(?:мо[яейюи]\w*) (жен[аыеуой]\w*|муж\w*)|\bmo(?:j|ja|jego|jej|jemu|im|ją) (mąż|męża|mężem|mężowi|żony|żonie|żoną|żonę)\b|\b(eşim|karım|kocam(?!an))\w*"
         r"|\b(asawa|mister|misis) ko\b|\baking (asawa)\b|\bmer[ie] (wife|biwi|patni|husband|pati)\b|\b(istri|suami)(?:ku| saya| aku)\b|\bminha (mulher)\b"
         r"|\b(زوجتي|زوجي)|\b(אשתי|בעלי)(?! חיים)",
         fixed(MARRIED), TAGGED),
    rule("relationship_status", r"\b(?:my|our) (?:own |happy |long |current |second |strong |healthy |lovely |wonderful |great |good |sexless |open |\d+[- ]year )?marriage\b|\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|many|several) years (?:of marriage|married)\b"
         r"|\b(?:since|when|after|before) (?:we|i) got married\b|\b(?:we|i)(?:'ve| have) been (?:happily )?married\b(?! before)", fixed(MARRIED), SELF_HEDGE),
    rule("relationship_status", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\bmy (?:now )?ex(?: girlfriend| boyfriend| gf| bf)? (?:told|left|dumped|broke)\b|\b(?:she|he) (?:left|dumped) me\b"
         r"|\bi broke up with (?:my|the|him|her)\b|\bwe (?:just |recently |finally |officially )?(?:broke up|broken up|split up)\b|\b(?:my|our) (?:\w+ )?(?:fianc[ée]e?|gf|bf|girlfriend|boyfriend|partner) and i (?:just |recently |finally )?(?:broke up|split up|split|separated|called it quits)\b|\b(?:she|he) broke up with me\b|\bforever alone\b|\bbeen single (?:for|since)\b|\b(?:i'm|im|i am) (?:a )?single (?:mom|mum|mother|dad|father|parent)\b", stated(fixed("single")), TAGGED),
    rule("relationship_status", rf"\b{I} (?:happily |currently |still |also |newly |recently |now |officially |finally |legally )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|unmarried|not married)\b"
         rf"{TAIL}", scoped(STATUSES), TAGGED),
    rule("relationship_status", rf"(?<!every){LEAD}(?:recently |newly |happily |also |still |currently |now |not |un)?(single\b{FOLLOW}|(?:taken|attached)\b{FOLLOW}|married|divorced|separated|widowed|engaged)\b(?! (?:men|women|people|guys|girls|moms|dads|mothers|fathers|parents|couples|folks|life|ladies|ones|friends|or|vs|status|sex|player|file|use|cock)\b)(?!-){TAIL}",
         lambda match: None if SCOPED.search(match.string, max(0, match.start() - 30), match.start()) else "single" if re.search(r"(?:not |un)married", match.group()) else None if "not " in match.group() else STATUSES[match.group(1)], TAGGED),
    rule("relationship_status", r"\b(?:i'm|im|i am|we're|we are|we've been|i've been|i have been|we have been) (?:happily |currently |exclusively |casually |now )?dating (?:for|since|someone|a |an |another|this|each other)\b"
         r"|\bi (?:have |'ve )?(?:recently |just |finally )?(?:entered|got into|started|began) (?:a |an )(?:new |serious |committed |long[- ]distance |relationship )?relationship\b", stated(kept(DATING), FUTURE), TAGGED),
    rule("relationship_status", rf"\b{I} (?:\w+ )?in an? (?:[\w-]+ ){{1,2}}relationship\b(?! with (?:food|my (?:body|food|mom|dad|parents|family|job|work)|money|alcohol|god|jesus))", stated(fixed(DATING), FUTURE), TAGGED),
    rule("relationship_status", r"\bsingle\b(?=\s*(?:[,.!/)|&]|$|and\b|(?:looking|seeking|near|in|from|here|down|dtf|af|guy|girl|male|female|man|woman|dad|mom|mum|mother|father|\d)\b))",
         lambda match: stated(fixed("single"), FUTURE)(match) if SINGLE_LEAD.search(match.string, max(0, match.start() - 40), match.start()) else None, TAGGED),
    rule("relationship_status", r"\b[mf]4[mfat]\w*\]?\s*(?:-\s*)?(?:\d{2}\s*)?(?:-\s*)?(single|married|divorced|separated|widowed|engaged|taken)\b|\b(?<![^,/|( ])(?<![^,/|(] )(married|divorced|separated|widowed)\s*(?:[,/|)]|and\b)|\bmarital status\W*(single|married|divorced|separated|widowed|engaged)\b",
         lambda match: STATUSES.get(next(filter(None, match.groups()))) if free(match) else None, TAGGED),
    rule("relationship_status", r"\b(?:we(?:'re| are)|we got|we've been|now) (?:now |happily |both |finally |officially |just |recently )?married\b|\b(?:i'm|im|i am) (?:\w+ )?married to (?:a|an|my|the love|someone|him|her|\w+ (?:man|woman|guy|girl))\b", fixed(MARRIED), SCOPED),
    rule("relationship_status", r"\bmy (?:ex[- ]?(?:wife|husband|hubby|spouse|husbands|wifes)|divorce)\b|\b(?:after|since|during|before|post|through|finalized) (?:my|our|the) divorce\b|\b(?:i|we) (?:got|were|are|'re|am|'m) (?:\w+ )?divorced\b|\b(?:recently|newly|twice) divorced\b|\bdivorcee\b",
         fixed("divorced"), SCOPED),
    rule("relationship_status", r"\b(?:recently|newly|happily|still|forever) single\b|\bsingle (?:for|since) (?:\d+|a|the|over|almost|about|two|three|many|several)\b|\b(?:i have|i've got|i got|i'm|im|with) no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|relationship|spouse|so)\b"
         r"|\b(?<![^,; ])(?<![^,;] )no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|spouse)\s*[,;&]|\b(?<!you )(?<!he )(?<!she )(?<!they )(?<!u )(?:don't|do not|dont) (?:currently |even |really )?have (?:a |an )?(?:girlfriend|boyfriend|gf|bf|partner|significant other|wife|husband|spouse)\b"
         r"|\b(?:у меня нет|я не) (?:сейчас )?(?:отношений|девушки|парня|жены|мужа|замужем|женат)", fixed("single"), CONDITIONAL),
    rule("relationship_status", r"\b(?:estoy|soy) (casad[oa]|solter[oa]|divorciad[oa]|comprometid[oa])\b|\bestoy (?:en una relación|de novi[oa])\b|\bsou (casad[oa]|solteir[oa]|divorciad[oa]|noiv[oa])\b|\bestou (?:numa|em uma) relação\b"
         r"|\bich bin (verheiratet|single|ledig|geschieden|verlobt|vergeben)\b|\bje suis (mariée?|célibataire|divorcée?|fiancée?|en couple)\b|\bsono (sposat[oa]|single|fidanzat[oa]|divorziat[oa])\b"
         r"|\bjestem (żonaty|zamężna|mężatką|singlem|singielką|rozwiedzion[ya]|zaręczon[ya]|w związku)\b|\bik ben (getrouwd|single|vrijgezel|gescheiden|verloofd)\b|\bя (женат|замужем|холост|разведен[а]?|в отношениях)\b",
         lambda match: {"casad": MARRIED, "solte": "single", "divor": "divorced", "compr": ENGAGED, "noiv": ENGAGED, "verhe": MARRIED, "singl": "single", "ledig": "single", "gesch": "divorced", "verlo": ENGAGED,
                        "verge": DATING, "marié": MARRIED, "célib": "single", "fianc": ENGAGED, "en co": DATING, "sposa": MARRIED, "fidan": DATING, "żonat": MARRIED, "zamęż": MARRIED, "mężat": MARRIED,
                        "rozwi": "divorced", "zaręc": ENGAGED, "w zwi": DATING, "getro": MARRIED, "vrijg": "single", "женат": MARRIED, "замуж": MARRIED, "холос": "single", "разве": "divorced", "в отн": DATING}.get(
             (next(filter(None, match.groups()), None) or match.group().split(" ", 2)[-1])[:5], DATING), SCOPED),
    rule("relationship_status", r"\b(?:i|we) (?:just |recently |finally )?got (married|engaged|divorced)\b|\b(married) (?:for )?(?:\d+|a few|many|almost|over|nearly|about) (?:\w+ )?years\b",
         lambda match: {"married": MARRIED, "engaged": ENGAGED, "divorced": "divorced"}[next(filter(None, match.groups()))]),
    rule("relationship_status", r"\b(?:i'm|im|i am|we're|we are|we just|i just|just) (?:now |officially |recently |finally )?(?:got )?engaged\b(?! (?:in|with|by)\b)"
         r"|\bmy (?:husband|wife|hubby|bride|groom)[- ]to[- ]be\b|\b(?:planning|plan) (?:my|our) wedding\b|\b(?:our|my) wedding (?:is (?:in|next|on|this|coming|only)|will be|next (?:year|month|week)|planning|budget|venue|date)\b", stated(fixed(ENGAGED)), TAGGED),
    rule("relationship_status", r"\bmy late (?:wife|husband|hubby|spouse|partner)\b|\b(?:i lost|since i lost|after i lost|after losing|since losing) my (?:wife|husband|hubby|spouse)\b|\bmy (?:wife|husband|hubby|spouse) (?:passed away|died|passed)\b", stated(fixed("widowed")), TAGGED),
    rule("relationship_status", r"\bmy (?:estranged|separated) (?:wife|husband|hubby|spouse)\b|\bmy (?:stbx\w*|soon[- ]to[- ]be[- ]ex(?:[- ]\w+)?)\b|\b(?:we're|we are|we've been|we have been|we recently|we just) (?:\w+ )?separated\b", stated(fixed("separated")), TAGGED),
    rule("relationship_status", r"(?:^\W*(?:\d{2}\s*)?(?:[\[\(]\w+[\]\)]\s*)?(?:(?!he |she |they |you |who |we |got |get |not |never |was |were |be |been |is |are )\w+ )?married\b(?! (?:men|women|people|guys|couples|folks|life|cock|or)\b))", kept(MARRIED), TAGGED),
    rule("relationship_status", r"^\W*(?:(?:\d{2}\s*(?:[mf]\s*)?(?:/\s*\d{2}\s*(?:[mf]\s*)?)?)?[\[\(]?\s*(?:mf|fm)\s*4\s*[mfat]\w*|(?:\d{2}\s*)?[\[\(]?\s*mf\s*\d{2}\b|(?:(?!the |a |this |that |every |each |any |no )\w+ )?couple (?:looking|seeking|here|from|in|\d{2})\b)", couple, TAGGED),
    rule("relationship_status", r"(?:couple(?<=\bcouple) here|we(?<=\bwe)(?:'re| are) an? (?:\w+ )?couple)\b(?! (?:of|days?|weeks?|months?|years?|hours?|minutes?|games?|more|points?|times?|steps?|levels?)\b)", couple, TAGGED),
    rule("relationship_status", r"\b(gf|bf|boyfriend|girlfriend|jowa|partner) ko\b", owned(SPOUSES), TAGGED),
]

CHILD = (r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|"
         r"first ?born|lo|dc|dcs|bio kids|youngest|oldest|eldest|middle child|offspring|bairns?|sprogs?|tweens?|preteens?|pre-teens?|preschoolers?|kindergart(?:e)?ners?|(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth) graders?)")
AGE = r"(?:\d+|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks)?(?:[- ]old)?"
QUALIFIER = (rf"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|"
             r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)")
INFANT = re.compile(r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|crib|cot\b|formula|feeds?\b|feeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|bottle|sleep regression|stroller|pram|onesie|bassinet|car seat|"
                    r"kindergarten|preschool|school|daughter|son\b|mama|mommy|crawl|walking|talking|nap|\bborn\b|birth|pregnan|labou?r|deliver|milk|pump|nurs|ultrasound|\bob\b|\bweeks\b|\bmonths\b|teeth|tooth|\bcry|sleep")
PARENT_LEAD = re.compile(rf"(?:\b{I} an? |\bas an? |\bbeing an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[\]\)]\s*|[-|:]\s+|\b[mf]4[mfat]\w*\s*)(?:(?!my |his |her |your |their |our |the |a )[\w,-]+ ){{0,3}}$")
ROMANTIC = re.compile(r"\b(?:bf|gf|boyfriend|girlfriend|husband|hubby|wife|daddy|sex|sexy|cock|dick|pussy|fuck\w*|kiss\w*|cuddl\w*|horny|nsfw|lover|honey|babe|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?)\b")
PAST = re.compile(r"\b(?:was|were|been)\s+(?:\w+\s+)?$")
YEARS = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
PRONOUN = re.compile(r"\b(?:he|she|him|her|his|they|them|their)\b")
NOT_CHILD = (r"(?:dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|horses?|pony|birds?|cars?|trucks?|vans?|bikes?|house|home|laptop|computer|pc|phone|tv|account|self|body|brother|sister|cousin|nephew|niece|friend|student|students|"
             r"client|patient|boyfriend|girlfriend|bf|gf|husband|wife|grand\w*|mattress|bed|couch|boat|shoes|iphone|ipad|tablet|macbook|build|rig|tires?|battery|knees?|back|hips?)")


def aged(match):
    number, unit = match.group(1), match.group(2) or match.group(3)
    if unit.startswith(("y", "Y")) and number.isdigit() and int(number) > 17:
        return None
    return "has children" if free(match) and PRONOUN.search(match.string, match.end(), match.end() + 120) else None
FIRST = re.compile(r"\b(?:i|we)\b[^.!?\n]{0,40}$")
TEACHING = re.compile(r"\b(?:teach|teacher|class|classroom|students?|school|nanny|babysit\w*|camp|coach\w*|daycare|work)\b")
LISTED = re.compile(r"(?:^|[,;:]\s*|\b(?:single|married|divorced|no partner|no pets|no debt|\d{2}\s*[mf]?)\s*[,;&/]\s*(?:and )?)$")


def child(match):
    word = match.group(1)
    if not spoken(match):
        return None
    if word in ("baby", "babies", "bub", "bubba", "lo", "dc", "dcs") and not INFANT.search(match.string) and (word != "baby" or ROMANTIC.search(match.string)):
        return None
    if word == "teen" and not re.search(r"\d|year", match.group()):
        return None
    if word in ("youngest", "oldest", "eldest", "middle child") and re.match(r"\s*(?:brother|sister|sibling|cousin|friend|aunt|uncle|niece|nephew|grand|memor|and)", match.string[match.end():]):
        return None
    return "has children"


PARENTAL = [
    rule("parental_status", rf"(?:my (?<=\bmy )|our (?<=\bour ))(?:{QUALIFIER}[- ,]+){{0,3}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|cups?|tits|boobs|sister|brother|face|fever|shower)\b)", child, TAGGED),
    rule("parental_status", rf"\b(?:my|our) (?!(?:future|dream|unborn|imaginary|dog|cat|pup|puppy|fur|furry|kitty|bunny|plant|pet|god|ex|friends?|neighbou?rs?|sisters?|brothers?|cousins?|boyfriends?|girlfriends?|wife|husband|partner|aunt|uncle|boss|inner|little|baby|big|good)\b)[a-z]+ "
         rf"(?:{QUALIFIER}[- ,]+){{0,2}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|sister|brother|face|fever|shower)\b)",
         lambda match: None if match.group(1) in ("baby", "babies", "child") else child(match), TAGGED),
    rule("parental_status", r"\b(?:me and|i and|and i) the (?:kids|kiddos|little ones|twins)\b|\b(?:i|we) (?:\w+ )?(?:put|took|picked up|dropped off|drop off|pick up|bring|brought|bathed|fed) the (?:kids|kiddos|little ones|twins)\b(?! (?:in|at|from|of|who|that)\b)"
         r"|\bthe (?:kids|kiddos|little ones) and (?:i|me)\b", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"the (?<=\bthe )(?:kids|kiddos|little ones?|toddler|twins|baby|babies|newborn)\b(?! (?:in|at|from|of|who|that|these|those|they|i|we|you)\b)",
         lambda match: kept("has children")(match) if FIRST.search(match.string, max(0, match.start() - 44), match.start()) and not TEACHING.search(match.string) else None, TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|'ve got|have got|raised|am raising|'re raising|are raising|delivered) (?:only |just )?(?:twins|triplets|kids|children)\b(?! (?:of|in|at|who|that)\b)"
         r"|\bpregnant with (?:number|#|baby|no\.?) ?\d\b", lambda match: None if FUTURE.search(match.string, max(0, match.start() - 30), match.start()) else "expecting a child" if "pregnant" in match.group() else "has children", TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|'ve got|have got|raised|am raising|'re raising|are raising|delivered) (?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}"
         r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)",
         stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", rf"(?:\b{I}|{AS}) (?:a|an) (?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b"
         r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|solo|widowed|separated|older|hot|bored|lonely|bi|pervy|horny|sexy|naughty|boy|girl|twin|homeschool(?:ing)?|toddler|teen|preemie|nicu|autism|special needs|military|working[- ]class) ?(?:dad|mom|mum|father|mother|mama|mommy|parent)\b(?!s| bod| jokes?| energy| vibes| groups?| friends?| life| figure)",
         lambda match: stated(kept("has children"), FUTURE)(match) if PARENT_LEAD.search(match.string, max(0, match.start() - 60), match.start()) else None, TAGGED),
    rule("parental_status", rf"\b\d{{2}}\s*[mf]?\s*,?\s*(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)|\bfellow (?:parent|mom|mum|dad|mother|father)s?\b|\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?(?:\d+ |two |three |four )?{CHILD}\b"
         rf"|\b(?<![^\n.!? ])(?<![^\n.!?] )(?:the )?(?:wife|husband|hubby) (?:and|&) (?:the )?(?:\d+ |two |three )?(?:kids?|children|sons?|daughters?|boys|girls)\b|\bi have (?:a|an|one|two|three|\d) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)(?: 1/2| and a half)?[- ]?(?:year|yr|month)s?[- ]?olds?\b(?! (?:dog|cat|pup|puppy|kitten|horse|car|house|laptop|computer|phone))",
         kept("has children"), TAGGED),
    rule("parental_status", rf"\b(?:my|our) (\d+|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?(yo|y/o|year[- ]old|yr[- ]old|month[- ]old|week[- ]old)s?(?= (?!(?:{NOT_CHILD})\b)[a-z]+\b|[.,!?;)])",
         lambda match: None if match.group(2).startswith("y") and match.group(1).isdigit() and int(match.group(1)) > 17 else kept("has children")(match), TAGGED),
    rule("parental_status", rf"my (?<=\bmy )(?:now[- ]|almost[- ]|nearly[- ]|just[- ]turned[- ])?{YEARS}[- ]?(?:(years?|yrs?|months?|weeks?|wks?)[- ]olds?|(yo|y/o|mo|mos|m/o))\b(?! (?:{NOT_CHILD})\b)", aged, TAGGED),
    rule("parental_status", r"\bno (?:kids|children)\b(?! (?:allowed|please|zone|menu|under|in|at|on|were|are|will))",
         lambda match: "no children" if LISTED.search(match.string, 0, match.start()) or re.match(r"(?:,| and|;) no\b", match.string[match.end():]) or SELF.search(match.string, max(0, match.start() - 40), match.start()) else None, CONDITIONAL),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |almost |nearly |only |just |about |officially )?\d{1,2}(?:\+\d)? ?(?:w|wks?|weeks?)(?: along| pregnant|(?: and)? \d ?d(?:ays?)?)?\b(?! (?:sober|clean|out|post|into|off|postpartum|in|of|until|from|ago|later|since|after|before|without|free|smoke|nicotine|vape))"
         r"|\b\d{1,2} ?(?:weeks?|wks?) along\b|\bwe(?:'re| are) (?:having|expecting) (?:a baby|twins|a boy|a girl|our (?:first|second|third|rainbow)|another|baby)\b|\bi(?:'m| am) having (?:a baby|twins|my (?:first|second|third) (?:baby|child))\b|\bmy (?:due date|anatomy scan|nipt|nt scan|gender reveal|baby shower|glucose test)\b",
         stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"^\W*pregnant\b", stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:meine?n?|mein|unser\w*|mi|mis|mon|ma|mes|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|miei)\s+(?:\w+\s+)?(?:tochter|sohn|kinder|kindern|kids|söhne|söhnen|töchter|töchtern|hijo|hija|hijos|hijas|fils|fille|enfants|filho|filha|filhos|filhas|zoon|dochter|kinderen|córka|syn|dzieci|figlio|figlia|figli)\b"
         r"|\b(?:ich habe|ich hab|wir haben|tengo|tenemos|j'ai|nous avons|eu tenho|temos|ik heb|wij hebben|we hebben|ho|abbiamo|jeg har|vi har|jag har) (?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre|to|fire|två|fyra|\d) (?:\w+ )?"
         r"(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia|børn|barn|unger|døtre|sønner|söner|döttrar|søn|sønn|datter|dotter)\b",
         stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:min|mitt|mina|mit|mine|vores|våra|vår|vårt) (?:(?:lille|lilla|store|stora|yngste|ældste|eldste|äldsta|yngsta|to|tre|två) )?(?:son|søn|sønn|dotter|datter|døtre|döttrar|söner|sønner|barn|børn|unger|mindste|ældste|eldste|yngste|äldsta|yngsta)\b|\b(?:a |az )?(?:fiam|lányom|gyerekem|gyerekeim|kisfiam|kislányom)\b|\b(?:můj|moje|mého|mojí) (?:syn|dcera|děti|dítě|dceru|syna)\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) meu\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) (?:meu|mea|mei)\b|\b(?:mi|mis) (?:niño|niña|niños|niñas|bebé|nene|nena)\b",
         stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:have|'ve got|got|'ve) no (?:kids|children|child)\b|\bno (?:kids|children) (?:yet|of (?:my|our) own|here|for me)\b|\b(?:i|we) (?:don't|do not|dont) have (?:any )?(?:kids|children) (?:yet|of (?:my|our) own)\b|\bi(?:'ve| have) no (?:kids|children)\b",
         fixed("no children"), CONDITIONAL),
    rule("parental_status", r"\b(?:estoy|estou) (?:embarazada|grávida|gravida)\b|\bje suis enceinte\b|\bich bin schwanger\b|\bsono incinta\b|\bjestem w ciąży\b|\bik ben zwanger\b|\bя беременна\b|\bhamileyim\b|\bbuntis ako\b", stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:\d+ ?(?:weeks?|months?) )?post[- ]?partum\b|\bmy post[- ]?partum\b|\b\d+ ?(?:weeks?|months?|days?) post[- ]?partum\b|\b(?:since|after|when|before) (?:giving birth|i gave birth|(?:having|i had) my (?:\w+ )?(?:baby|son|daughter|kids?|child|children|first|second|third|twins|lo|youngest|oldest|little))\b|\bi gave birth\b|\bmy last pregnancy\b"
         r"|\bmy (?:c-section|c section|labor and delivery|birth story|epidural|maternity leave|paternity leave)\b|\bi(?:'m| am)? (?:still |exclusively |currently )?(?:breastfeeding|breastfed|ebf)\b|\bbreastfeeding my\b|\bnursing my (?:son|daughter|baby)\b", stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |finally |also )?(?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+(?:\+\d)? ?(?:weeks?|wks?|months?) pregnant\b|\b(?:i'm|im|i am|we're|we are) expecting(?= (?:a baby|our|my|twins|baby|a little|a boy|a girl|in|again)\b|[.!,]|$)"
         r"|\bmy (?:first |second |third |current |\d+(?:st|nd|rd|th) )?pregnancy\b|\b(?:my|our) (?:unborn|baby bump)\b|\bpregnant with (?:my|our) (?:first|second|third|\d|rainbow|twins|baby)\b|\bbaby (?:#|number )?\d on the way\b|\b(?:our|my) baby on the way\b"
         r"|\b(?:i'm|im|i am) due (?:in|next|this|any day|soon)\b|\bmy scheduled induction\b|\bcurrently pregnant\b|\bpregnant currently\b|\b(?:i'm|im|i am) currently \d+ ?(?:weeks|wks)\b", lambda match: None if PAST.search(match.string, max(0, match.start() - 20), match.start()) else stated(fixed("expecting a child"), FUTURE)(match), TAGGED),
    rule("parental_status", r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\b(?:i'm|im|i am|we're|we are) (?:\w+ )?child-?free\b|\bno kids of my own\b|\bi(?:'ve| have) never had (?:kids|children)\b|\bwe (?:don't|do not|dont) have (?:any )?(?:kids|children)\b"
         r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b"
         r"|\b(?:i|we) (?:love |enjoy )?being (?:kid|child)[- ]?free\b|\b(?:i|we) (?:can't|cannot|can not|couldn't|could not|wasn't able to|weren't able to|was never able to|am not able to|'m not able to) (?:have (?:kids|children|a baby|babies|a child)|conceive)\b"
         r"|\bneither of us (?:is|are|can|was|were) (?:able to )?(?:have|has) (?:kids|children)\b|\bi(?:'m| am) infertile\b|\bich habe keine? (?:kind|kinder)\b|\bje n'ai pas d'enfants?\b|\bno tengo hijos\b|\bnão tenho filhos\b|\bje ne suis pas (?:père|mère)\b", fixed("no children"), CONDITIONAL),
    rule("parental_status", r"\bmy (?:first|second|third|last|previous|older|other|eldest|oldest|youngest|\d+(?:st|nd|rd|th)) (?:birth|labou?r and delivery|delivery|c-?section|baby|born|kiddo|child)\b|\b(?:after|before|since) (?:i had|having) (?:my|our) (?:first|second|third|son|daughter|kids?|children|baby|babies)\b"
         r"|\bbefore i (?:got|became|was) pregnant (?:the first time|with (?:my|our))\b|\bafter my (?:first|second|third|last|previous|\d+(?:st|nd|rd|th)) pregnancy\b|\bwhen (?:i|we) had (?:my|our) (?:first|second|son|daughter|kids?|baby)\b", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:after|since|before) (?:just )?having (?:a |my |our |\d |two |three |four |the )?(?:\w+ )?(?:baby|babies|kids?|children|child|twins|son|daughter)\b|\bafter (?:having )?baby\b|\bafter i had my (?:\w+ )?(?:baby|son|daughter|kids?|first|second|third|twins)\b"
         r"|\b\d+ ?(?:years?|yrs?) post[- ]?partum\b|\b(?:i'm|im|i am) \d+ ?(?:weeks?|months?|wks?|mos?) pp\b|\b(?:my|both of my|all of my|each of my|all my|both my) (?:\w+ )?pregnancies\b|\b(?:i|since i|after i|when i) (?:just |recently |finally )?became a (?:\w+ )?(?:mom|mum|mother|dad|father|parent)\b"
         r"|\b(?:we|i) (?:just |recently )?had (?:a|our|my) (?:\w+ )?(?:baby|child|son|daughter)\b(?! (?:shower|of|in))|\b(?:married|divorced|single|separated|widowed) (?:with|w/) (?:\d+|one|two|three|four|five|a|an) (?:\w+ )?(?:kids?|children|child|sons?|daughters?|boys|girls)\b"
         r"|\b(?<![^\n,;:(|/ ])(?<![^\n,;:(|/] )(?:\d|two|three|four|five) (?:kids|children|teens)\b|\bkids\s*:\s*\d", stated(kept("has children"), FUTURE), TAGGED),
]

AKC_BREEDS = ("affenpinscher", "afghan hound", "airedale terrier", "akita", "alaskan klee kai", "alaskan malamute", "american bulldog", "american english coonhound", "american eskimo dog", "american foxhound", "american hairless terrier",
              "american leopard hound", "american staffordshire terrier", "american water spaniel", "anatolian shepherd dog", "appenzeller sennenhund", "australian cattle dog", "australian kelpie", "australian shepherd",
              "australian stumpy tail cattle dog", "australian terrier", "azawakh", "barbado da terceira", "barbet", "basenji", "basset fauve de bretagne", "basset hound", "bavarian mountain scent hound", "beagle", "bearded collie",
              "beauceron", "bedlington terrier", "belgian laekenois", "belgian malinois", "belgian sheepdog", "belgian tervuren", "bergamasco sheepdog", "berger picard", "bernese mountain dog", "bichon frise", "biewer terrier",
              "black and tan coonhound", "black russian terrier", "bloodhound", "blue picardy spaniel", "bluetick coonhound", "boerboel", "bohemian shepherd", "bolognese", "border collie", "border terrier", "borzoi", "boston terrier",
              "bouvier des ardennes", "bouvier des flandres", "boxer", "boykin spaniel", "bracco italiano", "braque du bourbonnais", "braque francais pyrenean", "braque saint-germain", "brazilian terrier", "briard", "brittany", "broholmer",
              "brussels griffon", "bull terrier", "bulldog", "bullmastiff", "cairn terrier", "calupoh", "canaan dog", "canadian eskimo dog", "cane corso", "cardigan welsh corgi", "carolina dog", "catahoula leopard dog",
              "caucasian shepherd dog", "cavalier king charles spaniel", "central asian shepherd dog", "cesky terrier", "chesapeake bay retriever", "chihuahua", "chinese crested", "chinese shar-pei", "chinook", "chow chow",
              "cirneco dell etna", "clumber spaniel", "cocker spaniel", "collie", "coton de tulear", "croatian sheepdog", "curly-coated retriever", "czechoslovakian vlciak", "dachshund", "dalmatian", "dandie dinmont terrier",
              "danish-swedish farmdog", "deutscher wachtelhund", "doberman pinscher", "dogo argentino", "dogue de bordeaux", "drentsche patrijshond", "drever", "dutch shepherd", "english cocker spaniel", "english foxhound", "english setter",
              "english springer spaniel", "english toy spaniel", "entlebucher mountain dog", "estrela mountain dog", "eurasier", "field spaniel", "finnish lapphund", "finnish spitz", "flat-coated retriever", "french bulldog",
              "french spaniel", "german longhaired pointer", "german pinscher", "german shepherd dog", "german shorthaired pointer", "german spitz", "german wirehaired pointer", "giant schnauzer", "glen of imaal terrier",
              "golden retriever", "gordon setter", "grand basset griffon vendéen", "great dane", "great pyrenees", "greater swiss mountain dog", "greyhound", "hamiltonstovare", "hanoverian scenthound", "harrier", "havanese",
              "hokkaido", "hovawart", "ibizan hound", "icelandic sheepdog", "irish red and white setter", "irish setter", "irish terrier", "irish water spaniel", "irish wolfhound", "italian greyhound", "jagdterrier",
              "japanese akitainu", "japanese chin", "japanese spitz", "japanese terrier", "kai ken", "karelian bear dog", "keeshond", "kerry blue terrier", "kishu ken", "komondor", "korean jindo dog", "kromfohrlander", "kuvasz",
              "labrador retriever", "lagotto romagnolo", "lakeland terrier", "lancashire heeler", "lapponian herder", "large munsterlander", "leonberger", "lhasa apso", "löwchen", "lucas terrier", "maltese",
              "manchester terrier (standard)", "manchester terrier (toy)", "mastiff", "miniature american shepherd", "miniature bull terrier", "miniature pinscher", "miniature schnauzer", "mountain cur", "mudi", "neapolitan mastiff",
              "nederlandse kooikerhondje", "nenets laika", "newfoundland", "norfolk terrier", "norrbottenspets", "norwegian buhund", "norwegian elkhound", "norwegian lundehund", "norwich terrier", "nova scotia duck tolling retriever",
              "old danish pointer", "old english sheepdog", "otterhound", "papillon", "parson russell terrier", "pekingese", "pembroke welsh corgi", "peruvian inca orchid", "petit basset griffon vendéen", "pharaoh hound", "plott hound",
              "pointer", "polish lowland sheepdog", "pomeranian", "pont-audemer spaniel", "poodle (miniature)", "poodle (standard)", "poodle (toy)", "porcelaine", "portuguese podengo", "portuguese podengo pequeno", "portuguese pointer",
              "portuguese sheepdog", "portuguese water dog", "presa canario", "pudelpointer", "pug", "puli", "pumi", "pyrenean mastiff", "pyrenean shepherd", "rafeiro do alentejo", "rat terrier", "redbone coonhound",
              "rhodesian ridgeback", "romanian carpathian shepherd", "romanian mioritic shepherd dog", "rottweiler", "russell terrier", "russian toy", "russian tsvetnaya bolonka", "saarloos wolfhond", "saint bernard", "saluki", "samoyed",
              "schapendoes", "schipperke", "scottish deerhound", "scottish terrier", "sealyham terrier", "segugio italiano", "shetland sheepdog", "shiba inu", "shih tzu", "shikoku ken", "siberian husky", "silken windhound",
              "silky terrier", "skye terrier", "sloughi", "slovakian wirehaired pointer", "slovensky cuvac", "slovensky kopov", "small munsterlander", "smooth fox terrier", "soft coated wheaten terrier", "spanish mastiff",
              "spanish water dog", "spinone italiano", "stabyhoun", "staffordshire bull terrier", "standard schnauzer", "sussex spaniel", "swedish lapphund", "swedish vallhund", "taiwan dog", "teddy roosevelt terrier", "thai bangkaew",
              "thai ridgeback", "tibetan mastiff", "tibetan spaniel", "tibetan terrier", "tornjak", "tosa", "toy fox terrier", "transylvanian hound", "treeing tennessee brindle", "treeing walker coonhound", "vizsla", "volpino italiano",
              "weimaraner", "welsh springer spaniel", "welsh terrier", "west highland white terrier", "wetterhoun", "whippet", "wire fox terrier", "wirehaired pointing griffon", "wirehaired vizsla", "working kelpie", "xoloitzcuintli",
              "yakutian laika", "yorkshire terrier")
WORDNET_DOGS = Path(__file__).with_name("wordnet_dogs.txt").read_text(encoding="utf-8").splitlines()
BREEDS = sorted({re.sub(r" \(.*\)| dog$", "", name) for name in AKC_BREEDS} | set(WORDNET_DOGS), key=lambda name: (-len(name), name))
DOG = rf"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt|(?!sham|snicker)[a-z]{{3,}}(?:poo|doodle)s?|(?:{'|'.join(map(re.escape, BREEDS))})s?)"
WIKIPEDIA_COAT_PATTERNS = (r"(?:mackerel |classic |blotched |spotted |ticked )?tabby", "tabbies", r"tortoiseshells?", r"torties?", r"torbies?", r"calicos?", r"tuxedos?", r"bicolou?rs?", r"vans?", r"harlequins?",
                           r"colou?rpoints?", r"smokes?", r"shaded", r"chinchillas?", r"solids?")
CAT = rf"(?:cats?|kittens?|kitty|kitties|catto|kitteh|(?:{'|'.join(WIKIPEDIA_COAT_PATTERNS)}))"
OTHER = (r"(?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|birds?|chickens?|hens|ducks?|goats?|horses?|pony|ponies|ball pythons?|corn snakes?|pet snakes?|snakes?|shrimps?|rodents?|"
         r"geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|fish|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|rats|mini pigs?|pet pigs?|alpacas?|llamas?|donkeys?|aquarium|fish tank)")
OWN = (r"\b(?:my|our) (?:(?!(?:friends|parents|moms|dads|mums|neighbors|neighbours|brothers|sisters|sons|daughters|boyfriends|girlfriends|bfs|gfs|cousins|grandmas|grandparents|roommates|aunts|uncles|exs|exes|kids|bosses|"
       r"husbands|wifes|future|dream|next|neighbor|neighbour|friend|sister|brother|family|families|childhood|late|previous|former|deceased|departed|first|last|the|a|an|and|but|or|so|after|before|of|to|in|on|at|for|with|from|by|about|like|than|as|that|this|these|those|which|who|where|when|while|if|is|was|are|were|be|been|am|has|had|have|do|does|did|i|you|he|she|it|we|they|me|him|her|us|them|not|no)\b)[a-z\d-]+ ){0,4}")
HAVE = r"\b(?:i|we) (?:also |both |still )?(?:have|got|'ve got|own|adopted|rescued|recently adopted|just adopted|just got|bought myself|got myself) (?:a |an |two |three |four |\d+ )?(?:(?!(?:to|seen|been|heard|watched|met|noticed|found|the|this|that|these|those|of|for|with|from|in|on|at|by|about|like|no|not|never|ever|always|is|was|are|were|and|or|but|my|your|his|her|their|our)\b)[a-z\d-]+ ){0,2}"
FELINE = re.compile(r"\bcats?\b|\bkitten|meow|litter|purr|feline|\bvet\b|catnip|scratching post|\bfur\b|indoor|outdoor|feral|adopt|rescue")
CANINE = re.compile(r"\b(?:dogs?|pups?|puppy|puppies|vet|walks?|walked|walking|leash|bark\w*|fetch|kibble|breed|breeder|groomer|crate|treats?|paws?|fur|tail|neutered|spayed)\b")
GENERIC_DOG = re.compile(r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt)$")


def pet(kind):
    def value(match):
        if not free(match):
            return None
        if kind == "cat" and match.group(1) and not re.fullmatch(r"cats?|kittens?|catto|kitteh|kitty|kitties", match.group(1)) and not FELINE.search(match.string):
            return None
        if kind == "dog" and (word := match.group(1)) and " " not in word and not GENERIC_DOG.match(word) and not CANINE.search(match.string):
            return None
        return kind
    return value


PETS = [
    rule("pets", rf"{OWN}({DOG})(?:'s)?\b(?! (?:girl|boy|face|eyes|fat|dog eyes|play)\b)(?!(?<=puppy) love\b)", pet("dog"), TAGGED),
    rule("pets", rf"{OWN}({CAT})(?:'s)?\b(?! (?:litter )?(?:is wet|pussy))", pet("cat"), TAGGED),
    rule("pets", rf"{HAVE}({DOG})\b(?! (?:in (?:this|the) (?:fight|race)|food|treats?|stickers?|shirts?|tattoos?|costumes?|emojis?)\b)", pet("dog"), SELF_HEDGE),
    rule("pets", rf"{HAVE}({CAT})\b", pet("cat"), SELF_HEDGE),
    rule("pets", rf"(?:\b{I} an? |{AS} an? )(?:proud |\w+ )?owner of (?:a |an |two |three |\d+ )?(?:[a-z-]+ ){{0,2}}(?:({DOG})|({CAT})|({OTHER}))\b",
         lambda match: pet("dog" if match.group(1) else "cat" if match.group(2) else "other pet")(match), SELF_HEDGE),
    rule("pets", rf"(?:\b{I} an? |{AS} an? )(?:proud |crazy |\w+ )?(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner|lady|person)\b|\b(dog|cat) (?:mom|mum|dad|mama|parent) here\b",
         lambda match: pet("dog" if (match.group(1) or match.group(2)) == "dog" else "cat")(match), SELF_HEDGE),
    rule("pets", r"\b(?:mi|mis) (perr[oa]s?|perrit[oa]s?|gat[oa]s?|gatit[oa]s?)\b|\b(?:meu|minha|meus|minhas) (cachorr[oa]s?|cadel[oa]s?|gat[oa]s?|gatinh[oa]s?)\b|\b(?:mon|ma|mes) (chien|chienne|chiens|chat|chatte|chats|chaton)\b|\b(?:mein|meine|meinen|meinem) (hund|hunde|hündin|katze|katzen|kater)\b"
         r"|\bmijn (hond|honden|kat|katten|poes)\b|\b(?:il mio|la mia|i miei|le mie) (cane|cani|cagnolino|gatto|gatta|gatti|gattino)\b|\b(?:mój|moja|moje) (pies|psy|piesek|kot|kotka|koty)\b|\b(köpeğim|kedim)\w*|\b(aso|pusa) ko\b",
         lambda match: ("cat" if re.match(r"gat|chat|kat|poes|kot|ked|pusa", next(filter(None, match.groups()))) else "dog") if free(match) else None, TAGGED),
    rule("pets", r"\bi (?:don't|do not|dont) have (?:any )?pets\b|\bi have no pets\b|\bwe (?:don't|do not|dont) have (?:any )?pets\b|\bno pets here\b", fixed("no pets"), CONDITIONAL),
    rule("pets", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:(?!from|of|with|and|to|in|on|at|for|is|was|the|a|an|are|were|be|been|has|had|have|by|little|high|lizard)[\w-]+ ){0,2}((?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|hens|chickens|ball pythons?|corn snakes?|snakes?|rodents?|geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|rats|horses?|ponies|snails?|shrimps?|fish tank|aquarium))\b(?! (?:brain|toy|game|collab)\b)", lambda match: "other pet" if free(match) else None, TAGGED),
]

LIVING = [
    rule("living_with", r"\bi (?:still )?live (?:all )?(?:alone|by myself|on my own)\b|\bliving (?:alone|by myself|on my own)\b|\bhappy alone\b|\bi'm (?:all )?alone\b|\b(?<!walking )(?<!walk )(?<!walked )(?<!going )(?<!go )(?<!went )(?<!come )(?<!came )(?<!coming )(?<!drive )(?<!driving )(?<!drove )(?<!get )(?<!got )(?<!getting )(?<!ride )(?<!riding )(?<!head )(?<!heading )(?<!headed )home alone\b(?! (?:today|tonight|now|too|right now|this (?:weekend|week|morning|afternoon|evening)|all (?:day|night|week|weekend)|for (?:the|a) (?:day|night|week|weekend|few)|and horny|& horny|with)\b)|\balone at home\b(?! (?:today|tonight|now|too|right now|this (?:weekend|week|morning|afternoon|evening)|all (?:day|night|week|weekend)|and horny)\b)|\balleine? (?:zu ?hause|daheim)\b", fixed("alone"), SELF_HEDGE),
    rule("living_with", r"\bi (?:have )?(?:lived|live|am living|'m living|still live) (?:at home )?with my (?:mom and dad|parents|mom|dad|mum|mother|father|folks|family|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi (?:still )?live at home\b|\bliving at home with\b",
         fixed("parents"), SELF_HEDGE),
    rule("living_with", r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse|sister|brother|son|daughter|aunt|uncle|cousin)\b|\bwe live together\b"
         r"|\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b"
         r"|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|hubby) and i (?:live|share (?:a|an|our)|rent|bought (?:a|our)|own (?:a|our)|have (?:a|an|our) (?:house|home|apartment|place|flat))\b|\bwho lives with me\b"
         r"|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))", fixed("partner or family"), SELF_HEDGE),
    rule("living_with", r"\b(?:my|our) (?:\w+ ){0,2}(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b|\b(?:ner|einer) wg\b", fixed("roommates"), SELF_HEDGE),
]

OWNING = re.compile(r"\b(?:mortgage|bought|buy|own|owned|paid|renovat\w*|remodel\w*|contractor|roof|hoa|property|selling|sell|sold|equity|yard|garage|basement|insurance|apprais\w*|built|build|attic|foundation|plumb\w*|furnace|hvac|siding|gutters?|lawn|deck|porch|driveway|landscap\w*)\b")
HOUSING = [
    rule("housing", r"\b(?:i|we) (?:just |recently |finally )?(?:own|bought|purchased|closed on) (?:a|my|our|the|this) (?:first |new |own )?(?:\w+ )?(?:house|home|condo|townhouse|townhome|property)\b|\bfirst[- ]time home ?buyers?\b(?= here)|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:\w+ )?(?:house|home|condo)\b|\bwhen (?:i|we) bought (?:my|our) (?:house|home)\b"
         r"|\b(?:,|and|who|[.!?]) (?:recently |just |finally )?(?:bought|purchased) (?:a|my|our) (?:new |first |\w+ )?(?:house|home|condo|townhouse)\b|\bselling (?:my|our) (?:house|home|condo)\b|\bin the middle of selling the house\b|\bmy house is (?:assessed|worth|paid off|valued|appraised)\b|\bclos(?:ed|ing) on (?:my|our) (?:\w+ )?(?:house|home|condo)\b"
         r"|\b(?:i|we) (?:have|own) (?:a|my own|our own) (?:\d+[- ]?(?:bed(?:room)?|br) )?(?:house|condo|townhouse|home)\b(?! (?:office|gym|studio|theater|theatre|bar|network|server|lab|loan|equity|warranty|base|page|game|birth|visit|care|health|nurse|depot))|\bpaid off (?:my|our) (?:house|mortgage|home)\b", fixed("homeowner")),
    rule("housing", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:mortgage|hoa|property tax(?:es)?|home ?owners? insurance|homeowner's insurance|home insurance)\b", kept("homeowner"), TAGGED),
    rule("housing", r"\b(?:my|our) (?:landlord|landlady|rent|leasing office|property manager|property owner|security deposit|tenancy|letting agent)\b|\b(?:ich )?wohne in (?:einer|ner) wg\b", kept("renter"), TAGGED),
    rule("housing", r"\bwe rent\b(?! (?:a car|cars|out)\b)|\b(?:i'm|im|i am|as) a tenant\b|\b(?:i|we) (?:pay|paid) (?:\$?\d[\d,]* (?:in |for |a month |per month )?|my |our |)rent\b|\bi rent (?:a|an|my)\b|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bi rent\b(?! (?:a car|cars|out|movies|equipment|tools|bikes?|a truck|a van|a uhaul|boats?|kayaks?|skis?)\b)|\bwe(?:'re| are) (?:currently )?renting\b", fixed("renter")),
    rule("housing", r"\b(?:i'm|im|i am|we're|we are|as|as new|as first[- ]time) (?:a |an )?(?:new |first[- ]time |proud )?(home ?owners?|renters?|tenants?)\b|\bi (?:live|am living|'m living|currently live) in an? (?:\w+ )?(?:apartment|apt|flat|studio)\b",
         lambda match: "homeowner" if match.group(1) and "own" in match.group(1) else "renter"),
    rule("housing", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bbeing homeless (?:for|since)\b|\bi(?:'ve| have) been homeless\b|\bi live in my car\b|\bi(?:'m| am) (?:living|sleeping) in (?:my|a) (?:car|van|tent|shelter)\b", fixed("homeless")),
    rule("housing", r"\bmy (?:current |new |apartment |\w+ )?lease\b|\b(?:i|we) (?:just |recently )?(?:signed|renewed|broke|break|re-?signed) (?:a|my|our|the) (?:\w+ )?lease\b|\b(?:resigning|renewing|breaking) (?:my|our) lease\b", lambda match: None if re.search(r"\b(?:car|cars|vehicle|truck|ev|tesla|auto|mileage|miles|bmw|honda|toyota|lease deal|lease payment)\b", match.string) else kept("renter")(match), TAGGED),
    rule("housing", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |\d+[- ]?(?:bed(?:room)?|br) )?house\b(?! (?:music|party|parties|rules|of|plants?|cat|guest|wine|band|special|keys?|key)\b)", lambda match: stated(kept("homeowner"), FUTURE)(match) if OWNING.search(match.string, *bounds(match)) else None, TAGGED),
]

RULES = [*RELATIONSHIP, *PARENTAL, *scoped_rules(PETS), *scoped_rules(LIVING), *HOUSING]
