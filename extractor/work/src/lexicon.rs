use crate::vocab::*;
use claimcore::*;
use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;

pub fn alnum(c: char) -> bool {
    c != '_' && is_word(c)
}

pub fn token_end(s: &[char], i: usize, end: usize) -> usize {
    let mut j = i;
    while j < end && alnum(s[j]) {
        j += 1;
    }
    while j + 1 < end && matches!(s[j], '\'' | '.' | '&' | '+') && alnum(s[j + 1]) {
        j += 1;
        while j < end && alnum(s[j]) {
            j += 1;
        }
    }
    j
}

pub fn tokens(s: &[char], start: usize, end: usize) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    let mut i = start;
    while i < end {
        if alnum(s[i]) {
            let j = token_end(s, i, end);
            out.push((i, j));
            i = j;
        } else {
            i += 1;
        }
    }
    out
}

pub fn phrase(text: &str) -> String {
    let lowered = lower(&chars(text));
    tokens(&lowered, 0, lowered.len()).iter().map(|&(a, b)| st(&lowered[a..b])).collect::<Vec<_>>().join(" ")
}

fn soc(code: &str) -> &'static str {
    for size in [7, 6, 4, 2] {
        if let Some(prefix) = code.get(..size) {
            if let Some((_, value)) = SOC.iter().find(|(key, _)| *key == prefix) {
                return value;
            }
        }
    }
    panic!("no soc for {code}")
}

fn onet() -> HashMap<String, &'static str> {
    let stop: HashSet<&str> = ONET_STOP.split(' ').collect();
    let mut votes: HashMap<String, Vec<(&'static str, usize)>> = HashMap::new();
    for line in data_file("onet_titles.tsv").lines() {
        let mut parts = line.split('\t');
        let (code, source, title) = (parts.next().unwrap(), parts.next().unwrap(), parts.next().unwrap());
        for name in title.split(['(', ')']) {
            let key = phrase(name);
            if !key.is_empty() && (key.contains(' ') || source == "R" && key.chars().count() > 4 && !stop.contains(key.as_str())) {
                let value = soc(code);
                let counts = votes.entry(key).or_default();
                match counts.iter_mut().find(|(v, _)| *v == value) {
                    Some(entry) => entry.1 += 1,
                    None => counts.push((value, 1)),
                }
            }
        }
    }
    let mut out = HashMap::new();
    for (key, counts) in votes {
        let top = counts.iter().map(|(_, n)| *n).max().unwrap();
        let winners: Vec<&(&str, usize)> = counts.iter().filter(|(_, n)| *n == top).collect();
        if winners.len() == 1 {
            out.insert(key, winners[0].0);
        }
    }
    out
}

pub static TITLES: LazyLock<HashMap<String, &'static str>> = LazyLock::new(|| {
    let mut jobs: HashMap<String, &'static str> = onet();
    for (value, words) in JOBS {
        for word in words.split('|') {
            jobs.insert(phrase(word), value);
        }
    }
    jobs
});

pub static FOREIGN_TITLES: LazyLock<HashMap<String, &'static str>> = LazyLock::new(|| {
    let mut out = HashMap::new();
    for (value, words) in FOREIGN {
        for word in words.split('|') {
            out.insert(phrase(word), *value);
        }
    }
    out
});

fn first_words<'a>(keys: impl Iterator<Item = &'a String>) -> HashSet<String> {
    keys.map(|key| key.split(' ').next().unwrap().to_string()).collect()
}

pub static TITLE_HEADS: LazyLock<HashSet<String>> = LazyLock::new(|| first_words(TITLES.keys()));
pub static FOREIGN_HEADS: LazyLock<HashSet<String>> = LazyLock::new(|| first_words(FOREIGN_TITLES.keys()));
pub static BLOCK: LazyLock<HashSet<&'static str>> = LazyLock::new(|| SKILL.split('|').chain(BLOCK_WORDS.split(' ')).collect());
pub static FOREIGN_BLOCKED: LazyLock<HashSet<&'static str>> = LazyLock::new(|| FOREIGN_BLOCK.split(' ').collect());
pub static HEAD_WORDS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| HEADS.split('|').collect());
static FORMER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*\(?\s*(?:retired|ret\.|former|ex)\b"));

fn run(s: &[char], start: usize) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    if start >= s.len() || !alnum(s[start]) {
        return out;
    }
    let mut end = token_end(s, start, s.len());
    out.push((start, end));
    while out.len() < 10 {
        let mut k = end;
        while k < s.len() && k - end < 3 && matches!(s[k], ' ' | '/' | '-') {
            k += 1;
        }
        if k == end || k >= s.len() || !alnum(s[k]) {
            break;
        }
        let next = token_end(s, k, s.len());
        out.push((k, next));
        end = next;
    }
    out
}

pub fn spot<V>(text: &[char], start: usize, skip: Option<usize>, block: &HashSet<&str>, titles: &HashMap<String, V>, heads: &HashSet<String>) -> Option<(String, usize)> {
    let spans = run(text, start);
    if spans.is_empty() {
        return None;
    }
    let names: Vec<String> = spans.iter().map(|&(a, b)| st(&text[a..b])).collect();
    let limit = match skip {
        None => names.len(),
        Some(skip) => (skip + 1).min(names.len()),
    };
    for offset in 0..limit {
        if block.contains(names[offset].as_str()) {
            return None;
        }
        if !heads.contains(&names[offset]) {
            continue;
        }
        for size in (1..=6.min(names.len() - offset)).rev() {
            let key = names[offset..offset + size].join(" ");
            if titles.contains_key(&key) {
                let after = offset + size;
                let end = spans[after - 1].1;
                if after < names.len() && HEAD_WORDS.contains(names[after].as_str()) || FORMER.at(text, end).is_some() {
                    return None;
                }
                return Some((key, end));
            }
        }
    }
    None
}

pub fn title(text: &[char], start: usize, skip: Option<usize>) -> Option<(&'static str, usize)> {
    let (key, end) = spot(text, start, skip, &BLOCK, &TITLES, &TITLE_HEADS)?;
    Some((TITLES.get_key_value(&key)?.0.as_str(), end))
}

pub fn job_kind(key: &str) -> &'static str {
    TITLES.get(key).or_else(|| FOREIGN_TITLES.get(key)).copied().unwrap_or_else(|| panic!("{key:?} is not a known job title"))
}

pub fn ended(text: &[char], start: usize, end: usize) -> Option<&'static str> {
    let mut names: Vec<String> = tokens(text, start, end).iter().map(|&(a, b)| st(&text[a..b])).collect();
    if let Some(last) = names.last_mut() {
        if !TITLES.contains_key(last.as_str()) && last.ends_with('s') {
            last.pop();
        }
    }
    for offset in names.len().saturating_sub(6)..names.len() {
        let key = names[offset..].join(" ");
        if let Some((found, _)) = TITLES.get_key_value(&key) {
            return if names[..offset].iter().any(|name| BLOCK.contains(name.as_str())) { None } else { Some(found.as_str()) };
        }
    }
    None
}
