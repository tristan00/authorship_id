import re

from .common import I, SELF_HEDGE, TAGGED, clause, fixed, group, rule

WANTING = re.compile(r"\b(?:looking for|look for|seeking|search(?:ing)? for|want(?:s|ed|ing)?|wish|need(?:s|ed)?|find(?:ing)?|future|someday|one day|hope|hoping|dream|imagine|pretend|roleplay|rp|"
                     r"if i (?:ever )?(?:had|have|get|got|find)|when i (?:have|get|find)|until i|without|any|anyone|all)\b")
CONDITIONAL = re.compile(r"\b(?:if|would|wish)\b")


def free(match, hedge=WANTING):
    text, start = match.string, match.start()
    return not hedge.search(text, max(clause(text, start), start - 40), start)


def owned(table, number=1):
    return lambda match: table.get(match.group(number)) if free(match) else None


def kept(result):
    return lambda match: result if free(match) else None


FOND = (r"(?:sweet|lovely|loving|beautiful|gorgeous|pretty|hot|sexy|naughty|amazing|wonderful|awesome|dear|dearest|darling|current|new|supportive|incredible|poor|long[- ]?term|live[- ]in|beloved|own|big|"
        r"little|cute|cuck(?:old)?|kinky|horny|slutty|shy|petite|busty|curvy|thick|chubby|young|younger|older|patient|perfect|handsome|lucky|silly|sleepy|grumpy|crazy|lazy|jealous|loyal|faithful|"
        r"asian|latina|latino|black|white|indian|aussie|british|american|german|french|canadian|mexican|filipina|italian|irish|japanese|korean|chinese|russian|brazilian|spanish|polish|english|scottish|dutch|"
        r"\d{2} ?[mf]?|\(\d{2} ?[mf]?\)|\d{2}[- ]?(?:yo|y/o|years?[- ]old)|(?:\w+[- ])?year[- ]old)")
MARRIED, DATING, ENGAGED = "married", "dating or in a relationship", "engaged"
SPOUSES = {"wife": MARRIED, "husband": MARRIED, "hubby": MARRIED, "wifey": MARRIED, "spouse": MARRIED, "missus": MARRIED, "missis": MARRIED, "mrs": MARRIED, "hubs": MARRIED, "wifes": MARRIED,
           "husbands": MARRIED, "hotwife": MARRIED, "dh": MARRIED, "bride": MARRIED, "girlfriend": DATING, "boyfriend": DATING, "gf": DATING, "bf": DATING, "partner": DATING, "bae": DATING,
           "significant other": DATING, "so": DATING, "other half": DATING, "better half": DATING, "fiance": ENGAGED, "fiancé": ENGAGED, "fiancee": ENGAGED, "fiancée": ENGAGED}
SPOUSE = r"(wife|husband|hubby|wifey|spouse|missus|missis|mrs|hubs|wifes|husbands|hotwife|dh|bride|girlfriend|boyfriend|gf|bf|partner|bae|significant other|so(?![- ]called)|other half|better half|fianc[ée]e?)"
STATUSES = {"single": "single", "married": MARRIED, "engaged": ENGAGED, "divorced": "divorced", "separated": "separated", "widowed": "widowed", "a widow": "widowed",
            "a widower": "widowed", "in a relationship": DATING, "taken": DATING}
RELATIONSHIP = [
    rule("relationship_status", rf"\b(?:my|our) (?:{FOND}[ ,]+){{0,3}}{SPOUSE}(?:'s)?\b(?![- ]?to[- ]be|(?:'s)? (?:in crime|at the time|back then|in (?:high school|college)|died|passed)\b)", owned(SPOUSES), TAGGED),
    rule("relationship_status", r"\bme (missus|missis|mrs|wife|husband|hubby)\b", owned(SPOUSES), TAGGED),
    rule("relationship_status", rf"^\W*(?:(?:re)?post\W*|update\W*)?(?:\d{{2}}\s*[mf]?\W*)?(?:(?:my|our)\s+)?(?:{FOND}\s+){{0,3}}(gf|girlfriend|bf|boyfriend)\b(?!\s*(?:wanted|needed|material|for\b|search|hunt|swap|request|appreciation))",
         owned(SPOUSES), TAGGED),
    rule("relationship_status", r"\b(?:me and|and i|i and|with) the (?:wife|missus|missis|mrs|hubby|husband|old lady)\b|\bthe (?:wife|missus|missis|mrs|hubby|husband) and (?:i|me|kids|the kids)\b", kept(MARRIED), TAGGED),
    rule("relationship_status", rf"\bi (?:do |also |already |currently )?(?:have|got) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))", owned(SPOUSES), SELF_HEDGE),
    rule("relationship_status", r"\b(?:mi|minha|meu|mon|ma|meine|mein|min|mijn|moja|mia|mio) (esposa|marido|esposo|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|vriendin|vriend|partner|partnerin)\b",
         group({"esposa": MARRIED, "marido": MARRIED, "esposo": MARRIED, "femme": MARRIED, "mari": MARRIED, "frau": MARRIED, "mann": MARRIED, "kone": MARRIED, "mand": MARRIED,
                "vrouw": MARRIED, "man": MARRIED, "żona": MARRIED, "moglie": MARRIED, "marito": MARRIED} | dict.fromkeys(("novia", "novio", "namorada", "namorado", "copine", "copain", "freundin", "freund", "kæreste", "vriendin", "vriend", "partner", "partnerin"), DATING))),
    rule("relationship_status", r"\b(?:happily|newly|recently|just) married\b(?= (?:man|woman|guy|girl|couple|dad|mom|and|for|with|\d)|[.!,]|$)|\b(?:our|my) (?:wedding|honeymoon|anniversary)\b(?! (?:is (?:in|next|on|this|coming|only)|will be|next|planning|budget|venue|date))"
         r"|\bmy (?:in-laws|in laws|mother-in-law|father-in-law|father in law|mother in law)\b", fixed(MARRIED)),
    rule("relationship_status", r"\b(?:my|our) (?:own |happy |long |current |second |strong |healthy |lovely |wonderful |great |good |sexless |open |\d+[- ]year )?marriage\b|\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|many|several) years (?:of marriage|married)\b"
         r"|\b(?:since|when|after|before) (?:we|i) got married\b|\b(?:we|i)(?:'ve| have) been (?:happily )?married\b(?! before)", fixed(MARRIED), SELF_HEDGE),
    rule("relationship_status", r"\b(?:i've been|i'm|im|i am|we've been|we are|we're) (?:seeing|dating) (?:someone|my|this|a|an|another|him|her)\b|\bi(?:'m| am) (?:happily |currently |now |also |still )?(?:dating|seeing) (?:a |an |someone|this|another|him|her)\b"
         r"|\bi(?:'m| am) in a (?:\w+ )?relationship\b|\bmy (?:bf/gf|gf/bf)\b|\bmy relationship\b(?! (?:with|to) (?:my )?(?:mom|mum|dad|mother|father|parents|family|brother|sister|son|daughter|kids|friends?|food|god|alcohol|money|work|job|body|self|myself|boss|religion|church|faith|weed|sleep|exercise|games?|sex|life)\b)"
         r"|\bwe(?:'re| are) (?:so |madly |deeply |still |very |both )?in love\b|\bi(?:'m| am) (?:also |happily )?partnered\b|\bpartnered (?:as well|too|up)\b|\b(?:relationship |boyfriend |girlfriend )?status:? taken\b"
         r"|\bwith (?:my )?(?:current|new) (?:partner|girlfriend|boyfriend|gf|bf)\b|\bwe(?:'ve| have) been together (?:for|since)\b", fixed(DATING)),
    rule("relationship_status", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\bmy (?:now )?ex(?: girlfriend| boyfriend| gf| bf)? (?:told|left|dumped|broke)\b|\b(?:she|he) (?:left|dumped) me\b|\bwe broke up\b"
         r"|\bi broke up with (?:my|the|him|her)\b|\b(?:she|he) broke up with me\b|\bforever alone\b|\bbeen single (?:for|since)\b|\b(?:i'm|im|i am) (?:a )?single (?:mom|mum|mother|dad|father|parent)\b", fixed("single")),
    rule("relationship_status", r"(?:\bi |(?:^|[.!?]\s*))(?:don't|do not|dont) (?:currently |even )?have (?:a |an )?(?:girlfriend|boyfriend|gf|bf|partner|significant other|wife|husband|spouse)\b|\bi(?:'ve| have)? never (?:had|been in) (?:a )?(?:girlfriend|boyfriend|gf|bf|relationship)\b",
         fixed("single"), CONDITIONAL),
    rule("relationship_status", rf"\b{I} (?:happily |currently |still |also |newly |recently |now )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|taken)\b(?! (?:to|with|by|for|from|of|about|in terms)\b)", group(STATUSES)),
    rule("relationship_status", r"\b(?:i|we) (?:just |recently |finally )?got (married|engaged|divorced)\b|\b(married) (?:for )?(?:\d+|a few|many|almost|over|nearly|about) (?:\w+ )?years\b",
         lambda match: {"married": MARRIED, "engaged": ENGAGED, "divorced": "divorced"}[next(filter(None, match.groups()))]),
    rule("relationship_status", r"\b(?:i'm|im|i am|we're|we are|we just|i just|just) (?:now |officially |recently |finally )?(?:got )?engaged\b|\b(?:our|my) engagement\b(?! (?:with|to))|\bmy (?:future|soon[- ]to[- ]be) (?:husband|wife|hubby|mrs|spouse|in[- ]laws)\b"
         r"|\bmy (?:husband|wife|hubby|bride|groom)[- ]to[- ]be\b|\b(?:planning|plan) (?:my|our) wedding\b|\b(?:our|my) wedding (?:is (?:in|next|on|this|coming|only)|will be|next (?:year|month|week)|planning|budget|venue|date)\b", fixed(ENGAGED)),
    rule("relationship_status", r"\bmy late (?:wife|husband|hubby|spouse|partner)\b|\b(?:i lost|since i lost|after i lost|after losing|since losing) my (?:wife|husband|hubby|spouse)\b|\bmy (?:wife|husband|hubby|spouse) (?:passed away|died|passed)\b", fixed("widowed")),
    rule("relationship_status", r"\bmy (?:estranged|separated) (?:wife|husband|hubby|spouse)\b|\bmy (?:stbx\w*|soon[- ]to[- ]be[- ]ex(?:[- ]\w+)?)\b|\b(?:we're|we are|we've been|we have been|we recently|we just) (?:\w+ )?separated\b", fixed("separated")),
    rule("relationship_status", r"\b(married) (?:man|woman|guy|dad|mom|mother|father|couple|male|female)\b", kept(MARRIED)),
    rule("relationship_status", r"(?:^\W*(?:\d{2}\s*)?(?:[\[\(]\w+[\]\)]\s*)?(?:(?!he |she |they |you |who |we |got |get |not |never |was |were |be |been |is |are )\w+ )?married\b"
         r"|\bmarried(?:/| and | )(?:dl|discreet|curious|bi|man|woman|guy|milf|dad|mom|couple|but|white|black|hwp|male|female|m|f)\b)", kept(MARRIED), TAGGED),
]

CHILD = (r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|boys|girls|boy|girl|"
         r"grandkids|grandchildren|grandsons?|granddaughters?|first ?born|lo|dc|dcs|bio kids|youngest|oldest|eldest|middle child)")
AGE = r"(?:\d+|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks)?(?:[- ]old)?"
QUALIFIER = (rf"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|"
             r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)")
INFANT = re.compile(r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|crib|cot\b|formula|feeds?\b|feeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|bottle|sleep regression|stroller|pram|onesie|bassinet|car seat|"
                    r"\blo\b|kindergarten|preschool|school|daughter|son\b|mama|mommy|crawl|walking|talking|nap")


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
    rule("parental_status", r"\b(?:i|we) (?:also |both |still )?(?:have|had|got|'ve got|have got|raised|am raising|'re raising|are raising) (?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}"
         r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)",
         kept("has children"), SELF_HEDGE),
    rule("parental_status", rf"\b(?:{I}|as) (?:a |an )?(?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b"
         r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))", kept("has children")),
    rule("parental_status", r"\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", kept("has children"), SELF_HEDGE),
    rule("parental_status", r"\b(?:mom|mum|mama|dad|parent) here\b|\b(?:sahm|sahd|wahm|wohm|sahp)\b|\bboy ?mom\b|\bgirl ?mom\b|\b(?:in|join) the (?:\w+ )?(?:mom|mum|grandma|dad|parent|grandparent)s? club\b", kept("has children"), SELF_HEDGE),
    rule("parental_status", rf"(?:\b{I} an? |\bas an? |^\W*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[-|:]\s+)(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|step|solo|widowed|separated|older|hot|bored|lonely|tired) (?:dad|mom|mum|father|mother|mama|parent)\b(?!s)",
         kept("has children"), SELF_HEDGE),
    rule("parental_status", r"\b(?:meine?n?|mein|mi|mis|mon|ma|mes|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|miei)\s+(?:\w+\s+)?(?:tochter|sohn|kinder|söhne|töchter|hijo|hija|hijos|hijas|fils|fille|enfants|filho|filha|filhos|filhas|zoon|dochter|kinderen|córka|syn|dzieci|figlio|figlia|figli)\b"
         r"|\b(?:ich habe|ich hab|tengo|j'ai|eu tenho|ik heb|ho) (?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre) (?:\w+ )?(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia)\b",
         fixed("has children"), SELF_HEDGE),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:\d+ ?(?:weeks?|months?) )?postpartum\b|\bmy postpartum\b|\b\d+ ?(?:weeks?|months?|days?) postpartum\b|\b(?:since|after|when|before) (?:giving birth|i gave birth|having my|i had my)\b|\bi gave birth\b|\bmy last pregnancy\b"
         r"|\bmy (?:c-section|c section|labor and delivery|birth story|epidural|maternity leave|paternity leave)\b|\bi(?:'m| am)? (?:still |exclusively |currently )?(?:breastfeeding|breastfed|ebf)\b|\bbreastfeeding my\b|\bnursing my (?:son|daughter|baby)\b", fixed("has children"), SELF_HEDGE),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:currently |now |finally |also )?(?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+(?:\+\d)? ?(?:weeks?|wks?|months?) pregnant\b|\b(?:i'm|im|i am|we're|we are) expecting(?= (?:a baby|our|my|twins|baby|a little|a boy|a girl|in|again)\b|[.!,]|$)"
         r"|\bmy (?:first |second |third |current |\d+(?:st|nd|rd|th) )?pregnancy\b|\b(?:my|our) (?:unborn|baby bump)\b|\bpregnant with (?:my|our) (?:first|second|third|\d|rainbow|twins|baby)\b|\bbaby (?:#|number )?\d on the way\b|\b(?:our|my) baby on the way\b", fixed("expecting a child")),
    rule("parental_status", r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\b(?:i'm|im|i am|we're|we are) (?:\w+ )?child-?free\b|\bno kids of my own\b|\bi(?:'ve| have) never had (?:kids|children)\b|\bwe (?:don't|do not|dont) have (?:any )?(?:kids|children)\b"
         r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b", fixed("no children"), CONDITIONAL),
]

DOG = (r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt|labrador|labradors|golden retrievers?|goldens|goldendoodle|labradoodle|bernedoodle|cavapoo|cockapoo|maltipoo|german shepherds?|australian shepherds?|gsd|huskies|husky|corgis?|chihuahuas?|poodles?|beagles?|"
       r"dachshunds?|doxies?|wiener dog|weiner dog|pugs?|bulldogs?|frenchies?|french bulldog|rottweilers?|rotties?|dobermans?|great danes?|shih tzus?|yorkies?|terriers?|pit ?bulls?|pitties?|pittie|staffies?|staffy|collies?|border collies?|heelers?|cattle dog|malinois|mastiffs?|greyhounds?|"
       r"whippets?|schnauzers?|maltese|pomeranians?|spaniels?|retrievers?|weimaraners?|vizslas?|akitas?|shibas?|shiba inu|samoyeds?|malamutes?|bernese|berners?|shelties?|bichons?|havanese|papillons?|bassets?|bloodhounds?|coonhounds?|hounds?|dalmatians?|basenjis?|cane corsos?|pyrenees)")
CAT = r"(?:cats?|kittens?|kitty|kitties|catto|kitteh|tabby|calico|tortie|maine coon|ragdoll|siamese|sphynx)"
OTHER = (r"(?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|birds?|chickens?|hens|ducks?|goats?|horses?|pony|ponies|ball pythons?|corn snakes?|pet snakes?|"
         r"geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|fish|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|rats|mini pigs?|pet pigs?|alpacas?|llamas?|donkeys?|aquarium|fish tank)")
OWN = (r"\b(?:my|our) (?:(?!(?:friends|parents|moms|dads|mums|neighbors|neighbours|brothers|sisters|sons|daughters|boyfriends|girlfriends|bfs|gfs|cousins|grandmas|grandparents|roommates|aunts|uncles|exs|exes|kids|bosses|"
       r"husbands|wifes|future|dream|next|neighbor|neighbour|friend|sister|brother|family|families|childhood)\b)[a-z\d-]+ ){0,3}")
HAVE = r"\b(?:i|we) (?:also |both |still )?(?:have|had|got|'ve got|own|adopted|rescued|recently adopted|just adopted|just got) (?:a |an |two |three |four |\d+ )?(?:[a-z-]+ ){0,2}"
FELINE = re.compile(r"\bcats?\b|\bkitten|meow|litter|purr|feline|\bvet\b|catnip|scratching post|\bfur\b|indoor|outdoor|feral|adopt|rescue")


def pet(kind):
    def value(match):
        if not free(match):
            return None
        if kind == "cat" and match.group(1) in ("kitty", "kitties") and not FELINE.search(match.string):
            return None
        if kind == "other pet":
            return kind
        return kind
    return value


PETS = [
    rule("pets", rf"{OWN}({DOG})(?:'s)?\b", pet("dog"), TAGGED),
    rule("pets", rf"{OWN}({CAT})(?:'s)?\b(?! (?:litter )?(?:is wet|pussy))", pet("cat"), TAGGED),
    rule("pets", rf"{OWN}({OTHER})(?:'s)?\b(?! (?:tacos?|sticks?|and chips|fillets?|fry|sauce|oil|vibe|vibrator|toy|wings|nuggets|breasts?|dinner|soup|curry|thighs|eggs|farm)\b)", pet("other pet"), TAGGED),
    rule("pets", rf"{HAVE}({DOG})\b(?! (?:in (?:this|the) (?:fight|race)|food|treats?)\b)", pet("dog"), SELF_HEDGE),
    rule("pets", rf"{HAVE}({CAT})\b", pet("cat"), SELF_HEDGE),
    rule("pets", rf"\b(?:{I} an? |as an? )(?:proud |crazy |\w+ )?(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner|lady|person)\b|\b(dog|cat) (?:mom|mum|dad|mama|parent) here\b",
         lambda match: pet("dog" if (match.group(1) or match.group(2)) == "dog" else "cat")(match), SELF_HEDGE),
    rule("pets", r"\bi (?:don't|do not|dont) have (?:any )?pets\b|\bi have no pets\b|\bwe (?:don't|do not|dont) have (?:any )?pets\b|\bno pets here\b", fixed("no pets"), CONDITIONAL),
]

LIVING = [
    rule("living_with", r"\bi live (alone|by myself|on my own)\b", fixed("alone")),
    rule("living_with", r"\bi (?:still )?live (?:at home )?with my (?:parents|mom|dad|mum|mother|father|folks|family)\b|\bi(?:'m| am) living with my parents\b|\bi live at home\b", fixed("parents")),
    rule("living_with", r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse|sister|brother|son|daughter|aunt|uncle|cousin)\b|\bwe live together\b", fixed("partner or family")),
    rule("living_with", r"\bmy (?:roommates?|roomates?|flatmates?|housemates?)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b", fixed("roommates")),
    rule("living_with", r"\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b"
         r"|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|hubby) and i (?:live|share (?:a|an|our)|rent|bought (?:a|our)|own (?:a|our)|have (?:a|an|our) (?:house|home|apartment|place|flat))\b|\bwho lives with me\b"
         r"|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))", fixed("partner or family"), SELF_HEDGE),
    rule("living_with", r"\bi (?:have )?(?:lived|live|am living|'m living|still live) (?:at home )?with my (?:mom and dad|parents|mom|dad|mum|mother|father|folks|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi live at home\b|\bliving at home with\b", fixed("parents"), SELF_HEDGE),
    rule("living_with", r"\b(?:my|our) (?:\w+ )?(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b", fixed("roommates"), SELF_HEDGE),
    rule("living_with", r"\bi live (?:all )?(alone|by myself|on my own)\b|\bliving (?:alone|by myself|on my own)\b|\bhappy alone\b|\bi'm (?:all )?alone\b", fixed("alone"), SELF_HEDGE),
]

HOUSING = [
    rule("housing", r"\bi (?:own|bought) (?:a|my|our) (?:\w+ )?(?:house|home|condo|townhouse|townhome)\b|\b(?:my|our) mortgage\b|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:\w+ )?(?:house|home|condo)\b|\bwhen (?:i|we) bought (?:my|our) (?:house|home)\b"
         r"|\b(?:my|our) (?:hoa|property tax(?:es)?|home ?owners? insurance|homeowner's insurance|home insurance)\b|\bselling (?:my|our) (?:house|home|condo)\b|\bin the middle of selling the house\b", fixed("homeowner")),
    rule("housing", r"\bmy (?:landlord|lease)\b|\bi rent (?:a|an|my)\b|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bmy rent (?:is|went)\b|\bour (?:landlord|landlady|lease|leasing office|property manager|property owner|rent)\b|\bmy (?:landlady|leasing office|property manager)\b"
         r"|\b(?:our|my) security deposit\b|\bwe(?:'re| are) (?:currently )?renting\b", fixed("renter")),
    rule("housing", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bi live in my car\b|\bi(?:'m| am) (?:living|sleeping) in (?:my|a) (?:car|van|tent|shelter)\b", fixed("homeless")),
]

RELIGIONS = {"christian": "christian", "catholic": "christian", "protestant": "christian", "mormon": "christian", "lds": "christian", "baptist": "christian", "methodist": "christian",
             "lutheran": "christian", "evangelical": "christian", "orthodox christian": "christian", "muslim": "muslim", "jew": "jewish", "jewish": "jewish", "hindu": "hindu",
             "buddhist": "buddhist", "sikh": "sikh", "pagan": "pagan or other religion", "wiccan": "pagan or other religion", "witch": "pagan or other religion",
             "spiritual": "spiritual, no religion", "agnostic": "agnostic", "atheist": "atheist", "not religious": "atheist"}
FAITH = "|".join(map(re.escape, RELIGIONS))
BELIEVER = r"(?=[^\w ]| (?:man|woman|person|guy|girl|lady|dude|mom|mum|dad|mother|father|myself|i|we|my|and|but|who|it|this|that|though|growing|raised|convert|believer|here|too|as well|now|so|because|since|for)\b|$)"
MUSLIM = re.compile(r"\b(?:allah|inshallah|insha'?allah|alhamdulillah|mashallah|ameen|quran|mosque)\b")

RELIGION = [
    rule("religion", rf"\b{I} (?:a |an |also a |also an |a devout |a practicing |a practising |a lifelong |a proud |an? ex-?\w+ turned )?({FAITH})\b{BELIEVER}", group(RELIGIONS)),
    rule("religion", rf"\bas an? (?:\w+ )?({FAITH})\b{BELIEVER}", group(RELIGIONS)),
    rule("religion", r"\bmy (?:faith|church|mosque|synagogue|temple|pastor|priest|rabbi|imam|bible|quran|parish|congregation|shul|gurdwara|mandir|coven|sangha)\b|\bi (?:go to|attend) (?:church|mass|mosque|synagogue|temple|shul|gurdwara)\b|\bi pray\b|\bas a (?:believer|follower of (?:christ|jesus))\b",
         lambda match: {"mosque": "muslim", "quran": "muslim", "imam": "muslim", "synagogue": "jewish", "rabbi": "jewish", "shul": "jewish", "temple": "hindu", "mandir": "hindu", "gurdwara": "sikh", "coven": "pagan or other religion", "sangha": "buddhist"}.get(
             next((word for word in ("mosque", "quran", "imam", "synagogue", "rabbi", "shul", "temple", "mandir", "gurdwara", "coven", "sangha") if word in match.group()), ""), "muslim" if MUSLIM.search(match.string) else "christian"), SELF_HEDGE),
    rule("religion", r"\b(?:allah|inshallah|insha'?allah|alhamdulillah|mashallah|masha'?allah|jazakallah|subhanallah|prophet muhammad|astaghfirullah|ameen)\b|\b(?:ramadan|eid) mubarak\b|\bmy (?:salah|wudu|deen|hijab)\b", fixed("muslim"), SELF_HEDGE),
    rule("religion", r"\b(?:bible study|my bible|jesus is my|my lord and savior|my savior|my saviour|christ is king|my rosary|i'm (?:a )?catholic|as a catholic|i(?:'m| am) (?:a )?born[- ]again|i accepted (?:jesus|christ))\b", fixed("christian"), SELF_HEDGE),
    rule("religion", r"\bi converted to (islam|christianity|judaism|catholicism|buddhism|hinduism|orthodoxy|sikhism)\b",
         group({"islam": "muslim", "christianity": "christian", "judaism": "jewish", "catholicism": "christian", "buddhism": "buddhist", "hinduism": "hindu", "orthodoxy": "christian", "sikhism": "sikh"}), SELF_HEDGE),
    rule("religion", r"\b(?:shabbat shalom|chag sameach|my (?:bar|bat) mitzvah)\b", fixed("jewish"), SELF_HEDGE),
    rule("religion", r"\b(?:waheguru|jai shri ram|har har mahadev|om namah shivaya)\b", lambda match: "sikh" if "waheguru" in match.group() else "hindu", SELF_HEDGE),
    rule("religion", r"\bi(?:'m| am) not (?:a )?religious(?: person)?\b|\bi (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|\bi loathe (?:all )?religion\b|\bspiritual,? but not religious\b|\bя не религиозн|\bno soy religios[oa]\b|\bich bin nicht religiös\b",
         lambda match: "atheist" if "god" in match.group() or "loathe" in match.group() else "spiritual, no religion", TAGGED),
]

POLITICS = {"communist": "communist or far left", "marxist": "communist or far left", "socialist": "socialist or left", "leftist": "socialist or left", "liberal": "progressive or liberal",
            "progressive": "progressive or liberal", "democrat": "progressive or liberal", "centrist": "centrist or moderate", "moderate": "centrist or moderate",
            "conservative": "conservative or right", "republican": "conservative or right", "libertarian": "libertarian", "anarchist": "anarchist",
            "nationalist": "nationalist or far right", "apolitical": "apolitical", "lefty": "socialist or left"}
PARTY = "|".join(POLITICS)
POLITICAL = [
    rule("political_identity", rf"\b{I} (?:a |an |also a |also an |a lifelong |a proud |a registered |pretty |very |fairly |quite )?({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|with|about|when|in terms|on|in my|of)\b)", group(POLITICS)),
    rule("political_identity", rf"\bas an? (?:\w+ )?({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?)\b)", group(POLITICS)),
    rule("political_identity", rf"(?:^|[.!?,;(] *)({PARTY}) here\b|\bfellow ({PARTY})s?\b", lambda match: POLITICS[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("political_identity", r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly on|solidly on|squarely on|also on)[*_]* the [*_]*(?:far[- ])?(left|right)\b|\b(?:i'm|im|i am|i m) (?:pretty |very |far |more |center |centre |a |fairly |quite )?(left[- ]wing|right[- ]wing|left[- ]leaning|right[- ]leaning|leftist|lefty|far[- ]left|far[- ]right|center[- ]left|centre[- ]left|center[- ]right|centre[- ]right)\b",
         lambda match: "socialist or left" if "left" in (match.group(1) or match.group(2)) or "lefty" in (match.group(1) or match.group(2)) else "conservative or right", SELF_HEDGE),
]

DIETS = {"vegan": "vegan", "vegetarian": "vegetarian", "veggie": "vegetarian", "pescatarian": "pescatarian", "pescetarian": "pescatarian", "keto": "keto or low carb",
         "halal": "halal or kosher", "kosher": "halal or kosher", "gluten free": "gluten free", "gluten-free": "gluten free"}
DIET = [
    rule("diet", rf"\b{I} (?:a |an |also a |also |a strict |fully |mostly |now )?(vegan|vegetarian|veggie|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)", group(DIETS)),
    rule("diet", r"\bas an? (vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)", group(DIETS)),
    rule("diet", r"\bi (?:eat|love) meat\b|\bi'?m a (?:meat eater|carnivore|omnivore)\b", fixed("eats everything")),
    rule("diet", r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian) here\b|\b(?:i've been|i went|been|went|i became|i turned) (vegan|vegetarian|pescatarian)\b", lambda match: DIETS[match.group(1) or match.group(2)], SELF_HEDGE),
]

SMOKING = [
    rule("smoking", r"\bi (?:smoke|vape)(?: cigarettes| cigs| a pack| daily| every day)?\b(?! (?:weed|pot|a joint|joints|blunts|cannabis|marijuana|meat|out)\b)|\b(?:i'm|im|i am) a (?:heavy |chain |social )?smoker\b|\bas a smoker\b|\bmy (?:vape|cigarettes)\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\bi (?:don't|do not|dont|never) smoke\b|\bi quit smoking\b|\b(?:i'm|im|i am) a non-?smoker\b|\bi've never smoked\b", fixed("non-smoker"), CONDITIONAL),
    rule("smoking", r"\b(?:i|me) (?:\w+ )?(?:smoke|smoked|vape|vaped) (?:for|to|after|before|when|every|a|cigarettes|cigs|daily)\b|\bmy (?:cigarettes?|cigs|vape|juul|pack of|smoke break|cigarette break)\b|\b(?:i'm|im|i am) a (?:heavy |chain |social |casual )?(?:smoker|vaper)\b"
         r"|\bi(?:'ve| have) been (?:smoking|vaping) (?:for|since)\b|\bi smoke (?:a|\d+|two) packs?\b|\bich rauche\b|\bwir rauchen\b|\brauchen den\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\bnon[- ]?smoker\b|\b(?:i|we) don'?t smoke\b", fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
]

MILITARY = [
    rule("military_status", rf"(?P<serving>\b{I} (?:currently |still )?(?:in|serving in|enlisted in) the (?:army|navy|marines|air force|military|national guard|coast guard|marine corps|reserves|space force)\b|\b{I} (?:on )?active duty\b|\b{I} (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service ?member|infantryman|paratrooper)\b|\b{I} (?:currently )?(?:deployed|stationed)\b|\bmy (?:unit|platoon|squadron|battalion|deployment|chain of command|first sergeant|drill sergeant|commanding officer|nco|squad leader)\b)"
         rf"|(?P<veteran>\b(?:{I}|as) (?:a |an )?(?:proud |disabled |combat |retired |former |old )?(?:(?:army|navy|marine|marine corps|air force|military|usmc|combat|iraq|afghanistan|war|coast guard) )?(?:vet|veteran)\b(?! (?:tech|clinic|bill|school|student)\b)|\bwhen i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|\bi (?:served|was) in the (?:army|navy|marines|air force|military|coast guard|marine corps)\b|\bi served (?:my country|\d+ years|overseas|(?:two|three|four|\d) tours)\b|\bi (?:got out of|retired from|separated from) the (?:army|navy|marines|air force|military|service)\b|\bretired (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force)\b)",
         lambda match: "serving in the military" if match.group("serving") else "military veteran", SELF_HEDGE),
]

RULES = [*RELATIONSHIP, *PARENTAL, *PETS, *LIVING, *HOUSING, *RELIGION, *POLITICAL, *DIET, *SMOKING, *MILITARY]
