import re
from pathlib import Path

from .common import HEDGE, SELF_HEDGE, TAGGED, clause, fixed, group, needs, rule

ME = r"i(?<!\wi)(?:'m|m| am|am| m|'am|'?ve been|'ve always been)"
NEAR = re.compile(r"\b(?:be|become|becoming|imagine|pretend|roleplay|rp|future|someday|dream|wish|if i (?:ever )?(?:had|have|get|got|find)|when i (?:have|get|find))[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
SCOPED = re.compile(r"\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
STATED = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once|used to|when i was|back when|no longer|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
FUTURE = re.compile(r"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|until|once|when|someday|one day|would|want to|wanna|hope to|plan to|planning to|used to|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$")
CONDITIONAL = re.compile(r"\b(?:if|would|wish)\b")
AS = (r"as(?:(?<=^as)|(?<=[\n.!?,;:(\"*\[\]-]as)|(?<=[\n.!?,;:(\"*\[\]-] as)|(?<=[\n.!?,;:(\"*\[\]-]  as)|(?<=\band as)|(?<=\bbut as)|(?<=\bso as)|(?<=\bme as)|(?<=\bmyself as)|(?<=\bthat as)|(?<=\bthis as)"
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
MARRIED, DATING, ENGAGED = "married", "dating or in a relationship", "engaged"
SPOUSES = {"wife": MARRIED, "husband": MARRIED, "hubby": MARRIED, "wifey": MARRIED, "spouse": MARRIED, "missus": MARRIED, "mrs": MARRIED, "hubs": MARRIED, "wifes": MARRIED,
           "husbands": MARRIED, "girlfriend": DATING, "boyfriend": DATING, "gf": DATING, "bf": DATING, "partner": DATING, "significant other": DATING, "misses": MARRIED,
           "fiance": ENGAGED, "fiancé": ENGAGED, "fiancee": ENGAGED, "fiancée": ENGAGED, "jowa": DATING}
SPOUSE = r"(wife|husband|hubby|wifey|spouse|wifes|husbands|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)"
STATUSES = {"single": "single", "married": MARRIED, "engaged": ENGAGED, "divorced": "divorced", "separated": "separated", "widowed": "widowed", "a widow": "widowed",
            "a widower": "widowed", "in a relationship": DATING, "taken": DATING, "unmarried": "single", "not married": "single", "attached": DATING, "partnered": DATING,
            "verheiratet": MARRIED, "vergeben": DATING, "geschieden": "divorced", "marié": MARRIED, "mariée": MARRIED, "divorcé": "divorced", "divorcée": "divorced", "casado": MARRIED, "casada": MARRIED,
            "divorciado": "divorced", "divorciada": "divorced", "sposato": MARRIED, "sposata": MARRIED, "getrouwd": MARRIED, "gescheiden": "divorced"}
BARE = r"(wife|wifey|hubby|husband|fianc[ée]e?|spouse|missus)"
LEAD = rf"(?:{ME} (?:a |an )?|\bas an? |\b\d{{2}}\s*(?:[mf]|yo|y/o|years? old)?\b\W*(?:and )?|\b[mf]\s?\d{{2}}\b\W*(?:and )?)"
OPENING = r"(?:^\W*|[\n.!?]\s*|[\]\)]\s*|[-|:]\s+)"
TAIL = (r"(?! (?:to (?:the|this|that|it|my (?:job|work|career))|by|about|in terms|aback|care|seriously|advantage|in (?:a|an|the|this|that|it|some|conversation|discussion|debate|activities|activity|work)|handedly|digit|file|minded|out|away|back|off|over|up|"
        r"with (?:the|this|that|it|work))\b)")
KIN = r"(?:brother|sister|son|daughter|dad|mom|mum|father|mother|cousin|friend|friends|uncle|aunt|boss|neighbou?r|roommate|buddy|bro|sis|ex|former|future|dream|next|last|previous|first|late|dead|imaginary|fake|virtual|ai|old|then|best|own)"
FOLLOW = (r"(?=\s*(?:[.,!;:)(/\n]|$|\d|[mf]\s?\d{2}\b|(?:and|but|with|for|since|in|here|now|again|too|af|m|f|male|female|man|woman|guy|girl|gal|lady|dude|mom|mum|mother|dad|father|parent|bbw|milf|dilf|couple)\b"
          r"|\w+ (?:with|and|from|in|looking|seeking|here|male|female|man|woman|guy|girl|mom|dad)\b))")


THIRD = re.compile(r"\b(?:he|she|they|you|u|his|her|their|your|ur)\b")
COUPLED = re.compile(r"\b(?:married|wife|husband|hubby|hotwife)\b")
PAIRED = re.compile(r"\b(?:couple|we|our)\b")
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


def sentence(match):
    ends = [found for found in (match.string.find(mark, match.end()) for mark in ".!?\n") if found >= 0]
    return max(match.string.rfind(mark, 0, match.start()) for mark in ".!?\n") + 1, min(ends, default=len(match.string))


def mine(match):
    return bool(SELF.search(match.string, *bounds(match)))


def couple(match):
    return None if COUPLED.search(match.string) or not PAIRED.search(match.string) or not spoken(match) else DATING


OTHERS = re.compile(r"(?:^|\W)(?:your|ur|her|his|their|a|an|some|someone's|whose|ex|future|dream|trophy|of|another|every|any|no|perfect|ideal|ex-|good|loyal|cuck|friends?|friend's)\W*$")
YOU = re.compile(r"\byou\b")


def bare(match):
    return None if not SELF.search(match.string) or YOU.search(match.string, max(0, match.start() - 60), match.start()) or OTHERS.search(match.string, max(0, match.start() - 14), match.start()) else kept(MARRIED)(match)


ATTACHED = re.compile(r"\b(?:married|wife|husband|hubby|my bf|my gf|my boyfriend|my girlfriend|my partner|couple|taken|engaged)\b")


def seeking(match):
    return None if ATTACHED.search(match.string) else stated(fixed("single"), FUTURE)(match)


SOLO_AD = r"^\W*(?:(?:\d{2}\s*[\]\)]?\s*)?[\[\(]?\s*(?:m|f|t|nb|tm|tf|mtf|ftm)\s*4\s*(?:[mfatr]|me|nb)\w*\s*[\]\)]?|\d{2}\s*(?:[mf]|yo|y/o|yrs?|years? old)\b|[mf]\s*\d{2}\b)"
HEAD = re.compile(r"\s*[^\n]*(?:\n\s*[^\n]*)?")
SOLICIT = re.compile(r"\b(?:looking for|seeking|searching for|in search of)\b")
FRIENDLY = re.compile(r"\b(?:friends?|friendship|frds?|bros?|buddy|buddies|pals?|penpals?|talk|chat|chatting|game|gaming|vent)\b")


def soliciting(match):
    head = HEAD.match(match.string).end()
    return None if ATTACHED.search(match.string) or COUPLED.search(match.string) or PAIRED.search(match.string, 0, head) or WRITING.search(match.string) or not SOLICIT.search(match.string, 0, head) or FRIENDLY.search(match.string, 0, head) else "single"


def partnered(match):
    return None if match.group(1) == "partner" and WRITING.search(match.string) else owned(SPOUSES)(match)


LEAD_STATUS = (rf"(?:recently |newly |happily |also |still |currently |now |not |un)?(single\b{FOLLOW}|(?:taken|attached)\b{FOLLOW}|married|divorced|separated|widowed|engaged)\b(?! (?:men|women|people|guys|girls|moms|dads|mothers|fathers|parents|couples|folks|life|ladies|ones|friends|or|vs|status|sex|player|file|use|cock)\b)(?!-){TAIL}")


BARE_TAIL = (rf"(?:(?:re)?post\W*|update\W*)?(?:{FOND}\s+){{0,3}}{BARE}(?:'s)?\b"
             r"(?=\s*(?:\(|\d{2}|[.,!](?!\w))|\s+(?!(?:wanted|needed|material|for|search|hunt|swap|request|appreciation|experience|goals|vibes|energy|wanna|of|or|vs|who|that|culture|beaters?|pics?|photos?|share|sharing)\b)[a-z])")


def bare_spouse(match):
    return owned(SPOUSES)(match) if mine(match) else None


def lead_status(match):
    return None if SCOPED.search(match.string, max(0, match.start() - 30), match.start()) else "single" if re.search(r"(?:not |un)married", match.group()) else None if "not " in match.group() else STATUSES[match.group(1)]


COUPLE_ADS = (r"^\W*(?:(?:\d{2}\s*(?:[mf]\s*)?(?:/\s*\d{2}\s*(?:[mf]\s*)?)?)?[\[\(]?\s*(?:mf|fm)\s*4\s*[mfat]\w*|(?:\d{2}\s*)?[\[\(]?\s*mf\s*\d{2}\b|(?:(?!the |a |this |that |every |each |any |no )\w+ )?couple (?:looking|seeking|here|from|in|\d{2})\b)",
              r"^\W*[\[\(]?(?:\d{2}\s*[mf]|[mf]\s*\d{2})\s*[/&+,]?\s*(?:\d{2}\s*[mf]|[mf]\s*\d{2})\b|^\W*(?:(?!the |a |this |that |every |each |any |no )\w+ )?couple (?:we|our)\b|^[^\n]*\b(?:mf|fm|m/f|f/m) couple (?:looking|seeking|here|from|in)\b",
              r"(?:couple(?<=\bcouple) here|we(?<=\bwe)(?:'re| are) an? (?:\w+ )?couple)\b(?! (?:of|days?|weeks?|months?|years?|hours?|minutes?|games?|more|points?|times?|steps?|levels?)\b)")


UNPARTNERED = re.compile(r"\b(?:wife|husband|hubby|my bf|my gf|my boyfriend|my girlfriend|my partner|engaged|fianc[ée]e?)\b")
NEVER_LEAD = re.compile(r"(?:^|[.!?\n,;(]|\band|\bbut|\bi|\bi've|\bi have|\bi'm|\bim|\bi am|\bstill)\s*$")
BREAK_LEAD = re.compile(r"(?:^|[.!?\n]\s*)(?:i )?(?:just |recently |finally )?$")


def unpartnered(match):
    text = match.group()
    lead = NEVER_LEAD if text.startswith("never") else BREAK_LEAD if text.startswith("broke up with") and not text.endswith(" me") else None
    if lead and not lead.search(match.string, max(0, match.start() - 24), match.start()):
        return None
    return "single" if spoken(match) and not UNPARTNERED.search(match.string, match.end()) else None


STATUS_LEAD = re.compile(r"(?:\b(?:as|being|i'm|im|i am|just|a fellow|as a fellow) an? |^\W*|[\n.!?]\s*|\b\d{2}\s*[mf]?\s*,?\s*|[\]\)]\s*)(?:(?!not|un|never|ex|former|soon|my|your|his|her|their|the|every|each|any|married)[\w-]+ ){0,2}$")


def status_person(match):
    if not STATUS_LEAD.search(match.string, max(0, match.start() - 60), match.start()) or THIRD.search(match.string, sentence(match)[0], match.start()):
        return None
    return stated(kept(STATUSES[match.group(1)]), FUTURE)(match)


RELATIONSHIP = [
    rule("relationship_status", rf"(?:my(?<=\bmy)|our(?<=\bour))\s*(?:\(\d{{2}} ?[mf]?\) ?)?(?:{FOND}[ ,]+){{0,3}}{SPOUSE}(?:'s)?\b(?![- ]?to[- ]be|(?:'s)? (?:in crime|at the time|back then|in (?:high school|college)|died|passed)\b|(?<=partner) (?:subreddits?|subs|communit(?:y|ies)|sites?|compan(?:y|ies)|organi[sz]ations?|programs?|brands?|channels?|servers?|stores?|shops?|schools?|agenc(?:y|ies)|networks?|pages?|firms?|businesses|universit(?:y|ies)|institutions?)\b)", partnered, TAGGED),
    rule("relationship_status", rf"(?:^|[\n.!?]\s*|\]\s*){BARE_TAIL}", bare_spouse, TAGGED),
    rule("relationship_status", rf"\b\d{{2}}\s*[mf]?\b\W*{BARE_TAIL}", bare_spouse, TAGGED),
    rule("relationship_status", rf"my (?<=\bmy )(?!{KIN}\b)(?!(?:business|lab|dance|tennis|study|writing|rp|gym|workout|sparring|accountability|training|climbing|golf|chess|duo|game|gaming|trading|research|project|work|running|hiking|language|practice|debate|doubles|play)\b)(?!x-)[a-z]+[ -](wife|husband|hubby|fianc[ée]e?|girlfriend|boyfriend|gf|bf|partner)\b(?!'s (?:friend|brother|sister|ex))", partnered, TAGGED),
    rule("relationship_status", rf"i (?<=\bi )(?:do |also |already |currently )?(?:have|got) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))", owned(SPOUSES), SELF_HEDGE),
    rule("relationship_status", r"\b(?:me and|and i|with|i and) the (wife|missus|mrs|hubby|wifey)\b|\bthe (wife|missus|mrs|hubby|wifey) and (?:i|me)\b|\bme (?:and|&) (?:my )?(hubby|wife|husband|missus|misses|mrs|wifey|hubs)\b", lambda match: SPOUSES.get(next(filter(None, match.groups()))) if free(match) else None, TAGGED),
    rule("relationship_status", r"(?<!')\b(?:mi|minha|meu|mon|ma|meine|mein|meiner|meinem|meinen|min|mijn|moja|mia|mio) (esposa|marido|esposo|mujer|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|hustru|ehemann|ehefrau|gatte|gattin|époux|épouse|echtgenoot|echtgenote|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|kjæreste|vriendin|vriend|partner|partnerin|pareja|compagnon|compagne|conjoint|conjointe|partenaire|compagno|compagna|ragazza|ragazzo|fidanzata|fidanzato|lebensgefährte|lebensgefährtin|sambo|flickvän|pojkvän|prometida|prometido|noiva|noivo|verlobte|verlobter|verloofde|fiancé|fiancée)\b",
         group({"esposa": MARRIED, "mujer": MARRIED, "marido": MARRIED, "esposo": MARRIED, "femme": MARRIED, "mari": MARRIED, "frau": MARRIED, "mann": MARRIED, "kone": MARRIED, "mand": MARRIED,
                "vrouw": MARRIED, "man": MARRIED, "żona": MARRIED, "moglie": MARRIED, "marito": MARRIED, "hustru": MARRIED, "ehemann": MARRIED, "ehefrau": MARRIED, "gatte": MARRIED, "gattin": MARRIED, "époux": MARRIED,
                "épouse": MARRIED, "echtgenoot": MARRIED, "echtgenote": MARRIED} | dict.fromkeys(("prometida", "prometido", "noiva", "noivo", "verlobte", "verlobter", "verloofde", "fiancé", "fiancée"), ENGAGED)
               | dict.fromkeys(("novia", "novio", "namorada", "namorado", "copine", "copain", "freundin", "freund", "kæreste", "kjæreste", "vriendin", "vriend", "partner", "partnerin", "pareja", "compagnon", "compagne", "conjoint",
                                "conjointe", "partenaire", "compagno", "compagna", "ragazza", "ragazzo", "fidanzata", "fidanzato", "lebensgefährte", "lebensgefährtin", "sambo", "flickvän", "pojkvän"), DATING)), TAGGED),
    rule("relationship_status", r"\b(?:мо[яейюи]\w*) (жен[аыеуой]\w*|муж\w*)|\bmo(?:j|ja|jego|jej|jemu|im|ją) (mąż|męża|mężem|mężowi|żony|żonie|żoną|żonę)\b|\b(eşim|karım|kocam(?!an))\w*"
         r"|\b(asawa|mister|misis) ko\b|\baking (asawa)\b|\bmer[ie] (wife|biwi|patni|husband|pati)\b|\b(istri|suami)(?:ku| saya| aku)\b|\bminha (mulher)\b"
         r"|\b(زوجتي|زوجي)|\b(אשתי|בעלי)(?! חיים)",
         fixed(MARRIED), TAGGED),
    rule("relationship_status", r"\b(?:my|our) (?:own |happy |long |current |second |strong |healthy |lovely |wonderful |great |good |sexless |open |\d+[- ]year )?marriage\b|\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|many|several) years (?:of marriage|married)\b"
         r"|\b(?:since|when|after|before) (?:we|i) got married\b|\b(?:we|i)(?:'ve| have) been (?:happily )?married\b(?! before)", fixed(MARRIED), SELF_HEDGE),
    rule("relationship_status", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\b(?:she|he) (?:left|dumped) me\b"
         r"|\bi broke up with (?:my|the|him|her)\b|\bwe (?:just |recently |finally |officially )?(?:broke up|broken up|split up)\b|\b(?:my|our) (?:\w+ )?(?:fianc[ée]e?|gf|bf|girlfriend|boyfriend|partner) and i (?:just |recently |finally )?(?:broke up|split up|split|separated|called it quits)\b|\b(?:she|he) broke up with me\b|\bforever alone\b|\bbeen single (?:for|since)\b|\bterminei (?:o |meu )(?:namoro|relacionamento)\b|\bterminei com (?:o |meu )?(?:ex|namorad[oa])\b|\btermin[eé] (?:la|mi|una) relación\b|\bmi relación (?:de \d+ años )?terminó\b|\bterminé con mi (?:novi[oa]|pareja)\b|\bj'ai rompu avec\b|\b(?:i'm|im|i am) (?:a )?single (?:mom|mum|mother|dad|father|parent)\b", stated(fixed("single")), TAGGED),
    rule("relationship_status", rf"{ME} (?:happily |currently |still |also |newly |recently |now |officially |finally |legally )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|unmarried|not married)\b"
         rf"{TAIL}", scoped(STATUSES), TAGGED),
    rule("relationship_status", rf"(?<!every){LEAD}{LEAD_STATUS}", lead_status, TAGGED),
    rule("relationship_status", rf"(?<!every){OPENING}{LEAD_STATUS}", lead_status, TAGGED),
    rule("relationship_status", r"\b(?:i'm|im|i am|we're|we are|we've been|i've been|i have been|we have been) (?:happily |currently |exclusively |casually |now )?dating (?:for|since|someone|a |an |another|this|each other)\b"
         r"|\bi (?:have |'ve )?(?:recently |just |finally )?(?:entered|got into|started|began) (?:a |an )(?:new |serious |committed |long[- ]distance |relationship )?relationship\b", stated(kept(DATING), FUTURE), TAGGED),
    rule("relationship_status", rf"{ME} (?:\w+ )?in an? (?:[\w-]+ ){{1,2}}relationship\b(?! with (?:food|my (?:body|food|mom|dad|parents|family|job|work)|money|alcohol|god|jesus))", stated(fixed(DATING), FUTURE), TAGGED),
    rule("relationship_status", r"\b[mf]4[mfat]\w*\]?\s*(?:-\s*)?(?:\d{2}\s*)?(?:-\s*)?(single|married|divorced|separated|widowed|engaged|taken)\b|\b(?<![^,/|( ])(?<![^,/|(] )(married|divorced|separated|widowed|verheiratet|vergeben|geschieden|mariée?|divorcée?|casad[oa]|divorciad[oa]|sposat[oa]|getrouwd|gescheiden)\s*(?:[,/|)]|(?:and|et|und|y|e|en)\b)|\bmarital status\W*(single|married|divorced|separated|widowed|engaged)\b",
         lambda match: STATUSES.get(next(filter(None, match.groups()))) if free(match) else None, TAGGED),
    rule("relationship_status", r"\b(?:we(?:'re| are)|we got|we've been|now) (?:now |happily |both |finally |officially |just |recently )?married\b|\b(?:i'm|im|i am) (?:\w+ )?married to (?:a|an|my|the love|someone|him|her|\w+ (?:man|woman|guy|girl))\b", fixed(MARRIED), SCOPED),
    rule("relationship_status", r"\b(?:as|being|i'm|im|i am|we're|we are|just|a fellow|as a fellow) an? (?:(?!single|not|un|never|ex|former|soon)[\w-]+ ){0,2}married (?:man|guy|woman|lady|dad|mom|mum|father|mother|couple|person|male|female|gal|dude|bi|white|black|latina|latino|asian|professional|parent)\b"
         r"|\bfellow married (?:man|guy|woman|lady|dad|mom|mum|father|mother|person|parent)\b", stated(kept(MARRIED), FUTURE), TAGGED),
    rule("relationship_status", r"\bmy (?:ex[- ]?(?:wife|husband|hubby|spouse|husbands|wifes)|divorce)\b|\b(?:after|since|during|before|post|through|finalized) (?:my|our|the) divorce\b|\b(?:i|we) (?:got|were|are|'re|am|'m) (?:\w+ )?divorced\b|\b(?:recently|newly|twice) divorced\b|\bdivorcee\b",
         fixed("divorced"), SCOPED),
    rule("relationship_status", r"\b(?:recently|newly|happily|still|forever|freshly|blissfully|proudly|totally|currently) single\b|\b(?:i have|i've got|i got|i'm|im|with) no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|relationship|spouse|so)\b"
         r"|\b(?<![^,; ])(?<![^,;] )no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|spouse)\s*[,;&]|\b(?<!you )(?<!he )(?<!she )(?<!they )(?<!u )(?:don't|do not|dont) (?:currently |even |really )?have (?:a |an )?(?:girlfriend|boyfriend|gf|bf|partner|significant other|wife|husband|spouse)\b"
         r"|\b(?:у меня нет|я не) (?:сейчас )?(?:отношений|девушки|парня|жены|мужа|замужем|женат)", fixed("single"), CONDITIONAL),
    rule("relationship_status", r"\b(?:estoy|soy) (?:felizmente |recién |recien |ya |también |tambien |todavía |todavia |aún |aun )?(casad[oa]|solter[oa]|divorciad[oa]|comprometid[oa]|separad[oa]|viud[oa])\b|\bestoy (?:en una relación|de novi[oa])\b|\b(?:sou|estou) (?:felizmente |recém |recem |já |ja |também |tambem |ainda )?(casad[oa]|solteir[oa]|divorciad[oa]|noiv[oa]|separad[oa]|viúv[oa]|viuv[oa])\b|\bestou (?:numa|em uma) relação\b"
         r"|\b(?:ich|und|aber) bin (?:glücklich |auch |schon |noch |wieder |jetzt |mittlerweile |inzwischen |frisch |seit \w+ (?:jahren|monaten) )?(verheiratet|single|ledig|geschieden|verlobt|vergeben|verwitwet)\b|\bje suis (?:heureusement |aussi |déjà |toujours |encore |actuellement |maintenant )?(mariée?|célibataire|divorcée?|fiancée?|en couple|pacsée?|séparée?|veuve|veuf)\b|\bsono (?:felicemente |già |anche |ancora )?(sposat[oa]|single|fidanzat[oa]|divorziat[oa]|separat[oa]|vedov[oa])\b"
         r"|\bjestem (żonaty|zamężna|mężatką|singlem|singielką|rozwiedzion[ya]|zaręczon[ya]|w związku)\b|\bik ben (?:al |ook |nog |gelukkig )?(getrouwd|single|vrijgezel|gescheiden|verloofd)\b|\b(?:jeg er|jag är) (?:også |också |lykkeligt |lyckligt |nu )?(gift|single|singel|skilt|skild|forlovet|förlovad)\b|\bя (женат|замужем|холост|разведен[а]?|в отношениях)\b|\b(?:انا|أنا) (متزوج)",
         lambda match: {"casad": MARRIED, "solte": "single", "divor": "divorced", "compr": ENGAGED, "noiv": ENGAGED, "noiva": ENGAGED, "noivo": ENGAGED, "verhe": MARRIED, "singl": "single", "ledig": "single", "gesch": "divorced", "verlo": ENGAGED,
                        "verge": DATING, "marié": MARRIED, "célib": "single", "fianc": ENGAGED, "en co": DATING, "sposa": MARRIED, "fidan": DATING, "żonat": MARRIED, "zamęż": MARRIED, "mężat": MARRIED,
                        "rozwi": "divorced", "zaręc": ENGAGED, "w zwi": DATING, "getro": MARRIED, "vrijg": "single", "женат": MARRIED, "замуж": MARRIED, "холос": "single", "разве": "divorced", "в отн": DATING,
                        "separ": "separated", "sépar": "separated", "viuda": "widowed", "viudo": "widowed", "viúva": "widowed", "viúvo": "widowed", "viuva": "widowed", "viuvo": "widowed", "verwi": "widowed", "pacsé": DATING,
                        "veuve": "widowed", "veuf": "widowed", "vedov": "widowed", "gift": MARRIED, "singe": "single", "skilt": "divorced", "skild": "divorced", "forlo": ENGAGED, "förlo": ENGAGED, "متزوج": MARRIED}.get(
             (next(filter(None, match.groups()), None) or match.group().split(" ", 2)[-1])[:5], DATING), SCOPED),
    rule("relationship_status", r"\b(?:i|we) (?:just |recently |finally )?got (married|engaged|divorced)\b|\b(married) (?:for )?(?:\d+|a few|many|almost|over|nearly|about) (?:\w+ )?years\b",
         lambda match: {"married": MARRIED, "engaged": ENGAGED, "divorced": "divorced"}[next(filter(None, match.groups()))]),
    rule("relationship_status", r"\bmy late (?:wife|husband|hubby|spouse|partner)\b|\b(?:i lost|since i lost|after i lost|after losing|since losing) my (?:wife|husband|hubby|spouse)\b|\bmy (?:wife|husband|hubby|spouse) (?:passed away|died|passed)\b", stated(fixed("widowed")), TAGGED),
    rule("relationship_status", r"\bmy (?:estranged|separated) (?:wife|husband|hubby|spouse)\b|\bmy (?:stbx\w*|soon[- ]to[- ]be[- ]ex(?:[- ]\w+)?)\b|\b(?:we're|we are|we've been|we have been|we recently|we just) (?:\w+ )?separated\b", stated(fixed("separated")), TAGGED),
    rule("relationship_status", r"(?:^\W*(?:\d{2}\s*)?(?:[\[\(]\w+[\]\)]\s*)?(?:(?!he |she |they |you |who |we |got |get |not |never |was |were |be |been |is |are |any |only |all )\w+ )?married\b(?! (?:men|women|people|guys|couples|folks|life|cock|or)\b))", kept(MARRIED), TAGGED),
    *(rule("relationship_status", pattern, couple, TAGGED) for pattern in COUPLE_ADS),
    rule("relationship_status", r"\b(gf|bf|boyfriend|girlfriend|jowa|partner) ko\b", owned(SPOUSES), TAGGED),
    rule("relationship_status", r"my (?<=\bmy )(?:current |new |\d+[- ](?:year|month)[- ]?(?:old )?|long[- ]distance |long[- ]term )?relationship\b(?! (?:with (?!(?:my )?(?:bf|gf|boyfriend|girlfriend|partner|husband|wife)\b)|status|history|goals|life|skills|issues|anxiety|advice|problems? with|coach)\b)", lambda match: None if ENDED.search(match.string) or BROKEN.search(match.string) or COUPLED.search(match.string) else stated(kept(DATING), FUTURE)(match), TAGGED),
    rule("relationship_status", r"\bi(?:'ve| have)? never (?:had|been in) (?:a |an )?(?:real |serious |proper |actual )?(?:girlfriend|boyfriend|gf|bf|relationship|partner)\b|\bi(?:'ve| have)? never (?:dated|been on a date|been kissed)\b"
         r"|\b(?:ich|hab|habe|hatte) (?:(?!er |sie |du |ihr |es )\S+ ){0,4}?(?:noch nie|noch keine|nie) (?:im leben )?(?:eine )?(?:freundin|beziehung)\b|\bnunca (?:he )?(?:tuve|tenido) (?:novi[oa]|pareja)\b|\bnunca tive (?:namorad[oa]|relacionamento)\b|\bjamais eu de (?:copine|copain|petite amie|petit ami)\b", seeking, TAGGED),
    rule("relationship_status", r"\bmy (?:\w+ )?(?:gf|bf|girlfriend|boyfriend|fianc[ée]e?|partner) (?:of \w+ (?:years?|months?) )?(?:just |recently |finally )?(?:broke up with|dumped|left|ghosted) me\b|\b(?:i|i just|i recently) got dumped\b", stated(fixed("single")), TAGGED),
    rule("relationship_status", r"looking for (?<=\blooking for )(?:a |an |my )?(?:\w+ )?(?:ltr|long[- ]term relationship|relationship|girlfriend|boyfriend|gf|bf|wife|husband|soulmate|life partner)\b", seeking, SELF_HEDGE),
    rule("relationship_status", SOLO_AD, soliciting, TAGGED),
    rule("relationship_status", r"hub(?<![\w'-]hub)(?:by|bie)(?:'s)?(?![\w'-])(?! material| hole)|hubs and i\b", bare, SELF_HEDGE),
    needs(rule("relationship_status", r"never (?<=\bnever )(?:been )?(?:married|dated)\b(?! (?:a|an|the|someone|anyone|him|her|them|my|your)\b)|broke up (?<=\bbroke up )w(?:ith (?:my|him|her)\b|(?:/|ith)? me\b)|(?:my(?<=\bmy)|our(?<=\bour)) (?:\w+ )?(?:gf|bf|girlfriend|boyfriend|partner|fianc[ée]e?) (?:of \w+ (?:years?|months?) )?(?:breaking up with|leaving|dumping) me\b",
         unpartnered, TAGGED), "never", "broke up", "breaking up", "leaving me", "dumping me"),
    needs(rule("relationship_status", r"\b(?:the |this )?(?:woman|man|girl|guy|person|lady|someone|gal|dude) (?:that |who )?(?:i'm|im|i am|i've been|i have been) (?:currently |now |casually )?(?:dating|seeing)\b",
         lambda match: None if ENDED.search(match.string) or BROKEN.search(match.string) else stated(kept(DATING), FUTURE)(match), TAGGED), "dating", "seeing"),
    needs(rule("relationship_status", r"\b(?:me and|me & ) my (?:man|girl|guy|woman|lady|boo|bae)\b|\bmy (?:man|girl|guy|woman|lady|boo|bae) (?:and|&) i\b", lambda match: None if BROKEN.search(match.string) else kept(DATING)(match), TAGGED), "me and", "me & ", " and i", " & i"),
    needs(rule("relationship_status", r"(?:(?<=\w) ?\(|(?<=[\w)\]]),)\s*single\b(?=\s*[),.]|\s+and\b)", lambda match: None if ATTACHED.search(match.string) or THIRD.search(match.string, sentence(match)[0], match.start()) else kept("single")(match), TAGGED), "single"),
    needs(rule("relationship_status", r"\bmy (?!future |soon )(?:\w+ )ex[- ]?(?:wife|husband|hubby|spouse)\b", lambda match: "divorced" if spoken(match) else None, TAGGED), "ex"),
    needs(rule("relationship_status", r"\b(?:i'm|im|i am) (?:already|just|actually|technically|currently|recently|newly|happily|so|totally|definitely|very|completely|literally|basically) (engaged|separated|divorced|in a relationship|single)\b|\bmy (?:recent )?engagement\b(?! (?:ring|rings|photos?|party|shoot|announcement|ceremony)\b)", lambda match: stated(kept(STATUSES.get(match.group(1), ENGAGED)), FUTURE)(match), TAGGED), "engage", "separated", "divorced", "relationship", "single"),
    needs(rule("relationship_status", r"\b(single|divorced|separated|widowed) (?:man|guy|woman|lady|dad|mom|mum|father|mother|person|male|female|gal|dude|parent|mama|daddy|mommy)\b(?!s\b|'s\b)", status_person, TAGGED), "single", "divorced", "separated", "widowed"),
]

CHILD = (r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|"
         r"first ?born|lo|dc|dcs|bio kids|youngest|oldest|eldest|middle child|offspring|bairns?|sprogs?|tweens?|preteens?|pre-teens?|preschoolers?|kindergart(?:e)?ners?|(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth) graders?)")
AGE = r"(?:\d+|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks)?(?:[- ]old)?"
QUALIFIER = (rf"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|"
             r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)")
INFANT = re.compile(r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|crib|cot\b|formula|feeds?\b|feeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|bottle|sleep regression|stroller|pram|onesie|bassinet|car seat|"
                    r"kindergarten|preschool|school|daughter|son\b|mama|mommy|crawl|walking|talking|nap|\bborn\b|birth|pregnan|labou?r|deliver|milk|pump|nurs|ultrasound|\bob\b|\bweeks\b|\bmonths\b|teeth|tooth|\bcry|sleep")
PARENT_LEAD = re.compile(rf"(?:{ME} an? |\bas an? |\bbeing an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[\]\)]\s*|[-|:]\s+|\b[mf]4[mfat]\w*\s*)(?:(?!my |his |her |your |their |our |the |a )[\w,-]+ ){{0,3}}$")
ROMANTIC = re.compile(r"\b(?:bf|gf|boyfriend|girlfriend|husband|hubby|wife|daddy|sex|sexy|cock|dick|pussy|fuck\w*|kiss\w*|cuddl\w*|horny|nsfw|lover|honey|babe|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?)\b")
PAST = re.compile(r"\b(?:was|were|been)\s+(?:\w+\s+)?$")
YEARS = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
PRONOUN = re.compile(r"\b(?:he|she|him|her|his|they|them|their)\b")
NOT_CHILD = (r"(?:rescues?|fosters?|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|horses?|pony|birds?|cars?|trucks?|vans?|bikes?|house|home|laptop|computer|pc|phone|tv|account|self|body|brother|sister|cousin|nephew|niece|friend|student|students|"
             r"client|patient|boyfriend|girlfriend|bf|gf|husband|wife|grand\w*|mattress|bed|couch|boat|shoes|iphone|ipad|tablet|macbook|build|rig|tires?|battery|knees?|back|hips?)")


def aged(match):
    number, unit = match.group(1), match.group(2) or match.group(3)
    if unit.startswith(("y", "Y")) and number.isdigit() and int(number) > 17:
        return None
    return "has children" if free(match) and PRONOUN.search(match.string, match.end(), bounds(match)[1]) else None
FIRST = re.compile(r"\b(?:i|we)\b[^.!?\n]{0,40}$")
TEACHING = re.compile(r"\b(?:teach|teacher|class|classroom|students?|school|nanny|babysit\w*|camp|coach\w*|daycare|work)\b")
LISTED = re.compile(r"(?:^|[,;:]\s*|\b(?:single|married|divorced|no partner|no pets|no debt|\d{2}\s*[mf]?)\s*[,;&/]\s*(?:and )?)$")


BABY_LEAD = re.compile(r"(?:^|[.!?\n]\s*|\b(?:and|but|so|when|while|until|because|since|for|with|myself and|me and) )$")


def parenting(match):
    return kept("has children")(match) if BABY_LEAD.search(match.string, max(0, match.start() - 14), match.start()) and INFANT.search(match.string) and SELF.search(match.string) and not ROMANTIC.search(match.string) else None


ORDINAL = r"(?:first|second|third|fourth|1st|2nd|3rd|4th)"
NEGATED = re.compile(r"\b(?:no|não|nao|non) $")
PARENT_WORD = r"(?:mamá|mama|mãe|madre|padre|papá|pai|maman|mère|papa|père|mutter|vater|mamma|papà|moeder|vader|mor|far|pappa|matką|mamą|ojcem|tatą|familienvater|familienmutter)"
THINGS = re.compile(r"\b(?:dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?|horses?|birds?|fish|rabbits?|bunny|car|cars|truck|bike|phone|laptop|pc|build|tattoo|hair|order|package|account|plant|plants|vet|spay\w*|neuter\w*)\b")


BIRTH_VERB = re.compile(r" (?:was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b")
BIRTH_LEAD = re.compile(r"\b(?:had|have|with|after|since|before|for|from|than|during) $")


def birth_order(match):
    if not BIRTH_VERB.match(match.string, match.end()) and not BIRTH_LEAD.search(match.string, max(0, match.start() - 8), match.start()):
        return None
    return kept("has children")(match) if INFANT.search(match.string) and not ROMANTIC.search(match.string) and not THINGS.search(match.string) else None


AWAITED = re.compile(r"\b(?:to|wanna|until|till|before|once|planning on|plan on) (?:have|having)\s+$")
DUE = re.compile(r"(?:'s)? (?:is |was )?due\b")


def child(match):
    word = match.group(1)
    if not spoken(match) or AWAITED.search(match.string, max(0, match.start() - 24), match.start()) or DUE.match(match.string, match.end()):
        return None
    if word in ("baby", "babies", "bub", "bubba", "lo", "dc", "dcs") and not INFANT.search(match.string) and (word != "baby" or ROMANTIC.search(match.string)):
        return None
    if word == "teen" and not re.search(r"\d|year", match.group()):
        return None
    if word in ("youngest", "oldest", "eldest", "middle child") and re.match(r"\s*(?:brother|sister|sibling|cousin|friend|aunt|uncle|niece|nephew|grand|memor|and)", match.string[match.end():]):
        return None
    return "has children"


KID_NOUN = (r"(?:kids?|kiddos?|children|child|sons?|daughters?|toddlers?|teens|teenagers|newborn|infant|twins|triplets|stepkids|step-?sons?|step-?daughters?|grandkids|grandchildren|"
            r"(?:1[0-7]|[1-9]|one|two|three|four|five|six|seven|eight|nine|ten)(?:[.,]5| 1/2| and a half)?[- ]?(?:years?|yrs?|y/o|yo|months?|mos?|weeks?|wks?)[- ]?olds?)")
KID_COUNT = r"(?:(?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|my|our|several|multiple) )?"
KID_WORDS = r"(?:(?!(?:no|any|not|never|to|been|seen|met|heard|watched|known|taught|worked|told|asked|other|those|these|the|this|that|your|his|her|their|some|many|lots|plenty|more|enough|of|with|in|at|for|on|by|from|about|like|as|until|till|since|when|after|before|and|or|but|so|then|than)\b)(?![a-z]+ed\b)[a-z\d-]+ ){0,2}"
KID_AFTER = r"\b(?!'s|'| (?:of|in law|in-law|in (?:my|the|our|his|her|class|school)|at|who|that|from|come|came|ask|asked|tell|told|say|said|walk|walked|run|ran|on|over|when|someday|before|edition|dogs?|cats?|pups?|puppy|car|house|laptop|phone)\b)"
HAD_KIDS = re.compile(r"\b(?:you|u|he|she|they|who|people|parents|someone|her|him|his|their)\b")
LEADING = re.compile(r"(?:^|[.!?\n,;]\s*|\band |\bbut )(?:also |now |still |already )?$")


def raising(match):
    if not match.group().startswith(("i", "we")) and not LEADING.search(match.string, max(0, match.start() - 16), match.start()):
        return None
    return None if HAD_KIDS.search(match.string, sentence(match)[0], match.start()) else stated(kept("has children"), FUTURE)(match)


OTHERS_PARENT = re.compile(r"\b(?:my|his|her|their|your|our|the|whose|he|she|they|you)\b")


def parent_label(match):
    return None if OTHERS_PARENT.search(match.string, clause(match.string, match.start()), match.start()) else stated(kept("has children"), FUTURE)(match)


PARENTAL = [
    rule("parental_status", rf"(?:my (?<=\bmy )|our (?<=\bour ))(?:{QUALIFIER}[- ,]+){{0,3}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|cups?|tits|boobs|sister|brother|face|fever|shower)\b)", child, TAGGED),
    rule("parental_status", rf"\b(?:my|our) (?!(?:future|dream|unborn|imaginary|dog|cat|pup|puppy|fur|furry|kitty|bunny|plant|pet|god|ex|friends?|neighbou?rs?|sisters?|brothers?|cousins?|boyfriends?|girlfriends?|wife|husband|partner|aunt|uncle|boss|inner|little|baby|big|good)\b)[a-z]+ "
         rf"(?:{QUALIFIER}[- ,]+){{0,2}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|sister|brother|face|fever|shower)\b)",
         lambda match: None if match.group(1) in ("baby", "babies", "child") else child(match), TAGGED),
    rule("parental_status", r"the (?<=\bthe )(?:kids|kiddos|little ones?|toddler|twins|baby|babies|newborn)\b(?! (?:in|at|from|of|who|that|these|those|they|i|we|you)\b)",
         lambda match: kept("has children")(match) if FIRST.search(match.string, max(0, match.start() - 44), match.start()) and not TEACHING.search(match.string) else None, TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:twins|triplets|kids|children)\b(?! (?:of|in|at|who|that)\b)"
         r"|\bpregnant with (?:number|#|baby|no\.?) ?\d\b", lambda match: None if FUTURE.search(match.string, max(0, match.start() - 30), match.start()) else "expecting a child" if "pregnant" in match.group() else "has children", TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}"
         r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)",
         stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", rf"(?:{ME}|{AS}) (?:a|an) (?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b"
         r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))", stated(kept("has children"), FUTURE), TAGGED),
    needs(rule("parental_status", r"(?<!dog )(?<!cat )(?<!fur )(?<!pet )(?<!plant )\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", stated(kept("has children"), FUTURE), TAGGED), "mom", "mum", "mama", "mother", "dad", "father", "parent"),
    needs(rule("parental_status", r"\b(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|solo|widowed|separated|older|hot|bored|lonely|bi|pervy|horny|sexy|naughty|boy|girl|twin|homeschool(?:ing)?|toddler|teen|preemie|nicu|autism|special needs|military|working[- ]class) ?(?:dad|mom|mum|father|mother|mama|mommy|parent)\b(?!s| bod| jokes?| energy| vibes| groups?| friends?| life| figure)",
         lambda match: stated(kept("has children"), FUTURE)(match) if PARENT_LEAD.search(match.string, max(0, match.start() - 60), match.start()) else None, TAGGED), "dad", "mom", "mum", "father", "mother", "mama", "parent"),
    rule("parental_status", r"^\W*[\[\(]?(?:\d{2}\s*[mf]?|[mf]\s*\d{2})[\]\)]?\W*(?:(?!dog|cat|fur|plant|pet|bonus|step|soccer|hockey|boy|girl)\w+\s+){0,2}(?:mom|mum|mother|mommy|mama|dad|father)\b(?!s| bod| jeans| energy| vibes| jokes?)", kept("has children"), TAGGED),
    rule("parental_status", rf"\b\d{{2}}\s*[mf]?\s*,?\s*(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)|\bthe (?:kids|kiddos|children|twins|baby|little ones?) and (?:i|me)\b|\b(?:me|myself) (?:and|&) the (?:kids|kiddos|children|twins|baby|little ones?)\b|\bfellow (?:parent|mom|mum|dad|mother|father)s?\b|\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?(?:\d+ |two |three |four )?{CHILD}\b"
         rf"|\b(?<![^\n.!? ])(?<![^\n.!?] )(?:the )?(?:wife|husband|hubby) (?:and|&) (?:the )?(?:\d+ |two |three )?(?:kids?|children|sons?|daughters?|boys|girls)\b|\b(?:i (?:do |also |already )?have|i've got|we (?:do |also |already )?have) (?:a|an|one|two|three|\d) (?:1[0-7]|\d|one|two|three|four|five|six|seven|eight|nine|ten)(?!\d)(?: 1/2| and a half)?[- ]?(?:year|yr|month)s?[- ]?olds?\b(?! (?:dog|cat|pup|puppy|kitten|horse|car|house|laptop|computer|phone))",
         kept("has children"), TAGGED),
    rule("parental_status", rf"\b(?:my|our) (\d+|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?(yo|y/o|year[- ]old|yr[- ]old|month[- ]old|week[- ]old)s?(?= (?!(?:{NOT_CHILD})\b)[a-z]+\b|[.,!?;)])",
         lambda match: None if match.group(2).startswith("y") and match.group(1).isdigit() and int(match.group(1)) > 17 else kept("has children")(match), TAGGED),
    rule("parental_status", rf"my (?<=\bmy )(?:now[- ]|almost[- ]|nearly[- ]|just[- ]turned[- ])?{YEARS}[- ]?(?:(years?|yrs?|months?|weeks?|wks?)[- ]olds?|(yo|y/o|mo|mos|m/o))\b(?! (?:{NOT_CHILD})\b)", aged, TAGGED),
    rule("parental_status", r"\bno (?:kids|children)\b(?! (?:allowed|please|zone|menu|under|in|at|on|were|are|will))|\b(?:keine kinder|sin hijos|sem filhos|sans enfants?|geen kinderen|senza figli|ingen børn|inga barn)\b",
         lambda match: "no children" if LISTED.search(match.string, 0, match.start()) or re.match(r"(?:,| and|;) no\b", match.string[match.end():]) or SELF.search(match.string, max(0, match.start() - 40), match.start()) else None, CONDITIONAL),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |almost |nearly |only |just |about |officially )?\d{1,2}(?:\+\d)? ?(?:w|wks?|weeks?)(?: along| pregnant|(?: and)? \d ?d(?:ays?)?)?\b(?! (?:sober|clean|out|post|into|off|postpartum|in|of|until|from|ago|later|since|after|before|without|free|smoke|nicotine|vape))"
         r"|\b\d{1,2} ?(?:weeks?|wks?) along\b|\bwe(?:'re| are) (?:having|expecting) (?:a baby|twins|a boy|a girl|our (?:first|second|third|rainbow)|another|baby)\b|\bi(?:'m| am) having (?:a baby|twins|my (?:first|second|third) (?:baby|child))\b|\bmy (?:due date|anatomy scan|nipt|nt scan|gender reveal|baby shower|glucose test)\b",
         stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:meine?[nmrs]?|mein|unser\w*|mi|mis|mon|ma|mes|notre|nuestr[oa]s?|noss[oa]s?|onze|nostr[oaie]|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|mie|miei)\s+(?:(?!inner)\w+\s+)?(?:tochter|sohn|kinder|kindern|kind(?! of)|kids|söhne|söhnen|töchter|töchtern|hijo|hija|hijos|hijas|fils|fille|filles|enfants|enfant|filho|filha|filhos|filhas|zoon|zonen|dochter|dochters|kinderen|córka|syn|dzieci|figlio|figlia|figli|figlie|bimba|bimbo|bambin[oaie])\b|\bnos (?:enfants|filles|fils)\b"
         r"|\b(?:ich habe|ich hab|wir haben|tengo|tenemos|j'ai|nous avons|eu tenho|tenho|temos|ik heb|wij hebben|we hebben|ho|abbiamo|jeg har|vi har|jag har) (?:(?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre|to|fire|två|fyra|\d) (?:\w+ )?|des |dei )?"
         r"(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia|børn|barn|unger|døtre|sønner|söner|döttrar|søn|sønn|datter|dotter)\b",
         lambda match: None if NEGATED.search(match.string, max(0, match.start() - 5), match.start()) else stated(fixed("has children"), FUTURE)(match), TAGGED),
    rule("parental_status", r"\b(?:min|mitt|mina|mit|mine|vores|våra|vår|vårt) (?:(?:lille|lilla|store|stora|yngste|ældste|eldste|äldsta|yngsta|to|tre|två) )?(?:son|søn|sønn|dotter|datter|døtre|döttrar|söner|sønner|barn|børn|unger|mindste|ældste|eldste|yngste|äldsta|yngsta)\b|\b(?:a |az )?(?:fiam|lányom|gyerekem|gyerekeim|kisfiam|kislányom)\b|\b(?:můj|moje|mého|mojí) (?:syn|dcera|děti|dítě|dceru|syna)\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) meu\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) (?:meu|mea|mei)\b|\b(?:mi|mis) (?:niño|niña|niños|niñas|bebé|nene|nena)\b",
         stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i|we) (?:have|got) no (?:kids|children|child)\b|\bno (?:kids|children) (?:yet|of (?:my|our) own|here|for me)\b|\b(?:i|we) (?:don't|do not|dont) have (?:any )?(?:kids|children) (?:yet|of (?:my|our) own)\b|\bi(?:'ve| have) no (?:kids|children)\b",
         fixed("no children"), CONDITIONAL),
    rule("parental_status", r"\b(?:estoy|estou|je suis|ich bin|sono|ik ben|jestem|jeg er|jag är)(?: (?!(?:pas|plus|jamais|nicht|nie|kein\w*|no|non|não|nao|nunca|niet|geen|ikke|inte)\b)[\w.]+){0,3}? (?:embarazada|grávida|gravida|enceinte|schwanger|incinta|zwanger|gravid|w ciąży)\b|\bbin (?:\w+ )?in der \d{1,2}\.? ?ssw\b|\bя беременна\b|\bhamileyim\b|\bbuntis ako\b", stated(fixed("expecting a child"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:\d+ ?(?:weeks?|months?) )?post[- ]?partum\b|\bmy post[- ]?partum\b|\b\d+ ?(?:weeks?|months?|days?) post[- ]?partum\b|\b(?:since|after|when|before) (?:giving birth|i gave birth|(?:having|i had) my (?:\w+ )?(?:baby|son|daughter|kids?|child|children|first|second|third|twins|lo|youngest|oldest|little))\b|\bi gave birth\b|\bmy last pregnancy\b"
         r"|\bmy (?:c-section|c section|labor and delivery|birth story|epidural|maternity leave|paternity leave)\b|\bi(?:'m| am)? (?:still |exclusively |currently )?(?:breastfeeding|breastfed|ebf)\b|\bbreastfeeding my\b|\bnursing my (?:son|daughter|baby)\b", stated(fixed("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |finally |also )?(?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+(?:\+\d)? ?(?:weeks?|wks?|months?) pregnant\b|\b(?:i'm|im|i am|we're|we are) expecting(?= (?:a baby|our|my|twins|baby|a little|a boy|a girl|in|again)\b|[.!,]|$)"
         r"|\bmy (?:first |second |third |current |\d+(?:st|nd|rd|th) )?pregnancy\b|\bthis pregnancy\b|\bmy (?:first|second|third) trimester\b|\b(?:my|our) (?:unborn|baby bump)\b|\bpregnant with (?:my|our) (?:first|second|third|\d|rainbow|twins|baby)\b|\bbaby (?:#|number )?\d on the way\b|\b(?:our|my) baby on the way\b"
         r"|\b(?:i'm|im|i am) due (?:in|next|this|any day|soon)\b|\bmy scheduled induction\b|\bcurrently pregnant\b|\bpregnant currently\b|\b(?:i'm|im|i am) currently \d+ ?(?:weeks|wks)\b", lambda match: None if PAST.search(match.string, max(0, match.start() - 20), match.start()) else stated(fixed("expecting a child"), FUTURE)(match), TAGGED),
    rule("parental_status", r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\b(?:i'm|im|i am|we're|we are|as an?) (?:\w+ )?child[- ]?free\b|\bno kids of my own\b|\bi(?:'ve| have) never had (?:kids|children)\b|\bwe (?:don't|do not|dont) have (?:any )?(?:kids|children)\b"
         r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b"
         r"|\b(?:i|we) (?:love |enjoy )?being (?:kid|child)[- ]?free\b|\b(?:i|we) (?:can't|cannot|can not|couldn't|could not|wasn't able to|weren't able to|was never able to|am not able to) (?:have (?:kids|children|a baby|babies|a child)|conceive)\b"
         r"|\bneither of us (?:is|are|can|was|were) (?:able to )?(?:have|has) (?:kids|children)\b|\bi(?:'m| am) infertile\b|\b(?:ich habe|ich hab|wir haben) (?:noch |gar |auch )?keine? (?:kind|kinder)\b|\b(?:je n'ai|nous n'avons) pas d'enfants?\b|\bno (?:tengo|tenemos) hijos?\b|\bn[ãa]o (?:tenho|temos) filhos?\b|\bnon (?:ho|abbiamo) figli\b|\b(?:ik|wij|we) (?:heb|hebben) geen kinderen\b|\b(?:jeg|vi) har ingen børn\b|\b(?:jag|vi) har inga barn\b|\b(?:nemám|nemáme) (?:\w+ )?děti\b|\bděti nemám\b|\bje ne suis pas (?:père|mère)\b"
         r"|\bi (?:also |still |just |really |even |currently |personally |myself |actually )(?:don't|do not|dont) have (?:any )?(?:kids|children)\b|\bi (?:\w+ )?(?:don't|do not|dont|never) (?:ever )?want(?:ed)? (?:any )?(?:kids|children)\b|\bi (?:also )?never (?:married or )?had (?:any )?(?:kids|children)\b|\b(?:i'm|im|i am|i ain't|i aint) (?:not |never )having (?:any )?(?:kids|children)\b|\bno dependents\b", fixed("no children"), CONDITIONAL),
    rule("parental_status", r"\b(?:after|before|since) (?:i had|having) (?:my|our) (?:first|second|third|son|daughter|kids?|children|baby|babies)\b"
         r"|\bbefore i (?:got|became|was) pregnant (?:the first time|with (?:my|our))\b|\bafter my (?:first|second|third|last|previous|\d+(?:st|nd|rd|th)) pregnancy\b|\bwhen (?:i|we) had (?:my|our) (?:first|second|son|daughter|kids?|baby)\b", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"\b(?:after|since|before) (?:just )?having (?:a |my |our |\d |two |three |four |the )?(?:\w+ )?(?:baby|babies|kids?|children|child|twins|son|daughter)\b|\bafter (?:having )?baby\b|\bafter i had my (?:\w+ )?(?:baby|son|daughter|kids?|first|second|third|twins)\b"
         r"|\b\d+ ?(?:years?|yrs?) post[- ]?partum\b|\b(?:i'm|im|i am) \d+ ?(?:weeks?|months?|wks?|mos?) pp\b|\b(?:my|both of my|all of my|each of my|all my|both my) (?:\w+ )?pregnancies\b|\b(?:i|since i|after i|when i) (?:just |recently |finally )?became a (?:\w+ )?(?:mom|mum|mother|dad|father|parent)\b"
         r"|\b(?:we|i) (?:just |recently )?had (?:a|our|my) (?:\w+ )?(?:baby|child|son|daughter)\b(?! (?:shower|of|in))|\b(?:married|divorced|single|separated|widowed) (?:with|w/) (?:(?:\d+|one|two|three|four|five|a|an) )?(?:(?!no\b)\w+ )?(?:kids?|kiddos?|children|child|sons?|daughters?|boys|girls|toddlers?|teens|babies|baby)\b"
         r"|\b(?<![^\n,;:(|/ ])(?<![^\n,;:(|/] )(?:\d|two|three|four|five) (?:kids|children|teens|kinder|kinderen|hijos|enfants|filhos|figli|børn|dzieci|děti)\b|\bkids\s*:\s*[1-9]"
         r"|\b(?:i was|i got|i had to be) induced\b|\bmy waters? broke\b|\bi was in labou?r\b|\b(?:both|all) (?:of )?my (?:births|deliveries|labou?rs)\b|\bi(?: had|'ve had| have had) (?:two |three |\d |a |an )?(?:c-?sections?|vaginal births?|home births?|natural births?|unmedicated births?)\b", stated(kept("has children"), FUTURE), TAGGED),
    rule("parental_status", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:two|three|four|five|\d|twin|little|baby|eldest|oldest|youngest|middle|teenage|fourth|third|second|first) (boys|girls|boy|girl)\b", child, TAGGED),
    rule("parental_status", r"(?:baby|toddler|kiddo|lo|bub) (?:is|was|has|had|decided|needs|got|will|sleeps|slept|woke|wakes|just|still|started|loves|hates|refuses|won't|doesn't|did|turned|takes|eats|arrived|came)\b", parenting, TAGGED),
    rule("parental_status", rf"(?:my (?<=\bmy )|our (?<=\bour )){ORDINAL}(?: one| two| three)?(?=[.,!?;)]|$| (?:and|but|at|in|i|we|he|she|they|it|was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b)", birth_order, TAGGED),
    needs(rule("parental_status", rf"(?:(?:i(?<=\bi)|we(?<=\bwe))(?:'ve| have)? (?:also |both |still |even |do |did |already |now |currently |usually |only )?(?:have|had|got|raised|birthed)"
         rf"|(?:have|had|got|raised)(?<![\w'-]have)(?<![\w'-]had)(?<![\w'-]got)(?<![\w'-]raised)) {KID_COUNT}{KID_WORDS}{KID_NOUN}{KID_AFTER}", raising, TAGGED), "kid", "child", "son", "daughter", "toddler", "teen", "newborn", "infant", "twin", "triplet", "step", "grand", "old"),
    needs(rule("parental_status", rf"{ME} (?:\w+,? ){{1,3}}and an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band)\w+ )?(?:mom|mum|mother|dad|father|parent)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur))|\b\d{{2}}\s*(?:yo|y/o|years? old|year-old|yr old|yrs old)\s*,?\s*(?:(?!dog|cat|pet|plant|fur|boy|girl)\w+ )?(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)",
         parent_label, TAGGED), "mom", "mum", "mother", "dad", "father", "parent", "mama"),
    needs(rule("parental_status", r"\b(?:as|being) an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band|bonus|future|good|bad)\w+ )?(?:mom|mum|mother|dad|father|parent|mama|mommy)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur)| figure| friend)",
         lambda match: parent_label(match) if SELF.search(match.string, *sentence(match)) else None, TAGGED), "mom", "mum", "mother", "dad", "father", "parent", "mama"),
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
HAVE = r"(?:i(?<=\bi)|we(?<=\bwe))(?: (?:also |both |still |do |currently |now |already )?(?:have|got|own|adopted|rescued|recently adopted|just adopted|just got|bought myself|got myself|just bought)|'ve (?:also |still )?got) (?:a |an |two |three |four |\d+ )?(?:(?!(?:to|seen|been|heard|watched|met|noticed|found|the|this|that|these|those|of|for|with|from|in|on|at|by|about|like|no|not|never|ever|always|is|was|are|were|and|or|but|my|your|his|her|their|our)\b)[a-z\d-]+ ){0,2}"
FELINE = re.compile(r"\bcats?\b|\bkitten|meow|litter|purr|feline|\bvet\b|catnip|scratching post|\bfur\b|indoor|outdoor|feral|adopt|rescue")
CANINE = re.compile(r"\b(?:dogs?|pups?|puppy|puppies|vet|walks?|walked|walking|leash|bark\w*|fetch|kibble|breed|breeder|groomer|crate|treats?|paws?|fur|tail|neutered|spayed)\b")
GENERIC_DOG = re.compile(r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt)$")
MOURNED = re.compile(r"\b(?:lost|losing|death of|passing of|loss of|rip|buried|bury|in memory of|used to|grew up|growing up|childhood)\b")
DIED = re.compile(r"(?:'s)?\s*(?:\w+ ){0,3}(?:passed|died|was put down|was put to sleep|crossed the rainbow bridge|is gone)\b")
GAME = re.compile(r"\b(?:game|games|gaming|gameplay|played|playing|playthrough|quests?|npcs?|server|mods?|dlc|console|ps4|ps5|xbox|steam|nintendo)\b")


def departed(match):
    return bool(MOURNED.search(match.string, clause(match.string, match.start()), match.start()) or DIED.match(match.string, match.end()))


def pet(kind):
    def value(match):
        if not free(match) or departed(match):
            return None
        if kind == "cat" and match.group(1) and not re.fullmatch(r"cats?|kittens?|catto|kitteh|kitty|kitties", match.group(1)) and not FELINE.search(match.string):
            return None
        if kind == "dog" and (word := match.group(1)) and " " not in word and not GENERIC_DOG.match(word) and word not in WORDNET_DOGS and word[:-1] not in WORDNET_DOGS and not CANINE.search(match.string):
            return None
        return kind
    return value


PETS = [
    rule("pets", rf"{OWN}({DOG})(?:'s)?\b(?! (?:girl|boy|face|eyes|fat|dog eyes|play)\b)(?!(?<=puppy) love\b)", pet("dog"), TAGGED),
    rule("pets", rf"{OWN}({CAT})(?:'s)?\b(?! (?:litter )?(?:is wet|pussy))", pet("cat"), TAGGED),
    rule("pets", rf"{HAVE}({DOG})\b(?! (?:in (?:this|the) (?:fight|race)|food|treats?|stickers?|shirts?|tattoos?|costumes?|emojis?)\b)", pet("dog"), SELF_HEDGE),
    rule("pets", rf"{HAVE}({CAT})\b", pet("cat"), SELF_HEDGE),
    rule("pets", rf"{HAVE}(?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|chickens|hens|ducks|goats|ball pythons?|corn snakes?|pet snakes?|snakes|geckos?|lizards?|bearded dragons?|tortoises?|turtles?|bettas?|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|mini pigs?|pet pigs?|horses|fish tank|aquarium|mice)\b(?! (?:in (?:this|the|a)|to fry|in a row)\b)", lambda match: "other pet" if free(match) and not departed(match) and not GAME.search(match.string) else None, SELF_HEDGE),
    rule("pets", rf"(?:{ME} an? |{AS} an? )(?:proud |\w+ )?owner of (?:a |an |two |three |\d+ )?(?:[a-z-]+ ){{0,2}}(?:({DOG})|({CAT})|({OTHER}))\b",
         lambda match: pet("dog" if match.group(1) else "cat" if match.group(2) else "other pet")(match), SELF_HEDGE),
    rule("pets", rf"(?:{ME} an? |{AS} an? )(?:proud |crazy |\w+ )?(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner|lady|person)\b|\b(dog|cat) (?:mom|mum|dad|mama|parent) here\b|\b(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner)s? (?:of|to) (?:\d+|one|two|three|four|five|a|an)\b",
         lambda match: pet("dog" if (match.group(1) or match.group(2) or match.group(3)) == "dog" else "cat")(match), SELF_HEDGE),
    rule("pets", r"\b(?:mi|mis) (perr[oa]s?|perrit[oa]s?|gat[oa]s?|gatit[oa]s?)\b|\b(?:meu|minha|meus|minhas) (cachorr[oa]s?|cadel[oa]s?|gat[oa]s?|gatinh[oa]s?)\b|\b(?:mon|ma|mes) (chien|chienne|chiens|chat|chatte|chats|chaton)\b|\b(?:mein|meine|meinen|meinem) (hund|hunde|hündin|katze|katzen|kater)\b"
         r"|\bmijn (hond|honden|kat|katten|poes)\b|\b(?:il mio|la mia|i miei|le mie) (cane|cani|cagnolino|gatto|gatta|gatti|gattino)\b|\b(?:mój|moja|moje) (pies|psy|piesek|kot|kotka|koty)\b|\b(köpeğim|kedim)\w*|\b(aso|pusa) ko\b",
         lambda match: ("cat" if re.match(r"gat|chat|kat|poes|kot|ked|pusa", next(filter(None, match.groups()))) else "dog") if free(match) else None, TAGGED),
    rule("pets", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:(?!from|of|with|and|to|in|on|at|for|is|was|the|a|an|are|were|be|been|has|had|have|by|little|high|lizard)[\w-]+ ){0,2}((?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|hens|chickens|ball pythons?|corn snakes?|snakes?|rodents?|geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|rats|horses?|ponies|snails?|shrimps?|fish tank|aquarium|fish(?:es)?|birds?|ducks?|ducklings?|frogs?|toads?|hermit crabs?|canar(?:y|ies)|finch(?:es)?|pigeons?|quails?|pony|donkeys?|alpacas?|llamas?|piglets?|goats|rat|mice|isopods|newts?|salamanders?))\b(?! (?:brain|toy|game|collab|tacos?|sticks?|fingers?|and chips|oil|sauce|market|soup|fry|dinner|recipe|curry|cakes?|fillets?|bones?|pie)\b)", lambda match: "other pet" if free(match) and not departed(match) and not GAME.search(match.string) else None, TAGGED),
]

def cohabiting(match):
    return "partner or family" if couple(match) else None


LIVING = [
    rule("living_with", r"\bi (?:still )?live (?:all )?(?:alone|by myself|on my own)\b|\bliving (?:alone|by myself|on my own)\b|\bhappy alone\b|\bi'm (?:all )?alone\b|\bhome(?<!walking home)(?<!walk home)(?<!walked home)(?<!going home)(?<!go home)(?<!went home)(?<!come home)(?<!came home)(?<!coming home)(?<!drive home)(?<!driving home)(?<!drove home)(?<!get home)(?<!got home)(?<!getting home)(?<!ride home)(?<!riding home)(?<!head home)(?<!heading home)(?<!headed home) alone\b(?! (?:today|tonight|now|too|right now|this (?:weekend|week|morning|afternoon|evening)|all (?:day|night|week|weekend)|for (?:the|a) (?:day|night|week|weekend|few)|and horny|& horny|with)\b)|\balone at home\b(?! (?:today|tonight|now|too|right now|this (?:weekend|week|morning|afternoon|evening)|all (?:day|night|week|weekend)|and horny)\b)|\balleine? (?:zu ?hause|daheim)\b", fixed("alone"), SELF_HEDGE),
    rule("living_with", r"\bi (?:have )?(?:lived|live|am living|still live) (?:at home )?with my (?:mom and dad|parents|mom|dad|mum|mother|father|folks|family|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi (?:still )?live at home\b|\bliving at home with\b",
         fixed("parents"), SELF_HEDGE),
    rule("living_with", r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse|sister|brother|son|daughter|aunt|uncle|cousin)\b|\bwe live together\b"
         r"|\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b"
         r"|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|hubby) and i (?:live|share (?:a|an|our)|rent|bought (?:a|our)|own (?:a|our)|have (?:a|an|our) (?:house|home|apartment|place|flat))\b|\bwho lives with me\b"
         r"|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))", fixed("partner or family"), SELF_HEDGE),
    rule("living_with", r"\b(?:my|our) (?:\w+ ){0,2}(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b|\b(?:ner|einer) wg\b", fixed("roommates"), SELF_HEDGE),
    *(rule("living_with", pattern, cohabiting, TAGGED) for pattern in COUPLE_ADS[1:]),
]

OWNING = re.compile(r"\b(?:mortgage|bought|buy|own|owned|paid|renovat\w*|remodel\w*|contractor|roof|hoa|property|selling|sell|sold|equity|yard|garage|basement|insurance|apprais\w*|built|build|attic|foundation|plumb\w*|furnace|hvac|siding|gutters?|lawn|deck|porch|driveway|landscap\w*)\b")
NOT_DWELLING = r"(?! (?:music|party|parties|rules|of|plants?|cat|guest|wine|band|special|keys?|key|country|town|city|state|office|page|screen|base|team|game|gym|network|router|server|assistant|lab|workout|cooked|made|school|schooling|planet|world|island|province|club|ground|turf|button|feed|depot|address|phone|internet|wifi|life|health|care|nurse|visits?|remedies|remedy)\b)"
RENTING = re.compile(r"\b(?:rent|rents|rented|renting|landlord|landlady|lease|leasing|tenant|tenants|tenancy|security deposit|sublet\w*|letting agent|property manager|leasing office)\b")
RENT_OUT = re.compile(r"\brent(?:s|ed|ing)? (?:it |them |\w+ )?out\b|\b(?:my|our) tenants?\b")
OTHER_PEOPLE = re.compile(r"\b(?:he|she|they|his|her|their|them|him|people|someone|anyone|everyone|you|your|op)\b")
MAYBE = re.compile(r"\b(?:would|wish|if|could|might|should|maybe)\b")


def first_person(match):
    start, end = sentence(match)
    return SELF.search(match.string, start, end) and not OTHER_PEOPLE.search(match.string, start, end) and not MAYBE.search(match.string, start, end)


def mortgaged(match):
    return kept("homeowner")(match) if first_person(match) else None


def tenure(match):
    return kept("homeowner" if match.group(1) else "renter")(match) if first_person(match) else None


HOUSING = [
    rule("housing", r"\b(?:i|we) (?:just |recently |finally )?(?:own|bought|purchased|closed on) (?:a|my|our|the|this) (?:first |new |own )?(?:\w+ )?(?:house|home|condo|townhouse|townhome|property)\b|\bfirst[- ]time home ?buyers?\b(?= here)|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:\w+ )?(?:house|home|condo)\b|\bwhen (?:i|we) bought (?:my|our) (?:house|home)\b"
         r"|\b(?:,|and|who|[.!?]) (?:recently |just |finally )?(?:bought|purchased) (?:a|my|our) (?:new |first |\w+ )?(?:house|home|condo|townhouse)\b|\bselling (?:my|our) (?:house|home|condo)\b|\bin the middle of selling the house\b|\bmy house is (?:assessed|worth|paid off|valued|appraised)\b|\bclos(?:ed|ing) on (?:my|our) (?:\w+ )?(?:house|home|condo)\b"
         r"|\b(?:i|we) (?:have|own) (?:a|my own|our own) (?:\d+[- ]?(?:bed(?:room)?|br) )?(?:house|condo|townhouse|home)\b(?! (?:office|gym|studio|theater|theatre|bar|network|server|lab|loan|equity|warranty|base|page|game|birth|visit|care|health|nurse|depot))|\bpaid off (?:my|our) (?:house|mortgage|home)\b", fixed("homeowner")),
    rule("housing", r"mortgage(?<=\bmortgage)(?:s|d)?\b(?! (?:loans?|brokers?|rates?|lenders?|industry|market|bankers?|officers?|advisors?|calculator)\b)", mortgaged, TAGGED),
    rule("housing", r"\b(?:my|our) (?:landlord|landlady|rent|leasing office|property manager|property owner|security deposit|tenancy|letting agent)\b|\b(?:ich )?wohne in (?:einer|ner) wg\b", kept("renter"), TAGGED),
    rule("housing", r"\bwe rent\b(?! (?:a car|cars|out)\b)|\b(?:i'm|im|i am|as) a tenant\b|\b(?:i|we) (?:pay|paid) (?:\$?\d[\d,]* (?:in |for |a month |per month )?|my |our |)rent\b|\bi rent (?:a|an|my)\b|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bi rent\b(?! (?:a car|cars|out|movies|equipment|tools|bikes?|a truck|a van|a uhaul|boats?|kayaks?|skis?)\b)|\bwe(?:'re| are) (?:currently )?renting\b", fixed("renter")),
    rule("housing", r"\b(?:i'm|im|i am|we're|we are|as|as new|as first[- ]time) (?:a |an )?(?:new |first[- ]time |proud )?(home ?owners?|renters?|tenants?)\b",
         lambda match: "homeowner" if "own" in match.group(1) else "renter"),
    rule("housing", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bbeing homeless (?:for|since)\b|\bi(?:'ve| have) been homeless\b|\bi live in my car\b|\bi(?:'m| am) (?:living|sleeping) in (?:my|a) (?:car|van|tent|shelter)\b", fixed("homeless")),
    rule("housing", r"\bmy (?:current |new |apartment |\w+ )?lease\b|\b(?:i|we) (?:just |recently )?(?:signed|renewed|broke|break|re-?signed) (?:a|my|our|the) (?:\w+ )?lease\b|\b(?:resigning|renewing|breaking) (?:my|our) lease\b", lambda match: None if re.search(r"\b(?:car|cars|vehicle|truck|ev|tesla|auto|mileage|miles|bmw|honda|toyota|lease deal|lease payment)\b", match.string) else kept("renter")(match), TAGGED),
    rule("housing", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |\d+[- ]?(?:bed(?:room)?|br) )?(?:house|home|condo|townhouse)\b" + NOT_DWELLING, lambda match: stated(kept("homeowner"), FUTURE)(match) if OWNING.search(match.string, *bounds(match)) else None, TAGGED),
    rule("housing", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |first |old |\d+[- ]?(?:bed(?:room)?|br) )?(?:apartment|apt|flat|studio|unit)\b(?! (?:complex|building)? ?(?:manager|managers|owner|owners)\b)", lambda match: stated(kept("renter"), FUTURE)(match) if RENTING.search(match.string, *bounds(match)) else None, TAGGED),
    rule("housing", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:current |new )?(?:house|home|room|bedroom|place)\b" + NOT_DWELLING, lambda match: stated(kept("renter"), FUTURE)(match) if RENTING.search(match.string, *bounds(match)) and not OWNING.search(match.string, *bounds(match)) and not RENT_OUT.search(match.string, *bounds(match)) else None, TAGGED),
    rule("housing", r"\b(?:(bought|purchased|closed on|built) (?:a|my|our|the|this) (?:[\w-]+ ){0,2}(?:house|home|condo|townhouse|place|property)\b(?! (?:for|as an investment)\b)|(?:renting|leasing|rent|rented|lease|leased) (?:a|an|my|our|this|the) (?:[\w-]+ ){0,2}(?:apartment|apt|flat|room|house|home|place|studio|unit|condo|townhouse)\b(?! out\b))", tenure, SELF_HEDGE),
    rule("housing", r"\b(?:my|our) first (?:house|home|condo|townhouse)\b(?! (?:game|run|base|office|page|screen)\b)|\bmoved into (?:my|our) (?:new |current )?(?:house|home|condo)\b|\b(?:got|have|bought) (?:my|our) own (?:place|house|home)\b|\bin the process of (?:buying|purchasing|closing on)\b",
         lambda match: stated(kept("homeowner"), FUTURE)(match) if SELF.search(match.string, *sentence(match)) else None, TAGGED),
    needs(rule("housing", r"(?:\b(?:i'm|im|i am|i've been|i was|we're|we are|as|being|and|also)(?: (?:a|an|the|now|also|still|currently|finally|proudly|happily|just))*(?: [\w-]+){0,2} |^\W*|[\n.!?(\[,]\s*)(home ?owners?|renters?)\b(?! (?:who|that|insurance|policy|association|associations|rights|protections?|credit|grant|programs?|market|groups?)\b)(?=\s*(?:[.,!;:)\]\n]|$|here|too|myself|and|but|with|in|for|since|now|so)\b|\s*[.,!;:)\]\n]|\s*$)",
         lambda match: ("homeowner" if "own" in match.group(1) else "renter") if spoken(match) and not THIRD.search(match.string, sentence(match)[0], match.start()) and not MAYBE.search(match.string, sentence(match)[0], match.start()) else None, TAGGED), "owner", "renter"),
    needs(rule("housing", r"\b(?:i|i'm|im|i am|i've been|i have been|i became|i ended up|i'm about to be|i am about to be|i'm going to be)(?: (?:just|now|currently|still|literally|basically|technically|actually|recently|already|officially|essentially|briefly|temporarily))? (?:became |become |ended up |end up |been )?homeless\b(?! (?:people|person|man|woman|guy|men|women|folks|shelters?|population|encampments?|camps?|kids|youth|veterans?)\b)"
         r"|\bi (?:\w+ )?(?:live|living|lived) (?:in|out of) (?:a|my) (?:tent|car|van|vehicle|truck|shelter)\b|\bi(?:'m| am|'ve been| have been)? (?:\w+ )?unhoused\b", stated(kept("homeless"), FUTURE), TAGGED), "homeless", "tent", "car", "van", "vehicle", "truck", "shelter", "unhoused"),
    needs(rule("housing", r"\b(?:i|we)(?:'ve| have)? (?:actually |also |already |finally |now |still |currently |just )?(?:own|owned) (?:a|my|our|\d|two|three) (?:[\w-]+ ){0,2}(?:house|home|condo|townhouse|townhome|place|flat|apartment|homes|houses|condos)\b(?! (?:for|as an investment|games?|office|gym|theater|theatre|network|page|screen)\b)"
         r"|\b(?:i|we) (?:\w+ )?(?:live|living|lived) in (?:a|an) (?:\w+ )?rented (?:apartment|flat|house|room|place|home|condo|unit|studio)\b|\b(?:i|we)(?:'ve| have) (?:only |always |never |also )?(?:ever )?rented\b(?! (?:a car|cars?|out|it|them|movies?|equipment|tools?|bikes?|a truck|a van|boats?|kayaks?)\b)|\b(?:i|we)(?:'re| are|'m| am)? (?:about to be |being |getting |got |just got )evicted\b",
         lambda match: stated(kept("renter" if "rent" in match.group() or "evict" in match.group() else "homeowner"), FUTURE)(match) if first_person(match) else None, TAGGED), "own", "rent", "evict"),
]

RULES = [*RELATIONSHIP, *PARENTAL, *scoped_rules(PETS), *scoped_rules(LIVING), *HOUSING]
