use crate::cues::{cues_of, Cues, MASKS};
use crate::lexicon::{self, *};
use claimcore::*;
use claimcore::schema::fan_value;
use rustc_hash::{FxHashMap, FxHashSet};
use std::sync::LazyLock;

pub const NAME: &str = r"((?:[Tt]he )?[A-Z0-9][\w'&.:!+-]*(?:,? (?:of|the|and|&|de|la|le|vs\.?|in|on|a|to|[A-Z0-9][\w'&.:!+-]*)){0,6})";
const DEGREE: &str = r"(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted|avid|hardcore|crazy|super|major|total|self[- ](?:admitted|proclaimed|confessed|described))";
const PERSON: &str = r"((?:[A-Z]\. |[A-Z][\w-]*(?:'[A-Z][\w-]*)? ){1,3}[A-Z][\w-]*(?:'[A-Z][\w-]*)?)(?![\w-])";

const KINDS: &[(&str, &str)] = &[("band", "artist"), ("artist", "artist"), ("singer", "artist"), ("rapper", "artist"), ("musician", "artist"), ("group", "artist"), ("musical artist", "artist"), ("composer", "artist"),
    ("show", "franchise"), ("tv show", "franchise"), ("series", "franchise"), ("anime", "franchise"), ("manga", "franchise"), ("movie", "franchise"), ("film", "franchise"),
    ("franchise", "franchise"), ("book series", "franchise"), ("cartoon", "franchise"), ("sitcom", "franchise"), ("comic", "franchise"), ("game", "video_game"), ("video game", "video_game"),
    ("videogame", "video_game"), ("book", "franchise"), ("novel", "franchise"), ("author", "author"), ("writer", "author"), ("team", "sports_team"), ("club", "sports_team"),
    ("player", "athlete"), ("athlete", "athlete"), ("driver", "athlete"), ("fighter", "athlete"), ("wrestler", "athlete"), ("character", "character"), ("pokemon", "character"),
    ("hero", "character"), ("villain", "character"), ("champion", "character"), ("streamer", "creator"), ("youtuber", "creator"), ("podcast", "creator"), ("podcaster", "creator"),
    ("creator", "creator"), ("actor", "celebrity"), ("actress", "celebrity"), ("comedian", "celebrity"), ("celebrity", "celebrity")];

const OBJECTS: &[(&str, &str)] = &[("music", "artist"), ("songs", "artist"), ("song", "artist"), ("album", "artist"), ("albums", "artist"), ("voice", "artist"), ("vocals", "artist"), ("lyrics", "artist"), ("art", "artist"),
    ("artwork", "artist"), ("movies", "celebrity"), ("films", "celebrity"), ("acting", "celebrity"), ("performance", "celebrity"), ("performances", "celebrity"), ("roles", "celebrity"),
    ("comedy", "celebrity"), ("standup", "celebrity"), ("specials", "celebrity"), ("videos", "creator"), ("video", "creator"), ("streams", "creator"), ("stream", "creator"),
    ("channel", "creator"), ("content", "creator"), ("podcast", "creator"), ("books", "author"), ("novels", "author"), ("writing", "author"), ("prose", "author")];

pub const COMMON_WORDS: &str = "i i'm im i've i'd i'll it it's its the this that these those my me mine we our you your he she they them his her their a an and but or so if when what why how where who which \
yes no yeah yep nope ok okay lol lmao omg oh hey hi hello thanks thank also just honestly literally well not then there here now today tomorrow yesterday \
love loved great best good amazing awesome edit update tldr tl;dr op reddit google youtube god jesus christmas monday tuesday wednesday thursday friday saturday \
sunday january february march april may june july august september october november december english american nta yta esh nah imo imho idk tbh btw \
definitely probably maybe sure same agreed true right wow damn dude bro man guys please sorry what's that's there's";
const EDGE_WORDS: &str = "since in on as about both because at for with from by during after before like all just really again still too ever even when while if than then so but or and of to \
into onto over under through every each some any much many more most very only also already almost around against without within across";
const GENERIC_WORDS: &str = "it this that these those him her them you me my your his their our how when being having to a an some any all every everything anything something nothing games game gaming music songs song anime \
shows show movies movie films film books book reading watching playing food sex cock dick pussy ass porn people men women guys girls kids dogs cats animals life it's them. \
him. you. that. this. here there out up down so very much more most doing going getting seeing playing talking working";

const PRONOUNS: [&str; 13] = ["i", "i'm", "im", "i've", "i'd", "i'll", "me", "my", "you", "we", "he", "she", "they"];
const PEOPLE: [&str; 6] = ["character", "artist", "athlete", "celebrity", "creator", "author"];
const ALL_OPTIONS: [&str; 8] = ["character", "artist", "athlete", "celebrity", "creator", "author", "franchise", "video_game"];
const UNPRAISED: [&str; 3] = ["athlete", "celebrity", "author"];
const NAMED_ONLY: [&str; 3] = ["character", "athlete", "celebrity"];
const CRUSHED: [&str; 4] = ["character", "athlete", "celebrity", "artist"];
const SPELLED: [&str; 4] = ["athlete", "celebrity", "author", "creator"];
const GATED: [&str; 2] = ["artist", "author"];
const LISTS: [&str; 3] = ["artist", "franchise", "video_game"];
const LIKABLE: [&str; 2] = ["artist", "franchise"];
const LOOSE: [&str; 1] = ["video_game"];
const SHOWN: [&str; 2] = ["franchise", "video_game"];
const BOOKISH: [&str; 9] = ["author", "novel", "writ", "wrote", "book", "read", "series", "trilogy", "saga"];
const ANSWERED: [&str; 4] = ["athlete", "creator", "celebrity", "artist"];
const CHEERED: [&str; 2] = ["celebrity", "creator"];
const PLAYED: [&str; 2] = ["video_game", "artist"];
const RUN: usize = 3;
const WINDOW: usize = 150;
pub const CONTEXT_KINDS: [&str; 8] = ["video_game", "franchise", "artist", "character", "author", "creator", "athlete", "celebrity"];

fn word_set(words: &'static str) -> FxHashSet<&'static str> {
    words.split_whitespace().collect()
}

pub static COMMON: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(COMMON_WORDS));
static EDGE: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(EDGE_WORDS));
static GENERIC: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(GENERIC_WORDS));

fn py_escape(word: &str) -> String {
    let mut out = String::new();
    for c in word.chars() {
        if "()[]{}?*+-|^$\\.&~# \t\n\r\u{b}\u{c}".contains(c) {
            out.push('\\');
        }
        out.push(c);
    }
    out
}

static KIND_WORDS: LazyLock<String> = LazyLock::new(|| {
    let mut words: Vec<String> = KINDS.iter().filter(|(k, _)| !k.is_empty()).map(|(k, _)| py_escape(k)).collect();
    words.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    words.join("|")
});

fn kind_of(word: &str) -> Option<&'static str> {
    KINDS.iter().find(|(k, _)| *k == word).map(|(_, v)| *v)
}

macro_rules! re {
    ($name:ident, $pat:expr) => {
        pub static $name: LazyLock<Re> = LazyLock::new(|| Re::new(&$pat));
    };
}

re!(TRAILING, r"(?:\s+(?:of|the|and|&|de|la|le|vs\.?|in|on|a|to))+$|[\s,.:!]+$");
re!(FAVORITE, { let kind_words = &*KIND_WORDS; format!(r"(?i:\b(?:one of )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|favs) ({kind_words})s?(?: of all time| ever| right now| atm| at the moment)? (?:is|has to be|would be|would have to be|was always|remains|are)\s+){NAME}") });
re!(FAVORED, { let kind_words = &*KIND_WORDS; format!(r"{NAME}(?i: (?:is|are|was|has always been|have always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?(?:one of )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)s?(?: ({kind_words})s?)?\b)") });
re!(POSITIVE, concat!(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |seriously |genuinely |do |personally )?(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig|recommend|second|rewatched|replayed)\b|",
    r"\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big )?fan of|hooked on|in love with)\b|\bcan'?t get enough of\b|",
    r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rites?|faves?|favs?)\b|\bfell in love with\b|",
    r"\b(?:is|are|was|were) (?:so |really |very |absolutely |just |still |honestly |such an? |pretty |easily |definitely |by far )?(?:good|great|amazing|awesome|excellent|fantastic|",
    r"underrated|underappreciated|goated|incredible|perfect|beautiful|fun|peak|fire|the goat|the best|my jam|a banger|bangers|a masterpiece|a classic|brilliant|",
    r"phenomenal|gorgeous|lovely|wonderful|so fun)\b|\b(?:been|currently|finally|started) (?:playing|watching|listening to|reading|bingeing|binging|replaying|rewatching)\b|",
    r"\bfor me\b|\bmine is\b|\bhands down\b|\bthe goat\b|\bi'?m (?:playing|watching|listening to|reading|replaying|rewatching)\b)"));
re!(NEGATIVE, r"(?i:\b(?:hate|hated|don'?t like|didn'?t like|not a fan|dislike|overrated|boring|worst|trash|garbage|sucks|terrible|awful|meh|never (?:played|watched|liked))\b)");
re!(CANDIDATE, r#"(?<![\w'])((?:[A-Z][\w'&:.!+-]*|\d+[a-z]*)(?: (?:of|the|and|&|de|la|vs\.?|in|on|a|to|no|[A-Z0-9][\w'&:.!+-]*))*)|["“]([^"”\n]{2,40})["”]"#);
re!(SENTENCE, r"[^.!?\n]+[.!?]*");
re!(CODE, r"[\d\W]*\w?\d[\w-]*");
re!(ADJACENT, concat!(r"\b(?:i (?:really |absolutely |just |also |still |honestly |do |genuinely )?(?:love|loved|adore|adored|enjoy|enjoyed)|obsessed with|addicted to|can'?t get enough of|a (?:huge |big |massive )?fan of|in love with|hooked on|",
    r"my (?:all[- ]time |absolute |personal )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|has to be|would be|was)|i'?m (?:currently |still |also )?(?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging)|",
    r"i'?ve been (?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging|obsessed with)|i (?:just )?(?:finished|beat|started) (?:playing |watching |reading )?|i (?:still |also |mostly |mainly |usually |really )?(?:play|played|replayed|rewatched))\s+",
    r"((?:the )?[\w'&:.!+-]+(?: [\w'&:.!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|it|is|was|lol|too|again|right|atm|lately|recently|these|since|for|with|on|in|at|when|while|haha|tbh|honestly|now|today)\b)"));
re!(FAN_CUE, r"(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)");
re!(GOATED_CUE, r"(?i: (?:the|my) goat\b)");
re!(FAN, format!(r"(?i:\b(?:i'm|im|i am|i was|i've been|ive been|been|as|being|become|became|becoming|grew up|growing up|raised) )(?:(?i:an? )(?:(?i:{DEGREE}) |(?!(?:not|never|no|an?|the|by|of|to) )[a-z][a-z'-]* ){{0,3}}|(?:(?i:{DEGREE}) ){{0,3}}){NAME}(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)"));
re!(TEAM_FAN, format!(concat!(r"(?i:\b(?:(?:i'm|im|i am|i was|i've been|ive been|been|as|being|from|become|became|becoming|grew up|growing up|raised|als) |(?:fellow|{DEGREE}) ))(?:(?i:an? )(?:(?i:{DEGREE}) |(?!(?:not|never|no|an?|the|by|of|to) )[a-z][a-z'-]* ){{0,3}}|(?:(?i:{DEGREE}) ){{0,3}}){NAME}(?i: (?:fan|supporter)s?\b)|",
    r"(?:(?m:^)|(?<=[.!?] ))(?:[^\W\d_][\w'-]* ){{0,2}}?{NAME}(?i: (?:fan|supporter)(?:s? (?:here|since|for life|all my life|my whole life|through and through|lol|lmao|haha|tbh|btw|myself)\b|(?=[,.!;:]|(?m:$))))"), DEGREE = DEGREE, NAME = NAME));
re!(OWN_TEAM, format!(r"{NAME}(?i: (?:is|are|was|were|has always been|have always been|will always be) (?:still |definitely |always |forever )?my (?:home |hometown |local |second |other |first |main |real |true |only )?team\b)|(?i:\bmy (?:home |hometown |local |second |other |first |main |real |true |only )?team (?:is|are|was|has always been|will always be) (?:still |always |forever )?(?:the )?){NAME}"));
re!(FAN_OF, format!(r"(?i:\b(?:i'm|im|i am|i was|i've been|ive been|i've always been|been|as) (?:also |still |definitely |honestly |really |such |always )?(?:an? |the )?(?:{DEGREE} )*(?:fan|supporter|admirer) of (?:the )?){NAME}"));
re!(STAN, format!(r"(?i:\bi (?:also |still |will always |literally |really )?stan ){NAME}"));
re!(GOAT, format!(r"(?i:\bmy (?:all[- ]time )?goat:? ){NAME}"));
re!(GOATED, format!(r"{NAME}(?i: (?:is|was|will always be|remains) (?:still |easily |honestly )?(?:the|my) goat\b| the goat\b)"));
re!(LOVED, format!(concat!(r"(?i:\bi(?:'m| am)? (?:really |absolutely |just |also |still |honestly |genuinely |do |totally |fucking |friggin |freaking |freakin |fricking |effing |actually |so |personally |\w+ly )*",
    r"(?:love|adore|loved|adored|enjoy|enjoyed|in love with|obsessed with) ){NAME}"), NAME = NAME));
re!(DROPPED, format!(r"(?:(?m:^)|(?<=[.!?] ))(?i:(?:really |absolutely |just |also |still |honestly |genuinely |totally |so |\w+ly )*(?:love|adore|loved|adored) ){NAME}"));
re!(CRUSH, format!(r"(?i:\bcrush(?:es)? on ){NAME}"));
re!(LOWER_FAN, format!(r"(?i:\b(?:i'm|im|i am|i've been|ive been|as|being) (?:an? )?(?:{DEGREE} )*)((?:[a-z][\w'-]* ){{0,2}}[a-z][\w'-]*) (?:fan|stan|supporter)\b"));
re!(LIKED_PERSON, format!(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |genuinely |do |totally |personally |kinda |always |actually |\w+ly )*(?:like|liked) ){NAME}"));
re!(CREATED, format!(r"{NAME}(?:(?:'s|s'|’s) |(?<!'s)(?= (?i:youtube|yt|twitch|tiktok) ))(?i:(?: ?(?:youtube|yt|twitch|tiktok) )?(?:new |latest |recent |old |last |early )?(?:videos?|vids|streams?|vods?|channel|podcasts?|content|vlogs?)\b)"));
re!(WATCHED, format!(r"(?i:\b(?:i (?:\w+ )?(?:watch|watching|watched)|subscribed to|i follow|i'?ve been following) ){NAME}(?i: (?:on|'s) (?:youtube|twitch|tiktok|kick)\b)"));
re!(LISTENED, format!(r"(?i:\b(?:i(?:'m| am|'ve been| have been)? (?:\w+ )?(?:listening to|listen to|listened to|jamming to|bumping)|been (?:listening to|bumping|jamming to)) ){NAME}"));
re!(ALBUM, format!(r"{NAME}(?:'s|s'|’s) (?i:(?:new |latest |last |debut |first |second |third |next |old |early )?(?:albums?|songs?|singles?|discography|tour|concerts?|records?|ep|lp|music|vocals|lyrics)\b)"));
re!(SEEN, format!(r"(?i:\b(?:i|we) (?:\w+ )?(?:saw|seen|see|seeing) ){NAME}(?i: (?:live|in concert|perform|play live|open for)\b)"));
re!(PRAISED, format!(concat!(r"(?:(?m:^)|(?<=[.!?] )){NAME}(?i: (?:is|was|are|were|has been|remains) (?:still |so |fucking |really |honestly |just |literally |absolutely |easily |genuinely |lowkey )*",
    r"(?:peak|goated|amazing|incredible|underrated|phenomenal|a masterpiece|a banger|fire|elite|god ?tier|top tier|the goat|the best\b|one of the best)\b)"), NAME = NAME));
re!(FAVORITE_PLAIN, { let kind_words = &*KIND_WORDS; format!(r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav) ({kind_words})s? (?:is|has to be|would be|was|are)\s+")
    + r"((?:the )?[\w'&:!+-]+(?: [\w'&:!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|lol|too|tbh|honestly|by far|hands down|of all time|ever|for sure)\b)" });
re!(ANYTHING, format!(r"(?i:\b(?:anything|everything)(?: (?:else|ever|written|sung|made|done|released|recorded|produced|published))* (?:by|from) ){NAME}"));
re!(WRITTEN_BY, format!(r"(?<!read )\bby {PERSON}"));
re!(BLANK, r"\n[^\S\n]*\n");
re!(ADVISED, r"(?i:\b(?:recommend\w*|suggest\w*|advise|try|check out)\b)");
re!(WROTE, format!(r"{PERSON}(?:'s|s') (?:[\w:'-]+ ){{0,6}}?(?i:books?|novels?|series|trilogy|saga|writing)\b|(?i:\b(?:read|reading|finished|love|loved|enjoy|enjoyed)\b (?:\w+ ){{0,3}}){PERSON}(?i: (?:books|novels)\b)"));
re!(CHOICE, r"\^\((?:My choice|Me|Chose|My pick): ([^)|\n]{2,60}?)\s*[)|]");
re!(SPLIT, r"\s*(?:,|/|&|\band\b)\s*");
re!(POSSESSIVE, r"'s\b.*$");
re!(STOP, r"[.!?:;]\s");
re!(LISTED, r"[\s,;/&*|>()\[\]^:.\d-]{1,12}|\s*(?:,\s*)?(?:and|or)\s+");
re!(ANSWER, r"(?i:(?:(i'?d say|i'?d go with|i go with|easily|definitely|probably|obviously|prob|has to be|gotta be|got to be|clearly|always|me|mine|mine is|for me) )?(.+?)(,? (?:for me|for sure|defo|definitely|easily|100%|hands down|all day|obviously|by far|for now|all the way|of course|forever|always|imo|tbh|no question|no doubt|is the goat|my goat|the goat))?)");
re!(HEADERS, r"(?:\s*\n|[*_#>\s]*\*[^*\n]+\*[*_ \t]*\n|[ \t]*(?:!\[[^\]\n]*\]\([^)\n]*\)|https?://\S+)[ \t]*\n)*+");
re!(MEDIA, r"(?:\s*\n[ \t]*(?:!\[[^\]\n]*\]\([^)\n]*\)|https?://\S+)[ \t]*)+$");
re!(RIM, r"[\W_]+");
re!(LIKED, r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |genuinely |do |personally |fucking )*(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig)|\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big |massive )?fan of|hooked on|in love with)|\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|are|was|has to be))(?: the)?\s+$");
re!(SELF, r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)");
re!(PRODROP, r"[\W_]*(?i:(?:still|currently|just|finally|also|now|recently|been|really|absolutely|honestly) )*(?i:(love|loved|loving|enjoyed|enjoying|digging)|playing|played|replaying|replayed|finished|finishing|watching|watched|rewatching|rewatched|reading|rereading|listening to|listened to|started|bought)\b");
re!(BACKING, r"(?i:\b(?:my|our|we|us|go|let'?s go|lets go|up the|c'?mon|come on|i (?:always |still |also |really |just |will always |have always |\w+ly )?(?:love|like|liked|support|supported|root for|rooted for|cheer for|follow|followed)|i'?ve (?:always |also )?(?:supported|followed|rooted for)|fan of|rooting for|cheering for|supporter of|supporting|following)(?: the| my| our| beloved| boys)?\s*$)");
re!(BACKER, r"(?i:\s*(?:nation|faithful|for life|forever|till i die|all the way)\b)");
re!(SEASON, r"\s+(?:baseball|football|hockey|basketball|soccer|games?|season|gameday|matches|match)\b");
re!(ATTENDED, r"\b(?:watch|watched|watching|went|go|going|been to|attend|attended|attending|tickets?|seats?)\b");
re!(FANNED, r"(?i:\s*(?:fan|supporter)\b)");
re!(AVOWED, r"(?i:\b(?:i'?m|i am|as|been|being|be)\b[\w\s-]{0,20}$)");
re!(OWNED, r"(?:my|our|we|us)\b");
re!(PEER, r"(?i:\b(?:he|she|they|his|her|their|dad|mom|father|mother|brother|sister|wife|husband|son|daughter|friend|friends|boyfriend|girlfriend|partner|people|everyone|nobody|every)\b)");
re!(FAVOURED, r"(?i:fav(?<!least fav)(?<!\wfav)(?:ou?rites?|es?|s)?\b[^\n:]*:|\^\(likes?:)");

const CONTEXT_SOURCES: [&str; 8] = [
    r"(?i:\b(?:games?|gaming|gamer|play|played|playing|playthrough|steam|xbox|playstation|ps[1-5]|switch|nintendo|console|dlc|boss|bosses|speedrun|multiplayer|co-?op|rpg|jrpg|mmo|mmorpg|fps|roguelike|patch|grind|raid|quest|controller|remake|remaster|sequel|campaign|achievements?|platinum)\b)",
    r"(?i:\b(?:show|shows|series|season|seasons|episode|episodes|anime|manga|movie|movies|film|films|watch|watched|watching|rewatch|rewatching|binge|tv|netflix|hbo|disney|sitcom|cartoon|comic|comics|trilogy|franchise|novel|novels|books?)\b)",
    r"(?i:\b(?:songs?|albums?|band|bands|music|concerts?|tour|listen|listened|listening|tracks?|singer|rapper|vinyl|ep|lp|spotify|lyrics|discography|gig|setlist|live show|banger|bangers|vocals|guitarist|drummer)\b)",
    r"(?i:\b(?:character|characters|main|maining|mains|waifu|husbando|ship|shipped|arc|villain|protagonist|cosplay|pokemon|pokémon|hero|heroes|champion|skin)\b)",
    r"(?i:\b(?:author|authors|novelist|writer)\b)",
    r"(?i:\b(?:streamer|streamers|streams|streaming|twitch|youtube|youtuber|youtubers|vtuber|tiktok|tiktoker|channel|subscribed|subscribers|podcast|podcasts|podcaster|vlogs?|vods?)\b)",
    concat!(r"(?i:\b(?:nba|nfl|mlb|nhl|epl|premier league|champions league|la liga|serie a|bundesliga|ipl|cricket|football|soccer|basketball|baseball|hockey|rugby|tennis|golf|f1|",
        r"formula 1|ufc|mma|boxing|wrestling|striker|midfielder|defender|goalie|goalkeeper|quarterback|qb|pitcher|playoffs|super bowl|world cup|stanley cup|mvp|",
        r"all-star|touchdowns?|goals|scored|dunk|hat trick|coach|draft|rookie|stadium)\b)"),
    concat!(r"(?i:\b(?:actor|actors|actress|actresses|acting|comedian|comedians|stand-?up|hollywood|oscars?|celebrity|celebrities|starred|starring|his movies|her movies|",
        r"his films|her films|roles?)\b)"),
];
const AUTHORING_SOURCE: &str = r"(?i:\b(?:author|authors|novelist|writer|writes|wrote|written|books?|novels?|reading|read|series|trilogy)\b)";
const LEXICON_ARTIST: usize = 8;
const LEXICON_FRANCHISE: usize = 9;
const AUTHORING: usize = 10;
const PATTERN_COUNT: usize = 11;

static CONTEXTS: LazyLock<Vec<Re>> = LazyLock::new(|| {
    let mut patterns: Vec<Re> = CONTEXT_SOURCES.iter().map(|p| Re::new(p)).collect();
    let cut = |p: &str| p[..p.len() - 4].to_string();
    patterns.push(Re::new(&(cut(CONTEXT_SOURCES[2]) + r"|sing|sings|sang|singing|playlist|records?|records|festival|fans?|stan)\b)")));
    patterns.push(Re::new(&(cut(CONTEXT_SOURCES[1]) + r"|read|reading|fandom|canon|plot|characters?|finale|spinoff|reboot|adaptation)\b)")));
    patterns.push(Re::new(AUTHORING_SOURCE));
    patterns
});

fn context(kind: &str) -> usize {
    CONTEXT_KINDS.iter().position(|k| *k == kind).unwrap()
}

fn lexicon_context(kind: &str) -> usize {
    match kind {
        "artist" => LEXICON_ARTIST,
        "franchise" => LEXICON_FRANCHISE,
        _ => context(kind),
    }
}

fn target_context(kind: &str) -> usize {
    if kind == "author" {
        AUTHORING
    } else {
        lexicon_context(kind)
    }
}

pub fn pattern(index: usize) -> &'static Re {
    &CONTEXTS[index]
}

pub struct Totals<'a> {
    text: &'a [char],
    counts: [Option<usize>; PATTERN_COUNT],
}

impl<'a> Totals<'a> {
    pub fn new(text: &'a [char]) -> Totals<'a> {
        Totals { text, counts: [None; PATTERN_COUNT] }
    }

    pub fn get(&mut self, index: usize) -> usize {
        if let Some(count) = self.counts[index] {
            return count;
        }
        let count = CONTEXTS[index].count(self.text);
        self.counts[index] = Some(count);
        count
    }
}

pub fn has(list: &[&str], item: &str) -> bool {
    list.contains(&item)
}

fn best<'k>(scores: &[(&'k str, usize)]) -> (&'k str, usize) {
    let mut top = scores[0];
    for &score in &scores[1..] {
        if score.1 > top.1 {
            top = score;
        }
    }
    top
}

pub fn chars_of(s: &str) -> Vec<char> {
    s.chars().collect()
}

pub fn join_words(words: &[&[char]]) -> Vec<char> {
    let mut out = Vec::new();
    for (index, word) in words.iter().enumerate() {
        if index > 0 {
            out.push(' ');
        }
        out.extend_from_slice(word);
    }
    out
}

pub fn rstrip<'a>(s: &'a [char], set: &str) -> &'a [char] {
    let mut end = s.len();
    while end > 0 && set.contains(s[end - 1]) {
        end -= 1;
    }
    &s[..end]
}

pub fn first_piece<'a>(re: &Re, s: &'a [char]) -> &'a [char] {
    match re.find(s) {
        Some(m) => &s[..m.start()],
        None => s,
    }
}

pub fn re_split<'a>(re: &Re, s: &'a [char]) -> Vec<&'a [char]> {
    let mut pieces = Vec::new();
    let mut last = 0;
    for m in re.iter(s) {
        pieces.push(&s[last..m.start()]);
        last = m.end();
    }
    pieces.push(&s[last..]);
    pieces
}

fn window(s: &[char], start: usize, end: usize, width: usize) -> &[char] {
    let a = start.saturating_sub(width);
    let b = (end + width).min(s.len());
    if a >= b {
        &s[0..0]
    } else {
        &s[a..b]
    }
}

pub fn sentence(text: &[char], start: usize, end: usize) -> (usize, usize) {
    (last_mark(text, start, ".!?\n"), next_mark(text, end, ".!?\n"))
}

fn at(text: &[char], index: usize) -> Option<char> {
    text.get(index).copied()
}

pub fn praised(text: &[char], start: usize, end: usize) -> bool {
    let (left, right) = sentence(text, start, end);
    POSITIVE.test_in(text, left, right) && !NEGATIVE.test_in(text, left, right) && at(text, right) != Some('?')
}

#[derive(Clone, Copy)]
pub struct Mention {
    pub attribute: &'static str,
    pub start: usize,
    pub end: usize,
    pub value: &'static str,
    pub cased: bool,
    pub common: bool,
    pub links: u32,
}

struct Words {
    bounds: Vec<(usize, usize)>,
    shown_all: String,
    low_all: String,
    shown_at: Vec<(usize, usize)>,
    low_at: Vec<(usize, usize)>,
}

impl Words {
    fn of(text: &[char]) -> Words {
        let bounds = word_spans(text);
        let mut words = Words { shown_all: String::with_capacity(text.len()), low_all: String::with_capacity(text.len()), shown_at: Vec::with_capacity(bounds.len()), low_at: Vec::with_capacity(bounds.len()), bounds };
        for &(a, b) in &words.bounds {
            let begin = words.shown_all.len();
            words.shown_all.extend(&text[a..b]);
            words.shown_at.push((begin, words.shown_all.len()));
            let begin = words.low_all.len();
            let word = &words.shown_all[words.shown_at.last().unwrap().0..];
            if word.is_ascii() {
                for c in word.bytes() {
                    words.low_all.push(c.to_ascii_lowercase() as char);
                }
            } else {
                let lowered = word.to_lowercase();
                words.low_all.push_str(&lowered);
            }
            words.low_at.push((begin, words.low_all.len()));
        }
        words
    }

    fn shown(&self, i: usize) -> &str {
        &self.shown_all[self.shown_at[i].0..self.shown_at[i].1]
    }

    fn low(&self, i: usize) -> &str {
        &self.low_all[self.low_at[i].0..self.low_at[i].1]
    }
}

type Found2 = (usize, Option<&'static Vec<Entry>>, Option<&'static Vec<Entry>>);

fn longest_at(text: &[char], words: &Words, index: usize, verdicts: &mut Vec<((usize, usize), bool)>, key: &mut String, surface: &mut String) -> Option<Option<Found2>> {
    let total = words.bounds.len();
    let mut entry = match probe(words.low(index)) {
        Probe::Absent => return None,
        Probe::Prefix => None,
        Probe::Entry(node) => Some(node),
    };
    key.clear();
    key.push_str(words.low(index));
    surface.clear();
    surface.push_str(words.shown(index));
    let mut size = 1;
    let mut found: Option<Found2> = None;
    loop {
        if let Some(node) = entry {
            let plain = node.plain;
            let cased = node.surface(lexicon::CASED, surface.as_str())
                .or_else(|| if size == 1 { node.surface(lexicon::RAISED, surface.as_str()) } else { None })
                .or_else(|| if plain.is_none() { node.surface(lexicon::SENTENCE, surface.as_str()) } else { None });
            if plain.is_some() || cased.is_some() {
                found = Some((size, plain, cased));
            } else {
                let film_plain = node.film_plain;
                let film_cased = node.surface(lexicon::FILM_CASED, surface.as_str());
                if (film_plain.is_some() || film_cased.is_some()) && praised_once(text, verdicts, words.bounds[index].0, words.bounds[index + size - 1].1) {
                    found = Some((size, film_plain, film_cased));
                }
            }
        }
        if index + size == total {
            break;
        }
        key.push(' ');
        key.push_str(words.low(index + size));
        surface.push(' ');
        surface.push_str(words.shown(index + size));
        size += 1;
        match probe(key.as_str()) {
            Probe::Absent => break,
            Probe::Prefix => entry = None,
            Probe::Entry(node) => entry = Some(node),
        }
    }
    Some(found)
}

fn spread(words: &Words, index: usize, found: Found2, spans: &mut Vec<Mention>) -> usize {
    let (size, a, b) = found;
    let start = words.bounds[index].0;
    let end = words.bounds[index + size - 1].1;
    for e in a.into_iter().flatten().chain(b.into_iter().flatten()) {
        spans.push(Mention { attribute: e.attribute, start, end, value: e.value, cased: e.cased, common: e.common, links: e.links });
    }
    size
}

pub fn mentions(text: &[char]) -> Vec<Mention> {
    let words = Words::of(text);
    let mut spans = Vec::new();
    let mut verdicts = Vec::new();
    let mut key = String::new();
    let mut surface = String::new();
    let mut index = 0;
    while index < words.bounds.len() {
        match longest_at(text, &words, index, &mut verdicts, &mut key, &mut surface) {
            Some(Some(found)) => index += spread(&words, index, found, &mut spans),
            _ => index += 1,
        }
    }
    spans
}

pub fn leading(text: &[char]) -> Vec<Mention> {
    let words = Words::of(text);
    let mut spans = Vec::new();
    if words.bounds.first().map_or(true, |&(a, _)| a != 0) {
        return spans;
    }
    if let Some(Some(found)) = longest_at(text, &words, 0, &mut Vec::new(), &mut String::new(), &mut String::new()) {
        spread(&words, 0, found, &mut spans);
    }
    spans
}

type Hit = (&'static str, Vec<char>);

fn same_words(a: &[char], b: &[char]) -> bool {
    joined_words(a) == joined_words(b)
}

pub fn shown(surface: &[char], value: &str) -> Vec<char> {
    let value_chars = chars_of(value);
    if surface.len() > SHORT_KEY && !same_words(&lower(surface), &value_chars) {
        surface.to_vec()
    } else {
        value_chars
    }
}

fn max_hit<'m>(hits: impl Iterator<Item = &'m Mention>) -> Option<&'m Mention> {
    let mut top: Option<&Mention> = None;
    for m in hits {
        if top.map_or(true, |t| (m.links, m.attribute, m.value) > (t.links, t.attribute, t.value)) {
            top = Some(m);
        }
    }
    top
}

pub fn lexical(name: &[char]) -> Option<Hit> {
    let surface = rstrip(name, " .,!:");
    let found = leading(name);
    let top = max_hit(found.iter().filter(|m| m.start == 0 && m.end == surface.len()))?;
    Some((top.attribute, shown(surface, top.value)))
}

fn entitled(name: &[char], options: &[&str]) -> Option<Hit> {
    let words: Vec<String> = split_ws(name).iter().map(|w| capitalize(&st(w))).collect();
    let single = words.len() == 1;
    let titled = chars_of(&words.join(" "));
    let found = leading(&titled);
    options.iter().find_map(|&attribute| found.iter().find(|m| m.start == 0 && m.end == titled.len() && m.attribute == attribute && !((single || m.common) && m.links < FAMOUS_SITELINKS)))
        .map(|m| (m.attribute, chars_of(m.value)))
}

pub fn proper(name: &[char]) -> Option<Hit> {
    let words: Vec<String> = split_ws(name).iter().map(|w| capitalize(&st(w))).collect();
    let titled = chars_of(&words.join(" "));
    let found = leading(&titled);
    let top = max_hit(found.iter().filter(|m| m.start == 0 && m.end == titled.len() && !m.common && has(&PEOPLE, m.attribute) && m.attribute != "character"))?;
    Some((top.attribute, chars_of(top.value)))
}

fn classified(text: &[char], totals: &mut Totals, start: usize, name: &[char], options: &[&'static str]) -> Option<Hit> {
    if let Some(hit) = lexical(name) {
        return Some(hit);
    }
    let around = window(text, start, start, 200);
    let scores: Vec<(&'static str, usize)> = options.iter().map(|&kind| {
        let index = target_context(kind);
        (kind, 3 * CONTEXTS[index].count(around) + totals.get(index))
    }).collect();
    let (kind, score) = best(&scores);
    if score == 0 {
        return None;
    }
    if kind == "athlete" && (split_ws(name).len() < 2 || name.last() == Some(&'s')) {
        return None;
    }
    Some((kind, name.to_vec()))
}

pub fn named(attribute: &str, name: &[char], found: &mut Found, position: usize) {
    let cleaned = TRAILING.sub(name, "");
    let name = strip_space(&cleaned);
    if name.len() <= 1 || name.len() > 40 {
        return;
    }
    let low = lower(name);
    let words = split_ws(&low);
    if has(&PRONOUNS, &st(words[0])) || has(&PRONOUNS, &st(words[words.len() - 1])) {
        return;
    }
    if let Some(value) = fan_value(attribute, &low) {
        found.set(attribute, st(&value), position);
    }
}

fn parts(name: &[char]) -> Vec<Vec<char>> {
    let name = first_piece(&STOP, name);
    if !name.contains(&' ') || lexical(name).is_some() {
        return vec![name.to_vec()];
    }
    let stripped = POSSESSIVE.sub(name, "");
    re_split(&SPLIT, &stripped).into_iter().filter(|p| !p.is_empty()).map(|p| p.to_vec()).collect()
}

fn junk(name: &[char]) -> bool {
    let cleaned = TRAILING.sub(name, "");
    let low = lower(strip_space(&cleaned));
    let words = split_ws(&low);
    let (first, last) = if words.is_empty() { (String::new(), String::new()) } else { (st(words[0]), st(words[words.len() - 1])) };
    EDGE.contains(first.as_str()) || EDGE.contains(last.as_str()) || last.ends_with("'s") || last.ends_with("s'") || contains(&low, " and ")
}

fn othered(lowered: &[char], start: usize, end: usize) -> bool {
    let left = clause(lowered, start);
    PEER.test_in(lowered, left, start) && !SELF.test_in(lowered, left, end)
}

fn bare_word_in(text: &[char], word: &[char]) -> bool {
    if word.is_empty() || word.len() > text.len() {
        return false;
    }
    let outside = |c: char| !(is_word_char(c) || c == '\'');
    (0..=text.len() - word.len()).any(|i| {
        text[i] == word[0] && &text[i..i + word.len()] == word && (i == 0 || outside(text[i - 1])) && (i + word.len() == text.len() || outside(text[i + word.len()]))
    })
}

pub fn fandom(text: &[char], found: &mut Found) {
    if !cues_of(text).any(MASKS.POSITIVE) || positive_starts(text).is_empty() {
        return;
    }
    for sentence in SENTENCE.iter(text) {
        let part = sentence.text();
        let Some(cue) = POSITIVE.find(part) else {
            continue;
        };
        if NEGATIVE.test(part) {
            continue;
        }
        let low = lower(part);
        if hedged(&low, cue.start(), cue.end(), self_hedge()) {
            continue;
        }
        let first = part.iter().position(|&c| !is_space(c)).unwrap_or(part.len());
        let mut names: Vec<(usize, &'static str, Vec<char>)> = Vec::new();
        let mut totals = Totals::new(part);
        for m in CANDIDATE.iter(part) {
            let raw = m.nonempty(1).or(m.group(2)).unwrap_or(&[]);
            let mut name: Vec<char> = first_piece(&STOP, strip_space(raw)).to_vec();
            let lowered_name = lower(&name);
            let mut words: Vec<String> = split_ws(&lowered_name).iter().map(|w| st(w)).collect();
            if !words.is_empty() && COMMON.contains(words[0].as_str()) {
                name = join_words(&split_ws(&name)[1..]);
                words.remove(0);
            }
            if words.is_empty() || !two_letters(&name) || CODE.fullmatch(&name, 0, name.len()).is_some() {
                continue;
            }
            if words.len() == 1 && (COMMON.contains(words[0].as_str()) || name.len() < 4 || m.start() == first || bare_word_in(text, &chars_of(&words[0]))) {
                continue;
            }
            if cue.start() <= m.start() && m.start() < cue.end() {
                continue;
            }
            let around = window(part, m.start(), m.end(), 80);
            let scores: Vec<(&'static str, usize)> = (0..8).map(|i| (CONTEXT_KINDS[i], 3 * CONTEXTS[i].count(around) + totals.get(i))).collect();
            let (kind, score) = best(&scores);
            if score > 0 && !(kind == "franchise" && othered(&low, m.start(), m.end())) {
                names.push((m.start().abs_diff(cue.start()), kind, name));
            }
        }
        names.sort();
        for (_, kind, name) in names {
            if has(&NAMED_ONLY, kind) || junk(&name) {
                continue;
            }
            let size = split_ws(&TRAILING.sub(&name, "")).len();
            if kind == "artist" || (1 < size && size < 4) {
                named(kind, &name, found, sentence.start());
            }
        }
    }
}

pub fn adjacent(text: &[char], found: &mut Found) {
    let lowered = lower(text);
    let mut totals = Totals::new(text);
    for m in ADJACENT.iter(&lowered) {
        let group = m.group(1).unwrap_or(&[]);
        let group = if starts_at(group, 0, "the ") { &group[4..] } else { group };
        let name = strip_space(group);
        let words = split_ws(name);
        if STOP.test(name) || words.is_empty() {
            continue;
        }
        let first = st(words[0]);
        let last = st(words[words.len() - 1]);
        if GENERIC.contains(first.as_str()) || GENERIC.contains(last.as_str()) || COMMON.contains(first.as_str()) || name.len() < 3 || !two_letters(name)
            || hedged(&lowered, m.start(), m.end(), self_hedge()) || NEGATIVE.test(&lowered[m.start()..(m.end() + 40).min(lowered.len())]) {
            continue;
        }
        let part = window(text, m.start(), m.end(), 150);
        let scores: Vec<(&'static str, usize)> = (0..8).map(|i| (CONTEXT_KINDS[i], 3 * CONTEXTS[i].count(part) + totals.get(i))).collect();
        let (kind, score) = best(&scores);
        if score > 0 && !has(&NAMED_ONLY, kind) && !junk(name) && (words.len() < 3 || kind == "franchise" && words.len() < 4) {
            named(kind, name, found, m.start());
        }
    }
}

fn object_kind(word: &str) -> Option<&'static str> {
    OBJECTS.iter().find(|(k, _)| *k == word).map(|(_, v)| *v)
}

fn partition<'a>(s: &'a [char], mark: &str) -> (&'a [char], bool, &'a [char]) {
    match find(s, mark, 0) {
        Some(p) => (&s[..p], true, &s[p + mark.chars().count()..]),
        None => (s, false, &s[0..0]),
    }
}

fn first_word(s: &[char]) -> String {
    word_spans(s).first().map(|&(a, b)| st(&s[a..b])).unwrap_or_default()
}

pub fn favorites(text: &[char], found: &mut Found) {
    let lowered = lower(text);
    let cues = cues_of(text);
    let masks = &*MASKS;
    let fanned = (contains(&lowered, " fan") || contains(&lowered, " supporter") || contains(&lowered, " stan") || contains(&lowered, " enjoyer")) && FAN_CUE.test(text);
    let mut totals = Totals::new(text);
    let hedge = self_hedge();
    if contains(&lowered, "fav") || contains(&lowered, "goat") {
        for (index, pattern) in [&*FAVORITE, &*FAVORED].into_iter().enumerate() {
            for m in pattern.iter(text) {
                let (name, kind) = if index == 0 { (m.group(2), m.group(1)) } else { (m.group(1), m.group(2)) };
                let attribute = kind_of(&st(&lower(kind.unwrap_or(&[]))));
                if hedged(&lowered, m.start(), m.end(), hedge) {
                    continue;
                }
                for piece in parts(name.unwrap_or(&[])) {
                    if let Some(attribute) = attribute {
                        named(attribute, &piece, found, m.start());
                    } else if let Some((a, v)) = classified(text, &mut totals, m.start(), &piece, &ALL_OPTIONS) {
                        named(a, &v, found, m.start());
                    }
                }
            }
        }
    }
    for m in FAVORITE_PLAIN.iter(if cues.any(masks.FAV) { &lowered[..] } else { &lowered[..0] }) {
        let group = m.group(2).unwrap_or(&[]);
        let group = if starts_at(group, 0, "the ") { &group[4..] } else { group };
        let words = split_ws(group);
        if words.is_empty() {
            continue;
        }
        let first = st(words[0]);
        if !COMMON.contains(first.as_str()) && !GENERIC.contains(first.as_str()) && !hedged(&lowered, m.start(), m.end(), hedge) {
            if let Some(attribute) = kind_of(&st(m.group(1).unwrap_or(&[]))) {
                named(attribute, &join_words(&words), found, m.start());
            }
        }
    }
    if contains(&lowered, " fan") || contains(&lowered, " supporter") {
        for m in TEAM_FAN.iter(gate(text, fanned)) {
            if hedged(&lowered, m.start(), m.end(), hedge) {
                continue;
            }
            let second = m.nonempty(2).is_some();
            for piece in parts(m.nonempty(1).or(m.group(2)).unwrap_or(&[])) {
                let spaces = piece.iter().filter(|&&c| c == ' ').count();
                let drops = if second { 3.min(spaces + 1) } else { 1 };
                for drop in 0..drops {
                    let tail = split_tail(&piece, drop);
                    if let Some(club) = team(tail) {
                        if !club.is_empty() {
                            named("sports_team", &chars_of(club), found, m.start());
                            break;
                        }
                    }
                }
            }
        }
    }
    if contains(&lowered, "my") && contains(&lowered, " team") {
        for m in OWN_TEAM.iter(text) {
            if hedged(&lowered, m.start(), m.end(), hedge) {
                continue;
            }
            for piece in parts(m.nonempty(1).or(m.group(2)).unwrap_or(&[])) {
                if let Some(club) = team(&piece).filter(|c| !c.is_empty()) {
                    named("sports_team", &chars_of(club), found, m.start());
                }
            }
        }
    }
    let literals: [&[&str]; 6] = [&[" fan", " supporter", " stan", " enjoyer"], &["fan of", "supporter of", "admirer of"], &["stan"], &["goat"], &["goat"], &[""]];
    for (index, pattern) in [&*FAN, &*FAN_OF, &*STAN, &*GOAT, &*GOATED, &*PRAISED].into_iter().enumerate() {
        if !literals[index].iter().any(|w| contains(&lowered, w)) || index == 5 && !cues.any(masks.PRAISED) {
            continue;
        }
        for m in pattern.iter(gate(text, match index { 0 => fanned, 1 => cues.any(masks.FAN_OF), 2 => cues.any(masks.STAN), 3 => cues.any(masks.GOAT), 4 => GOATED_CUE.test(text), _ => true })) {
            if hedged(&lowered, m.start(), m.end(), hedge) {
                continue;
            }
            for piece in parts(m.group(1).unwrap_or(&[])) {
                if index <= 1 {
                    if let Some(club) = team(&piece) {
                        if !club.is_empty() {
                            named("sports_team", &chars_of(club), found, m.start());
                            continue;
                        }
                    }
                    if index == 0 && placed(&piece) && lexical(&piece).map_or(true, |(a, _)| a != "athlete") {
                        named("sports_team", &piece, found, m.start());
                        continue;
                    }
                }
                if let Some((a, v)) = classified(text, &mut totals, m.start(), &piece, &ALL_OPTIONS) {
                    if index != 5 || !has(&UNPRAISED, a) {
                        named(a, &v, found, m.start());
                    }
                }
            }
        }
    }
    if (contains(&lowered, "lov") || contains(&lowered, "ador") || contains(&lowered, "enjoy") || contains(&lowered, "obsess")) && cues.any(masks.LOVED) {
        for (index, pattern) in [&*LOVED, &*DROPPED].into_iter().enumerate() {
            for m in pattern.iter(text) {
                if hedged(&lowered, m.start(), m.end(), hedge) {
                    continue;
                }
                let (name, mark, rest) = partition(m.group(1).unwrap_or(&[]), "'s");
                let kind = if mark {
                    let source = if rest.is_empty() { &text[m.end().min(text.len())..(m.end() + 20).min(text.len())] } else { rest };
                    object_kind(&first_word(source).to_lowercase())
                } else {
                    None
                };
                if let Some(kind) = kind {
                    named(kind, first_piece(&STOP, name), found, m.start());
                    continue;
                }
                let hit = lexical(name);
                if let Some((a, v)) = &hit {
                    if has(&NAMED_ONLY, a) {
                        named(a, v, found, m.start());
                        continue;
                    }
                }
                if hit.is_none() && index == 0 {
                    for piece in parts(name) {
                        if let Some((a, v)) = classified(text, &mut totals, m.start(), &piece, &PEOPLE) {
                            named(a, &v, found, m.start());
                        }
                    }
                }
            }
        }
    }
    if contains(&lowered, "crush") && cues.any(masks.CRUSH) {
        for m in CRUSH.iter(text) {
            if SELF.test_in(text, clause(text, m.start()), m.start()) && !hedged(&lowered, m.start(), m.end(), hedge) {
                if let Some((a, v)) = lexical(first_piece(&STOP, m.group(1).unwrap_or(&[]))) {
                    if has(&CRUSHED, a) {
                        named(a, &v, found, m.start());
                    }
                }
            }
        }
    }
    if contains(&lowered, " fan") || contains(&lowered, " stan") || contains(&lowered, " supporter") {
        for m in LOWER_FAN.iter(gate(text, fanned)) {
            if hedged(&lowered, m.start(), m.end(), hedge) {
                continue;
            }
            let group = m.group(1).unwrap_or(&[]);
            match team(group).filter(|c| !c.is_empty()) {
                Some(club) => named("sports_team", &chars_of(club), found, m.start()),
                None => {
                    if let Some((a, v)) = proper(group).or_else(|| entitled(group, &SHOWN)) {
                        named(a, &v, found, m.start());
                    }
                }
            }
        }
    }
    for m in LIKED_PERSON.iter(gate(text, cues.any(masks.LIKED_PERSON))) {
        if !hedged(&lowered, m.start(), m.end(), hedge) {
            if let Some((a, v)) = lexical(first_piece(&STOP, m.group(1).unwrap_or(&[]))) {
                if has(&NAMED_ONLY, a) {
                    named(a, &v, found, m.start());
                }
            }
        }
    }
    for m in CHOICE.iter(gate(text, cues.any(masks.CHOICE))) {
        let name = strip_space(m.group(1).unwrap_or(&[]));
        let spaced = name.contains(&' ');
        let hit = if spaced { lexical(name) } else { proper(name) };
        if let Some((a, v)) = hit {
            if spaced || a != "author" {
                named(a, &v, found, m.start());
            }
        }
    }
    for (pattern, open) in [(&*CREATED, cues.any(masks.CREATED)), (&*WATCHED, cues.any(masks.WATCHED))] {
        for m in pattern.iter(gate(text, open)) {
            let left = clause(text, m.start());
            let around = &text[left..(m.end() + 80).min(text.len())];
            let group = m.group(1).unwrap_or(&[]);
            if (SELF.test(around) || POSITIVE.test(around)) && !hedged(&lowered, m.start(), m.end(), hedge) && lexical(group).is_none() {
                named("creator", first_piece(&STOP, group), found, m.start());
            }
        }
    }
    for (pattern, open) in [(&*LISTENED, cues.any(masks.LISTENED)), (&*ALBUM, cues.any(masks.ALBUM) && cues.any(masks.ALBUM_WORDS)), (&*SEEN, cues.any(masks.SEEN) && cues.any(masks.SEEN_WORDS))] {
        for m in pattern.iter(gate(text, open)) {
            let left = clause(text, m.start());
            let around = &text[left..(m.end() + 80).min(text.len())];
            if (SELF.test(around) || POSITIVE.test(around)) && !hedged(&lowered, m.start(), m.end(), hedge) {
                for piece in parts(m.group(1).unwrap_or(&[])) {
                    match lexical(&piece) {
                        None => named("artist", &piece, found, m.start()),
                        Some((a, v)) => {
                            if a == "artist" {
                                named("artist", &v, found, m.start());
                            }
                        }
                    }
                }
            }
        }
    }
    if contains(&lowered, "ything ") {
        for m in ANYTHING.iter(text) {
            let (left, right) = sentence(text, m.start(), m.end());
            if !hedged(&lowered, m.start(), m.end(), hedge) && !NEGATIVE.test_in(text, left, right) {
                let name = rstrip(first_piece(&STOP, m.group(1).unwrap_or(&[])), " .,!:");
                let readings = leading(name);
                let whole: Vec<&Mention> = readings.iter().filter(|r| r.start == 0 && r.end == name.len() && !r.common).collect();
                for attribute in ["author", "artist"] {
                    if let Some(reading) = whole.iter().find(|r| r.attribute == attribute) {
                        named(attribute, &shown(name, reading.value), found, m.start());
                        break;
                    }
                }
            }
        }
    }
    authored(text, &lowered, &cues, found);
    answered(text, found);
    known(text, &lowered, &cues, found);
}

fn placed(name: &[char]) -> bool {
    let joined = joined_words(&lower(&folded_chars(name)));
    LEXICON.nations.contains(joined.strip_prefix("the ").unwrap_or(&joined))
}

fn split_tail(piece: &[char], drop: usize) -> &[char] {
    let mut start = 0;
    let mut dropped = 0;
    for (index, &c) in piece.iter().enumerate() {
        if dropped == drop {
            break;
        }
        if c == ' ' {
            start = index + 1;
            dropped += 1;
        }
    }
    &piece[start..]
}

fn opening(text: &[char], start: usize) -> bool {
    let before = rstrip(&text[..start.min(text.len())], " \t\"'*(#>-_[");
    before.is_empty() || ".!?\n:".contains(before[before.len() - 1])
}

fn paragraph(text: &[char], start: usize) -> usize {
    BLANK.search(text, start, text.len()).map_or(text.len(), |m| m.start())
}

fn authored(text: &[char], lowered: &[char], cues: &Cues, found: &mut Found) {
    if !BOOKISH.iter().any(|w| contains(lowered, w)) {
        return;
    }
    for (index, pattern) in [&*WRITTEN_BY, &*WROTE].into_iter().enumerate() {
        let open = cues.any(if index == 0 { MASKS.WRITTEN_BY } else { MASKS.WROTE });
        for m in pattern.iter(gate(text, open)) {
            let name = m.nonempty(1).or(m.group(2)).unwrap_or(&[]);
            let (left, right) = sentence(text, m.start(), m.end());
            let alone = index == 0 && opening(text, left) && strip_chars(&text[m.end()..right.max(m.end())], " .,!*}").is_empty();
            let supported = SELF.test_in(text, left, right) || POSITIVE.test_in(text, left, right) || alone && SELF.test_in(text, right, paragraph(text, right));
            if !supported || NEGATIVE.test_in(text, left, right) || at(text, right) == Some('?') || ADVISED.test_in(text, left, right) || hedged(lowered, m.start(), m.end(), self_hedge()) {
                continue;
            }
            let hit = lexical(name);
            if let Some((a, _)) = &hit {
                if !has(&["author", "celebrity", "artist"], a) {
                    continue;
                }
            }
            let wide = left.saturating_sub(100);
            if index == 1 || CONTEXTS[AUTHORING].test_in(text, wide, right + 100) && !CONTEXTS[context("artist")].test_in(text, wide, right + 100) {
                match &hit {
                    Some((a, v)) if *a == "author" => named("author", v, found, m.start()),
                    _ => named("author", name, found, m.start()),
                }
            }
        }
    }
}

fn answered(text: &[char], found: &mut Found) {
    let body = strip_space(text);
    let body: Vec<char> = if contains(body, "](") || contains(body, "http") { MEDIA.sub(body, "") } else { body.to_vec() };
    let (head, last) = match rfindc(&body, '\n', body.len()) {
        Some(p) => (&body[..p], &body[p + 1..]),
        None => (&body[..0], &body[..]),
    };
    if last.is_empty() {
        return;
    }
    if !head.is_empty() {
        let mut lines = head.to_vec();
        lines.push('\n');
        if HEADERS.fullmatch(&lines, 0, lines.len()).is_none() {
            return;
        }
    }
    let lead = RIM.at(last, 0).map_or(0, |m| m.end());
    let reversed: Vec<char> = last.iter().rev().copied().collect();
    let tail = RIM.at(&reversed, 0).map_or(0, |m| m.end());
    let inner = slice(last, lead as isize, (last.len() - tail) as isize);
    let Some(m) = ANSWER.fullmatch(inner, 0, inner.len()) else {
        return;
    };
    let name = m.group(2).unwrap_or(&[]);
    let single = !name.contains(&' ');
    let lex: &'static Lexicon = &LEXICON;
    if !(m.nonempty(1).is_some() || m.nonempty(3).is_some() || !head.is_empty()) {
        if !single && count(name, " ") <= lex.team_span {
            let club = if isascii(name) {
                let joined = joined_words(name).to_lowercase();
                let key = joined.strip_prefix("the ").unwrap_or(&joined);
                lex.team_words.get(key).copied()
            } else {
                team(name)
            };
            if let Some(club) = club.filter(|c| !c.is_empty()) {
                named("sports_team", &chars_of(club), found, 0);
            }
        }
        return;
    }
    if let Some(club) = team(name).filter(|c| !c.is_empty()) {
        let listed = lex.plain.get(st(&lower(name)).as_str()).map_or(false, |entries| entries.iter().any(|e| e.attribute == "sports_team"));
        if !(single && !listed) {
            named("sports_team", &chars_of(club), found, 0);
            return;
        }
    }
    let mut hits: Vec<(&'static str, &'static str)> = Vec::new();
    for mention in leading(name) {
        if mention.start == 0 && mention.end == name.len() && !mention.common && !(single && mention.links < FAMOUS_SITELINKS) {
            match hits.iter_mut().find(|(a, _)| *a == mention.attribute) {
                Some(slot) => slot.1 = mention.value,
                None => hits.push((mention.attribute, mention.value)),
            }
        }
    }
    for attribute in ANSWERED {
        if let Some((_, value)) = hits.iter().find(|(a, _)| *a == attribute) {
            if attribute != "celebrity" || hits.len() == 1 {
                named(attribute, &chars_of(value), found, 0);
                return;
            }
        }
    }
}

fn supported(text: &[char], lowered: &[char], start: usize, end: usize) -> bool {
    let before = start.saturating_sub(30);
    let mut backed = BACKING.search(lowered, before, start);
    if let Some(b) = &backed {
        if islower(&text[start..end]) && OWNED.at(b.text(), 0).is_some() {
            backed = None;
        }
    }
    let watched = || SEASON.at(lowered, end).is_some() && {
        let (left, right) = sentence(text, start, end);
        SELF.test_in(text, left, right) && ATTENDED.test_in(lowered, left, right)
    };
    if !(backed.is_some() || BACKER.at(lowered, end).is_some() || (FANNED.at(lowered, end).is_some() && AVOWED.test_in(lowered, before, start)) || watched()) {
        return false;
    }
    !PEER.test_in(lowered, clause(lowered, start), start) && !hedged(lowered, start, end, self_hedge())
}

fn favoured(segments: &[(usize, usize)], start: usize) -> bool {
    segments.iter().any(|&(left, right)| left <= start && start < right)
}

fn engaged(text: &[char], start: usize, end: usize, attribute: &str, popular: bool, plain: bool) -> bool {
    let narrow = sentence(text, start, end);
    let (mut left, mut right) = narrow;
    let dropped = if has(&TITLES, attribute) && clause(text, start) <= left { PRODROP.at_in(text, left, start) } else { None };
    let loving = dropped.as_ref().map_or(false, |d| d.nonempty(1).is_some());
    let self_in = |a: usize, b: usize| SELF.test_in(text, a, b);
    if at(text, right) == Some('?') || attribute == "athlete" && !(self_in(narrow.0, narrow.1) || dropped.is_some()) {
        return false;
    }
    if plain && attribute == "franchise" {
        return POSITIVE.test_in(text, narrow.0, narrow.1) || loving;
    }
    let done = match attribute {
        "video_game" => Some(&*DONE_GAME),
        "franchise" => Some(&*DONE_FRANCHISE),
        "artist" => Some(&*DONE_ARTIST),
        _ => None,
    };
    if done.is_some() && (text[start..end].contains(&' ') || attribute == "artist" || attribute == "video_game" && !popular) {
        left = left.saturating_sub(100);
        right += 100;
    }
    if POSITIVE.test_in(text, left, right) || loving {
        return true;
    }
    if let Some(done) = done {
        if !popular {
            let scope = if attribute == "video_game" { (left, right) } else { narrow };
            return (self_in(scope.0, scope.1) || dropped.is_some()) && done.test_in(text, scope.0, scope.1);
        }
    }
    !has(&CHEERED, attribute) && (self_in(left, right) || dropped.is_some())
}

re!(DONE_GAME, r"(?i:\b(?:play|playing|played|replay\w*|beat|beaten|finished|finishing|completed|platinumed|grinding|started|bought|preordered|pre-ordered|hours|hrs)\b)");
re!(DONE_FRANCHISE, r"(?i:\b(?:watch|watching|watched|rewatch\w*|binge\w*|binging|read|reading|reread\w*|finished|finishing|started)\b)");
re!(DONE_ARTIST, r"(?i:\b(?:listen|listening|listened|saw|seen|concerts?|gigs?|vinyl|albums?|discography|tickets?|merch|tours?|records?|cds?|cassettes?|bought|preordered)\b)");

type Span = (usize, usize, &'static str, &'static str);
type Spot = (usize, usize, &'static str);

fn preferred(start: usize, end: usize, options: &[(&'static str, &'static str)], bypassed: &FxHashSet<Spot>, loved: &FxHashSet<Spot>) -> Vec<(&'static str, &'static str)> {
    if loved.is_empty() {
        let kept: Vec<_> = options.iter().copied().filter(|o| !bypassed.contains(&(start, end, o.0))).collect();
        return if kept.is_empty() { options.to_vec() } else { kept };
    }
    let plain: Vec<_> = options.iter().copied().filter(|o| !loved.contains(&(start, end, o.0))).collect();
    let kept: Vec<_> = plain.iter().copied().filter(|o| !bypassed.contains(&(start, end, o.0))).collect();
    let mut result = if kept.is_empty() { plain } else { kept };
    result.extend(options.iter().copied().filter(|o| loved.contains(&(start, end, o.0))));
    result
}

fn chosen(text: &[char], start: usize, options: Vec<(&'static str, &'static str)>, totals: &mut Totals) -> Vec<(&'static str, &'static str)> {
    if options.len() == 1 {
        return options;
    }
    let around = window(text, start, start, 150);
    options.into_iter().filter(|option| {
        let index = lexicon_context(option.0);
        let score = 3 * CONTEXTS[index].count(around) + totals.get(index);
        score > 0 || option.0 != "video_game"
    }).collect()
}

fn known(text: &[char], lowered: &[char], cues: &Cues, found: &mut Found) {
    let lex: &'static Lexicon = &LEXICON;
    let mut grouped: FxHashMap<(usize, usize), Vec<(&'static str, &'static str)>> = FxHashMap::default();
    let mut opened: FxHashSet<Spot> = FxHashSet::default();
    let mut famous: FxHashSet<Spot> = FxHashSet::default();
    let mut ordinary: FxHashSet<Spot> = FxHashSet::default();
    let mut bypassed: FxHashSet<Spot> = FxHashSet::default();
    let mut loved: FxHashSet<Spot> = FxHashSet::default();
    let mut readings: FxHashMap<Spot, &'static str> = FxHashMap::default();
    let mut totals = Totals::new(text);
    let segments: Vec<(usize, usize)> = FAVOURED.iter(gate(text, cues.any(MASKS.FAVOURED))).map(|m| (m.end(), findc(text, '\n', m.end()).unwrap_or(text.len()))).collect();
    let all = mentions(text);
    for mention in all {
        let Mention { attribute, start, end, value, cased, common, links } = mention;
        if attribute == "sports_team" {
            if supported(text, lowered, start, end) {
                named(attribute, &chars_of(value), found, start);
            }
            continue;
        }
        if has(&PEOPLE, attribute) {
            readings.entry((start, end, attribute)).or_insert(value);
        }
        if attribute == "character" || (cased && has(&SPELLED, attribute)) {
            continue;
        }
        let surface = &text[start..end];
        let spaced = surface.contains(&' ');
        let titled = has(&TITLES, attribute);
        let liking = || has(&LIKABLE, attribute) && LIKED.test_in(text, start.saturating_sub(40), start);
        let mut liked = None;
        if common && links < FAMOUS_SITELINKS && !spaced {
            let verdict = liking();
            liked = Some(verdict);
            if !verdict {
                continue;
            }
        }
        if titled && value.chars().filter(|&c| is_word_char(c)).count() <= 2 {
            continue;
        }
        if titled && plain_title(lex, surface) {
            continue;
        }
        if (has(&LOOSE, attribute) && !cased && common && links < FAMOUS_SITELINKS && islower(surface))
            || (attribute == "franchise" && islower(surface) && surface.iter().any(|&c| isdigit(&[c])))
        {
            continue;
        }
        let liked = liked.unwrap_or_else(liking);
        let gated = (cased || common || has(&NAMED_ONLY, attribute) || has(&GATED, attribute)) && !CONTEXTS[target_context(attribute)].test_in(text, start.saturating_sub(WINDOW), end + WINDOW);
        if gated && !(((attribute == "franchise" && links >= FAMOUS_SITELINKS && !common || has(&NAMED_ONLY, attribute)) && praised(text, start, end)) || liked || favoured(&segments, start)) {
            continue;
        }
        if gated && liked && attribute != "franchise" {
            loved.insert((start, end, attribute));
        }
        if cased && !spaced && opening(text, start) {
            let (a, b) = sentence(text, start, end);
            if !(titled && POSITIVE.test_in(text, a, b) || attribute == "video_game" && SELF.test_in(text, a, b)) {
                opened.insert((start, end, attribute));
            }
        }
        if links >= FAMOUS_SITELINKS && titled {
            famous.insert((start, end, attribute));
        }
        if common && links < FAMOUS_SITELINKS {
            ordinary.insert((start, end, attribute));
        }
        if gated && has(&NAMED_ONLY, attribute) && !favoured(&segments, start) {
            bypassed.insert((start, end, attribute));
        }
        grouped.entry((start, end)).or_default().push((attribute, value));
    }
    let mut spans: Vec<Span> = Vec::new();
    for (&(start, end), options) in &grouped {
        for (attribute, value) in chosen(text, start, preferred(start, end, options, &bypassed, &loved), &mut totals) {
            spans.push((start, end, attribute, value));
        }
    }
    spans.sort();
    let mut listed: FxHashSet<Span> = FxHashSet::default();
    let mut run: Vec<Span> = Vec::new();
    for index in 0..=spans.len() {
        let span = spans.get(index).copied();
        if let (Some(span), Some(previous)) = (span, run.last()) {
            if span.2 == previous.2 && LISTED.fullmatch(text, previous.1, span.0).is_some() {
                run.push(span);
                continue;
            }
        }
        if run.len() >= RUN && has(&LISTS, run[0].2) {
            listed.extend(run.iter().copied());
        }
        run = span.into_iter().collect();
    }
    let mut told: FxHashSet<(&'static str, &'static str)> = FxHashSet::default();
    for span in spans {
        let (start, end, attribute, value) = span;
        if attribute == "video_game" && othered(lowered, start, end) {
            continue;
        }
        let spot = (start, end, attribute);
        if told.contains(&(attribute, value)) {
            continue;
        }
        let accepted = listed.contains(&span) || favoured(&segments, start) || (!opened.contains(&spot) && engaged(text, start, end, attribute, famous.contains(&spot), ordinary.contains(&spot)));
        if !accepted || (!has(&PLAYED, attribute) && hedged(lowered, start, end, self_hedge())) {
            continue;
        }
        told.insert((attribute, value));
        named(attribute, &shown(&text[start..end], value), found, start);
        if attribute == "franchise" {
            if let Some(writer) = lex.author_of_book.get(value) {
                if !writer.is_empty() && CONTEXTS[AUTHORING].test(text) && praised(text, start, end) {
                    named("author", &chars_of(writer), found, start);
                }
            }
        }
        if attribute == "video_game" {
            if let Some(series) = lex.series_of_game.get(value) {
                named("franchise", &chars_of(series), found, start);
            }
        }
        let also: &[&str] = match attribute {
            "celebrity" => &["artist", "author"],
            "creator" => &["celebrity", "artist"],
            _ => &[],
        };
        for other in also {
            if let Some(reading) = readings.get(&(start, end, *other)) {
                named(other, &shown(&text[start..end], reading), found, start);
            }
        }
    }
}

pub fn init() {
    for index in 0..PATTERN_COUNT {
        pattern(index);
    }
    for re in [&TRAILING, &FAVORITE, &FAVORED, &POSITIVE, &NEGATIVE, &CANDIDATE, &SENTENCE, &CODE, &ADJACENT, &FAN, &TEAM_FAN, &FAN_OF, &STAN, &GOAT, &GOATED, &LOVED, &DROPPED, &CRUSH,
        &LOWER_FAN, &LIKED_PERSON, &OWN_TEAM, &CREATED, &WATCHED, &LISTENED, &ALBUM, &SEEN, &PRAISED, &FAVORITE_PLAIN, &WRITTEN_BY, &ANYTHING, &BLANK, &ADVISED, &WROTE, &CHOICE, &SPLIT, &POSSESSIVE, &STOP,
        &LISTED, &ANSWER, &HEADERS, &MEDIA, &RIM, &LIKED, &SELF, &PRODROP, &BACKING, &BACKER, &SEASON, &ATTENDED, &FANNED, &AVOWED, &OWNED, &PEER, &FAVOURED, &DONE_GAME, &DONE_FRANCHISE, &DONE_ARTIST] {
        LazyLock::force(re);
    }
}

fn praised_once(text: &[char], verdicts: &mut Vec<((usize, usize), bool)>, start: usize, end: usize) -> bool {
    let bounds = sentence(text, start, end);
    if let Some(&(_, verdict)) = verdicts.iter().find(|(b, _)| *b == bounds) {
        return verdict;
    }
    let (left, right) = bounds;
    let verdict = POSITIVE.test_in(text, left, right) && !NEGATIVE.test_in(text, left, right) && at(text, right) != Some('?');
    verdicts.push((bounds, verdict));
    verdict
}

fn gate(text: &[char], open: bool) -> &[char] {
    if open {
        text
    } else {
        &text[..0]
    }
}

fn plain_title(lex: &Lexicon, surface: &[char]) -> bool {
    let joined = joined_words(&lower(&folded_chars(surface)));
    let key = joined.strip_prefix("the ").unwrap_or(&joined);
    if !(COMMON.contains(key) || lex.places.contains(key)) {
        return false;
    }
    let surface_string = st(surface);
    let trimmed = surface_string.strip_prefix("the ").unwrap_or(&surface_string);
    let trimmed = trimmed.strip_prefix("The ").unwrap_or(trimmed);
    trimmed == key || trimmed == capitalize(key) || trimmed == title(key)
}

thread_local! {
    static POSITIVE_STARTS: std::cell::RefCell<(Vec<char>, Vec<usize>)> = const { std::cell::RefCell::new((Vec::new(), Vec::new())) };
}

pub fn positive_starts(text: &[char]) -> Vec<usize> {
    POSITIVE_STARTS.with(|cache| {
        let mut cache = cache.borrow_mut();
        if cache.0.as_slice() != text {
            let starts = POSITIVE.iter(text).map(|m| m.start()).collect();
            *cache = (text.to_vec(), starts);
        }
        cache.1.clone()
    })
}
