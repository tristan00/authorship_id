import re

from .common import HEDGE, I, SELF_HEDGE, TAGGED, fixed, group, rule

NEAR = re.compile(r"\b(?:be|become|becoming|imagine|pretend|roleplay|rp|future|someday|dream|wish|if i (?:ever )?(?:had|have|get|got|find)|when i (?:have|get|find))[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
SCOPED = re.compile(r"\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
STATED = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once|used to|when i was|back when|no longer|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
FUTURE = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|until|once|when|someday|one day|would|want to|wanna|hope to|plan to|planning to|used to|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
FREE = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b)\w+ )?"
CONDITIONAL = re.compile(r"\b(?:if|would|wish)\b")


def free(match, hedge=NEAR):
    return not hedge.search(match.string, max(0, match.start() - 40), match.start())


def owned(table, number=1):
    return lambda match: table.get(match.group(number)) if free(match) else None


def kept(result):
    return lambda match: result if free(match) else None


FOND = (r"(?:sweet|lovely|loving|beautiful|gorgeous|pretty|hot|sexy|naughty|amazing|wonderful|awesome|dear|dearest|darling|current|new|supportive|incredible|poor|long[- ]?term|live[- ]in|beloved|own|big|"
        r"little|cute|cuck(?:old)?|kinky|horny|slutty|shy|petite|busty|curvy|thick|chubby|young|younger|older|patient|perfect|handsome|lucky|silly|sleepy|grumpy|crazy|lazy|jealous|loyal|faithful|now|second|2nd|third|3rd|"
        r"\d{2} ?[mf]?|\(\d{2} ?[mf]?\)|\d{2}[- ]?(?:yo|y/o|years?[- ]old)|(?:\w+[- ])?year[- ]old)")
WRITING = re.compile(r"\b(?:rp|roleplay|role play|role-play|writing|literate|kinks?|plot|para)\b")
SINGLE_LEAD = re.compile(r"(?<!every\. )(?<!every )(?<!my )(?<!stay )(?:^|[\n,(/|]|\b\d{2}\s*[mf]?\b|\b[mf]\s?\d{2}\b|\b[mf]4[mfat]\w*)\W*(?:[a-z]+ )?$")
MARRIED, DATING, ENGAGED = "married", "dating or in a relationship", "engaged"
SPOUSES = {"wife": MARRIED, "husband": MARRIED, "hubby": MARRIED, "wifey": MARRIED, "spouse": MARRIED, "missus": MARRIED, "missis": MARRIED, "mrs": MARRIED, "hubs": MARRIED, "wifes": MARRIED,
           "husbands": MARRIED, "hotwife": MARRIED, "dh": MARRIED, "bride": MARRIED, "girlfriend": DATING, "boyfriend": DATING, "gf": DATING, "bf": DATING, "partner": DATING, "bae": DATING,
           "significant other": DATING, "so": DATING, "misses": MARRIED, "other half": DATING, "better half": DATING, "fiance": ENGAGED, "fiancé": ENGAGED, "fiancee": ENGAGED, "fiancée": ENGAGED}
SPOUSE = r"(wife|husband|hubby|wifey|spouse|missus|missis|mrs|hubs|wifes|husbands|hotwife|dh|bride|girlfriend|boyfriend|gf|bf|partner|bae|significant other|so(?![- ]called)|other half|better half|fianc[ée]e?)"
STATUSES = {"single": "single", "married": MARRIED, "engaged": ENGAGED, "divorced": "divorced", "separated": "separated", "widowed": "widowed", "a widow": "widowed",
            "a widower": "widowed", "in a relationship": DATING, "taken": DATING, "unmarried": "single", "not married": "single", "attached": DATING, "partnered": DATING}
BARE = r"(wife|wifey|hubby|husband|hotwife|fianc[ée]e?|spouse|missus)"
LEAD = rf"(?:\b{I} (?:a |an )?|\bas an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*(?:[mf]|yo|y/o|years? old)?\b\W*(?:and )?|[\]\)]\s*|[-|:]\s+)"
TAIL = (r"(?! (?:to (?:the|this|that|it|my (?:job|work|career))|by|about|in terms|aback|care|seriously|advantage|in (?:a|an|the|this|that|it|some|conversation|discussion|debate|activities|activity|work)|handedly|digit|file|minded|out|away|back|off|over|up|"
        r"with (?:the|this|that|it|work))\b)")
KIN = r"(?:brother|sister|son|daughter|dad|mom|mum|father|mother|cousin|friend|friends|uncle|aunt|boss|neighbou?r|roommate|buddy|bro|sis|ex|former|future|dream|next|last|previous|first|late|dead|imaginary|fake|virtual|ai|old|then|best|own)"
FOLLOW = (r"(?=\s*(?:[.,!;:)(/\n]|$|\d|(?:and|but|with|for|since|in|here|now|again|too|af|m|f|male|female|man|woman|guy|girl|gal|lady|dude|mom|mum|mother|dad|father|parent|bbw|milf|dilf|couple)\b"
          r"|\w+ (?:with|and|from|in|looking|seeking|here|male|female|man|woman|guy|girl|mom|dad)\b))")


def stated(value, hedge=STATED):
    return lambda match: None if hedge.search(match.string, max(0, match.start() - 30), match.start()) else value(match)


def scoped_rules(rules):
    return [(attribute, pattern, stated(value, FUTURE), TAGGED) if hedge in (HEDGE, SELF_HEDGE) else (attribute, pattern, value, hedge) for attribute, pattern, value, hedge in rules]


def scoped(table):
    return lambda match: None if SCOPED.search(match.string, max(0, match.start() - 30), match.start()) else table.get(match.group(1))


RELATIONSHIP = [
    rule("relationship_status", rf"\b(?:my|our)\s*(?:\(\d{{2}} ?[mf]?\) ?)?(?:{FOND}[ ,]+){{0,3}}{SPOUSE}(?:'s)?\b(?![- ]?to[- ]be|(?:'s)? (?:in crime|at the time|back then|in (?:high school|college)|died|passed)\b)",
         lambda match: None if match.group(1) == "partner" and WRITING.search(match.string) else owned(SPOUSES)(match), TAGGED),
    rule("relationship_status", rf"(?:^|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\b\W*|\]\s*)(?:(?:re)?post\W*|update\W*)?(?:{FOND}\s+){{0,3}}{BARE}(?:'s)?\b"
         r"(?=\s*(?:\(|\d{2}|[.,!](?!\w))|\s+(?!(?:wanted|needed|material|for|search|hunt|swap|request|appreciation|experience|goals|vibes|energy|wanna|of|or|vs|who|that|culture|beaters?|pics?|photos?|share|sharing)\b)[a-z])", owned(SPOUSES), TAGGED),
    rule("relationship_status", rf"\bmy (?!{KIN}\b)[a-z]+ (wife|husband|hubby|fianc[ée]e?)\b(?!'s (?:friend|brother|sister|ex))", owned(SPOUSES), TAGGED),
    rule("relationship_status", rf"\bi (?:do |also |already |currently )?(?:have|got) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))", owned(SPOUSES), SELF_HEDGE),
    rule("relationship_status", r"\b(?:me and|and i|with|i and) the (wife|missus|mrs|hubby|wifey)\b|\bthe (wife|missus|mrs|hubby|wifey) and (?:i|me)\b|\bme (?:and|&) (?:my )?(hubby|wife|husband|missus|misses|mrs|wifey|hubs)\b", lambda match: SPOUSES.get(next(filter(None, match.groups()))) if free(match) else None, TAGGED),
    rule("relationship_status", r"\b(?:mi|minha|meu|mon|ma|meine|mein|min|mijn|moja|mia|mio) (esposa|marido|esposo|mujer|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|vriendin|vriend|partner|partnerin)\b",
         group({"esposa": MARRIED, "mujer": MARRIED, "marido": MARRIED, "esposo": MARRIED, "femme": MARRIED, "mari": MARRIED, "frau": MARRIED, "mann": MARRIED, "kone": MARRIED, "mand": MARRIED,
                "vrouw": MARRIED, "man": MARRIED, "żona": MARRIED, "moglie": MARRIED, "marito": MARRIED} | dict.fromkeys(("novia", "novio", "namorada", "namorado", "copine", "copain", "freundin", "freund", "kæreste", "vriendin", "vriend", "partner", "partnerin"), DATING)), TAGGED),
    rule("relationship_status", r"\b(?:мо[яейюи]\w*) (жен[аыеуой]\w*|муж\w*)|\bmo(?:j|ja|jego|jej|jemu|im|ją) (mąż|męża|mężem|mężowi|żony|żonie|żoną|żonę)\b|\b(eşim|karım|kocam(?!an))\w*"
         r"|\b(asawa|mister|misis) ko\b|\baking (asawa)\b|\bmer[ie] (wife|biwi|patni|husband|pati)\b|\b(istri|suami)(?:ku| saya| aku)\b|\bminha (mulher)\b"
         r"|\b(زوجتي|زوجي)|\b(אשתי|בעלי)(?! חיים)",
         fixed(MARRIED), TAGGED),
    rule("relationship_status", r"\b(?:my|our) (?:own |happy |long |current |second |strong |healthy |lovely |wonderful |great |good |sexless |open |\d+[- ]year )?marriage\b|\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|many|several) years (?:of marriage|married)\b"
         r"|\b(?:since|when|after|before) (?:we|i) got married\b|\b(?:we|i)(?:'ve| have) been (?:happily )?married\b(?! before)", fixed(MARRIED), SELF_HEDGE),
    rule("relationship_status", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\bmy (?:now )?ex(?: girlfriend| boyfriend| gf| bf)? (?:told|left|dumped|broke)\b|\b(?:she|he) (?:left|dumped) me\b"
         r"|\bi broke up with (?:my|the|him|her)\b|\b(?:my|our) (?:\w+ )?(?:fianc[ée]e?|gf|bf|girlfriend|boyfriend|partner) and i (?:just |recently |finally )?(?:broke up|split up|split|separated|called it quits)\b|\b(?:she|he) broke up with me\b|\bforever alone\b|\bbeen single (?:for|since)\b|\b(?:i'm|im|i am) (?:a )?single (?:mom|mum|mother|dad|father|parent)\b", stated(fixed("single")), TAGGED),
    rule("relationship_status", rf"\b{I} (?:happily |currently |still |also |newly |recently |now |officially |finally |legally )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|unmarried|not married)\b"
         rf"{TAIL}", scoped(STATUSES), TAGGED),
    rule("relationship_status", rf"(?<!every){LEAD}(?:recently |newly |happily |also |still |currently |now |not |un)?(single\b{FOLLOW}|(?:taken|attached)\b{FOLLOW}|married|divorced|separated|widowed|engaged)\b(?! (?:men|women|people|guys|girls|moms|dads|mothers|fathers|parents|couples|folks|life|ladies|ones|friends|or|vs|status|sex|player|file|use|cock)\b)(?!-){TAIL}",
         lambda match: None if SCOPED.search(match.string, max(0, match.start() - 30), match.start()) else "single" if re.search(r"(?:not |un)married", match.group()) else None if "not " in match.group() else STATUSES[match.group(1)], TAGGED),
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
    rule("relationship_status", r"(?:^\W*(?:\d{2}\s*)?(?:[\[\(]\w+[\]\)]\s*)?(?:(?!he |she |they |you |who |we |got |get |not |never |was |were |be |been |is |are )\w+ )?married\b(?! (?:men|women|people|guys|couples|folks|life|cock|or)\b)"
         r"|\bmarried(?:/| and | )(?:dl|discreet|curious|bi|man|woman|guy|milf|dad|mom|couple|but|white|black|hwp|male|female|m|f)\b)", kept(MARRIED), TAGGED),
]

CHILD = (r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|boys|girls|boy|girl|"
         r"first ?born|lo|dc|dcs|bio kids|youngest|oldest|eldest|middle child)")
AGE = r"(?:\d+|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks)?(?:[- ]old)?"
QUALIFIER = (rf"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|"
             r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)")
INFANT = re.compile(r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|crib|cot\b|formula|feeds?\b|feeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|bottle|sleep regression|stroller|pram|onesie|bassinet|car seat|"
                    r"\blo\b|kindergarten|preschool|school|daughter|son\b|mama|mommy|crawl|walking|talking|nap|\bborn\b|birth|pregnan|labou?r|deliver|milk|pump|nurs|ultrasound|\bob\b|\bweeks\b|\bmonths\b|teeth|tooth|\bcry|sleep")
PARENT_LEAD = re.compile(rf"(?:\b{I} an? |\bas an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[\]\)]\s*|[-|:]\s+|\b[mf]4[mfat]\w*\s*)(?:(?!my |his |her |your |their |our |the |a )[\w,-]+ ){{0,3}}$")
PAST = re.compile(r"\b(?:was|were|been)\s+(?:\w+\s+)?$")
LISTED = re.compile(r"(?:^|[,;:]\s*|\b(?:single|married|divorced|no partner|no pets|no debt|\d{2}\s*[mf]?)\s*[,;&/]\s*(?:and )?)$")


def child(match):
    word = match.group(1)
    if not free(match):
        return None
    if word in ("boy", "girl", "boys", "girls") and not re.search(r"\b(?:\d+|one|two|three|little|lil|wee|baby|youngest|oldest|eldest|teenage)\b", match.group()):
        return None
    if word in ("baby", "babies", "bub", "bubba", "lo", "dc", "dcs") and not INFANT.search(match.string):
        return None
    if word == "teen" and not re.search(r"\d|year", match.group()):
        return None
    if word in ("youngest", "oldest", "eldest", "middle child") and re.match(r"\s*(?:brother|sister|sibling|cousin|friend|aunt|uncle|niece|nephew|grand|memor|and)", match.string[match.end():]):
        return None
    return "has children"


PARENTAL = [
    rule("parental_status", rf"\b(?:my|our) (?:{QUALIFIER}[- ,]+){{0,3}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|cups?|tits|boobs|sister|brother|face|fever|shower)\b)", child, TAGGED),
    rule("parental_status", rf"\b(?:my|our) (?!(?:future|dream|unborn|imaginary|dog|cat|pup|puppy|fur|furry|kitty|bunny|plant|pet|god|ex|friends?|neighbou?rs?|sisters?|brothers?|cousins?|boyfriends?|girlfriends?|wife|husband|partner|aunt|uncle|boss|inner|little|baby|big|good)\b)[a-z]+ "
         rf"(?:{QUALIFIER}[- ,]+){{0,2}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|sister|brother|face|fever|shower)\b)",
         lambda match: None if match.group(1) in ("baby", "babies", "child", "girl") else child(match), TAGGED),
    rule("parental_status", r"\b(?:me and|i and|and i) the (?:kids|kiddos|little ones|twins)\b|\b(?:i|we) (?:\w+ )?(?:put|took|picked up|dropped off|drop off|pick up|bring|brought|bathed|fed) the (?:kids|kiddos|little ones|twins)\b(?! (?:in|at|from|of|who|that)\b)"
         r"|\bthe (?:kids|kiddos|little ones) and (?:i|me)\b", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|'ve got|have got|raised|am raising|'re raising|are raising|delivered) (?:only |just )?(?:twins|triplets|kids|children)\b(?! (?:of|in|at|who|that)\b)"
         r"|\bpregnant with (?:number|#|baby|no\.?) ?\d\b", lambda match: None if FUTURE.search(match.string, max(0, match.start() - 30), match.start()) else "expecting a child" if "pregnant" in match.group() else "has children", TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|'ve got|have got|raised|am raising|'re raising|are raising|delivered) (?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}"
         r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)",
         stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", rf"\b(?:{I}|as) (?:a|an) (?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b"
         r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|solo|widowed|separated|older|hot|bored|lonely|bi|pervy|horny|sexy|naughty) ?(?:dad|mom|mum|father|mother|mama|mommy|parent)\b(?!s| bod| jokes?| energy| vibes| groups?| friends?| life| figure)",
         lambda match: stated(kept("has children"), FUTURE)(match) if PARENT_LEAD.search(match.string, max(0, match.start() - 60), match.start()) else None, TAGGED),
    rule("parental_status", rf"\b\d{{2}}\s*[mf]?\s*,?\s*(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)|\bfellow (?:parent|mom|mum|dad|mother|father)s?\b|\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?(?:\d+ |two |three |four )?{CHILD}\b"
         rf"|\b(?<![^\n.!? ])(?<![^\n.!?] )(?:the )?(?:wife|husband|hubby) (?:and|&) (?:the )?(?:\d+ |two |three )?(?:kids?|children|sons?|daughters?|boys|girls)\b|\bi have (?:a|an|one|two|three|\d) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)(?: 1/2| and a half)?[- ]?(?:year|yr|month)s?[- ]?olds?\b(?! (?:dog|cat|pup|puppy|kitten|horse|car|house|laptop|computer|phone))"
         r"|\b(?:my|our) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?(?:yo|y/o|year[- ]old|yr[- ]old|month[- ]old|week[- ]old)s?(?= (?:is|was|has|had|and|loves|likes|started|will|won't|can|can't|does|doesn't|did|didn't|just|still|keeps|gets|got|says|said|asked|wants|refuses|goes|went|son|daughter|boy|girl|twins|daughters|sons)\b|[.,!?;)])",
         kept("has children"), TAGGED),
    rule("parental_status", r"\bno (?:kids|children)\b(?! (?:allowed|please|zone|menu|under|in|at|on|were|are|will))",
         lambda match: "no children" if LISTED.search(match.string, 0, match.start()) or re.match(r"(?:,| and|;) no\b", match.string[match.end():]) else None, CONDITIONAL),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |almost |nearly |only |just |about |officially )?\d{1,2}(?:\+\d)? ?(?:w|wks?|weeks?)(?: along| pregnant|(?: and)? \d ?d(?:ays?)?)?\b(?! (?:sober|clean|out|post|into|off|postpartum|in|of|until|from|ago|later|since|after|before|without|free|smoke|nicotine|vape))"
         r"|\b\d{1,2} ?(?:weeks?|wks?) along\b|\bwe(?:'re| are) (?:having|expecting) (?:a baby|twins|a boy|a girl|our (?:first|second|third|rainbow)|another|baby)\b|\bi(?:'m| am) having (?:a baby|twins|my (?:first|second|third) (?:baby|child))\b|\bmy (?:due date|anatomy scan|nipt|nt scan|gender reveal|baby shower|glucose test)\b",
         stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"^\W*pregnant\b", stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:meine?n?|mein|unser\w*|mi|mis|mon|ma|mes|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|miei)\s+(?:\w+\s+)?(?:tochter|sohn|kinder|kindern|kids|söhne|söhnen|töchter|töchtern|hijo|hija|hijos|hijas|fils|fille|enfants|filho|filha|filhos|filhas|zoon|dochter|kinderen|córka|syn|dzieci|figlio|figlia|figli)\b"
         r"|\b(?:ich habe|ich hab|wir haben|tengo|j'ai|eu tenho|ik heb|ho) (?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre) (?:\w+ )?(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia)\b",
         stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:min|mitt|mina) (?:son|dotter|döttrar|söner|barn)\b|\b(?:a |az )?(?:fiam|lányom|gyerekem|gyerekeim|kisfiam|kislányom)\b|\b(?:můj|moje|mého|mojí) (?:syn|dcera|děti|dítě|dceru|syna)\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) meu\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) (?:meu|mea|mei)\b|\b(?:mi|mis) (?:niño|niña|niños|niñas|bebé|nene|nena)\b",
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
         r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b", fixed("no children"), CONDITIONAL),
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
BREEDS = sorted({re.sub(r" \(.*\)| dog$", "", name) for name in AKC_BREEDS}, key=len, reverse=True)
DOG = rf"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt|(?:{'|'.join(map(re.escape, BREEDS))})s?)"
WIKIPEDIA_COAT_PATTERNS = (r"(?:mackerel |classic |blotched |spotted |ticked )?tabby", "tabbies", r"tortoiseshells?", r"torties?", r"torbies?", r"calicos?", r"tuxedos?", r"bicolou?rs?", r"vans?", r"harlequins?",
                           r"colou?rpoints?", r"smokes?", r"shaded", r"chinchillas?", r"solids?")
CAT = rf"(?:cats?|kittens?|kitty|kitties|catto|kitteh|(?:{'|'.join(WIKIPEDIA_COAT_PATTERNS)}))"
OTHER = (r"(?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|birds?|chickens?|hens|ducks?|goats?|horses?|pony|ponies|ball pythons?|corn snakes?|pet snakes?|snakes?|shrimps?|rodents?|"
         r"geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|fish|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|rats|mini pigs?|pet pigs?|alpacas?|llamas?|donkeys?|aquarium|fish tank)")
OWN = (r"\b(?:my|our) (?:(?!(?:friends|parents|moms|dads|mums|neighbors|neighbours|brothers|sisters|sons|daughters|boyfriends|girlfriends|bfs|gfs|cousins|grandmas|grandparents|roommates|aunts|uncles|exs|exes|kids|bosses|"
       r"husbands|wifes|future|dream|next|neighbor|neighbour|friend|sister|brother|family|families|childhood)\b)[a-z\d-]+ ){0,4}")
HAVE = r"\b(?:i|we) (?:also |both |still )?(?:have|had|got|'ve got|own|adopted|rescued|recently adopted|just adopted|just got|bought myself|got myself) (?:a |an |two |three |four |\d+ )?(?:[a-z\d-]+ ){0,2}"
FELINE = re.compile(r"\bcats?\b|\bkitten|meow|litter|purr|feline|\bvet\b|catnip|scratching post|\bfur\b|indoor|outdoor|feral|adopt|rescue")
CANINE = re.compile(r"\b(?:dogs?|pups?|puppy|puppies|vet|walks?|walked|walking|leash|bark\w*|fetch|kibble|breed|breeder|groomer|crate|treats?|paws?|fur|tail|neutered|spayed)\b")
GENERIC_DOG = re.compile(r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt)$")


def pet(kind):
    def value(match):
        if not free(match):
            return None
        if kind == "cat" and match.group(1) and not re.fullmatch(r"cats?|kittens?|catto|kitteh", match.group(1)) and not FELINE.search(match.string):
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
    rule("pets", rf"\b(?:{I} an? |as an? )(?:proud |\w+ )?owner of (?:a |an |two |three |\d+ )?(?:[a-z-]+ ){{0,2}}(?:({DOG})|({CAT})|({OTHER}))\b",
         lambda match: pet("dog" if match.group(1) else "cat" if match.group(2) else "other pet")(match), SELF_HEDGE),
    rule("pets", rf"\b(?:{I} an? |as an? )(?:proud |crazy |\w+ )?(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner|lady|person)\b|\b(dog|cat) (?:mom|mum|dad|mama|parent) here\b",
         lambda match: pet("dog" if (match.group(1) or match.group(2)) == "dog" else "cat")(match), SELF_HEDGE),
    rule("pets", r"\b(?:mi|mis) (perr[oa]s?|perrit[oa]s?|gat[oa]s?|gatit[oa]s?)\b|\b(?:meu|minha|meus|minhas) (cachorr[oa]s?|cadel[oa]s?|gat[oa]s?|gatinh[oa]s?)\b|\b(?:mon|ma|mes) (chien|chienne|chiens|chat|chatte|chats|chaton)\b|\b(?:mein|meine|meinen|meinem) (hund|hunde|hündin|katze|katzen|kater)\b"
         r"|\bmijn (hond|honden|kat|katten|poes)\b|\b(?:il mio|la mia|i miei|le mie) (cane|cani|cagnolino|gatto|gatta|gatti|gattino)\b|\b(?:mój|moja|moje) (pies|psy|piesek|kot|kotka|koty)\b|\b(köpeğim|kedim)\w*|\b(aso|pusa) ko\b",
         lambda match: ("cat" if re.match(r"gat|chat|kat|poes|kot|ked|pusa", next(filter(None, match.groups()))) else "dog") if free(match) else None, TAGGED),
    rule("pets", r"\bi (?:don't|do not|dont) have (?:any )?pets\b|\bi have no pets\b|\bwe (?:don't|do not|dont) have (?:any )?pets\b|\bno pets here\b", fixed("no pets"), CONDITIONAL),
]

LIVING = [
    rule("living_with", r"\bi (?:still )?live (?:all )?(?:alone|by myself|on my own)\b|\bliving (?:alone|by myself|on my own)\b|\bhappy alone\b|\bi'm (?:all )?alone\b|\bhome alone\b|\balone at home\b|\balleine? (?:zu ?hause|daheim)\b", fixed("alone"), SELF_HEDGE),
    rule("living_with", r"\bi (?:have )?(?:lived|live|am living|'m living|still live) (?:at home )?with my (?:mom and dad|parents|mom|dad|mum|mother|father|folks|family|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi (?:still )?live at home\b|\bliving at home with\b",
         fixed("parents"), SELF_HEDGE),
    rule("living_with", r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse|sister|brother|son|daughter|aunt|uncle|cousin)\b|\bwe live together\b"
         r"|\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b"
         r"|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|hubby) and i (?:live|share (?:a|an|our)|rent|bought (?:a|our)|own (?:a|our)|have (?:a|an|our) (?:house|home|apartment|place|flat))\b|\bwho lives with me\b"
         r"|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))", fixed("partner or family"), SELF_HEDGE),
    rule("living_with", r"\b(?:my|our) (?:\w+ ){0,2}(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b|\b(?:ner|einer) wg\b", fixed("roommates"), SELF_HEDGE),
]

HOUSING = [
    rule("housing", r"\b(?:i|we) (?:just |recently |finally )?(?:own|bought|purchased|closed on) (?:a|my|our|the|this) (?:first |new |own )?(?:\w+ )?(?:house|home|condo|townhouse|townhome|property)\b|\bfirst[- ]time home ?buyers?\b(?= here)|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:\w+ )?(?:house|home|condo)\b|\bwhen (?:i|we) bought (?:my|our) (?:house|home)\b"
         r"|\b(?:,|and|who|[.!?]) (?:recently |just |finally )?(?:bought|purchased) (?:a|my|our) (?:new |first |\w+ )?(?:house|home|condo|townhouse)\b|\bselling (?:my|our) (?:house|home|condo)\b|\bin the middle of selling the house\b|\bmy house is (?:assessed|worth|paid off|valued|appraised)\b|\bclos(?:ed|ing) on (?:my|our) (?:\w+ )?(?:house|home|condo)\b"
         r"|\b(?:i|we) (?:have|own) (?:a|my own|our own) (?:\d+[- ]?(?:bed(?:room)?|br) )?(?:house|condo|townhouse|home)\b|\bcasa própria\b|\bpaid off (?:my|our) (?:house|mortgage|home)\b", fixed("homeowner")),
    rule("housing", r"\b(?:my|our) (?:mortgage|hoa|property tax(?:es)?|home ?owners? insurance|homeowner's insurance|home insurance)\b", kept("homeowner"), TAGGED),
    rule("housing", r"\b(?:my|our) (?:landlord|landlady|rent|leasing office|property manager|property owner|security deposit|tenancy|letting agent)\b|\b(?:ich )?wohne in (?:einer|ner) wg\b", kept("renter"), TAGGED),
    rule("housing", r"\bwe rent\b(?! (?:a car|cars|out)\b)|\b(?:i'm|im|i am|as) a tenant\b|\b(?:i|we) (?:pay|paid) (?:\$?\d[\d,]* (?:in |for |a month |per month )?|my |our |)rent\b|\bi rent (?:a|an|my)\b|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bi rent\b(?! (?:a car|cars|out|movies|equipment|tools|bikes?|a truck|a van|a uhaul|boats?|kayaks?|skis?)\b)|\bwe(?:'re| are) (?:currently )?renting\b", fixed("renter")),
    rule("housing", r"\b(?:i'm|im|i am|we're|we are|as|as new|as first[- ]time) (?:a |an )?(?:new |first[- ]time |proud )?(home ?owners?|renters?|tenants?)\b|\bi (?:live|am living|'m living|currently live) in an? (?:\w+ )?(?:apartment|apt|flat|studio)\b",
         lambda match: "homeowner" if match.group(1) and "own" in match.group(1) else "renter"),
    rule("housing", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bbeing homeless (?:for|since)\b|\bi(?:'ve| have) been homeless\b|\bi live in my car\b|\bi(?:'m| am) (?:living|sleeping) in (?:my|a) (?:car|van|tent|shelter)\b", fixed("homeless")),
]

RELIGIONS = {"christian": "christian", "catholic": "christian", "protestant": "christian", "mormon": "christian", "lds": "christian", "baptist": "christian", "methodist": "christian",
             "lutheran": "christian", "evangelical": "christian", "orthodox christian": "christian", "muslim": "muslim", "jew": "jewish", "jewish": "jewish", "hindu": "hindu",
             "buddhist": "buddhist", "sikh": "sikh", "pagan": "pagan or other religion", "wiccan": "pagan or other religion", "witch": "pagan or other religion",
             "spiritual": "spiritual, no religion", "agnostic": "agnostic", "atheist": "atheist"}
FAITH = "|".join(map(re.escape, RELIGIONS))
BELIEVER = r"(?=[^\w ]| (?:man|woman|person|guy|girl|lady|dude|mom|mum|dad|mother|father|myself|i|we|my|and|but|who|it|this|that|though|growing|raised|convert|believer|here|too|as well|now|so|because|since|for)\b|$)"

RELIGION = [
    rule("religion", rf"\b{I} {FREE}(?:a |an )?{FREE}({FAITH})\b(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater)\b)", scoped(RELIGIONS), TAGGED),
    rule("religion", rf"\bas an? (?:\w+ )?({FAITH})\b{BELIEVER}|\b(?:we|us) ({FAITH})s\b|\bi (?:became|became a|turned|am now|'m now|have become) ({FAITH})\b", lambda match: RELIGIONS.get(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("religion", r"(?:أنا|انا) (مسلم|مسلمة|مسيحي|مسيحية|ملحد|ملحدة)",
         lambda match: next((value for stem, value in (("مسلم", "muslim"), ("مسيح", "christian"), ("ملحد", "atheist"), ("ate", "atheist"), ("athe", "atheist"), ("athé", "atheist"), ("musul", "muslim"), ("muzu", "muslim"), ("muslim", "muslim"), ("moslim", "muslim"),
                                                       ("jud", "jewish"), ("jüd", "jewish"), ("juif", "jewish"), ("juive", "jewish"), ("ebre", "jewish"), ("joods", "jewish"), ("agnost", "agnostic")) if match.group().split()[-1].startswith(stem)), "christian"), SELF_HEDGE),
    rule("religion", r"\b(?:soy|sou) (católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|agnóstic[oa]|evangélic[oa])\b"
         r"|\bje suis (catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|agnostique)\b|\bich bin (katholisch|christ|christin|atheist|atheistin|muslim|muslima|jüdisch|evangelisch|agnostiker)\b"
         r"|\bjestem (katolikiem|katoliczką|ateistą|ateistką|chrześcijaninem|chrześcijanką|muzułmaninem|muzułmanką)\b|\bsono (cattolic[oa]|ateo|atea|cristian[oa]|musulman[oa]|ebre[oa])\b|\bik ben (katholiek|christen|atheïst|moslim|joods)\b",
         lambda match: next((value for stem, value in (("مسلم", "muslim"), ("مسيح", "christian"), ("ملحد", "atheist"), ("ate", "atheist"), ("athe", "atheist"), ("athé", "atheist"), ("musul", "muslim"), ("muzu", "muslim"), ("muslim", "muslim"), ("moslim", "muslim"),
                                                       ("jud", "jewish"), ("jüd", "jewish"), ("juif", "jewish"), ("juive", "jewish"), ("ebre", "jewish"), ("joods", "jewish"), ("agnost", "agnostic")) if match.group().split()[-1].startswith(stem)), "christian"), SELF_HEDGE),
    rule("religion", r"\bmy (?:salah|wudu|deen|hijab)\b", fixed("muslim"), SELF_HEDGE),
    rule("religion", r"\b(?:bible study|my bible|jesus is my|my lord and savior|my savior|my saviour|christ is king|my rosary|i'm (?:a )?catholic|as a catholic|i(?:'m| am) (?:a )?born[- ]again|i accepted (?:jesus|christ))\b", fixed("christian"), SELF_HEDGE),
    rule("religion", r"\bi converted to (islam|christianity|judaism|catholicism|buddhism|hinduism|orthodoxy|sikhism)\b",
         group({"islam": "muslim", "christianity": "christian", "judaism": "jewish", "catholicism": "christian", "buddhism": "buddhist", "hinduism": "hindu", "orthodoxy": "christian", "sikhism": "sikh"}), SELF_HEDGE),
    rule("religion", r"\bmy (?:bar|bat) mitzvah\b", fixed("jewish"), SELF_HEDGE),
    rule("religion", r"\bi(?:'m| am) not (?:a )?religious(?: person)?\b|\bi (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|\bi loathe (?:all )?religion\b|\bspiritual,? but not religious\b|\bя не религиозн|\bno soy religios[oa]\b|\bich bin nicht religiös\b",
         lambda match: "atheist" if "god" in match.group() or "loathe" in match.group() else "spiritual, no religion", TAGGED),
    rule("religion", rf"\bi (?:consider myself|identify as|would call myself|describe myself as) (?:a |an )?(?:\w+ )?({FAITH})\b|(?:^|[.!?,;(] *)({FAITH}) here\b|\bfellow ({FAITH})s?\b", lambda match: RELIGIONS.get(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("religion", r"\bi (?:\w+ )?pray (?:that )?allah\b", fixed("muslim"), SELF_HEDGE),
    rule("religion", r"\bmy (?:relationship|walk|journey) with (?:god|christ|jesus|the lord)\b|\bi (?:\w+ )?(?:seek|follow|love|accepted|believe in|trust in|pray to|worship) (?:jesus|christ|the lord)\b|\bi (?:\w+ )?pray (?:to god|every (?:day|night|morning)|daily|the rosary)\b",
         fixed("christian"), SELF_HEDGE),
    rule("religion", r"\bmy (?:pagan|wiccan|witchy|heathen|druid\w*|witchcraft) (?:community|path|practice|journey|beliefs|faith|spirituality|tradition|altar|craft|friends|group)\b|\bmy (?:altar|deities|patron (?:god|goddess|deity)|book of shadows)\b", fixed("pagan or other religion"), SELF_HEDGE),
]

POLITICS = {"communist": "communist or far left", "marxist": "communist or far left", "socialist": "socialist or left", "leftist": "socialist or left", "liberal": "progressive or liberal",
            "progressive": "progressive or liberal", "democrat": "progressive or liberal", "centrist": "centrist or moderate", "moderate": "centrist or moderate",
            "conservative": "conservative or right", "republican": "conservative or right", "libertarian": "libertarian", "anarchist": "anarchist",
            "nationalist": "nationalist or far right", "apolitical": "apolitical", "lefty": "socialist or left"}
PARTY = "|".join(POLITICS)
POLITICAL = [
    rule("political_identity", rf"\b{I} {FREE}(?:a |an )?{FREE}({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|with|about|when|in terms|on|in my|of|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach)\b)",
         scoped(POLITICS), TAGGED),
    rule("political_identity", rf"\bi (?:consider myself|identify as|would call myself|describe myself as) (?:a |an )?(?:\w+ )?({PARTY})\b|\bi(?:'m| am) a registered (democrat|republican)\b|\bi lean (?:more )?(?:to the )?(left|right|liberal|conservative)\b",
         lambda match: POLITICS.get(match.group(1)) or POLITICS.get(match.group(2)) or {"left": "socialist or left", "right": "conservative or right", "liberal": "progressive or liberal", "conservative": "conservative or right"}.get(match.group(3)), SELF_HEDGE),
    rule("political_identity", rf"\b(?:we|us) ({PARTY})s\b|\bme and (?:every|other|fellow|all the) ({PARTY})s?\b|\b(?:center|centre)[- ](left|right)(?: \w+){{0,2}} here\b|\bi(?:'m| am) (?:a )?(?:maga|trump supporter)\b|\bi (?:\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(trump|republican|gop|biden|harris|kamala|democrat|bernie|obama)\b"
         r"|\b(?:volledig |totally |completely )?(apolitiek|apolitisch|apolítico|apolítica|apolitico|apolitica)\b",
         lambda match: POLITICS.get(match.group(1) or match.group(2)) or {"left": "progressive or liberal", "right": "conservative or right", "trump": "conservative or right", "republican": "conservative or right", "gop": "conservative or right"}.get(match.group(3) or match.group(4) or "", "apolitical" if match.group(5) else "conservative or right" if "maga" in match.group() or "trump" in match.group() else "progressive or liberal"), SELF_HEDGE),
    rule("political_identity", rf"\bas an? (?:\w+ )?({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?)\b)", group(POLITICS)),
    rule("political_identity", rf"(?:^|[.!?,;(] *)({PARTY}) here\b|\bfellow ({PARTY})s?\b", lambda match: POLITICS[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("political_identity", r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly on|solidly on|squarely on|also on)[*_]* the [*_]*(?:far[- ])?(left|right)\b(?! (?:track|path|side of|page|way|foot|direction|answer|thing|one|place|time|hand|lane|side of history)\b)|\b(?:i'm|im|i am|i m) (?:pretty |very |far |more |center |centre |a |fairly |quite )?(left[- ]wing|right[- ]wing|left[- ]leaning|right[- ]leaning|leftist|lefty|far[- ]left|far[- ]right|center[- ]left|centre[- ]left|center[- ]right|centre[- ]right)\b",
         lambda match: "socialist or left" if "left" in (match.group(1) or match.group(2)) or "lefty" in (match.group(1) or match.group(2)) else "conservative or right", SELF_HEDGE),
]

DIETS = {"vegan": "vegan", "vegetarian": "vegetarian", "veggie": "vegetarian", "pescatarian": "pescatarian", "pescetarian": "pescatarian", "keto": "keto or low carb",
         "halal": "halal or kosher", "kosher": "halal or kosher", "gluten free": "gluten free", "gluten-free": "gluten free"}
DIET = [
    rule("diet", rf"\b{I} (?:a |an |also a |also |a strict |fully |mostly |now )?(vegan|vegetarian|veggie|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)", group(DIETS)),
    rule("diet", r"\bas an? (vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)", group(DIETS)),
    rule("diet", r"\bwe(?:'re| are) (?:all |both |also |strictly )?(vegan|vegetarian|pescatarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly)\b)|\b(?:soy|sou|sono|ich bin|ik ben) (vegan[oa]?|vegetarian[oa]|vegetarisch|vegetarier(?:in)?|vegetariër|veganer(?:in)?)\b"
         r"|\bje suis (végane?|végétarien(?:ne)?|vegan)\b|\bjestem (weganką|weganinem|wegetarianką|wegetarianinem)\b", lambda match: DIETS.get(word := next(filter(None, match.groups()))) or ("vegetarian" if "tar" in word else "vegan"), SELF_HEDGE),
    rule("diet", r"\bi(?:'m| am)? (?:a )?(?:celiac|coeliac)\b|\bmy (?:celiac|coeliac)\b|\bi (?:eat|am|'m|have to (?:eat|be|stay)|keep|went|stay) (?:strictly |completely |100% )?gluten[- ]free\b|\bthe gf diet\b", fixed("gluten free"), SELF_HEDGE),
    rule("diet", r"\bi (?:eat|keep|only eat|stick to|stick with|have to stick with|follow) (?:strictly )?(halal|kosher)\b|\bi(?:'m| am) (?:on |doing )?(?:a |strict )?(keto)\b(?! (?:friendly|recipe))|\bi (?:do|eat|follow|went) (keto|low[- ]carb)\b",
         lambda match: "halal or kosher" if match.group(1) else "keto or low carb", SELF_HEDGE),
    rule("diet", r"\bi (?:don't|do not|dont) eat (meat|any meat|animal products)\b|\bi(?:'m| am) (?:fully |mostly |\d+% )?(plant[- ]based)\b|\bi eat (plant[- ]based)\b", lambda match: "vegetarian" if "meat" in match.group() else "vegan", SELF_HEDGE),
    rule("diet", r"\bi (?:eat|love) meat\b|\bi'?m a (?:meat eater|carnivore|omnivore)\b", fixed("eats everything")),
    rule("diet", r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian) here\b|\b(?:i've been|i went|been|went|i became|i turned) (vegan|vegetarian|pescatarian)\b", lambda match: DIETS[match.group(1) or match.group(2)], SELF_HEDGE),
]

SMOKING = [
    rule("smoking", r"\bi (?:smoke|vape)(?: cigarettes| cigs| a pack| daily| every day)?\b(?! (?:meat|out|detector|alarm)\b)|\b(?:i'm|im|i am|as) a (?:\w+ )?(?:weed |pot )?smoker\b|\bneed to smoke\b|\bi(?:'m| am)? (?:\w+ ){0,2}(?:buying|buy|bought|hitting|hit) (?:a |my )?(?:disposable |nic |nicotine )?(?:vape|juul|cigs|cigarettes|pack of (?:cigs|cigarettes|smokes))\b|\b(?:i'm|im|i am) a (?:heavy |chain |social )?smoker\b|\bas a smoker\b|\bmy (?:vape|cigarettes)\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\b(?:i |i've |i have )?(?:haven't|have not|havent) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b|\b(?:i |since i |after i |when i )(?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|\bi(?:'ve| have)? never smoked\b"
         r"|\b(?:days?|weeks?|months?|years?) (?:smoke|nicotine|vape|cigarette)[- ]free\b|\b(?:days?|weeks?|months?|years?) (?:without|off) (?:smoking|vaping|nicotine|cigarettes)\b|\b(?:days?|weeks?|months?) after (?:vaping|smoking) (?:since|for)\b", fixed("non-smoker"), SELF_HEDGE),
    rule("smoking", r"\bi (?:don't|do not|dont|never) smoke\b|\bi quit smoking\b|\bi used to (?:smoke|vape)\b|\b(?:i'm|im|i am) a non-?smoker\b|\bi've never smoked\b", fixed("non-smoker"), CONDITIONAL),
    rule("smoking", r"\b(?:i|me) (?:\w+ )?(?:smoke|smoked|vape|vaped) (?:for|to|after|before|when|every|a|cigarettes|cigs|daily)\b|\bmy (?:cigarettes?|cigs|vape|juul|pack of (?:cigs|cigarettes|smokes)|smoke break|cigarette break)\b|\b(?:i'm|im|i am) a (?:heavy |chain |social |casual )?(?:smoker|vaper)\b"
         r"|\bi(?:'ve| have) been (?:smoking|vaping) (?:for|since)\b|\bi smoke (?:a|\d+|two) packs?\b|\b420[- ]friendly\b|\bi (?:\w+ )?(?:drink|drink socially) and smoke\b|\bi (?:\w+ )?smoke and drink\b|\bich rauche\b|\bwir rauchen\b|\brauchen den\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\bnon[- ]?smoker\b|\b(?:i|we) don'?t smoke\b", fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
    rule("smoking", r"\b(?:i'm|im|i am|as|signed,?|i've been) (?:a |an )?(?:[\w-]+ ){0,2}?(?:smoker|vaper|stoner|pothead)\b", lambda match: None if "non" in match.group() else "smoker or vaper", SELF_HEDGE),
    rule("smoking", r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a few|several) (?:days?|weeks?|months?|years?)\W{0,8}(?:after|since|off|without|free from|clean from|of not) (?:vaping|smoking|nicotine|cigarettes|cigs|the vape|juul|tobacco)\b"
         r"|\bi(?:'ve| have)? (?:finally |officially |just )?(?:quit|stopped|given up|kicked) (?:the )?(?:vape|vaping|juul|cigarettes|cigs|nicotine|smoking|tobacco)\b", fixed("non-smoker"), SELF_HEDGE),
    rule("smoking", r"\bi (?:(?!don't|dont|do not|don|never|wouldn't|won't|can't|cannot|used|stopped|quit|need|needed|had|did|would|could|should|might|may|want|wanted|wanna|gonna|going|tried|try)[\w']+ ){1,2}(?:smoke|vape)\b(?! (?:meat|out|detector|alarm|free|ribs|brisket|fish|salmon|turkey|pork|chicken|signals?|bombs?|screen|machine)\b)"
         r"|\b(?:i'm|im|i am) (?:just |currently |still |now |literally |also )?(?:smoking|vaping)\b(?! (?:meat|ribs|brisket|out|hot|fish|salmon|turkey|pork|chicken)\b)|\bi (?:enjoy|love|like) (?:smoking|vaping)\b(?! (?:meat|ribs|brisket|fish|salmon|turkey|pork|chicken)\b)",
         fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\bi (?:don't|do not|dont|don) (?:drink|do drugs|party)(?:,? (?:or |and |nor )?(?:drink|do drugs|party))*,? (?:or |and |nor )?(?:smoke|vape)\b|\bnot a (?:drinker or (?:a )?)?smoker\b|\b(?:i|we)(?:'re| are|'m| am) (?:both )?(?:[\w&]+, )*non-?smokers?\b",
         fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
]

SERVICE = re.compile(r"\b(?:army|navy|marines?|military|usmc|air force|national guard|coast guard|deploy\w*|enlist\w*|veterans?|va|dd-?214|gi bill|mos|ets|boot ?camp|basic training|base|platoon|squadron|battalion|nco|sergeant|sgt|corporal|cpl|soldiers?|sailors?|airmen|servicemembers?|iraq|afghanistan|vietnam|served)\b")
MILITARY = [
    rule("military_status", rf"(?P<serving>\b{I} (?:currently |still )?(?:in|serving in|enlisted in) the (?:army|navy|marines|air force|military|national guard|coast guard|marine corps|reserves|space force)\b|\b{I} (?:on )?active duty\b|\b{I} (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service ?member|infantryman|paratrooper)\b|\b{I} (?:currently )?(?:deployed|stationed)\b|\bmy (?:unit|platoon|squadron|battalion|deployment|chain of command|first sergeant|drill sergeant|commanding officer|nco|squad leader)\b)"
         rf"|(?P<veteran>\b{I} (?:a |an )?(?:former|retired|ex[- ]?) ?(?:soldier|marine|sailor|airman|service ?member|military|army|navy|paratrooper|infantryman)\b|\bmy (?:time|years|service) in the (?:army|navy|military|marines|corps|marine corps|service|air force|national guard)\b|\bi(?:'m| am) prior service\b"
         rf"|\b(?:{I}|as) (?:a |an )?(?:proud |disabled |combat |retired |former |old )?(?:(?:army|navy|marine|marine corps|air force|military|usmc|combat|iraq|afghanistan|war|coast guard) )?(?:vet|veteran)\b(?! (?:tech|clinic|bill|school|student|player|gamer|member|user|fan|raider|streamer|poster|of (?:the|this))\b)|\bwhen i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|\bi (?:served|was) (?:\w+ )?in the (?:forces|raf|royal navy|royal marines|idf|army|navy|marines|air force|military|coast guard|marine corps)\b|\bi served (?:my country|\d+ years|overseas|(?:two|three|four|\d) tours)\b|\bi (?:got out of|retired from|separated from) the (?:army|navy|marines|air force|military|service)\b|\b(?:army|navy|military|marine|air force|usmc|coast guard) retiree\b|\b\d{{2,3}} ?% (?:p&t|sc|service[- ]connected)\b|\bretired (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force|military|usmc)\b"
         r"|(?:\bmy|\bi(?:'ve| have| was| got| am|'m)?)\b[^.!?\n]{0,40}?\b(?:va claim|va rating|va disability|dd-?214|c&p exam|nexus letter|service[- ]connected|100% p&t)\b)",
         lambda match: "serving in the military" if match.group("serving") else "military veteran", SELF_HEDGE),
    rule("military_status", rf"\b{I} (?:(?!on |at |my |so |to |no |in |an )[a-z]{{2}} |army |air )?(?:national )?guard(?:sman|swoman)?\b(?! (?:duty at|dog)\b)|\b{I} (?:a |an )?(?:reservist|guardsman|guardswoman)\b|\b{I} (?:in|with) the (?:\w+ )?(?:reserves?|guard)\b",
         fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", r"\bmy (?:va |disability |combined |current )?(?:rating|claim|c&p|dbq|vso|gi bill|tricare|dd-?214|va benefits|va healthcare|va doctor|va appointment|pact act)\b",
         lambda match: "military veteran" if re.search(r"\b(?:va|veterans?|military|service|army|navy|marines?|air force|usmc|vso|dbq|c&p)\b", match.string) else None, SELF_HEDGE),
    rule("military_status", rf"\b{I} (?:a |an )?(?:\w+ )?(?:officer|medic|nco|sergeant|corporal|private|specialist|pilot|mechanic|engineer|nurse|soldier|infantryman|linguist|analyst|doctor|chaplain) in the (?:army|navy|marines|air force|military|national guard|coast guard|reserves?|space force)\b",
         fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", rf"\bi (?:\w+ )?served (?:\w+ )?(?:in (?:iraq|afghanistan|vietnam|korea|kuwait|the gulf|desert storm|combat|bosnia|kosovo|syria)|overseas|(?:\d+|two|three|four|five|six|eight|ten|twenty) (?:years|yrs|tours)|my (?:time|country|contract|enlistment))\b"
         r"|\bfellow (?:veterans|vets|servicemembers|service members)\b"
         r"|\b(?:after|since|when|before|once) (?:i )?(?:got out|getting out|ets(?:'d|ed)?|i separated|separating|i was discharged)\b|\b(?:my|i did|i've done|i have done|i had) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b|\b\d+ deployments\b"
         rf"|\b(?:i'm|im|i am) (?:using|running|on) (?:the |my )?(?:gi bill|post[- ]9/11)\b|\bi (?:used|use) (?:the |my )?gi bill\b|\b{I} (?:a |an )?(?:[\w-]+ ){{1,3}}(?:and )?(?:a )?(?:war|combat|army|navy|marine|air force|military|disabled|retired|iraq|afghanistan|vietnam|gulf war|coast guard) (?:vet|veteran)\b"
         r"|\bi (?:was|spent) (?:\w+ ){1,3}in the (?:army|navy|marines|air force|military|coast guard|marine corps|national guard)\b", lambda match: "military veteran" if SERVICE.search(match.string) else None, SELF_HEDGE),
]

RULES = [*RELATIONSHIP, *PARENTAL, *scoped_rules(PETS), *scoped_rules(LIVING), *HOUSING, *scoped_rules(RELIGION), *scoped_rules(POLITICAL), *scoped_rules(DIET), *scoped_rules(SMOKING), *scoped_rules(MILITARY)]
