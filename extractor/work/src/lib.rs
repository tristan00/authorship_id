mod lexicon;
mod patterns;
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
static YOU: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*,?\s*(?:you|u|your|yourself)\b"));
static SELF: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me|myself)\b"));
static OPENED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|[.!?\n,]|\b(?:but|so|because|also))\s*$"));
static PERSONA: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\b[mf]4[a-z]+\b|\d{2}\s?(?:yo|y/o|yrs? old|years? old)\b"));
static STRICT_END: LazyLock<Re> = LazyLock::new(|| Re::new(r"[ \t]*(?:$|[.,!;|(\n]|(?:and|by trade|by profession|here)\b)"));
static PERSONA_END: LazyLock<Re> = LazyLock::new(|| Re::new(r"[ \t]*(?:$|[.,!;|(\n-]|(?:and|by trade|by profession|here|who|with|getting|looking|seeking|available|from|in)\b)"));
static WANTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:you|your|you're|u|ur|looking|seeking|want|wanted|wanting|prefer|preferably|ideally|bonus|like|into|for)\b"));
static OBJECT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+(?:my|your|his|her|their|this|that|these|those|the|a|an|me|you|him|them|us|it|or|one|some|any)\b"));
static ROLEPLAY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:rp|roleplay|role play|role-play|roleplaying|role playing)\b"));
static GRADUATE_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:grad|graduate|phd|masters?|master's|doctoral|med|law|medical)\b"));
static SCHOOL_LEVEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:high school|highschool|hs)\b"));
static LEVELED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:high|school|hs|grad|graduate|phd|masters?|master's|doctoral|med|law|medical|nursing|international|foreign|exchange|overseas)\b"));
const KIN: &str = "he|she|they|his|her|their|him|them|husband|wife|boyfriend|girlfriend|partner|friend|friends|brother|sister|son|daughter|mom|mum|dad|mother|father|cousin|roommate";
static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|you|your|u|someone|anyone|everyone|everybody|nobody|people)\b")));
static FIRST_NEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me)\b"));
static PEERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|batchmates?|classmates?|colleagues?|coworkers?)\b")));
static ASPIRING: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\b(?:goal|goals|pursue|pursuing|planning|plan|plans|apply|applying|application|considering|thinking|soch|want|wanted|wanting|hoping|dream|future|next|aspiring|",
    r"get|getting|start|starting|consider|choose|choosing|need|needs|require|requires|required|offer|offers)\b")));
static LEVELLESS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:international|foreign|exchange|overseas)\b"));
static WORDS: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\w'-]+"));
static MILESTONE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:passed|hit|crossed|topped|clear|cleared)\b"));
static COMPARED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:more|less|extra|higher|lower|raise|diff|differential)\b"));
static EARNERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|parents|family|you|your|u|we|someone|anyone|everyone|people)\b")));

pub(crate) static BUSINESS_MAP: LazyLock<Map> = LazyLock::new(|| listed(BUSINESSES));
pub(crate) static FIELD_MAP: LazyLock<Map> = LazyLock::new(|| listed(FIELDS));
pub(crate) static PLACE_MAP: LazyLock<Map> = LazyLock::new(|| listed(PLACES));
pub(crate) static VERB_MAP: LazyLock<Map> = LazyLock::new(|| pairs(VERBS));
pub(crate) static INTERNSHIP_MAP: LazyLock<Map> = LazyLock::new(|| pairs(INTERNSHIPS));
pub(crate) static SUBJECTS: LazyLock<Map> = LazyLock::new(|| {
    let mut out = pairs(SUBJECT_PAIRS);
    out.extend(listed(SUBJECT_TABLE));
    out
});
pub(crate) static DEGREE_MAP: LazyLock<Map> = LazyLock::new(|| pairs(DEGREES));
static SHORT: LazyLock<HashSet<&'static str>> = LazyLock::new(|| SHORT_DEGREES.iter().copied().collect());
static LEVELS: LazyLock<Map> = LazyLock::new(|| {
    let mut out: Map = DEGREES.iter().map(|(name, level)| (name.trim_end_matches('.').to_string(), Some(*level))).collect();
    out.insert("msn".to_string(), Some("master's degree"));
    out
});
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
        LazyLock::force(&RULES);
    });
}

fn get(map: &Map, key: Option<&[char]>) -> Option<String> {
    key.and_then(|k| map.get(&st(k)).copied().flatten()).map(String::from)
}

fn found(value: Option<&'static str>) -> Option<String> {
    value.map(String::from)
}

fn lookup(map: &'static LazyLock<Map>, number: usize) -> V {
    Box::new(move |m| get(map, m.group(number)))
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

fn after(m: &Match, using: Use) -> Option<&'static str> {
    if !free(m.string, m.start(), &SELF_HEDGE) {
        return None;
    }
    title(m.string, m.end(), None, using)?.0
}

fn opener(m: &Match, using: Use) -> Option<&'static str> {
    let (value, end) = title(m.string, m.end(), None, using)?;
    if YOU.at(m.string, end).is_some() {
        None
    } else {
        value
    }
}

fn opened(m: &Match, using: Use) -> Option<&'static str> {
    if OPENED.test_in(m.string, m.start().saturating_sub(20), m.start()) {
        opener(m, using)
    } else {
        None
    }
}

fn here(m: &Match, using: Use) -> Option<&'static str> {
    let (a, b) = m.span(1)?;
    ending(m.string, a, b, using)
}

fn hired(m: &Match, using: Use) -> Option<&'static str> {
    title(m.string, m.end(), None, using)?.0
}

fn abroad(m: &Match) -> Option<&'static str> {
    let (key, _) = spot(m.string, m.end(), Some(1), &FOREIGN_BLOCKED, &FOREIGN_TITLES, &FOREIGN_HEADS)?;
    Some(FOREIGN_TITLES[&key])
}

fn fragment(m: &Match) -> Option<&'static str> {
    let text = m.string;
    let lead = m.text();
    let persona = PERSONA.test(lead);
    if !persona {
        let end = m.end();
        if end >= text.len() || !alnum(text[end]) {
            return None;
        }
        let first = st(&text[end..token_end(text, end, text.len())]);
        if !TITLE_HEADS.contains(&first) {
            return None;
        }
    }
    if contains(lead, "hir") {
        return None;
    }
    let (value, end) = title(text, m.end(), Some(if persona { 2 } else { 0 }), Use::Job)?;
    if question(text, end) {
        return None;
    }
    if persona {
        return if PERSONA_END.at(text, end).is_some() { value } else { None };
    }
    if STRICT_END.at(text, end).is_some() && (SELF.test_in(text, end, end + 120) || text.len() < 60) {
        value
    } else {
        None
    }
}

fn retiree(m: &Match) -> Option<&'static str> {
    let (value, end) = title(m.string, m.end(), Some(1), Use::Job)?;
    if STRICT_END.at(m.string, end).is_some() { value } else { None }
}

fn tagged(m: &Match) -> Option<&'static str> {
    let text = m.string;
    let (value, end) = title(text, m.end(), Some(2), Use::Job)?;
    if question(text, end) || WANTED.test_in(text, m.start(), end) || OBJECT.at(text, end).is_some() {
        return None;
    }
    value
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
    let (value, end) = title(text, m.end(), Some(0), Use::Job)?;
    if STRICT_END.at(text, end).is_some() {
        value
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
    Box::new(move |m| match find(m) {
        Some(value) if value == FOUNDER => Some(BUSINESS.to_string()),
        Some(value) if value == OWNER => None,
        other => found(other),
    })
}

fn employed(find: impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static) -> V {
    Box::new(move |m| find(m).map(|value| if value == OWNER || value == FOUNDER { OWNER.to_string() } else { "employed".to_string() }))
}

fn scoped_with(value: V, hedge: &'static Re, played: bool) -> V {
    Box::new(move |m| if free(m.string, m.start(), hedge) && (played || !roleplay(m.string)) { value(m) } else { None })
}

fn scoped(value: V) -> V {
    scoped_with(value, &SELF_HEDGE, false)
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
        Some("college student".to_string())
    } else {
        None
    }
}

fn cased(m: &Match) -> Option<String> {
    let text = original(m.string)?;
    if !text.is_empty() && text[m.end() - 2..m.end()] == ['I', 'T'] {
        Some(SOFTWARE.to_string())
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
    if SHORT.contains(degree.as_str()) {
        let subject = m.g(2);
        if !is_subject(&subject) && !is_subject(subject.split_whitespace().next().unwrap_or("")) {
            return None;
        }
    }
    let left = clause(text, start).max(start.saturating_sub(60));
    if ASPIRING.test_in(text, left, start) || !(FIRST_NEAR.test_in(text, start.saturating_sub(80), start) || line_start(text, start) == start) {
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
    if block.contains(name.as_str()) {
        None
    } else {
        SUBJECTS.get(&name).copied().flatten().map(String::from)
    }
}

fn subject_before(text: &[char], start: usize) -> Option<String> {
    let words: Vec<String> = WORDS.iter_in(text, start.saturating_sub(60), start).map(|w| st(w.text())).collect();
    for size in [4, 3, 2, 1] {
        if words.len() >= size {
            let key = words[words.len() - size..].join(" ");
            if let Some(value) = SUBJECTS.get(&key) {
                return value.map(String::from);
            }
        }
    }
    None
}

fn leveled(m: &Match) -> Option<String> {
    let span = m.text();
    if GRADUATE_LEVEL.test(span) {
        Some("graduate student".to_string())
    } else if SCHOOL_LEVEL.test(span) {
        Some("high school student".to_string())
    } else if LEVELED.test(span) {
        None
    } else {
        Some("college student".to_string())
    }
}

fn period(name: Option<&str>, annual: bool) -> Option<f64> {
    let times = match name {
        None | Some("year" | "yr" | "annum" | "annually" | "yearly") => 1.0,
        Some("month" | "mo" | "monthly") => 12.0,
        Some("week" | "wk" | "weekly") => 52.0,
        Some("hour" | "hr" | "hourly") => 2080.0,
        _ => return None,
    };
    if annual && times != 1.0 {
        None
    } else {
        Some(times)
    }
}

fn scale(name: Option<&[char]>) -> f64 {
    match name.map(st).as_deref() {
        Some("k" | "thousand" | "grand") => 1000.0,
        Some("mil" | "million") => 1_000_000.0,
        _ => 1.0,
    }
}

fn income(m: &Match, annual: bool) -> Option<String> {
    let name = m.gs(4).or_else(|| m.gs(5)).or_else(|| if contains(m.text(), "hourly") { Some("hourly".to_string()) } else { None });
    let times = period(name.as_deref(), annual)?;
    if times > 1.0 && (MILESTONE.test(m.text()) || COMPARED.at(m.string, m.end()).is_some()) {
        return None;
    }
    let digits: Vec<char> = m.group(1)?.iter().copied().filter(|&c| c != ',').collect();
    let amount = py_float(&digits)? * scale(m.group(2).or(m.group(3))) * times;
    if (1000.0..=100_000_000.0).contains(&amount) {
        Some((amount as i64).to_string())
    } else {
        None
    }
}

fn earning(m: &Match) -> Option<String> {
    let text = m.string;
    let start = m.start();
    let left = clause(text, start);
    if (owned(text, start, 50) || PERSONA.test_in(text, left, start)) && !EARNERS.test_in(text, left, start) {
        income(m, false)
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
