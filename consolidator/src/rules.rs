use crate::database::put_string;
use std::collections::{BTreeMap, HashMap, HashSet};

pub const TEXT: u32 = u32::MAX;
const SHARE: f64 = 0.5;
const WIDE: f64 = 5.0;
const BOT_TEXTS: u32 = 3;
const BOT_SHARE: f64 = 0.2;
const GATE_COMPARISONS: u64 = 30;
const GATE_SKILL: f64 = 0.25;

pub struct Attribute {
    pub name: String,
    pub kind: String,
    pub anchor: String,
    pub precision: f64,
    pub unit: String,
    pub range: Option<(f64, f64)>,
}

fn years_per(attribute: &Attribute) -> f64 {
    match attribute.unit.as_str() {
        "years" => 1.0,
        "months" => 1.0 / 12.0,
        "days" => 1.0 / 365.25,
        unit => panic!("{} anchors to {} but counts {unit:?}, not years, months or days", attribute.name, attribute.anchor),
    }
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

struct Anchor {
    target: u32,
    elapsed: f64,
    low: i64,
    years: Vec<u32>,
}

pub struct Vocabulary {
    names: Interner,
    values: Interner,
    pub subreddits: Interner,
    precision: Vec<Option<f64>>,
    set: Vec<bool>,
    marker: Vec<bool>,
    anchor: Vec<Option<Anchor>>,
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
        vocabulary.anchor = attributes.iter().map(|attribute| (!attribute.anchor.is_empty()).then(|| vocabulary.anchored(attributes, attribute))).collect();
        vocabulary
    }

    fn anchored(&mut self, attributes: &[Attribute], attribute: &Attribute) -> Anchor {
        let target = attributes.iter().find(|other| other.name == attribute.anchor).unwrap_or_else(|| panic!("{} anchors to unknown attribute {}", attribute.name, attribute.anchor));
        let (low, high) = target.range.unwrap_or_else(|| panic!("{} anchors to {}, which has no low and high in schema.json", attribute.name, target.name));
        let (low, high) = (low.ceil() as i64, high.floor() as i64);
        Anchor { target: self.names.ids[&target.name], elapsed: years_per(attribute), low, years: (low..=high).map(|year| self.number_value(&year.to_string())).collect() }
    }

    pub fn attribute(&self, name: u32) -> &str {
        self.names.get(name)
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
        let Some(anchor) = &self.anchor[claim.name as usize] else {
            return Some((claim.name, claim.value));
        };
        let year = year_of(time) - (self.number(claim.value) * anchor.elapsed).round() as i64;
        let index = usize::try_from(year - anchor.low).ok().filter(|&index| index < anchor.years.len())?;
        Some((anchor.target, anchor.years[index]))
    }
}

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct Item {
    name: u32,
    stated: u32,
    doc: u32,
    subreddit: u32,
}

struct Support {
    value: u32,
    count: u32,
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
                self.items.push(Item { name, stated, doc, subreddit });
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
                Some(entry) if entry.value == item.stated => entry.count += 1,
                _ => values.push(Support { value: item.stated, count: 1 }),
            }
        }
        found
    }
}

pub type Blocked = HashSet<(u32, u32)>;

pub struct Decision {
    name: u32,
    best: u32,
}

fn leader(vocabulary: &Vocabulary, name: u32, support: &[Support]) -> Option<u32> {
    let scores: Vec<u32> = match vocabulary.precision[name as usize] {
        Some(precision) => support
            .iter()
            .map(|entry| support.iter().filter(|other| (vocabulary.number(entry.value) - vocabulary.number(other.value)).abs() <= precision).map(|other| other.count).sum())
            .collect(),
        None => support.iter().map(|entry| entry.count).collect(),
    };
    let mut order: Vec<usize> = (0..support.len()).collect();
    order.sort_by(|&left, &right| vocabulary.values.get(support[left].value).cmp(vocabulary.values.get(support[right].value)));
    let rank = |index: usize| (scores[index], support[index].count);
    let mut best = order[0];
    for &index in &order[1..] {
        if rank(index) > rank(best) {
            best = index;
        }
    }
    let total: u32 = support.iter().map(|entry| entry.count).sum();
    let plurality = support.iter().enumerate().all(|(index, entry)| index == best || entry.count < support[best].count);
    (scores[best] as f64 / total as f64 > SHARE || plurality).then_some(support[best].value)
}

fn decide(vocabulary: &Vocabulary, found: &[(u32, Vec<Support>)]) -> (Vec<Decision>, Vec<u32>) {
    let (mut decided, mut tied) = (Vec::new(), Vec::new());
    for (name, support) in found {
        if vocabulary.set[*name as usize] {
            decided.extend(support.iter().map(|entry| Decision { name: *name, best: entry.value }));
        } else if let Some(best) = leader(vocabulary, *name, support) {
            decided.push(Decision { name: *name, best });
        } else {
            tied.push(*name);
        }
    }
    (decided, tied)
}

pub fn consolidate(vocabulary: &Vocabulary, evidence: &Evidence, blocked: &Blocked) -> (Vec<Decision>, Vec<u32>) {
    if evidence.flagged >= BOT_TEXTS && evidence.flagged as f64 >= BOT_SHARE * evidence.texts as f64 {
        return (Vec::new(), Vec::new());
    }
    decide(vocabulary, &evidence.found(blocked, true))
}

#[derive(Default)]
pub struct Tallies {
    stats: HashMap<(u32, u32, u32), (u64, u64)>,
    base: HashMap<(u32, u32), u64>,
    authors: HashMap<u32, u64>,
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
        for (key, count) in other.authors {
            *self.authors.entry(key).or_default() += count;
        }
    }
}

fn audit(vocabulary: &Vocabulary, evidence: &Evidence, tallies: &mut Tallies) {
    let (decided, _) = decide(vocabulary, &evidence.found(&Blocked::new(), false));
    for (index, decision) in decided.iter().enumerate() {
        *tallies.base.entry((decision.name, decision.best)).or_default() += 1;
        if index == 0 || decided[index - 1].name != decision.name {
            *tallies.authors.entry(decision.name).or_default() += 1;
        }
    }
    let mut pairs: Vec<(u32, u32, u32)> = evidence.items.iter().filter(|item| item.subreddit != TEXT).map(|item| (item.subreddit, item.name, item.stated)).collect();
    pairs.sort_unstable();
    pairs.dedup();
    for (subreddit, name, stated) in pairs {
        let entry = tallies.stats.entry((subreddit, name, stated)).or_default();
        let mut members = decided.iter().filter(|decision| decision.name == name).peekable();
        if members.peek().is_some() {
            entry.0 += 1;
            entry.1 += members.any(|decision| vocabulary.near(name, stated, decision.best)) as u64;
        }
    }
}

pub enum Step {
    Decided(Vec<Decision>, Vec<u32>),
    Deferred(Evidence),
}

pub fn first(vocabulary: &Vocabulary, evidence: Evidence, tallies: &mut Tallies) -> Step {
    if evidence.flaired {
        audit(vocabulary, &evidence, tallies);
        Step::Deferred(evidence)
    } else {
        let (decided, tied) = consolidate(vocabulary, &evidence, &Blocked::new());
        Step::Decided(decided, tied)
    }
}

fn skill(count: u64, hits: u64, expected: f64) -> f64 {
    let random = expected / count as f64;
    (hits as f64 / count as f64 - random) / (1.0 - random).max(1e-6)
}

fn agrees(count: u64, hits: u64, expected: f64) -> bool {
    count >= GATE_COMPARISONS && skill(count, hits, expected) >= GATE_SKILL
}

pub fn blocked(vocabulary: &Vocabulary, tallies: &Tallies) -> Blocked {
    let mut base: HashMap<u32, Vec<(u32, u64)>> = HashMap::new();
    for (&(name, value), &count) in &tallies.base {
        base.entry(name).or_default().push((value, count));
    }
    let mut chances: HashMap<(u32, u32), f64> = HashMap::new();
    let mut stats: Vec<(&(u32, u32, u32), &(u64, u64))> = tallies.stats.iter().collect();
    stats.sort_unstable();
    let mut scopes: BTreeMap<(u32, u32), (u64, u64, f64)> = BTreeMap::new();
    for (&(subreddit, name, value), &(count, hits)) in stats {
        let entry = scopes.entry((subreddit, name)).or_default();
        if count == 0 {
            continue;
        }
        let chance = *chances.entry((name, value)).or_insert_with(|| {
            base[&name].iter().filter(|&&(other, _)| vocabulary.near(name, value, other)).map(|entry| entry.1).sum::<u64>() as f64 / tallies.authors[&name] as f64
        });
        entry.0 += count;
        entry.1 += hits;
        entry.2 += chance * count as f64;
    }
    let mut found = Blocked::new();
    let mut pools: BTreeMap<u32, (Vec<u32>, u64, u64, f64)> = BTreeMap::new();
    let mut judged = 0;
    for (&(subreddit, name), &(count, hits, expected)) in &scopes {
        if count < GATE_COMPARISONS {
            let pool = pools.entry(name).or_default();
            pool.0.push(subreddit);
            pool.1 += count;
            pool.2 += hits;
            pool.3 += expected;
            continue;
        }
        judged += 1;
        if !agrees(count, hits, expected) {
            found.insert((subreddit, name));
        }
    }
    let judged_blocked = found.len();
    let (mut passed, mut passed_scopes, mut blocked_scopes) = (0, 0, 0);
    for (&name, (subreddits, count, hits, expected)) in &pools {
        let open = agrees(*count, *hits, *expected);
        crate::log(&format!(
            "flair pool attribute={} scopes={} comparisons={count} hits={hits} skill={:.3} {}",
            vocabulary.attribute(name),
            subreddits.len(),
            skill(*count, *hits, *expected),
            if open { "passed" } else { "blocked" }
        ));
        if open {
            passed += 1;
            passed_scopes += subreddits.len();
        } else {
            blocked_scopes += subreddits.len();
            found.extend(subreddits.iter().map(|&subreddit| (subreddit, name)));
        }
    }
    crate::log(&format!(
        "flair gate scopes={} judged={judged} judged_blocked={judged_blocked} pools={} pools_passed={passed} pooled_scopes_passed={passed_scopes} pooled_scopes_blocked={blocked_scopes} blocked={}",
        scopes.len(),
        pools.len(),
        found.len()
    ));
    found
}

impl Decision {
    pub fn encode(&self, vocabulary: &Vocabulary, author: &str, out: &mut Vec<u8>) {
        put_string(out, author);
        put_string(out, vocabulary.names.get(self.name));
        put_string(out, vocabulary.values.get(self.best));
    }
}
