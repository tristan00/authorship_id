use crate::cues::{cues_of, Cues, MASKS};
use crate::lexicon::{self, *};
use claimcore::*;
use claimcore::schema::fan_value;
use rustc_hash::{FxHashMap, FxHashSet};
use std::sync::LazyLock;

pub const NAME: &str = r"((?:[Tt]he )?[A-Z0-9][\w'&.:!+-]*(?:,? (?:of|the|and|&|de|la|le|vs\.?|in|on|a|to|[A-Z0-9][\w'&.:!+-]*)){0,6})";
const DEGREE: &str = r"(?:huge|big|biggest|number one|#1|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted|avid|hardcore|crazy|super|major|total|self[- ](?:admitted|proclaimed|confessed|described))";

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

const CALENDAR_WORDS: &str = "january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday \
weekend weekday spring summer autumn fall winter halloween christmas xmas easter thanksgiving morning afternoon evening night tonight today tomorrow yesterday midnight noon day days week weeks \
month months year years decade decades hour hours minute minutes second seconds new eve";
const COLOUR_WORDS: &str = "red orange yellow green blue purple violet pink brown black white gray grey silver gold golden beige teal cyan magenta maroon navy crimson scarlet turquoise indigo lavender";
const CONTINENTS: [&str; 13] = ["africa", "antarctica", "asia", "europe", "oceania", "america", "americas", "north america", "south america", "latin america", "central america", "middle east", "australia"];
const DEMONYM_WORDS: &str = "american british english scottish welsh irish canadian australian aussie french german spanish italian portuguese dutch russian chinese japanese korean indian pakistani \
mexican brazilian argentine argentinian arab arabic african asian european latin latina latino hispanic polish swedish norwegian danish finnish greek turkish persian israeli ukrainian filipino \
vietnamese thai hindi urdu bengali cuban egyptian nigerian swiss austrian belgian hungarian czech romanian";
const INTERJECTION_WORDS: &str = "lol lmao omg haha dude bro yeah yep nope ok okay hey wow damn tbh imo idk btw nah u ur ya know";
const FILLER_WORDS: &str = "u ur ya y'all yall know mean let lots plenty every some most many few other such own here's there's what's let's gonna wanna gotta kinda sorta";
const CREATOR_WORDS: &str = "youtube yt tiktok twitch kick reddit instagram insta twitter facebook snapchat podcast podcasts channel channels video videos vlog vlogs stream streams streaming streamer \
streamers youtuber youtubers content ai watch watching watched subscribe";
const PLATFORM_WORDS: &str = "switch nintendo playstation ps1 ps2 ps3 ps4 ps5 psp vita xbox wii gameboy 3ds steam amazon spotify itunes soundcloud bandcamp pandora youtube tiktok netflix hulu internet";
const PLATFORM_PARTS: &str = "one deck store music prime video";
const PLATFORM_TARGETS: [&str; 4] = ["artist", "celebrity", "athlete", "video_game"];
const LOWERCASE_TARGETS: [&str; 1] = ["video_game"];
const ALIASED: [&str; 5] = ["artist", "celebrity", "creator", "athlete", "author"];
const CALENDAR_TARGETS: [&str; 6] = ["artist", "celebrity", "creator", "athlete", "author", "video_game"];
const COLOUR_TARGETS: [&str; 5] = ["celebrity", "creator", "athlete", "author", "video_game"];
const DEMONYM_TARGETS: [&str; 6] = ["artist", "creator", "athlete", "author", "video_game", "franchise"];
const FILLER_TARGETS: [&str; 6] = ["celebrity", "creator", "athlete", "author", "video_game", "franchise"];
const GENERIC_TARGETS: [&str; 4] = ["celebrity", "creator", "athlete", "author"];
const PRONOUNS: [&str; 13] = ["i", "i'm", "im", "i've", "i'd", "i'll", "me", "my", "you", "we", "he", "she", "they"];
const PEOPLE: [&str; 6] = ["character", "artist", "athlete", "celebrity", "creator", "author"];
const ALL_OPTIONS: [&str; 8] = ["character", "artist", "athlete", "celebrity", "creator", "author", "franchise", "video_game"];
const NAMED_ONLY: [&str; 3] = ["character", "athlete", "celebrity"];
const SPELLED: [&str; 4] = ["athlete", "celebrity", "author", "creator"];
const LIKABLE: [&str; 2] = ["artist", "franchise"];
const LOOSE: [&str; 1] = ["video_game"];
const SHOWN: [&str; 2] = ["franchise", "video_game"];
const PLAYED: [&str; 2] = ["video_game", "artist"];
pub const CONTEXT_KINDS: [&str; 8] = ["video_game", "franchise", "artist", "character", "author", "creator", "athlete", "celebrity"];

fn word_set(words: &'static str) -> FxHashSet<&'static str> {
    words.split_whitespace().collect()
}

static CALENDAR: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(CALENDAR_WORDS));
static COLOURS: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(COLOUR_WORDS));
static DEMONYMS: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(DEMONYM_WORDS));
static FILLER: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(FILLER_WORDS));
static INTERJECTIONS: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(INTERJECTION_WORDS));
static CREATOR_TERMS: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(CREATOR_WORDS));
pub static COMMON: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(COMMON_WORDS));
static EDGE: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(EDGE_WORDS));
static PLATFORMS: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(PLATFORM_WORDS));
static PLATFORM_PART: LazyLock<FxHashSet<&'static str>> = LazyLock::new(|| word_set(PLATFORM_PARTS));
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
re!(FAVORED, { let kind_words = &*KIND_WORDS; format!(r"{NAME}(?i: (?:is|are|was|has always been|have always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?(?:one of )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)s?(?: ({kind_words})s?\b|(?=\s*(?:[.,!?;:)\n]|$))))") });
re!(POSITIVE, concat!(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |seriously |genuinely |do |personally )?(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig|recommend|second|rewatched|replayed)\b|",
    r"\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big )?fan of|hooked on|in love with)\b|\bcan'?t get enough of\b|",
    r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rites?|faves?|favs?)\b|\bfell in love with\b|",
    r"\b(?:is|are|was|were) (?:so |really |very |absolutely |just |still |honestly |such an? |pretty |easily |definitely |by far )?(?:good|great|amazing|awesome|excellent|fantastic|",
    r"underrated|underappreciated|goated|incredible|perfect|beautiful|fun|peak|fire|the goat|the best|my jam|a banger|bangers|a masterpiece|a classic|brilliant|",
    r"phenomenal|gorgeous|lovely|wonderful|so fun)\b|\b(?:been|currently|finally|started) (?:playing|watching|listening to|reading|bingeing|binging|replaying|rewatching)\b|",
    r"\bfor me\b|\bmine is\b|\bhands down\b|\bthe goat\b|\bi'?m (?:playing|watching|listening to|reading|replaying|rewatching)\b)"));
re!(NEGATIVE, r"(?i:\b(?:hate|hated|don'?t like|didn'?t like|not a fan|dislike|overrated|boring|worst|trash|garbage|sucks|terrible|awful|meh|never (?:played|watched|liked))\b)");
re!(ADJACENT, concat!(r"\b(?:(?:i'?m|im|i am|i'?ve been|ive been|i'?ve always been)(?: (?:so|really|totally|completely|also|still|honestly|such|always|lowkey|kinda))* (?:obsessed with|a (?:huge |big |massive |die[- ]?hard |long[- ]?time )?fan of)|",
    r"my (?:all[- ]time |absolute |personal )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|has to be|would be))\s+",
    r"((?:the )?[\w'&:.!+-]+(?: [\w'&:.!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|it|is|was|lol|too|again|right|atm|lately|recently|these|since|for|with|on|in|at|when|while|haha|tbh|honestly|now|today)\b)"));
re!(FAN_CUE, r"(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)");
re!(FAN, format!(r"(?i:\b(?:i'm|im|i am|i was|i've been|ive been|been|as|being|become|became|becoming|grew up|growing up|raised) )(?:(?i:an? |the )(?:(?i:{DEGREE}) |(?!(?:not|never|no|an?|the|by|of|to) )[a-z][a-z'-]* ){{0,3}}|(?:(?i:{DEGREE}) ){{0,3}}){NAME}(?i: (?:fan|supporter|stan|enjoyer|fanboy|fangirl)s?\b)"));
re!(TEAM_FAN, format!(concat!(r"(?i:\b(?:(?:i'm|im|i am|i was|i've been|ive been|been|as|being|from|become|became|becoming|grew up|growing up|raised|als) |(?:fellow|{DEGREE}) ))(?:(?i:an? )(?:(?i:{DEGREE}) |(?!(?:not|never|no|an?|the|by|of|to) )[a-z][a-z'-]* ){{0,3}}|(?:(?i:{DEGREE}) ){{0,3}}){NAME}(?i: (?:fan|supporter)s?\b)|",
    r"(?:(?m:^)|(?<=[.!?] ))(?:[^\W\d_][\w'-]* ){{0,2}}?{NAME}(?i: (?:fan|supporter)(?:s? (?:here|since|for life|all my life|my whole life|through and through|lol|lmao|haha|tbh|btw|myself)\b|(?=[,.!;:]|(?m:$))))"), DEGREE = DEGREE, NAME = NAME));
re!(OWN_TEAM, format!(r"{NAME}(?i: (?:is|are|was|were|has always been|have always been|will always be) (?:still |definitely |always |forever )?my (?:home |hometown |local |second |other |first |main |real |true |only )?team\b)|(?i:\bmy (?:home |hometown |local |second |other |first |main |real |true |only )?team (?:is|are|was|has always been|will always be) (?:still |always |forever )?(?:the )?){NAME}"));
re!(FAN_OF, format!(r"(?:(?i:\b(?:i'm|im|i am|i was|i've been|ive been|i've always been|been|as) (?:also |still |definitely |honestly |really |such |always )?(?:an? |the )?(?:{DEGREE} )*(?:fan|supporter|admirer) of (?:the )?)|(?:(?m:^)|(?<=[.!?] ))(?i:(?:{DEGREE} )+fan of (?:the )?)){NAME}"));
re!(STAN, format!(r"(?i:\bi (?:also |still |will always |literally |really )?stan ){NAME}"));
re!(GOAT, format!(r"(?i:\bmy (?:all[- ]time )?goat:? ){NAME}"));
re!(LOVED, format!(concat!(r"(?i:\bi(?:'m| am)? (?:really |absolutely |just |also |still |honestly |genuinely |do |totally |fucking |friggin |freaking |freakin |fricking |effing |actually |so |personally |\w+ly )*",
    r"obsessed with ){NAME}"), NAME = NAME));
re!(LOWER_FAN, format!(r"(?i:\b(?:i'm|im|i am|i've been|ive been|as|being) (?:an? )?(?:{DEGREE} )*)((?:[a-z][\w'-]* ){{0,2}}[a-z][\w'-]*) (?:fan|stan|supporter)\b"));
re!(FAVORITE_PLAIN, { let kind_words = &*KIND_WORDS; format!(r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav) ({kind_words})s?(?: of all time| ever)? (?:is|has to be|would be|was|are)\s+")
    + r"((?:the )?[\w'&:!+-]+(?: [\w'&:!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|lol|too|tbh|honestly|by far|hands down|of all time|ever|for sure)\b)" });
re!(SPLIT, r"\s*(?:,|/|&|\band\b)\s*");
re!(POSSESSIVE, r"'s\b.*$");
re!(STOP, r"[.!?:;]\s");
re!(LISTED, r"[\s,;/&*|>()\[\]^:.\d-]{1,12}|\s*(?:,\s*)?(?:and|or)\s+");
re!(LIKED, r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |genuinely |do |personally |fucking )*(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig)|\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big |massive )?fan of|hooked on|in love with)|\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|are|was|has to be))(?: the)?\s+$");
re!(SELF, r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)");
re!(BACKING, r"(?i:\b(?:my|our|we|us|go|let'?s go|lets go|up the|c'?mon|come on|i (?:always |still |also |really |just |will always |have always |\w+ly )?(?:love|like|liked|support|supported|root for|rooted for|cheer for|follow|followed)|i'?ve (?:always |also )?(?:supported|followed|rooted for)|fan of|rooting for|cheering for|supporter of|supporting|following)(?: the| my| our| beloved| boys)?\s*$)");
re!(BACKER, r"(?i:\s*(?:for life|forever|till i die|all the way)\b)");
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
    let low = folded(&(index..index + size).map(|i| words.low(i)).collect::<Vec<_>>().join(" "));
    let aliased = |e: &Entry| folded(&joined_words(&chars_of(e.value))) != low;
    let short = tiny(&low);
    let worded = size == 1 && LEXICON.words.contains(low.as_str());
    let fictional = a.into_iter().flatten().chain(b.into_iter().flatten()).any(|e| e.attribute == "character" && !aliased(e));
    for e in a.into_iter().flatten().chain(b.into_iter().flatten()) {
        let unnamed = (short && has(&ALIASED, e.attribute) || worded && e.attribute == "artist" || fictional && e.attribute != "athlete" && has(&ALIASED, e.attribute)) && aliased(e) && !named_in(words, e.value);
        let value = if unnamed { "" } else { e.value };
        spans.push(Mention { attribute: e.attribute, start, end, value, cased: e.cased, common: e.common, links: e.links });
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
    if !value.is_empty() && surface.len() > SHORT_KEY && !same_words(&lower(surface), &value_chars) {
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
    if attribute == "character" {
        return;
    }
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
        let value = st(&value);
        if !junk_value(attribute, &value) {
            found.set(if attribute == "sports_team" { "sports_teams" } else { "fandoms" }, value, position);
        }
    }
}

fn named_in(words: &Words, value: &str) -> bool {
    let own: Vec<&str> = value.split(' ').filter(|w| w.chars().filter(|&c| is_letter(c)).count() >= 3).collect();
    (0..words.bounds.len()).any(|i| own.contains(&words.low(i)))
}

fn labelled(attribute: &str, value: &str) -> bool {
    match probe(value) {
        Probe::Entry(node) => node.entries().any(|e| e.attribute == attribute && e.value == value),
        _ => false,
    }
}

fn tiny(value: &str) -> bool {
    value.chars().filter(|&c| is_letter(c)).count() < 3 && !has_digit(value)
}

fn is_number(word: &str) -> bool {
    !word.is_empty() && word.chars().all(|c| c.is_ascii_digit())
}

fn junk_value(attribute: &str, value: &str) -> bool {
    let words: Vec<&str> = value.split(' ').filter(|w| !w.is_empty()).collect();
    if words.is_empty() || attribute == "sports_team" {
        return false;
    }
    let within = |set: &FxHashSet<&'static str>| words.iter().all(|w| set.contains(w) || is_number(w)) && words.iter().any(|w| set.contains(w));
    let every = |test: &dyn Fn(&str) -> bool| words.iter().all(|w| test(w));
    let folded_value = folded(value);
    let generic = |w: &str| GENERIC.contains(w) || COMMON.contains(w) || EDGE.contains(w);
    (has(&CALENDAR_TARGETS, attribute) && within(&CALENDAR))
        || (has(&PLATFORM_TARGETS, attribute) && every(&|w| PLATFORMS.contains(w) || PLATFORM_PART.contains(w) || is_number(w)) && words.iter().any(|w| PLATFORMS.contains(w)))
        || (has(&COLOUR_TARGETS, attribute) && every(&|w| COLOURS.contains(w)))
        || LEXICON.nations.contains(folded_value.as_str())
        || CONTINENTS.contains(&folded_value.as_str())
        || (has(&DEMONYM_TARGETS, attribute) && every(&|w| DEMONYMS.contains(w)))
        || (has(&FILLER_TARGETS, attribute) && every(&|w| COMMON.contains(w) || EDGE.contains(w) || FILLER.contains(w)))
        || (has(&GENERIC_TARGETS, attribute) && every(&generic))
        || (has(&LOWERCASE_TARGETS, attribute) && words.len() == 1 && LEXICON.words.contains(words[0]) && !capitalized(words[0]))
        || (attribute == "artist" && every(&|w| INTERJECTIONS.contains(w)) && !words.iter().any(|w| capitalized(w)))
        || (has(&ALIASED, attribute) && tiny(value) && !labelled(attribute, value))
        || (attribute == "creator" && (every(&|w| CREATOR_TERMS.contains(w) || generic(w)) || matches!(words[words.len() - 1], "stream" | "streams")))
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

thread_local! {
    static TEXT: std::cell::Cell<(usize, usize)> = const { std::cell::Cell::new((0, 0)) };
}

fn remember(text: &[char]) {
    TEXT.with(|t| t.set((text.as_ptr() as usize, text.len())));
}

fn capitalized(word: &str) -> bool {
    let (pointer, size) = TEXT.with(|t| t.get());
    if pointer == 0 {
        return true;
    }
    let text = unsafe { std::slice::from_raw_parts(pointer as *const char, size) };
    let target: Vec<char> = word.chars().collect();
    word_spans(text).into_iter().any(|(a, b)| b - a == target.len() && text[a].is_uppercase() && lower(&text[a..b]) == target)
}

re!(SPORTS_FLAIR, r"^r/(?i:cfb|collegebasketball|collegebaseball|baseball|nfl|nba|hockey|soccer|mls): :([\w-]+):[ \t]*(?::[\w-]+:[ \t]*)*([^•|:\n]+?)[ \t]*(?:•|\n|$)");
re!(GO_FLAIR, r"^r/(?i:pokemongo\w*): (?i::(mystic|valor|instinct):|(?:team )?(mystic|valor|instinct)\b)");
re!(GO_TEAM, r"\b(?:(?:i'?m|im|i am|i'?ve been|ive been|we'?re)(?: (?:also|always|still|proudly|on|in|part of|a member of))* team (mystic|valor|instinct)\b|team (mystic|valor|instinct) (?:here|for life|forever|all the way)\b|my team is (?:team )?(mystic|valor|instinct)\b)");

fn coded(code: &str, name: &str) -> bool {
    let code = code.to_lowercase();
    let code = code.trim_end_matches(|c: char| c.is_ascii_digit());
    let joined: String = name.to_lowercase().chars().filter(|c| c.is_alphanumeric()).collect();
    let initials: String = name.split_whitespace().filter_map(|w| w.chars().next()).flat_map(char::to_lowercase).collect();
    !code.is_empty() && (joined.starts_with(code) || initials == code)
}

pub fn fandom(text: &[char], found: &mut Found) {
    if let Some(m) = SPORTS_FLAIR.at(text, 0) {
        let name = m.group(2).unwrap_or(&[]);
        if coded(&st(m.group(1).unwrap_or(&[])), &st(name)) {
            named("sports_team", name, found, m.span(2).map_or(0, |(start, _)| start));
        }
    }
    if let Some(m) = GO_FLAIR.at(text, 0) {
        let team = m.nonempty(1).or(m.group(2)).unwrap_or(&[]);
        found.set("pokemon_go_team", st(&lower(team)), m.start());
    }
    let lowered = lower(text);
    crate::interests::interests(&lowered, found);
    if !contains(&lowered, "team ") {
        return;
    }
    for m in GO_TEAM.iter(&lowered) {
        if !hedged(&lowered, m.start(), m.end(), self_hedge()) {
            found.set("pokemon_go_team", st(m.nonempty(1).or(m.nonempty(2)).or(m.group(3)).unwrap_or(&[])), m.start());
        }
    }
}

pub fn adjacent(text: &[char], found: &mut Found) {
    remember(text);
    let lowered = lower(text);
    let mut totals = Totals::new(text);
    for m in ADJACENT.iter(&lowered) {
        let group = m.group(1).unwrap_or(&[]);
        let group = if starts_at(group, 0, "the ") { &group[4..] } else { group };
        let group = POSSESSIVE.sub(group, "");
        let name = strip_space(&group);
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
    remember(text);
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
            if hedged(&lowered, m.start(), m.end(), hedge) || peer(&lowered, m.start()) {
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
    let literals: [&[&str]; 4] = [&[" fan", " supporter", " stan", " enjoyer"], &["fan of", "supporter of", "admirer of"], &["stan"], &["goat"]];
    for (index, pattern) in [&*FAN, &*FAN_OF, &*STAN, &*GOAT].into_iter().enumerate() {
        if !literals[index].iter().any(|w| contains(&lowered, w)) {
            continue;
        }
        for m in pattern.iter(gate(text, match index { 0 => fanned, 1 => cues.any(masks.FAN_OF), 2 => cues.any(masks.STAN), _ => cues.any(masks.GOAT) })) {
            if hedged(&lowered, m.start(), m.end(), hedge) || peer(&lowered, m.start()) {
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
                    named(a, &v, found, m.start());
                }
            }
        }
    }
    if contains(&lowered, "obsess") && cues.any(masks.LOVED) {
        for m in LOVED.iter(text) {
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
            match lexical(name) {
                Some((a, v)) => named(a, &v, found, m.start()),
                None => {
                    for piece in parts(name) {
                        if let Some((a, v)) = classified(text, &mut totals, m.start(), &piece, &ALL_OPTIONS) {
                            named(a, &v, found, m.start());
                        }
                    }
                }
            }
        }
    }
    if contains(&lowered, " fan") || contains(&lowered, " stan") || contains(&lowered, " supporter") {
        for m in LOWER_FAN.iter(gate(text, fanned)) {
            if hedged(&lowered, m.start(), m.end(), hedge) || peer(&lowered, m.start()) {
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
    known(text, &lowered, &cues, found);
}

fn placed(name: &[char]) -> bool {
    let joined = joined_words(&lower(&folded_chars(name)));
    LEXICON.nations.contains(joined.strip_prefix("the ").unwrap_or(&joined))
}

fn peer(lowered: &[char], start: usize) -> bool {
    PEER.test_in(lowered, clause(lowered, start), start)
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
    let segments: Vec<(usize, usize)> = FAVOURED.iter(gate(text, cues.any(MASKS.FAVOURED))).map(|m| (m.end(), findc(text, '\n', m.end()).unwrap_or(text.len()))).collect();
    let mut grouped: FxHashMap<(usize, usize), Vec<(&'static str, &'static str)>> = FxHashMap::default();
    for mention in mentions(text) {
        let Mention { attribute, start, end, value, cased, common, links } = mention;
        if attribute == "sports_team" {
            if supported(text, lowered, start, end) {
                named(attribute, &chars_of(value), found, start);
            }
            continue;
        }
        if attribute == "character" || !favoured(&segments, start) || (cased && has(&SPELLED, attribute)) {
            continue;
        }
        let surface = &text[start..end];
        let titled = has(&TITLES, attribute);
        if common && links < FAMOUS_SITELINKS && !surface.contains(&' ') && !(has(&LIKABLE, attribute) && LIKED.test_in(text, start.saturating_sub(40), start)) {
            continue;
        }
        if titled && (value.chars().filter(|&c| is_word_char(c)).count() <= 2 || plain_title(lex, surface)) {
            continue;
        }
        if (has(&LOOSE, attribute) && !cased && common && links < FAMOUS_SITELINKS && islower(surface)) || (attribute == "franchise" && islower(surface) && surface.iter().any(|&c| isdigit(&[c]))) {
            continue;
        }
        grouped.entry((start, end)).or_default().push((attribute, value));
    }
    let mut spans: Vec<((usize, usize), Vec<(&'static str, &'static str)>)> = grouped.into_iter().collect();
    spans.sort();
    let mut totals = Totals::new(text);
    for ((start, end), options) in spans {
        for (attribute, value) in chosen(text, start, options, &mut totals) {
            if !(attribute == "video_game" && othered(lowered, start, end)) && (has(&PLAYED, attribute) || !hedged(lowered, start, end, self_hedge())) {
                named(attribute, &shown(&text[start..end], value), found, start);
            }
        }
    }
}

pub fn init() {
    for index in 0..PATTERN_COUNT {
        pattern(index);
    }
    for re in [&TRAILING, &FAVORITE, &FAVORED, &POSITIVE, &NEGATIVE, &ADJACENT, &FAN, &TEAM_FAN, &FAN_OF, &STAN, &GOAT, &LOVED, &LOWER_FAN, &OWN_TEAM, &FAVORITE_PLAIN, &SPLIT, &POSSESSIVE, &STOP,
        &LISTED, &LIKED, &SELF, &BACKING, &BACKER, &SEASON, &ATTENDED, &FANNED, &AVOWED, &OWNED, &PEER, &FAVOURED, &SPORTS_FLAIR, &GO_FLAIR, &GO_TEAM] {
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
