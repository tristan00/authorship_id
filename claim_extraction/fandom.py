import re
import unicodedata
from pathlib import Path

from .common import SELF_HEDGE, clause, hedged
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
FAVORITE = re.compile(rf"(?i:\b(?:one of )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|favs) ({KIND_WORDS})s?(?: of all time| ever| right now| atm| at the moment)? (?:is|has to be|would be|would have to be|was always|remains|are)\s+){NAME}")
FAVORED = re.compile(rf"{NAME}(?i: (?:is|are|was|has always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?(?:one of )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)s?(?: ({KIND_WORDS})s?)?\b)")
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
    "creator": re.compile(r"(?i:\b(?:streamer|streamers|streams|streaming|twitch|youtube|youtuber|youtubers|vtuber|tiktok|tiktoker|channel|subscribed|subscribers|podcast|podcasts|podcaster|vlogs?|vods?)\b)"),
    "athlete": re.compile(r"(?i:\b(?:nba|nfl|mlb|nhl|epl|premier league|champions league|la liga|serie a|bundesliga|ipl|cricket|football|soccer|basketball|baseball|hockey|rugby|tennis|golf|f1|"
                          r"formula 1|ufc|mma|boxing|wrestling|striker|midfielder|defender|goalie|goalkeeper|quarterback|qb|pitcher|playoffs|super bowl|world cup|stanley cup|mvp|"
                          r"all-star|touchdowns?|goals|scored|dunk|hat trick|coach|draft|rookie|stadium)\b)"),
    "celebrity": re.compile(r"(?i:\b(?:actor|actors|actress|actresses|acting|comedian|comedians|stand-?up|hollywood|oscars?|celebrity|celebrities|starred|starring|his movies|her movies|"
                            r"his films|her films|roles?)\b)"),
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
            name = STOP.split((match.group(1) or match.group(2)).strip())[0]
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
            if kind not in NAMED_ONLY and not junk(name) and (kind != "video_game" or " " in name.strip()):
                named(kind, name, found, sentence.start())


EDGE = frozenset("since in on as about both because at for with from by during after before like all just really again still too ever even when while if than then so but or and of to "
                 "into onto over under through every each some any much many more most very only also already almost around against without within across".split())


def junk(name):
    name = TRAILING.sub("", name).strip()
    words = name.lower().split() or [""]
    return words[0] in EDGE or words[-1] in EDGE or words[-1].endswith(("'s", "s'")) or " and " in name.lower()


ADJACENT = re.compile(r"\b(?:i (?:really |absolutely |just |also |still |honestly |do |genuinely )?(?:love|loved|adore|adored|enjoy|enjoyed)|obsessed with|addicted to|can'?t get enough of|a (?:huge |big |massive )?fan of|in love with|hooked on|"
                      r"my (?:all[- ]time |absolute |personal )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|has to be|would be|was)|i'?m (?:currently |still |also )?(?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging)|"
                      r"i'?ve been (?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging|obsessed with)|i (?:just )?(?:finished|beat|started) (?:playing |watching |reading )?|i (?:still |also |mostly |mainly |usually |really )?(?:play|played|replayed|rewatched))\s+"
                      r"((?:the )?[\w'&:.!+-]+(?: [\w'&:.!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|it|is|was|lol|too|again|right|atm|lately|recently|these|since|for|with|on|in|at|when|while|haha|tbh|honestly|now|today)\b)")
GENERIC = frozenset("it this that these those him her them you me my your his their our how when being having to a an some any all every everything anything something nothing games game gaming music songs song anime "
                    "shows show movies movie films film books book reading watching playing food sex cock dick pussy ass porn people men women guys girls kids dogs cats animals life it's them. "
                    "him. you. that. this. here there out up down so very much more most doing going getting seeing playing talking working".split())


def adjacent(text, found):
    lowered = text.lower()
    for match in ADJACENT.finditer(lowered):
        name = re.sub(r"^the ", "", match.group(1)).strip()
        words = name.split()
        if STOP.search(name) or not words or words[0] in GENERIC or words[-1] in GENERIC or words[0] in COMMON or len(name) < 3 or not LETTERS.search(name) or hedged(lowered, match.start(), match.end(), SELF_HEDGE) or NEGATIVE.search(lowered[match.start():match.end() + 40]):
            continue
        part = text[max(0, match.start() - 150):match.end() + 150]
        kinds = {kind: 3 * len(pattern.findall(part)) + len(pattern.findall(text)) for kind, pattern in CONTEXTS.items()}
        kind = max(kinds, key=kinds.get)
        if kinds[kind] and kind not in NAMED_ONLY and not junk(name) and (kind == "franchise" and len(words) < 3 or re.search(r"[A-Z0-9]", text[match.start(1):match.end(1)])):
            named(kind, name, found, match.start())


DEGREE = r"(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted|avid|hardcore|crazy|super|major|total)"
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am|i've been|ive been|been|as|being) (?:an? )?(?:{DEGREE} )*){NAME}(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)")
TEAM_FAN = re.compile(rf"(?i:\b(?:(?:i'm|im|i am|i've been|ive been|been|as|being) (?:an? )?|(?:fellow|{DEGREE}) )(?:{DEGREE} )*){NAME}(?i: (?:fan|supporter)s?\b)|"
                      rf"(?:(?m:^)|(?<=[.!?] )){NAME}(?i: (?:fan|supporter)s? (?:here|since|for life|all my life|my whole life|through and through)\b)")
FAN_OF = re.compile(rf"(?i:\b(?:i'm|im|i am|i've been|ive been|i've always been|been|as) (?:also |still |definitely |honestly |really |such |always )?(?:an? |the )?(?:{DEGREE} )*(?:fan|supporter|admirer) of (?:the )?){NAME}")
STAN = re.compile(rf"(?i:\bi (?:also |still |will always |literally |really )?stan ){NAME}")
GOAT = re.compile(rf"(?i:\bmy (?:all[- ]time )?goat:? ){NAME}")
GOATED = re.compile(rf"{NAME}(?i: (?:is|was|will always be|remains) (?:still |easily |honestly )?(?:the|my) goat\b| the goat\b)")
OBJECTS = {"music": "artist", "songs": "artist", "song": "artist", "album": "artist", "albums": "artist", "voice": "artist", "vocals": "artist", "lyrics": "artist", "art": "artist",
           "artwork": "artist", "movies": "celebrity", "films": "celebrity", "acting": "celebrity", "performance": "celebrity", "performances": "celebrity", "roles": "celebrity",
           "comedy": "celebrity", "standup": "celebrity", "specials": "celebrity", "videos": "creator", "video": "creator", "streams": "creator", "stream": "creator",
           "channel": "creator", "content": "creator", "podcast": "creator", "books": "author", "novels": "author", "writing": "author", "prose": "author"}
LOVED = re.compile(rf"(?i:\bi(?:'m| am)? (?:really |absolutely |just |also |still |honestly |genuinely |do |totally |fucking |friggin |so |personally )*"
                   rf"(?:love|adore|loved|adored|enjoy|enjoyed|in love with|obsessed with) ){NAME}")
CREATED = re.compile(rf"{NAME}(?:'s|s'|’s) (?i:(?:new |latest |recent |old |last |early )?(?:videos?|streams?|vods?|channel|podcasts?|content|vlogs?)\b)")
TITLED = re.compile(rf"(?i:\b(?:youtubers?|streamers?|creators?|podcasters?|vtubers?|youtube channel|twitch channel|podcast)(?: i (?:follow|watch|like|love|enjoy|recommend))?,?\s+(?:called |named )?){NAME}")
WATCHED = re.compile(rf"(?i:\b(?:i (?:\w+ )?(?:watch|watching|watched)|subscribed to|i follow|i'?ve been following) ){NAME}(?i: (?:on|'s) (?:youtube|twitch|tiktok|kick)\b)")
LISTENED = re.compile(rf"(?i:\b(?:i(?:'m| am|'ve been| have been)? (?:\w+ )?(?:listening to|listen to|listened to|jamming to|bumping)|been (?:listening to|bumping|jamming to)) ){NAME}")
ALBUM = re.compile(rf"{NAME}(?:'s|s'|’s) (?i:(?:new |latest |last |debut |first |second |third |next |old |early )?(?:albums?|songs?|singles?|discography|tour|concerts?|records?|ep|lp|music|vocals|lyrics)\b)")
SEEN = re.compile(rf"(?i:\b(?:i|we) (?:\w+ )?(?:saw|seen|see|seeing) ){NAME}(?i: (?:live|in concert|perform|play live|open for)\b)")
BRACED = re.compile(r"\{([^{}\n=;:<>\"]{2,80})\}")
PRAISED = re.compile(rf"(?:(?m:^)|(?<=[.!?] )){NAME}(?i: (?:is|was|are|were|has been|remains) (?:still |so |fucking |really |honestly |just |literally |absolutely |easily |genuinely |lowkey )*"
                     rf"(?:peak|goated|amazing|incredible|underrated|phenomenal|a masterpiece|a banger|fire|elite|god ?tier|top tier|the goat|the best\b|one of the best)\b)")
FAVORITE_PLAIN = re.compile(rf"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav) ({KIND_WORDS})s? (?:is|has to be|would be|was|are)\s+"
                            r"((?:the )?[\w'&:!+-]+(?: [\w'&:!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|lol|too|tbh|honestly|by far|hands down|of all time|ever|for sure)\b)")
SPLIT = re.compile(r"\s*(?:,|/|&|\band\b)\s*")
POSSESSIVE = re.compile(r"'s\b.*$")
STOP = re.compile(r"[.!?:;]\s")
PRONOUNS = frozenset({"i", "i'm", "im", "i've", "i'd", "i'll", "me", "my", "you", "we", "he", "she", "they"})
PEOPLE = ("character", "artist", "athlete", "celebrity", "creator", "author")
UNPRAISED = frozenset({"athlete", "celebrity", "author"})
NAMED_ONLY = frozenset({"character", "athlete", "celebrity"})
SPELLED = frozenset({"athlete", "celebrity", "author", "creator"})
GATED = frozenset({"artist", "author"})
LISTED = re.compile(r"[\s,;/&*|>()\[\]^:.\d-]{1,12}|\s*(?:,\s*)?(?:and|or)\s+")
LISTS = frozenset({"artist"})
RUN = 3


def parts(name):
    name = STOP.split(name)[0]
    if " " not in name or lexical(name):
        return [name]
    return [piece for piece in SPLIT.split(POSSESSIVE.sub("", name)) if piece]


def lexical(name):
    hits = [(links, attribute, value) for attribute, start, end, value, _, _, links in mentions(name) if start == 0 and end == len(name.rstrip(" .,!:"))]
    return max(hits)[1:] if hits else None


def classified(text, start, name, options):
    if hit := lexical(name):
        return hit
    window = text[max(0, start - 200):start + 200]
    scores = {kind: 3 * len(TARGET_CONTEXT[kind].findall(window)) + len(TARGET_CONTEXT[kind].findall(text)) for kind in options}
    kind = max(scores, key=scores.get)
    if not scores[kind]:
        return None
    if kind == "athlete" and (len(name.split()) < 2 or name.endswith("s")):
        return None
    return kind, name


def favorites(text, found):
    lowered = text.lower()
    for pattern in (FAVORITE, FAVORED):
        for match in pattern.finditer(text):
            name, kind = (match.group(2), match.group(1)) if pattern is FAVORITE else (match.group(1), match.group(2))
            attribute = KINDS.get((kind or "").lower())
            if hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                continue
            for piece in parts(name):
                if attribute:
                    named(attribute, piece, found, match.start())
                elif hit := classified(text, match.start(), piece, (*PEOPLE, "franchise", "video_game")):
                    named(*hit, found, match.start())
    for match in FAVORITE_PLAIN.finditer(lowered):
        words = match.group(2).removeprefix("the ").split()
        if words and words[0] not in COMMON and words[0] not in GENERIC and not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            named(KINDS[match.group(1)], " ".join(words), found, match.start())
    for match in TEAM_FAN.finditer(text):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            for piece in parts(match.group(1) or match.group(2)):
                if club := team(piece):
                    named("sports_team", club, found, match.start())
    for pattern in (FAN, FAN_OF, STAN, GOAT, GOATED, PRAISED):
        for match in pattern.finditer(text):
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for piece in parts(match.group(1)):
                    if pattern in (FAN, FAN_OF) and (club := team(piece)):
                        named("sports_team", club, found, match.start())
                    elif (hit := classified(text, match.start(), piece, (*PEOPLE, "franchise", "video_game"))) and (pattern is not PRAISED or hit[0] not in UNPRAISED):
                        named(*hit, found, match.start())
    for match in LOVED.finditer(text):
        if hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            continue
        name, mark, rest = match.group(1).partition("'s")
        kind = OBJECTS.get(next(iter(WORD.findall(rest or text[match.end():match.end() + 20])), "").lower()) if mark else None
        if kind:
            named(kind, STOP.split(name)[0], found, match.start())
        elif not lexical(name):
            for piece in parts(name):
                if hit := classified(text, match.start(), piece, PEOPLE):
                    named(*hit, found, match.start())
    for pattern in (CREATED, WATCHED, TITLED):
        for match in pattern.finditer(text):
            sentence = text[clause(text, match.start()):match.end() + 80]
            if (SELF.search(sentence) or POSITIVE.search(sentence)) and not hedged(lowered, match.start(), match.end(), SELF_HEDGE) and not lexical(match.group(1)):
                named("creator", STOP.split(match.group(1))[0], found, match.start())
    for pattern in (LISTENED, ALBUM, SEEN):
        for match in pattern.finditer(text):
            sentence = text[clause(text, match.start()):match.end() + 80]
            if (SELF.search(sentence) or POSITIVE.search(sentence)) and not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for piece in parts(match.group(1)):
                    hit = lexical(piece)
                    if not hit or hit[0] == "artist":
                        named("artist", hit[1] if hit else piece, found, match.start())
    if SELF.search(text) or POSITIVE.search(text):
        for match in BRACED.finditer(text):
            title, _, writer = match.group(1).strip().partition(" by ")
            if len(title.split()) <= 10:
                named("franchise", title, found, match.start())
                if writer:
                    named("author", writer, found, match.start())
    known(text, found)


def named(attribute, name, found, position):
    name = TRAILING.sub("", name).strip()
    words = name.lower().split()
    if 1 < len(name) <= 40 and words[0] not in PRONOUNS and words[-1] not in PRONOUNS and (value := fan_value(attribute, name.lower())):
        found.setdefault((attribute, value), position)


NFL_TEAMS_2025 = """arizona cardinals;atlanta falcons|Falcons;baltimore ravens|Ravens;buffalo bills|Bills;carolina panthers;chicago bears|Bears;cincinnati bengals|Bengals;cleveland browns|Browns;
dallas cowboys|Cowboys;denver broncos|Broncos;detroit lions|Lions;green bay packers|Packers;houston texans|Texans;indianapolis colts|Colts;jacksonville jaguars|Jaguars|Jags;
kansas city chiefs|Chiefs;las vegas raiders|oakland raiders|Raiders;los angeles chargers|Chargers;los angeles rams|Rams;miami dolphins|Dolphins;minnesota vikings|Vikings;
new england patriots|Patriots|Pats;new orleans saints|Saints;new york giants|Giants;new york jets|Jets;philadelphia eagles|Eagles;pittsburgh steelers|Steelers;
san francisco 49ers|49ers|Niners;seattle seahawks|Seahawks;tampa bay buccaneers|Buccaneers|Bucs;tennessee titans|Titans;washington commanders|Commanders"""
NBA_TEAMS_2025 = """atlanta hawks|Hawks;boston celtics|Celtics;brooklyn nets|Nets;charlotte hornets|Hornets;chicago bulls|Bulls;cleveland cavaliers|Cavaliers|Cavs;dallas mavericks|Mavericks|Mavs;
denver nuggets|Nuggets;detroit pistons|Pistons;golden state warriors|Warriors;houston rockets|Rockets;indiana pacers|Pacers;la clippers|los angeles clippers|Clippers;
los angeles lakers|Lakers;memphis grizzlies|Grizzlies;miami heat;milwaukee bucks|Bucks;minnesota timberwolves|Timberwolves|Wolves;new orleans pelicans|Pelicans;new york knicks|Knicks;
oklahoma city thunder|OKC;orlando magic;philadelphia 76ers|76ers|Sixers;phoenix suns|Suns;portland trail blazers|trail blazers|Blazers;sacramento kings|Kings;san antonio spurs|Spurs;
toronto raptors|Raptors;utah jazz;washington wizards|Wizards"""
MLB_TEAMS_2025 = """arizona diamondbacks|Diamondbacks|D-backs;atlanta braves|Braves;baltimore orioles|Orioles;boston red sox|red sox;chicago cubs|Cubs;chicago white sox|white sox;
cincinnati reds|Reds;cleveland guardians|Guardians;colorado rockies|Rockies;detroit tigers|Tigers;houston astros|Astros;kansas city royals|Royals;los angeles angels|Angels;
los angeles dodgers|Dodgers;miami marlins|Marlins;milwaukee brewers|Brewers;minnesota twins|Twins;new york mets|Mets;new york yankees|Yankees;athletics|oakland athletics|A's;
philadelphia phillies|Phillies;pittsburgh pirates|Pirates;san diego padres|Padres;san francisco giants|Giants;seattle mariners|Mariners;st. louis cardinals|Cardinals;
tampa bay rays|Rays;texas rangers|Rangers;toronto blue jays|blue jays|Jays;washington nationals|Nationals|Nats"""
NHL_TEAMS_2025 = """anaheim ducks|Ducks;boston bruins|Bruins;buffalo sabres|Sabres;calgary flames|Flames;carolina hurricanes|Hurricanes|Canes;chicago blackhawks|Blackhawks;
colorado avalanche|Avalanche|Avs;columbus blue jackets|blue jackets;dallas stars|Stars;detroit red wings|red wings;edmonton oilers|Oilers;florida panthers|Panthers;
los angeles kings|Kings;minnesota wild;montreal canadiens|Canadiens|Habs;nashville predators|Predators|Preds;new jersey devils|Devils;new york islanders|Islanders|Isles;
new york rangers|Rangers;ottawa senators|Senators|Sens;philadelphia flyers|Flyers;pittsburgh penguins|Penguins|Pens;san jose sharks|Sharks;seattle kraken|Kraken;
st. louis blues|Blues;tampa bay lightning|Lightning|Bolts;toronto maple leafs|maple leafs|Leafs;utah mammoth|utah hockey club;vancouver canucks|Canucks;
vegas golden knights|golden knights;washington capitals|Capitals|Caps;winnipeg jets|Jets"""
MLS_TEAMS_2025 = """atlanta united;austin fc;charlotte fc;chicago fire fc;fc cincinnati;colorado rapids;columbus crew;d.c. united|dc united;fc dallas;houston dynamo;inter miami;la galaxy;
los angeles fc|LAFC;minnesota united;cf montréal|cf montreal;nashville sc;new england revolution;new york city fc|NYCFC;new york red bulls;orlando city;philadelphia union;
portland timbers|Timbers;real salt lake;san diego fc;san jose earthquakes;seattle sounders|Sounders;sporting kansas city;st. louis city sc;toronto fc;vancouver whitecaps|Whitecaps"""
PREMIER_LEAGUE_TEAMS_2025 = """arsenal|Arsenal|Gunners;aston villa;bournemouth|Bournemouth;brentford|Brentford;brighton & hove albion|brighton and hove albion|Brighton;burnley|Burnley;
chelsea|Chelsea;crystal palace;everton|Everton;fulham|Fulham;leeds united|Leeds;liverpool|Liverpool;manchester city|man city;manchester united|man united|man utd;
newcastle united|Newcastle;nottingham forest;sunderland|Sunderland;tottenham hotspur|tottenham|Spurs;west ham united|west ham;wolverhampton wanderers|Wolves"""
LA_LIGA_TEAMS_2025 = """deportivo alavés|Alavés;athletic bilbao|athletic club;atlético madrid|atletico madrid|Atleti;fc barcelona|Barcelona|Barça|Barca;celta vigo|Celta;elche|Elche;
espanyol|Espanyol;getafe|Getafe;girona|Girona;levante|Levante;mallorca|Mallorca;osasuna|Osasuna;rayo vallecano;real betis|Betis;real madrid;real oviedo;real sociedad;
sevilla|Sevilla;valencia|Valencia;villarreal|Villarreal"""
SERIE_A_TEAMS_2025 = """atalanta|Atalanta;bologna|Bologna;cagliari|Cagliari;como|Como;cremonese|Cremonese;fiorentina|Fiorentina;genoa|Genoa;hellas verona|Verona;inter milan|internazionale|Inter;
juventus|Juventus|Juve;lazio|Lazio;lecce|Lecce;ac milan|Milan;napoli|Napoli;parma|Parma;pisa|Pisa;as roma|Roma;sassuolo|Sassuolo;torino|Torino;udinese|Udinese"""
BUNDESLIGA_TEAMS_2025 = """fc augsburg|Augsburg;union berlin;werder bremen|Bremen;borussia dortmund|Dortmund|BVB;eintracht frankfurt;sc freiburg|Freiburg;hamburger sv|HSV;1. fc heidenheim|Heidenheim;
tsg hoffenheim|Hoffenheim;1. fc köln|fc köln|fc koln;rb leipzig|Leipzig;bayer leverkusen|Leverkusen;mainz 05|Mainz;borussia mönchengladbach|mönchengladbach|Gladbach;
bayern munich|bayern münchen|Bayern;fc st. pauli|St. Pauli;vfb stuttgart|Stuttgart;vfl wolfsburg|Wolfsburg"""
LIGUE_1_TEAMS_2025 = """angers|Angers;auxerre|Auxerre;stade brestois|Brest;le havre;rc lens|Lens;lille|Lille|LOSC;lorient|Lorient;olympique lyonnais|Lyon;olympique de marseille|Marseille;
metz|Metz;as monaco|Monaco;nantes|Nantes;ogc nice;paris fc;paris saint-germain|PSG;stade rennais|Rennes;strasbourg|Strasbourg;toulouse|Toulouse"""
IPL_TEAMS_2025 = """chennai super kings|CSK;delhi capitals;gujarat titans;kolkata knight riders|KKR;lucknow super giants|LSG;mumbai indians;punjab kings;rajasthan royals;
royal challengers bengaluru|royal challengers bangalore|RCB;sunrisers hyderabad|SRH"""
TEAMS = (NFL_TEAMS_2025, NBA_TEAMS_2025, MLB_TEAMS_2025, NHL_TEAMS_2025, MLS_TEAMS_2025, PREMIER_LEAGUE_TEAMS_2025, LA_LIGA_TEAMS_2025, SERIE_A_TEAMS_2025, BUNDESLIGA_TEAMS_2025,
         LIGUE_1_TEAMS_2025, IPL_TEAMS_2025)
KNOWLEDGE = Path(__file__).with_name("knowledge.tsv")
SHORT_KEY = 3
LOOSE = frozenset({"video_game"})
WINDOW = 150
FAMOUS_SITELINKS = 40
TITLES = frozenset({"franchise", "video_game"})
WORD = re.compile(r"\w+")


def folded(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def table():
    teams = {}
    for entry in filter(None, (piece.strip() for block in TEAMS for piece in block.replace("\n", "").split(";"))):
        head, *aliases = entry.split("|")
        for variant in {form for alias in (head, *aliases) for form in (alias, folded(alias))}:
            tokens = WORD.findall(variant)
            single = sum(token.lower() != "the" for token in tokens) == 1
            if not (single and variant == variant.lower()):
                teams.setdefault(" ".join(tokens).lower(), set()).add(head.lower())
    plain, cased = {}, {}
    for key, values in teams.items():
        if len(values) == 1:
            plain.setdefault(key, []).append(("sports_team", next(iter(values)), False, False, 0))
    with open(KNOWLEDGE, encoding="utf-8") as rows:
        next(rows)
        for line in rows:
            key, attribute, value, links, surfaces, common = line.rstrip("\n").split("\t")
            entry = (attribute, value, bool(surfaces), common == "1" or len(key) <= SHORT_KEY, int(links))
            for surface in surfaces.split("|") if surfaces else ():
                cased.setdefault(surface, []).append(entry)
            if not surfaces or (attribute in LOOSE and common == "1" and " " in key.removeprefix("the ")):
                plain.setdefault(key, []).append((attribute, value, False, common == "1" or len(key) <= SHORT_KEY, int(links)))
    prefixes = set()
    for key in (*plain, *cased):
        tokens = key.lower().split(" ")
        prefixes.update(" ".join(tokens[:size]) for size in range(1, len(tokens) + 1))
    return plain, cased, prefixes


PLAIN, CASED, PREFIXES = table()


def team_words():
    words = {}
    for entry in filter(None, (piece.strip() for block in TEAMS for piece in block.replace("\n", "").split(";"))):
        head, *aliases = entry.split("|")
        tokens = WORD.findall(head)
        for form in (head, *aliases, tokens[-1]):
            key = " ".join(WORD.findall(folded(form))).lower()
            for variant in (key, key[:-1]) if key.endswith("s") and " " not in key and len(key) > 4 else (key,):
                words.setdefault(variant, set()).add(head.lower())
    return {key: next(iter(heads)) if len(heads) == 1 else key for key, heads in words.items()}


TEAM_WORDS = team_words()


def team(name):
    return TEAM_WORDS.get(" ".join(WORD.findall(folded(name))).lower().removeprefix("the "))


def mentions(text):
    words = list(WORD.finditer(text))
    shown = [word.group() for word in words]
    lows = [word.lower() for word in shown]
    spans, index, total = [], 0, len(words)
    while index < total:
        found, size, key, surface = None, 1, lows[index], shown[index]
        while key in PREFIXES:
            plain, cased = PLAIN.get(key), CASED.get(surface)
            if plain or cased:
                found = size, (plain or []) + (cased or [])
            if index + size == total:
                break
            key, surface, size = key + " " + lows[index + size], surface + " " + shown[index + size], size + 1
        if found:
            size, entries = found
            spans.extend((attribute, words[index].start(), words[index + size - 1].end(), value, cased, common, links) for attribute, value, cased, common, links in entries)
            index += size
        else:
            index += 1
    return spans


LEXICON_CONTEXT = dict(CONTEXTS)
LEXICON_CONTEXT["artist"] = re.compile(CONTEXTS["artist"].pattern[:-4] + r"|sing|sings|sang|singing|playlist|records?|records|festival|fans?|stan)\b)")
LEXICON_CONTEXT["franchise"] = re.compile(CONTEXTS["franchise"].pattern[:-4] + r"|read|reading|fandom|canon|plot|characters?|finale|spinoff|reboot|adaptation)\b)")

AUTHORING = re.compile(r"(?i:\b(?:author|authors|novelist|writer|writes|wrote|written|books?|novels?|reading|read|series|trilogy)\b)")
GATES = {**LEXICON_CONTEXT, "author": AUTHORING}
TARGET_CONTEXT = {**LEXICON_CONTEXT, "author": AUTHORING}


def opening(text, start):
    before = text[:start].rstrip(" \t\"'*(#>-_[")
    return not before or before[-1] in ".!?\n:"


SELF = re.compile(r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)")
DONE = {"video_game": re.compile(r"(?i:\b(?:play|playing|played|replay\w*|beat|beaten|finished|finishing|completed|platinumed|grinding|started)\b)"),
        "franchise": re.compile(r"(?i:\b(?:watch|watching|watched|rewatch\w*|binge\w*|binging|read|reading|reread\w*|finished|finishing|started)\b)"),
        "artist": re.compile(r"(?i:\b(?:listen|listening|listened|saw|seen|concerts?|gigs?|vinyl|albums?|discography)\b)")}


def sentence(text, start, end):
    return max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1, min((found for found in (text.find(mark, end) for mark in ".!?\n") if found >= 0), default=len(text))


def praised(text, start, end):
    left, right = sentence(text, start, end)
    return bool(POSITIVE.search(text, left, right)) and not NEGATIVE.search(text, left, right) and text[right:right + 1] != "?"


def engaged(text, start, end, attribute, popular, plain):
    left, right = narrow = sentence(text, start, end)
    if text[right:right + 1] == "?":
        return False
    if plain and attribute == "franchise":
        return bool(POSITIVE.search(text, *narrow))
    if attribute in DONE:
        left, right = max(0, left - 100), right + 100
    if POSITIVE.search(text, left, right):
        return True
    if attribute in DONE and not popular:
        return bool(SELF.search(text, *narrow) and DONE[attribute].search(text, *narrow))
    return bool(SELF.search(text, left, right))


BACKING = re.compile(r"(?i:\b(?:my|our|go|let'?s go|lets go|up the|c'?mon|come on|i (?:love|support|root for|cheer for|follow)|fan of|rooting for|cheering for|supporter of)(?: the| my| our| beloved| boys)?\s*$)")
BACKER = re.compile(r"(?i:\s*(?:nation|faithful|for life|forever|till i die|all the way)\b)")
FANNED = re.compile(r"(?i:\s*(?:fan|supporter)\b)")
AVOWED = re.compile(r"(?i:\b(?:i'?m|i am|as|been|being)\b[\w\s-]{0,20}$)")
PEER = re.compile(r"(?i:\b(?:he|she|they|his|her|their|dad|mom|father|mother|brother|sister|wife|husband|son|daughter|friend|friends|boyfriend|girlfriend|partner|people|everyone|nobody|every)\b)")


def supported(text, start, end):
    lowered = text.lower()
    before = max(0, start - 30)
    if not (BACKING.search(lowered, before, start) or BACKER.match(lowered, end) or (FANNED.match(lowered, end) and AVOWED.search(lowered, before, start))):
        return False
    return not PEER.search(lowered, clause(lowered, start), start) and not hedged(lowered, start, end, SELF_HEDGE)


def chosen(text, start, options, totals):
    if len(options) == 1:
        return options
    window = text[max(0, start - 150):start + 150]
    scored = [(3 * len(LEXICON_CONTEXT[option[0]].findall(window)) + totals(option[0]), option) for option in options]
    return [option for score, option in scored if score or option[0] == "franchise"] or [max(scored)[1]]


def known(text, found):
    grouped, counts, opened, famous, ordinary = {}, {}, set(), set(), set()

    def totals(attribute):
        if attribute not in counts:
            counts[attribute] = len(LEXICON_CONTEXT[attribute].findall(text))
        return counts[attribute]

    for attribute, start, end, value, cased, common, links in mentions(text):
        if attribute == "sports_team":
            if supported(text, start, end):
                named(attribute, value, found, start)
            continue
        if (attribute == "character" or (cased and attribute in SPELLED) or (common and links < FAMOUS_SITELINKS and " " not in text[start:end])
                or ((cased or common or attribute in NAMED_ONLY or attribute in GATED) and not GATES[attribute].search(text, max(0, start - WINDOW), end + WINDOW)
                    and not (attribute == "franchise" and links >= FAMOUS_SITELINKS and not common and praised(text, start, end)))):
            continue
        if cased and " " not in text[start:end] and opening(text, start):
            opened.add((start, end))
        if links >= FAMOUS_SITELINKS and attribute in TITLES:
            famous.add((start, end, attribute))
        if common and links < FAMOUS_SITELINKS:
            ordinary.add((start, end, attribute))
        grouped.setdefault((start, end), []).append((attribute, value))
    spans = sorted((start, end, attribute, value) for (start, end), options in grouped.items() for attribute, value in chosen(text, start, options, totals))
    listed = set()
    run = []
    for span in [*spans, None]:
        if span and run and span[2] == run[-1][2] and LISTED.fullmatch(text, run[-1][1], span[0]):
            run.append(span)
            continue
        if len(run) >= RUN and run[0][2] in LISTS:
            listed.update(run)
        run = [span]
    told = set()
    for span in spans:
        start, end, attribute, value = span
        if (attribute, value) not in told and (span in listed or ((start, end) not in opened and engaged(text, start, end, attribute, (start, end, attribute) in famous, (start, end, attribute) in ordinary))):
            told.add((attribute, value))
            surface = text[start:end]
            named(attribute, surface if len(surface) > SHORT_KEY and " ".join(WORD.findall(surface.lower())) != " ".join(WORD.findall(value)) else value, found, start)
