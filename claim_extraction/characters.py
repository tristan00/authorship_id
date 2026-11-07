import re
from pathlib import Path

from .common import SELF_HEDGE, hedged
from .fandom import CANDIDATE, CASED, COMMON, NAME, NEGATIVE, PLAIN, POSITIVE as LIKING, SELF, TRAILING
from .literals import scan
from .schema import fan_value

KIND = r"(?:characters?|chars?|pokemon|pokémon|heroe?s?|heroines?|villains?|antagonists?|protagonists?|waifus?|husbandos?|girls?|boys?|champions?|champs?|agents?|operators?|legends?|survivors?|killers?|servants?|units?|fighters?|brawlers?|princess(?:es)?|princes?|digimon|starters?|legendar(?:y|ies)|gundams?|mobile suits?|mechs?|robots?|monsters?|bosses|boss|companions?|npcs?|ships?|couples?|pairings?|duos?|ninjas?|shadows?|mains?|5 stars?|5\*|4 stars?|4\*|warframes?|frames?|resonators?|valkyries?|idols?|trainers?|gym leaders?|members?|ocs?|dolls?|figures?|mcs?|mc's|commanders?|leaders?|picks?)"
TIER = r"(?:all[- ]time |absolute |personal |current |top |new |second |2nd |third |3rd |most |favou?rite |very |)*"
FAVOURITE = r"(?:favou?rites?|faves?|favs?|fav(?:ou?)?rite|fave?ou?rite)"
ADVERB = r"(?:really |absolutely |just |also |still |honestly |genuinely |do |totally |fucking |friggin |so |personally |lowkey |low key |kinda |kind of |sort of |sorta |actually |always |will always |definitely |truly |only |even |especially |generally |particularly |simply |mostly |mainly |secretly |unironically |legit |def |deeply |too |)*"
ANY = r"((?:[Tt]he )?[\w'.&+-]+(?: [\w'.&+-]+){0,3})"
LEXICON = Path(__file__).with_name("character_names.tsv")


def lexicon():
    plain, cased, lower = {}, {}, {}
    with open(LEXICON, encoding="utf-8") as rows:
        next(rows)
        for line in rows:
            key, _, _, links, surfaces, common = line.rstrip("\n").split("\t")
            if surfaces:
                for surface in surfaces.split("|"):
                    cased[surface] = max(cased.get(surface, 0), int(links))
                    if int(links) >= 3 and not common and surface.isalpha() and surface.istitle():
                        lower[surface.lower()] = surface
            else:
                plain[key] = int(links)
    return plain, cased, lower


CHARACTERS, SURFACES, LOWERCASED = lexicon()
RARE = frozenset(LOWERCASED)
OTHERS = {key for key, entries in PLAIN.items() if all(entry[0] != "character" for entry in entries)} | {surface.lower() for surface, entries in CASED.items() if all(entry[0] != "character" for entry in entries)}
STOP = re.compile(r"[.!?:;\n(]|(?i:\s(?:and then|right there|here|there|but|because|cause|bc|since|who|which|that|when|as|from|in|on|at|is|was|are|were|so|too|for|with|lol|lmao|haha|tbh|honestly|now|though|tho|more|the most|a lot|much|over|than|if|to|by|of all time|ever|right now|atm|i|he|she|they|it|my)\b)")
LISTED = re.compile(r"\s*(?:,|/|&|\band\b|\bor\b|\bx\b)\s*")
GENERIC = frozenset("i i'm im me my mine you your he him his she her they them their we us our it its it's this that these those the a an all any every everyone everything some someone something one ones "
                    "character characters game games show anime manga movie film series book books guy guys girl girls boy boys man woman people dude bro lol ok okay yes no yeah here there "
                    "now today then also just really very so much more most both either each other others another what who how why when where which not no none nothing "
                    "playing play using use being having doing going getting watching reading such only neither hello calling absolutely probably actually seriously totally truly genuinely "
                    "perhaps sometimes always lately currently recently especially mostly mainly usually basically obviously clearly surely personally easily".split()) | COMMON
ROLES = frozenset("support supports tank tanks dps healer healers heal jungle jungler mid top adc bot carry assassin assassins mage mages marksman fighter fighters "
                  "melee ranged caster casters sniper snipers striker defender attacker sword spear bow gun guns hammer lance axe axes staff dagger daggers fist fists "
                  "random it them her him".split())
STRONG = scan(r"(?i:\b(?:characters?|char|main|maining|mains|mained|waifu|husbando|ship|shipped|shipping|otp|arc|villain|protagonist|antagonist|cosplay|kit|banner|pulls?|pulled|lore|canon|fanart|fan art|"
                    r"backstory|personality|design|voice lines?|skins?|pokemon|pokémon|hero|heroes|champions?|anime|manga|episode|season|chapter)\b)")
ADJECTIVAL = r"(?:characters?|quests?|story|storyline|menu|thread|events?|reason|issues?|problems?|point|focus|goals?|cast|villains?|antagonists?|protagonists?|heroe?s?|heroines?|plot|themes?|road|street|entrance|course|dish|page|account|sub|line|stats?|weapons?|deck|team|job|class|game|mode|campaign|boss|area|hub|city|base|source|thing|things|part|parts|topic|topics|hobb(?:y|ies)|kinks?|car|language|value|tips?|riff|attraction|draw|selling point|ingredient|pon(?:y|ies))"
POSITIVE = r"(?:good|great|cool|amazing|awesome|interesting|fun|compelling|lovable|loveable|likable|likeable|well[- ]written|underrated|beautiful|fantastic|wonderful|best|fascinating|incredible|complex|badass|hilarious|funny|sweet|cute|adorable|perfect|brilliant|iconic|memorable|relatable|unique|fire|peak|goated|elite|top tier|god tier|strong|nice|hot|sexy|fine|gorgeous|lovely|precious|baddest|coolest|hottest|cutest|greatest|realest|funniest)"
MEDIA = r"(?i:series|movies?|films?|games?|franchise|books?|novels?|shows?|music|songs?|albums?|level design|scents?|lore|universe|trilogy|saga|comics?|manga|anime|cartoons?|era|style|soundtrack|ost|band|brand|products?|stuff|team|version|remake|reboot|episodes?|seasons?|chapters?)"
NOUNS = rf"(?:{MEDIA}|ways?|things?|parts?|moments?|segments?|lines?|quotes?|scenes?|models?|builds?|places?|foods?|drinks?|colou?rs?|flavou?rs?|brands?|cars?|days?|times?|kinds?|types?|sets?|cards?|items?|weapons?|maps?|levels?|modes?|classes|races|factions?|guns?|looks?|players?|teams?|athletes?|drivers?|bands?|singers?|artists?|authors?|writers?|actors?|actress(?:es)?|youtubers?|streamers?|podcasts?|channels?)"
ASPECT = scan(r"\s*(?i:character|design|personality|arc|voice|story|storyline|kit|outfit|look|vibe|energy|backstory|lines?|scenes?|moments?|dialogue|development|growth|fights?|theme|attitude|animations?|abilities|ability|skills|model|portrayal|combat|gameplay|playstyle|moveset|powers?|humou?r|relationship|dynamic|interactions?|expressions?|smile|face|hair|eyes|laugh|style|aesthetic|songs?|ult|ultimate|skins?|art|writing|journey|redemption|quotes?)\b")
DEAR = r"(?:king|queen|baby|babygirl|wife|husband|man|boy|girl|everything|beloved|goat|son|daughter|husbando|waifu|bae|crush|princess|prince|goddess|pookie|precious|love|one true love|comfort character)"


def known(name, least=1):
    return max(CHARACTERS.get(name.lower(), -1), SURFACES.get(name, -1)) >= least


def foreign(name):
    return name.lower() in OTHERS and not known(name, 0)


NUMERAL = re.compile(r"\d+(?:st|nd|rd|th|s|am|pm)$|(?:19|20)\d\d$")


def pieces(name, last=False):
    head = STOP.split(" " + name + " ")[-1 if last else 0].strip()
    head = re.sub(r"(?:'s|s'|’s)\b.*$", "", head)
    for piece in LISTED.split(head):
        piece = TRAILING.sub("", re.sub(r"^(?:[Tt]he|[Mm]y|[Oo]ur|[Ff]ellow|[Aa]s an?|[Aa]n?) ", "", piece)).strip(" *_\"'()[]~")
        if piece.islower():
            piece = " ".join(re.split(r" (?:the|a|an|this|that|some|every|all|other|last|next) ", piece)[0].split()[:3])
        words = piece.lower().split()
        if words and words[0] not in GENERIC and words[-1] not in GENERIC and piece.lower() not in ROLES and 1 < len(piece) <= 40 and re.search(r"[^\W\d_]", piece) and not NUMERAL.match(words[0]):
            yield piece


def sentence(text, position):
    return max(text.rfind(mark, 0, position) for mark in ".!?\n") + 1, min((end for end in (text.find(mark, position + 1) for mark in ".!?\n") if end >= 0), default=len(text))


def emit(name, found, text, position, gate, last=False):
    for piece in pieces(name, last):
        if gate == "known" and (piece.lower() in OTHERS or not known(piece)):
            continue
        if gate == "medium" and not known(piece, 0) and (foreign(piece) or not STRONG.search(text, *sentence(text, position))):
            continue
        if gate == "named" and foreign(piece):
            continue
        if gate == "rare" and (piece.lower() in OTHERS or piece.lower() not in LOWERCASED):
            continue
        if value := fan_value("character", piece.lower()):
            found.setdefault(("character", value), position)


WORD = re.compile(r"[a-z0-9]+|<3|[❤♥💕💖💜💙💛💚🩷😍🥰]")
I = frozenset({"i"})
MY = frozenset({"my"})
MAINS = frozenset("main mains mained maining trick onetrick twotrick otp".split())
FAVS = frozenset("fav favs fave faves favorite favorites favourite favourites favrite favrites faveorite faveourite".split())
LIKES = frozenset("love loved adore adored like liked stan simp prefer obsessed sucker soft thing".split())
DEARS = frozenset("king queen baby babygirl wife husband man boy girl everything beloved goat son daughter husbando waifu bae crush princess prince goddess pookie precious love true comfort".split())
CHARMING = frozenset("cute adorable hot sexy fine badass goated peak mommy daddy queen king girl boy precious lovable loveable baddie slay iconic underrated legend goat gorgeous beautiful stunning handsome cutest hottest sexiest prettiest sweetest coolest baddest cutie sweetheart menace wholesome endearing charming favorite fave fav favourite best greatest".split())
HEARTS = frozenset("<3 ❤ ♥ 💕 💖 💜 💙 💛 💚 🩷 😍 🥰".split())
RULES = (
    ("main", re.compile(rf"(?i:\bi(?:'m| am)? (?:also |still |mostly |mainly |usually |always |only |just |now |currently |exclusively |primarily )?(?:main|mained|maining|one[- ]?trick|two[- ]?trick|otp|play as|playing as) ){ANY}"), "any", (I, MAINS | {"play", "playing"})),
    ("mains", re.compile(rf"(?:(?i:\b(?:an?|as an?|fellow|other|us|we|i'?m an?|im an?|i am an?|i'?m|i am|im|been an?|being an?|i play) ))({NAME}|[a-z][\w'-]*)(?i: (?:main|mains|one[- ]?trick|two[- ]?trick|otp)\b(?! {ADJECTIVAL}))"), "any", (MAINS,)),
    ("main_tag", re.compile(rf"(?m:^[\W_]*){NAME}(?i: (?:main|mains|otp|one[- ]?trick)(?= here\b| btw\b| and\b| since\b| for\b| who\b|\s*[,.!:\n]|\s*$))"), "any", (MAINS,)),
    ("my_main", re.compile(rf"(?i:\bmy (?:current |new |og |first |only )?(?:mains?|main character|main girl|main boy|one[- ]?trick)(?: (?:is|are|was|has been|have been|include|includes|remains)|:)\s+){ANY}"), "any", (MY, MAINS)),
    ("play", re.compile(rf"(?i:\bi (?:mostly |usually |always |only |mainly |still |also |)(?:play|played|use|used) ){NAME}"), "known", (I, {"play", "played", "use", "used"})),
    ("fav_kind", re.compile(rf"(?i:\b(?:one of )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}(?: of all time| ever| right now| atm| at the moment| so far| by far| in the (?:game|show|series|anime|manga|book))? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*){ANY}"), "any", (MY, FAVS)),
    ("fav_plain", re.compile(rf"(?i:\b(?:one of )?my {TIER}{FAVOURITE}(?: of all time| ever| right now| atm| at the moment| so far| by far)? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*|\b(?:other )?{FAVOURITE} of mine (?:are|include|is)\s+){NAME}"), "medium", (FAVS,)),
    ("favored_kind", re.compile(rf"{NAME}(?i: (?:is|are|was|were|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), "any", (MY, FAVS)),
    ("favored_apposition", re.compile(rf"{NAME}(?i:, (?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), "known", (MY, FAVS)),
    ("fav_kind_direct", re.compile(rf"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) {KIND},? ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), "known", (MY, FAVS)),
    ("favored_list", re.compile(rf"{NAME}(?i:,? (?:are |is |)(?:also |definitely |)(?:one of|among|some of) my {TIER}{FAVOURITE}\b(?! (?:\w+ ){{0,2}}{NOUNS}\b))"), "medium", (MY, FAVS)),
    ("fav_direct", re.compile(rf"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), "medium", (MY, FAVS)),
    ("favored_plain", re.compile(rf"{NAME}(?i: (?:is|are|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}(?:{FAVOURITE}|goat|comfort character|top \d)s?\b(?! (?:\w+ ){{0,2}}{NOUNS}\b))"), "medium", (MY, FAVS | {"goat", "goats", "comfort", "top"})),
    ("labelled", re.compile(rf"(?im:^\W*(?:my )?{FAVOURITE} (?:\w+ )?{KIND}\W*[:=-]\s*){NAME}"), "any", (FAVS,)),
    ("best_girl", re.compile(rf"(?i:\bbest (?:girl|boy|waifu|husbando)s?,? (?:is |goes to |= |: |)){NAME}|{NAME}(?i:,? (?:is |= )?(?:the |my |)best (?:girl|boy|waifu|husbando)\b)"), "any", ({"best"}, {"girl", "girls", "boy", "boys", "waifu", "waifus", "husbando", "husbandos"})),
    ("beloved", re.compile(rf"{NAME},? (?i:my (?:beloved|one true love|comfort character|precious|(?:glorious |beloved |)(?:goat|king|queen|waifu|husbando|babygirl))\b)"), "any", (MY, {"beloved", "true", "comfort", "precious", "goat", "king", "queen", "waifu", "husbando", "babygirl"})),
    ("my_beloved", re.compile(rf"(?i:\bmy (?:beloved|precious|glorious|queen|king|goddess|husbando|waifu|princess|prince|pookie|goat|boi|bbg) ){NAME}"), "any", (MY, {"beloved", "precious", "glorious", "queen", "king", "goddess", "husbando", "waifu", "princess", "prince", "pookie", "goat", "boi", "bbg"})),
    ("is_my", re.compile(rf"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |)my {DEAR}\b)"), "any", (MY, DEARS)),
    ("is_my_adorned", re.compile(rf"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |also |)my (?:[a-z-]+ ){{1,2}}(?:{DEAR}|hero|heroine)\b)"), "known", (MY, DEARS | {"hero", "heroine"})),
    ("loved", re.compile(rf"(?i:\b(?:i(?:'m| am|'ll|'ve| have)?|im) {ADVERB}(?:lo+ve|adore|like|lo+ved|adored|liked|stan|simp for|prefer|obsessed with|am a sucker for|have a soft spot for|have a thing for|(?:had|have|developed) a (?:huge |big |massive |little |small |slight |)crush on) ){NAME}\b"), "named", (I | {"im"}, LIKES | {"loove", "looove", "loooove", "crush"})),
    ("loved_how", re.compile(rf"(?i:\bi {ADVERB}(?:love|adore|like|loved|liked|adored) (?:how|that|when|the way) ){NAME}"), "medium", (I, {"love", "adore", "like", "loved", "liked", "adored"}, {"how", "that", "when", "way"})),
    ("as_character", re.compile(rf"{NAME}(?i:(?:'s| is| was|,)? (?:such |so |soo+ |a |an |the |one of the |my |honestly |really |genuinely |easily |still |also |very |pretty |fucking |most |)*{POSITIVE}(?:(?:,| and|, and) (?:most |very |so |)\w+)? (?:characters?|char|protagonist|villain|antagonist|hero|heroine|girl|boy|design)\b| as a character\b)"), "medium", ({"character", "characters", "char", "protagonist", "villain", "antagonist", "hero", "heroine", "girl", "boy", "design"},)),
    ("fan", re.compile(rf"(?i:\b(?:i'?m|im|i am|as|been|being|i've been|from) (?:an? |the )?(?:huge |big |massive |die[- ]?hard |long ?time |proud |true |real |giant |hardcore |super |casual |)*){NAME}(?i: (?:fan|stan|fanboy|fangirl|simp|lover|enjoyer)s?\b)"), "known", ({"fan", "fans", "stan", "stans", "fanboy", "fanboys", "fangirl", "fangirls", "simp", "simps", "lover", "lovers", "enjoyer", "enjoyers"},)),
    ("heart", re.compile(rf"(?m:^[\W_]*){NAME}(?=\s*(?:<3|❤|♥|💕|💖|💜|💙|💛|💚|🩷|😍|🥰))"), "known", (HEARTS,)),
    ("praised", re.compile(rf"{NAME}(?i:(?:'s| is| was| are|'re) (?:so |such |soo+ |a |an |the |honestly |really |genuinely |literally |just |fucking |damn |very |pretty |still |always |ultimate |absolute |)*(?:cute|adorable|hot|sexy|fine|badass|goated|peak|mommy|daddy|my queen|my king|best girl|best boy|precious|lovable|loveable|baddie|slay|iconic|underrated|a legend|the goat|my goat|gorgeous|beautiful|stunning|handsome|cutest|hottest|sexiest|prettiest|sweetest|coolest|baddest|a cutie|a sweetheart|a queen|a king|a menace|wholesome|endearing|charming|my favorite|my fave|my fav|my favourite|the best|the greatest|the coolest)\b)"), "known", (CHARMING,)),
    ("answer", re.compile(rf"(?m:^[\W_]*){NAME}(?i:,? (?:for me|of course|100%|1000%|all the way|hands down|all day|no contest|every time|any day|without a doubt|no question|for sure|by far|ftw|supremacy|for the win|forever))(?=[^\w\n]*(?:\n|$)|\s*(?:[.!?,;:)]| tbh\b| imo\b| lol\b))"), "medium", ({"me", "course", "100", "1000", "way", "hands", "day", "contest", "time", "doubt", "question", "sure", "far", "ftw", "supremacy", "win", "forever"},)),
    ("enjoyed", re.compile(rf"(?i:\b(?:i(?:'m| am|'ve| have)?|im) {ADVERB}(?:enjoy|enjoyed|enjoying|miss|missed|respect|admire|admired|appreciate|support|root for|rooting for|ship|shipped|worship|cherish|treasure|idolize|vibe with|relate to|connect with|been obsessed with|fell in love with|fallen in love with|in love with|into|a fan of|a big fan of|a huge fan of|a massive fan of|such a fan of|so into) ){NAME}\b"), "named", (I | {"im"}, {"enjoy", "enjoyed", "enjoying", "miss", "missed", "respect", "admire", "admired", "appreciate", "support", "root", "rooting", "ship", "shipped", "worship", "cherish", "treasure", "idolize", "vibe", "relate", "connect", "obsessed", "fell", "fallen", "love", "into", "fan"})),
    ("owned_my", re.compile(rf"(?i:\bmy (?:[a-z]\d |e\d |c\d |s\d |shiny |new |first |lil |little |baby |sweet |precious |poor |)){NAME}"), "rare", (MY, RARE)),
    ("playing_as", re.compile(rf"(?<!you )(?<!can )(?<!to )(?<!they )(?<!we )(?<!he )(?<!she )(?i:\b(?:playing|play|played) as |\b(?:like|love|enjoy|prefer|liked|loved|enjoyed|preferred) (?:to play|playing) ){NAME}(?=\s*(?:[.,!?;:)|(\[\n]|$| (?:and|or|because|cause|bc|since|for|as|from|in)\b))"), "known", ({"playing", "play", "played"}, {"as", "like", "love", "enjoy", "prefer", "liked", "loved", "enjoyed", "preferred"})),
    ("for_me", re.compile(rf"(?m:(?:^|[.!?]\s+)[\W_]*)(?i:for me(?: personally)?,? it(?:'s| is| has to be| would be| was))\s*[*_\"]*{NAME}(?=\s*(?:[.,!?;:)|(\[\n]|$| (?:and|or|because|cause|bc|since|for|as|from|in)\b))"), "known", ({"for"}, {"me"}, {"it"})),
    ("found_charming", re.compile(rf"(?i:\bi (?:also |really |personally |honestly |just |always |)find ){NAME}(?i: (?:the |so |really |very |most |super |incredibly |extremely |)(?:attractive|hot|cute|sexy|adorable|interesting|fascinating|compelling|relatable|hilarious|funny|charming|endearing|gorgeous|beautiful)\b)"), "known", (I, {"find"})),
    ("team", re.compile(rf"(?i:\bi(?:'m| am) (?:also |definitely |firmly |always |still |)team ){NAME}"), "known", (I, {"team"})),
    ("cosplay", re.compile(rf"(?i:\bmy ){NAME}(?i: cosplay)|{NAME}(?i: (?:cosplay|fan ?art|drawing) (?:by|from) me\b)|(?i:\bi (?:\w+ )?(?:made|did|finished|wore) (?:a|an|my) ){NAME}(?i: cosplay)|(?i:\bi(?:'m| am| was|'ve been)? (?:\w+ )?cosplay(?:ed|ing)? (?:as|of) ){NAME}"), "any", ({"cosplay", "cosplays", "cosplayed", "cosplaying", "cosplayer", "cosplayers", "fanart", "art", "drawing"},)),
)


def rule(pattern, gate):
    def stage(text, found, lowered, words):
        for match in pattern.finditer(text):
            index = next(number for number, group in enumerate(match.groups(), 1) if group)
            if match.group(index).endswith(("'s", "s'")) and match.end(index) == match.end() and not ASPECT.match(text, match.end()):
                continue
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                emit(match.group(index), found, text, match.start(), gate, match.end(index) < match.end())
    return stage


BLANK = re.compile(r"\n[ \t]*\n")
REFERRED = scan(r"(?i:\bi (?:\w+ ){0,2}(?:love|adore|like|stan|loved|adored|liked|enjoy|miss|respect) (?:her|him)\b)")
PRONOUN_I = re.compile(r"I(?:'m|'ve|'d|'ll)?$")


def referred(text, found, lowered, words):
    if "i" not in words or words.isdisjoint(("her", "him")) or words.isdisjoint(("love", "adore", "like", "stan", "loved", "adored", "liked", "enjoy", "miss", "respect")):
        return
    for match in REFERRED.finditer(text):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            names = [name.group(1) for name in re.finditer(NAME, text[max((blank.end() for blank in BLANK.finditer(text, 0, match.start())), default=0):match.start()]) if not PRONOUN_I.match(name.group(1)) and any(pieces(name.group(1)))]
            if names:
                emit(names[-1], found, text, match.start(), "medium")


CLAUSE = re.compile(r"[^.!?\n]+[.!?]*")
PARAGRAPH = re.compile(r"(?:[^\n]|\n(?![ \t]*\n))+")


CUES = frozenset("love loved adore adored enjoy enjoyed like liked dig recommend second rewatched replayed obsessed addicted into fan hooked enough favorite favorites favourite favourites fave faves fav favs fell "
                 "good great amazing awesome excellent fantastic underrated underappreciated goated incredible perfect beautiful fun peak fire goat best jam banger bangers masterpiece classic brilliant phenomenal "
                 "gorgeous lovely wonderful playing watching listening reading bingeing binging replaying rewatching mine hands".split())
FOR_ME = frozenset({"for", "me"})


def liked(text, found, lowered, words):
    if words.isdisjoint(CUES) and not FOR_ME <= words:
        return
    starts = [cue.start() for cue in LIKING.finditer(text)]
    if not starts:
        return
    single = bool(STRONG.search(text))
    cue = 0
    for part in CLAUSE.finditer(text):
        while starts[cue] < part.start():
            cue += 1
            if cue == len(starts):
                break
        else:
            clause = part.group()
            if starts[cue] >= part.end() or NEGATIVE.search(clause) or not SELF.search(clause):
                continue
            for match in CANDIDATE.finditer(clause):
                if match.group(1):
                    for piece in pieces(match.group(1)):
                        if single or " " in piece:
                            emit(piece, found, text, part.start() + match.start(), "known")
            continue
        break
    if not single:
        return
    for part in PARAGRAPH.finditer(text):
        block = part.group()
        if any(part.start() <= cue < part.end() for cue in starts) and SELF.search(block) and not NEGATIVE.search(block):
            for match in CANDIDATE.finditer(block):
                if match.group(1):
                    for piece in pieces(match.group(1)):
                        if " " in piece and known(piece, 3):
                            emit(piece, found, text, part.start() + match.start(), "known")


CHEER = re.compile(rf"(?m:(?:^|[.!?]\s+)[\W_]*(?:(?i:absolutely |really |just |still |totally |fucking |fuckin |so |gotta |truly |honestly |)(?:[Ll]ove|LOVE|[Aa]dore|ADORE) |(?i:hell yeah|hell yes|let'?s go|justice for|respect for|protect|love for|all hail|long live|w) )){NAME}(?=[^\w\n]*(?:\n|$)|\s*[.!?,;:)]| (?i:so much|forever|always|tho|though|too)\b)")

CHEERED = re.compile(r"(?:[Ll]ove|LOVE|[Aa]dore|ADORE|(?i:hell yeah|hell yes|let'?s go|justice for|respect for|protect|all hail|long live|w)) (?:[Tt]he )?[A-Z0-9]")


def cheer(text, found, lowered, words):
    if words.isdisjoint(("love", "adore", "hell", "go", "justice", "respect", "protect", "hail", "live", "w")) or not CHEERED.search(text):
        return
    for match in CHEER.finditer(text):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            emit(match.group(1), found, text, match.start(), "known")


STAGES = tuple((rule(pattern, gate), needs) for label, pattern, gate, needs in RULES)
NEEDED = {}
for number, (_, needs) in enumerate(STAGES):
    for part, need in enumerate(needs):
        for word in need:
            NEEDED.setdefault(word, set()).add((number, part))
REQUIRED = [frozenset((number, part) for part in range(len(needs))) for number, (_, needs) in enumerate(STAGES)]
UNNEEDED = frozenset(number for number, required in enumerate(REQUIRED) if not required)


BARE = re.compile(r"(?:^|[^\w'-])(?i:the|a|an|to|this|that|some|any) $")


SPOTS = {}


def recased(text, words):
    for word in words & LOWERCASED.keys():
        if word not in SPOTS:
            SPOTS[word] = re.compile(rf"(?<![\w'-]){word}(?![\w'-])")
        text = SPOTS[word].sub(lambda match: match.group() if BARE.search(text, max(0, match.start() - 6), match.start()) else LOWERCASED[word], text)
    return text


def characters(text, found):
    lowered = text.lower()
    words = set(WORD.findall(lowered))
    text = recased(text, words)
    met = set()
    for word in words & NEEDED.keys():
        met |= NEEDED[word]
    for number in sorted(UNNEEDED.union(number for number, _ in met)):
        if REQUIRED[number] <= met:
            STAGES[number][0](text, found, lowered, words)
    for stage in (referred, liked, cheer):
        stage(text, found, lowered, words)
