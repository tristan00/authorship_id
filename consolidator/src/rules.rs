use crate::database::put_string;
use std::collections::{HashMap, HashSet};

pub const TEXT: u32 = u32::MAX;
pub const NEED: u32 = 1;
const SHARE: f64 = 0.5;
const WIDE: f64 = 5.0;
const FIRST_YEAR: i64 = 1900;
const LAST_YEAR: i64 = 2100;
const BOT_TEXTS: u32 = 3;
const BOT_SHARE: f64 = 0.2;
const GATE_COMPARISONS: u64 = 30;
const GATE_SKILL: f64 = 0.25;

pub struct Attribute {
    pub name: String,
    pub kind: String,
    pub anchor: String,
    pub precision: f64,
}

fn year_of(seconds: u32) -> i64 {
    let days = seconds as i64 / 86_400 + 719_468;
    let era = days.div_euclid(146_097);
    let day = days - era * 146_097;
    let year = (day - day / 1460 + day / 36_524 - day / 146_096) / 365;
    let within = day - (365 * year + year / 4 - year / 100);
    let month = (5 * within + 2) / 153;
    year + era * 400 + (month >= 10) as i64
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
    marker: bool,
    name: u32,
    value: u32,
}

pub struct Vocabulary {
    names: Interner,
    values: Interner,
    pub subreddits: Interner,
    precision: Vec<Option<f64>>,
    set: Vec<bool>,
    marker: Vec<bool>,
    anchor: Vec<Option<u32>>,
    years: Vec<u32>,
    numbers: Vec<Option<f64>>,
    claim_ids: HashMap<Vec<u8>, u32>,
    claims: Vec<Claim>,
    key: Vec<u8>,
}

impl Vocabulary {
    pub fn new(attributes: &[Attribute]) -> Vocabulary {
        let mut vocabulary = Vocabulary {
            names: Interner::default(),
            values: Interner::default(),
            subreddits: Interner::default(),
            precision: Vec::new(),
            set: Vec::new(),
            marker: Vec::new(),
            anchor: Vec::new(),
            years: Vec::new(),
            numbers: Vec::new(),
            claim_ids: HashMap::new(),
            claims: Vec::new(),
            key: Vec::new(),
        };
        for attribute in attributes {
            vocabulary.names.id(&attribute.name);
            vocabulary.precision.push((attribute.kind == "number").then_some(attribute.precision));
            vocabulary.set.push(attribute.kind == "set");
            vocabulary.marker.push(attribute.kind == "marker");
        }
        vocabulary.anchor = attributes
            .iter()
            .map(|attribute| {
                (!attribute.anchor.is_empty())
                    .then(|| *vocabulary.names.ids.get(&attribute.anchor).unwrap_or_else(|| panic!("{} anchors to unknown attribute {}", attribute.name, attribute.anchor)))
            })
            .collect();
        if vocabulary.anchor.iter().any(Option::is_some) {
            vocabulary.years = (FIRST_YEAR..=LAST_YEAR).map(|year| vocabulary.number_value(&year.to_string())).collect();
        }
        vocabulary
    }

    fn name(&self, name: &str) -> u32 {
        *self.names.ids.get(name).unwrap_or_else(|| panic!("claimed attribute {name:?} is not in claim_attributes"))
    }

    fn number_value(&mut self, value: &str) -> u32 {
        let id = self.values.id(value);
        self.numbers.resize(self.values.len(), None);
        self.numbers[id as usize] = Some(value.parse().unwrap_or_else(|error| panic!("numeric value {value:?} does not parse: {error}")));
        id
    }

    fn value(&mut self, name: u32, value: &str) -> u32 {
        if self.precision[name as usize].is_some() {
            return self.number_value(value);
        }
        let id = self.values.id(value);
        self.numbers.resize(self.values.len(), None);
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
        let name = self.name(&String::from_utf8_lossy(attribute));
        let value = self.value(name, &String::from_utf8_lossy(value));
        let id = self.claims.len() as u32;
        self.claims.push(Claim { marker: self.marker[name as usize], name, value });
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
        match self.precision[name as usize] {
            Some(precision) => (self.number(left) - self.number(right)).abs() <= WIDE * precision,
            None => left == right,
        }
    }

    fn stated(&self, claim: &Claim, time: u32) -> Option<(u32, u32)> {
        let Some(target) = self.anchor[claim.name as usize] else {
            return Some((claim.name, claim.value));
        };
        let year = year_of(time) - self.number(claim.value).round() as i64;
        let index = usize::try_from(year - FIRST_YEAR).ok().filter(|&index| index < self.years.len())?;
        Some((target, self.years[index]))
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
            self.flagged += claims.iter().any(|&claim| vocabulary.claims[claim as usize].marker) as u32;
        } else {
            self.flaired = true;
        }
        for &claim in claims {
            let claim = &vocabulary.claims[claim as usize];
            if claim.marker {
                continue;
            }
            if let Some((name, stated)) = vocabulary.stated(claim, time) {
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

fn tally(vocabulary: &Vocabulary, name: u32, support: &[Support], recent: bool) -> Option<Decision> {
    if support.is_empty() {
        return None;
    }
    let scores: Vec<u32> = match vocabulary.precision[name as usize] {
        Some(precision) => support
            .iter()
            .map(|entry| support.iter().filter(|other| (vocabulary.number(entry.value) - vocabulary.number(other.value)).abs() <= precision).map(|other| other.count).sum())
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
    Some(Decision { name, best: support[best].value, score: scores[best], share: scores[best] as f64 / total as f64, support: support.to_vec() })
}

fn plurality(decision: &Decision) -> bool {
    let best = decision.support.iter().find(|entry| entry.value == decision.best).unwrap().count;
    decision.support.iter().all(|entry| entry.value == decision.best || entry.count < best)
}

fn decide(vocabulary: &Vocabulary, found: &[(u32, Vec<Support>)], need: u32) -> Vec<Decision> {
    let mut decided = Vec::new();
    for (name, values) in found {
        if vocabulary.set[*name as usize] {
            let total: u32 = values.iter().map(|entry| entry.count).sum();
            decided.extend(values.iter().filter(|entry| entry.count >= need).map(|entry| Decision {
                name: *name,
                best: entry.value,
                score: entry.count,
                share: entry.count as f64 / total as f64,
                support: values.clone(),
            }));
            continue;
        }
        let Some(decision) = tally(vocabulary, *name, values, false) else { continue };
        if decision.score >= need && (decision.share > SHARE || plurality(&decision)) {
            decided.push(decision);
        } else if let Some(recent) = tally(vocabulary, *name, values, true).filter(|decision| decision.score >= need) {
            decided.push(recent);
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

impl Decision {
    pub fn encode(&self, vocabulary: &Vocabulary, author: &str, out: &mut Vec<u8>) {
        put_string(out, author);
        put_string(out, vocabulary.names.get(self.name));
        put_string(out, vocabulary.values.get(self.best));
    }
}
