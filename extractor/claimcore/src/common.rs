use crate::re::{Match, Re, M};
use crate::text::*;
use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;

pub const I: &str = r"(?:i'm|im|i am|iam|i m|i'am|i'?ve been|i've always been)";
pub const TAG: &str = r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?([mf])|([mf])\s?(\d{2}))(?![\w'%])";
pub const FOR: &str = r"(?<![a-z0-9])(?:(\d{2})\s*)?[\[\(]?\s*(nb|[mf])[mf]?\s*4\s*(?:[mfatr]|me|r|nb)\w*\s*[\]\)]?(?:\s*[-–|:#]?\s*(\d{2})(?!\d))?";

pub static MASKED: LazyLock<Re> = LazyLock::new(|| Re::with(r"https?://\S+|www\.\S+|\]\([^)\s]*\)|^[ \t]*(?:>|&gt;)[^\n]*", M));
pub static HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|wants to|trying to|tryna|going to|gonna|might|maybe|someday|used to|",
    r"not|never|no longer|anymore|former|formerly|when i was|back when|before i was)\b|n't\b"
)));
pub static SELF_HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|trying to|going to|gonna|might|maybe|used to|not|never|no longer|anymore|",
    r"when i was|back when)\b|n't\b"
)));
static FLAIRED: LazyLock<Re> = LazyLock::new(|| Re::new(r"r/\w+:\s*"));
static ASKED: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^.!?\n,;]{0,40}\?"));
static BOUNDARY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:because|cause|cuz|coz|cos|bc|since|and|but|so|although|though|as)\b"));
static SUBORDINATE: LazyLock<Re> = LazyLock::new(|| Re::new(r"if|unless|whether|when i was|back when|before i was|wish|hope|imagine|pretend"));
static NEGATION: LazyLock<Re> = LazyLock::new(|| Re::new(r"n't|not|never|no longer|anymore"));
static SUBJECT: LazyLock<Re> = LazyLock::new(|| Re::new(r"i(?:m|ve)?\b"));
static BRIDGE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"^(?:\W*\b(?:think|thinks|thought|believe|believes|say|says|said|saying|mean|means|meant|sure|certain|convinced|know|knew|guess|feel|feels|felt|like|seem|seems|sound|sounds|",
    r"look|looks|call|consider|claim|claiming|admit|realize|realise|remember|suppose|that|it|it's|its|is|was|be|to|even|really|actually|necessarily|exactly|honestly|so|too|quite)\b)*\W*$"
)));
pub static BOT_TEXT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bi am a bot\b|\bperformed automatically\b|\bplease (?:make sure|include|read)\b|\bpost (?:has been |was )?removed\b|\bmust (?:include|contain)\b"));

pub type Hedge = Option<&'static Re>;
pub const TAGGED: Hedge = None;

pub fn hedge() -> Hedge {
    Some(&*HEDGE)
}

pub fn self_hedge() -> Hedge {
    Some(&*SELF_HEDGE)
}

pub fn fold(c: char) -> char {
    match c {
        '\u{2019}' | '\u{2018}' | '\u{b4}' | '\u{2bc}' | '\u{ff07}' | '`' => '\'',
        '\u{130}' => 'I',
        _ => c,
    }
}

pub fn prepared(raw: &str) -> Vec<char> {
    let text: Vec<char> = raw.chars().map(fold).collect();
    let mut out = text.clone();
    for found in MASKED.iter(&text) {
        for c in &mut out[found.start()..found.end()] {
            *c = ' ';
        }
    }
    out
}

pub fn clause(text: &[char], start: usize) -> usize {
    last_mark(text, start, ".!?\n;,")
}

pub fn question(text: &[char], end: usize) -> bool {
    let stop = next_mark(text, end, ".!\n");
    end < stop && text[end..stop].contains(&'?')
}

pub fn opening(text: &[char]) -> usize {
    FLAIRED.at(text, 0).map_or(0, |m| m.end())
}

pub fn asked(text: &[char], end: usize) -> bool {
    ASKED.at(text, end).is_some()
}

fn qualifies(text: &[char], hedge: &Match, start: usize) -> bool {
    let word = hedge.text();
    let between = &text[hedge.end()..start];
    if BOUNDARY.test(between) {
        return false;
    }
    if SUBJECT.at(text, start).is_none() || SUBORDINATE.fullmatch(word, 0, word.len()).is_some() {
        return true;
    }
    BRIDGE.test(between) && !(NEGATION.fullmatch(word, 0, word.len()).is_some() && between.iter().all(|c| !c.is_alphanumeric()))
}

pub fn limited(text: &[char], start: usize, pattern: &Re) -> bool {
    pattern.iter_in(text, clause(text, start).max(start.saturating_sub(40)), start).any(|hedge| qualifies(text, &hedge, start))
}

pub fn hedged(text: &[char], start: usize, end: usize, pattern: Hedge) -> bool {
    pattern.is_some_and(|pattern| limited(text, start, pattern) || asked(text, end))
}

pub type ValueFn = Box<dyn Fn(&Match) -> Option<String> + Send + Sync>;
pub type Origin = &'static std::panic::Location<'static>;

pub struct Rule {
    pub attribute: &'static str,
    pub re: Re,
    pub gate: Option<Vec<Vec<char>>>,
    pub value: ValueFn,
    pub hedge: Hedge,
    pub origin: Origin,
}

#[track_caller]
pub fn rule(attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static, hedge: Hedge) -> Rule {
    Rule { attribute, re: Re::new(pattern), gate: None, value: Box::new(value), hedge, origin: std::panic::Location::caller() }
}

pub fn needs(mut entry: Rule, anchors: &[&str]) -> Rule {
    entry.gate = Some(anchors.iter().map(|a| a.chars().collect()).collect());
    entry
}

pub fn words_present(anchors: &[Vec<char>], text: &[char]) -> bool {
    anchors.iter().any(|anchor| contains_chars(text, anchor))
}

pub fn contains_chars(text: &[char], needle: &[char]) -> bool {
    if needle.is_empty() {
        return true;
    }
    if needle.len() > text.len() {
        return false;
    }
    let first = needle[0];
    (0..=text.len() - needle.len()).any(|i| text[i] == first && &text[i..i + needle.len()] == needle)
}

impl Rule {
    pub fn open(&self, text: &[char]) -> bool {
        self.gate.as_ref().map_or(true, |anchors| words_present(anchors, text))
    }
}

pub fn fixed(result: &'static str) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |_| Some(result.to_string())
}

pub type Table = HashMap<String, &'static str>;

pub fn table(pairs: &[(&str, &'static str)]) -> Table {
    pairs.iter().map(|(k, v)| (k.to_string(), *v)).collect()
}

pub fn lookup(table: &Table, key: Option<&[char]>) -> Option<String> {
    key.and_then(|k| table.get(&st(k)).map(|v| v.to_string()))
}

pub fn group(table: &'static LazyLock<Table>, number: usize) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| lookup(table, m.group(number))
}

pub fn escape(word: &str) -> String {
    let mut out = String::with_capacity(word.len() + 4);
    for c in word.chars() {
        if c.is_ascii_alphanumeric() || c == '_' || !c.is_ascii() {
            out.push(c);
        } else if c == '\n' {
            out.push_str("\\n");
        } else if c == '\t' {
            out.push_str("\\t");
        } else {
            out.push('\\');
            out.push(c);
        }
    }
    out
}

pub fn alternation<'a>(words: impl IntoIterator<Item = &'a str>) -> String {
    words.into_iter().map(escape).collect::<Vec<_>>().join("|")
}

pub fn longest_first<'a>(words: impl IntoIterator<Item = &'a str>) -> String {
    let mut sorted: Vec<&str> = words.into_iter().collect();
    sorted.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    sorted.dedup();
    alternation(sorted)
}

pub struct Names {
    index: HashMap<String, Vec<HashSet<String>>>,
}

impl Names {
    pub fn new<'a>(names: impl IntoIterator<Item = &'a str>) -> Names {
        let mut index: HashMap<String, Vec<HashSet<String>>> = HashMap::new();
        for name in names {
            let tokens: Vec<&str> = name.split(' ').collect();
            let mut key = tokens[0];
            for token in &tokens {
                if token.chars().count() > key.chars().count() {
                    key = token;
                }
            }
            index.entry(key.to_string()).or_default().push(tokens.iter().map(|t| t.to_string()).collect());
        }
        Names { index }
    }

    pub fn within(&self, words: &HashSet<String>) -> bool {
        words.iter().any(|word| self.index.get(word).map_or(false, |sets| sets.iter().any(|tokens| tokens.is_subset(words))))
    }
}
