import re

from .common import SELF_HEDGE, hedged
from .schema import fan_value

NAME = r"((?:[Tt]he )?[A-Z0-9][\w'&.:!+-]*(?:,? (?:of|the|and|&|de|la|le|vs\.?|in|on|a|to|[A-Z0-9][\w'&.:!+-]*)){0,6})"
TRAILING = re.compile(r"(?:\s+(?:of|the|and|&|de|la|le|vs\.?|in|on|a|to))+$|[\s,.:!]+$")

KINDS = {"band": "artist", "artist": "artist", "singer": "artist", "rapper": "artist", "musician": "artist", "group": "artist", "musical artist": "artist", "composer": "artist",
         "show": "franchise", "tv show": "franchise", "series": "franchise", "anime": "franchise", "manga": "franchise", "movie": "franchise", "film": "franchise",
         "franchise": "franchise", "book series": "franchise", "cartoon": "franchise", "sitcom": "franchise", "comic": "franchise", "game": "video_game", "video game": "video_game",
         "videogame": "video_game", "book": "franchise", "novel": "franchise", "author": "author", "writer": "author", "team": "sports_team", "club": "sports_team",
         "player": "athlete", "athlete": "athlete", "driver": "athlete", "fighter": "athlete", "wrestler": "athlete", "character": "character", "pokemon": "character",
         "hero": "character", "villain": "character", "champion": "character", "streamer": "creator", "youtuber": "creator", "podcast": "creator", "podcaster": "creator",
         "creator": "creator", "actor": "celebrity", "actress": "celebrity", "comedian": "celebrity", "celebrity": "celebrity"}
KIND_WORDS = "|".join(sorted(map(re.escape, KINDS), key=len, reverse=True))
LETTERS = re.compile(r"[^\W\d_]{2}")
RULES = []
FAVORITE = re.compile(rf"(?i:\bmy (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|favs) ({KIND_WORDS})(?: of all time| ever| right now| atm| at the moment)? (?:is|has to be|would be|would have to be|was always|remains|are)\s+){NAME}")
FAVORED = re.compile(rf"{NAME}(?i: (?:is|are|was|has always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)(?: ({KIND_WORDS}))?\b)")
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am) (?:an? )?(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted) ){NAME}(?i: (?:fan|supporter|stan)\b)")
MAIN = re.compile(rf"(?i:\bi (?:main|mained|play as|always play as) ){NAME}")
SPORTS = re.compile(r"(?i:fc|united|city|athletic|rovers|wanderers|lakers|celtics|yankees|dodgers|cowboys|patriots|packers|eagles|giants|warriors|bulls|knicks|chiefs|steelers|bears|"
                    r"49ers|niners|raiders|ravens|broncos|seahawks|rams|jets|dolphins|bills|lions|vikings|saints|falcons|panthers|buccaneers|bucs|titans|colts|texans|jaguars|"
                    r"browns|bengals|chargers|cardinals|commanders|red sox|cubs|mets|astros|braves|phillies|padres|mariners|blue jays|orioles|twins|tigers|royals|rangers|"
                    r"brewers|pirates|reds|rockies|marlins|nationals|white sox|guardians|athletics|heat|nets|bucks|suns|mavericks|mavs|nuggets|spurs|rockets|thunder|jazz|"
                    r"clippers|kings|pelicans|grizzlies|hawks|hornets|pistons|pacers|cavaliers|cavs|magic|wizards|raptors|76ers|sixers|timberwolves|wolves|blazers|"
                    r"maple leafs|leafs|canadiens|habs|bruins|oilers|flames|canucks|penguins|flyers|blackhawks|red wings|avalanche|lightning|capitals|islanders|devils|sabres|"
                    r"senators|jets|kraken|predators|stars|blues|wild|ducks|sharks|golden knights|arsenal|chelsea|liverpool|tottenham|spurs|everton|barcelona|real madrid|"
                    r"juventus|bayern|dortmund|psg|ajax|celtic|rangers|milan|inter|napoli|roma|benfica|porto|galatasaray|fenerbahce|boca|river plate)\b")
POSITIVE = re.compile(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |seriously |genuinely |do |personally )?(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig|recommend|second|rewatched|replayed)\b|"
                      r"\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big )?fan of|hooked on|in love with)\b|\bcan'?t get enough of\b|"
                      r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rites?|faves?|favs?)\b|\bfell in love with\b|"
                      r"\b(?:is|are|was|were) (?:so |really |very |absolutely |just |still |honestly |such an? |pretty |easily |definitely |by far )?(?:good|great|amazing|awesome|excellent|fantastic|"
                      r"underrated|underappreciated|goated|incredible|perfect|beautiful|fun|peak|fire|the goat|the best|my jam|a banger|bangers|a masterpiece|a classic|brilliant|"
                      r"phenomenal|gorgeous|lovely|wonderful|so fun)\b|\b(?:been|currently|finally|started) (?:playing|watching|listening to|reading|bingeing|binging|replaying|rewatching)\b|"
                      r"\bfor me\b|\bmine is\b|\bhands down\b|\bthe goat\b|\bi'?m (?:playing|watching|listening to|reading|replaying|rewatching)\b)")
NEGATIVE = re.compile(r"(?i:\b(?:hate|hated|don'?t like|didn'?t like|not a fan|dislike|overrated|boring|worst|trash|garbage|sucks|terrible|awful|meh|never (?:played|watched|liked))\b)")
CONTEXTS = {
    "video_game": re.compile(r"(?i:\b(?:games?|gaming|gamer|play|played|playing|playthrough|steam|xbox|playstation|ps[1-5]|switch|nintendo|console|dlc|boss|bosses|speedrun|multiplayer|co-?op|rpg|jrpg|mmo|mmorpg|fps|roguelike|patch|grind|raid|quest|controller|remake|remaster|sequel|campaign|achievements?|platinum)\b)"),
    "franchise": re.compile(r"(?i:\b(?:show|shows|series|season|seasons|episode|episodes|anime|manga|movie|movies|film|films|watch|watched|watching|rewatch|rewatching|binge|tv|netflix|hbo|disney|sitcom|cartoon|comic|comics|trilogy|franchise|novel|novels|books?)\b)"),
    "artist": re.compile(r"(?i:\b(?:songs?|albums?|band|bands|music|concerts?|tour|listen|listened|listening|tracks?|singer|rapper|vinyl|ep|lp|spotify|lyrics|discography|gig|setlist|live show|banger|bangers|vocals|guitarist|drummer)\b)"),
    "character": re.compile(r"(?i:\b(?:character|characters|main|maining|mains|waifu|husbando|ship|shipped|arc|villain|protagonist|cosplay|pokemon|pokémon|hero|heroes|champion|skin)\b)"),
    "author": re.compile(r"(?i:\b(?:author|authors|novelist|writer)\b)"),
    "creator": re.compile(r"(?i:\b(?:streamer|streams|streaming|twitch|youtuber|youtube channel|podcast|podcasts|podcaster|vlogs?)\b)"),
}
CANDIDATE = re.compile(r"(?<![\w'])((?:[A-Z][\w'&:.!+-]*|\d+[a-z]*)(?: (?:of|the|and|&|de|la|vs\.?|in|on|a|to|no|[A-Z0-9][\w'&:.!+-]*))*)|[\"“]([^\"”\n]{2,40})[\"”]")
COMMON = frozenset("i i'm im i've i'd i'll it it's its the this that these those my me mine we our you your he she they them his her their a an and but or so if when what why how where who which "
                   "yes no yeah yep nope ok okay lol lmao omg oh hey hi hello thanks thank also just honestly literally well not then there here now today tomorrow yesterday "
                   "love loved great best good amazing awesome edit update tldr tl;dr op reddit google youtube god jesus christmas monday tuesday wednesday thursday friday saturday "
                   "sunday january february march april may june july august september october november december english american nta yta esh nah imo imho idk tbh btw "
                   "definitely probably maybe sure same agreed true right wow damn dude bro man guys please sorry what's that's there's".split())


def fandom(text, found):
    for sentence in re.finditer(r"[^.!?\n]+[.!?]*", text):
        part = sentence.group()
        if not (cue := POSITIVE.search(part)) or NEGATIVE.search(part):
            continue
        if hedged(part.lower(), cue.start(), cue.end(), SELF_HEDGE):
            continue
        first = len(part) - len(part.lstrip())
        names = []
        for match in CANDIDATE.finditer(part):
            name = (match.group(1) or match.group(2)).strip()
            words = name.lower().split()
            if words and words[0] in COMMON:
                name, words = " ".join(name.split()[1:]), words[1:]
            if not words or not LETTERS.search(name) or re.fullmatch(r"[\d\W]*\w?\d[\w-]*", name):
                continue
            if len(words) == 1 and (words[0] in COMMON or len(name) < 4 or match.start() == first or re.search(rf"(?<![\w'])(?-i:{re.escape(words[0])})(?![\w'])", text)):
                continue
            if cue.start() <= match.start() < cue.end():
                continue
            window = part[max(0, match.start() - 80):match.end() + 80]
            kinds = {kind: 3 * len(pattern.findall(window)) + len(pattern.findall(part)) for kind, pattern in CONTEXTS.items()}
            kind = max(kinds, key=kinds.get)
            if kinds[kind]:
                names.append((abs(match.start() - cue.start()), kind, name))
        for _, kind, name in sorted(names)[:2]:
            named(kind, name, found, sentence.start())


ADJACENT = re.compile(r"\b(?:i (?:really |absolutely |just |also |still |honestly |do |genuinely )?(?:love|loved|adore|adored|enjoy|enjoyed)|obsessed with|addicted to|can'?t get enough of|a (?:huge |big |massive )?fan of|in love with|hooked on|"
                      r"my (?:all[- ]time |absolute |personal )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|has to be|would be|was)|i'?m (?:currently |still |also )?(?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging)|"
                      r"i'?ve been (?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging|obsessed with)|i (?:just )?(?:finished|beat|started) (?:playing |watching |reading )?)\s+"
                      r"((?:the )?[\w'&:.!+-]+(?: [\w'&:.!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|it|is|was|lol|too|again|right|atm|lately|recently|these|since|for|with|on|in|at|when|while|haha|tbh|honestly|now|today)\b)")
GENERIC = frozenset("it this that these those him her them you me my your his their our how when being having to a an some any all every everything anything something nothing games game gaming music songs song anime "
                    "shows show movies movie films film books book reading watching playing food sex cock dick pussy ass porn people men women guys girls kids dogs cats animals life it's them. "
                    "him. you. that. this. here there out up down so very much more most doing going getting seeing playing talking working".split())


def adjacent(text, found):
    lowered = text.lower()
    for match in ADJACENT.finditer(lowered):
        name = re.sub(r"^the ", "", match.group(1)).strip()
        words = name.split()
        if not words or words[0] in GENERIC or words[-1] in GENERIC or words[0] in COMMON or len(name) < 3 or not LETTERS.search(name) or hedged(lowered, match.start(), match.end(), SELF_HEDGE) or NEGATIVE.search(lowered[match.start():match.end() + 40]):
            continue
        part = text[max(0, match.start() - 150):match.end() + 150]
        kinds = {kind: 3 * len(pattern.findall(part)) + len(pattern.findall(text)) for kind, pattern in CONTEXTS.items()}
        kind = max(kinds, key=kinds.get)
        if kinds[kind]:
            named(kind, name, found, match.start())


def favorites(text, found):
    for pattern in (FAVORITE, FAVORED):
        for match in pattern.finditer(text):
            name, kind = (match.group(2), match.group(1)) if pattern is FAVORITE else (match.group(1), match.group(2))
            attribute = KINDS.get((kind or "").lower())
            if attribute and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
                named(attribute, name, found, match.start())
    for match in FAN.finditer(text):
        if SPORTS.search(match.group(1)) and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("sports_team", match.group(1), found, match.start())
    for match in MAIN.finditer(text):
        if not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("character", match.group(1), found, match.start())


def named(attribute, name, found, position):
    name = TRAILING.sub("", name).strip()
    if 1 < len(name) <= 40 and (value := fan_value(attribute, name.lower())):
        found.setdefault((attribute, value), position)
