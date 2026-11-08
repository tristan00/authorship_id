use crate::fandom::{chars_of, first_piece, join_words, positive_starts, re_split, CANDIDATE, COMMON, NAME, NEGATIVE, SELF, TRAILING};
use crate::cues::{cues_of, MASKS};
use crate::lexicon::*;
use claimcore::*;
use claimcore::schema::fan_value;
use rustc_hash::{FxHashMap, FxHashSet};
use std::sync::LazyLock;

const KIND: &str = r"(?:characters?|chars?|pokemon|pokémon|heroe?s?|heroines?|villains?|antagonists?|protagonists?|waifus?|husbandos?|girls?|boys?|champions?|champs?|agents?|operators?|legends?|survivors?|killers?|servants?|units?|fighters?|brawlers?|princess(?:es)?|princes?|digimon|starters?|legendar(?:y|ies)|gundams?|mobile suits?|mechs?|robots?|monsters?|bosses|boss|companions?|npcs?|ships?|couples?|pairings?|duos?|ninjas?|shadows?|mains?|5 stars?|5\*|4 stars?|4\*|warframes?|frames?|resonators?|valkyries?|idols?|trainers?|gym leaders?|members?|ocs?|dolls?|figures?|mcs?|mc's|commanders?|leaders?|picks?)";
const TIER: &str = r"(?:all[- ]time |absolute |personal |current |top |new |second |2nd |third |3rd |most |favou?rite |very |)*";
const FAVOURITE: &str = r"(?:favou?rites?|faves?|favs?|fav(?:ou?)?rite|fave?ou?rite)";
const ADVERB: &str = r"(?:really |absolutely |just |also |still |honestly |genuinely |do |totally |fucking |friggin |so |personally |lowkey |low key |kinda |kind of |sort of |sorta |actually |always |will always |definitely |truly |only |even |especially |generally |particularly |simply |mostly |mainly |secretly |unironically |legit |def |deeply |too |)*";
const ANY: &str = r"((?:[Tt]he )?[\w'.&+-]+(?: [\w'.&+-]+){0,3})";
const ADJECTIVAL: &str = r"(?:characters?|quests?|story|storyline|menu|thread|events?|reason|issues?|problems?|point|focus|goals?|cast|villains?|antagonists?|protagonists?|heroe?s?|heroines?|plot|themes?|road|street|entrance|course|dish|page|account|sub|line|stats?|weapons?|deck|team|job|class|game|mode|campaign|boss|area|hub|city|base|source|thing|things|part|parts|topic|topics|hobb(?:y|ies)|kinks?|car|language|value|tips?|riff|attraction|draw|selling point|ingredient|pon(?:y|ies))";
const POSITIVE: &str = r"(?:good|great|cool|amazing|awesome|interesting|fun|compelling|lovable|loveable|likable|likeable|well[- ]written|underrated|beautiful|fantastic|wonderful|best|fascinating|incredible|complex|badass|hilarious|funny|sweet|cute|adorable|perfect|brilliant|iconic|memorable|relatable|unique|fire|peak|goated|elite|top tier|god tier|strong|nice|hot|sexy|fine|gorgeous|lovely|precious|baddest|coolest|hottest|cutest|greatest|realest|funniest)";
const MEDIA: &str = r"(?i:series|movies?|films?|games?|franchise|books?|novels?|shows?|music|songs?|albums?|level design|scents?|lore|universe|trilogy|saga|comics?|manga|anime|cartoons?|era|style|soundtrack|ost|band|brand|products?|stuff|team|version|remake|reboot|episodes?|seasons?|chapters?)";
const DEAR: &str = r"(?:king|queen|baby|babygirl|wife|husband|man|boy|girl|everything|beloved|goat|son|daughter|husbando|waifu|bae|crush|princess|prince|goddess|pookie|precious|love|one true love|comfort character)";

const GENERIC_WORDS: &str = "i i'm im me my mine you your he him his she her they them their we us our it its it's this that these those the a an all any every everyone everything some someone something one ones \
character characters game games show anime manga movie film series book books guy guys girl girls boy boys man woman people dude bro lol ok okay yes no yeah here there \
now today then also just really very so much more most both either each other others another what who how why when where which not no none nothing \
playing play using use being having doing going getting watching reading such only neither hello calling absolutely probably actually seriously totally truly genuinely \
perhaps sometimes always lately currently recently especially mostly mainly usually basically obviously clearly surely personally easily";
const ROLES_WORDS: &str = "support supports tank tanks dps healer healers heal jungle jungler mid top adc bot carry assassin assassins mage mages marksman fighter fighters \
melee ranged caster casters sniper snipers striker defender attacker sword spear bow gun guns hammer lance axe axes staff dagger daggers fist fists \
random it them her him killer killers survivor survivors";
const CUES_WORDS: &str = "love loved adore adored enjoy enjoyed like liked dig recommend second rewatched replayed obsessed addicted into fan hooked enough favorite favorites favourite favourites fave faves fav favs fell \
good great amazing awesome excellent fantastic underrated underappreciated goated incredible perfect beautiful fun peak fire goat best jam banger bangers masterpiece classic brilliant phenomenal \
gorgeous lovely wonderful playing watching listening reading bingeing binging replaying rewatching mine hands";

const CALENDAR_WORDS: &str = "january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday today tonight tomorrow yesterday morning afternoon evening night noon midnight weekend week month year day hour minute second time season summer winter spring autumn fall christmas xmas halloween easter thanksgiving valentine valentines hanukkah ramadan diwali birthday holiday holidays";

fn nouns() -> String {
    format!(r"(?:{MEDIA}|ways?|things?|parts?|moments?|segments?|lines?|quotes?|scenes?|models?|builds?|places?|foods?|drinks?|colou?rs?|flavou?rs?|brands?|cars?|days?|times?|kinds?|types?|sets?|cards?|items?|weapons?|maps?|levels?|modes?|classes|races|factions?|guns?|looks?|players?|teams?|athletes?|drivers?|bands?|singers?|artists?|authors?|writers?|actors?|actress(?:es)?|youtubers?|streamers?|podcasts?|channels?)")
}

pub struct Tables {
    characters: FxHashMap<&'static str, i64>,
    surfaces: FxHashMap<&'static str, i64>,
    lowercased: FxHashMap<String, &'static str>,
    named: FxHashSet<String>,
    plurals: FxHashSet<&'static str>,
    initials: FxHashSet<&'static str>,
    others: FxHashSet<String>,
    generic: FxHashSet<&'static str>,
    roles: FxHashSet<&'static str>,
    cues: FxHashSet<&'static str>,
    calendar: FxHashSet<&'static str>,
}

fn build() -> Tables {
    let data: &'static str = leak(data_file("character_names.tsv"));
    let mut characters = FxHashMap::default();
    let mut surfaces: FxHashMap<&'static str, i64> = FxHashMap::default();
    let mut lowercased = FxHashMap::default();
    let mut named = FxHashSet::default();
    let mut plurals = FxHashSet::default();
    let mut initials = FxHashSet::default();
    for line in data.lines().skip(1) {
        let fields: Vec<&'static str> = line.split('\t').collect();
        let (key, value, links, cased, common) = (fields[0], fields[2], fields[3].parse::<i64>().unwrap(), fields[4], fields[5]);
        if key.chars().count() < 3 && key != value {
            initials.insert(key);
        }
        if key.strip_suffix('s') == Some(value) {
            plurals.insert(key);
        }
        if cased.is_empty() {
            characters.insert(key, links);
            continue;
        }
        for surface in cased.split('|') {
            let slot = surfaces.entry(surface).or_insert(links);
            *slot = (*slot).max(links);
            let chars = chars_of(surface);
            if links >= 3 && common.is_empty() && isalpha(&chars) && istitle(&chars) {
                lowercased.insert(surface.to_lowercase(), surface);
                if key == value {
                    named.insert(surface.to_lowercase());
                }
            }
        }
    }
    let lex: &'static Lexicon = &LEXICON;
    let mut others: FxHashSet<String> = FxHashSet::default();
    for (key, entries) in &lex.plain {
        if entries.iter().all(|e| e.attribute != "character") {
            others.insert(key.to_string());
        }
    }
    for (surface, entries) in &lex.cased {
        if entries.iter().all(|e| e.attribute != "character") {
            others.insert(surface.to_lowercase());
        }
    }
    let mut generic: FxHashSet<&'static str> = GENERIC_WORDS.split_whitespace().collect();
    generic.extend(COMMON.iter().copied());
    Tables {
        characters,
        surfaces,
        lowercased,
        named,
        plurals,
        initials,
        others,
        generic,
        roles: ROLES_WORDS.split_whitespace().collect(),
        cues: CUES_WORDS.split_whitespace().collect(),
        calendar: CALENDAR_WORDS.split_whitespace().collect(),
    }
}

static TABLES: LazyLock<Tables> = LazyLock::new(|| timed("character lexicon", build));

macro_rules! re {
    ($name:ident, $pat:expr) => {
        static $name: LazyLock<Re> = LazyLock::new(|| Re::new(&$pat));
    };
}

re!(STOP, r"[.!?:;\n(]|(?i:\s(?:and then|right there|here|there|but|because|cause|bc|since|who|which|that|when|as|from|in|on|at|is|was|are|were|so|too|for|with|lol|lmao|haha|tbh|honestly|now|though|tho|more|the most|a lot|much|over|than|if|to|by|of all time|ever|right now|atm|i|he|she|they|it|my)\b)");
re!(LISTED, r"\s*(?:,|/|&|\band\b|\bor\b|\bx\b)\s*");
re!(STRONG, concat!(r"(?i:\b(?:characters?|char|main|maining|mains|mained|waifu|husbando|ship|shipped|shipping|otp|arc|villain|protagonist|antagonist|cosplay|kit|banner|pulls?|pulled|lore|canon|fanart|fan art|",
    r"backstory|personality|design|voice lines?|skins?|pokemon|pokémon|hero|heroes|champions?|anime|manga|episode|season|chapter)\b)"));
re!(ASPECT, r"\s*(?i:character|design|personality|arc|voice|story|storyline|kit|outfit|look|vibe|energy|backstory|lines?|scenes?|moments?|dialogue|development|growth|fights?|theme|attitude|animations?|abilities|ability|skills|model|portrayal|combat|gameplay|playstyle|moveset|powers?|humou?r|relationship|dynamic|interactions?|expressions?|smile|face|hair|eyes|laugh|style|aesthetic|songs?|ult|ultimate|skins?|art|writing|journey|redemption|quotes?)\b");
re!(NUMERAL, r"\d+(?:st|nd|rd|th|s|am|pm)$|(?:19|20)\d\d$");
re!(POSSESSED, r"(?:'s|s'|’s)\b.*$");
re!(ARTICLE, r"^(?:[Tt]he|[Mm]y|[Oo]ur|[Ff]ellow|[Aa]s an?|[Aa]n?) ");
re!(DETERMINER, r" (?:the|a|an|this|that|some|every|all|other|last|next) ");
re!(LETTER, r"[^\W\d_]");
re!(BLANK, r"\n[ \t]*\n");
re!(REFERRED, r"(?i:\bi (?:\w+ ){0,2}(?:love|adore|like|stan|loved|adored|liked|enjoy|miss|respect) (?:her|him)\b)");
re!(PRONOUN_I, r"I(?:'m|'ve|'d|'ll)?$");
re!(NAMED, NAME);
re!(CLAUSE, r"[^.!?\n]+[.!?]*");
re!(PARAGRAPH, r"(?:[^\n]|\n(?![ \t]*\n))+");
re!(CHEER, format!(r"(?m:(?:^|[.!?]\s+)[\W_]*(?:(?i:absolutely |really |just |still |totally |fucking |fuckin |so |gotta |truly |honestly |)(?:[Ll]ove|LOVE|[Aa]dore|ADORE) |(?i:hell yeah|hell yes|let'?s go|justice for|respect for|protect|love for|all hail|long live|w) )){NAME}(?=[^\w\n]*(?:\n|$)|\s*[.!?,;:)]| (?i:so much|forever|always|tho|though|too)\b)"));
re!(CHEERED, r"(?:[Ll]ove|LOVE|[Aa]dore|ADORE|(?i:hell yeah|hell yes|let'?s go|justice for|respect for|protect|all hail|long live|w)) (?:[Tt]he )?[A-Z0-9]");
re!(HONORIFIC, r"^(?i:mr|mrs|ms|mx|dr|sr|jr|st|prof|sgt|lt|capt)\.?$");
re!(NUMBERED, r"^(?i:(?:number|no\.?|#)\s*)?(?i:\d+|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|last)$");
re!(INTERJECTION, r"^(?i:hell|heck|damn|dang|darn|gosh|jeez|geez|wow|omg|lol|lmao|haha|yay|ugh|oh|ah|hey|hi|thanks|please|sorry|yeah|yes|nope|nah|yep|welp|whoa|ouch|oops|bruh)$");
re!(KINSHIP, r"^(?i:mom|mum|mommy|mummy|mother|dad|daddy|father|papa|mama|sister|sis|brother|bro|wife|husband|hubby|son|daughter|grandma|grandpa|granny|grandmother|grandfather|aunt|auntie|uncle|cousin|niece|nephew|boyfriend|girlfriend|bf|gf|kid|kids|kiddo|child|children|homie|buddy|friend|bestie)$");
re!(ANIMAL, r"^(?i:cat|cats|kitty|kitten|kittens|dog|dogs|doggo|puppy|puppies|pup|bunny|rabbit|horse|pony|bird|fish|hamster|mouse|rat|snake|lizard|turtle|frog|duck|cow|pig|goat|sheep|chicken|fox|wolf|bear|lion|tiger|monkey|parrot)$");
re!(CATEGORY, r"^(?i:pok[eé]mon|digimon)s?$");
re!(BARE, r"(?:^|[^\w'-])(?i:the|a|an|to|this|that|some|any) $");

#[derive(Clone, Copy, PartialEq)]
enum Gate {
    Any,
    Known,
    Medium,
    Named,
    Rare,
}

struct Stage {
    re: Re,
    gate: Gate,
    needs: Vec<Vec<&'static str>>,
    avoids: &'static [&'static str],
}

const I_SET: &[&str] = &["i"];
const MY: &[&str] = &["my"];
const MAINS: &[&str] = &["main", "mains", "mained", "maining", "trick", "onetrick", "twotrick", "otp"];
const FAVS: &[&str] = &["fav", "favs", "fave", "faves", "favorite", "favorites", "favourite", "favourites", "favrite", "favrites", "faveorite", "faveourite"];
const LIKES: &[&str] = &["love", "loved", "adore", "adored", "like", "liked", "stan", "simp", "prefer", "obsessed", "sucker", "soft", "thing"];
const DEARS: &[&str] = &["king", "queen", "baby", "babygirl", "wife", "husband", "man", "boy", "girl", "everything", "beloved", "goat", "son", "daughter", "husbando", "waifu", "bae", "crush", "princess", "prince", "goddess", "pookie", "precious", "love", "true", "comfort"];
const CHARMING: &[&str] = &["cute", "adorable", "hot", "sexy", "fine", "badass", "goated", "peak", "mommy", "daddy", "queen", "king", "girl", "boy", "precious", "lovable", "loveable", "baddie", "slay", "iconic", "underrated", "legend", "goat", "gorgeous", "beautiful", "stunning", "handsome", "cutest", "hottest", "sexiest", "prettiest", "sweetest", "coolest", "baddest", "cutie", "sweetheart", "menace", "wholesome", "endearing", "charming", "favorite", "fave", "fav", "favourite", "best", "greatest"];
const HEARTS: &[&str] = &["<3", "❤", "♥", "💕", "💖", "💜", "💙", "💛", "💚", "🩷", "😍", "🥰"];
const RARE: &[&str] = &[];
const RANDOMIZER: &[&str] = &["roll", "rolled", "rolling", "random", "randomizer", "wheel", "spin", "spun"];

fn with(base: &[&'static str], extra: &[&'static str]) -> Vec<&'static str> {
    base.iter().chain(extra.iter()).copied().collect()
}

fn stage(pattern: String, gate: Gate, needs: Vec<Vec<&'static str>>) -> Stage {
    Stage { re: Re::new(&pattern), gate, needs, avoids: &[] }
}

fn avoiding(stage: Stage, avoids: &'static [&'static str]) -> Stage {
    Stage { avoids, ..stage }
}

static STAGES: LazyLock<Vec<Stage>> = LazyLock::new(|| {
    let nouns = nouns();
    let v = |s: &[&'static str]| s.to_vec();
    use Gate::*;
    vec![
        stage(format!(r"(?i:\bi(?:'m| am)? (?:also |still |mostly |mainly |usually |always |only |just |now |currently |exclusively |primarily )?(?:main|mained|maining|one[- ]?trick|two[- ]?trick|otp|play as|playing as) ){ANY}"), Any, vec![v(I_SET), with(MAINS, &["play", "playing"])]),
        stage(format!(r"(?:(?i:\b(?:an?|as an?|fellow|other|us|we|i'?m an?|im an?|i am an?|i'?m|i am|im|been an?|being an?|i play) ))({NAME}|[a-z][\w'-]*)(?i: (?:main|mains|one[- ]?trick|two[- ]?trick|otp)\b(?! {ADJECTIVAL}))"), Any, vec![v(MAINS)]),
        stage(format!(r"(?m:^[\W_]*){NAME}(?i: (?:main|mains|otp|one[- ]?trick)(?= here\b| btw\b| and\b| since\b| for\b| who\b|\s*[,.!:\n]|\s*$))"), Any, vec![v(MAINS)]),
        stage(format!(r"(?i:\bmy (?:current |new |og |first |only )?(?:mains?|main character|main girl|main boy|one[- ]?trick)(?: (?:is|are|was|has been|have been|include|includes|remains)|:)\s+){ANY}"), Any, vec![v(MY), v(MAINS)]),
        stage(format!(r"(?i:\bi (?:mostly |usually |always |only |mainly |still |also |)(?:play|played) ){NAME}"), Known, vec![v(I_SET), vec!["play", "played"]]),
        stage(format!(r"(?i:\bi (?:mostly |usually |always |only |mainly |still |also |)(?:use|used) ){NAME}(?<! to)(?! (?i:to|for)\b)"), Known, vec![v(I_SET), vec!["use", "used"]]),
        stage(format!(r"(?i:\b(?:one of )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}(?: of all time| ever| right now| atm| at the moment| so far| by far| in the (?:game|show|series|anime|manga|book))? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*){ANY}"), Any, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\b(?:one of )?my {TIER}{FAVOURITE}(?: of all time| ever| right now| atm| at the moment| so far| by far)? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*|\b(?:other )?{FAVOURITE} of mine (?:are|include|is)\s+){NAME}"), Medium, vec![v(FAVS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|was|were|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), Any, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i:, (?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), Known, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) {KIND},? ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), Known, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i:,? (?:are |is |)(?:also |definitely |)(?:one of|among|some of) my {TIER}{FAVOURITE}\b(?! (?:\w+ ){{0,2}}{nouns}\b))"), Medium, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), Medium, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}(?:{FAVOURITE}|goat|comfort character|top \d)s?\b(?! (?:\w+ ){{0,2}}{nouns}\b))"), Medium, vec![v(MY), with(FAVS, &["goat", "goats", "comfort", "top"])]),
        stage(format!(r"(?im:^\W*(?:my )?{FAVOURITE} (?:\w+ )?{KIND}\W*[:=-]\s*){NAME}"), Any, vec![v(FAVS)]),
        stage(format!(r"(?i:\bbest (?:girl|boy|waifu|husbando)s?,? (?:is |goes to |= |: |)){NAME}|{NAME}(?i:,? (?:is |= )?(?:the |my |)best (?:girl|boy|waifu|husbando)\b)"), Any, vec![vec!["best"], vec!["girl", "girls", "boy", "boys", "waifu", "waifus", "husbando", "husbandos"]]),
        stage(format!(r"{NAME},? (?i:my (?:beloved|one true love|comfort character|precious|(?:glorious |beloved |)(?:goat|king|queen|waifu|husbando|babygirl))\b)"), Any, vec![v(MY), vec!["beloved", "true", "comfort", "precious", "goat", "king", "queen", "waifu", "husbando", "babygirl"]]),
        stage(format!(r"(?i:\bmy (?:beloved|precious|glorious|queen|king|goddess|husbando|waifu|princess|prince|pookie|goat|boi|bbg) ){NAME}"), Any, vec![v(MY), vec!["beloved", "precious", "glorious", "queen", "king", "goddess", "husbando", "waifu", "princess", "prince", "pookie", "goat", "boi", "bbg"]]),
        stage(format!(r"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |)my {DEAR}\b)"), Any, vec![v(MY), v(DEARS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |also |)my (?:[a-z-]+ ){{1,2}}(?:{DEAR}|hero|heroine)\b)"), Known, vec![v(MY), with(DEARS, &["hero", "heroine"])]),
        stage(format!(r"(?i:\b(?:i(?:'m| am|'ll|'ve| have)?|im) {ADVERB}(?:lo+ve|adore|like|lo+ved|adored|liked|stan|simp for|prefer|obsessed with|am a sucker for|have a soft spot for|have a thing for|(?:had|have|developed) a (?:huge |big |massive |little |small |slight |)crush on) ){NAME}\b"), Named, vec![with(I_SET, &["im"]), with(LIKES, &["loove", "looove", "loooove", "crush"])]),
        stage(format!(r"(?i:\bi {ADVERB}(?:love|adore|like|loved|liked|adored) (?:how|that|when|the way) ){NAME}"), Medium, vec![v(I_SET), vec!["love", "adore", "like", "loved", "liked", "adored"], vec!["how", "that", "when", "way"]]),
        stage(format!(r"{NAME}(?i:(?:'s| is| was|,)? (?:such |so |soo+ |a |an |the |one of the |my |honestly |really |genuinely |easily |still |also |very |pretty |fucking |most |)*{POSITIVE}(?:(?:,| and|, and) (?:most |very |so |)\w+)? (?:characters?|char|protagonist|villain|antagonist|hero|heroine|girl|boy|design)\b| as a character\b)"), Medium, vec![vec!["character", "characters", "char", "protagonist", "villain", "antagonist", "hero", "heroine", "girl", "boy", "design"]]),
        stage(format!(r"(?i:\b(?:i'?m|im|i am|as|been|being|i've been|from) (?:an? |the )?(?:huge |big |massive |die[- ]?hard |long ?time |proud |true |real |giant |hardcore |super |casual |)*){NAME}(?i: (?:fan|stan|fanboy|fangirl|simp|lover|enjoyer)s?\b)"), Known, vec![vec!["fan", "fans", "stan", "stans", "fanboy", "fanboys", "fangirl", "fangirls", "simp", "simps", "lover", "lovers", "enjoyer", "enjoyers"]]),
        stage(format!(r"(?m:^[\W_]*){NAME}(?=\s*(?:<3|❤|♥|💕|💖|💜|💙|💛|💚|🩷|😍|🥰))"), Known, vec![v(HEARTS)]),
        stage(format!(r"{NAME}(?i:(?:'s| is| was| are|'re) (?:so |such |soo+ |a |an |the |honestly |really |genuinely |literally |just |fucking |damn |very |pretty |still |always |ultimate |absolute |)*(?:cute|adorable|hot|sexy|fine|badass|goated|peak|mommy|daddy|my queen|my king|best girl|best boy|precious|lovable|loveable|baddie|slay|iconic|underrated|a legend|the goat|my goat|gorgeous|beautiful|stunning|handsome|cutest|hottest|sexiest|prettiest|sweetest|coolest|baddest|a cutie|a sweetheart|a queen|a king|a menace|wholesome|endearing|charming|my favorite|my fave|my fav|my favourite|the best|the greatest|the coolest)\b)"), Known, vec![v(CHARMING)]),
        stage(format!(r"(?m:^[\W_]*){NAME}(?i:,? (?:for me|of course|100%|1000%|all the way|hands down|all day|no contest|every time|any day|without a doubt|no question|for sure|by far|ftw|supremacy|for the win|forever))(?=[^\w\n]*(?:\n|$)|\s*(?:[.!?,;:)]| tbh\b| imo\b| lol\b))"), Medium, vec![vec!["me", "course", "100", "1000", "way", "hands", "day", "contest", "time", "doubt", "question", "sure", "far", "ftw", "supremacy", "win", "forever"]]),
        stage(format!(r"(?i:\b(?:i(?:'m| am|'ve| have)?|im) {ADVERB}(?:enjoy|enjoyed|enjoying|miss|missed|respect|admire|admired|appreciate|support|root for|rooting for|ship|shipped|worship|cherish|treasure|idolize|vibe with|relate to|connect with|been obsessed with|fell in love with|fallen in love with|in love with|into|a fan of|a big fan of|a huge fan of|a massive fan of|such a fan of|so into) ){NAME}\b"), Named, vec![with(I_SET, &["im"]), vec!["enjoy", "enjoyed", "enjoying", "miss", "missed", "respect", "admire", "admired", "appreciate", "support", "root", "rooting", "ship", "shipped", "worship", "cherish", "treasure", "idolize", "vibe", "relate", "connect", "obsessed", "fell", "fallen", "love", "into", "fan"]]),
        stage(format!(r"(?i:\bmy (?:[a-z]\d |e\d |c\d |s\d |shiny |new |first |lil |little |baby |sweet |precious |poor |)){NAME}"), Rare, vec![v(MY), v(RARE)]),
        stage(format!(r"(?<!you )(?<!can )(?<!to )(?<!they )(?<!we )(?<!he )(?<!she )(?i:\b(?:playing|play|played) as |\b(?:like|love|enjoy|prefer|liked|loved|enjoyed|preferred) (?:to play|playing) ){NAME}(?=\s*(?:[.,!?;:)|(\[\n]|$| (?:and|or|because|cause|bc|since|for|as|from|in)\b))"), Known, vec![vec!["playing", "play", "played"], vec!["as", "like", "love", "enjoy", "prefer", "liked", "loved", "enjoyed", "preferred"]]),
        stage(format!(r#"(?m:(?:^|[.!?]\s+)[\W_]*)(?i:for me(?: personally)?,? it(?:'s| is| has to be| would be| was))\s*[*_"]*{NAME}(?=\s*(?:[.,!?;:)|(\[\n]|$| (?:and|or|because|cause|bc|since|for|as|from|in)\b))"#), Known, vec![vec!["for"], vec!["me"], vec!["it"]]),
        stage(format!(r"(?i:\bi (?:also |really |personally |honestly |just |always |)find ){NAME}(?i: (?:the |so |really |very |most |super |incredibly |extremely |)(?:attractive|hot|cute|sexy|adorable|interesting|fascinating|compelling|relatable|hilarious|funny|charming|endearing|gorgeous|beautiful)\b)"), Known, vec![v(I_SET), vec!["find"]]),
        stage(format!(r"(?i:\bi(?:'m| am) (?:also |definitely |firmly |always |still |)team ){NAME}"), Known, vec![v(I_SET), vec!["team"]]),
        stage(format!(r"(?i:\bmy ){NAME}(?i: cosplay)|{NAME}(?i: (?:cosplay|fan ?art|drawing) (?:by|from) me\b)|(?i:\bi (?:\w+ )?(?:made|did|finished|wore) (?:a|an|my) ){NAME}(?i: cosplay)|(?i:\bi(?:'m| am| was|'ve been)? (?:\w+ )?cosplay(?:ed|ing)? (?:as|of) ){NAME}"), Any, vec![vec!["cosplay", "cosplays", "cosplayed", "cosplaying", "cosplayer", "cosplayers", "fanart", "art", "drawing"]]),
        stage(format!(r"\^\((?i:me):\s*{NAME}\)"), Known, vec![vec!["me"]]),
        avoiding(stage(format!(r"(?i:\bi(?:'d|'ll| would| will)? (?:also |probably |personally |definitely |always |would |)(?:pick|picked|choose|chose|go with|went with) ){NAME}(?=\s*(?:[.,!;:)\n]|$| (?:because|cause|bc|since|for sure|every time|any day|hands down|easily|obviously)\b))"), Known, vec![v(I_SET), vec!["pick", "picked", "choose", "chose", "go", "went"]]), RANDOMIZER),
    ]
});

fn known(name: &[char], least: i64) -> bool {
    let tables = &*TABLES;
    let low = st(&lower(name));
    let plain = tables.characters.get(low.as_str()).copied().unwrap_or(-1);
    let cased = tables.surfaces.get(st(name).as_str()).copied().unwrap_or(-1);
    plain.max(cased) >= least
}

fn other(name: &[char]) -> bool {
    TABLES.others.contains(&st(&lower(name)))
}

fn foreign(name: &[char]) -> bool {
    other(name) && !known(name, 0)
}

fn pieces(name: &[char], last: bool) -> Vec<Vec<char>> {
    let tables = &*TABLES;
    let mut padded = vec![' '];
    padded.extend_from_slice(name);
    padded.push(' ');
    let head = if last { STOP.split_last(&padded) } else { first_piece(&STOP, &padded) };
    let head = POSSESSED.sub(strip_space(head), "");
    let mut result = Vec::new();
    for raw in re_split(&LISTED, &head) {
        let unarticled = ARTICLE.sub(raw, "");
        let trimmed = TRAILING.sub(&unarticled, "");
        let mut piece: Vec<char> = strip_chars(&trimmed, " *_\"'()[]~").to_vec();
        if islower(&piece) {
            let before = re_split(&DETERMINER, &piece)[0].to_vec();
            let words = split_ws(&before);
            piece = join_words(&words[..words.len().min(3)]);
        }
        let low = lower(&piece);
        let words = split_ws(&low);
        if words.is_empty() {
            continue;
        }
        let first = st(words[0]);
        let final_word = st(words[words.len() - 1]);
        if !tables.generic.contains(first.as_str()) && !tables.generic.contains(final_word.as_str()) && !tables.roles.contains(st(&low).as_str())
            && 1 < piece.len() && piece.len() <= 40 && LETTER.test(&piece) && NUMERAL.at(words[0], 0).is_none() {
            result.push(piece);
        }
    }
    result
}

fn sentence(text: &[char], position: usize) -> (usize, usize) {
    (last_mark(text, position, ".!?\n"), next_mark(text, position + 1, ".!?\n"))
}

fn emit(name: &[char], found: &mut Found, text: &[char], position: usize, gate: Gate, last: bool) {
    let tables = &*TABLES;
    for piece in pieces(name, last) {
        let low = st(&lower(&piece));
        if location::geographic(&low) || tables.calendar.contains(low.as_str()) || CATEGORY.test(&piece) || HONORIFIC.test(&piece) || NUMBERED.test(&piece) || INTERJECTION.test(&piece) || KINSHIP.test(&piece) || ANIMAL.test(&piece) || tables.plurals.contains(low.as_str()) || tables.initials.contains(low.as_str()) && { let (a, b) = sentence(text, position); !STRONG.test_in(text, a, b) } || demographics::ETHNICITIES.contains_key(low.as_str()) {
            continue;
        }
        match gate {
            Gate::Known if other(&piece) || !known(&piece, 1) => continue,
            Gate::Medium if !known(&piece, 0) && (foreign(&piece) || { let (a, b) = sentence(text, position); !STRONG.test_in(text, a, b) }) => continue,
            Gate::Named if foreign(&piece) => continue,
            Gate::Rare if other(&piece) || !tables.named.contains(&st(&lower(&piece))) => continue,
            _ => {}
        }
        if let Some(value) = fan_value("character", &lower(&piece)) {
            found.set("character", st(&value), position);
        }
    }
}

fn word_tokens(buffer: &str) -> FxHashSet<&str> {
    let mut words: FxHashSet<&str> = FxHashSet::with_capacity_and_hasher(buffer.len() / 3 + 4, Default::default());
    let bytes = buffer.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        let b = bytes[index];
        if b.is_ascii_lowercase() || b.is_ascii_digit() {
            let start = index;
            while index < bytes.len() && (bytes[index].is_ascii_lowercase() || bytes[index].is_ascii_digit()) {
                index += 1;
            }
            words.insert(&buffer[start..index]);
            continue;
        }
        if b == b'<' && bytes.get(index + 1) == Some(&b'3') {
            words.insert(&buffer[index..index + 2]);
            index += 2;
            continue;
        }
        if b < 0x80 {
            index += 1;
            continue;
        }
        let c = buffer[index..].chars().next().unwrap();
        let size = c.len_utf8();
        if "❤♥💕💖💜💙💛💚🩷😍🥰".contains(c) {
            words.insert(&buffer[index..index + size]);
        }
        index += size;
    }
    words
}

fn disjoint(words: &FxHashSet<&str>, set: &[&str]) -> bool {
    !set.iter().any(|w| words.contains(*w))
}

fn run_stage(stage: &Stage, text: &[char], found: &mut Found, lowered: &[char]) {
    for m in stage.re.iter(text) {
        let Some(index) = m.first_index() else {
            continue;
        };
        let group = m.group(index).unwrap();
        let (_, group_end) = m.span(index).unwrap();
        if (ends_at(group, group.len(), "'s") || ends_at(group, group.len(), "s'")) && group_end == m.end() && ASPECT.at(text, m.end()).is_none() {
            continue;
        }
        if !hedged(lowered, m.start(), m.end(), self_hedge()) {
            emit(group, found, text, m.start(), stage.gate, group_end < m.end());
        }
    }
}

fn recased(text: &[char], words: &FxHashSet<&str>) -> Vec<char> {
    let tables = &*TABLES;
    let mut text = text.to_vec();
    for word in words {
        let Some(surface) = tables.lowercased.get(*word) else {
            continue;
        };
        let needle = chars_of(word);
        let replacement = chars_of(surface);
        let outside = |c: char| !(is_word_char(c) || c == '\'' || c == '-');
        let mut out = Vec::with_capacity(text.len());
        let mut index = 0;
        let mut last = 0;
        while index + needle.len() <= text.len() {
            if text[index..index + needle.len()] == needle[..] && (index == 0 || outside(text[index - 1])) && (index + needle.len() == text.len() || outside(text[index + needle.len()])) {
                out.extend_from_slice(&text[last..index]);
                if BARE.test_in(&text, index.saturating_sub(6), index) {
                    out.extend_from_slice(&needle);
                } else {
                    out.extend_from_slice(&replacement);
                }
                index += needle.len();
                last = index;
            } else {
                index += 1;
            }
        }
        if last > 0 {
            out.extend_from_slice(&text[last..]);
            text = out;
        }
    }
    text
}

fn referred(text: &[char], found: &mut Found, lowered: &[char], words: &FxHashSet<&str>) {
    if !words.contains("i") || disjoint(words, &["her", "him"]) || disjoint(words, &["love", "adore", "like", "stan", "loved", "adored", "liked", "enjoy", "miss", "respect"]) {
        return;
    }
    for m in REFERRED.iter(text) {
        if hedged(lowered, m.start(), m.end(), self_hedge()) {
            continue;
        }
        let from = BLANK.iter_in(text, 0, m.start()).last().map_or(0, |b| b.end());
        let scope = &text[from.min(m.start())..m.start()];
        let mut names: Vec<&[char]> = Vec::new();
        for name in NAMED.iter(scope) {
            let group = name.group(1).unwrap_or(&[]);
            if PRONOUN_I.at(group, 0).is_none() && !pieces(group, false).is_empty() {
                names.push(group);
            }
        }
        if let Some(name) = names.last() {
            emit(name, found, text, m.start(), Gate::Medium, false);
        }
    }
}

fn liked(text: &[char], found: &mut Found, words: &FxHashSet<&str>, possible: bool) {
    let tables = &*TABLES;
    if !tables.cues.iter().any(|w| words.contains(*w)) && !(words.contains("for") && words.contains("me")) {
        return;
    }
    if !possible {
        return;
    }
    let starts = positive_starts(text);
    if starts.is_empty() {
        return;
    }
    let single = STRONG.test(text);
    let mut cue = 0;
    for part in CLAUSE.iter(text) {
        let mut exhausted = false;
        while starts[cue] < part.start() {
            cue += 1;
            if cue == starts.len() {
                exhausted = true;
                break;
            }
        }
        if exhausted {
            break;
        }
        let clause = part.text();
        if starts[cue] >= part.end() || NEGATIVE.test(clause) || !SELF.test(clause) {
            continue;
        }
        for m in CANDIDATE.iter(clause) {
            if let Some(group) = m.nonempty(1) {
                for piece in pieces(group, false) {
                    if single || piece.contains(&' ') {
                        emit(&piece, found, text, part.start() + m.start(), Gate::Known, false);
                    }
                }
            }
        }
    }
    if !single {
        return;
    }
    for part in PARAGRAPH.iter(text) {
        let block = part.text();
        if starts.iter().any(|&c| part.start() <= c && c < part.end()) && SELF.test(block) && !NEGATIVE.test(block) {
            for m in CANDIDATE.iter(block) {
                if let Some(group) = m.nonempty(1) {
                    for piece in pieces(group, false) {
                        if piece.contains(&' ') && known(&piece, 3) {
                            emit(&piece, found, text, part.start() + m.start(), Gate::Known, false);
                        }
                    }
                }
            }
        }
    }
}

fn cheer(text: &[char], found: &mut Found, lowered: &[char], words: &FxHashSet<&str>) {
    if disjoint(words, &["love", "adore", "hell", "go", "justice", "respect", "protect", "hail", "live", "w"]) || !CHEERED.test(text) {
        return;
    }
    for m in CHEER.iter(text) {
        if !hedged(lowered, m.start(), m.end(), self_hedge()) {
            emit(m.group(1).unwrap_or(&[]), found, text, m.start(), Gate::Known, false);
        }
    }
}

pub fn characters(text: &[char], found: &mut Found) {
    let tables = &*TABLES;
    let lowered = lower(text);
    let buffer: String = lowered.iter().collect();
    let words = word_tokens(&buffer);
    let possible = cues_of(text).any(MASKS.POSITIVE);
    let text = recased(text, &words);
    for stage in STAGES.iter() {
        let open = disjoint(&words, stage.avoids) && stage.needs.iter().all(|need| {
            if need.is_empty() {
                words.iter().any(|w| tables.lowercased.contains_key(*w))
            } else {
                need.iter().any(|w| words.contains(*w))
            }
        });
        if open {
            run_stage(stage, &text, found, &lowered);
        }
    }
    referred(&text, found, &lowered, &words);
    liked(&text, found, &words, possible);
    cheer(&text, found, &lowered, &words);
}

pub fn init() {
    LazyLock::force(&TABLES);
    LazyLock::force(&STAGES);
}
