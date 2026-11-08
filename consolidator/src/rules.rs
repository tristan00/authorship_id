use crate::database::put_string;
use crate::schema::{decomposed, stored_field, BOT};
use std::collections::{HashMap, HashSet};

pub const TEXT: u32 = u32::MAX;
pub const NEED: u32 = 1;
const SHARE: f64 = 0.5;
const CHILD_AGE: f64 = 18.0;
const NOT_A_CHILD: [(&str, &[&str]); 3] = [
    ("parental_status", &["has children"]),
    ("relationship_status", &["married", "separated", "divorced", "widowed"]),
    ("employment_status", &["retired"]),
];
const BOT_TEXTS: u32 = 3;
const BOT_SHARE: f64 = 0.2;
const GATE_COMPARISONS: u64 = 30;
const GATE_SKILL: f64 = 0.25;
const FAN: &str = "fan_";

#[derive(Clone, Copy)]
enum Span {
    Absolute(f64),
    Relative(f64),
}

impl Span {
    fn close(self, left: f64, right: f64) -> bool {
        match self {
            Span::Absolute(amount) => (left - right).abs() <= amount,
            Span::Relative(amount) => (left - right).abs() <= amount * left.max(right),
        }
    }
}

#[derive(Clone, Copy)]
struct Numeric {
    tolerance: Span,
    wide: Span,
    low: f64,
    high: f64,
}

fn numeric(name: &str) -> Option<Numeric> {
    let (tolerance, wide, low, high) = match name {
        "age" => (Span::Absolute(1.0), Span::Absolute(5.0), 13.0, 100.0),
        "height" => (Span::Absolute(2.0), Span::Absolute(5.0), 120.0, 230.0),
        "weight" => (Span::Relative(0.05), Span::Relative(0.15), 30.0, 300.0),
        "income" => (Span::Relative(0.1), Span::Relative(0.5), 1000.0, 10_000_000.0),
        _ => return None,
    };
    Some(Numeric { tolerance, wide, low, high })
}

#[derive(Default)]
pub struct Interner {
    ids: HashMap<String, u32>,
    texts: Vec<String>,
}

impl Interner {
    pub fn id(&mut self, text: &str) -> u32 {
        if let Some(&id) = self.ids.get(text) {
            return id;
        }
        let id = self.texts.len() as u32;
        self.ids.insert(text.to_string(), id);
        self.texts.push(text.to_string());
        id
    }

    pub fn get(&self, id: u32) -> &str {
        &self.texts[id as usize]
    }

    pub fn len(&self) -> usize {
        self.texts.len()
    }
}

struct Claim {
    bot: bool,
    parts: Vec<(u32, u32)>,
}

pub struct Vocabulary {
    names: Interner,
    values: Interner,
    pub subreddits: Interner,
    numeric: Vec<Option<Numeric>>,
    single: Vec<bool>,
    numbers: Vec<Option<f64>>,
    claim_ids: HashMap<Vec<u8>, u32>,
    claims: Vec<Claim>,
    key: Vec<u8>,
    age: u32,
    adult: Vec<(u32, Vec<u32>)>,
}

impl Vocabulary {
    pub fn new() -> Vocabulary {
        let mut vocabulary = Vocabulary {
            names: Interner::default(),
            values: Interner::default(),
            subreddits: Interner::default(),
            numeric: Vec::new(),
            single: Vec::new(),
            numbers: Vec::new(),
            claim_ids: HashMap::new(),
            claims: Vec::new(),
            key: Vec::new(),
            age: 0,
            adult: Vec::new(),
        };
        vocabulary.age = vocabulary.name("age");
        vocabulary.adult = NOT_A_CHILD.iter().map(|(field, values)| (vocabulary.name(field), values.iter().map(|value| vocabulary.values.id(value)).collect())).collect();
        vocabulary
    }

    fn name(&mut self, name: &str) -> u32 {
        let id = self.names.id(name);
        if id as usize == self.numeric.len() {
            self.numeric.push(numeric(name));
            self.single.push(!name.starts_with(FAN));
        }
        id
    }

    fn value(&mut self, name: u32, value: &str) -> u32 {
        let id = self.values.id(value);
        self.numbers.resize(self.values.len(), None);
        if self.numeric[name as usize].is_some() && self.numbers[id as usize].is_none() {
            self.numbers[id as usize] = Some(value.parse().unwrap_or_else(|error| panic!("numeric value {value:?} does not parse: {error}")));
        }
        id
    }

    pub fn claim(&mut self, attribute: &[u8], value: &[u8]) -> u32 {
        self.key.clear();
        self.key.extend_from_slice(attribute);
        self.key.push(0);
        self.key.extend_from_slice(value);
        if let Some(&id) = self.claim_ids.get(&self.key) {
            return id;
        }
        let (attribute, value) = (String::from_utf8_lossy(attribute).into_owned(), String::from_utf8_lossy(value).into_owned());
        let bot = attribute == BOT;
        let parts = if bot {
            Vec::new()
        } else {
            decomposed(&stored_field(&attribute), &value)
                .into_iter()
                .map(|(name, stated)| {
                    let name = self.name(&name);
                    (name, self.value(name, &stated))
                })
                .collect()
        };
        let id = self.claims.len() as u32;
        self.claims.push(Claim { bot, parts });
        self.claim_ids.insert(self.key.clone(), id);
        id
    }

    pub fn claim_count(&self) -> usize {
        self.claims.len()
    }

    fn number(&self, value: u32) -> f64 {
        self.numbers[value as usize].unwrap()
    }

    fn near(&self, name: u32, left: u32, right: u32) -> bool {
        match self.numeric[name as usize] {
            Some(numeric) => numeric.wide.close(self.number(left), self.number(right)),
            None => left == right,
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct Item {
    name: u32,
    stated: u32,
    doc: u32,
    subreddit: u32,
    time: u32,
}

#[derive(Clone, Copy)]
struct Support {
    value: u32,
    count: u32,
    newest: u32,
}

#[derive(Default)]
pub struct Evidence {
    texts: u32,
    flagged: u32,
    docs: u32,
    flaired: bool,
    items: Vec<Item>,
}

impl Evidence {
    pub fn add(&mut self, vocabulary: &Vocabulary, subreddit: u32, time: u32, claims: &[u32]) {
        let doc = self.docs;
        self.docs += 1;
        if subreddit == TEXT {
            self.texts += 1;
            self.flagged += claims.iter().any(|&claim| vocabulary.claims[claim as usize].bot) as u32;
        } else {
            self.flaired = true;
        }
        for &claim in claims {
            for &(name, stated) in &vocabulary.claims[claim as usize].parts {
                self.items.push(Item { name, stated, doc, subreddit, time });
            }
        }
    }

    pub fn finish(&mut self) {
        self.items.sort_unstable();
    }

    fn found(&self, blocked: &Blocked, flairs: bool) -> Vec<(u32, Vec<Support>)> {
        let mut found: Vec<(u32, Vec<Support>)> = Vec::new();
        let mut last = None;
        for item in &self.items {
            if item.subreddit != TEXT && (!flairs || blocked.contains(&(item.subreddit, item.name))) {
                continue;
            }
            if last == Some((item.name, item.stated, item.doc)) {
                continue;
            }
            last = Some((item.name, item.stated, item.doc));
            if found.last().map(|entry| entry.0) != Some(item.name) {
                found.push((item.name, Vec::new()));
            }
            let values = &mut found.last_mut().unwrap().1;
            match values.last_mut() {
                Some(entry) if entry.value == item.stated => {
                    entry.count += 1;
                    entry.newest = entry.newest.max(item.time);
                }
                _ => values.push(Support { value: item.stated, count: 1, newest: item.time }),
            }
        }
        found
    }
}

pub type Blocked = HashSet<(u32, u32)>;

pub struct Decision {
    name: u32,
    best: u32,
    score: u32,
    share: f64,
    support: Vec<Support>,
}

fn tally(vocabulary: &Vocabulary, name: u32, values: &[Support], recent: bool) -> Option<Decision> {
    let numeric = vocabulary.numeric[name as usize];
    let support: Vec<Support> = match numeric {
        Some(bounds) => values.iter().filter(|entry| (bounds.low..=bounds.high).contains(&vocabulary.number(entry.value))).copied().collect(),
        None => values.to_vec(),
    };
    if support.is_empty() {
        return None;
    }
    let scores: Vec<u32> = match numeric {
        Some(bounds) => support
            .iter()
            .map(|entry| support.iter().filter(|other| bounds.tolerance.close(vocabulary.number(entry.value), vocabulary.number(other.value))).map(|other| other.count).sum())
            .collect(),
        None => support.iter().map(|entry| entry.count).collect(),
    };
    let mut order: Vec<usize> = (0..support.len()).collect();
    order.sort_by(|&left, &right| vocabulary.values.get(support[left].value).cmp(vocabulary.values.get(support[right].value)));
    let rank = |index: usize| (if recent { support[index].newest } else { 0 }, scores[index], support[index].count);
    let mut best = order[0];
    for &index in &order[1..] {
        if rank(index) > rank(best) {
            best = index;
        }
    }
    let total: u32 = support.iter().map(|entry| entry.count).sum();
    Some(Decision { name, best: support[best].value, score: scores[best], share: scores[best] as f64 / total as f64, support })
}

fn plurality(decision: &Decision) -> bool {
    let best = decision.support.iter().find(|entry| entry.value == decision.best).unwrap().count;
    decision.support.iter().all(|entry| entry.value == decision.best || entry.count < best)
}

fn decide(vocabulary: &Vocabulary, found: &[(u32, Vec<Support>)], need: u32) -> Vec<Decision> {
    let mut decided: Vec<Decision> = found
        .iter()
        .filter_map(|(name, values)| {
            let decision = tally(vocabulary, *name, values, false)?;
            if decision.score >= need && (decision.share > SHARE || plurality(&decision)) {
                Some(decision)
            } else if vocabulary.single[*name as usize] {
                tally(vocabulary, *name, values, true).filter(|decision| decision.score >= need)
            } else {
                None
            }
        })
        .collect();
    if let Some(age) = decided.iter().position(|decision| decision.name == vocabulary.age) {
        let adult = vocabulary.adult.iter().any(|(field, values)| decided.iter().any(|decision| decision.name == *field && values.contains(&decision.best)));
        if vocabulary.number(decided[age].best) < CHILD_AGE && adult {
            decided.remove(age);
        }
    }
    decided
}

pub fn consolidate(vocabulary: &Vocabulary, evidence: &Evidence, need: u32, blocked: &Blocked) -> Vec<Decision> {
    if evidence.flagged >= BOT_TEXTS && evidence.flagged as f64 >= BOT_SHARE * evidence.texts as f64 {
        return Vec::new();
    }
    decide(vocabulary, &evidence.found(blocked, true), need)
}

#[derive(Default)]
pub struct Tallies {
    stats: HashMap<(u32, u32, u32), (u64, u64)>,
    base: HashMap<(u32, u32), u64>,
}

impl Tallies {
    pub fn merge(&mut self, other: Tallies) {
        for (key, (count, hits)) in other.stats {
            let entry = self.stats.entry(key).or_default();
            entry.0 += count;
            entry.1 += hits;
        }
        for (key, count) in other.base {
            *self.base.entry(key).or_default() += count;
        }
    }
}

fn audit(vocabulary: &Vocabulary, evidence: &Evidence, need: u32, tallies: &mut Tallies) {
    let decided = decide(vocabulary, &evidence.found(&Blocked::new(), false), need);
    for decision in &decided {
        *tallies.base.entry((decision.name, decision.best)).or_default() += 1;
    }
    let mut pairs: Vec<(u32, u32, u32)> = evidence.items.iter().filter(|item| item.subreddit != TEXT).map(|item| (item.subreddit, item.name, item.stated)).collect();
    pairs.sort_unstable();
    pairs.dedup();
    for (subreddit, name, stated) in pairs {
        if let Some(decision) = decided.iter().find(|decision| decision.name == name) {
            let entry = tallies.stats.entry((subreddit, name, stated)).or_default();
            entry.0 += 1;
            entry.1 += vocabulary.near(name, stated, decision.best) as u64;
        }
    }
}

pub enum Step {
    Decided(Vec<Decision>),
    Deferred(Evidence),
}

pub fn first(vocabulary: &Vocabulary, evidence: Evidence, need: u32, tallies: &mut Tallies) -> Step {
    if evidence.flaired {
        audit(vocabulary, &evidence, need, tallies);
        Step::Deferred(evidence)
    } else {
        Step::Decided(consolidate(vocabulary, &evidence, need, &Blocked::new()))
    }
}

pub fn blocked(vocabulary: &Vocabulary, tallies: &Tallies) -> Blocked {
    let mut base: HashMap<u32, Vec<(u32, u64)>> = HashMap::new();
    for (&(name, value), &count) in &tallies.base {
        base.entry(name).or_default().push((value, count));
    }
    let totals: HashMap<u32, u64> = base.iter().map(|(&name, values)| (name, values.iter().map(|entry| entry.1).sum())).collect();
    let mut chances: HashMap<(u32, u32), f64> = HashMap::new();
    let mut stats: Vec<(&(u32, u32, u32), &(u64, u64))> = tallies.stats.iter().collect();
    stats.sort_unstable();
    let mut scopes: HashMap<(u32, u32), (u64, u64, f64)> = HashMap::new();
    for (&(subreddit, name, value), &(count, hits)) in stats {
        let chance = *chances.entry((name, value)).or_insert_with(|| {
            base[&name].iter().filter(|&&(other, _)| vocabulary.near(name, value, other)).map(|entry| entry.1).sum::<u64>() as f64 / totals[&name] as f64
        });
        let entry = scopes.entry((subreddit, name)).or_default();
        entry.0 += count;
        entry.1 += hits;
        entry.2 += chance * count as f64;
    }
    let mut found = Blocked::new();
    let mut judged = 0;
    for (&scope, &(count, hits, expected)) in &scopes {
        let random = expected / count as f64;
        if count >= GATE_COMPARISONS {
            judged += 1;
            if (hits as f64 / count as f64 - random) / (1.0 - random).max(1e-6) < GATE_SKILL {
                found.insert(scope);
            }
        }
    }
    crate::log(&format!("flair gate scopes={} judged={judged} blocked={}", scopes.len(), found.len()));
    found
}

fn json_string(out: &mut String, text: &str) {
    out.push('"');
    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            control if (control as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", control as u32)),
            other => out.push(other),
        }
    }
    out.push('"');
}

impl Decision {
    pub fn attribute<'a>(&self, vocabulary: &'a Vocabulary) -> &'a str {
        vocabulary.names.get(self.name)
    }

    pub fn value<'a>(&self, vocabulary: &'a Vocabulary) -> &'a str {
        vocabulary.values.get(self.best)
    }

    pub fn support(&self) -> f32 {
        self.score as f32
    }

    pub fn share(&self) -> f32 {
        self.share as f32
    }

    pub fn candidates(&self, vocabulary: &Vocabulary) -> String {
        let mut ranked: Vec<(&str, u32)> = self.support.iter().map(|entry| (vocabulary.values.get(entry.value), entry.count)).collect();
        ranked.sort_by(|left, right| right.1.cmp(&left.1).then(left.0.cmp(right.0)));
        let mut out = String::from("[");
        for (index, (value, amount)) in ranked.iter().enumerate() {
            if index > 0 {
                out.push_str(", ");
            }
            out.push('[');
            json_string(&mut out, value);
            out.push_str(&format!(", {amount}]"));
        }
        out.push(']');
        out
    }

    pub fn encode(&self, vocabulary: &Vocabulary, author: &str, out: &mut Vec<u8>) {
        put_string(out, author);
        put_string(out, self.attribute(vocabulary));
        put_string(out, self.value(vocabulary));
        out.extend_from_slice(&self.support().to_le_bytes());
        out.extend_from_slice(&self.share().to_le_bytes());
        put_string(out, &self.candidates(vocabulary));
    }
}
