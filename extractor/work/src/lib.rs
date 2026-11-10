mod lexicon;
mod patterns;
mod schools;
mod standing;
mod vocab;

use claimcore::*;
use lexicon::*;
use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;
use vocab::*;

type V = Box<dyn Fn(&Match) -> Option<String> + Send + Sync>;

static CONDITIONAL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:if|would|wish|imagine|pretend|unless|whether|might|maybe)\b"));
static UNLESS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:if|would|wish)\b"));
static SCOPE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:because|cause|cuz|since|and|but|so|as|although|though|after|before|while|until)\b"));
static PRETEND: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:like|as if|as though|pretend|pretending|imagine)\s*$"));
static YOU: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*,?\s*(?:you|u|your|yourself)\b|\s+(?:is|isn't|means|requires|sucks|can|could|will|would|has|was|takes|seems|makes|he|she|they)\b"));
static OPENED: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,]|\b(?:but|so|because|also))\s*$")));
static FLAIR: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\A", claimcore::flair!())));
static PERSONA: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\b[mf]4[a-z]+\b|\d{2}\s?(?:yo|y/o|yrs? old|years? old)\b"));
static SELF: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me|myself)\b"));
static PAIRED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+and (?:i|me) (?:are|were|have|had|went|both|figured|got|did|decided)\b"));
static STRICT_END: LazyLock<Re> = LazyLock::new(|| Re::new(r"[ \t]*(?:$|[.,!;|(\n]|(?:and|by trade|by profession|here)\b)"));
static PERSONA_END: LazyLock<Re> = LazyLock::new(|| Re::new(r"[ \t]*(?:$|[.,!;|(\n-]|(?:and|by trade|by profession|here|who|with|getting|looking|seeking|available|from|in)\b)"));
static WANTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:you|your|you're|u|ur|looking|seeking|want|wanted|wanting|prefer|preferably|ideally|bonus|like|into|for)\b"));
static OBJECT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+(?:my|your|his|her|their|this|that|these|those|the|a|an|me|you|him|them|us|it|or|one|some|any)\b"));
static ROLEPLAY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:rp|roleplay|role play|role-play|roleplaying|role playing)\b"));
static ASPIRANT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:aspiring|wannabe|future|budding|would-be|soon[- ]to[- ]be)\b"));
static COMMUNITY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bcommunity college\b"));
static GRADUATE_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:grad|graduate|phd|masters?|master's|doctoral|med|law|medical)\b"));
static SCHOOL_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:high school|highschool|hs)\b"));
static PHD_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:phd|ph\.d|doctoral|doctorate|dissertation|dphil)\b"));
static MASTERS_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:masters?|master's|msc|mba|msw|mfa|ma|ms|mtech|m\.tech|meng|llm|postgrad)\b"));
static PRO_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:law|(?<!pre )(?<!pre-)med|(?<!pre )(?<!pre-)medical|dental|vet|veterinary|pharmacy|nursing|bsn|[123]l|ms[1-4])\b"));
static COLLEGE_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:college|uni|university|engineering|undergrad|undergraduate|bachelor'?s?|bachelors|bsc|btech|campus|major|majoring|degree|faculdade|facul|universidad|universidade|facultad|fac|studium)\b"));
static STUDENT_WORD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:student|students|studying|study|studies|studiere|estudiante|estudante|studente|studentessa|étudiant|étudiante|fresher|freshie|semester|sem)\b"));
static UNI_YEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:(1st|first)|(2nd|second)|(3rd|third)|(4th|fourth|final|last))[- ](?:year|yr)\b"));
static CLASS_YEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:(freshman|fresher|freshie)|(sophomore)|(junior)|(senior))\b"));
static GRADE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\b(?:(6th|7th|8th|sixth|seventh|eighth|year [78])|(9th|10th|ninth|tenth|freshman|sophomore|first|second|1st|2nd|class (?:9|10|ix|x)|grade (?:9|10)|(?:year|yr|y) ?(?:9|10))|",
    r"(11th|eleventh|junior|third|3rd|class (?:11|xi)|grade 11|(?:year|yr|y) ?11)|(12th|twelfth|senior|fourth|final|last|4th|class (?:12|xii)|grade 12|(?:year|yr|y) ?12)|((?:year|yr|y) ?13))\b")));
pub(crate) static GRAD_SCHOOL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bgrad(?:uate)? (?:school|student)\b"));
static SCHOOL_YEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:y|yr|year) ?(?:9|10|11|12|13)\b"));
static ACADEMIC_SUB: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:univ|college|tards|student|btech|iit|nit|vit|bits|dtu|nsut|pesu|srm|manipal|amity|lpu|kiit|mbbs|medico|campus|engineering|jee)"));
static ACADEMIC_FLAIR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:cse|ece|eee|mech|civil|aids|aiml|ise|it|ep|bca|mca|bsc|bba|btech|b\.tech|mbbs|core|ee|cs|engineering|uni|college|university)\b"));
static WHEN: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:when|once|until|before|after|if)\s+$"));
pub(crate) static IN_PROGRESS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:doing|studying|finishing|completing|working on|working towards|currently|enrolled|middle of|halfway|toward|towards)\b"));
const KIN: &str = "he|she|they|his|her|their|him|them|husband|wife|boyfriend|girlfriend|partner|friend|friends|brother|sister|son|daughter|mom|mum|dad|mother|father|cousin|roommate";
static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|you|your|u|someone|anyone|everyone|everybody|nobody|people)\b")));
static FIRST_NEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me)\b"));
static PEERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|batchmates?|classmates?|colleagues?|coworkers?)\b")));
pub(crate) static ASPIRING: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\b(?:eventually|someday|love to|build|building|idea|goal|goals|pursue|pursuing|planning|plan|plans|apply|applying|application|considering|thinking|soch|want|wanted|wanting|hoping|dream|future|next|aspiring|",
    r"get|getting|start|starting|consider|choose|choosing|need|needs|require|requires|required|offer|offers)\b")));
pub(crate) static FUTURE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:planning|plan|plans|want|wanted|wanting|hoping|thinking|considering|consider|apply|applying|dream|eventually|someday|will|might|may)\b"));
pub(crate) static LEVELLESS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:international|foreign|exchange|overseas)\b"));
static WORDS: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\w'-]+"));
static MILESTONE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:passed|hit|crossed|topped|clear|cleared)\b"));
static COMPARED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:more|less|extra|higher|lower|raise|diff|differential)\b"));
static EARNERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|parents|family|you|your|u|we|someone|anyone|everyone|people)\b")));
static AMERICAN: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\b(?:usd|us dollars?|401\s?\(?k|403\s?\(?b|457\s?\(?b|roth (?:ira|401)|irs|w-?2|(?<![$\d.,])1099|fica|medicaid|fafsa|usa|united states|in the (?:us|states)|veterans affairs|va (?:disability|benefits|loan|rating)|",
    r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming",
    r")\b|\bus\$|\bu\.s\.")));
static ABROAD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:cad|aud|nzd|sgd|hkd|eur|euros?|gbp|inr|rupees?|lakhs?|canada|canadian|australia|australian|new zealand|singapore|hong kong)\b|\b(?:c|ca|a|au|nz|s|hk)\$|[€£₹]"));
static SUBCONTINENT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:pkr|pakistan|pakistani|npr|nepal|nepali|nepalese|lkr|sri lanka|sri lankan|bdt|bangladesh|bangladeshi|taka)\b"));
static HOPED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:goal|goals|aim|aiming|hope|hoping|want|wanted|wanting|plan|planning|dream|could|would|will|might|may)\b"));
static NAMED: LazyLock<Vec<(&str, &str, Re)>> = LazyLock::new(|| {
    [("¥", "jpy", r"\b(?:yen|jpy)\b"), ("¥", "cny", r"\b(?:yuan|rmb|cny|renminbi)\b"), ("kr", "sek", r"\b(?:sek|kronor|swedish kron[ae])\b"),
     ("kr", "nok", r"\b(?:nok|norwegian kroner?)\b"), ("kr", "dkk", r"\b(?:dkk|danish kroner?)\b"), ("kr", "isk", r"\b(?:isk|icelandic kron(?:a|ur))\b")]
    .into_iter().map(|(symbol, code, pattern)| (symbol, code, Re::new(pattern))).collect()
});
static RATES: LazyLock<HashMap<String, f64>> = LazyLock::new(|| {
    timed("work.rates", || data_file("currency_rates.tsv").lines().map(|line| {
        let cells: Vec<&str> = line.split('\t').collect();
        (cells[0].to_string(), cells[1].parse().unwrap())
    }).collect())
});

pub(crate) const SELF_EMPLOYED: &str = "self-employed / freelance";
pub(crate) const UNDERGRAD: &str = "undergraduate (year unstated)";
pub(crate) const GRADUATED: &str = "graduated (level unstated)";
pub(crate) const PROFESSIONAL_SCHOOL: &str = "medical / law / professional school";
const UNI_YEARS: [&str; 4] = ["university 1st year", "university 2nd year", "university 3rd year", "university 4th / final year"];

pub(crate) static BUSINESS_MAP: LazyLock<Map> = LazyLock::new(|| listed(BUSINESSES));
pub(crate) static FIELD_MAP: LazyLock<Map> = LazyLock::new(|| listed(FIELDS));
pub(crate) static VERB_MAP: LazyLock<Map> = LazyLock::new(|| pairs(VERBS));
pub(crate) static SUBJECTS: LazyLock<Map> = LazyLock::new(|| {
    let mut out = pairs(SUBJECT_PAIRS);
    out.extend(listed(SUBJECT_TABLE));
    out
});
pub(crate) static DEGREE_MAP: LazyLock<Map> = LazyLock::new(|| pairs(DEGREES));
const DEGREE_OF: [&str; 12] = ["science", "arts", "engineering", "business", "fine", "education", "laws", "law", "philosophy", "music", "social", "public"];
static SHORT: LazyLock<HashSet<&'static str>> = LazyLock::new(|| SHORT_DEGREES.iter().copied().collect());
static LEVELS: LazyLock<Map> = LazyLock::new(|| DEGREES.iter().map(|(name, level)| (name.trim_end_matches('.').to_string(), Some(*level))).collect());
static SCHOOL_MAP: LazyLock<Map> = LazyLock::new(|| pairs(SCHOOLS));
static FOREIGN_SUBJECT_MAP: LazyLock<Map> = LazyLock::new(|| listed(FOREIGN_SUBJECTS));
pub(crate) static DEGREE_SUBJECTS: LazyLock<Map> = LazyLock::new(|| {
    let mut out = SUBJECTS.clone();
    out.extend(pairs(DEGREE_SUBJECT_EXTRA));
    out
});
pub(crate) static DEGREE_FIELD_MAP: LazyLock<Map> = LazyLock::new(|| listed(DEGREE_FIELDS));
static AMBIGUOUS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| AMBIGUOUS_SUBJECTS.iter().copied().collect());
static NO_SUBJECTS: LazyLock<HashSet<&'static str>> = LazyLock::new(HashSet::new);
static AI_SUBJECTS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| ["it", "ai"].into_iter().collect());

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(patterns::build);

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn init() {
    timed("work.init", || {
        LazyLock::force(&TITLES);
        LazyLock::force(&FOREIGN_TITLES);
        LazyLock::force(&TITLE_HEADS);
        LazyLock::force(&FOREIGN_HEADS);
        LazyLock::force(&schools::SCHOOLS);
        LazyLock::force(&RULES);
    });
}

fn get(map: &Map, key: Option<&[char]>) -> Option<String> {
    key.and_then(|k| map.get(&st(k)).copied().flatten()).map(String::from)
}

fn keyed(map: &Map, key: Option<&[char]>) -> Option<String> {
    let key = st(key?);
    map.get(&key).copied().flatten().map(|_| key)
}

fn lookup(map: &'static LazyLock<Map>, number: usize) -> V {
    Box::new(move |m| get(map, m.group(number)))
}

fn keys(map: &'static LazyLock<Map>, number: usize) -> V {
    Box::new(move |m| keyed(map, m.group(number)))
}

fn sector(m: &Match) -> Option<String> {
    let key = keyed(&FIELD_MAP, m.group(1))?;
    if key.starts_with("a ") || FIELD_MAP[&key] == Some(MILITARY) {
        return None;
    }
    Some(key.trim_start_matches("the ").to_string())
}

fn branch(m: &Match) -> Option<String> {
    let key = m.gs(1)?;
    let value = match key.trim_start_matches("the ") {
        "army" | "army reserve" => "army",
        "navy" => "navy",
        "air force" => "air force",
        "marines" | "marine corps" => "marines",
        "coast guard" => "coast guard",
        _ => return None,
    };
    Some(value.to_string())
}

fn fixed(value: &'static str) -> V {
    Box::new(move |_| Some(value.to_string()))
}

fn free(text: &[char], start: usize, hedge: &Re) -> bool {
    let mut start = start;
    while start < text.len() && !alnum(text[start]) {
        start += 1;
    }
    if PRETEND.test_in(text, start.saturating_sub(16), start) {
        return false;
    }
    let left = clause(text, start).max(start.saturating_sub(40));
    let cut = SCOPE.iter_in(text, left, start).map(|m| m.end()).max().unwrap_or(left);
    !hedge.test_in(text, cut, start)
}

fn after(m: &Match) -> Option<&'static str> {
    if !free(m.string, m.start(), &SELF_HEDGE) {
        return None;
    }
    Some(title(m.string, m.end(), None)?.0)
}

fn opener(m: &Match) -> Option<&'static str> {
    let (value, end) = title(m.string, m.end(), None)?;
    if YOU.at(m.string, end).is_some() {
        None
    } else {
        Some(value)
    }
}

fn opened(m: &Match) -> Option<&'static str> {
    if OPENED.test_in(m.string, m.start().saturating_sub(20), m.start()) {
        opener(m)
    } else {
        None
    }
}

fn here(m: &Match) -> Option<&'static str> {
    let (a, b) = m.span(1)?;
    ended(m.string, a, b)
}

fn hired(m: &Match) -> Option<&'static str> {
    Some(title(m.string, m.end(), None)?.0)
}

fn abroad(m: &Match) -> Option<&'static str> {
    let (key, _) = spot(m.string, m.end(), Some(1), &FOREIGN_BLOCKED, &FOREIGN_TITLES, &FOREIGN_HEADS)?;
    Some(FOREIGN_TITLES.get_key_value(&key)?.0.as_str())
}

fn fragment(m: &Match) -> Option<&'static str> {
    let text = m.string;
    let lead = m.text();
    if contains(lead, "hir") {
        return None;
    }
    if PERSONA.test(lead) {
        let (value, end) = title(text, m.end(), Some(2))?;
        return (!question(text, end) && PERSONA_END.at(text, end).is_some()).then_some(value);
    }
    let (value, end) = title(text, m.end(), Some(0))?;
    if question(text, end) || STRICT_END.at(text, end).is_none() || PAIRED.at(text, end).is_some() || addressed(text, end) || enumerated(text, m.start(), end) {
        return None;
    }
    (SELF.test_in(text, end, end + 120) || text.len() - body(text) < 60).then_some(value)
}

fn body(text: &[char]) -> usize {
    FLAIR.at(text, 0).map_or(0, |m| m.end())
}

fn addressed(text: &[char], end: usize) -> bool {
    let Some(comma) = (end..text.len()).find(|&i| text[i] != ' ' && text[i] != '\t') else { return false };
    if text[comma] != ',' {
        return false;
    }
    let Some(word) = (comma + 1..text.len()).find(|&i| !is_space(text[i])) else { return false };
    let name = st(&text[word..token_end(text, word, text.len())]);
    !matches!(name.as_str(), "i" | "i'm" | "i've" | "i'd" | "i'll") && original(text).is_some_and(|raw| raw[word].is_uppercase())
}

fn enumerated(text: &[char], start: usize, end: usize) -> bool {
    let next = (end..text.len()).find(|&i| text[i] == '\n').map(|i| i + 1);
    let before = line_start(text, start);
    let previous = (before > 0).then(|| line_start(text, before - 1));
    [next, previous].into_iter().flatten().any(|line| {
        let first = (line..text.len()).find(|&i| alnum(text[i]) || text[i] == '\n').unwrap_or(text.len());
        first < text.len() && text[first] != '\n' && title(text, first, Some(0)).is_some_and(|(_, stop)| STRICT_END.at(text, stop).is_some())
    })
}

fn bare(m: &Match) -> Option<&'static str> {
    let (value, end) = title(m.string, m.end(), Some(0))?;
    let named = !value.contains(' ') && original(m.string).is_some_and(|text| text.get(m.end()).is_some_and(|c| c.is_uppercase()));
    (!named && !question(m.string, end) && PERSONA_END.at(m.string, end).is_some()).then_some(value)
}

fn retiree(m: &Match) -> Option<&'static str> {
    let (value, end) = title(m.string, m.end(), Some(1))?;
    if STRICT_END.at(m.string, end).is_some() { Some(value) } else { None }
}

fn tagged(m: &Match) -> Option<&'static str> {
    let text = m.string;
    let (value, end) = title(text, m.end(), Some(2))?;
    if question(text, end) || WANTED.test_in(text, m.start(), end) || OBJECT.at(text, end).is_some() {
        return None;
    }
    Some(value)
}

#[derive(Default)]
struct PerText {
    key: (u64, usize, usize),
    played: Option<bool>,
    persona: Option<bool>,
    breaks: Option<Vec<usize>>,
    marks: HashMap<usize, (usize, usize)>,
}

thread_local! {
    static CACHE: RefCell<PerText> = RefCell::new(PerText::default());
}

fn cached<R>(text: &[char], work: impl FnOnce(&mut PerText) -> R) -> R {
    CACHE.with(|cache| {
        let mut cache = cache.borrow_mut();
        let key = (serial(), text.as_ptr() as usize, text.len());
        if cache.key != key {
            cache.key = key;
            cache.played = None;
            cache.persona = None;
            cache.breaks = None;
            if !cache.marks.is_empty() {
                cache.marks = HashMap::new();
            }
        }
        work(&mut cache)
    })
}

fn line_of(text: &[char], start: usize) -> usize {
    cached(text, |c| {
        let breaks = c.breaks.get_or_insert_with(|| (0..text.len()).filter(|&i| text[i] == '\n').collect());
        let before = breaks.partition_point(|&b| b < start);
        if before == 0 { 0 } else { breaks[before - 1] + 1 }
    })
}

fn marks(text: &[char], line: usize) -> (usize, usize) {
    if let Some(found) = cached(text, |c| c.marks.get(&line).copied()) {
        return found;
    }
    let end = findc(text, '\n', line).unwrap_or(text.len());
    let persona = PERSONA.search(text, line, end).map_or(end + 1, |p| p.end());
    let wanted = WANTED.search(text, line, end).map_or(end, |w| w.start());
    cached(text, |c| c.marks.insert(line, (persona, wanted)));
    (persona, wanted)
}

fn celled(m: &Match) -> Option<&'static str> {
    let text = m.string;
    let start = m.start();
    if !cached(text, |c| *c.persona.get_or_insert_with(|| maybe_persona(text) && PERSONA.test(text))) {
        return None;
    }
    let (persona, wanted) = marks(text, line_of(text, start));
    if persona > start || wanted < start {
        return None;
    }
    let (value, end) = title(text, m.end(), Some(0))?;
    if STRICT_END.at(text, end).is_some() {
        Some(value)
    } else {
        None
    }
}

fn personal(m: &Match) -> bool {
    let text = m.string;
    let start = m.start();
    if !cached(text, |c| *c.persona.get_or_insert_with(|| maybe_persona(text) && PERSONA.test(text))) {
        return false;
    }
    let (persona, wanted) = marks(text, line_of(text, start));
    persona <= start && wanted >= start
}

fn roleplay(text: &[char]) -> bool {
    cached(text, |c| *c.played.get_or_insert_with(|| ROLEPLAY.test(text)))
}

fn occupied(find: impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static) -> V {
    Box::new(move |m| find(m).filter(|key| job_kind(key) != OWNER).map(String::from))
}

fn status(key: &str) -> Option<&'static str> {
    let job = job_kind(key);
    if key.ends_with(" owner") || job == FOUNDER && !key.starts_with("business") {
        Some(standing::BUSINESS_OWNER)
    } else if job == OWNER {
        Some(SELF_EMPLOYED)
    } else if key == "intern" || key.ends_with(" intern") {
        Some("intern")
    } else if key == "apprentice" || key.starts_with("apprentice ") || key.ends_with(" apprentice") {
        Some("apprentice")
    } else {
        None
    }
}

fn employed(find: impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static) -> V {
    Box::new(move |m| find(m).and_then(status).filter(|_| ASPIRANT.at(m.string, m.end()).is_none()).map(String::from))
}

fn scoped_with(value: V, hedge: &'static Re, played: bool) -> V {
    Box::new(move |m| if free(m.string, m.start(), hedge) && (played || !roleplay(m.string)) { value(m) } else { None })
}

fn scoped(value: V) -> V {
    scoped_with(value, &SELF_HEDGE, false)
}

fn ranged(m: &Match, low: f64, high: f64) -> Option<String> {
    let value: f64 = m.first_s()?.parse().ok()?;
    (low..=high).contains(&value).then(|| m.first_s()).flatten()
}

fn said(attribute: &'static str, pattern: &str, value: V, hedge: &'static Re) -> Rule {
    rule(attribute, pattern, scoped_with(value, hedge, false), TAGGED)
}

fn sentence(text: &[char], start: usize) -> usize {
    last_mark(text, start, ".!?\n")
}

fn mine(value: V) -> V {
    Box::new(move |m| if OTHERS.test_in(m.string, clause(m.string, m.start()), m.start()) { None } else { value(m) })
}

fn near(value: V) -> V {
    Box::new(move |m| if FIRST_NEAR.test_in(m.string, sentence(m.string, m.start()), m.start()) { value(m) } else { None })
}

fn college(m: &Match) -> Option<String> {
    let text = m.string;
    let start = m.start();
    let begin = sentence(text, start);
    if (FIRST_NEAR.test_in(text, begin, start) || PERSONA.test_in(text, begin, start + 6)) && !OTHERS.test_in(text, begin, start) {
        Some(UNDERGRAD.to_string())
    } else {
        None
    }
}

fn cased(m: &Match) -> Option<String> {
    let text = original(m.string)?;
    if !text.is_empty() && text[m.end() - 2..m.end()] == ['I', 'T'] {
        Some("it".to_string())
    } else {
        None
    }
}

fn owned(text: &[char], start: usize, reach: usize) -> bool {
    let left = clause(text, start).max(start.saturating_sub(reach));
    FIRST_NEAR.test_in(text, left, start) && !PEERS.test_in(text, left, start)
}

fn is_subject(name: &str) -> bool {
    SUBJECTS.contains_key(name)
}

fn degree_in(m: &Match) -> Option<String> {
    let text = m.string;
    let start = m.start();
    let degree = m.gs(1)?;
    let level = LEVELS.get(&degree).copied().flatten()?;
    let subject = m.g(2);
    let first = subject.split_whitespace().next().unwrap_or("");
    if !is_subject(&subject) && !is_subject(first) && (SHORT.contains(degree.as_str()) || !DEGREE_OF.contains(&first)) {
        return None;
    }
    let left = clause(text, start).max(start.saturating_sub(60));
    if ASPIRING.test_in(text, left, start) || IN_PROGRESS.test_in(text, left, start) || OTHERS.test_in(text, clause(text, start), start) || !(FIRST_NEAR.test_in(text, start.saturating_sub(80), start) || line_start(text, start) == start || body(text) == start) {
        return None;
    }
    Some(level.to_string())
}

fn anchored(text: &[char], start: usize) -> bool {
    let mut head_end = start;
    let head_start = line_start(text, start);
    while head_end > head_start && is_space(text[head_end - 1]) {
        head_end -= 1;
    }
    let marked = head_end > head_start && matches!(text[head_end - 1], ':' | '|');
    (owned(text, start, 50) || marked) && !ASPIRING.test_in(text, clause(text, start), start)
}

fn subject(m: &Match, block: &HashSet<&'static str>) -> Option<String> {
    let name = m.first_s()?;
    if block.contains(name.as_str()) || !SUBJECTS.contains_key(&name) {
        None
    } else {
        Some(name)
    }
}

fn subject_before(text: &[char], start: usize) -> Option<String> {
    let words: Vec<String> = WORDS.iter_in(text, start.saturating_sub(60), start).map(|w| st(w.text())).collect();
    for size in [4, 3, 2, 1] {
        if words.len() >= size {
            let key = words[words.len() - size..].join(" ");
            if SUBJECTS.contains_key(&key) {
                return Some(key);
            }
        }
    }
    None
}

fn graduate(text: &[char]) -> &'static str {
    if PHD_LEVEL.test(text) {
        "phd student"
    } else if MASTERS_LEVEL.test(text) {
        "master's student"
    } else {
        "graduate student (level unstated)"
    }
}

fn year_of(found: &Match) -> Option<&'static str> {
    Some(UNI_YEARS[(1..=4).find(|&i| found.group(i).is_some())? - 1])
}

fn level(m: &Match) -> Option<String> {
    let span = m.text();
    if SCHOOL_LEVEL.test(span) || LEVELLESS.test(span) || question(m.string, m.end()) || WHEN.test_in(m.string, m.start().saturating_sub(8), m.start()) {
        return None;
    }
    let value = if COMMUNITY.test(span) {
        "community college"
    } else if PRO_LEVEL.test(span) {
        PROFESSIONAL_SCHOOL
    } else if GRADUATE_LEVEL.test(span) || PHD_LEVEL.test(span) || MASTERS_LEVEL.test(span) {
        graduate(span)
    } else if let Some(year) = UNI_YEAR.search(span, 0, span.len()) {
        if !COLLEGE_LEVEL.test(span) && !STUDENT_WORD.test(span) {
            return None;
        }
        year_of(&year)?
    } else if COLLEGE_LEVEL.test(span) {
        match CLASS_YEAR.search(span, 0, span.len()) {
            Some(year) => year_of(&year)?,
            None => UNDERGRAD,
        }
    } else {
        "student (level unstated)"
    };
    Some(value.to_string())
}

fn flair_level(m: &Match) -> Option<String> {
    let text = m.string;
    let (a, b) = m.span(2)?;
    if let Some(found) = SCHOOL_YEAR.search(text, a, b) {
        return Some(match GRADE.search(found.text(), 0, found.text().len()) {
            Some(year) => ["middle school", "high school year 9-10", "year 11", "year 12", "year 13"][(1..=5).find(|&i| year.group(i).is_some())? - 1],
            None => return None,
        }
        .to_string());
    }
    let year = UNI_YEAR.search(text, a, b)?;
    if ACADEMIC_SUB.test(m.group(1)?) || ACADEMIC_FLAIR.test_in(text, a, b) {
        Some(year_of(&year)?.to_string())
    } else {
        None
    }
}

fn grade(m: &Match) -> Option<String> {
    let value = match GRADE.search(m.text(), 0, m.text().len()) {
        Some(found) => ["middle school", "high school year 9-10", "year 11", "year 12", "year 13"][(1..=5).find(|&i| found.group(i).is_some())? - 1],
        None => "high school (year unstated)",
    };
    Some(value.to_string())
}

fn period(name: Option<&str>) -> Option<f64> {
    let times = match name {
        None | Some("year" | "yr" | "annum" | "annually" | "yearly") => 1.0,
        Some("month" | "mo" | "monthly") => 12.0,
        Some("week" | "wk" | "weekly") => 52.0,
        _ => return None,
    };
    Some(times)
}

fn scale(name: Option<&[char]>) -> f64 {
    match name.map(st).as_deref() {
        Some("k" | "thousand" | "grand") => 1000.0,
        Some("lpa" | "lakh" | "lakhs" | "lac" | "lacs") => 100_000.0,
        Some("mil" | "million") => 1_000_000.0,
        Some("crore" | "crores") => 10_000_000.0,
        _ => 1.0,
    }
}

fn code(marker: &str) -> Option<&'static str> {
    let value = match marker {
        "us$" | "usd" | "us dollar" | "us dollars" | "american dollar" | "american dollars" => "usd",
        "€" | "eur" | "euro" | "euros" => "eur",
        "£" | "gbp" | "pound" | "pounds" | "quid" => "gbp",
        "₹" | "inr" => "inr",
        "c$" | "ca$" | "cad" | "canadian dollar" | "canadian dollars" => "cad",
        "a$" | "au$" | "aud" | "australian dollar" | "australian dollars" => "aud",
        "nz$" | "nzd" => "nzd",
        "s$" | "sgd" => "sgd",
        "hk$" | "hkd" => "hkd",
        "r$" | "brl" | "reais" => "brl",
        "zł" | "pln" => "pln",
        "jpy" | "yen" => "jpy",
        "cny" | "rmb" | "yuan" => "cny",
        "chf" => "chf",
        "sek" => "sek",
        "nok" => "nok",
        "dkk" => "dkk",
        _ => return None,
    };
    Some(value)
}

fn american(text: &[char]) -> bool {
    AMERICAN.test(text) && !ABROAD.test(text)
}

fn named(text: &[char], marker: &str) -> Option<&'static str> {
    match marker.trim_end_matches('.') {
        "$" | "dollar" | "dollars" | "bucks" => american(text).then_some("usd"),
        "rs" | "rupee" | "rupees" | "lpa" | "lakh" | "lakhs" | "lac" | "lacs" | "crore" | "crores" => (!SUBCONTINENT.test(text)).then_some("inr"),
        _ => {
            let found: Vec<&'static str> = NAMED.iter().filter(|(symbol, _, re)| *symbol == marker && re.test(text)).map(|(_, code, _)| *code).collect();
            (found.len() == 1).then(|| found[0])
        }
    }
}

fn currency(m: &Match) -> Option<&'static str> {
    let markers: Vec<String> = [1, 3, 4, 5].into_iter().filter_map(|number| m.gs(number)).collect();
    let codes: HashSet<&'static str> = markers.iter().filter_map(|marker| code(marker)).collect();
    match codes.len() {
        0 => markers.iter().find_map(|marker| named(m.string, marker)),
        1 => codes.into_iter().next(),
        _ => None,
    }
}

fn income(m: &Match) -> Option<String> {
    if contains(m.text(), "hourly") {
        return None;
    }
    let name = m.gs(6).or_else(|| m.gs(7));
    let times = period(name.as_deref())?;
    if times > 1.0 && (MILESTONE.test(m.text()) || COMPARED.at(m.string, m.end()).is_some()) {
        return None;
    }
    let rate = RATES[currency(m)?];
    let digits: Vec<char> = m.group(2)?.iter().copied().filter(|&c| c != ',').collect();
    let dollars = py_float(&digits)? * scale(m.group(3).or(m.group(4))) * times * rate;
    (1000.0..=10_000_000.0).contains(&dollars).then(|| (dollars.round() as i64).to_string())
}

fn figures(m: &Match) -> Option<String> {
    american(m.string).then(|| "100000".to_string())
}

fn earning(m: &Match) -> Option<String> {
    let text = m.string;
    let start = m.start();
    let left = clause(text, start);
    if (owned(text, start, 50) || PERSONA.test_in(text, left, start)) && !EARNERS.test_in(text, left, start) && !HOPED.test_in(text, left, start) {
        income(m)
    } else {
        None
    }
}

fn digit(c: char) -> bool {
    c.is_ascii_digit() || !c.is_ascii() && is_decimal(c)
}

fn maybe_persona(text: &[char]) -> bool {
    text.windows(2).any(|pair| digit(pair[0]) && digit(pair[1]) || pair[1] == '4' && matches!(pair[0], 'm' | 'f'))
}
