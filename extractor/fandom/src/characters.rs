use crate::fandom::{chars_of, first_piece, join_words, re_split, COMMON, NAME, TRAILING};
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
const MEDIA: &str = r"(?i:series|movies?|films?|games?|franchise|books?|novels?|shows?|music|songs?|albums?|level design|scents?|lore|universe|trilogy|saga|comics?|manga|anime|cartoons?|era|style|soundtrack|ost|band|brand|products?|stuff|team|version|remake|reboot|episodes?|seasons?|chapters?)";
const DEAR: &str = r"(?:husbando|waifu|comfort character)";

const GENERIC_WORDS: &str = "i i'm im me my mine you your he him his she her they them their we us our it its it's this that these those the a an all any every everyone everything some someone something one ones \
character characters game games show anime manga movie film series book books guy guys girl girls boy boys man woman people dude bro lol ok okay yes no yeah here there \
now today then also just really very so much more most both either each other others another what who how why when where which not no none nothing \
playing play using use being having doing going getting watching reading such only neither hello calling absolutely probably actually seriously totally truly genuinely \
perhaps sometimes always lately currently recently especially mostly mainly usually basically obviously clearly surely personally easily";
const ROLES_WORDS: &str = "support supports tank tanks dps healer healers heal jungle jungler mid top adc bot carry assassin assassins mage mages marksman fighter fighters \
melee ranged caster casters sniper snipers striker defender attacker sword spear bow gun guns hammer lance axe axes staff dagger daggers fist fists \
random it them her him killer killers survivor survivors";

const CALENDAR_WORDS: &str = "january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday today tonight tomorrow yesterday morning afternoon evening night noon midnight weekend week month year day hour minute second time season summer winter spring autumn fall christmas xmas halloween easter thanksgiving valentine valentines hanukkah ramadan diwali birthday holiday holidays";

fn nouns() -> String {
    format!(r"(?:{MEDIA}|ways?|things?|parts?|moments?|segments?|lines?|quotes?|scenes?|models?|builds?|places?|foods?|drinks?|colou?rs?|flavou?rs?|brands?|cars?|days?|times?|kinds?|types?|sets?|cards?|items?|weapons?|maps?|levels?|modes?|classes|races|factions?|guns?|looks?|players?|teams?|athletes?|drivers?|bands?|singers?|artists?|authors?|writers?|actors?|actress(?:es)?|youtubers?|streamers?|podcasts?|channels?)")
}

pub struct Tables {
    characters: FxHashMap<&'static str, i64>,
    surfaces: FxHashMap<&'static str, i64>,
    lowercased: FxHashMap<String, &'static str>,
    plurals: FxHashSet<&'static str>,
    initials: FxHashSet<&'static str>,
    others: FxHashSet<String>,
    generic: FxHashSet<&'static str>,
    roles: FxHashSet<&'static str>,
    calendar: FxHashSet<&'static str>,
}

fn build() -> Tables {
    let data: &'static str = leak(data_file("character_names.tsv"));
    let mut characters = FxHashMap::default();
    let mut surfaces: FxHashMap<&'static str, i64> = FxHashMap::default();
    let mut lowercased = FxHashMap::default();
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
        plurals,
        initials,
        others,
        generic,
        roles: ROLES_WORDS.split_whitespace().collect(),
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
re!(HONORIFIC, r"^(?i:mr|mrs|ms|mx|dr|sr|jr|st|prof|sgt|lt|capt)\.?$");
re!(NUMBERED, r"^(?i:(?:number|no\.?|#)\s*)?(?i:\d+|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|last)$");
re!(INTERJECTION, r"^(?i:hell|heck|damn|dang|darn|gosh|jeez|geez|wow|omg|lol|lmao|haha|yay|ugh|oh|ah|hey|hi|thanks|please|sorry|yeah|yes|nope|nah|yep|welp|whoa|ouch|oops|bruh)$");
re!(KINSHIP, r"^(?i:mom|mum|mommy|mummy|mother|dad|daddy|father|papa|mama|sister|sis|brother|bro|wife|husband|hubby|son|daughter|grandma|grandpa|granny|grandmother|grandfather|aunt|auntie|uncle|cousin|niece|nephew|boyfriend|girlfriend|bf|gf|kid|kids|kiddo|child|children|homie|buddy|friend|bestie)$");
re!(ANIMAL, r"^(?i:cat|cats|kitty|kitten|kittens|dog|dogs|doggo|puppy|puppies|pup|bunny|rabbit|horse|pony|bird|fish|hamster|mouse|rat|snake|lizard|turtle|frog|duck|cow|pig|goat|sheep|chicken|fox|wolf|bear|lion|tiger|monkey|parrot)$");
re!(CATEGORY, r"^(?i:pok[eé]mon|digimon)s?$");
re!(BARE, concat!(r"(?:^", claimcore::flair!(), r"|[^\w'-])(?i:the|a|an|to|this|that|some|any) $"));

#[derive(Clone, Copy, PartialEq)]
enum Gate {
    Any,
    Known,
    Medium,
    Named,
}

struct Stage {
    re: Re,
    gate: Gate,
    needs: Vec<Vec<&'static str>>,
}

const I_SET: &[&str] = &["i"];
const MY: &[&str] = &["my"];
const FAVS: &[&str] = &["fav", "favs", "fave", "faves", "favorite", "favorites", "favourite", "favourites", "favrite", "favrites", "faveorite", "faveourite"];
const DEARS: &[&str] = &["husbando", "waifu", "comfort"];

fn with(base: &[&'static str], extra: &[&'static str]) -> Vec<&'static str> {
    base.iter().chain(extra.iter()).copied().collect()
}

fn stage(pattern: String, gate: Gate, needs: Vec<Vec<&'static str>>) -> Stage {
    Stage { re: Re::new(&pattern), gate, needs }
}

static STAGES: LazyLock<Vec<Stage>> = LazyLock::new(|| {
    let nouns = nouns();
    let v = |s: &[&'static str]| s.to_vec();
    use Gate::*;
    vec![
        stage(format!(r"(?i:\b(?:one of )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}(?: of all time| ever| right now| atm| at the moment| so far| by far| in the (?:game|show|series|anime|manga|book))? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*){ANY}"), Any, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\b(?:one of )?my {TIER}{FAVOURITE}(?: of all time| ever| right now| atm| at the moment| so far| by far)? (?:is|has to be|would be|would have to be|remains|are|has always been|will always be|was|has got to be|gotta be|:)(?: (?:probably|definitely|easily|still|honestly|always|def|obviously|hands down|without a doubt|either|currently|now|tied between))?\s*|\b(?:other )?{FAVOURITE} of mine (?:are|include|is)\s+){NAME}"), Medium, vec![v(FAVS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|was|were|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), Any, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i:, (?:one of |among )?my {TIER}{FAVOURITE} (?:\w+ ){{0,2}}{KIND}\b)"), Known, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) {KIND},? ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), Known, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i:,? (?:are |is |)(?:also |definitely |)(?:one of|among|some of) my {TIER}{FAVOURITE}\b(?! (?:\w+ ){{0,2}}{nouns}\b))"), Medium, vec![v(MY), v(FAVS)]),
        stage(format!(r"(?i:\bmy (?:all[- ]time |absolute |personal |)(?:favou?rite|fave|fav) ){NAME}(?=\s*(?:[,.!?;:)\n]|$| (?:from|in|is|was|and|ever|by far|too|lol|tbh)\b))"), Medium, vec![v(MY), v(FAVS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|has always been|will always be|remains|has become|became) (?:still |definitely |probably |easily |honestly |hands down |also |by far |absolutely |literally )*(?:one of |among )?my {TIER}(?:{FAVOURITE}|goat|comfort character|top \d)s?\b(?! (?:\w+ ){{0,2}}{nouns}\b))"), Medium, vec![v(MY), with(FAVS, &["goat", "goats", "comfort", "top"])]),
        stage(format!(r"(?im:^{flair}\W*(?:my )?{FAVOURITE} (?:\w+ )?{KIND}\W*[:=-]\s*){NAME}", flair = claimcore::flair!()), Any, vec![v(FAVS)]),
        stage(format!(r"(?i:\bbest (?:girl|boy|waifu|husbando)s?,? (?:is |goes to |= |: |)){NAME}|{NAME}(?i:,? (?:is |= )?(?:the |my |)best (?:girl|boy|waifu|husbando)\b)"), Any, vec![vec!["best"], vec!["girl", "girls", "boy", "boys", "waifu", "waifus", "husbando", "husbandos"]]),
        stage(format!(r"{NAME},? (?i:my (?:comfort character|waifu|husbando)\b)"), Known, vec![v(MY), vec!["comfort", "waifu", "husbando"]]),
        stage(format!(r"(?i:\bmy (?:husbando|waifu) ){NAME}"), Known, vec![v(MY), vec!["husbando", "waifu"]]),
        stage(format!(r"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |)my {DEAR}\b)"), Known, vec![v(MY), v(DEARS)]),
        stage(format!(r"{NAME}(?i: (?:is|are|will always be|has always been) (?:still |literally |honestly |forever |always |also |)my (?:[a-z-]+ ){{1,2}}(?:{DEAR}|hero|heroine)\b)"), Known, vec![v(MY), with(DEARS, &["hero", "heroine"])]),
        stage(format!(r"(?i:\b(?:i(?:'m| am|'ll|'ve| have)?|im) {ADVERB}(?:stan|simp for|obsessed with) ){NAME}\b"), Named, vec![with(I_SET, &["im"]), vec!["stan", "simp", "obsessed"]]),
        stage(format!(r"(?i:\b(?:i'?m|im|i am|as|been|being|i've been|from) (?:an? |the )?(?:huge |big |biggest |massive |die[- ]?hard |long ?time |proud |true |real |giant |hardcore |super |number one |#1 |no\. ?1 |)*){NAME}(?i: (?:fan|stan|fanboy|fangirl|simp|lover|enjoyer)s?\b)"), Known, vec![vec!["fan", "fans", "stan", "stans", "fanboy", "fanboys", "fangirl", "fangirls", "simp", "simps", "lover", "lovers", "enjoyer", "enjoyers"]]),
        stage(format!(r"(?i:\b(?:i(?:'m| am|'ve| have)?|im) {ADVERB}(?:been obsessed with|obsessed with|a fan of|a big fan of|a huge fan of|a massive fan of|such a fan of|a die[- ]?hard fan of) ){NAME}\b"), Named, vec![with(I_SET, &["im"]), vec!["obsessed", "fan"]]),
        stage(format!(r"(?i:\bmy (?:ult |ultimate |current |first |og |main )?(?:bias|oshi)(?: (?:is|has always been|will always be|remains)|:)\s*){NAME}|{NAME}(?i: (?:is|has always been|will always be|remains) (?:still |always |forever )?my (?:ult |ultimate |current |first |og |main )?(?:bias|oshi)\b)"), Any, vec![v(MY), vec!["bias", "oshi"]]),
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
            _ => {}
        }
        if let Some(value) = fan_value("character", &lower(&piece)) {
            found.set("fandoms", st(&value), position);
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

pub fn characters(text: &[char], found: &mut Found) {
    let tables = &*TABLES;
    let lowered = lower(text);
    let buffer: String = lowered.iter().collect();
    let words = word_tokens(&buffer);
    let text = recased(text, &words);
    for stage in STAGES.iter() {
        let open = stage.needs.iter().all(|need| {
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
}

pub fn init() {
    LazyLock::force(&TABLES);
    LazyLock::force(&STAGES);
}
