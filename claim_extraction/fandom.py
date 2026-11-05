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
            if kinds[kind] and not (kind == "franchise" and othered(part.lower(), match.start(), match.end())):
                names.append((abs(match.start() - cue.start()), kind, name))
        for _, kind, name in sorted(names):
            if kind not in NAMED_ONLY and not junk(name) and (kind == "artist" or 1 < len(TRAILING.sub("", name).split()) < 4):
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
        if kinds[kind] and kind not in NAMED_ONLY and not junk(name) and (len(words) < 3 or kind == "franchise" and len(words) < 4):
            named(kind, name, found, match.start())


DEGREE = r"(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted|avid|hardcore|crazy|super|major|total|self[- ](?:admitted|proclaimed|confessed|described))"
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am|i've been|ive been|been|as|being) (?:an? )?(?:{DEGREE} )*){NAME}(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)")
TEAM_FAN = re.compile(rf"(?i:\b(?:(?:i'm|im|i am|i've been|ive been|been|as|being|from) (?:an? )?|(?:fellow|{DEGREE}) )(?:{DEGREE} )*){NAME}(?i: (?:fan|supporter)s?\b)|"
                      rf"(?:(?m:^)|(?<=[.!?] )){NAME}(?i: (?:fan|supporter)(?:s? (?:here|since|for life|all my life|my whole life|through and through)\b|(?=[,.!;:]|(?m:$))))")
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
LOWER_FAN = re.compile(rf"(?i:\b(?:i'm|im|i am|i've been|ive been|as|being) (?:an? )?(?:{DEGREE} )*)((?:[a-z][\w'-]* ){{0,2}}[a-z][\w'-]*) (?:fan|stan|supporter)\b")
LIKED_PERSON = re.compile(rf"(?i:\bi (?:really |absolutely |just |also |still |honestly |genuinely |do |totally |personally |kinda |always )*(?:like|liked) ){NAME}")
CREATED = re.compile(rf"{NAME}(?:(?:'s|s'|’s) |(?<!'s)(?= (?i:youtube|yt|twitch|tiktok) ))(?i:(?: ?(?:youtube|yt|twitch|tiktok) )?(?:new |latest |recent |old |last |early )?(?:videos?|vids|streams?|vods?|channel|podcasts?|content|vlogs?)\b)")
WATCHED = re.compile(rf"(?i:\b(?:i (?:\w+ )?(?:watch|watching|watched)|subscribed to|i follow|i'?ve been following) ){NAME}(?i: (?:on|'s) (?:youtube|twitch|tiktok|kick)\b)")
LISTENED = re.compile(rf"(?i:\b(?:i(?:'m| am|'ve been| have been)? (?:\w+ )?(?:listening to|listen to|listened to|jamming to|bumping)|been (?:listening to|bumping|jamming to)) ){NAME}")
ALBUM = re.compile(rf"{NAME}(?:'s|s'|’s) (?i:(?:new |latest |last |debut |first |second |third |next |old |early )?(?:albums?|songs?|singles?|discography|tour|concerts?|records?|ep|lp|music|vocals|lyrics)\b)")
SEEN = re.compile(rf"(?i:\b(?:i|we) (?:\w+ )?(?:saw|seen|see|seeing) ){NAME}(?i: (?:live|in concert|perform|play live|open for)\b)")
PRAISED = re.compile(rf"(?:(?m:^)|(?<=[.!?] )){NAME}(?i: (?:is|was|are|were|has been|remains) (?:still |so |fucking |really |honestly |just |literally |absolutely |easily |genuinely |lowkey )*"
                     rf"(?:peak|goated|amazing|incredible|underrated|phenomenal|a masterpiece|a banger|fire|elite|god ?tier|top tier|the goat|the best\b|one of the best)\b)")
LITERALS = {FAN: (" fan", " supporter", " stan", " enjoyer"), FAN_OF: ("fan of", "supporter of", "admirer of"), STAN: ("stan",), GOAT: ("goat",), GOATED: ("goat",)}
FAVORITE_PLAIN = re.compile(rf"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav) ({KIND_WORDS})s? (?:is|has to be|would be|was|are)\s+"
                            r"((?:the )?[\w'&:!+-]+(?: [\w'&:!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|lol|too|tbh|honestly|by far|hands down|of all time|ever|for sure)\b)")
PERSON = r"((?:[A-Z]\. |[A-Z][\w-]*(?:'[A-Z][\w-]*)? ){1,3}[A-Z][\w-]*(?:'[A-Z][\w-]*)?)(?![\w-])"
WRITTEN_BY = re.compile(rf"(?<!read )\bby {PERSON}")
BOOKISH = ("author", "novel", "writ", "wrote", "book", "read", "series", "trilogy", "saga")
BLANK = re.compile(r"\n[^\S\n]*\n")
ADVISED = re.compile(r"(?i:\b(?:recommend\w*|suggest\w*|advise|try|check out)\b)")
WROTE = re.compile(rf"{PERSON}(?:'s|s') (?:[\w:'-]+ ){{0,6}}?(?i:books?|novels?|series|trilogy|saga|writing)\b|(?i:\b(?:read|reading|finished|love|loved|enjoy|enjoyed)\b (?:\w+ ){{0,3}}){PERSON}(?i: (?:books|novels)\b)")
CHOICE = re.compile(r"\^\((?:My choice|Me|Chose|My pick): ([^)|\n]{2,60}?)\s*[)|]")
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
LISTS = frozenset({"artist", "franchise", "video_game"})
LIKABLE = frozenset({"artist", "franchise"})
RUN = 3


def parts(name):
    name = STOP.split(name)[0]
    if " " not in name or lexical(name):
        return [name]
    return [piece for piece in SPLIT.split(POSSESSIVE.sub("", name)) if piece]


def lexical(name):
    surface = name.rstrip(" .,!:")
    hits = [(links, attribute, value) for attribute, start, end, value, _, _, links in mentions(name) if start == 0 and end == len(surface)]
    if not hits:
        return None
    _, attribute, value = max(hits)
    return attribute, shown(surface, value)


def proper(name):
    titled = " ".join(word.capitalize() for word in name.split())
    hits = [(links, attribute, value) for attribute, start, end, value, _, common, links in mentions(titled) if start == 0 and end == len(titled) and not common and attribute in PEOPLE and attribute != "character"]
    return max(hits)[1:] if hits else None


def shown(surface, value):
    return surface if len(surface) > SHORT_KEY and " ".join(WORD.findall(surface.lower())) != " ".join(WORD.findall(value)) else value


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
    for pattern in (FAVORITE, FAVORED) if "fav" in lowered or "goat" in lowered else ():
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
    for match in TEAM_FAN.finditer(text) if " fan" in lowered or " supporter" in lowered else ():
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            for piece in parts(match.group(1) or match.group(2)):
                if club := team(piece):
                    named("sports_team", club, found, match.start())
    for pattern in (FAN, FAN_OF, STAN, GOAT, GOATED, PRAISED):
        for match in pattern.finditer(text) if any(word in lowered for word in LITERALS.get(pattern, ("",))) else ():
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
        elif (hit := lexical(name)) and hit[0] in NAMED_ONLY:
            named(*hit, found, match.start())
        elif not hit:
            for piece in parts(name):
                if hit := classified(text, match.start(), piece, PEOPLE):
                    named(*hit, found, match.start())
    for match in LOWER_FAN.finditer(text) if " fan" in lowered or " stan" in lowered or " supporter" in lowered else ():
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            if club := team(match.group(1)):
                named("sports_team", club, found, match.start())
            elif hit := proper(match.group(1)):
                named(*hit, found, match.start())
    for match in LIKED_PERSON.finditer(text):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE) and (hit := lexical(STOP.split(match.group(1))[0])) and hit[0] in NAMED_ONLY:
            named(*hit, found, match.start())
    for match in CHOICE.finditer(text):
        if " " in (name := match.group(1).strip()) and (hit := lexical(name)):
            named(*hit, found, match.start())
    for pattern in (CREATED, WATCHED):
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
    authored(text, found)
    known(text, found)


def paragraph(text, start):
    return blank.start() if (blank := BLANK.search(text, start)) else len(text)


def authored(text, found):
    lowered = text.lower()
    if not any(word in lowered for word in BOOKISH):
        return
    for pattern in (WRITTEN_BY, WROTE):
        for match in pattern.finditer(text):
            name = match.group(1) or match.group(2)
            left, right = sentence(text, match.start(), match.end())
            alone = pattern is WRITTEN_BY and opening(text, left) and not text[match.end():right].strip(" .,!*}")
            if not (SELF.search(text, left, right) or POSITIVE.search(text, left, right) or alone and SELF.search(text, right, paragraph(text, right))) or NEGATIVE.search(text, left, right) or text[right:right + 1] == "?" or ADVISED.search(text, left, right) or hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                continue
            hit = lexical(name)
            if hit and hit[0] not in ("author", "celebrity", "artist"):
                continue
            if pattern is WROTE or AUTHORING.search(text, max(0, left - 100), right + 100) and not CONTEXTS["artist"].search(text, max(0, left - 100), right + 100):
                named("author", hit[1] if hit and hit[0] == "author" else name, found, match.start())


def named(attribute, name, found, position):
    name = TRAILING.sub("", name).strip()
    words = name.lower().split()
    if 1 < len(name) <= 40 and words[0] not in PRONOUNS and words[-1] not in PRONOUNS and (value := fan_value(attribute, name.lower())):
        found.setdefault((attribute, value), position)


NFL_TEAMS_2025 = """arizona cardinals;atlanta falcons|Falcons;baltimore ravens|Ravens;buffalo bills|Bills;carolina panthers;chicago bears|Bears;cincinnati bengals|Bengals;cleveland browns|Browns;
dallas cowboys|Cowboys;denver broncos|Broncos;detroit lions|Lions;green bay packers|Packers;houston texans|Texans;indianapolis colts|Colts;jacksonville jaguars|Jaguars;
kansas city chiefs|Chiefs;las vegas raiders|oakland raiders|Raiders;los angeles chargers|Chargers;los angeles rams|Rams;miami dolphins|Dolphins;minnesota vikings|Vikings;
new england patriots|Patriots;new orleans saints|Saints;new york giants|Giants;new york jets|Jets;philadelphia eagles|Eagles;pittsburgh steelers|Steelers;
san francisco 49ers|49ers;seattle seahawks|Seahawks;tampa bay buccaneers|Buccaneers;tennessee titans|Titans;washington commanders|Commanders"""
NBA_TEAMS_2025 = """atlanta hawks|Hawks;boston celtics|Celtics;brooklyn nets|Nets;charlotte hornets|Hornets;chicago bulls|Bulls;cleveland cavaliers|Cavaliers;dallas mavericks|Mavericks;
denver nuggets|Nuggets;detroit pistons|Pistons;golden state warriors|Warriors;houston rockets|Rockets;indiana pacers|Pacers;la clippers|los angeles clippers|Clippers;
los angeles lakers|Lakers;memphis grizzlies|Grizzlies;miami heat;milwaukee bucks|Bucks;minnesota timberwolves|Timberwolves;new orleans pelicans|Pelicans;new york knicks|Knicks;
oklahoma city thunder;orlando magic;philadelphia 76ers|76ers;phoenix suns|Suns;portland trail blazers|trail blazers|Blazers;sacramento kings|Kings;san antonio spurs|Spurs;
toronto raptors|Raptors;utah jazz;washington wizards|Wizards"""
MLB_TEAMS_2025 = """arizona diamondbacks|Diamondbacks;atlanta braves|Braves;baltimore orioles|Orioles;boston red sox|red sox;chicago cubs|Cubs;chicago white sox|white sox;
cincinnati reds|Reds;cleveland guardians|Guardians;colorado rockies|Rockies;detroit tigers|Tigers;houston astros|Astros;kansas city royals|Royals;los angeles angels|Angels;
los angeles dodgers|Dodgers;miami marlins|Marlins;milwaukee brewers|Brewers;minnesota twins|Twins;new york mets|Mets;new york yankees|Yankees;athletics|oakland athletics;
philadelphia phillies|Phillies;pittsburgh pirates|Pirates;san diego padres|Padres;san francisco giants|Giants;seattle mariners|Mariners;st. louis cardinals|Cardinals;
tampa bay rays|Rays;texas rangers|Rangers;toronto blue jays|blue jays|Jays;washington nationals|Nationals"""
NHL_TEAMS_2025 = """anaheim ducks|Ducks;boston bruins|Bruins;buffalo sabres|Sabres;calgary flames|Flames;carolina hurricanes|Hurricanes;chicago blackhawks|Blackhawks;
colorado avalanche|Avalanche;columbus blue jackets|blue jackets;dallas stars|Stars;detroit red wings|red wings;edmonton oilers|Oilers;florida panthers|Panthers;
los angeles kings|Kings;minnesota wild;montreal canadiens|Canadiens;nashville predators|Predators;new jersey devils|Devils;new york islanders|Islanders;
new york rangers|Rangers;ottawa senators|Senators;philadelphia flyers|Flyers;pittsburgh penguins|Penguins;san jose sharks|Sharks;seattle kraken|Kraken;
st. louis blues|Blues;tampa bay lightning|Lightning;toronto maple leafs|maple leafs|Leafs;utah mammoth|utah hockey club;vancouver canucks|Canucks;
vegas golden knights|golden knights;washington capitals|Capitals;winnipeg jets|Jets"""
MLS_TEAMS_2025 = """atlanta united;austin fc;charlotte fc;chicago fire fc;fc cincinnati;colorado rapids;columbus crew;d.c. united|dc united;fc dallas;houston dynamo;inter miami;la galaxy;
los angeles fc;minnesota united;cf montréal|cf montreal;nashville sc;new england revolution;new york city fc;new york red bulls;orlando city;philadelphia union;
portland timbers|Timbers;real salt lake;san diego fc;san jose earthquakes;seattle sounders|Sounders;sporting kansas city;st. louis city sc;toronto fc;vancouver whitecaps|Whitecaps"""
PREMIER_LEAGUE_TEAMS_2025 = """arsenal|Arsenal;aston villa;bournemouth|Bournemouth;brentford|Brentford;brighton & hove albion|brighton and hove albion;burnley|Burnley;
chelsea|Chelsea;crystal palace;everton|Everton;fulham|Fulham;leeds united;liverpool|Liverpool;manchester city;manchester united;
newcastle united;nottingham forest;sunderland|Sunderland;tottenham hotspur;west ham united;wolverhampton wanderers"""
LA_LIGA_TEAMS_2025 = """deportivo alavés|Alavés;athletic bilbao|athletic club;atlético madrid|atletico madrid;fc barcelona|Barcelona;celta vigo;elche|Elche;
espanyol|Espanyol;getafe|Getafe;girona|Girona;levante|Levante;mallorca|Mallorca;osasuna|Osasuna;rayo vallecano;real betis|Betis;real madrid;real oviedo;real sociedad;
sevilla|Sevilla;valencia|Valencia;villarreal|Villarreal"""
SERIE_A_TEAMS_2025 = """atalanta|Atalanta;bologna|Bologna;cagliari|Cagliari;como|Como;cremonese|Cremonese;fiorentina|Fiorentina;genoa|Genoa;hellas verona|Verona;inter milan|internazionale;
juventus|Juventus;lazio|Lazio;lecce|Lecce;ac milan|Milan;napoli|Napoli;parma|Parma;pisa|Pisa;as roma|Roma;sassuolo|Sassuolo;torino|Torino;udinese|Udinese"""
BUNDESLIGA_TEAMS_2025 = """fc augsburg|Augsburg;union berlin;werder bremen|Bremen;borussia dortmund|Dortmund;eintracht frankfurt;sc freiburg|Freiburg;hamburger sv;1. fc heidenheim|Heidenheim;
tsg hoffenheim|Hoffenheim;1. fc köln|fc köln|fc koln;rb leipzig|Leipzig;bayer leverkusen|Leverkusen;mainz 05;borussia mönchengladbach|mönchengladbach;
bayern munich|bayern münchen;fc st. pauli|St. Pauli;vfb stuttgart|Stuttgart;vfl wolfsburg|Wolfsburg"""
LIGUE_1_TEAMS_2025 = """angers|Angers;auxerre|Auxerre;stade brestois;le havre;rc lens|Lens;lille|Lille;lorient|Lorient;olympique lyonnais;olympique de marseille|Marseille;
metz|Metz;as monaco|Monaco;nantes|Nantes;ogc nice;paris fc;paris saint-germain;stade rennais;strasbourg|Strasbourg;toulouse|Toulouse"""
IPL_TEAMS_2025 = """chennai super kings;delhi capitals;gujarat titans;kolkata knight riders;lucknow super giants;mumbai indians;punjab kings;rajasthan royals;
royal challengers bengaluru|royal challengers bangalore;sunrisers hyderabad"""
TEAMS = (NFL_TEAMS_2025, NBA_TEAMS_2025, MLB_TEAMS_2025, NHL_TEAMS_2025, MLS_TEAMS_2025, PREMIER_LEAGUE_TEAMS_2025, LA_LIGA_TEAMS_2025, SERIE_A_TEAMS_2025, BUNDESLIGA_TEAMS_2025,
         LIGUE_1_TEAMS_2025, IPL_TEAMS_2025)
KNOWLEDGE = Path(__file__).with_name("knowledge.tsv")
CLUBS = Path(__file__).with_name("clubs.tsv")
FILMS = Path(__file__).with_name("films.tsv")
AUTHOR_OF_BOOK = dict(line.split("\t") for line in Path(__file__).with_name("book_authors.tsv").read_text(encoding="utf-8").splitlines()[1:])
SERIES_OF_GAME = dict(line.split("\t") for line in Path(__file__).with_name("game_series.tsv").read_text(encoding="utf-8").splitlines()[1:])
NONWORD_TITLES = frozenset(Path(__file__).with_name("nonword_titles.tsv").read_text(encoding="utf-8").splitlines()[1:])
PLACES = frozenset(line.split("\t", 1)[0] for line in Path(__file__).with_name("gazetteer.tsv").read_text(encoding="utf-8").splitlines()[1:])
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
    read(KNOWLEDGE, plain, cased)
    films = read(FILMS, {}, {})
    prefixes = set()
    for key in (*plain, *cased, *films[0], *films[1]):
        tokens = key.lower().split(" ")
        prefixes.update(" ".join(tokens[:size]) for size in range(1, len(tokens) + 1))
    return plain, cased, *films, prefixes


def read(path, plain, cased):
    with open(path, encoding="utf-8") as rows:
        next(rows)
        for line in rows:
            key, attribute, value, links, surfaces, common = line.rstrip("\n").split("\t")
            entry = (attribute, value, bool(surfaces), common == "1" or len(key) <= SHORT_KEY and not (any(char.isdigit() for char in key) and LETTERS.search(key)), int(links))
            for surface in surfaces.split("|") if surfaces else ():
                cased.setdefault(surface, []).append(entry)
            if not surfaces or (attribute in LOOSE and common == "1" and " " in key.removeprefix("the ")):
                plain.setdefault(key, []).append((attribute, value, False, common == "1" or len(key) <= SHORT_KEY, int(links)))
    return plain, cased


PLAIN, CASED, FILM_PLAIN, FILM_CASED, PREFIXES = table()


def team_words():
    words, places = {}, {}
    for entry in filter(None, (piece.strip() for block in TEAMS for piece in block.replace("\n", "").split(";"))):
        head, *aliases = entry.split("|")
        tokens = WORD.findall(head)
        for form in (head, *aliases, tokens[-1]):
            key = " ".join(WORD.findall(folded(form))).lower()
            for variant in (key, key[:-1]) if key.endswith("s") and " " not in key and len(key) > 4 else (key,):
                words.setdefault(variant, set()).add(head.lower())
        if len(tokens) > 1:
            places.setdefault(" ".join(WORD.findall(folded(" ".join(tokens[:-1])))).lower(), set()).add(head.lower())
    known = {key: next(iter(heads)) if len(heads) == 1 else key for key, heads in words.items()} | {key: next(iter(heads)) for key, heads in places.items() if len(heads) == 1 and key not in words}
    clubs = {}
    with open(CLUBS, encoding="utf-8") as rows:
        next(rows)
        for line in rows:
            key, _, value, *_ = line.split("\t")
            clubs[key] = value
    return clubs | known


TEAM_WORDS = team_words()


def team(name):
    return TEAM_WORDS.get(" ".join(WORD.findall(folded(name))).lower().removeprefix("the "))


def raised():
    lowered = {}
    for surface, entries in CASED.items():
        if " " not in surface and surface.lower().capitalize() == surface and (famous := [entry for entry in entries if entry[0] in TITLES and not entry[3] and entry[4] >= FAMOUS_SITELINKS]):
            lowered[surface.lower()] = famous
        elif " " not in surface and any(char.isdigit() for char in surface) and LETTERS.search(surface) and (coded := [entry for entry in entries if entry[0] in TITLES and not entry[3]]):
            lowered.setdefault(surface.lower(), coded)
        elif surface.lower() in NONWORD_TITLES and (coined := [entry for entry in entries if entry[0] in TITLES and not entry[3]]):
            lowered.setdefault(surface.lower(), coined)
    return lowered


RAISED = raised()


def sentence_cased():
    forms = {}
    for surface, entries in CASED.items():
        if " " in surface and (form := surface[0] + surface[1:].lower()) != surface and form not in CASED and (artists := [entry for entry in entries if entry[0] == "artist"]):
            forms.setdefault(form, []).extend(artists)
    return forms


SENTENCE_CASED = sentence_cased()


def mentions(text):
    words = list(WORD.finditer(text))
    shown = [word.group() for word in words]
    lows = [word.lower() for word in shown]
    spans, index, total = [], 0, len(words)
    while index < total:
        found, size, key, surface = None, 1, lows[index], shown[index]
        while key in PREFIXES:
            plain = PLAIN.get(key)
            cased = CASED.get(surface) or size == 1 and RAISED.get(surface) or not plain and SENTENCE_CASED.get(surface) or None
            if plain or cased:
                found = size, (plain or []) + (cased or [])
            elif (films := FILM_PLAIN.get(key, []) + FILM_CASED.get(surface, [])) and praised(text, words[index].start(), words[index + size - 1].end()):
                found = size, films
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


LIKED = re.compile(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |genuinely |do |personally |fucking )*(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig)|\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big |massive )?fan of|hooked on|in love with)|\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|are|was|has to be))(?: the)?\s+$")
SELF = re.compile(r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)")
DONE = {"video_game": re.compile(r"(?i:\b(?:play|playing|played|replay\w*|beat|beaten|finished|finishing|completed|platinumed|grinding|started|bought|preordered|pre-ordered|hours|hrs)\b)"),
        "franchise": re.compile(r"(?i:\b(?:watch|watching|watched|rewatch\w*|binge\w*|binging|read|reading|reread\w*|finished|finishing|started)\b)"),
        "artist": re.compile(r"(?i:\b(?:listen|listening|listened|saw|seen|concerts?|gigs?|vinyl|albums?|discography|tickets?|merch|tours?|records?|cds?|cassettes?|bought|preordered)\b)")}
CHEERED = frozenset({"celebrity", "creator"})
PLAYED = frozenset({"video_game", "artist"})
ALSO = {"celebrity": ("artist", "author"), "creator": ("celebrity", "artist")}


def sentence(text, start, end):
    return max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1, min((found for found in (text.find(mark, end) for mark in ".!?\n") if found >= 0), default=len(text))


def praised(text, start, end):
    left, right = sentence(text, start, end)
    return bool(POSITIVE.search(text, left, right)) and not NEGATIVE.search(text, left, right) and text[right:right + 1] != "?"


PRODROP = re.compile(r"[\W_]*(?i:(?:still|currently|just|finally|also|now|recently|been|really|absolutely|honestly) )*(?i:(love|loved|loving|enjoyed|enjoying|digging)|playing|played|replaying|replayed|finished|finishing|watching|watched|rewatching|rewatched|reading|rereading|listening to|listened to|started|bought)\b")


def engaged(text, start, end, attribute, popular, plain):
    left, right = narrow = sentence(text, start, end)
    dropped = attribute in TITLES and clause(text, start) <= left and PRODROP.match(text, left, start)
    if text[right:right + 1] == "?" or attribute == "athlete" and not (SELF.search(text, *narrow) or dropped):
        return False
    if plain and attribute == "franchise":
        return bool(POSITIVE.search(text, *narrow) or dropped and dropped.group(1))
    if attribute in DONE and (" " in text[start:end] or attribute == "artist" or attribute == "video_game" and not popular):
        left, right = max(0, left - 100), right + 100
    if POSITIVE.search(text, left, right) or dropped and dropped.group(1):
        return True
    if attribute in DONE and not popular:
        scope = (left, right) if attribute == "video_game" else narrow
        return bool((SELF.search(text, *scope) or dropped) and DONE[attribute].search(text, *scope))
    return attribute not in CHEERED and bool(SELF.search(text, left, right) or dropped)


BACKING = re.compile(r"(?i:\b(?:my|our|go|let'?s go|lets go|up the|c'?mon|come on|i (?:love|support|root for|cheer for|follow)|fan of|rooting for|cheering for|supporter of)(?: the| my| our| beloved| boys)?\s*$)")
BACKER = re.compile(r"(?i:\s*(?:nation|faithful|for life|forever|till i die|all the way)\b)")
FANNED = re.compile(r"(?i:\s*(?:fan|supporter)\b)")
AVOWED = re.compile(r"(?i:\b(?:i'?m|i am|as|been|being)\b[\w\s-]{0,20}$)")
OWNED = re.compile(r"(?:my|our)\b")
PEER = re.compile(r"(?i:\b(?:he|she|they|his|her|their|dad|mom|father|mother|brother|sister|wife|husband|son|daughter|friend|friends|boyfriend|girlfriend|partner|people|everyone|nobody|every)\b)")


def othered(lowered, start, end):
    left = clause(lowered, start)
    return bool(PEER.search(lowered, left, start)) and not SELF.search(lowered, left, end)


def supported(text, start, end):
    lowered = text.lower()
    before = max(0, start - 30)
    backed = BACKING.search(lowered, before, start)
    if backed and text[start:end].islower() and OWNED.match(backed.group()):
        backed = None
    if not (backed or BACKER.match(lowered, end) or (FANNED.match(lowered, end) and AVOWED.search(lowered, before, start))):
        return False
    return not PEER.search(lowered, clause(lowered, start), start) and not hedged(lowered, start, end, SELF_HEDGE)


def chosen(text, start, options, totals):
    if len(options) == 1:
        return options
    window = text[max(0, start - 150):start + 150]
    scored = [(3 * len(LEXICON_CONTEXT[option[0]].findall(window)) + totals(option[0]), option) for option in options]
    return [option for score, option in scored if score or option[0] != "video_game"]


FAVOURED = re.compile(r"(?i:fav(?<!least fav)(?<!\wfav)(?:ou?rites?|es?|s)?\b[^\n:]*:|\^\(likes?:)")


def favoured(segments, start):
    return any(left <= start < right for left, right in segments)


def preferred(start, end, options, bypassed, loved):
    if not loved:
        return [option for option in options if (start, end, option[0]) not in bypassed] or options
    plain = [option for option in options if (start, end, option[0]) not in loved]
    return ([option for option in plain if (start, end, option[0]) not in bypassed] or plain) + [option for option in options if (start, end, option[0]) in loved]


def known(text, found):
    grouped, counts, opened, famous, ordinary, bypassed, readings, loved = {}, {}, set(), set(), set(), set(), {}, set()

    def totals(attribute):
        if attribute not in counts:
            counts[attribute] = len(LEXICON_CONTEXT[attribute].findall(text))
        return counts[attribute]

    segments = [(match.end(), end if (end := text.find("\n", match.end())) >= 0 else len(text)) for match in FAVOURED.finditer(text)]
    for attribute, start, end, value, cased, common, links in mentions(text):
        if attribute == "sports_team":
            if supported(text, start, end):
                named(attribute, value, found, start)
            continue
        if attribute in PEOPLE:
            readings.setdefault((start, end, attribute), value)
        surface = text[start:end]
        key = " ".join(WORD.findall(folded(surface).lower())).removeprefix("the ")
        liked = attribute in LIKABLE and LIKED.search(text, max(0, start - 40), start)
        if (attribute == "character" or (cased and attribute in SPELLED) or (common and links < FAMOUS_SITELINKS and " " not in surface and not liked)
                or (attribute in TITLES and len("".join(WORD.findall(value))) <= 2)
                or (attribute in TITLES and (key in COMMON or key in PLACES) and surface.removeprefix("the ").removeprefix("The ") in (key, key.capitalize(), key.title()))
                or (attribute in LOOSE and not cased and common and links < FAMOUS_SITELINKS and surface.islower())
                or (attribute == "franchise" and surface.islower() and any(char.isdigit() for char in surface))):
            continue
        gated = (cased or common or attribute in NAMED_ONLY or attribute in GATED) and not GATES[attribute].search(text, max(0, start - WINDOW), end + WINDOW)
        if gated and not ((attribute == "franchise" and links >= FAMOUS_SITELINKS and not common or attribute in NAMED_ONLY) and praised(text, start, end)
                          or liked or favoured(segments, start)):
            continue
        if gated and liked and attribute != "franchise":
            loved.add((start, end, attribute))
        if cased and " " not in surface and opening(text, start):
            bounds = sentence(text, start, end)
            if not (attribute in TITLES and POSITIVE.search(text, *bounds) or attribute == "video_game" and SELF.search(text, *bounds)):
                opened.add((start, end, attribute))
        if links >= FAMOUS_SITELINKS and attribute in TITLES:
            famous.add((start, end, attribute))
        if common and links < FAMOUS_SITELINKS:
            ordinary.add((start, end, attribute))
        if gated and attribute in NAMED_ONLY and not favoured(segments, start):
            bypassed.add((start, end, attribute))
        grouped.setdefault((start, end), []).append((attribute, value))
    spans = sorted((start, end, attribute, value) for (start, end), options in grouped.items() for attribute, value in chosen(text, start, preferred(start, end, options, bypassed, loved), totals))
    listed = set()
    run = []
    for span in [*spans, None]:
        if span and run and span[2] == run[-1][2] and LISTED.fullmatch(text, run[-1][1], span[0]):
            run.append(span)
            continue
        if len(run) >= RUN and run[0][2] in LISTS:
            listed.update(run)
        run = [span]
    told, lowered = set(), ""
    for span in spans:
        start, end, attribute, value = span
        if attribute == "video_game" and othered(lowered := lowered or text.lower(), start, end):
            continue
        if ((attribute, value) not in told and (span in listed or favoured(segments, start) or ((start, end, attribute) not in opened and engaged(text, start, end, attribute, (start, end, attribute) in famous, (start, end, attribute) in ordinary)))
                and not (attribute not in PLAYED and hedged(lowered := lowered or text.lower(), start, end, SELF_HEDGE))):
            told.add((attribute, value))
            named(attribute, shown(text[start:end], value), found, start)
            if attribute == "franchise" and (writer := AUTHOR_OF_BOOK.get(value)) and AUTHORING.search(text) and praised(text, start, end):
                named("author", writer, found, start)
            if attribute == "video_game" and value in SERIES_OF_GAME:
                named("franchise", SERIES_OF_GAME[value], found, start)
            for other in ALSO.get(attribute, ()):
                if (start, end, other) in readings:
                    named(other, shown(text[start:end], readings[start, end, other]), found, start)
