mod lexicon;
mod patterns;
mod standing;
mod vocab;

use claimcore::*;
use lexicon::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::sync::LazyLock;
use vocab::*;

type V = Box<dyn Fn(&Match) -> Option<String> + Send + Sync>;

static CONDITIONAL: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:if|would|wish|imagine|pretend|unless|whether|might|maybe)\b"));
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
const KIN: &str = "he|she|they|his|her|their|him|them|husband|wife|boyfriend|girlfriend|partner|friend|friends|brother|sister|son|daughter|mom|mum|dad|mother|father|cousin|roommate";
static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{KIN}|you|your|u|someone|anyone|everyone|everybody|nobody|people)\b")));
static FIRST_NEAR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me)\b"));
pub(crate) static ASPIRING: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"\b(?:eventually|someday|love to|build|building|idea|goal|goals|pursue|pursuing|planning|plan|plans|apply|applying|application|considering|thinking|soch|want|wanted|wanting|hoping|dream|future|next|aspiring|",
    r"get|getting|start|starting|consider|choose|choosing|need|needs|require|requires|required|offer|offers)\b")));

pub(crate) const SELF_EMPLOYED: &str = "self-employed / freelance";

pub(crate) static BUSINESS_MAP: LazyLock<Map> = LazyLock::new(|| listed(BUSINESSES));
pub(crate) static FIELD_MAP: LazyLock<Map> = LazyLock::new(|| listed(FIELDS));
pub(crate) static VERB_MAP: LazyLock<Map> = LazyLock::new(|| pairs(VERBS));

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
        let unknown: Vec<&str> = VERBS.iter().map(|(_, title)| *title).chain(["registered nurse", "teacher"]).filter(|title| !TITLES.contains_key(*title)).collect();
        assert!(unknown.is_empty(), "occupation titles without a job family: {unknown:?}");
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

fn sector(m: &Match) -> Option<String> {
    let key = keyed(&FIELD_MAP, m.group(1))?;
    if key.starts_with("a ") || FIELD_MAP[&key] == Some(MILITARY) {
        return None;
    }
    Some(key.trim_start_matches("the ").to_string())
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
    let lead = &text[m.start().max(body(text)).min(m.end())..m.end()];
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

#[track_caller]
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

fn cased(m: &Match) -> Option<String> {
    let text = original(m.string)?;
    if !text.is_empty() && text[m.end() - 2..m.end()] == ['I', 'T'] {
        Some("it".to_string())
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

fn family(value: &str) -> Option<&'static str> {
    if value.starts_with("retired ") {
        return None;
    }
    if value == "it" {
        return Some(SOFTWARE);
    }
    if let Some(stem) = value.strip_suffix(" owner").filter(|_| !TITLES.contains_key(value)) {
        return *BUSINESS_MAP.get(stem).or_else(|| BUSINESS_MAP.get(&format!("own {stem}"))).unwrap_or_else(|| panic!("{value:?} names no known business"));
    }
    if let Some(field) = FIELD_MAP.get(value).or_else(|| FIELD_MAP.get(&format!("the {value}"))) {
        return *field;
    }
    match job_kind(value) {
        OWNER => None,
        FOUNDER => Some(BUSINESS),
        kind => Some(kind),
    }
}

pub fn settle(found: &mut Found) {
    let grouped: Vec<(&'static str, usize, Origin)> = found.items.iter()
        .filter(|(attribute, ..)| attribute == "occupation")
        .filter_map(|(_, value, position, origin)| family(value).map(|group| (group, *position, *origin)))
        .collect();
    for (group, position, origin) in grouped {
        found.put("occupation_group", group, position, origin);
    }
}
