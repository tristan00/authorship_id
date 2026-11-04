import re

from .common import FOR, I, SELF_HEDGE, TAG, clause, rule
from .common import hedged as qualified
from .places import NATIONS, PEOPLES, PLACES, TOKEN

DIRECTIONS = "north south east west northern southern eastern western central upstate downstate rural coastal middle sw se nw ne northeast northwest southeast southwest downtown uptown metro inner outer far deep".split()
LEXICON = {**{name.removeprefix("the "): entry for name, entry in PLACES.items() if name not in DIRECTIONS}, **PEOPLES, **{name: ("nation", country, "", country, "") for name, country in NATIONS.items()}}
SQUASHED = {name.replace(" ", ""): entry for name, entry in LEXICON.items() if " " in name and entry[0] not in ("nation", "people")}
FIRST = {}
for name in LEXICON:
    FIRST[name.split(" ", 1)[0]] = max(FIRST.get(name.split(" ", 1)[0], 0), name.count(" ") + 1)
NATION = "|".join(sorted(map(re.escape, NATIONS), key=len, reverse=True))
LANGUAGES = frozenset("english spanish french german italian portuguese dutch swedish norwegian danish finnish polish czech slovak hungarian romanian bulgarian greek croatian serbian "
                      "russian ukrainian turkish arabic hebrew persian farsi hindi urdu bengali punjabi tamil telugu marathi gujarati malayalam kannada chinese mandarin cantonese japanese "
                      "korean vietnamese thai tagalog filipino indonesian malay swahili afrikaans catalan basque icelandic estonian latvian lithuanian albanian".split())
GAP = re.compile(r"[ .'-]{1,3}")
JOIN = re.compile(r"\s*[,(/–-]?\s*")
END = rf"(?:(?:an?|the)\s+(?:\w+\s+){{0,2}}(?:town|village|city|suburb|part|side|area|middle of nowhere)\s+(?:in|of|near|outside(?: of)?)\s+)?(?:the\s+)?(?:city of\s+|state of\s+|town of\s+|province of\s+|greater\s+)?(?:(?:{'|'.join(DIRECTIONS)})\s+)?[*_]*\Z"
ADVERB = r"(?:(?:currently|now|still|also|just|actually|already|really|basically|technically|originally|both|all|recently|happily|finally|permanently)\s+)*"
WAY = r"(?:(?:just|right|somewhere|up|down|out|over|back|here|there|mostly)\s+)*(?:(?:north|south|east|west|northeast|northwest|southeast|southwest|outside|close to|next to|near)\s+(?:of\s+)?)?"
PREP = r"(?:in|near|outside(?: of)?|around|by|at|out of)\s+"
SUBJECT = r"(?:\bi|\bwe|\bme and my \w+|\bmy (?:wife|husband|partner|family|girlfriend|boyfriend|fiance|fiancee|kids|parents) and i)"
LIVE = re.compile(rf"{SUBJECT}(?:\s+(?:currently|now|still|also|just|actually|already|really|recently|both|all|happily|finally))*(?:\s+(?:live|reside|moved|relocated|settled)|(?:'ve|\s+have)\s+(?:been\s+)?(?:lived|living|based|settled))\s+{ADVERB}{WAY}(?:{PREP}|to\s+|on\s+)?(?:(?!(?:a|an|the|my|our|with|and|but|for|of|to|in|by|near|at|from|this|that|fear|hope|peace|sin|denial)\b)[a-z]+\s+){{0,2}}?{END}")
BEING = re.compile(rf"(?:\bi'm|\bim|\bi am|\bwe're|\bwe are|\biam|\bi (?:now|currently|still|also) am)(?:\s+(?:currently|now|still|also|just|actually|already|really|basically|technically|both|all|living|based|located|residing|settled|here|out|over|down|up|back|happily|permanently|right|somewhere))*\s+(?:{WAY}{PREP}|(?:(?:just|right)\s+)?(?:north|south|east|west|northeast|northwest|southeast|southwest|outside)\s+of\s+){END}")
BARE = re.compile(rf"(?:^|[\n.!?;:•*>(|/-]\s*|\b(?:and|but|also|currently|now|so|still)\s+)(?:currently\s+|now\s+|also\s+|still\s+)?(?:live|living|lives|based|located|residing|reside)\s+(?:here\s+)?{PREP}{END}")
HERE = re.compile(rf"\b(?:here|over here|out here|down here|up here)\s+in\s+{END}|(?:^|[\n.!?,;:(]\s*|\b(?:for|of|to|with|among)\s+)(?:we|us)\s+(?:here\s+)?in\s+{END}|\b(?:greetings|hello|hi|hey|love|cheers|regards|blessings|hugs|howdy|saludos|grüße|grüsse)\s+from\s+{END}"
                  rf"|\b(?:my|our) (?:city|town|country|state|province|county|neighborhood|neighbourhood|island|village|area|house|building|apartment|flat)(?:\s*(?:of residence|of|,|:|-|\(|\.|is in|in))*\s*{END}")
MOVED = re.compile(rf"(?:(?:^|[\n.!?;:(]\s*|\bthen\s+|\b\d{{2}}\s?[mf]\s+)(?:just\s+|recently\s+|finally\s+|eventually\s+)?(?:moved|relocated)|\bdecided to (?:move|relocate))\s+(?:back\s+)?(?:over\s+)?(?:here\s+)?to\s+{END}")
ABROAD = re.compile(rf"\b(?:vivo|vivimos|resido|radico|estoy|estamos|moro|moramos|wohne|wohnen|lebe|leben|j'habite|habite|je vis|je réside|j'vis|je me trouve|me trouve|abito|risiedo|woon|wonen)\s+(?:actualmente\s+|atualmente\s+|aktuell\s+|derzeit\s+|zurzeit\s+|actuellement\s+|attualmente\s+|nu\s+)?"
                    rf"(?:en|em|no|na|in|im|à|a|au|aux|dans le|dans la|dans les|dans|nel|nella|bei|nahe|cerca de|perto de|près de|vicino a|in der nähe von)\s+(?:el\s+|la\s+|o\s+|a\s+|der\s+|den\s+|le\s+|il\s+|het\s+)?\Z"
                    r"|\b(?:aquí|aqui|acá|hier|ici|qui)\s+(?:en|em|no|na|in|à|a)\s+\Z")
FROM = re.compile(rf"(?:\bi'm|\bim|\bi am|\bwe're|\bwe are|\bi come|\bwe come|\boriginally|\bbeing|\bme being)(?:\s+(?:currently|still|also|just|actually|originally|both|all|here|over|out|down|up|\w+ly))*\s+from\s+{END}"
                  rf"|(?:^|[\s(\[])(?:\d{{2}}\s?[mfw]|[mfw]\s?\d{{2}}|cpl)(?:\s+here)?\s+from\s+{END}"
                  rf"|\b(?:i'm|im|i am)\s+(?:an?\s+)?\d{{2}}(?:\s*-?\s*(?:years?[- ]old|yo|y/o|[mf]))?(?:\s+[a-z]+){{0,3}}\s+from\s+{END}")
GERMAN = re.compile(r"\b(?:ich\s+)?(?:komme|kommen|bin)\s+(?:\w+\s+)?(?:aus|von)\s+(?:der nähe von\s+|dem\s+|der\s+)?\Z|(?:^|[,(\[/])\s*aus\s+\Z|\b(?:[mwf]\s?\d{2}|\d{2}\s?[mwf]|[mwf])\s+aus\s+\Z")
LEFT = re.compile(r"\b(?:soy|somos|sou)\s+(?:de|del|da|do|originario de|originaria de|natural de)\s+(?:la\s+|el\s+|o\s+|a\s+)?\Z|\b(?:ich\s+)?stamme\s+(?:\w+\s+)?(?:aus|von)\s+(?:der nähe von\s+|dem\s+|der\s+)?\Z"
                  r"|\bje (?:suis|viens) (?:de|du|d')\s*\Z|\bsono di\s+\Z|\bvengo (?:de|da|dal|dalla)\s+\Z|\b(?:ik\s+)?kom (?:uit|van)\s+\Z")
ORIGIN = re.compile(rf"(?:{SUBJECT}|\bas an? (?:person|guy|girl|woman|man|kid|someone) who)(?:\s+(?:was|were|got))?(?:\s+(?:\w+ly|also|both|all))*\s+(?:grew up|raised|born|brought up)(?:\s+and\s+(?:raised|bred))?\s+(?:in|on|near|outside(?: of)?|around)\s+{END}"
                    rf"|\bborn and (?:raised|bred) (?:in|on)\s+{END}|(?:^|[\n.!?(]\s*)(?:grew up|born|raised|born and raised) in\s+{END}"
                    rf"|(?:^|[\n.!?(,]\s*)(?:growing up|having grown up) (?:in|on)\s+{END}|\b(?:i|i'm|im|i was|me)\b[^.!?\n]{{0,60}}?\b(?<!kids )(?<!children )(?<!son )(?<!daughter )(?<!they )(?<!who )growing up (?:in|on)\s+{END}|\b(?:i|we)\s+(?:\w+ly\s+)?hail from\s+{END}|\b(?:i|we)\s+spent (?:my|our) (?:\w+\s+)?(?:childhood|youth|teens|teenage years|early years) (?:in|on)\s+{END}|\b(?:i'm|im|i am) (?:an?\s+)?native of\s+{END}"
                    rf"|\b(?:my|our) (?:\w+\s+)?(?:hometown|home town|home country|homeland|birthplace|birth country|native country|motherland|home state)(?:\s*(?:is|was|of|in|,|:|-|\())*\s*{END}"
                    r"|\b(?:nací|naci|nasci|nacido|nacida|nascido|nascida|geboren|né|née|nato|nata)\s+(?:en|em|no|na|in|à|a|au)\s+\Z")
HEDGE = re.compile(r"\b(?:if|when|whenever|unless|whether|wish|wished|hope|imagine|pretend|once|until|till|before|would|could|should|wanna|want to|plan to|planning to|used to|thinking about|considering)\s+(?:\w+\s+){0,2}\Z")
LATER = re.compile(r"\s*(?:for\s+(?:(?:a|an|the|this|next|one|two|three|few|couple|\d+)\s+){0,2}(?:of\s+)?(?:day|days|week|weeks|weekend|night|nights|month|months|trip|holiday|holidays|vacation|work|business|bit|while|now|summer|conference)\b|on|until|till|next|this|last|right now|today|tonight|tomorrow|again|visiting|at the moment)\b")
START = re.compile(r"(?:^|[\n.!?,;(:]\s*|\b(?:also|fellow|another|a|an|proud)\s+)\Z")
PERSON = r"(?:guy|girl|man|woman|boy|lady|dude|gal|person|couple|cpl|student|kid|teen|teenager|mom|mum|dad|father|mother|wife|husband|bro|native|immigrant|expat|top|bottom|vers|bear|twink|femboy|sub|dom|daddy|milf|bull|transfem|transmasc|nurse|doctor|engineer|teacher|developer|artist|writer|player|gamer)s?"
HERE_AFTER = re.compile(rf"(?:\s+(?:{PERSON}|people|resident|local|area|family|fan|collector|redditor|user))?,?\s+here\b(?=\s*(?:$|[\n.!,;:)\-–—(&]|and\b|too\b|as well\b|lol|haha|so\b|but\b|with\b))")
SELF = re.compile(r"(?:\b(?:i'm|im|i am|we're|we are|am)\s+(?:an?\s+)?|^|[\n.!?,;]\s*)\Z")
BORN = re.compile(r"(?:\b(?:i'm|im|i am|we're|we are|am|my|i was)\s+(?:an?\s+)?|^|[\n.!?,;(]\s*)\Z")
PEOPLE = re.compile(r"\b(?:i'm|im|i am|iam|as|am|we're|we are|being)\s+(?:an?\s+)?(?:(?!not\b|never\b|half\b|part\b|quarter\b|mixed\b)\w+\s+)?\Z|\b(?:native|fellow)\s+\Z")
CITIZEN = re.compile(r"\b(?:i'm|im|i am|as|am|we're|we are|being|dual)\s+(?:an?\s+)?(?:\w+\s+)?\Z|\(\Z")
TITLE = re.compile(rf"(?<![\w-])(?:{FOR}|{TAG}|\b\d{{2}},\s*[mf]\b|\[\d{{2}}\]|\(\d{{2}}\)|\b[mft]4[mfatr]\w*|\bage:?\s*\d{{2}}\b|\b\d{{2}}\s*/\s*[mf]\b|\b[mf]\s*/\s*\d{{2}}\b)|^\s*\d{{2}}(?=\s+(?!(?:years?|days?|weeks?|months?|hours?|minutes?|seconds?|times?|percent|people|of)\b(?!\s+old))[a-z])", re.M)
LEAD = re.compile(rf"(?:{FOR}|{TAG}|[\[\](){{}}#/|,:;!.–-]|\b(?:in|from|near|around|aus|de|em|en|di|loc|male|female)|^\s*\(?\d{{2}}\)?|^)\s*(?:(?:{'|'.join(DIRECTIONS)})\s+)?\Z", re.M)
TOWN_LEAD = re.compile(rf"\b(?:in|from|to|of|near|around|outside|at)\s+(?:(?:{'|'.join(DIRECTIONS)})\s+)?\Z")
TAG_LEAD = re.compile(rf"(?:{FOR}|{TAG})\s*\Z")
LAST = re.compile(r"[\W_]*\Z")
NEAR = re.compile(r"\b(?:in|from|near|around|aus)\s+\Z")
ASKING = re.compile(r"\b(?:for|looking|seeking|searching|want|wants|need|needs|into|with|like|likes|love|loves|any|anyone|you|you're|youre|your|if)\b")
ADMINISTRATIVE = re.compile(r"\b(?:region|city|province|district|county|governorate|prefecture|department|municipality|oblast|division|capital)\b")
FEDERAL = frozenset({"united states", "canada", "australia", "india"})
TITLE_REGIONS = FEDERAL | {"united kingdom"}
LOOSE = re.compile(rf"\b(?:and|but|so)\s+(?:then\s+|just\s+|recently\s+|finally\s+|eventually\s+)?(?:moved|relocated)\s+(?:back\s+)?(?:here\s+)?to\s+{END}|(?<!be )(?<!it's )(?<!its )(?<!it )(?<!is )(?<!are )(?<!was )(?<!were )(?<!they're )\b(?:living|based|located|residing)\s+(?:here\s+)?{PREP}{END}|\b(?:currently|now)\s+(?:living\s+|based\s+)?in\s+{END}")
SELF_FROM = re.compile(rf"\b(?:i'm|im|i am)\s+(?:(?!(?:with|to|for|about|of|in|on|at|and|or|but|that|who|my|his|her|their|our|your|the|this|it|is|was|not|never|from|away|far|apart|miles?|mi|km|hours?|hrs|minutes?|mins?|drive|walk|days?|weeks?|months?|back|home|free|safe|different|done|off|out|coming|moved|relocated|transferred|graduated|returned|retired|escaped|fled|immigrated|emigrated|banned|removed|separated|divorced|exiled|kicked|evacuated|deported|isolated|disconnected|\w+ing)\b)[\w'/-]+,?\s+){{1,8}}?from\s+{END}")
TAG_FROM = re.compile(rf"(?:^|[\s(\[\]/|,-])(?:\d{{2}}|{PERSON})\s+from\s+{END}")
AGED_IN = re.compile(rf"(?:{TAG}|\b\d{{2}}[- ]?(?:years?[- ]old|yrs?[- ]old|yo|y/o)\b)(?:\s+(?!(?:for|looking|seeking|want|wants|need|needs|into|with|like|likes|love|loves|any|anyone|you|your|if|visiting|going|travel|traveling|travelling|staying|stuck|be|will)\b)[\w'-]+){{0,5}}\s+in\s+{END}")
ROLE = re.compile(rf"\b(?:i'm|im|i am)\s+an?\s+(?:(?!not\b|never\b)[\w-]+\s+){{1,4}}in\s+{END}")
STOP = re.compile(r"[.!?\n]")
OPENING = re.compile(r"(?:^|[.!?\n])[\s\"'*]*\Z")
AREA = re.compile(r"\s+(?:area|county)\b", re.I)
HOSTING = re.compile(rf"\b(?:hosting|can host|new)\s+(?:in|to)\s+{END}")
HAILS = re.compile(rf"(?:\bhere|\bthis side|\b\d{{2}} years|(?:^|[\n.!?]\s*)am|\bcpl|\bcouple)\s+from\s+{END}")
LOCATION = re.compile(r"(?:^|\n)[\W_]*(?:location|loc|based)[\W_]*[:=-][\W_]*\Z")
HOMETOWN = re.compile(r"\s*[,.(-]?\s*(?:(?:it's|its|it is|is|was)\s+)?my\s+(?:hometown|home town|birthplace)\b")
LIFE = re.compile(r"(?:,?\s+[a-z]+){0,2}?,?\s+(?:my|all my|for my) (?:entire |whole )?life\b")
AUTOMATED = re.compile(r"\bi am a bot\b|\bperformed automatically\b|\bplease (?:make sure|include)\b|\bpost (?:has been |was )?removed\b|\bmust (?:include|contain)\b")
REPOST = re.compile(r"(?:original (?:post|text)|copy of (?:your|the) post|backup of your post|post body)[^\n:]{0,30}:[*\s]*")
SUBJECTIVE = re.compile(r"\b(?:i|i'm|im|we|we're|me|as an?)\b")
CHAIN = re.compile(r"[\s,(:–—-]*(?:(?:more\s+)?specifically|namely|in|near|around|outside(?: of)?|just outside(?: of)?|close to)?[\s,(:–—-]*(?:the\s+)?")


BLOCK = r"(?!(?:not|never|no|half|part|partly|quarter|mixed|fan|big|huge|of|in|to|from|with|the|for|into|like|than|fluent|native|married|probably|maybe|ex|former|formerly|called)\b)(?!\w+ing\b)[\w'-]+ "
BRIEF = r"(?!(?:sorry|sure|pretty|glad|afraid|aware|against|about|any|some|every|on|at|over|so|very|not|never|no|half|part|partly|quarter|mixed|fan|big|huge|of|in|to|from|with|the|for|into|like|than|fluent|native|married|probably|maybe|ex|former|formerly|called)\b)(?!\w+ing\b)[\w'-]+ "
BELIEF = r"christian|muslim|jew|jewish|catholic|atheist|conservative|liberal|i|we|\w+ly"
SELF_NATION = rf"(?:\b{I}|(?:^|[.!?\n(]\s*)am) {ADVERB}(?:an? |a proud |a born and raised |proud(?:ly)? )?(?:{BLOCK}){{0,3}}?({NATION})(?: citizen| national)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|too|myself|citizen|national|here|living|who|born|by|from|in|as|lol|haha|though|btw|with|not|or|mate|bro|guy|girl|man|woman|dude|male|female|person|boy|lady|kid|teen|teenager|student|mom|mum|dad|father|mother|wife|husband|couple|family|redditor|resident|immigrant|expat|that|{BELIEF})\b)[a-z])"
AS_NATION = rf"(?:\bas (?:an?|another|a fellow) |(?:^|[.!?\n,]\s*|\bme )as (?=\w+,?\s+(?:i|i'm|im|we|myself)\b))({NATION})(?:[- ]born)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|myself|citizen|national|person|man|woman|guy|girl|dude|male|female|living|who|born|raised|here|in|from|it|there|that|by|expat|immigrant|veteran|mom|mother|dad|father|parent|voter|taxpayer|kid|child|adult|student|resident|native|lol|{BELIEF})\b)[a-z])"
LOOSE_NATION = rf"\b{I} {ADVERB}(?:an? |a proud |a born and raised |proud(?:ly)? )?(?:{BRIEF}){{0,3}}?({NATION})(?: citizen| national)?(?=$|[\s.,!;:)])(?!\s+(?:teacher|tutor|speaker|speaking|learner|major|lit|literature|class|course|translator|food|cuisine|company|restaurant|accent)\b)"
AS_VERBS = frozenset("known seen treated regarded described classified identified identify identifies disguised dressed dress posing pose poses pass passes passing passed count counts counted reincarnated reborn such same just much well so portrayed depicted cast labeled labelled viewed considered perceived recognized recognised registered mistaken mistook".split())
NOUNS = r"teacher|tutor|speaker|speaking|learner|major|lit|literature|class|course|translator|food|cuisine|company|restaurant|accent|dish|product|brand|movie|film|show|song|word|name|language|music|culture|history|government|team"
AS_FRAME = rf"\bas {''.join(f'(?<!{verb} as )' for verb in sorted(AS_VERBS))}(?:an? |a fellow )(?:{BRIEF}){{0,2}}?(?<!north )(?<!south )(?<!latin )(?<!central )(?<!great )({NATION})(?:[- ]born)?(?=$|[\s.,!;:)])(?!\s+(?:{NOUNS})s?\b)"
WE_FRAME = rf"\b(?:we|us)(?: (?:fellow|proud|all))? ({NATION})s?(?=$|[\s.,!;:)])(?!\s+(?:{NOUNS})s?\b)|\bwe're (?:all |both )?({NATION})(?=$|[\s.,!;:)])|\bproud to be (?:an? )?({NATION})(?=$|[\s.,!;:)])"
AGE_FRAME = rf"(?<![\w.$#'/:+-])\d\d(?<!my \d\d)(?<!a \d\d)(?<!an \d\d)(?<!the \d\d)(?<!her \d\d)(?<!his \d\d)(?<!our \d\d)[- ]?(?:years?[- ]old|yrs?[- ]old|yo|y/o)[\s,-]+(?:{BRIEF}){{0,2}}?({NATION})(?=$|[\s.,!;:)])"
HELD_FRAME = rf"\b(?:my|have|hold|holding|got|own)\s+(?:an?\s+|dual\s+)?({NATION})\s+(?:passport|citizenship)\b|\bdual (?:citizenship|nationality|citizen|national)s?\s*[:,(-]?\s*({NATION})\b"
WIDE_START = re.compile(r"(?:^|[\n.!?,;(:—–/-]\s*|\b(?:also|fellow|another|a|an|proud|dual|half)\s+)\Z")
WIDE_HERE = re.compile(r",?\s+here\b(?!\s+(?:is|are|was|were|in|on|at|for|to|from|of)\b)")
FRAMES = [re.compile(frame) for frame in (AS_FRAME, WE_FRAME, AGE_FRAME, HELD_FRAME)]
SPOKEN = (rf"\b{I} {ADVERB}(?:an? |a proud |a born and raised |proud(?:ly)? )?({NATION})(?: citizen| national)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|too|myself|citizen|national|here|living|who|born|by|from|in|as|lol|haha|though|btw|with|not|or|mate|bro|guy|girl|man|woman|dude|male|female|person)\b)[a-z])"
          rf"|\bas (?:an?|another|a fellow) ({NATION})(?:[- ]born)?(?=$|[\s.,!;:)])(?!\s+(?!(?:and|but|so|myself|citizen|national|person|man|woman|guy|girl|dude|male|female|living|who|born|raised|here|in|from|i|we|it|there|that|by|expat|immigrant|veteran|mom|mother|dad|father|parent|voter|taxpayer|kid|child|adult|student|resident|native|lol)\b)[a-z])")


def spoken(word):
    return word if word in LANGUAGES else None


RULES = [
    rule("nationality", rf"{LOOSE_NATION}|{SELF_NATION}", lambda match: NATIONS.get(match.group(1) or match.group(2))),
    rule("nationality", AS_NATION, lambda match: NATIONS.get(match.group(1))),
    rule("native_language", SPOKEN, lambda match: spoken(match.group(1) or match.group(2))),
    rule("native_language", r"\b(?:my )?(?:first|native|mother) (?:language|tongue) is \**(\w+)\b|\b(\w+)\** is my (?:first|native|mother) (?:language|tongue)\b|\b(?:i'm|im|i am|as) (?:also |actually )?(?:an? )?native \**(\w+)\** speaker\b|\bnative \**(\w+)\** speaker here\b|\b(?:i'm|im|i am|as) an? native speaker of \**(\w+)\b|\b(\w+)\**\s*\(native\)|\bnative(?: language)?\s*[:=-]\s*\**(\w+)\b",
         lambda match: spoken(next(filter(None, match.groups())))),
    rule("native_language", r"\b(\w+) is the only language i (?:speak|know)\b|\bas (?:a )?native (\w+ )?speakers?\b", lambda match: spoken(match.group(1)) if match.group(1) else spoken(match.group(2).strip()) if match.group(2) else "english", SELF_HEDGE),
]


def fits(entry, text, start, end):
    if entry[4] == "code":
        return text[start:end].isupper() and any(letter.islower() for letter in text[max(0, start - 30):end + 30])
    if entry[4] == "town" and text[start:end].isupper():
        return False
    if entry[4] in ("1", "town"):
        return text[start].isupper() and any(letter.islower() for letter in text[max(0, start - 30):end + 30]) and not OPENING.search(text, 0, start) and not AREA.match(text, end)
    return True


def longest(words, index, lowered):
    for size in range(min(FIRST.get(words[index][2], 0), len(words) - index), 0, -1):
        span = words[index:index + size]
        if all(GAP.fullmatch(lowered, left[1], right[0]) for left, right in zip(span, span[1:])) and (entry := LEXICON.get(" ".join(word for _, _, word in span))):
            return size, entry
    return 0, None


def mentions(text, lowered):
    words = [(match.start(), match.end(), match.group()) for match in TOKEN.finditer(lowered)]
    spots = []
    index = 0
    while index < len(words):
        size, entry = longest(words, index, lowered)
        start = words[index][0]
        if not entry and start and lowered[start - 1] == "#" and (entry := SQUASHED.get(words[index][2])):
            size = 1
        end = words[index + size - 1][1] if entry else 0
        if entry and fits(entry, text, start, end):
            if spots and entry[0] in ("region", "country") and spots[-1][2][0] in ("city", "region") and JOIN.fullmatch(lowered, spots[-1][1], start) and (joined := within(spots[-1][2], entry)):
                spots[-1][1:] = [end, joined]
            elif spots and spots[-1][2][0] == "country" and entry[0] in ("city", "region") and entry[3] == spots[-1][2][3] and JOIN.fullmatch(lowered, spots[-1][1], start):
                spots[-1][1:] = [end, (entry[0], entry[1], entry[2] if entry[0] == "region" else "", entry[3], entry[4])]
            else:
                spots.append([start, end, entry])
            index += size
        else:
            index += 1
    return spots


def within(head, container):
    kind, value, region, country, flag = head
    if container[0] == "region" and kind == "city":
        return kind, value, container[1], container[3], ""
    if container[0] == "country":
        return head if country == container[3] else (kind, value, region if kind == "region" else "", container[3], flag)
    return None


def asked(lowered, end):
    stop = STOP.search(lowered, end)
    return bool(stop) and stop.group() == "?" and stop.start() - end < 60 and not re.search(r"[,;]", lowered[end:stop.start()])


def hedged(lowered, opening, start, end):
    return bool(HEDGE.search(lowered, clause(lowered, opening), opening)) or asked(lowered, end)


def stance(lowered, start, end, entry):
    opening = max(clause(lowered, start) - 1, start - 90, 0)
    for pattern, kind in ((LIVE, "residence"), (BARE, "residence"), (HERE, "local"), (ABROAD, "local"), (GERMAN, "aus"), (BEING, "being"), (FROM, "from"), (LEFT, "from"), (ORIGIN, "origin"), (ROLE, "being"), (AGED_IN, "being"), (SELF_FROM, "from"), (MOVED, "residence")):
        if match := pattern.search(lowered, max(start - 60, 0) if pattern is HERE else max(lowered.rfind("\n", 0, start) + 1, start - 70) if pattern is AGED_IN else opening, start):
            if hedged(lowered, match.start(), start, end):
                return None
            if kind == "being":
                return None if LATER.match(lowered, end) else "residence"
            return kind
    line = lowered.rfind("\n", 0, start) + 1
    if (match := TAG_FROM.search(lowered, line, start)) and TITLE.search(lowered, line, match.start() + 1) and not ASKING.search(lowered, line, match.start()) and not hedged(lowered, match.start(), start, end):
        return "from"
    if (match := LOOSE.search(lowered, opening, start)) and SUBJECTIVE.search(lowered, max(lowered.rfind(mark, 0, start) for mark in ".!?\n") + 1, match.start()):
        return None if hedged(lowered, match.start(), start, end) else "residence"
    if START.search(lowered, max(0, start - 12), start) and HERE_AFTER.match(lowered, end):
        return "here"
    if lowered.startswith(("-based", " based"), end) and SELF.search(lowered, max(0, start - 20), start):
        return "residence"
    if (local := re.match(r"\s+(native|local|resident)\b", lowered[end:end + 12])) and re.search(rf"\b(?:i'm|im|i am|as|am)\s+an?\s+{ADVERB}(?:(?:{'|'.join(DIRECTIONS)})\s+)?\Z", lowered[max(0, start - 40):start]):
        return "origin" if local.group(1) == "native" else "residence"
    if HOMETOWN.match(lowered, end):
        return "origin"
    if lowered.startswith(("-born", " born"), end) and BORN.search(lowered, max(0, start - 20), start) or lowered.startswith((" ass ", " self "), end) and lowered.endswith("my ", 0, start):
        return "born"
    if re.match(r"\.?\s+(?:citizen|national|passport holder)s?\b", lowered[end:end + 20]) and CITIZEN.search(lowered, max(0, start - 30), start):
        return "citizen"
    return None


def titled(text, lowered, start, end, entry):
    opening, closing = lowered.rfind("\n", 0, start) + 1, (lowered.find("\n", end) + 1 or len(lowered) + 1) - 1
    if closing - opening >= 250 or not TITLE.search(lowered, opening, closing):
        return False
    if lowered[start - 1:start] == "#":
        return True
    asking = ASKING.search(lowered, opening, start)
    if entry[4] == "1" and not (" " in text[start:end] and text[start:end].istitle()) or asking and (entry[0] == "country" or entry[4] == "1" or ASKING.search(lowered, max([opening] + [tag.end() for tag in TITLE.finditer(lowered, opening, start)]), start)):
        return False
    last = LAST.match(lowered, end, closing)
    if entry[4] == "1":
        return bool(LEAD.search(lowered, opening, start) or last)
    if not (LEAD.search(lowered, opening, start) or last):
        return "loose" if opening == 0 and entry[0] != "country" and text[start].isupper() and end - start >= 5 else False
    if entry[0] == "city" and " " not in lowered[start:end] and text[start].islower() and not (NEAR.search(lowered, max(0, start - 8), start) or TAG_LEAD.search(lowered, opening, start)):
        return "loose" if last else "bare"
    return "loose" if asking else True


def places(text, lowered, found):
    for key in [key for key in found if key[0] == "nationality"]:
        found.setdefault(("origin_country", key[1]), found[key])
    if AUTOMATED.search(lowered):
        if not (copy := REPOST.search(lowered)):
            return
        stop = AUTOMATED.search(lowered, copy.end())
        cut = slice(copy.end(), stop.start() if stop else None)
        text, lowered = text[cut], lowered[cut]
    spots = mentions(text, lowered)
    if not spots:
        return
    line_end = lowered.find("\n") % (len(lowered) + 1)
    tagged = line_end < 150 and bool(TITLE.search(lowered, 0, line_end))
    residence, fallback, framed = [], [], []
    for start, end, entry in spots:
        if entry[4] == "town":
            kind = stance(lowered, start, end, entry) if TOWN_LEAD.search(lowered, max(0, start - 30), start) else None
            if kind in ("residence", "local") or kind is None and TAG_LEAD.search(lowered, lowered.rfind("\n", 0, start) + 1, start) and titled(text, lowered, start, end, entry) is True:
                residence.append(((*entry[:2], "", *entry[3:]), end, False))
            elif kind in ("from", "origin", "born"):
                found.setdefault(("origin_city", entry[1]), end)
            continue
        kind = stance(lowered, start, end, entry)
        if entry[0] == "nation":
            if kind is None and WIDE_START.search(lowered, max(0, start - 12), start) and WIDE_HERE.match(lowered, end):
                framed.append((("nationality", entry[3]), start))
            nation(lowered, start, end, entry, kind, line_end, tagged, found)
            continue
        if entry[0] == "people":
            if kind == "here" or PEOPLE.search(lowered, max(0, start - 30), start):
                placed("origin", ("region", *entry[1:]), end, found)
                found.setdefault(("nationality", entry[3]), start)
                fallback.append((("region", *entry[1:]), end, False))
            continue
        if kind in ("here", "aus") and entry[0] == "country":
            found.setdefault(("nationality", entry[3]), start)
        if kind == "aus" and entry[0] == "country":
            found.setdefault(("origin_country", entry[3]), start)
        title = kind is None and titled(text, lowered, start, end, entry)
        foreign = entry[3] not in TITLE_REGIONS
        if foreign and entry[0] == "city" and not text[start].isupper():
            continue
        if foreign and (entry[0] == "region" or title == "loose"):
            title = False
        if title and entry[0] == "country":
            found.setdefault(("nationality", entry[3]), start)
        if kind is None and residence and residence[-1][0][3] == entry[3] and CHAIN.fullmatch(lowered, residence[-1][1], start):
            kind = "residence"
        if kind is None and not title and entry[0] == "city" and (host := HOSTING.search(lowered, max(0, start - 20), start)) and not hedged(lowered, host.start(), start, end) and not LATER.match(lowered, end):
            kind = "here"
        if kind is None and not title and entry[0] == "region" and LOCATION.search(lowered, max(0, start - 30), start):
            kind = "residence"
        if kind is None and entry[0] == "city" and (other := HAILS.search(lowered, max(0, start - 30), start)) and not hedged(lowered, other.start(), start, end) and not LATER.match(lowered, end):
            found.setdefault(("origin_city", entry[1]), end)
        if kind == "residence" and LIFE.match(lowered, end):
            placed("origin", entry, end, found)
        if foreign and entry[0] == "region" and kind in ("residence", "local"):
            continue
        if kind == "here" and entry[0] == "city":
            entry = (*entry[:2], "", *entry[3:])
        if title == "bare":
            entry = (*entry[:2], "", *entry[3:])
        if kind in ("residence", "aus", "local") or kind == "here" and entry[4] != "1" or kind is None and title:
            residence.append((entry, end, entry[0] == "country" or title not in ("loose", "bare") and kind != "aus" and not (title and foreign)))
        elif kind == "from":
            placed("origin", entry, end, found, entry[0] == "country" or not foreign)
            if entry[0] == "country":
                found.setdefault(("nationality", entry[3]), start)
            fallback.append((entry, end, entry[0] == "country" or not foreign))
        elif kind in ("origin", "born"):
            placed("origin", entry, end, found)
            if kind == "born" and entry[0] == "country":
                found.setdefault(("nationality", entry[3]), start)
        elif kind == "citizen" and entry[0] == "country":
            found.setdefault(("nationality", entry[3]), start)
    for entry, end, whole in residence or fallback[:1]:
        placed("residence", entry, end, found, whole)
    if not any(attribute == "residence_country" for attribute, _ in found) and len(nations := [key for key in found if key[0] == "nationality"]) == 1:
        found.setdefault(("residence_country", nations[0][1]), found[nations[0]])
    for frame in FRAMES:
        for match in frame.finditer(lowered):
            if not qualified(lowered, match.start(), match.end()) and (country := NATIONS.get(next(filter(None, match.groups())))):
                framed.append((("nationality", country), match.start()))
    for key, position in framed:
        found.setdefault(key, position)


def nation(lowered, start, end, entry, kind, line_end, tagged, found):
    country = entry[3]
    if kind == "here":
        found.setdefault(("nationality", country), start)
        found.setdefault(("origin_country", country), start)
        found.setdefault(("residence_country", country), start)
    elif kind == "born":
        found.setdefault(("origin_country", country), start)
        found.setdefault(("nationality", country), start)
    elif kind == "citizen":
        found.setdefault(("nationality", country), start)
    elif tagged and start < line_end and not ASKING.search(lowered, 0, start):
        found.setdefault(("nationality", country), start)
        found.setdefault(("origin_country", country), start)


def placed(prefix, entry, end, found, whole=True):
    kind, value, region, country, _ = entry
    if kind == "city":
        found.setdefault((f"{prefix}_city", value), end)
    if kind in ("city", "region") and region and (kind == "region" and prefix == "residence" or country != "united kingdom") and not (kind == "city" and (ADMINISTRATIVE.search(region) or prefix == "residence" and country not in FEDERAL and region != value)):
        found.setdefault((f"{prefix}_region", region), end)
    if whole:
        found.setdefault((f"{prefix}_country", country), end)
