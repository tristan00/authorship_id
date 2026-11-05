import re

from .common import SELF_HEDGE, TAGGED, fixed, group, rule
from .life import AS, CONDITIONAL, free, scoped, scoped_rules

FREE = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b)\w+ )?"
FILLER = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b)[\w-]+,? (?:and )?){0,2}?(?:a |an )?"

ME = r"(?:'m|m| am|am| m|'am|'?ve been|'ve always been)"

RELIGIONS = {"christian": "christian", "catholic": "christian", "protestant": "christian", "mormon": "christian", "lds": "christian", "baptist": "christian", "methodist": "christian",
             "lutheran": "christian", "evangelical": "christian", "orthodox christian": "christian", "muslim": "muslim", "jew": "jewish", "jewish": "jewish", "hindu": "hindu",
             "buddhist": "buddhist", "sikh": "sikh", "pagan": "pagan or other religion", "wiccan": "pagan or other religion", "witch": "pagan or other religion",
             "spiritual": "spiritual, no religion", "agnostic": "agnostic", "atheist": "atheist", "presbyterian": "christian", "anglican": "christian", "episcopalian": "christian", "pentecostal": "christian",
             "adventist": "christian", "quaker": "christian", "mennonite": "christian", "coptic": "christian", "sunni": "muslim", "shia": "muslim", "shiite": "muslim", "moslem": "muslim",
             "satanist": "pagan or other religion", "polytheist": "pagan or other religion", "animist": "pagan or other religion",
             "taoist": "pagan or other religion", "jain": "pagan or other religion", "zoroastrian": "pagan or other religion", "rastafarian": "pagan or other religion", "luciferian": "pagan or other religion",
             "deist": "pagan or other religion", "pantheist": "pagan or other religion", "unitarian": "pagan or other religion", "shintoist": "pagan or other religion",
             "greek orthodox": "christian", "russian orthodox": "christian", "eastern orthodox": "christian", "jehovah's witness": "christian", "latter-day saint": "christian", "latter day saint": "christian",
             "secular humanist": "atheist", "humanist": "atheist", "nonbeliever": "atheist", "non-believer": "atheist", "bahai": "pagan or other religion", "baha'i": "pagan or other religion"}
FAITH = "|".join(map(re.escape, RELIGIONS))


def labelled(lead, table):
    def value(match):
        found = lead.search(match.string, max(0, match.start() - 80), match.start())
        return table.get(found.group(1)) if found else None
    return value


STEMS = (("مسلم", "muslim"), ("مسيح", "christian"), ("ملحد", "atheist"), ("ate", "atheist"), ("athe", "atheist"), ("athé", "atheist"), ("musul", "muslim"), ("muzu", "muslim"), ("muslim", "muslim"), ("moslim", "muslim"),
         ("jud", "jewish"), ("jüd", "jewish"), ("juif", "jewish"), ("juive", "jewish"), ("ebre", "jewish"), ("joods", "jewish"), ("agnost", "agnostic"))


def foreign(match):
    return next((value for stem, value in STEMS if match.group().split()[-1].startswith(stem)), "christian")


RELIGION = [
    rule("religion", rf"i(?<=\bi){ME} {FREE}(?:a |an )?{FREE}({FAITH})\b(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater)\b)", scoped(RELIGIONS), TAGGED),
    rule("religion", rf"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b|my\b|being\b|for\b|to\b|at\b|by\b|with\b|about\b)[\w-]+,? (?:and )?){{2,4}}(?:a |an )?({FAITH})\b(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater|household|family|parents)\b)", scoped(RELIGIONS), SELF_HEDGE),
    rule("religion", rf"{AS} an? (?:\w+ )?({FAITH})\b|\b(?:we|us) ({FAITH})s\b|\bi (?:became|became a|turned|am now|'m now|have become) ({FAITH})\b", lambda match: RELIGIONS.get(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("religion", r"(?:أنا|انا) (مسلم|مسلمة|مسيحي|مسيحية|ملحد|ملحدة)", foreign, SELF_HEDGE),
    rule("religion", r"\b(?:soy|sou) (católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|agnóstic[oa]|evangélic[oa])\b"
         r"|\bje suis (catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|agnostique)\b|\bich bin (katholisch|christ|christin|atheist|atheistin|muslim|muslima|jüdisch|evangelisch|agnostiker)\b"
         r"|\bjestem (katolikiem|katoliczką|ateistą|ateistką|chrześcijaninem|chrześcijanką|muzułmaninem|muzułmanką)\b|\bsono (cattolic[oa]|ateo|atea|cristian[oa]|musulman[oa]|ebre[oa])\b|\bik ben (katholiek|christen|atheïst|moslim|joods)\b"
         r"|\b(?:como|en tant que|als|come|jako) (?:un |una |um |uma |une |ein |eine )?(católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|judeu|judia|evangélic[oa]|catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|katholik(?:in)?|christ(?:in)?|atheist(?:in)?|jude|jüdin|cattolic[oa]|katolik|ateista|ateistka|chrześcijanin|chrześcijanka)\b",
         foreign, SELF_HEDGE),
    rule("religion", r"i(?<=\bi)(?:'m| am|m| m) (?:also |personally |actually |just |definitely |certainly |honestly )?not (?:a |very |really |particularly |that |super |overly |at all |even |remotely |exactly |all that |terribly |the least bit )?religious(?: person)?\b|n(?<=\bn)ot(?:(?<=^not)|(?<=[.!?\n]not)|(?<=[.!?\n] not)|(?<=[.!?\n]  not)) (?:a |very |really |particularly )?religious(?: person)?\b|i(?<=\bi)(?:'m| am) (?:a )?(?:non-?religious|irreligious)\b|i(?<=\bi) (?:don't|do not|dont) (?:have|practice|follow) (?:a |any )religion\b|i(?<=\bi) have no religion\b|i(?<=\bi) (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|i(?<=\bi) loathe (?:all )?religion\b|s(?<=\bs)piritual,? (?:but )?not religious\b|m(?<=\bm)ore spiritual than religious\b|я(?<=\bя) не религиозн|n(?<=\bn)o soy religios[oa]\b|i(?<=\bi)ch bin nicht religiös\b",
         lambda match: "atheist" if "god" in match.group() or "loathe" in match.group() else "spiritual, no religion", TAGGED),
    rule("religion", rf"\b(?:i|i'd|i would) (?:consider myself|identify as|would call myself|call myself|describe myself as) (?:a |an )?(?:\w+ )?({FAITH})\b|\b(?:we|us) as ({FAITH})s\b|{AS} ({FAITH})s,? (?:we|us|our)\b|\bfellow ({FAITH})s?\b", lambda match: RELIGIONS.get(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("religion", r"here(?<=\bhere)\b", labelled(re.compile(rf"(?:^|[.!?,;(] *)(?:(?!former\b|ex\b|recovering\b|lapsed\b|non\b|not\b|raised\b|born\b|anti\b)\w+ )?({FAITH}) \Z"), RELIGIONS), SELF_HEDGE),
    rule("religion", rf"\A\W*(?:\d{{2}}\s*[mf]?\W*)?(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?({FAITH}) (?:couple|guy|girl|man|woman|male|female|m|f|dad|mom|here|only)\b", group(RELIGIONS), SELF_HEDGE),
    rule("religion", r"i (?<=\bi )(?:\w+ )?pray (?:that )?allah\b", fixed("muslim"), SELF_HEDGE),
    rule("religion", r"my (?<=\bmy )(?:relationship|walk|journey) with (?:god|christ|jesus|the lord)\b|i (?<=\bi )(?:\w+ )?(?:seek|follow|love|accepted|believe in|trust in|pray to|worship) (?:jesus|christ|the lord)\b|i (?<=\bi )(?:\w+ )?pray (?:to god|every (?:day|night|morning)|daily|the rosary)\b",
         fixed("christian"), SELF_HEDGE),
    rule("religion", r"my (?<=\bmy )(?:pagan|wiccan|witchy|heathen|druid\w*|witchcraft) (?:community|path|practice|journey|beliefs|faith|spirituality|tradition|altar|craft|friends|group)\b|my (?<=\bmy )(?:altar|deities|patron (?:god|goddess|deity)|book of shadows)\b", fixed("pagan or other religion"), SELF_HEDGE),
    rule("religion", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:home |local |new |old )?(church|pastor|priest|parish|congregation|mosque|masjid|imam|synagogue|shul|rabbi)\b(?! (?:friends?|youth group)\b)", lambda match: ("muslim" if match.group(1) in ("mosque", "masjid", "imam") else "jewish" if match.group(1) in ("synagogue", "shul", "rabbi") else "christian") if free(match) else None, SELF_HEDGE),
]

POLITICS = {"communist": "communist or far left", "marxist": "communist or far left", "socialist": "socialist or left", "leftist": "socialist or left", "liberal": "progressive or liberal",
            "progressive": "progressive or liberal", "democrat": "progressive or liberal", "centrist": "centrist or moderate", "moderate": "centrist or moderate",
            "conservative": "conservative or right", "republican": "conservative or right", "libertarian": "libertarian", "anarchist": "anarchist",
            "nationalist": "nationalist or far right", "apolitical": "apolitical", "lefty": "socialist or left"}
PARTY = "|".join(POLITICS)
POLITICAL = [
    rule("political_identity", rf"i(?<=\bi){ME} {FREE}(?:a |an )?{FREE}{FILLER}({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|with|about|when|in terms|on|in my|of|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach)\b)",
         scoped(POLITICS), TAGGED),
    rule("political_identity", rf"i(?<=\bi) (?:consider myself|identify as|would call myself|describe myself as) (?:a |an )?(?:\w+ )?({PARTY})\b|i(?<=\bi)(?:'m| am) a registered (democrat|republican)\b|i(?<=\bi) (?:\w+ )?lean(?:s)? (?:more |pretty |very |slightly |a bit |a little |heavily |strongly |hard )?(?:to the |towards the |toward the |towards |toward )?(left|right|liberal|conservative|progressive|libertarian|socialist)\b(?! (?:on|against|into|over|back|forward|in)\b)",
         lambda match: POLITICS.get(match.group(1)) or POLITICS.get(match.group(2)) or {"left": "socialist or left", "right": "conservative or right"}.get(match.group(3)) or POLITICS.get(match.group(3)), SELF_HEDGE),
    rule("political_identity", rf"\b(?:we|us) ({PARTY})s\b|\bme and (?:every|other|fellow|all the) ({PARTY})s?\b|\b(?:center|centre)[- ](left|right)(?: \w+){{0,2}} here\b|\bi(?:'m| am) (?:a )?maga\b|\bi (?:\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(republican|gop|democrat)\b"
         r"|\b(?:volledig |totally |completely )?(apolitiek|apolitisch|apolítico|apolítica|apolitico|apolitica)\b",
         lambda match: POLITICS.get(match.group(1) or match.group(2)) or {"left": "progressive or liberal", "right": "conservative or right", "republican": "conservative or right", "gop": "conservative or right"}.get(match.group(3) or match.group(4) or "", "apolitical" if match.group(5) else "conservative or right" if "maga" in match.group() else "progressive or liberal"), SELF_HEDGE),
    rule("political_identity", rf"{AS} an? (?:\w+ )?({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?)\b)", group(POLITICS)),
    rule("political_identity", r"here(?<=\bhere)\b", labelled(re.compile(rf"(?:^|[.!?,;(] *)({PARTY}) \Z"), POLITICS), SELF_HEDGE),
    rule("political_identity", rf"f(?<=\bf)ellow ({PARTY})s?\b", group(POLITICS), SELF_HEDGE),
    rule("political_identity", r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly on|solidly on|squarely on|also on)[*_]* the [*_]*(?:far[- ])?(left|right)\b(?! (?:track|path|side of|page|way|foot|direction|answer|thing|one|place|time|hand|lane|side of history)\b)|\b(?:i'm|im|i am|i m) (?:pretty |very |far |more |center |centre |a |fairly |quite )?(left[- ]wing|right[- ]wing|left[- ]leaning|right[- ]leaning|leftist|lefty|far[- ]left|far[- ]right|center[- ]left|centre[- ]left|center[- ]right|centre[- ]right|left of cent(?:er|re)|right of cent(?:er|re))\b",
         lambda match: "socialist or left" if "left" in (match.group(1) or match.group(2)) or "lefty" in (match.group(1) or match.group(2)) else "conservative or right", SELF_HEDGE),
]

DIETS = {"vegan": "vegan", "vegetarian": "vegetarian", "veggie": "vegetarian", "pescatarian": "pescatarian", "pescetarian": "pescatarian", "keto": "keto or low carb",
         "halal": "halal or kosher", "kosher": "halal or kosher", "gluten free": "gluten free", "gluten-free": "gluten free"}
DIET = [
    rule("diet", rf"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b|recovering\b|bad\b)[\w-]+ )?(?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b)[\w-]+ )?(vegan|vegetarian|veggie|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)", group(DIETS)),
    rule("diet", rf"{AS} an? (vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)", group(DIETS)),
    rule("diet", r"\bwe(?:'re| are) (?:all |both |also |strictly )?(vegan|vegetarian|pescatarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly)\b)|\b(?:soy|sou|sono|ich bin|ik ben) (vegan[oa]?|vegetarian[oa]|vegetarisch|vegetarier(?:in)?|vegetariër|veganer(?:in)?)\b"
         r"|\bje suis (végane?|végétarien(?:ne)?|vegan)\b|\bjestem (weganką|weganinem|wegetarianką|wegetarianinem)\b", lambda match: DIETS.get(word := next(filter(None, match.groups()))) or ("vegetarian" if "tar" in word else "vegan"), SELF_HEDGE),
    rule("diet", r"i(?<=\bi)(?:'m| am| have| was diagnosed with| got diagnosed with|'ve got| also have)? (?:a )?(?:celiac|coeliac)\b|m(?<=\bm)y (?:celiac|coeliac)\b|i(?<=\bi) (?:eat|am|'m|have to (?:eat|be|stay)|keep|went|stay) (?:strictly |completely |100% )?gluten[- ]free\b|t(?<=\bt)he gf diet\b", fixed("gluten free"), SELF_HEDGE),
    rule("diet", r"i(?<=\bi) (?:eat|keep|only eat|stick to|stick with|have to stick with|follow) (?:strictly )?(halal|kosher)\b|i(?<=\bi)(?:'m| am) (?:on |doing )?(?:a |strict )?(keto)\b(?! (?:friendly|recipe))|i(?<=\bi) (?:do|eat|follow|went) (keto|low[- ]carb)\b",
         lambda match: "halal or kosher" if match.group(1) else "keto or low carb", SELF_HEDGE),
    rule("diet", r"i(?<=\bi) (?:don't|do not|dont) eat (meat|any meat|animal products)\b|i(?<=\bi)(?:'m| am) (?:fully |mostly |\d+% )?(plant[- ]based)\b|i(?<=\bi) eat (plant[- ]based)\b", lambda match: "vegetarian" if "meat" in match.group() else "vegan", SELF_HEDGE),
    rule("diet", r"i(?<=\bi) (?:eat|love) meat\b|i(?<=\bi)'?m a (?:meat eater|carnivore|omnivore)\b", fixed("eats everything")),
    rule("diet", r"here(?<=\bhere)\b", labelled(re.compile(r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian) \Z"), DIETS), SELF_HEDGE),
    rule("diet", r"i(?<=\bi)(?:'ve been| went| became| turned) (vegan|vegetarian|pescatarian)\b|been(?<=\bbeen) (vegan|vegetarian|pescatarian)\b|went(?<=\bwent) (vegan|vegetarian|pescatarian)\b", lambda match: DIETS.get(next(filter(None, match.groups()))), SELF_HEDGE),
]


SELF_NEAR = re.compile(r"\b(?:i|i'm|im|i've|ive|me|my|we)\b")
OTHER_NEAR = re.compile(r"\b(?:you|he|she|they|people|someone|somebody|anyone|everyone|his|her|their|your|friends?|dad|mom|husband|wife|boyfriend|girlfriend|kids?|son|daughter)\b")


def smoking_mine(match):
    lead = match.string[max(match.string.rfind(mark, 0, match.start()) for mark in ".!?\n") + 1:match.start()]
    return "smoker or vaper" if SELF_NEAR.search(lead) and not OTHER_NEAR.search(lead) else None


SMOKED = r"(?:a |my |some |the )?(?:weed|pot|cigs?|cigarettes?|blunts?|joints?|bowls?|spliffs?|tobacco|cigars?|pipe|dabs?|carts?|j)\b"
QUIT_SPAN = r"(?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes)|after (?:vaping|smoking) (?:since|for))\b"


SMOKING = [
    rule("smoking", rf"\bi (?:smoke|vape)(?: cigarettes| cigs| a pack| daily| every day)?\b(?! (?:meat|out|detector|alarm)\b)|(?:\b(?:i'm|im|i am)|{AS}) a (?:\w+ )?(?:weed |pot )?smoker\b|\bneed to smoke\b|\bi(?:'m| am)? (?:\w+ ){{0,2}}(?:buying|buy|bought|hitting|hit) (?:a |my )?(?:disposable |nic |nicotine )?(?:vape|juul|cigs|cigarettes|pack of (?:cigs|cigarettes|smokes))\b|\b(?:i'm|im|i am) a (?:heavy |chain |social )?smoker\b|\bmy (?:vape|cigarettes)\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"i(?<=\bi)(?: |'ve | have )(?:haven't|have not|havent) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b|h(?<=\bh)ave(?:n't| not|nt) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b"
         r"|i(?<=\bi) (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|since(?<=\bsince) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|after(?<=\bafter) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b"
         r"|when(?<=\bwhen) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|i(?<=\bi)(?:'ve| have)? never smoked\b"
         rf"|day(?<=\bday)s? {QUIT_SPAN}|week(?<=\bweek)s? {QUIT_SPAN}|month(?<=\bmonth)s? {QUIT_SPAN}|year(?<=\byear)s? (?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes))\b", fixed("non-smoker"), SELF_HEDGE),
    rule("smoking", r"i(?<=\bi) (?:don't|do not|dont|never) smoke\b|i(?<=\bi) quit smoking\b|i(?<=\bi) used to (?:smoke|vape)\b|i(?<=\bi)(?:'m|m| am) a non-?smoker\b|i(?<=\bi)'ve never smoked\b", fixed("non-smoker"), CONDITIONAL),
    rule("smoking", r"\b(?:i|me) (?:\w+ )?(?:smoke|smoked|vape|vaped) (?:for|to|after|before|when|every|a|cigarettes|cigs|daily)\b|\bmy (?:cigarettes?|cigs|vape|juul|pack of (?:cigs|cigarettes|smokes)|smoke break|cigarette break)\b|\b(?:i'm|im|i am) a (?:heavy |chain |social |casual )?(?:smoker|vaper)\b"
         r"|\bi(?:'ve| have) been (?:smoking|vaping) (?:for|since)\b|\bi smoke (?:a|\d+|two) packs?\b|\bi (?:\w+ )?(?:drink|drink socially) and smoke\b|\bi (?:\w+ )?smoke and drink\b|\bich rauche\b|\bwir rauchen\b|\brauchen den\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"non(?<=\bnon)[- ]?smoker\b|i(?<=\bi) don'?t smoke\b|we(?<=\bwe) don'?t smoke\b", fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
    rule("smoking", rf"(?:\b(?:i'm|im|i am|signed,?|i've been)|{AS}) (?:a |an )?(?:(?!(?:not|never|no|former|ex)\b)[\w-]+ ){{0,2}}?(?:smoker|vaper|stoner|pothead)\b", lambda match: None if "non" in match.group() else "smoker or vaper", SELF_HEDGE),
    rule("smoking", r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a few|several) (?:days?|weeks?|months?|years?)\W{0,8}(?:after|since|off|without|free from|clean from|of not) (?:vaping|smoking|nicotine|cigarettes|cigs|the vape|juul|tobacco)\b"
         r"|\bi(?:'ve| have)? (?:finally |officially |just )?(?:quit|stopped|given up|kicked) (?:the )?(?:vape|vaping|juul|cigarettes|cigs|nicotine|smoking|tobacco)\b", fixed("non-smoker"), SELF_HEDGE),
    rule("smoking", r"\bi (?:(?!don't|dont|do not|don|never|wouldn't|won't|can't|cannot|used|stopped|quit|need|needed|had|did|would|could|should|might|may|want|wanted|wanna|gonna|going|tried|try)[\w']+ ){1,2}(?:smoke|vape)\b(?! (?:meat|out|detector|alarm|free|ribs|brisket|fish|salmon|turkey|pork|chicken|signals?|bombs?|screen|machine)\b)"
         r"|\bi (?:(?!don't|dont|do not|don|never|wouldn't|won't|can't|cannot|used|stopped|quit|need|needed|would|could|should|might|may|want|wanted|wanna|gonna|going|tried|try|hate|hated|smell|smelled|see|saw|watch|watched|notice|noticed|someone|somebody|people|anyone|everyone|add|added)[\w']+ ){1,3}(?:smoking|vaping)\b(?![/-]| (?:meat|ribs|brisket|out|hot|fish|salmon|turkey|pork|chicken|gun|area|section|ban|room|wood|chips|pellets)\b)"
         r"|\b(?:i'm|im|i am) (?:just |currently |still |now |literally |also )?(?:smoking|vaping)\b(?! (?:meat|ribs|brisket|out|hot|fish|salmon|turkey|pork|chicken)\b)|\bi (?:enjoy|love|like) (?:smoking|vaping)\b(?! (?:meat|ribs|brisket|fish|salmon|turkey|pork|chicken)\b)",
         fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"i(?<=\bi) (?:don't|do not|dont|don) (?:drink|do drugs|party)(?:,? (?:or |and |nor )?(?:drink|do drugs|party))*,? (?:or |and |nor )?(?:smoke|vape)\b|not(?<=\bnot) a (?:drinker or (?:a )?)?smoker\b|i(?<=\bi)(?:'re| are|'m| am) (?:both )?(?:[\w&]+, )*non-?smokers?\b|we(?<=\bwe)(?:'re| are|'m| am) (?:both )?(?:[\w&]+, )*non-?smokers?\b",
         fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
    rule("smoking", r"do(?:(?<=[,;:] do)|(?<=[,;:]do))(?:n't|n| not|nt) (?:(?:drink|do drugs|party)(?:,? (?:or |and |nor )?(?:drink|do drugs|party))*,? (?:or |and |nor )?(?:smoke|vape)|(?:smoke|vape),? (?:or |and |nor )(?:drink|do drugs|party))\b",
         fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
    rule("smoking", rf"smok(?<=\bsmok)(?:e|ing) {SMOKED}|vap(?<=\bvap)(?:e|ing) {SMOKED}|roll(?<=\broll)(?:ing)? {SMOKED}|light(?<=\blight)(?:ing)? up {SMOKED}", smoking_mine, SELF_HEDGE),
]

SERVICE = re.compile(r"\b(?:army|navy|marines?|military|usmc|air force|national guard|coast guard|deploy\w*|enlist\w*|veterans?|va|dd-?214|gi bill|mos|ets|boot ?camp|basic training|base|platoon|squadron|battalion|nco|sergeant|sgt|corporal|cpl|soldiers?|sailors?|airmen|servicemembers?|served)\b")

VET = r"(?:a |an )?(?:proud |disabled |combat |retired |former |old )?(?:(?:army|navy|marine|marine corps|air force|military|usmc|combat|war|coast guard) )?(?:vet|veteran)\b(?! (?:tech|clinic|bill|school|student|player|gamer|member|user|fan|raider|streamer|poster|of (?:the|this))\b)"
VA = r"[^.!?\n]{0,40}?\b(?:va claim|va rating|va disability|dd-?214|c&p exam|nexus letter|service[- ]connected|100% p&t|the va\b(?! (?:area|beach|state|border|side|suburbs|region)\b))\b"
MILITARY = [
    rule("military_status", rf"i(?<=\bi){ME} (?:currently |still )?(?:in|serving in|enlisted in) the (?:army|navy|marines|air force|military|national guard|coast guard|marine corps|reserves|space force)\b|i(?<=\bi){ME} (?:on )?active duty\b"
         rf"|i(?<=\bi){ME} (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service ?member|infantryman|paratrooper)\b|i(?<=\bi){ME} (?:currently )?(?:deployed|stationed)\b"
         r"|my(?<=\bmy) (?:unit|platoon|squadron|battalion|deployment|chain of command|first sergeant|drill sergeant|commanding officer|nco|squad leader)\b", fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", rf"i(?<=\bi){ME} (?:a |an )?(?:former|retired|ex[- ]?) ?(?:soldier|marine|sailor|airman|service ?member|military|army|navy|paratrooper|infantryman)\b|my(?<=\bmy) (?:time|years|service) in the (?:army|navy|military|marines|corps|marine corps|service|air force|national guard)\b|i(?<=\bi)(?:'m| am) prior service\b"
         rf"|i(?<=\bi){ME} {VET}|{AS} {VET}|when(?<=\bwhen) i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|i(?<=\bi) (?:served|was) (?:\w+ )?in the (?:forces|army|navy|marines|air force|military|coast guard|marine corps)\b|i(?<=\bi) served (?:my country|\d+ years|overseas|(?:two|three|four|\d) tours)\b"
         r"|i(?<=\bi) (?:got out of|retired from|separated from) the (?:army|navy|marines|air force|military|service)\b|army(?<=\barmy) retiree\b|navy(?<=\bnavy) retiree\b|military(?<=\bmilitary) retiree\b|marine(?<=\bmarine) retiree\b|air(?<=\bair) force retiree\b|usmc(?<=\busmc) retiree\b|coast(?<=\bcoast) guard retiree\b"
         r"|retired(?<=\bretired) (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force|military|usmc)\b"
         rf"|my(?<=\bmy)\b{VA}|i(?<=\bi)(?:'ve| have| was| got| am|'m)?\b{VA}", fixed("military veteran"), SELF_HEDGE),
    rule("military_status", r"\d(?<!\w\d)\d{1,2} ?% (?:p&t|sc|service[- ]connected)\b", fixed("military veteran"), SELF_HEDGE),
    rule("military_status", r"\bi (?:went to boot ?camp|went through (?:boot ?camp|basic(?: training)?)|did basic(?: training)?|got out of the (?:army|navy|marines|military|air force|service|guard|corps)|was (?:honorably |medically )?discharged|"
         r"was (?:a|an) (?:\w+ )?(?:soldier|marine|sailor|airman|medic|paratrooper|infantryman|nco)|was (?:a |an )?(?:\w+ )?(?:officer|sergeant|corporal|specialist) in the (?:army|navy|marines|air force|military))\b"
         r"|\b(?:i did|i spent|i served|after|my) (?:\d+|two|three|four|five|six|eight|ten|twelve|fifteen|twenty) (?:years|yrs) (?:in|of) (?:the )?(?:army|navy|marines|military|air force|service|active duty|marine corps|guard|reserves)\b",
         lambda match: "military veteran" if SERVICE.search(match.string) else None, SELF_HEDGE),
    rule("military_status", rf"i(?<=\bi){ME} (?:(?!on |at |my |so |to |no |in |an )[a-z]{{2}} |army |air )?(?:national )?guard(?:sman|swoman)?\b(?! (?:duty at|dog)\b)|i(?<=\bi){ME} (?:a |an )?(?:reservist|guardsman|guardswoman)\b|i(?<=\bi){ME} (?:in|with) the (?:\w+ )?(?:reserves?|guard)\b",
         fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", r"my (?<=\bmy )(?:va |disability |combined |current )?(?:rating|claim|c&p|dbq|vso|gi bill|tricare|dd-?214|va benefits|va healthcare|va doctor|va appointment|pact act)\b",
         lambda match: "military veteran" if re.search(r"\b(?:va|veterans?|military|service|army|navy|marines?|air force|usmc|vso|dbq|c&p)\b", match.string) else None, SELF_HEDGE),
    rule("military_status", rf"i(?<=\bi){ME} (?:a |an )?(?:\w+ )?(?:officer|medic|nco|sergeant|corporal|private|specialist|pilot|mechanic|engineer|nurse|soldier|infantryman|linguist|analyst|doctor|chaplain) in the (?:army|navy|marines|air force|military|national guard|coast guard|reserves?|space force)\b",
         fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", rf"\bi (?:\w+ )?served (?:\w+ )?(?:in (?:combat)|overseas|(?:\d+|two|three|four|five|six|eight|ten|twenty) (?:years|yrs|tours)|my (?:time|country|contract|enlistment))\b"
         r"|\bfellow (?:veterans|vets|servicemembers|service members)\b"
         r"|\b(?:after|since|when|before|once) (?:i )?(?:got out|getting out|ets(?:'d|ed)?|i separated|separating|i was discharged)\b|\b(?:my|i did|i've done|i have done|i had) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b|\b\d+ deployments\b"
         rf"|\b(?:i'm|im|i am) (?:using|running|on) (?:the |my )?(?:gi bill|post[- ]9/11)\b|\bi (?:used|use) (?:the |my )?gi bill\b|i(?<=\bi){ME} (?:a |an )?(?:[\w-]+ ){{1,3}}(?:and )?(?:a )?(?:war|combat|army|navy|marine|air force|military|disabled|retired|coast guard) (?:vet|veteran)\b"
         r"|\bi (?:was|spent) (?:\w+ ){1,3}in the (?:army|navy|marines|air force|military|coast guard|marine corps|national guard)\b", lambda match: "military veteran" if SERVICE.search(match.string) else None, SELF_HEDGE),
]


RULES = [*scoped_rules(RELIGION), *scoped_rules(POLITICAL), *scoped_rules(DIET), *scoped_rules(SMOKING), *scoped_rules(MILITARY)]
