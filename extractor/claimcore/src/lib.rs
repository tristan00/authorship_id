pub mod common;
pub mod contract;
pub mod prefilter;
pub mod re;
pub mod schema;
pub mod text;

use std::cell::Cell;
use std::time::Instant;

pub use common::*;
pub use re::{Match, Re};
pub use text::*;

pub const DATA: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../claim_extraction");
pub const SINGLE: [&str; 2] = ["age", "gender"];

pub fn data_file(name: &str) -> String {
    std::fs::read_to_string(format!("{DATA}/{name}")).unwrap_or_else(|error| panic!("cannot read {name}: {error}"))
}

pub fn log(message: &str) {
    eprintln!("{} {message}", chrono_like());
}

fn chrono_like() -> String {
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
    format!("{now:.3}")
}

pub fn timed<T>(name: &str, work: impl FnOnce() -> T) -> T {
    let started = Instant::now();
    log(&format!("{name} start"));
    let result = work();
    log(&format!("{name} done seconds={:.3}", started.elapsed().as_secs_f64()));
    result
}

#[derive(Default, Clone)]
pub struct Found {
    pub items: Vec<(String, String, usize)>,
}

impl Found {
    pub fn set(&mut self, attribute: &str, value: impl AsRef<str>, position: usize) {
        let value = value.as_ref();
        if !self.has(attribute, value) {
            self.items.push((attribute.to_string(), value.to_string(), position));
        }
    }

    pub fn get(&self, attribute: &str, value: &str) -> Option<usize> {
        self.items.iter().find(|(a, v, _)| a == attribute && v == value).map(|(_, _, p)| *p)
    }

    pub fn has(&self, attribute: &str, value: &str) -> bool {
        self.get(attribute, value).is_some()
    }

    pub fn any(&self, attribute: &str) -> bool {
        self.items.iter().any(|(a, _, _)| a == attribute)
    }

    pub fn values(&self, attribute: &str) -> Vec<String> {
        self.items.iter().filter(|(a, _, _)| a == attribute).map(|(_, v, _)| v.clone()).collect()
    }
}

thread_local! {
    static CURRENT: Cell<(usize, usize, usize)> = const { Cell::new((0, 0, 0)) };
}

pub fn set_current(text: &[char], lowered: &[char]) {
    CURRENT.with(|current| current.set((text.as_ptr() as usize, lowered.as_ptr() as usize, lowered.len())));
    SERIAL.with(|serial| serial.set(serial.get() + 1));
}

thread_local! {
    static SERIAL: Cell<u64> = const { Cell::new(0) };
}

pub fn serial() -> u64 {
    SERIAL.with(|serial| serial.get())
}

pub fn original<'a>(lowered: &'a [char]) -> Option<&'a [char]> {
    let (text, low, len) = CURRENT.with(|current| current.get());
    if low == lowered.as_ptr() as usize && len == lowered.len() && text != 0 {
        Some(unsafe { std::slice::from_raw_parts(text as *const char, len) })
    } else {
        None
    }
}

pub fn finish(found: Found) -> Vec<(String, String, usize)> {
    let mut order: Vec<usize> = (0..found.items.len()).collect();
    order.sort_by_key(|&i| found.items[i].2);
    let mut earliest: Vec<(&str, &str)> = Vec::new();
    for i in order {
        let (attribute, value, _) = &found.items[i];
        if SINGLE.contains(&attribute.as_str()) && !earliest.iter().any(|(a, _)| a == attribute) {
            earliest.push((attribute, value));
        }
    }
    let mut picks: Vec<(String, String, usize)> = Vec::new();
    for (attribute, value, position) in &found.items {
        if SINGLE.contains(&attribute.as_str()) && !earliest.iter().any(|(a, v)| a == attribute && v == value) {
            continue;
        }
        if !picks.iter().any(|(pa, pv, _)| pa == attribute && pv == value) {
            picks.push((attribute.clone(), value.clone(), *position));
        }
    }
    picks
}

pub fn run_possible(rules: &[&Rule], possible: &[bool], lowered: &[char], automatic: bool, bot_safe: &dyn Fn(&str) -> bool, found: &mut Found) {
    for (entry, &open) in rules.iter().zip(possible) {
        if !open || (automatic && !bot_safe(entry.attribute)) || !entry.open(lowered) {
            continue;
        }
        for found_match in entry.re.iter(lowered) {
            if let Some(stated) = (entry.value)(&found_match) {
                if !hedged(lowered, found_match.start(), found_match.end(), entry.hedge) {
                    found.set(entry.attribute, stated, found_match.start());
                }
            }
        }
    }
}
