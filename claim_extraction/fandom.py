import re
import unicodedata

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
MAIN = re.compile(rf"(?i:\bi (?:main|mained|play as|always play as) ){NAME}")
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
            named(kind, name, found, sentence.start())


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
        if kinds[kind] and kind not in NAMED_ONLY and (kind == "franchise" or re.search(r"[A-Z0-9]", text[match.start(1):match.end(1)])):
            named(kind, name, found, match.start())


DEGREE = r"(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted|avid|hardcore|crazy|super|major|total)"
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am|i've been|ive been|been|as|being) (?:an? )?(?:{DEGREE} )*){NAME}(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)")
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
MAINS = re.compile(rf"(?i:\b(?:an?|as an?|fellow|other|us|we|i'm an?|im an?|i am an?|been an?) ){NAME}(?i: (?:main|mains|one-?trick|otp)\b)")
MY_MAIN = re.compile(rf"(?i:\bmy (?:current |new |og |first )?mains? (?:is|are|was|has been|have been|include|includes):? ){NAME}")
SPLIT = re.compile(r"\s*(?:,|/|&|\band\b)\s*")
POSSESSIVE = re.compile(r"'s\b.*$")
STOP = re.compile(r"[.!?:;]\s")
PRONOUNS = frozenset({"i", "i'm", "im", "i've", "i'd", "i'll", "me", "my", "you", "we", "he", "she", "they"})
PEOPLE = ("character", "artist", "athlete", "celebrity", "creator", "author")
NAMED_ONLY = frozenset({"character", "athlete", "celebrity"})


def parts(name):
    name = STOP.split(name)[0]
    if " " not in name or lexical(name):
        return [name]
    return [piece for piece in SPLIT.split(POSSESSIVE.sub("", name)) if piece]


def lexical(name):
    return next(((attribute, value) for attribute, start, end, value, _, _ in mentions(name) if start == 0 and end == len(name.rstrip(" .,!:"))), None)


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
    for pattern in (FAN, FAN_OF, STAN, GOAT, GOATED, PRAISED):
        for match in pattern.finditer(text):
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for piece in parts(match.group(1)):
                    if hit := classified(text, match.start(), piece, (*PEOPLE, "franchise", "video_game")):
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
                elif not TARGET_CONTEXT["athlete"].search(text) and classified(text, match.start(), piece, ("franchise", "video_game")):
                    named("character", piece, found, match.start())
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
    for pattern in (MAIN, MAINS, MY_MAIN):
        for match in pattern.finditer(text):
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for piece in parts(match.group(1)):
                    named("character", piece, found, match.start())
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
BEST_SELLING_VIDEO_GAMES = """Tetris;Minecraft;Grand Theft Auto V;Red Dead Redemption 2;Wii Sports;Mario Kart 8 / Deluxe;PUBG: Battlegrounds;Terraria;The Elder Scrolls V: Skyrim;The Witcher 3: Wild Hunt;
Super Mario Bros.;Human: Fall Flat;Animal Crossing: New Horizons;Stardew Valley;Overwatch;Pokémon Red / Blue / Yellow;Wii Fit / Plus;Call of Duty: Black Ops III;Call of Duty: Modern Warfare;
Sonic the Hedgehog;Payday 2;Cyberpunk 2077;Hogwarts Legacy;Super Smash Bros. Ultimate;Mario Kart Wii;The Legend of Zelda: Breath of the Wild;Fallout 4;Wii Sports Resort;Borderlands 2;
New Super Mario Bros.;Super Mario Odyssey;Monster Hunter: World;New Super Mario Bros. Wii;Pokémon Gold / Silver / Crystal;Phasmophobia;Call of Duty: Black Ops Cold War;It Takes Two;
Elden Ring;Pokémon Scarlet / Violet;Duck Hunt;Wii Play;Black Myth: Wukong;Grand Theft Auto: San Andreas;Pokémon Sword / Shield;Call of Duty: Modern Warfare 3;Call of Duty: Black Ops;
Pokémon Sun / Moon / Ultra Sun / Ultra Moon;Garry's Mod;Pokémon Diamond / Pearl / Platinum;Grand Theft Auto IV"""
BEST_SELLING_VIDEO_GAME_FRANCHISES = """Mario;Tetris;Pokémon;Call of Duty;Grand Theft Auto;Minecraft;FIFA;Assassin's Creed;Resident Evil;Final Fantasy;Wii;Lego;The Sims;NBA 2K;The Legend of Zelda;Madden NFL;Need for Speed;
Sonic the Hedgehog;Monster Hunter;Red Dead;Pro Evolution Soccer;Star Wars;Mortal Kombat;Tomb Raider;Gran Turismo;Bejeweled;Borderlands;Dragon Quest;Tamagotchi;WWE 2K;The Witcher;Just Dance;
Battlefield;Donkey Kong;Halo;Civilization;The Walking Dead;Worms;Super Smash Bros.;Counter-Strike;Animal Crossing;Metal Gear;God of War;The Oregon Trail;The Elder Scrolls;Tekken;
Street Fighter;Far Cry;Kirby;Hitman;Metro;Destiny;Overwatch;Marvel's Spider-Man"""
GAME_AWARDS_GAME_OF_THE_YEAR_NOMINEES = """Dragon Age: Inquisition;Bayonetta 2;Dark Souls II;Hearthstone;Middle-earth: Shadow of Mordor;The Witcher 3: Wild Hunt;Bloodborne;Fallout 4;Metal Gear Solid V: The Phantom Pain;
Super Mario Maker;Overwatch;Doom;Inside;Titanfall 2;Uncharted 4: A Thief's End;The Legend of Zelda: Breath of the Wild;Horizon Zero Dawn;Persona 5;PlayerUnknown's Battlegrounds;
Super Mario Odyssey;God of War;Assassin's Creed Odyssey;Celeste;Marvel's Spider-Man;Monster Hunter: World;Red Dead Redemption 2;Sekiro: Shadows Die Twice;Control;Death Stranding;
Resident Evil 2;Super Smash Bros. Ultimate;The Outer Worlds;The Last of Us Part II;Animal Crossing: New Horizons;Doom Eternal;Final Fantasy VII Remake;Ghost of Tsushima;Hades;It Takes Two;
Deathloop;Metroid Dread;Psychonauts 2;Ratchet & Clank: Rift Apart;Resident Evil Village;Elden Ring;A Plague Tale: Requiem;God of War Ragnarök;Horizon Forbidden West;Stray;
Xenoblade Chronicles 3;Baldur's Gate 3;Alan Wake 2;The Legend of Zelda: Tears of the Kingdom;Marvel's Spider-Man 2;Resident Evil 4;Super Mario Bros. Wonder;Astro Bot;Balatro;
Black Myth: Wukong;Elden Ring Shadow of the Erdtree;Final Fantasy VII Rebirth;Metaphor: ReFantazio;Clair Obscur: Expedition 33;Death Stranding 2: On the Beach;Donkey Kong Bananza;Hades II;
Hollow Knight: Silksong;Kingdom Come: Deliverance II"""
VIDEO_GAMES_LISTED_AMONG_THE_BEST = """The Oregon Trail;Pong;Combat;Zork;Space Invaders;Asteroids;Adventure;Battlezone;Missile Command;Pac-Man;Centipede;Defender;Donkey Kong;Frogger;Galaga;Tempest;
Wizardry: Proving Grounds of the Mad Overlord;Zaxxon;Joust;Ms. Pac-Man;Pitfall!;Pole Position;Robotron: 2084;Archon: The Light and the Dark;Lode Runner;M.U.L.E.;Star Wars;Elite;
Marble Madness;Gauntlet;Ghosts 'n Goblins;A Mind Forever Voyaging;Super Mario Bros.;Tetris;Ultima IV: Quest of the Avatar;Arkanoid;Bubble Bobble;Castlevania;The Legend of Zelda;Metroid;
Out Run;Contra;Double Dragon;Dungeon Master;Head over Heels;Mike Tyson's Punch-Out!!;R-Type;Sid Meier's Pirates!;Mega Man 2;Ninja Gaiden;Super Mario Bros. 3;Final Fight;Golden Axe;Populous;
Prince of Persia;SimCity;Pilotwings;The Secret of Monkey Island;Speedball 2: Brutal Deluxe;Super Mario World;Wing Commander;Another World;Civilization;Final Fantasy IV;
The Legend of Zelda: A Link to the Past;Lemmings;Micro Machines;Monkey Island 2: LeChuck's Revenge;Sonic the Hedgehog;Street Fighter II;Super Castlevania IV;Alone in the Dark;
Contra III: The Alien Wars;Dune II;Flashback;Indiana Jones and the Fate of Atlantis;Mortal Kombat;Sensible Soccer;Sonic the Hedgehog 2;Star Control II;Streets of Rage 2;Super Mario Kart;
Ultima VII: The Black Gate;Virtua Racing;Wolfenstein 3D;Day of the Tentacle;Doom;Gunstar Heroes;The Legend of Zelda: Link's Awakening;Mega Man X;Mortal Kombat II;Myst;NBA Jam;
Phantasy Star IV;Ridge Racer;Sam & Max Hit the Road;Secret of Mana;Samurai Shodown;SimCity 2000;Sonic CD;Star Fox;Syndicate;Daytona USA;Donkey Kong Country;Doom II;EarthBound;
Final Fantasy VI;Puzzle Bobble;Sensible World of Soccer;Star Wars: TIE Fighter;Super Metroid;Tempest 2000;Theme Park;Virtua Fighter 2;X-COM: UFO Defense;Chrono Trigger;Command & Conquer;
MechWarrior 2: 31st Century Combat;Sega Rally Championship;Warcraft II: Tides of Darkness;Wipeout;Worms;Yoshi's Island;Civilization II;Command & Conquer: Red Alert;Duke Nukem 3D;
Mario Kart 64;Nights into Dreams;PaRappa the Rapper;Quake;Resident Evil;Super Mario 64;Tomb Raider;Wave Race 64;Wipeout 2097;Age of Empires;Castlevania: Symphony of the Night;Diablo;Fallout;
Final Fantasy Tactics;Final Fantasy VII;GoldenEye 007;Gran Turismo;Grand Theft Auto;Quake II;Star Fox 64;Star Wars Jedi Knight: Dark Forces II;Tekken 3;Total Annihilation;Ultima Online;
Baldur's Gate;Banjo-Kazooie;Crash Bandicoot: Warped;Dance Dance Revolution;Fallout 2;Grim Fandango;Half-Life;The Legend of Zelda: Ocarina of Time;Metal Gear Solid;Panzer Dragoon Saga;
Resident Evil 2;StarCraft;Suikoden II;Thief: The Dark Project;Xenogears;Age of Empires II;Crazy Taxi;EverQuest;Final Fantasy VIII;Freespace 2;Gran Turismo 2;Heroes of Might and Magic III;
Homeworld;Planescape: Torment;Quake III Arena;Shenmue;Silent Hill;Street Fighter III: 3rd Strike;System Shock 2;Tony Hawk's Pro Skater;Unreal Tournament;Baldur's Gate II: Shadows of Amn;
Counter-Strike;Deus Ex;Diablo II;Final Fantasy IX;Jet Set Radio;The Legend of Zelda: Majora's Mask;Perfect Dark;Marvel vs. Capcom 2: New Age of Heroes;The Sims;Skies of Arcadia;
Thief II: The Metal Age;Tony Hawk's Pro Skater 2;Vagrant Story;Advance Wars;Animal Crossing;Devil May Cry;Final Fantasy X;Gran Turismo 3: A-Spec;Grand Theft Auto III;Halo: Combat Evolved;
Ico;Ikaruga;Max Payne;Metal Gear Solid 2: Sons of Liberty;Phoenix Wright: Ace Attorney;Rez;Silent Hill 2;Super Smash Bros. Melee;Tony Hawk's Pro Skater 3;Virtua Fighter 4;Battlefield 1942;
The Elder Scrolls III: Morrowind;Eternal Darkness: Sanity's Requiem;Grand Theft Auto: Vice City;Kingdom Hearts;The Legend of Zelda: The Wind Waker;Metroid Prime;Soulcalibur II;
Tom Clancy's Splinter Cell;Warcraft III: Reign of Chaos;Beyond Good & Evil;F-Zero GX;Max Payne 2: The Fall of Max Payne;Prince of Persia: The Sands of Time;
Star Wars: Knights of the Old Republic;Viewtiful Joe;WarioWare, Inc.: Mega Microgames!;Burnout 3: Takedown;The Chronicles of Riddick: Escape from Butcher Bay;Dragon Quest VIII;
Gran Turismo 4;Grand Theft Auto: San Andreas;Half-Life 2;Halo 2;Katamari Damacy;Lumines: Puzzle Fusion;Metal Gear Solid 3: Snake Eater;Rome: Total War;The Sims 2;World of Warcraft;
Battlefield 2;Call of Duty 2;Civilization IV;Devil May Cry 3: Dante's Awakening;God of War;Guitar Hero;Kingdom Hearts II;Psychonauts;Resident Evil 4;Shadow of the Colossus;
Tom Clancy's Splinter Cell: Chaos Theory;Company of Heroes;The Elder Scrolls IV: Oblivion;Gears of War;Hitman: Blood Money;The Legend of Zelda: Twilight Princess;Ōkami;Virtua Fighter 5;
Wii Sports;BioShock;Call of Duty 4: Modern Warfare;God of War II;Halo 3;Mass Effect;Pac-Man Championship Edition;Peggle;Portal;Rock Band;Super Mario Galaxy;Team Fortress 2;
The World Ends with You;Braid;Burnout Paradise;Dead Space;Fable II;Fallout 3;Gears of War 2;Grand Theft Auto IV;Left 4 Dead;LittleBigPlanet;Metal Gear Solid 4: Guns of the Patriots;
Persona 4;Rock Band 2;Spelunky;Street Fighter IV;Super Smash Bros. Brawl;Valkyria Chronicles;Angry Birds;Assassin's Creed II;Batman: Arkham Asylum;Bayonetta;Borderlands;Demon's Souls;
Dragon Age: Origins;League of Legends;Left 4 Dead 2;Plants vs. Zombies;The Sims 3;Uncharted 2: Among Thieves;Assassin's Creed: Brotherhood;Civilization V;Fallout: New Vegas;God of War III;
Heavy Rain;Limbo;Mass Effect 2;Red Dead Redemption;Rock Band 3;StarCraft II: Wings of Liberty;Super Mario Galaxy 2;Super Meat Boy;Xenoblade Chronicles;Batman: Arkham City;Dark Souls;
The Elder Scrolls V: Skyrim;Minecraft;Portal 2;Borderlands 2;Dishonored;Far Cry 3;Fire Emblem Awakening;Hotline Miami;Journey;Mass Effect 3;The Walking Dead;XCOM: Enemy Unknown;
Assassin's Creed IV: Black Flag;BioShock Infinite;Dota 2;Final Fantasy XIV: A Realm Reborn;Grand Theft Auto V;The Last of Us;Papers, Please;The Stanley Parable;Alien: Isolation;Destiny;
Hearthstone;Mario Kart 8;Shovel Knight;Bloodborne;Life Is Strange;Metal Gear Solid V: The Phantom Pain;Rocket League;Undertale;The Witcher 3: Wild Hunt;Dishonored 2;Inside;Overwatch;
Persona 5;Stardew Valley;Titanfall 2;Uncharted 4: A Thief's End;The Witness;Divinity: Original Sin II;Fortnite;Hollow Knight;Nier: Automata;The Legend of Zelda: Breath of the Wild;
Super Mario Odyssey;Celeste;Red Dead Redemption 2;Return of the Obra Dinn;Super Smash Bros. Ultimate;Disco Elysium;Outer Wilds;Animal Crossing: New Horizons;Hades;The Last of Us Part II;
Elden Ring;Baldur's Gate 3"""
BEST_SELLING_PC_GAMES = """PUBG: Battlegrounds;PUBG Universe;Minecraft;Terraria;Stardew Valley;Garry's Mod;Euro Truck Simulator 2;Truck Simulator;Diablo III;Diablo;Meccha Chameleon;Counter-Strike: Source;
Counter-Strike;World of Warcraft;Warcraft;Helldivers 2;Grand Theft Auto V;Half-Life 2;Half-Life;The Witcher 3: Wild Hunt;The Witcher;Valheim;The Sims;StarCraft;Ready or Not;
Kingdom Come: Deliverance;RollerCoaster Tycoon 3;RollerCoaster Tycoon;Fall Guys;Peak;Civilization V;Civilization;Deep Rock Galactic;Cyberpunk 2077;The Sims 3;Star Wars: Empire at War;
Guild Wars;The Sims 2;Cities: Skylines;StarCraft II: Wings of Liberty;Myst;Age of Empires;Last Ninja 2;Last Ninja;ARMA 3;ARMA;Satisfactory;Tomb Raider;Fallout: New Vegas;Fallout;
Baldur's Gate 3;Baldur's Gate;Sea of Thieves;SimCity 3000;SimCity;Guild Wars 2;Arma 2: Operation Arrowhead;RV There Yet?;BioShock Infinite;BioShock;American Truck Simulator;The Last Ninja;
Risk of Rain 2;Diablo II;Buckshot Roulette;Carmen Sandiego;Populous;Warhammer 40,000: Dawn of War;Warhammer;Sid Meier's Civilization VI;Dark Souls;Factorio;Dark Souls III;
Total War: Three Kingdoms;Total War;Mount & Blade;Resident Evil 4: Ultimate HD Edition;Resident Evil;Manor Lords;Command & Conquer;Command & Conquer: Red Alert;EverQuest;
Warcraft III: Reign of Chaos;Escape from Duckov;Civilization IV;Crysis;Space Engineers;V Rising;Super Meat Boy;Hitman: Absolution;Hitman;Outlast;The Walking Dead;Prison Architect;Subnautica;
Magicka;Infestation: Survivor Stories;Dark Souls II;Lords of the Realm II;Caesar II;Caesar III;Anno 1602;Anno;Starbound;Hotline Miami;Rise of the Tomb Raider;Battlefield 1942;Battlefield;
Batman: Arkham City - Game of the Year Edition;Batman: Arkham;Command & Conquer: Tiberian Sun;Horizon Zero Dawn;Horizon;Mafia II;Mafia;Papers, Please;Content Warning;Last Epoch;
Final Fantasy VII;Final Fantasy;Banished;IL-2 Sturmovik;Deer Hunter;Doom;Doom II: Hell on Earth;Warcraft II: Tides of Darkness;Plague Inc.: Evolved;Baldur's Gate II: Shadows of Amn;
Age of Empires II: The Age of Kings;Ensemble Studios;Microsoft;Orion: Prelude;Civilization III;Sons of the Forest;Neverwinter Nights;Stronghold: Crusader;Stronghold;
Mafia: The City of Lost Heaven;SimCity 4;Anno 1503;Counter-Strike: Condition Zero;Far Cry;Age of Empires III;Cossacks II: Napoleonic Wars;Cossacks;Crusader Kings III;The 7th Guest;
The Witcher 2: Assassins of Kings;Battlefield 2;7 Days to Die;Metro 2033 Redux;Planet Coaster;Stick Fight: The Game;BattleBit Remastered;Tale of Immortal;
Metal Gear Solid V: The Phantom Pain;Metal Gear Solid;Barbie Fashion Designer;Max Payne 3;Star Citizen;Dungeon Siege;Assassin's Creed IV Black Flag;Assassin's Creed;L.A. Noire;BioShock 2;
Railroad Tycoon II;Railroad Tycoon;International Karate;Marvel's Spider-Man Remastered;Marvel's Spider-Man;Sega Mega Drive and Genesis Classics;PlateUp!;Windrose;Monster Hunter Wilds;
Monster Hunter;Dead Rising 3 Apocalypse Edition;Dead Rising;Frostpunk;Age of Conan;Ultra Street Fighter IV;Street Fighter;Battlefield Vietnam;Riven;Resident Evil 6;Gujian 3;Lost Ark;FEZ;
Monopoly;Nier: Automata;Nier;SimCity 2000;Pac-Man Championship Edition DX+;Pac-Man;To the Moon;Brothers: A Tale of Two Sons;The Walking Dead: Season Two;Hotline Miami 2: Wrong Number;
The Wolf Among Us;Braid;Assassin's Creed Origins;BlazBlue;Hydlide;Creatures;Big G All-Stars vs. Major League Baseball;Mewgenics;Tetris;Hollow Knight;RoboCop;Return to Zork;Zork;
Star Wars: Rebel Assault;Star Wars;Star Wars Galaxies;Soma;Wing Commander 3: Heart of the Tiger;Wing Commander;Paralives;Celtic Kings: Rage of War;HyperBlade;
Daryl F. Gates' Police Quest: SWAT;Police Quest;Duke Nukem 3D;Duke Nukem;Civilization II;Quake;Quake II;Chuck Yeager's Advanced Flight Trainer;Grand Prix 2;Coral Island;Dwarf Fortress;
Angels of Death;Total Annihilation;Don't Starve;Deer Hunter II: The Hunt Continues;Unreal;Unreal Tournament;Commandos: Behind Enemy Lines;Commandos;InZOI;Dave the Diver;Move or Die;
Stellar Blade;Hidden & Dangerous;The Planet Crafter;Brotato;Who Wants to Be a Millionaire?;Loop Hero;American McGee's Alice;Command & Conquer: Red Alert 2;Depth;Tropico;
Operation Flashpoint: Cold War Crisis;Rocket League;Black Myth: Wukong;Runaway: A Road Adventure;Zoo Tycoon;Aion;Empire Earth;Dome Keeper;Harry Potter;Slay the Spire;Dune: Awakening;
Return to Castle Wolfenstein;Wolfenstein;Gunfire Reborn;Among Us;Escape Simulator;Persona 4 Golden;Contraband Police;Hotel Giant;Age of Mythology;The Legend of Sword and Fairy 3;
The Legend of Sword and Fairy;Anno 2070;Hidden & Dangerous 2;Patrician III: Rise of the Hanse;The Patrician;CloverPit;Inscryption;Rome: Total War;Psychonauts;Imperivm: Great Battles of Rome;
Glory of the Roman Empire;Microsoft Flight Simulator X;Microsoft Flight Simulator;Thexder;F-15 Strike Eagle;The Scroll of Taiwu;Scum;Command & Conquer 3: Tiberium Wars;
The Murder of Sonic the Hedgehog;Sonic the Hedgehog;Crysis Warhead;Sultan's Game;Grim Dawn;Green Hell;Warhammer Online: Age of Reckoning;Torchlight II;Resident Evil 5;Machinarium;Megabonk;
The Legend of Sword and Fairy 5;Crusader Kings II;Crusader Kings;StarCraft II: Heart of the Swarm;Europa Universalis IV;Europa Universalis;The Stanley Parable;Just Survive;
Ark: Survival Evolved;Lego Island;StarCraft II: Legacy of the Void;Danganronpa: Trigger Happy Havoc;Danganronpa;Danganronpa 2: Goodbye Despair;Hearts of Iron IV;No Rest for the Wicked;
Divinity: Original Sin II;Divinity;Cuphead"""
BEST_SELLING_NINTENDO_SWITCH_GAMES = """Mario Kart 8 Deluxe;Animal Crossing: New Horizons;Super Smash Bros. Ultimate;The Legend of Zelda: Breath of the Wild;Super Mario Odyssey;The Legend of Zelda: Tears of the Kingdom;
Super Mario Party;New Super Mario Bros. U Deluxe;Nintendo Switch Sports;Super Mario Bros. Wonder;Ring Fit Adventure;Pokémon Legends: Arceus;Luigi's Mansion 3;Mario Party Superstars;
Splatoon 2;Super Mario 3D World + Bowser's Fury;Splatoon 3;Super Mario Party Jamboree;Pokémon Legends: Z-A;Super Mario 3D All-Stars;Super Mario Maker 2;Monster Hunter Rise;
Tomodachi Life: Living the Dream;Stardew Valley;Kirby and the Forgotten Land;Suika Game;Minecraft;The Legend of Zelda: Link's Awakening;Clubhouse Games: 51 Worldwide Classics;
Donkey Kong Country: Tropical Freeze;Mario Tennis Aces;Kirby Star Allies;The Legend of Zelda: Skyward Sword HD;Fire Emblem: Three Houses;The Legend of Zelda: Echoes of Wisdom;
Hyrule Warriors: Age of Calamity;Momotaro Dentetsu: Showa, Heisei, Reiwa Mo Teiban!;1-2-Switch;Pikmin 4;Paper Mario: The Origami King;Yoshi's Crafted World;Super Mario RPG;Among Us;
Metroid Dread;Mario + Rabbids Sparks of Hope;Super Mario Galaxy 2;New Pokémon Snap;Arms;Xenoblade Chronicles 2;Super Mario Galaxy;Mario Strikers: Battle League;Mario Golf: Super Rush;
Dragon Ball FighterZ;Pikmin 3 Deluxe;Captain Toad: Treasure Tracker;Taiko no Tatsujin: Drum 'n' Fun!;Octopath Traveler;Paper Mario: The Thousand-Year Door;Human: Fall Flat;
Mario + Rabbids Kingdom Battle;Pokémon Mystery Dungeon: Rescue Team DX;Mario & Luigi: Brothership;Big Brain Academy: Brain vs. Brain;Luigi's Mansion 2 HD;
Xenoblade Chronicles: Definitive Edition;Xenoblade Chronicles 3;Dragon Ball Xenoverse 2;Miitopia;Mario Kart Live: Home Circuit;Naruto Shippudden: Ultimate Ninja Storm Trilogy;
Resident Evil: Revelations Collection;Fire Emblem Engage;Marvel Ultimate Alliance 3: The Black Order;Pokkén Tournament DX;Momotaro Dentetsu World: Chikyuu wa Kibou de Mawatteru!;
Kirby's Return to Dream Land Deluxe;Nintendo Labo Toy-Con 01: Variety Kit;WarioWare: Get It Together!;Astral Chain;Dragon's Dogma: Dark Arisen;Princess Peach: Showtime!;Resident Evil 6;
Donkey Kong Country Returns HD;Dr Kawashima's Brain Training for Nintendo Switch;Bayonetta;Bayonetta 2;Resident Evil 4;Dark Souls Remastered;Game Builder Garage;Mario vs. Donkey Kong;
Shin Megami Tensei V;Metroid Prime Remastered;Bayonetta 3;Mario & Sonic at the Olympic Games Tokyo 2020;Dragon Quest III HD-2D Remake;Dragon Quest Monsters: The Dark Prince;
Enter the Gungeon;Fire Emblem Warriors: Three Hopes;Fitness Boxing;Rhythm Heaven Groove;Story of Seasons: Pioneers of Olive Town;Thief Simulator"""
BEST_SELLING_PLAYSTATION_4_GAMES = """Grand Theft Auto V;Marvel's Spider-Man;God of War;Horizon Zero Dawn;Uncharted 4: A Thief's End;The Last of Us Remastered;Minecraft: PlayStation 4 Edition;Call of Duty: Black Ops III;
Call of Duty: WWII;Gran Turismo Sport;The Witcher 3: Wild Hunt;The Last of Us Part II;Uncharted: The Nathan Drake Collection;Ghost of Tsushima;Bloodborne;Call of Duty: Infinite Warfare;
Star Wars Battlefront;Days Gone;Ratchet & Clank;Tekken 7;Naruto Shippuden: Ultimate Ninja Storm 4;Call of Duty: Advanced Warfare;Infamous Second Son;God of War III Remastered;
Detroit: Become Human;LittleBigPlanet 3;Uncharted: The Lost Legacy;Final Fantasy VII Remake;Driveclub;Dragon Ball Xenoverse 2;Death Stranding;Dragon Ball FighterZ;Until Dawn;
Monster Hunter: World;Dark Souls III;Jump Force;Cyberpunk 2077;Metal Gear Solid V: The Phantom Pain;Dragon Ball Z: Kakarot;FIFA 17;Elden Ring;Nioh;Nier: Automata;Final Fantasy XV;
Dragon Ball: Xenoverse;Crash Bandicoot N. Sane Trilogy;FIFA 18;Persona 5 Royal;Naruto to Boruto: Shinobi Striker;Killzone: Shadow Fall;Gran Turismo 7;
Naruto Shippuden: Ultimate Ninja Storm Trilogy;Knack;Dark Souls Remastered;Kingdom Hearts HD 1.5 + 2.5 Remix;Dark Souls II: Scholar of the First Sin;FIFA 20;Nioh 2;FIFA 19;Soulcalibur VI;
Battlefield 1;Dragon Quest XI: Echoes of an Elusive Age;Kingdom Hearts HD 2.8 Final Chapter Prologue;Metal Gear Solid V: Ground Zeroes;Tales of Berseria;Final Fantasy XII: The Zodiac Age;
FIFA 22;FIFA 21;One Piece: Pirate Warriors 3;Code Vein;Ark: Survival Evolved;Final Fantasy Type-0 HD;Kingdom Hearts III"""
BEST_SELLING_PLAYSTATION_5_GAMES = """Marvel's Spider-Man 2;Gran Turismo 7;EA Sports FC 26;Resident Evil 4;Black Myth: Wukong;Helldivers 2;Forza Horizon 5;Astro Bot;God of War Ragnarök;Ghost of Yōtei;Ratchet & Clank: Rift Apart;
Elden Ring;Stellar Blade;Battlefield 6;Clair Obscur: Expedition 33;ARC Raiders;Final Fantasy XVI;Monster Hunter Wilds;Resident Evil Requiem;Assassin's Creed Shadows;Demon's Souls;
Sea of Thieves;Dragon's Dogma 2;Elden Ring Nightreign;Minecraft;EA Sports FC 24;Death Stranding 2: On the Beach;The Elder Scrolls IV: Oblivion Remastered;Crimson Desert;
EA Sports College Football 26;EA Sports FC 25;Madden NFL 26"""
BEST_SELLING_NINTENDO_GAMES = """Wii Sports;Mario Kart 8 Deluxe;Animal Crossing: New Horizons;Super Mario Bros.;Super Smash Bros. Ultimate;Mario Kart Wii;The Legend of Zelda: Breath of the Wild;Wii Sports Resort;
Pokémon Red/Green/Blue;New Super Mario Bros.;Super Mario Odyssey;New Super Mario Bros. Wii;Duck Hunt;Wii Play;Pokémon Sword/Shield;Nintendogs;Pokémon Gold/Silver;Mario Kart DS;
The Legend of Zelda: Tears of the Kingdom;Wii Fit;Super Mario Party;Wii Fit Plus;Super Mario World"""
BEST_SELLING_GAME_BOY_GAMES = """Pokémon Yellow;Tetris;Pokémon Crystal;Super Mario Land;Super Mario Land 2: 6 Golden Coins;Dr. Mario;Pokémon Pinball;Wario Land: Super Mario Land 3;Kirby's Dream Land;
Super Mario Bros. Deluxe;Donkey Kong Land;The Legend of Zelda: Link's Awakening;Pokémon Trading Card Game;F1 Race;Yoshi;Donkey Kong;Tamagotchi;Yu-Gi-Oh! Dark Duel Stories;
Kirby's Dream Land 2;Donkey Kong Land 2;Dragon Warrior Monsters;The Legend of Zelda: Link's Awakening DX;Wario Land 3;Kirby's Pinball Land;Donkey Kong Country;Golf;Tennis;Alleyway;Tetris DX;
Metroid II: Return of Samus;Baseball;Dragon Warrior Monsters 2;Yoshi's Cookie;Wario Land II;DuckTales;The Final Fantasy Legend;Yakuman;Tetris 2;Kirby Tilt 'n' Tumble;Game & Watch Gallery 2;
Game & Watch Gallery 3;Solar Striker;Mario Tennis;Qix;Super R.C. Pro-Am;Donkey Kong Land III;The Bugs Bunny Crazy Castle;The Bugs Bunny Crazy Castle 2;Mickey's Dangerous Chase;
The Little Mermaid;Mega Man: Dr. Wily's Revenge;Mega Man II;Wave Race;Star Wars;DuckTales 2;Mortal Kombat;Mickey Mouse: Magic Wands!;Space Invaders;The Smurfs;Street Fighter II;
Game & Watch Gallery;James Bond 007"""
BEST_SELLING_GAME_BOY_ADVANCE_GAMES = """Pokémon Emerald;Mario Kart: Super Circuit;Super Mario World: Super Mario Advance 2;Super Mario Advance;Super Mario Advance 4: Super Mario Bros. 3;Namco Museum;Pac-Man Collection;
Yoshi's Island: Super Mario Advance 3;The Legend of Zelda: A Link to the Past;Pokémon Mystery Dungeon: Red Rescue Team;Classic NES Series;Wario Land 4;Mario & Luigi: Superstar Saga;
Kirby: Nightmare in Dream Land;Finding Nemo;Donkey Kong Country;The Legend of Zelda: The Minish Cap;Yu-Gi-Oh! The Eternal Duelist Soul;Frogger's Adventures: Temple of the Frog;Golden Sun;
Final Fantasy Tactics Advance;Metroid Fusion;Kingdom Hearts: Chain of Memories;Sonic Advance;Kirby & the Amazing Mirror;Yu-Gi-Oh! Worldwide Edition: Stairway to the Destined Duel;
Dragon Ball Z: The Legacy of Goku;Mario vs. Donkey Kong;Pokémon Pinball: Ruby & Sapphire;The Incredibles;Mega Man Battle Network 4;Harry Potter and the Chamber of Secrets;
Golden Sun: The Lost Age;WarioWare, Inc.: Mega Microgames!;F-Zero: Maximum Velocity;Sonic Advance 2;Spyro: Season of Ice"""
BEST_SELLING_GAMECUBE_GAMES = """Super Smash Bros. Melee;Mario Kart: Double Dash;Super Mario Sunshine;The Legend of Zelda: The Wind Waker;Luigi's Mansion;Metroid Prime;Animal Crossing;Mario Party 4;Pokémon Colosseum;
Mario Party 5;Mario Party 7;Paper Mario: The Thousand-Year Door;Star Fox Adventures;Sonic Adventure 2: Battle;Mario Party 6;Pikmin;Resident Evil 4;Sonic Adventure DX: Director's Cut;
Super Mario Strikers;The Legend of Zelda: Twilight Princess;Pokémon XD: Gale of Darkness;Sonic Heroes;Sonic Mega Collection;Resident Evil;Kirby Air Ride;Final Fantasy Crystal Chronicles;
Resident Evil Zero;Mario Golf: Toadstool Tour;Donkey Konga;Mario Power Tennis;Star Wars Rogue Squadron II: Rogue Leader;Pikmin 2;Metroid Prime 2: Echoes;Soulcalibur II;
Mario Superstar Baseball;Sonic Gems Collection"""
BEST_SELLING_NINTENDO_3DS_GAMES = """Mario Kart 7;New Super Mario Bros. 2;Animal Crossing: New Leaf;Super Mario 3D Land;Super Smash Bros. for Nintendo 3DS;Yo-kai Watch 2;Tomodachi Life;Luigi's Mansion: Dark Moon;
The Legend of Zelda: Ocarina of Time 3D;Nintendogs + Cats;Monster Hunter Generations;The Legend of Zelda: A Link Between Worlds;Monster Hunter 4 Ultimate;Monster Hunter 4;
Super Mario Maker for Nintendo 3DS;Animal Crossing: Happy Home Designer;The Legend of Zelda: Majora's Mask 3D;Yo-kai Watch;Mario Party: Island Tour;Donkey Kong Country Returns 3D;
Mario & Luigi: Dream Team;Kirby: Triple Deluxe;Monster Hunter 3 Ultimate;Paper Mario: Sticker Star;Fire Emblem Awakening;Yo-kai Watch 3;Yoshi's New Island;
Lego City Undercover: The Chase Begins;Monster Hunter XX;Dragon Quest XI: Echoes of an Elusive Age;Pokémon Super Mystery Dungeon;Kirby: Planet Robobot;
Dragon Quest VII: Fragments of the Forgotten Past;Mario Tennis Open;Puzzle & Dragons Z: Pazudora Z;Pokémon Red / Green / Blue;Professor Layton and the Miracle Mask;Style Savvy: Trendsetters;
Pokémon Rumble Blast;Bravely Default;Pokémon Mystery Dungeon: Gates to Infinity;Kid Icarus: Uprising;The Legend of Zelda: Tri Force Heroes;Super Street Fighter IV: 3D Edition;
Kingdom Hearts 3D: Dream Drop Distance;Miitopia;Fantasy Life;Mario & Luigi: Paper Jam;Star Fox 64 3D;Rhythm Heaven Megamix;Monster Strike;Style Savvy: Fashion Forward;
Fire Emblem Echoes: Shadows of Valentia"""
BEST_SELLING_NINTENDO_64_GAMES = """Super Mario 64;Mario Kart 64;GoldenEye 007;The Legend of Zelda: Ocarina of Time;Super Smash Bros.;Pokémon Stadium;Donkey Kong 64;Diddy Kong Racing;Star Fox 64;Banjo-Kazooie;Pokémon Snap;
The Legend of Zelda: Majora's Mask;Star Wars Episode I: Racer;Wave Race 64;Yoshi's Story;Mario Party;Star Wars: Shadows of the Empire;Pokémon Stadium 2;Perfect Dark;Mario Party 2;
Mario Tennis;Star Wars: Rogue Squadron;1080° Snowboarding;Excitebike 64;Mario Party 3;WCW/nWo Revenge;Hey You, Pikachu!;Kirby 64: The Crystal Shards;Cruis'n USA;Tony Hawk's Pro Skater;
F-1 World Grand Prix;Turok: Dinosaur Hunter;Banjo-Tooie;Mario Golf;Turok 2: Seeds of Evil;Paper Mario;WCW vs. nWo: World Tour;Mission: Impossible;Kobe Bryant in NBA Courtside;WWF No Mercy;
Jet Force Gemini;WWF WrestleMania 2000;Pilotwings 64;F-Zero X;Pocket Monsters Stadium;007: The World Is Not Enough;Namco Museum 64;Bomberman 64;Bomberman Hero;
Waialae Country Club: True Golf Classics;South Park Rally;International Superstar Soccer 64;Snowboard Kids"""
BEST_SELLING_NINTENDO_DS_GAMES = """New Super Mario Bros.;Nintendogs;Mario Kart DS;Brain Age: Train Your Brain in Minutes a Day!;Brain Age 2: More Training in Minutes a Day!;Animal Crossing: Wild World;Super Mario 64 DS;
Mario Party DS;Pokémon Platinum;Big Brain Academy;Dragon Quest IX: Sentinels of the Starry Skies;Lego Star Wars: The Complete Saga;The Legend of Zelda: Phantom Hourglass;
Mario & Luigi: Bowser's Inside Story;Professor Layton and the Curious Village;Mario & Sonic at the Olympic Games;Professor Layton and the Diabolical Box;Tomodachi Collection;
Pokémon Mystery Dungeon: Blue Rescue Team;Yoshi's Island DS;Flash Focus: Vision Training in Minutes a Day;Rhythm Heaven;Professor Layton and the Unwound Future;
Professor Kageyama's Maths Training: The Hundred Cell Calculation Method;Kirby Super Star Ultra;Mario vs. Donkey Kong: Mini-Land Mayhem!;Style Savvy;The Legend of Zelda: Spirit Tracks;
Pokémon Ranger;Tetris DS;Clubhouse Games;WarioWare: Touched!;Pokémon Ranger: Shadows of Almia;Art Academy;Final Fantasy III;Kirby: Squeak Squad;Cooking Mama;
Cooking Guide: Can't Decide What to Eat?;Professor Layton and the Last Specter;Mario Hoops 3-on-3;Dragon Quest Monsters: Joker 2;Dragon Quest Monsters: Joker;Mario & Luigi: Partners in Time;
Super Princess Peach;Dragon Quest V: Hand of the Heavenly Bride;Dragon Quest VI: Realms of Revelation;Kingdom Hearts 358/2 Days;Common Sense Training;Dragon Quest IV: Chapters of the Chosen;
Sonic Rush;Diddy Kong Racing DS;Pokémon Ranger: Guardian Signs;Mario vs. Donkey Kong 2: March of the Minis;Pokémon Mystery Dungeon: Explorers of Sky;Tamagotchi Connection: Corner Shop;
Guitar Hero: On Tour;Hannah Montana;MySims;Kirby Mass Attack;High School Musical: Makin' the Cut!;Final Fantasy IV;Love and Berry DS Collection;Chrono Trigger;
Tamagotchi Connection: Corner Shop 2;Metroid Prime Hunters;Final Fantasy XII: Revenant Wings;Drawn to Life;Scribblenauts;Spectrobes;Pony Friends"""
BEST_SELLING_PLAYSTATION_GAMES = """Gran Turismo;Final Fantasy VII;Gran Turismo 2;Final Fantasy VIII;Tekken 3;Harry Potter and the Philosopher's Stone;Crash Bandicoot 2: Cortex Strikes Back;Crash Bandicoot: Warped;Tomb Raider;
Metal Gear Solid;Crash Bandicoot;Tomb Raider II;Tomb Raider III;Resident Evil 2;Tekken 2;Final Fantasy IX;Resident Evil;Spyro the Dragon;Crash Team Racing;Oddworld: Abe's Oddysee;
Tomb Raider: The Last Revelation;Dragon Quest VII;Rayman;Tony Hawk's Pro Skater;Resident Evil 3: Nemesis;Spyro 2: Ripto's Rage;Frogger;Spyro: Year of the Dragon;Driver;
Tony Hawk's Pro Skater 2;Croc: Legend of the Gobbos;Driver 2;Yu-Gi-Oh! Forbidden Memories;Dino Crisis;Namco Museum Vol. 3;Everybody's Golf;Final Fantasy Tactics;Air Combat;WWF War Zone;
Tony Hawk's Pro Skater 3;Mortal Kombat Trilogy;Derby Stallion;Silent Hill;Frogger 2: Swampy's Revenge;Parasite Eve;WWF SmackDown!;WWF SmackDown! 2: Know Your Role;Crash Bash;Spider-Man;
Namco Museum Vol. 1;Tetris Plus;Syphon Filter;Twisted Metal 2;Tekken;007: Tomorrow Never Dies;Formula 1;Need for Speed III: Hot Pursuit;PaRappa the Rapper;Medal of Honor;Everybody's Golf 2;
Arc the Lad;Madden NFL 99;A Bug's Life;007: The World Is Not Enough;Legacy of Kain: Soul Reaver;Chrono Cross;Madden NFL 2000;NFL GameDay 98;Ridge Racer;Rugrats: Search for Reptar;
Grand Theft Auto 2;Cool Boarders 3;Syphon Filter 2;Dance Dance Revolution;Ape Escape;Tomb Raider: Chronicles;Need for Speed: High Stakes;The Legend of Dragoon;Pac-Man World;Jet Moto 2;
WCW Nitro;Twisted Metal III;Battle Arena Toshinden;Jet Moto;Spec Ops: Stealth Patrol;Madden NFL 98;Dragon Quest IV;Tenchu: Stealth Assassins;SaGa Frontier;Cool Boarders 2;Xenogears;
Dino Crisis 2;Monopoly;Arc the Lad II;Metal Gear Solid: VR Missions;Chocobo's Mysterious Dungeon;Ace Combat 3: Electrosphere;NASCAR 98;NBA Live 98;Devil Dice;NASCAR 99;Tales of Destiny;
NFL GameDay 99;I.Q.: Intelligent Qube;Doko Demo Issyo;beatmania;Derby Stallion 99;Star Ocean: The Second Story;Ace Combat 2;2Xtreme;Parasite Eve II;Twisted Metal;Test Drive 5;
Twisted Metal 4;SpongeBob SquarePants: SuperSponge;R4: Ridge Racer Type 4;Densha de Go!;Dance Dance Revolution 2nd ReMix;NFL GameDay;Monster Rancher;Fighting Force;Colin McRae Rally;
Simple 1500 Series Vol. 1: The Mahjong;Street Fighter Alpha 3;WCW/nWo Thunder;NBA Live 2000;Dancing Stage Party Edition"""
BEST_SELLING_PLAYSTATION_2_GAMES = """Grand Theft Auto: San Andreas;Gran Turismo 3: A-Spec;Grand Theft Auto: Vice City;Gran Turismo 4;Grand Theft Auto III;Tekken 5;Final Fantasy X;Metal Gear Solid 2: Sons of Liberty;
Final Fantasy XII;Kingdom Hearts;Final Fantasy X-2;Kingdom Hearts II;Dragon Quest VIII: Journey of the Cursed King;God of War;Madden NFL 2005;Tekken 4;Tekken Tag Tournament;God of War II;
Metal Gear Solid 3: Snake Eater;Jak and Daxter: The Precursor Legacy;EyeToy: Play;Madden NFL 2004;Madden NFL 06;Ratchet & Clank;Need for Speed: Underground;Star Wars: Battlefront;
Star Wars: Battlefront II;Medal of Honor: Frontline;Lego Star Wars: The Video Game;Guitar Hero II;Pro Evolution Soccer 3;Star Wars: Episode III – Revenge of the Sith;
Guitar Hero III: Legends of Rock;Ratchet & Clank: Up Your Arsenal;Madden NFL 2003;Pro Evolution Soccer 4;The Getaway;Ratchet & Clank: Going Commando;Sonic Heroes;WWE SmackDown! vs. Raw 2006;
Pro Evolution Soccer 2008;Pro Evolution Soccer 2;Spider-Man;Madden NFL 07;SOCOM U.S. Navy SEALs;Crash Bandicoot: The Wrath of Cortex;Ace Combat 04: Shattered Skies;Dragon Ball Z: Budokai;
The Simpsons: Hit & Run;Need for Speed: Most Wanted;Medal of Honor: Rising Sun;The Lord of the Rings: The Two Towers;Driver 3;Dynasty Warriors 4;Tony Hawk's Underground;
Tony Hawk's Pro Skater 3;Devil May Cry 3: Dante's Awakening;Madden NFL 2002;Resident Evil 4;Dynasty Warriors 3;The Simpsons: Road Rage;Ratchet: Deadlocked;SOCOM II U.S. Navy SEALs;
Devil May Cry;Hot Shot Golf 3;Max Payne;Need for Speed: Underground 2;Onimusha 2: Samurai's Destiny;Dragon Ball Z: Budokai 2;True Crime: Streets of LA;007: Agent Under Fire;
Onimusha: Warlords;Dragon Ball Z: Budokai Tenkaichi;ESPN NFL 2K5;Killzone;Pro Evolution Soccer 5;WWE SmackDown! vs. Raw;ATV Offroad Fury;NBA Live 2005;Midnight Club: Street Racing;
Spider-Man 2;Madden NFL 08;Pro Evolution Soccer 6;Hot Shots Golf Fore!;Dragon Ball Z: Budokai 3;Dragon Quest V: Hand of the Heavenly Bride;007: Nightfire;Ace Combat 5: The Unsung War;
Namco Museum;ATV Offroad Fury 2;Sonic Mega Collection Plus;WWE SmackDown! Shut Your Mouth;Call of Duty: Finest Hour;NBA Street;Devil May Cry 2;Grand Theft Auto: Liberty City Stories;
Mortal Kombat: Deadly Alliance;Yakuza;Virtua Fighter 4;Enter the Matrix;Need for Speed: Hot Pursuit 2;Jak II;NBA Street Vol. 2;WWE SmackDown! Here Comes the Pain;Gran Turismo Concept;
Dynasty Warriors 5;Guitar Hero;WWE SmackDown vs. Raw 2007;Onimusha 3: Demon Siege;Bratz: Rock Angelz;Bully;Samurai Warriors;Tony Hawk's Underground 2;NBA Live 2004;
WWF SmackDown! Just Bring It;Disney•Pixar Finding Nemo;Resident Evil Outbreak;Yu-Gi-Oh! The Duelists of the Roses;Tiger Woods PGA Tour 2004;Tony Hawk's Pro Skater 4;
Hitman 2: Silent Assassin;The Sims;Gran Turismo 4 Prologue;Resident Evil – Code: Veronica X;NCAA Football 06;Crazy Taxi;LEGO Star Wars II: The Original Trilogy;
The Lord of the Rings: The Return of the King;Star Ocean: Till the End of Time;Burnout 3: Takedown;Jak 3;NCAA Football 07;Tom Clancy's Ghost Recon;Soulcalibur II;Shrek 2;Midnight Club II;
NCAA Football 2004;NBA Live 06;NFL Blitz Pro;Shadow the Hedgehog;Dirge of Cerberus: Final Fantasy VII;Madden NFL 2001;Scarface: The World Is Yours;Pac-Man World 2;Dark Cloud;NBA Live 2003;
ESPN NBA 2K5;Scooby-Doo! Night of 100 Frights;Tom Clancy's Splinter Cell;Jissen Pachi-Slot Hisshoho! Hokuto no Ken;MVP Baseball 2005;Twisted Metal: Black;Fight Night 2004;
Midnight Club 3: DUB Edition;DDRMAX2 Dance Dance Revolution 7thMix;SpyHunter;Naruto: Ultimate Ninja 2;Harry Potter and the Chamber of Secrets;The Incredibles;MVP Baseball 2004;
Disney•Pixar Cars;Dead or Alive 2;Guitar Hero Encore: Rocks the 80s;NCAA Football 2003;Silent Hill 2;Sly Cooper and the Thievius Raccoonus;Xenosaga Episode I: Der Wille zur Macht"""
BEST_SELLING_PLAYSTATION_3_GAMES = """Grand Theft Auto V;Gran Turismo 5;Grand Theft Auto IV;The Last of Us;Uncharted 3: Drake's Deception;Uncharted 2: Among Thieves;Metal Gear Solid 4: Guns of the Patriots;Batman: Arkham City;
Gran Turismo 5 Prologue;Gran Turismo 6;God of War III;Final Fantasy XIII;Uncharted: Drake's Fortune;Call of Duty: Modern Warfare 2;LittleBigPlanet;Batman: Arkham Asylum;MotorStorm;
Call of Duty: Black Ops;Heavy Rain;God of War: Ascension;Resistance 2;Beyond: Two Souls;Resistance: Fall of Man;God of War Collection;Batman: Arkham Origins;
Lego Star Wars: The Complete Saga;inFAMOUS;Killzone 2;Mortal Kombat vs. DC Universe;Dark Souls;Call of Duty 4: Modern Warfare;Call of Duty: World at War;Demon's Souls;L.A. Noire;
Resident Evil 5;Heavenly Sword;Minecraft: PlayStation 3 Edition;Metal Gear Rising: Revengeance;Pro Evolution Soccer 2008;Red Dead Redemption;Ratchet & Clank Future: Tools of Destruction;
One Piece: Pirate Warriors;Dark Souls II;Ni no Kuni: Wrath of the White Witch;FIFA 11;FIFA 12;FIFA 13;MotorStorm: Pacific Rift;Valkyria Chronicles"""
BEST_SELLING_SUPER_NINTENDO_ENTERTAINMENT_SYSTEM_GAMES = """Super Mario World;Super Mario All-Stars;Donkey Kong Country;Super Mario Kart;Street Fighter II: The World Warrior;Donkey Kong Country 2: Diddy's Kong Quest;
The Legend of Zelda: A Link to the Past;Super Mario World 2: Yoshi's Island;Street Fighter II Turbo;Star Fox;Donkey Kong Country 3: Dixie Kong's Double Trouble!;Final Fantasy VI;
Killer Instinct;Dragon Quest VI;F-Zero;Dragon Quest V;Chrono Trigger;Final Fantasy V;Mario Paint;Super Mario RPG;Pilotwings;Super Street Fighter II;SimCity;Secret of Mana;Final Fantasy IV;
Disney's Aladdin;Super Puyo Puyo;Super Scope 6;Mortal Kombat II;Romancing SaGa 2;Final Fight;Dragon Ball Z: Super Butōden;Kirby Super Star;Super Metroid;Dragon Quest III;Romancing SaGa;
Wonder Project J;Romancing SaGa 3;The Lion King;NBA Jam;Mortal Kombat 3;The Magical Quest Starring Mickey Mouse;Dragon Quest I & II;Ken Griffey Jr. Presents Major League Baseball;
Derby Stallion;Mega Man X;Dragon Ball Z: Super Butōden 2;Super Ghouls 'n Ghosts;Final Fight 2;Super Tetris 2 + Bombliss;Tetris 2;Space Invaders: The Original Game;Super Star Wars;
Super Bomberman 2"""
BEST_SELLING_WII_GAMES = """Wii Sports;Mario Kart Wii;Wii Sports Resort;New Super Mario Bros. Wii;Wii Play;Wii Fit;Wii Fit Plus;Super Smash Bros. Brawl;Super Mario Galaxy;Just Dance 3;Wii Party;Mario Party 8;
The Legend of Zelda: Twilight Princess;Super Mario Galaxy 2;Mario & Sonic at the Olympic Games;Donkey Kong Country Returns;Mario & Sonic at the Olympic Winter Games;Link's Crossbow Training;
Lego Star Wars: The Complete Saga;Just Dance 2;Animal Crossing: City Folk;Just Dance;Super Paper Mario;The Legend of Zelda: Skyward Sword;Big Brain Academy: Wii Degree;Mario Party 9;
Wii Music;Mario Strikers Charged;Mario & Sonic at the London 2012 Olympic Games;WarioWare: Smooth Moves;Mario Super Sluggers;Super Mario All-Stars: 25th Anniversary Edition;
Guitar Hero III: Legends of Rock;Michael Jackson: The Experience;Resident Evil 4: Wii Edition;Deca Sports;Epic Mickey;Game Party;Mario Sports Mix;Pokémon Battle Revolution;
Kirby's Return to Dream Land;Monster Hunter Tri;Kirby's Epic Yarn;EA Sports Active;New Play Control! Mario Power Tennis;Wii Play: Motion;Carnival Games;Metroid Prime 3: Corruption;
Guitar Hero World Tour;Resident Evil: The Umbrella Chronicles;PokéPark Wii: Pikachu's Adventure;Sonic and the Secret Rings;Rayman Raving Rabbids;We Ski;Big Beach Sports;Punch-Out!!;
Wario Land: Shake It!;Active Life: Outdoor Challenge;Call of Duty: World at War;Red Steel;Rock Band;Zumba Fitness;Super Mario Bros. 3;Game Party 2"""
BEST_SELLING_WII_U_GAMES = """Mario Kart 8;Super Mario 3D World;New Super Mario Bros. U;Super Smash Bros. for Wii U;Nintendo Land;Splatoon;Super Mario Maker;New Super Luigi U;The Legend of Zelda: The Wind Waker HD;
Mario Party 10;Donkey Kong Country: Tropical Freeze;Wii Party U;The Legend of Zelda: Breath of the Wild;Yoshi's Woolly World;Captain Toad: Treasure Tracker;Pikmin 3;
The Legend of Zelda: Twilight Princess HD;Lego City Undercover;Hyrule Warriors;Pokkén Tournament"""
BEST_SELLING_XBOX_360_GAMES = """Kinect Adventures!;Grand Theft Auto V;Minecraft: Xbox 360 Edition;Call of Duty: Modern Warfare 3;Call of Duty: Black Ops;Halo 3;Call of Duty: Black Ops II;The Elder Scrolls V: Skyrim;
Call of Duty: Modern Warfare 2;Red Dead Redemption;Grand Theft Auto IV;Call of Duty: Ghosts;Halo: Reach;Call of Duty 4: Modern Warfare;Gears of War;Gears of War 2;Batman: Arkham City;
Fable II;Batman: Arkham Asylum;Call of Duty: World at War;Gears of War 3;Left 4 Dead 2;Halo 3: ODST;Kinect Sports;Assassin's Creed II;Star Wars: The Force Unleashed;Assassin's Creed;
Dance Central;Lego Star Wars: The Complete Saga;L.A. Noire;Marvel: Ultimate Alliance;Uno;Final Fantasy XIII;Guitar Hero II;Saints Row;Trials HD;The Elder Scrolls IV: Oblivion;Madden NFL 09;
Dead Rising;Rock Band;Madden NFL 07;Lost Planet: Extreme Condition;Guitar Hero III: Legends of Rock;Mass Effect;Mass Effect 2;Tom Clancy's Rainbow Six: Vegas;Call of Duty 3;Madden NFL 08;
Fallout 3;BioShock;Crackdown;Perfect Dark Zero;Resident Evil 5;Tom Clancy's Ghost Recon Advanced Warfighter;Call of Duty 2;Fight Night Round 3;UFC 2009 Undisputed;Dead or Alive 4;
Guitar Hero World Tour;Tom Clancy's Rainbow Six: Vegas 2;Battlefield: Bad Company 2;Rock Band 2;Gears of War: Judgement;FIFA 11;FIFA 12;FIFA 13;FIFA 14;Halo Wars;Left 4 Dead;Ninja Gaiden II;
The Orange Box;Tom Clancy's Ghost Recon Advanced Warfighter 2;Viva Piñata;Trials Evolution"""
BEST_SELLING_XBOX_ONE_GAMES = """Grand Theft Auto V;Forza Horizon 4;PUBG: Battlegrounds;Call of Duty: Black Ops III;Call of Duty: WWII;Call of Duty: Advanced Warfare;Halo 5: Guardians;Call of Duty: Infinite Warfare;
The Witcher 3: Wild Hunt;Dead Rising 3;Minecraft: Xbox One Edition;Star Wars Battlefront;Cyberpunk 2077;Cuphead;Forza Horizon 3;Dragon Ball Xenoverse 2;Forza Motorsport 5;Dark Souls III;
Sunset Overdrive;Dead Rising 4;Dragon Ball FighterZ;Ark: Survival Evolved;Jump Force;Dark Souls II: Scholar of the First Sin;Dragon Ball Z: Kakarot;Tekken 7;Ryse: Son of Rome;
Dragon Ball Xenoverse;Naruto to Boruto: Shinobi Striker;FIFA 16;FIFA 17;Forza Motorsport 6;Rise of the Tomb Raider"""
HIGHEST_GROSSING_MEDIA_FRANCHISES = """Pokémon;Mickey Mouse & Friends;Winnie-the-Pooh;Star Wars;Disney Princess;Call of Duty;Anpanman;Marvel Cinematic Universe (MCU);Barbie;Wizarding World (Harry Potter);Hello Kitty;Batman;
Spider-Man;Transformers;Naruto;Dungeon Fighter Online (DFO);Cars;Candy Crush;Paw Patrol;Looney Tunes;Teenage Mutant Ninja Turtles;SpongeBob SquarePants;Toy Story;The Lion King;
Dora the Explorer;Pac-Man;Peanuts;Avengers;Frozen;Space Invaders;Warcraft;Despicable Me (Minions);Star Trek;Dragon Ball;Street Fighter;Grand Theft Auto (GTA);Demon Slayer: Kimetsu no Yaiba;
Jurassic Park;Rilakkuma;Monster Strike;James Bond;Mario;Angry Birds;The Railway Series / Thomas & Friends;Fortnite;Super Sentai / Power Rangers;Middle-earth (The Lord of the Rings);X-Men;
Superman;DC Extended Universe (DCEU);Fast & Furious;Lilo & Stitch (Stitch);Pirates of the Caribbean;Ben 10;Sesame Street (The Muppets);Ultra Series (Ultraman);Sonic the Hedgehog;Avatar;
Puzzle & Dragons;Madden NFL;Fate;Halo;Ice Age;Genshin Impact;Shrek;The Phantom of the Opera;My Little Pony;Scooby-Doo;Yu-Gi-Oh!;Mamma Mia;Mortal Kombat;Gundam;The Sims;Bob the Builder;
MapleStory;The Simpsons;Assassin's Creed;Mission: Impossible;Beyblade;The Big Bang Theory;Seinfeld;Minecraft;Twilight;Gran Turismo;Strawberry Shortcake;The Smurfs;Cabbage Patch Kids;
G.I. Joe;The Hunger Games;Blue's Clues;Beauty and the Beast;Skylanders;Titanic;Titanfall;Bratz;Fengshen Cinematic Universe;Care Bears;Hamtaro;Terminator;Astro Boy;Thor;
Zootopia (Zootropolis);Iron Man;Guardians of the Galaxy;Inside Out;The Elder Scrolls;Godzilla (Gojira);Indiana Jones;Madagascar;Captain America;Kung Fu Panda;Winx Club;The Powerpuff Girls;
Friends;Sailor Moon;The Incredibles;Kumamon;Aladdin;Black Panther;Planet of the Apes;Jumanji;The Little Mermaid;The Conjuring Universe;Ghostbusters;Finding Nemo;The Matrix;Rocky;
MonsterVerse;Yo-kai Watch;The Chronicles of Narnia;E.T. the Extra-Terrestrial;Robert Langdon;Bourne;Men in Black;Resident Evil (Biohazard);Guitar Hero;Lego;NBA Jam;Neon Genesis Evangelion;
Farm Heroes Saga"""
BEST_SELLING_MANGA = """One Piece;Doraemon;Golgo 13;Case Closed / Detective Conan;Dragon Ball;Naruto;Demon Slayer: Kimetsu no Yaiba;Slam Dunk;KochiKame: Tokyo Beat Cops;Jujutsu Kaisen;Crayon Shin-chan;
Attack on Titan;Oishinbo;Bleach;JoJo's Bizarre Adventure;Kingdom;Astro Boy;Baki the Grappler;Fist of the North Star;Hajime no Ippo;Hunter × Hunter;The Kindaichi Case Files;My Hero Academia;
Touch;Captain Tsubasa;Fullmetal Alchemist;Sazae-san;Kinnikuman;Vagabond;Sangokushi;Tokyo Revengers;Haikyu;Gintama;Fairy Tail;Rurouni Kenshin;Berserk;Major;Blue Lock;
That Time I Got Reincarnated as a Slime;Boys Over Flowers;Minami no Teiō;The Prince of Tennis;Rokudenashi Blues;The Apothecary Diaries;Initial D;Bad Boys;H2;Ranma ½;The Seven Deadly Sins;
Shura no Mon;Super Radical Gag Family;City Hunter;Cobra;Devilman;Dragon Quest: The Adventure of Dai;Fisherman Sanpei;Glass Mask;Great Teacher Onizuka;Inuyasha;Nana;Saint Seiya;Shoot!;
YuYu Hakusho;Dokaben;Black Jack;Kosaku Shima;Tokyo Ghoul;Crows;Sailor Moon;Shizukanaru Don – Yakuza Side Story;Ace of Diamond;Dear Boys;Shonan Junai Gumi;Yu-Gi-Oh!;The Promised Neverland;
Spy × Family;Shaman King;Be-Bop High School;Cooking Papa;Crest of the Royal Family;Kyō Kara Ore Wa;Nodame Cantabile;One-Punch Man;Black Butler;Chainsaw Man;Kimi ni Todoke;The Chef;
Chibi Maruko-chan;Frieren: Beyond Journey's End;Itazura na Kiss;Salary Man Kintaro;Space Brothers;Urusei Yatsura;Worst;Yowamushi Pedal;3×3 Eyes;Kaze Densetsu: Bukkomi no Taku;
Hell Teacher: Jigoku Sensei Nube;The Silent Service;A Certain Magical Index;Kuroko's Basketball;Bastard;Chameleon;Death Note;Dr. Slump;The Fable;Fruits Basket;Golden Kamuy;Jarinko Chie;
Jingi;Kaiji;Pokémon Adventures;Reborn!;Tokimeki Tonight;Toriko;Ushio & Tora;Yawara!;Futari Ecchi;Chihayafuru;Shonan Bakusozoku;Asari-chan;Assassination Classroom;D.Gray-man;Eyeshield 21;
Sakigake;Seito Shokun!;Yūkan Club;20th Century Boys;Aoashi;Bari Bari Densetsu;Tsuribaka Nisshi;Angel Heart;Ashita no Joe;Black Clover;Blue Exorcist;Boys Be...;Flame of Recca;Fushigi Yûgi;
Hikaru no Go;Magi: The Labyrinth of Magic;Maison Ikkoku;Miyuki;Neon Genesis Evangelion;Oh My Goddess!;Oshi no Ko;Patalliro!;Parasyte;The Ping Pong Club;Saiyuki;Ahiru no Sora;Gantz;
Kaguya-sama: Love Is War;Zatch Bell!;Rave Master;Giant Killing;The Rose of Versailles;Ushijima the Loan Shark;Abu-san;Cardcaptor Sakura;Don't Call It Mystery;Hayate the Combat Butler;
Hoshin Engi;Made in Abyss;Swan;Terra Formars;Dōbutsu no Oisha-san;Osu! Karate Club;Rookies;Tsubasa: Reservoir Chronicle;Dragon Quest: The Mark of Erdick;Soul Eater;750 Rider;Buddha;
Cat's Eye;Dr. Stone;Fire Force;Food Wars!: Shokugeki no Soma;Haruhi Suzumiya;Kaiju No. 8;Keiji;Kimagure Orange Road;Love Hina;Master Keaton;Mazinger Z;Monster;Negima! Magister Negi Magi;
Peacock King;The Quintessential Quintuplets;Record of Ragnarok;Red River;Shōnen Ashibe;Sukeban Deka;Tokyo Daigaku Monogatari;Weed;Welcome to Demon School! Iruma-kun"""
BEST_SELLING_BOOK_SERIES = """Harry Potter;Goosebumps;Perry Mason;Diary of a Wimpy Kid;Choose Your Own Adventure;Berenstain Bears;Mr. Men and Little Miss;Sweet Valley High;Noddy;Jack Reacher;
The Railway Series and Thomas & Friends;Nancy Drew;San-Antonio;Robert Langdon;Geronimo Stilton;Percy Jackson & the Olympians;The Baby-sitters Club;American Girl;Twilight;Star Wars;
Little Critter;Peter Rabbit;Fifty Shades;Chicken Soup for the Soul;Clifford the Big Red Dog;Frank Merriwell;Dirk Pitt;宮本武蔵 (Musashi);The Chronicles of Narnia;SAS;A Song of Ice and Fire;
The Hunger Games;James Bond;Martine;Millennium;The Wheel of Time;Discworld;Nijntje (Miffy);Alex Cross;Anpanman (アンパンマン);Captain Underpants;Fear Street;Pippi Långstrump (Pippi Longstocking);
The Vampire Chronicles;OSS 117;Winnie-the-Pooh;Magic Tree House series;Left Behind;A Series of Unfortunate Events;Arthur;Little House on the Prairie;All Creatures Great and Small;
The Magic School Bus;Where's Wally?;Men Are from Mars, Women Are from Venus;The Hardy Boys;The Bobbsey Twins;Tarzan;The Shadowhunter Chronicles;Earth's Children;
A Child's First Library of Learning;Junie B. Jones;Harry Bosch;Harry Hole;Warriors;连环画 铁道游击队 (Picture-and-story book Railway Guerilla);かいけつゾロリ (Kaiketsu Zorori);Paddington Bear;Animorphs;
Divergent trilogy;ノンタン (Nontan);グイン・サーガ (Guin Saga);The Inheritance Cycle;Rich Dad, Poor Dad;とある魔術の禁書目録 (Toaru Majutsu no Index);(Tokugawa Ieyasu);Ramona;The Dark Tower;Dork Diaries;
The Destroyer;The Ramses Saga;地球往事 (Remembrance of Earth's Past);(Calico Cat Holmes series);Curious George;Shannara;Kurt Wallander;Sagan om Isfolket (The Legend of the Ice People);
The Sword of Truth;Outlander;(Zukkoke Sanningumi);鬼平犯科帳 (Onihei Hankachō);Brain Quest;South Beach Diet;His Dark Materials;ソードアート・オンライン (Sword Art Online);竜馬がゆく (Ryoma ga Yuku);Artemis Fowl;
The Cosmere;Dune series;I Survived;Découvertes Gallimard;Redwall;Maisy;Dragonlance;幻魔大戦 (Genma Taisen);青春の門 (The Gate of Youth);スレイヤーズ (Slayers);The Foundation Trilogy;Horrible Histories;
Rainbow Magic;Morgan Kane;The Southern Vampire Mysteries;Doc Savage;涼宮ハルヒシリーズ (Haruhi Suzumiya Series);一億人の昭和史 (1-oku nin no Shōwa shi / Shōwa History of 100 million people);
科学のアルバム (Kagaku no album / Science's Album);剣客商売 (Kenkaku Shōbai);Erast Fandorin series;Dragonriders of Pern;吸血鬼ハンターD (Vampire Hunter D);The Hitchhiker's Guide to the Galaxy;(Bokura series);
Bridget Jones;銀河英雄伝説 (Legend of the Galactic Heroes);The No. 1 Ladies Detective Agency;Der Regenbogenfisch (Rainbow Fish);The Riftwar Cycle;The Thrawn trilogy;Wiedźmin (The Witcher);
(The family of fourteen)"""
EMMY_OUTSTANDING_DRAMA_SERIES_NOMINEES = """Pulitzer Prize Playhouse;Fireside Theatre;Mama;The Philco Television Playhouse;Studio One;Celanese Theatre;Robert Montgomery Presents;Kraft Television Theatre;Dragnet;The Big Story;
Foreign Intrigue;Martin Kane, Private Eye;Racket Squad;The United States Steel Hour;I Led 3 Lives;Suspense;The Web;Four Star Playhouse;Medic;Waterfront;Stories of the Century;
The Adventures of Wild Bill Hickok;Annie Oakley;Death Valley Days;The Roy Rogers Show;Producers' Showcase;Alcoa Theatre;Climax!;Walt Disney anthology television series;
Alfred Hitchcock Presents;Gunsmoke;The Lineup;The Phil Silvers Show;Father Knows Best;The Jack Benny Program;Person to Person;Caesar's Hour;The Ed Sullivan Show;Omnibus;Lassie;Maverick;
Perry Mason;Wagon Train;Playhouse 90;Hallmark Hall of Fame;General Electric Theater;The Loretta Young Show;Naked City;Peter Gunn;Have Gun – Will Travel;The Rifleman;DuPont Show of the Month;
The Moon and Sixpence;Startime;The Untouchables;Sacco-Vanzetti Story;The Twilight Zone;The Defenders;Alcoa Premiere;Ben Casey;The Dick Powell Show;The Eleventh Hour;
Bob Hope Presents the Chrysler Theatre;East Side/West Side;Mr. Novak;The Richard Boone Show;The Dick Van Dyke Show;My Name Is Barbra;Young People's Concerts;The Andy Williams Show;
A Carol for Another Christmas;The Man from U.N.C.L.E.;Profiles in Courage;Who Has Seen the Wind?;The Fugitive;Bonanza;I Spy;Slattery's People;Mission: Impossible;The Avengers;
Run for Your Life;Star Trek: The Original Series;NET Playhouse;The F.B.I.;Ironside;Judd, for the Defense;The Name of the Game;Marcus Welby, M.D.;The Forsyte Saga;The Mod Squad;
The Bold Ones: The Senator;The First Churchills;Masterpiece;Elizabeth R;Columbo;The NBC Mystery Movie;Mannix;The Six Wives of Henry VIII;The Waltons;Cannon;Hawaii Five-O;Kung Fu;
Upstairs, Downstairs;Kojak;Police Story;The Streets of San Francisco;Baretta;Family;The Rockford Files;Lou Grant;Quincy, M.E.;The Paper Chase;Dallas;The White Shadow;Hill Street Blues;
Dynasty;Fame;Magnum, P.I.;Cagney & Lacey;St. Elsewhere;Miami Vice;Murder, She Wrote;Moonlighting;L.A. Law;thirtysomething;Beauty and the Beast;Rumpole of the Bailey;China Beach;Wiseguy;
Quantum Leap;Twin Peaks;Northern Exposure;I'll Fly Away;Law & Order;Picket Fences;Homefront;NYPD Blue;Star Trek: The Next Generation;Chicago Hope;ER;The X-Files;The Practice;The Sopranos;
The West Wing;CSI: Crime Scene Investigation;Six Feet Under;Joan of Arcadia;Lost;Deadwood;Grey's Anatomy;House;Boston Legal;Heroes;Mad Men;Damages;Dexter;Big Love;Breaking Bad;The Good Wife;
True Blood;Boardwalk Empire;Friday Night Lights;Game of Thrones;Homeland;Downton Abbey;House of Cards;True Detective;Better Call Saul;Orange Is the New Black;The Americans;Mr. Robot;
The Handmaid's Tale;The Crown;Stranger Things;This Is Us;Westworld;Bodyguard;Killing Eve;Ozark;Pose;Succession;The Mandalorian;The Boys;Bridgerton;Lovecraft Country;Euphoria;Severance;
Squid Game;Yellowjackets;Andor;House of the Dragon;The Last of Us;The White Lotus;Shōgun;Fallout;The Gilded Age;The Morning Show;Mr. & Mrs. Smith;Slow Horses;3 Body Problem;The Pitt;
The Diplomat;Paradise;A Knight of the Seven Kingdoms;Pluribus;Your Friends & Neighbors"""
EMMY_OUTSTANDING_COMEDY_SERIES_NOMINEES = """The Red Skelton Show;The George Burns and Gracie Allen Show;The Herb Shriner Show;I Love Lucy;You Bet Your Life;The Adventures of Ozzie and Harriet;Amos 'n' Andy;Mister Peepers;
Our Miss Brooks;Topper;The Danny Thomas Show;Private Secretary;The Phil Silvers Show;The Bob Cummings Show;Caesar's Hour;The Jack Benny Program;Alfred Hitchcock Presents;Father Knows Best;
Person to Person;Climax!;The Ed Sullivan Show;Omnibus;The Art Carney Special;The Andy Griffith Show;Candid Camera;The Flintstones;The Bob Newhart Show;Car 54, Where Are You?;Hazel;
The Dick Van Dyke Show;The Beverly Hillbillies;The Danny Kaye Show;McHale's Navy;The Bill Dana Show;The Farmer's Daughter (TV series);That Was the Week That Was;Hallmark Hall of Fame;
My Name Is Barbra;Young People's Concerts;The Andy Williams Show;Bob Hope Presents the Chrysler Theatre;A Carol for Another Christmas;The Defenders;The Man from U.N.C.L.E.;Mr. Novak;
Profiles in Courage;Walt Disney anthology television series;Who Has Seen the Wind?;Batman;Bewitched;Get Smart;Hogan's Heroes;The Monkees;Family Affair;The Lucy Show;Julia;
The Ghost & Mrs. Muir;My World and Welcome to It;The Bill Cosby Show;The Courtship of Eddie's Father;Love, American Style;Room 222;All in the Family;Arnie;The Mary Tyler Moore Show;
The Odd Couple;Sanford and Son;M*A*S*H;Maude;Rhoda;Barney Miller;Welcome Back, Kotter;Soap;Three's Company;Taxi;Mork & Mindy;WKRP in Cincinnati;Love, Sidney;Cheers;Buffalo Bill;Newhart;
Family Ties;Kate & Allie;The Cosby Show;Night Court;The Golden Girls;The Wonder Years;Frank's Place;Designing Women;Murphy Brown;Brooklyn Bridge;Home Improvement;Seinfeld;
The Larry Sanders Show;Frasier;Mad About You;Friends;3rd Rock from the Sun;Ally McBeal;Everybody Loves Raymond;Sex and the City;Will & Grace;Malcolm in the Middle;Curb Your Enthusiasm;
Arrested Development;Desperate Housewives;Scrubs;The Office;Two and a Half Men;30 Rock;Entourage;Ugly Betty;Family Guy;Flight of the Conchords;How I Met Your Mother;Weeds;Modern Family;Glee;
Nurse Jackie;The Big Bang Theory;Parks and Recreation;Girls;Veep;Louie;Orange Is the New Black;Silicon Valley;Transparent;Unbreakable Kimmy Schmidt;Black-ish;Master of None;Atlanta;
The Marvelous Mrs. Maisel;Barry;GLOW;Fleabag;The Good Place;Russian Doll;Schitt's Creek;Dead to Me;Insecure;The Kominsky Method;What We Do in the Shadows;Ted Lasso;Cobra Kai;Emily in Paris;
The Flight Attendant;Hacks;Pen15;Abbott Elementary;Only Murders in the Building;The Bear;Jury Duty;Wednesday;Palm Royale;Reservation Dogs;The Studio;Nobody Wants This;Shrinking;Widow's Bay;
Margo's Got Money Troubles"""
CRUNCHYROLL_ANIME_OF_THE_YEAR_NOMINEES = """Yuri on Ice;Descending Stories: Showa Genroku Rakugo Shinju;Erased (manga);Joker Game;Kabaneri of the Iron Fortress;Mob Psycho 100;My Hero Academia;Re:Zero;Made in Abyss;
Land of the Lustrous;Little Witch Academia;March Comes In like a Lion;Devilman Crybaby;A Place Further than the Universe;Hinamatsuri (manga);Megalo Box;Violet Evergarden;Zombie Land Saga;
Demon Slayer: Kimetsu no Yaiba;Carole & Tuesday;O Maidens in Your Savage Season;The Promised Neverland;Vinland Saga;Jujutsu Kaisen;Appare-Ranman!;Beastars;Dorohedoro;Great Pretender;
Keep Your Hands Off Eizouken!;Attack on Titan;Odd Taxi;Ranking of Kings;Sonny Boy;Cyberpunk: Edgerunners;Lycoris Recoil;Spy × Family;Bocchi the Rock!;Chainsaw Man;Oshi no Ko;Solo Leveling;
Dandadan;Delicious in Dungeon;Frieren;Kaiju No. 8;The Apothecary Diaries;Gachiakuta;Takopi's Original Sin;The Summer Hikaru Died;Unwavering Resolve Arc;Entertainment District Arc;
Swordsmith Village Arc"""
BEST_SELLING_MUSIC_ARTISTS = """The Beatles;Michael Jackson;Elvis Presley;Madonna;Elton John;Queen;Led Zeppelin;Rihanna;Pink Floyd;Eminem;Mariah Carey;Whitney Houston;Taylor Swift;Beyoncé;Ed Sheeran;AC/DC;Eagles;
Celine Dion;The Rolling Stones;Drake;Coldplay;Garth Brooks;U2;Kanye West;Billy Joel;Katy Perry;Justin Bieber;Bruno Mars;Britney Spears;Metallica;Bruce Springsteen;Aerosmith;Phil Collins;
Barbra Streisand;ABBA;Julio Iglesias;Frank Sinatra;Chris Brown;Jay-Z;Lady Gaga;Lil Wayne;Maroon 5;Adele;Red Hot Chili Peppers;Bon Jovi;Fleetwood Mac;Rod Stewart;Bee Gees;Dire Straits;
Roberto Carlos;Nicki Minaj;Linkin Park;George Strait;Journey;Pink;Guns N' Roses;Christina Aguilera;Shania Twain;B'z;Backstreet Boys;Eric Clapton;Neil Diamond;Prince;Paul McCartney;
Janet Jackson;Kenny Rogers;The Doors;Santana;Simon & Garfunkel;The Beach Boys;George Michael;Foreigner;Bob Dylan;Chicago;Cher;Meat Loaf;The Carpenters;Earth, Wind & Fire;David Bowie;
Def Leppard;Stevie Wonder;Genesis;Gloria Estefan;Tina Turner;Mötley Crüe;James Taylor;Olivia Newton-John;Linda Ronstadt;Donna Summer;Diana Ross;The Supremes;Shakira;Ariana Grande;
Alicia Keys;Tim McGraw;Lionel Richie;Andrea Bocelli;Johnny Cash;Justin Timberlake;Pearl Jam;R.E.M.;Kelly Clarkson;Post Malone;Flo Rida;Usher;The Black Eyed Peas;Van Halen;Ayumi Hamasaki;
Tom Petty;Johnny Hallyday;The Weeknd;Imagine Dragons;Luke Bryan;Tupac Shakur;Nirvana;Oasis;Green Day;Alabama;R. Kelly;Robbie Williams;Bob Seger;Kenny G;Enya;Bryan Adams;Bob Marley;
The Police;Barry Manilow;Kiss;Aretha Franklin"""
MOST_STREAMED_SPOTIFY_ARTISTS = """Bruno Mars;Rihanna;The Weeknd;Justin Bieber;Lady Gaga;Taylor Swift;Drake;Ariana Grande;Michael Jackson;Coldplay;Bad Bunny;Shakira;Katy Perry;David Guetta;Billie Eilish;Maroon 5;Ed Sheeran;
Pitbull;Lana Del Rey;Olivia Rodrigo;Dua Lipa;Eminem;Calvin Harris;SZA;Kanye West;J Balvin;Karol G;Sia;Kendrick Lamar;Daddy Yankee;Tame Impala;Black Eyed Peas;Harry Styles;Beyoncé;
Post Malone;Travis Scott;Adele;Miley Cyrus;Justin Timberlake;Sean Paul;Doja Cat;Arctic Monkeys;Shreya Ghoshal;Linkin Park;Chris Brown;Shawn Mendes;Sombr;Alicia Keys;Halsey;Britney Spears;
Arijit Singh;BTS;A.R. Rahman;Pritam;Blackpink;Imagine Dragons;Queen;XXXTentacion;Selena Gomez;Anirudh Ravichander;Sidhu Moose Wala;Anuel AA;Neha Kakkar;Atif Aslam;Juice Wrld;
Yo Yo Honey Singh;Diljit Dosanjh;Alan Walker;One Direction;Ozuna;Maluma;Marília Mendonça"""
BEST_SELLING_FICTION_AUTHORS = """William Shakespeare;Agatha Christie;Barbara Cartland;Danielle Steel;Harold Robbins;Georges Simenon;J. K. Rowling;Eiichiro Oda;Enid Blyton;Jackie Collins;Sidney Sheldon;Rick Riordan;
Gilbert Patten;Dr. Seuss;Akira Toriyama;Leo Tolstoy;Corín Tellado;James Patterson;Dean Koontz;Stephen King;Horatio Alger;Nora Roberts;R. L. Stine;Alexander Pushkin;Paulo Coelho;Jirō Akagawa;
Jeffrey Archer;Louis L'Amour;René Goscinny;Erle Stanley Gardner;Edgar Wallace;Janet Dailey;Jin Yong;Robert Ludlum;Takehiko Inoue;Osamu Tezuka;Frédéric Dard;Stan and Jan Berenstain;
Roald Dahl;Zane Grey;Irving Wallace;Masashi Kishimoto;Gosho Aoyama;J. R. R. Tolkien;John Grisham;Karl May;Mickey Spillane;C. S. Lewis;Kyotaro Nishimura;Mitsuru Adachi;Rumiko Takahashi;
Dan Brown;Alistair MacLean;Ann M. Martin;Ryōtarō Shiba;Arthur Hailey;Keigo Higashino;Astrid Lindgren;Koyoharu Gotouge;Anne Rice;Gérard de Villiers;Beatrix Potter;Michael Crichton;
Richard Scarry;Clive Cussler;Ken Follett;Debbie Macomber;Naoki Urasawa;E.L. James;Carter Brown;Tite Kubo;Eiji Yoshikawa;Hajime Isayama;Catherine Cookson;Stephenie Meyer;Norman Bridwell;
David Baldacci;Nicholas Sparks;Hirohiko Araki;Tom Clancy;Andrew Neiderman;Evan Hunter;Roger Hargreaves;Robin Cook;Wilbur Smith;Erskine Caldwell;Judith Krantz;Eleanor Hibbert;Lewis Carroll;
Hiroshi Motomiya;Denise Robins;Cao Xueqin;Ian Fleming;Hermann Hesse;Rex Stout;Anne Golon;Frank G. Slaughter;Edgar Rice Burroughs;John Creasey;James A. Michener;Yasuo Uchida;Seiichi Morimura;
Mary Higgins Clark;Penny Jordan;Patricia Cornwell"""
MOST_SUBSCRIBED_YOUTUBE_CHANNELS = """MrBeast;T-Series;Cocomelon - Nursery Rhymes;SET India;Vlad and Niki;Stokes Twins;Kids Diana Show;김프로KIMPRO;Like Nastya;Alejo Igoa;Zee Music Company;WWE;Goldmines;PewDiePie;Sony SAB;
Alan's Universe;Blackpink;Zee TV;ChuChu TV Nursery Rhymes & Kids Songs;Topper Guild;A4;KL BRO Biju Rithvik;BANGTANTV;Mark Rober;Baby Shark - Pinkfong Kids’ Songs & Stories;
ZAMZAM BROTHERS OFFICIAL;UR · Cristiano;T-Series Bhakti Sagar;Hybe Labels;Toys and Colors;Tips Official;Colors TV;Zhong;Fede Vigevani;5-Minute Crafts;Justin Bieber;Bispo Bruno Leonardo;
Anaya Kandhal;Aaj Tak;ISSEI / いっせい;Shemaroo Filmi Gaane;HAR PAL GEO;Sony Music India;YRF;Infobells - Hindi;El Reino Infantil;YOLO AVENTURAS;Wave Music (Indian record label)|Wave Music;
ARY Digital HD;Canal KondZilla;Celine Dept;Eminem Music;Movieclips;Dangal TV Channel;Saregama Music;Taylor Swift;MrBeast 2;Dude Perfect;LooLoo Kids - Nursery Rhymes and Children's Songs;
Shemaroo;PANDA BOI;IShowSpeed;MrBeast Gaming;आचार्य प्रशान्त - Acharya Prashant;Alfredo Larin;SonyMusicIndiaVEVO;Ed Sheeran;ToRung;Marshmello;Billie Eilish;Mikecrack;JioHotstar Kids;
Ariana Grande;Billion Surprise Toys;Get Movies;JuegaGerman;shfa;StarPlus;Juan de Dios Pantoja;Masha and the Bear;HUM TV;ABS-CBN Entertainment;Natan por Aí;Sierra & Rhia FAM;Jess No Limit;
Shakira;shfa2 - شفا;T-Series Bollywood Classics;Ishtar Music;MR. INDIAN HACKER;Karla Bustillos;LUCCAS NETO;Techno Gamerz;Bad Bunny;Real fools shorts official;BEN EAGLE;BeatboxJCOP;
BETER BÖCÜK;Ben Azelart"""
MOST_FOLLOWED_TWITCH_CHANNELS = """KaiCenat;Ibai;Ninja;Auronplay;Rubius;xQc;EasyLiker;TheGrefg;
Juansguarnizo;Tfue;Shroud;Jynxzi;ElMariana;Edu90;ElSpreen;
Pokimane;Sodapoppin;caseoh_;Clix;Alanzoka;TimTheTatman;Riot Games;Myth;Tommyinnit;
SypherPK;Coringa;Mongraal;AriGameplays;Rivers_gg;AdinRoss;ESLCS;NICKMERCS;
Quackity;Summit1g;Fortnite;AMOURANTH;Dream;Moistcr1tikal;Its_j0schi;Robleis;
Squeezie;NickEh30;MontanaBlack88;Elded;Loltyler1;Bugha;IShowSpeed;
Tubbo;Buster;stableronaldo"""


ACADEMY_AWARD_BEST_ACTOR_NOMINEES = """Emil Jannings;Richard Barthelmess;Charlie Chaplin;Warner Baxter;George Bancroft;Chester Morris;Paul Muni;Lewis Stone;George Arliss;Wallace Beery;Maurice Chevalier;Ronald Colman;
Lawrence Tibbett;Lionel Barrymore;Jackie Cooper;Richard Dix;Fredric March;Adolphe Menjou;Alfred Lunt;Charles Laughton;Leslie Howard;Clark Gable;Frank Morgan;William Powell;Victor McLaglen;
Franchot Tone;Gary Cooper;Walter Huston;Spencer Tracy;Charles Boyer;Robert Montgomery;James Cagney;Robert Donat;Laurence Olivier;Mickey Rooney;James Stewart;Henry Fonda;Raymond Massey;
Cary Grant;Orson Welles;Walter Pidgeon;Monty Woolley;Paul Lukas;Humphrey Bogart;Bing Crosby;Barry Fitzgerald;Alexander Knox;Ray Milland;Gene Kelly;Gregory Peck;Cornel Wilde;Larry Parks;
John Garfield;Michael Redgrave;Lew Ayres;Montgomery Clift;Dan Dailey;Clifton Webb;Broderick Crawford;Kirk Douglas;Richard Todd;John Wayne;José Ferrer;Louis Calhern;William Holden;
Marlon Brando;Arthur Kennedy;Alec Guinness;Richard Burton;Burt Lancaster;James Mason;Dan O'Herlihy;Ernest Borgnine;James Dean;Frank Sinatra;Yul Brynner;Rock Hudson;Anthony Franciosa;
Anthony Quinn;David Niven;Tony Curtis;Paul Newman;Sidney Poitier;Charlton Heston;Laurence Harvey;Jack Lemmon;Trevor Howard;Maximilian Schell;Stuart Whitman;Marcello Mastroianni;
Peter O'Toole;Albert Finney;Richard Harris;Rex Harrison;Peter Sellers;Lee Marvin;Rod Steiger;Oskar Werner;Paul Scofield;Alan Arkin;Michael Caine;Steve McQueen;Warren Beatty;Dustin Hoffman;
Cliff Robertson;Alan Bates;Ron Moody;Jon Voight;George C. Scott;Melvyn Douglas;James Earl Jones;Jack Nicholson;Ryan O'Neal;Gene Hackman;Peter Finch;Walter Matthau;Paul Winfield;Al Pacino;
Robert Redford;Art Carney;James Whitmore;Robert De Niro;Giancarlo Giannini;Sylvester Stallone;Richard Dreyfuss;Woody Allen;John Travolta;Gary Busey;Roy Scheider;Robert Duvall;John Hurt;
Dudley Moore;Ben Kingsley;Tom Conti;Tom Courtenay;F. Murray Abraham;Jeff Bridges;Tom Hulce;Sam Waterston;William Hurt;Harrison Ford;James Garner;Dexter Gordon;Bob Hoskins;James Woods;
Michael Douglas;Robin Williams;Tom Hanks;Edward James Olmos;Max von Sydow;Daniel Day-Lewis;Kenneth Branagh;Tom Cruise;Morgan Freeman;Jeremy Irons;Kevin Costner;Gérard Depardieu;
Anthony Hopkins;Nick Nolte;Robert Downey Jr.;Clint Eastwood;Stephen Rea;Denzel Washington;Laurence Fishburne;Liam Neeson;Nigel Hawthorne;Nicolas Cage;Sean Penn;Massimo Troisi;Geoffrey Rush;
Ralph Fiennes;Woody Harrelson;Billy Bob Thornton;Matt Damon;Peter Fonda;Roberto Benigni;Ian McKellen;Edward Norton;Kevin Spacey;Russell Crowe;Richard Farnsworth;Javier Bardem;Ed Harris;
Will Smith;Tom Wilkinson;Adrien Brody;Johnny Depp;Jude Law;Bill Murray;Jamie Foxx;Don Cheadle;Leonardo DiCaprio;Philip Seymour Hoffman;Terrence Howard;Heath Ledger;Joaquin Phoenix;
David Strathairn;Forest Whitaker;Ryan Gosling;George Clooney;Tommy Lee Jones;Viggo Mortensen;Richard Jenkins;Frank Langella;Brad Pitt;Mickey Rourke;Colin Firth;Jeremy Renner;Jesse Eisenberg;
James Franco;Jean Dujardin;Demián Bichir;Gary Oldman;Bradley Cooper;Hugh Jackman;Matthew McConaughey;Christian Bale;Bruce Dern;Chiwetel Ejiofor;Eddie Redmayne;Steve Carell;
Benedict Cumberbatch;Michael Keaton;Bryan Cranston;Michael Fassbender;Casey Affleck;Andrew Garfield;Timothée Chalamet;Daniel Kaluuya;Rami Malek;Willem Dafoe;Antonio Banderas;Adam Driver;
Jonathan Pryce;Riz Ahmed;Chadwick Boseman;Steven Yeun;Brendan Fraser;Austin Butler;Colin Farrell;Paul Mescal;Bill Nighy;Cillian Murphy;Colman Domingo;Paul Giamatti;Jeffrey Wright;
Sebastian Stan;Michael B. Jordan;Ethan Hawke;Wagner Moura"""
ACADEMY_AWARD_BEST_ACTRESS_NOMINEES = """Janet Gaynor;Louise Dresser;Gloria Swanson;Mary Pickford;Ruth Chatterton;Betty Compson;Jeanne Eagels;Corinne Griffith;Bessie Love;Norma Shearer;Nancy Carroll;Greta Garbo;Marie Dressler;
Marlene Dietrich;Irene Dunne;Ann Harding;Helen Hayes;Lynn Fontanne;Katharine Hepburn;May Robson;Diana Wynyard;Claudette Colbert;Bette Davis;Grace Moore;Elisabeth Bergner;Miriam Hopkins;
Merle Oberon;Luise Rainer;Gladys George;Carole Lombard;Barbara Stanwyck;Fay Bainter;Wendy Hiller;Margaret Sullavan;Vivien Leigh;Greer Garson;Ginger Rogers;Joan Fontaine;Martha Scott;
Olivia de Havilland;Rosalind Russell;Teresa Wright;Jennifer Jones;Jean Arthur;Ingrid Bergman;Joan Crawford;Gene Tierney;Celia Johnson;Jane Wyman;Loretta Young;Susan Hayward;Dorothy McGuire;
Jeanne Crain;Deborah Kerr;Judy Holliday;Anne Baxter;Eleanor Parker;Shelley Winters;Shirley Booth;Julie Harris;Audrey Hepburn;Leslie Caron;Ava Gardner;Maggie McNamara;Grace Kelly;
Dorothy Dandridge;Judy Garland;Anna Magnani;Carroll Baker;Nancy Kelly;Joanne Woodward;Elizabeth Taylor;Lana Turner;Shirley MacLaine;Simone Signoret;Doris Day;Melina Mercouri;Sophia Loren;
Piper Laurie;Geraldine Page;Natalie Wood;Anne Bancroft;Lee Remick;Patricia Neal;Rachel Roberts;Julie Andrews;Debbie Reynolds;Kim Stanley;Julie Christie;Samantha Eggar;Elizabeth Hartman;
Anouk Aimée;Ida Kamińska;Lynn Redgrave;Vanessa Redgrave;Faye Dunaway;Edith Evans;Barbra Streisand;Maggie Smith;Geneviève Bujold;Jane Fonda;Liza Minnelli;Jean Simmons;Glenda Jackson;
Jane Alexander;Ali MacGraw;Sarah Miles;Carrie Snodgress;Janet Suzman;Diana Ross;Cicely Tyson;Liv Ullmann;Ellen Burstyn;Marsha Mason;Diahann Carroll;Valerie Perrine;Gena Rowlands;
Louise Fletcher;Isabelle Adjani;Carol Kane;Marie-Christine Barrault;Talia Shire;Sissy Spacek;Diane Keaton;Jill Clayburgh;Sally Field;Bette Midler;Goldie Hawn;Mary Tyler Moore;Susan Sarandon;
Meryl Streep;Jessica Lange;Debra Winger;Julie Walters;Judy Davis;Whoopi Goldberg;Marlee Matlin;Kathleen Turner;Sigourney Weaver;Glenn Close;Holly Hunter;Sally Kirkland;Jodie Foster;
Melanie Griffith;Jessica Tandy;Pauline Collins;Michelle Pfeiffer;Kathy Bates;Anjelica Huston;Julia Roberts;Geena Davis;Laura Dern;Emma Thompson;Catherine Deneuve;Mary McDonnell;
Angela Bassett;Stockard Channing;Miranda Richardson;Winona Ryder;Elisabeth Shue;Sharon Stone;Frances McDormand;Brenda Blethyn;Kristin Scott Thomas;Emily Watson;Helen Hunt;
Helena Bonham Carter;Judi Dench;Kate Winslet;Gwyneth Paltrow;Cate Blanchett;Fernanda Montenegro;Hilary Swank;Annette Bening;Janet McTeer;Julianne Moore;Erin Brockovich;Joan Allen;
Juliette Binoche;Laura Linney;Halle Berry;Nicole Kidman;Renée Zellweger;Salma Hayek;Diane Lane;Charlize Theron;Keisha Castle-Hughes;Samantha Morton;Naomi Watts;Catalina Sandino Moreno;
Imelda Staunton;Reese Witherspoon;Felicity Huffman;Keira Knightley;Helen Mirren;Penélope Cruz;Marion Cotillard;Elliot Page;Anne Hathaway;Angelina Jolie;Melissa Leo;Sandra Bullock;
Carey Mulligan;Gabourey Sidibe;Natalie Portman;Jennifer Lawrence;Michelle Williams;Viola Davis;Rooney Mara;Jessica Chastain;Emmanuelle Riva;Quvenzhané Wallis;Amy Adams;Felicity Jones;
Rosamund Pike;Brie Larson;Charlotte Rampling;Saoirse Ronan;Emma Stone;Isabelle Huppert;Ruth Negga;Sally Hawkins;Margot Robbie;Olivia Colman;Yalitza Aparicio;Lady Gaga;Melissa McCarthy;
Cynthia Erivo;Scarlett Johansson;Andra Day;Vanessa Kirby;Kristen Stewart;Michelle Yeoh;Ana de Armas;Andrea Riseborough;Lily Gladstone;Sandra Hüller;Mikey Madison;Karla Sofía Gascón;
Demi Moore;Fernanda Torres;Jessie Buckley;Rose Byrne;Kate Hudson;Renate Reinsve"""
BALLON_DOR_PODIUM = """Stanley Matthews;Alfredo Di Stéfano;Raymond Kopa;Billy Wright;Duncan Edwards;Helmut Rahn;Just Fontaine;John Charles;Luis Suárez;Ferenc Puskás;Uwe Seeler;Omar Sívori;Johnny Haynes;
Josef Masopust;Eusébio;Karl-Heinz Schnellinger;Lev Yashin;Gianni Rivera;Jimmy Greaves;Denis Law;Amancio;Giacinto Facchetti;Bobby Charlton;Franz Beckenbauer;Flórián Albert;Jimmy Johnstone;
George Best;Dragan Džajić;Gigi Riva;Gerd Müller;Bobby Moore;Johan Cruyff;Sandro Mazzola;Günter Netzer;Dino Zoff;Kazimierz Deyna;Oleg Blokhin;Rob Rensenbrink;Ivo Viktor;Allan Simonsen;
Kevin Keegan;Michel Platini;Hans Krankl;Karl-Heinz Rummenigge;Ruud Krol;Bernd Schuster;Paul Breitner;Paolo Rossi;Alain Giresse;Zbigniew Boniek;Kenny Dalglish;Jean Tigana;Preben Elkjær;
Igor Belanov;Gary Lineker;Emilio Butragueño;Ruud Gullit;Paulo Futre;Marco van Basten;Frank Rijkaard;Franco Baresi;Lothar Matthäus;Salvatore Schillaci;Andreas Brehme;Jean-Pierre Papin;
Dejan Savićević;Darko Pančev;Hristo Stoichkov;Dennis Bergkamp;Roberto Baggio;Eric Cantona;Paolo Maldini;George Weah;Jürgen Klinsmann;Jari Litmanen;Matthias Sammer;Ronaldo;Alan Shearer;
Predrag Mijatović;Zinedine Zidane;Davor Šuker;Rivaldo;David Beckham;Andriy Shevchenko;Luís Figo;Michael Owen;Raúl;Oliver Kahn;Roberto Carlos;Pavel Nedvěd;Thierry Henry;Deco;Ronaldinho;
Frank Lampard;Steven Gerrard;Fabio Cannavaro;Gianluigi Buffon;Kaká;Cristiano Ronaldo;Lionel Messi;Fernando Torres;Xavi;Andrés Iniesta;Franck Ribéry;Manuel Neuer;Neymar;Antoine Griezmann;
Luka Modrić;Virgil van Dijk;Robert Lewandowski;Jorginho;Karim Benzema;Sadio Mané;Kevin De Bruyne;Erling Haaland;Kylian Mbappé;Rodri;Vinícius Júnior;Jude Bellingham;Ousmane Dembélé;
Lamine Yamal;Vitinha;Harry Kane"""
FORMULA_ONE_WORLD_CHAMPIONS = """Giuseppe Farina;Juan Manuel Fangio;Alberto Ascari;Mike Hawthorn;Jack Brabham;Phil Hill;Graham Hill;Jim Clark;John Surtees;Denny Hulme;Jackie Stewart;Jochen Rindt;Emerson Fittipaldi;
Niki Lauda;James Hunt;Mario Andretti;Jody Scheckter;Alan Jones;Nelson Piquet;Keke Rosberg;Alain Prost;Ayrton Senna;Nigel Mansell;Michael Schumacher;Damon Hill;Jacques Villeneuve;
Mika Häkkinen;Fernando Alonso;Kimi Räikkönen;Lewis Hamilton;Jenson Button;Sebastian Vettel;Nico Rosberg;Max Verstappen;Lando Norris;Kimi Antonelli"""
NBA_MVP_WINNERS = """Bob Pettit;Bob Cousy;Bill Russell;Wilt Chamberlain;Oscar Robertson;Wes Unseld;Willis Reed;Lew Alcindor;Kareem Abdul-Jabbar;Dave Cowens;Bob McAdoo;Bill Walton;Moses Malone;Julius Erving;
Larry Bird;Magic Johnson;Michael Jordan;Charles Barkley;Hakeem Olajuwon;David Robinson;Karl Malone;Shaquille O'Neal;Allen Iverson;Tim Duncan;Kevin Garnett;Steve Nash;Dirk Nowitzki;
Kobe Bryant;LeBron James;Derrick Rose;Kevin Durant;Stephen Curry;Russell Westbrook;James Harden;Giannis Antetokounmpo;Nikola Jokić;Joel Embiid;Shai Gilgeous-Alexander"""
LEXICONS = {"sports_team": (NFL_TEAMS_2025, NBA_TEAMS_2025, MLB_TEAMS_2025, NHL_TEAMS_2025, MLS_TEAMS_2025, PREMIER_LEAGUE_TEAMS_2025, LA_LIGA_TEAMS_2025, SERIE_A_TEAMS_2025,
                            BUNDESLIGA_TEAMS_2025, LIGUE_1_TEAMS_2025, IPL_TEAMS_2025),
            "video_game": (BEST_SELLING_GAME_BOY_GAMES, BEST_SELLING_GAME_BOY_ADVANCE_GAMES, BEST_SELLING_GAMECUBE_GAMES, BEST_SELLING_NINTENDO_3DS_GAMES,
                           BEST_SELLING_NINTENDO_64_GAMES, BEST_SELLING_NINTENDO_DS_GAMES, BEST_SELLING_PLAYSTATION_GAMES, BEST_SELLING_PLAYSTATION_2_GAMES,
                           BEST_SELLING_PLAYSTATION_3_GAMES, BEST_SELLING_SUPER_NINTENDO_ENTERTAINMENT_SYSTEM_GAMES, BEST_SELLING_WII_GAMES, BEST_SELLING_WII_U_GAMES,
                           BEST_SELLING_XBOX_360_GAMES, BEST_SELLING_XBOX_ONE_GAMES, BEST_SELLING_NINTENDO_SWITCH_GAMES, BEST_SELLING_PLAYSTATION_4_GAMES,
                           BEST_SELLING_PLAYSTATION_5_GAMES, BEST_SELLING_NINTENDO_GAMES, BEST_SELLING_VIDEO_GAMES, BEST_SELLING_VIDEO_GAME_FRANCHISES,
                           GAME_AWARDS_GAME_OF_THE_YEAR_NOMINEES, VIDEO_GAMES_LISTED_AMONG_THE_BEST, BEST_SELLING_PC_GAMES),
            "franchise": (HIGHEST_GROSSING_MEDIA_FRANCHISES, BEST_SELLING_MANGA, BEST_SELLING_BOOK_SERIES, EMMY_OUTSTANDING_DRAMA_SERIES_NOMINEES,
                          EMMY_OUTSTANDING_COMEDY_SERIES_NOMINEES, CRUNCHYROLL_ANIME_OF_THE_YEAR_NOMINEES),
            "artist": (BEST_SELLING_MUSIC_ARTISTS, MOST_STREAMED_SPOTIFY_ARTISTS),
            "author": (BEST_SELLING_FICTION_AUTHORS,),
            "creator": (MOST_SUBSCRIBED_YOUTUBE_CHANNELS, MOST_FOLLOWED_TWITCH_CHANNELS),
            "athlete": (BALLON_DOR_PODIUM, FORMULA_ONE_WORLD_CHAMPIONS, NBA_MVP_WINNERS),
            "celebrity": (ACADEMY_AWARD_BEST_ACTOR_NOMINEES, ACADEMY_AWARD_BEST_ACTRESS_NOMINEES)}
FULL_NAMES = frozenset({"sports_team", "athlete", "celebrity"})
PERSONS = frozenset({"athlete"})
WORD = re.compile(r"\w+")
DESCRIPTORS = frozenset({"manga", "anime", "franchise", "series", "tv series", "film", "video game", "novel"})


def folded(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def variants(title):
    title = title.replace("×", "x")
    names = [re.sub(r"\s*\([^)]*\)", "", title).strip(), *(inner for inner in re.findall(r"\(([^)]*)\)", title) if inner.lower() not in DESCRIPTORS)]
    names = [part for name in names for index, part in enumerate(name.split(" / ")) if index == 0 or " " in part]
    names += [side for name in names if ": " in name for side in name.split(": ", 1)]
    names += [name[4:] for name in names if name.startswith("The ")]
    whole = names[0].removeprefix("The ")
    return {(variant, name.removeprefix("The ") == whole) for name in names for variant in (name, folded(name)) if LETTERS.search(variant)}


def table():
    entries = {}
    for attribute, blocks in LEXICONS.items():
        for block in blocks:
            for entry in filter(None, (piece.strip() for piece in block.replace("\n", "").split(";"))):
                head, *aliases = entry.split("|")
                surname = [(head.split()[-1], False)] if attribute in PERSONS and " " in head else []
                for alias in (head, *aliases):
                    for variant, primary in [*variants(alias), *surname]:
                        tokens = tuple(WORD.findall(variant))
                        single = sum(token.lower() != "the" for token in tokens) == 1
                        if single and variant == variant.lower():
                            continue
                        cased = tokens if single or variant.isupper() or not (primary or attribute in FULL_NAMES) else None
                        value = (head if attribute in FULL_NAMES else variant).lower()
                        entries.setdefault(" ".join(tokens).lower(), {}).setdefault(attribute, set()).add((value, cased, primary))
    lookup, first = {}, {}
    for key, kinds in entries.items():
        main = any(primary for pairs in kinds.values() for _, _, primary in pairs)
        if kept := tuple((attribute, value, cased) for attribute, pairs in kinds.items() if len({value for value, _, _ in pairs}) == 1 and (not main or any(primary for _, _, primary in pairs))
                         for value, cased in {(value, cased) for value, cased, _ in pairs}):
            lookup[key] = kept
            head = key.split()[0]
            first[head] = max(first.get(head, 0), len(key.split()))
    return lookup, first


TABLE, FIRST = table()


def mentions(text, loose=False):
    words = [(match.start(), match.end(), match.group()) for match in WORD.finditer(text)]
    lows = [word.lower() for _, _, word in words]
    spans = []
    for index, low in enumerate(lows):
        taken = set()
        for size in range(min(FIRST.get(low, 0), len(words) - index), 0, -1):
            if entries := TABLE.get(" ".join(lows[index:index + size])):
                shown = tuple(word for _, _, word in words[index:index + size])
                matched = [(attribute, words[index][0], words[index + size - 1][1], value, cased, not cased or cased == shown) for attribute, value, cased in entries
                           if attribute not in taken and (loose or not cased or cased == shown)]
                spans.extend(matched)
                taken.update(attribute for attribute, *_ in matched)
    return spans


LEXICON_CONTEXT = dict(CONTEXTS)
LEXICON_CONTEXT["artist"] = re.compile(CONTEXTS["artist"].pattern[:-4] + r"|sing|sings|sang|singing|playlist|records?|records|festival|fans?|stan)\b)")
LEXICON_CONTEXT["franchise"] = re.compile(CONTEXTS["franchise"].pattern[:-4] + r"|read|reading|fandom|canon|plot|characters?|finale|spinoff|reboot|adaptation)\b)")
AUTHORING = re.compile(r"(?i:\b(?:author|authors|novelist|writer|writes|wrote|written|books?|novels?|reading|read|series|trilogy)\b)")
TARGET_CONTEXT = {**LEXICON_CONTEXT, "author": AUTHORING}


def opening(text, start):
    before = text[:start].rstrip(" \t\"'*(#>-_[")
    return not before or before[-1] in ".!?\n:"


SELF = re.compile(r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)")
SHORT = 6
OPEN = frozenset({"franchise", "artist"})
ITEMS = re.compile(r"\s*(?:,|;|\||/|\band\b|&)\s*")


def engaged(text, start, end, attribute):
    left = max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1
    right = min((found for found in (text.find(mark, end) for mark in ".!?\n") if found >= 0), default=len(text))
    if text[right:right + 1] == "?":
        return False
    if attribute == "video_game":
        left, right = max(0, left - 100), right + 100
    scope = (0, len(text)) if attribute in OPEN else (left, right)
    return bool(SELF.search(text, *scope) or POSITIVE.search(text, left, right))


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


def chosen(text, start, options):
    if len(options) == 1:
        return options
    window = text[max(0, start - 150):start + 150]
    scored = [(3 * len(LEXICON_CONTEXT[option[0]].findall(window)) + len(LEXICON_CONTEXT[option[0]].findall(text)), option) for option in options]
    return [option for score, option in scored if score or option[0] == "franchise"] or [max(scored)[1]]


def known(text, found):
    grouped = {}
    for attribute, start, end, value, cased, exact in mentions(text, True):
        if attribute == "sports_team":
            if supported(text, start, end):
                named(attribute, value, found, start)
            continue
        if not exact or (cased and len(cased) == 1 and opening(text, start)) or ((cased or attribute in NAMED_ONLY) and not LEXICON_CONTEXT[attribute].search(text)):
            continue
        grouped.setdefault((start, end), []).append((attribute, value))
    spans = [(attribute, start, end, value) for (start, end), options in grouped.items() for attribute, value in chosen(text, start, options)]
    for attribute, start, end, value in spans:
        if any(other == attribute and left <= start and end <= right and right - left > end - start for other, left, right, _ in spans):
            continue
        if engaged(text, start, end, attribute):
            named(attribute, value, found, start)
    listed(text, spans, found)


def pieces(text, start, end):
    cursor = start
    for separator in ITEMS.finditer(text, start, end):
        yield cursor, separator.start()
        cursor = separator.end()
    yield cursor, end


def lists(text):
    lines = [(line.start(), line.end()) for line in re.finditer(r"[^\n]*\S[^\n]*", text)]
    for start, end in lines:
        if len(items := list(pieces(text, start, end))) >= 3:
            yield items


def listed(text, spans, found):
    for items in lists(text):
        inside = [(attribute, left, right) for attribute, left, right, _ in spans if items[0][0] <= left and right <= items[-1][1]]
        if not inside:
            continue
        counts = {attribute: sum(other == attribute for other, _, _ in inside) for attribute, _, _ in inside}
        attribute = max(counts, key=counts.get)
        if counts[attribute] < 2 or attribute != "franchise":
            continue
        for start, end in items:
            item = re.sub(r"^\W*(?:\d+[.)]\s*)?|[\W_]+$", "", text[start:end])
            words = item.lower().split()
            if not words or len(words) > SHORT or words[0] in COMMON or words[0] in GENERIC or not LETTERS.search(item):
                continue
            if any(left < end and start < right for _, left, right in inside):
                continue
            named(attribute, item.lower(), found, start)
