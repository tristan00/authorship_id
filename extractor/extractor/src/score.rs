use crate::{init, positioned, read_lines};
use claimcore::contract::SCHEMA;
use claimcore::{log, timed};
use serde::Deserialize;
use serde_json::value::RawValue;
use serde_json::{json, Value};
use std::collections::{BTreeMap, HashMap};
use std::io::{BufWriter, Write};

const EXAMPLES: usize = 25;
const SNIPPET: usize = 400;
const OPEN: &str = "*";

#[derive(Deserialize)]
struct Text {
    id: Box<RawValue>,
    text: String,
}

#[derive(Deserialize)]
struct Answer {
    id: Box<RawValue>,
    answer: Option<String>,
    error: Option<Value>,
}

#[derive(Default)]
struct Tally {
    hits: usize,
    wrong: usize,
    missed: usize,
    votes: BTreeMap<usize, usize>,
    values: BTreeMap<String, [usize; 3]>,
    false_positives: Vec<Value>,
    false_negatives: Vec<Value>,
}

fn answers(directory: &str) -> HashMap<String, String> {
    let mut paths: Vec<_> = std::fs::read_dir(directory)
        .unwrap_or_else(|error| panic!("cannot list {directory}: {error}"))
        .map(|entry| entry.unwrap().path())
        .filter(|path| path.extension().is_some_and(|extension| extension == "jsonl") && path.file_stem().is_some_and(|stem| stem.to_string_lossy().bytes().all(|byte| byte.is_ascii_digit())))
        .collect();
    paths.sort();
    let mut found = HashMap::new();
    for path in paths {
        for line in read_lines(&path.to_string_lossy()) {
            let row: Answer = serde_json::from_str(&line).unwrap_or_else(|error| panic!("bad answer line in {}: {error}", path.display()));
            if let (None, Some(answer)) = (row.error, row.answer) {
                found.insert(row.id.get().to_string(), answer);
            }
        }
    }
    found
}

fn extracted(texts: &[&Text], prompt: &str, threads: usize) -> (Vec<Vec<(String, String)>>, BTreeMap<String, usize>) {
    let mut raw: Vec<Vec<(String, String)>> = vec![Vec::new(); texts.len()];
    let chunk = texts.len().div_ceil(threads.max(1)).max(1);
    std::thread::scope(|scope| {
        for (slots, part) in raw.chunks_mut(chunk).zip(texts.chunks(chunk)) {
            scope.spawn(move || {
                for (slot, text) in slots.iter_mut().zip(part) {
                    *slot = positioned(&text.text).into_iter().map(|(attribute, value, _)| (attribute, value)).collect();
                }
            });
        }
    });
    let mut invalid = BTreeMap::new();
    let claims = raw
        .into_iter()
        .map(|found| {
            found
                .into_iter()
                .filter_map(|(attribute, value)| match SCHEMA.attribute(&attribute) {
                    None => {
                        *invalid.entry(format!("unknown attribute {attribute}")).or_insert(0) += 1;
                        None
                    }
                    Some(known) if known.prompt.as_deref() != Some(prompt) => None,
                    Some(known) => match known.normal(&value) {
                        Some(normal) => Some((attribute, normal)),
                        None => {
                            *invalid.entry(format!("invalid value {attribute}={value}")).or_insert(0) += 1;
                            None
                        }
                    },
                })
                .collect()
        })
        .collect();
    (claims, invalid)
}

type Shown = BTreeMap<String, Vec<String>>;

fn open(name: &str) -> bool {
    SCHEMA.attribute(name).is_some_and(|attribute| attribute.values.is_empty() && attribute.kind != "number")
}

fn grouped(claims: &[(String, String)], shown: &mut Shown) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    for (attribute, value) in claims {
        let claim = if open(attribute) {
            let values = shown.entry(attribute.clone()).or_default();
            if !values.contains(value) {
                values.push(value.clone());
            }
            (attribute.clone(), OPEN.to_string())
        } else {
            (attribute.clone(), value.clone())
        };
        if !out.contains(&claim) {
            out.push(claim);
        }
    }
    out
}

fn displayed(shown: &Shown, attribute: &str, value: &str) -> String {
    if value == OPEN { shown[attribute].join(" | ") } else { value.to_string() }
}

fn example(text: &Text, value: &str, votes: usize) -> Value {
    json!({"id": text.id.get().trim_matches('"'), "value": value, "votes": votes, "text": text.text.chars().take(SNIPPET).collect::<String>()})
}

pub fn score(prompt: &str, texts_path: &str, report_path: &str, agree: usize, threads: usize, directories: &[&str], contested: Option<&str>) {
    timed("score", || {
        let texts: Vec<Text> = read_lines(texts_path).iter().map(|line| serde_json::from_str(line).unwrap_or_else(|error| panic!("bad text line: {error}"))).collect();
        let models: Vec<HashMap<String, String>> = directories.iter().map(|directory| timed("answers", || answers(directory))).collect();
        let kept: Vec<&Text> = texts.iter().filter(|text| models.iter().all(|model| model.contains_key(text.id.get()))).collect();
        log(&format!("score texts={} answered_by_all={} models={} agree={agree}", texts.len(), kept.len(), models.len()));
        let mut rejected: Vec<BTreeMap<&str, usize>> = vec![BTreeMap::new(); models.len()];
        let mut claimed = vec![0usize; models.len()];
        let mut panel = vec![[0usize; 3]; models.len()];
        let rest = models.len().saturating_sub(1).div_ceil(2).max(1);
        let labels: Vec<(BTreeMap<(String, String), usize>, Shown)> = kept
            .iter()
            .map(|text| {
                let mut votes = BTreeMap::new();
                let mut shown = Shown::new();
                let mut each = Vec::with_capacity(models.len());
                for (index, model) in models.iter().enumerate() {
                    let parsed = SCHEMA.parse_answer(prompt, &text.text, &model[text.id.get()]);
                    parsed.rejected.iter().for_each(|reason| *rejected[index].entry(reason).or_insert(0) += 1);
                    let claims = grouped(&parsed.claims, &mut shown);
                    claimed[index] += claims.len();
                    claims.iter().for_each(|claim| *votes.entry(claim.clone()).or_insert(0) += 1);
                    each.push(claims);
                }
                for (index, own) in each.iter().enumerate() {
                    for (claim, &count) in &votes {
                        let mine = own.contains(claim);
                        let others = count - mine as usize;
                        panel[index][0] += (mine && others >= rest) as usize;
                        panel[index][1] += mine as usize;
                        panel[index][2] += (others >= rest) as usize;
                    }
                }
                (votes, shown)
            })
            .collect();
        for (directory, [agreed, own, majority]) in directories.iter().zip(&panel) {
            log(&format!("panel {directory} claims={own} rest_majority={majority} precision={:.3} recall={:.3}", *agreed as f64 / (*own).max(1) as f64, *agreed as f64 / (*majority).max(1) as f64));
        }
        if let Some(path) = contested {
            timed("contested", || {
                let mut out = BufWriter::new(std::fs::File::create(path).unwrap_or_else(|error| panic!("cannot write {path}: {error}")));
                let mut count = 0usize;
                for (text, (votes, _)) in kept.iter().zip(&labels) {
                    if votes.values().any(|&count| count < models.len()) {
                        writeln!(out, "{}", json!({"id": serde_json::from_str::<Value>(text.id.get()).unwrap(), "text": text.text})).unwrap();
                        count += 1;
                    }
                }
                out.flush().unwrap();
                log(&format!("contested texts={count} of {}", kept.len()));
            });
        }
        timed("init", init);
        let (rules, invalid) = timed("rules", || extracted(&kept, prompt, threads));
        let rules: Vec<(Vec<(String, String)>, Shown)> = rules
            .iter()
            .map(|found| {
                let mut shown = Shown::new();
                (grouped(found, &mut shown), shown)
            })
            .collect();
        let mut tallies: BTreeMap<String, Tally> = BTreeMap::new();
        for ((text, (votes, said)), (found, emitted)) in kept.iter().zip(&labels).zip(&rules) {
            for ((attribute, value), &count) in votes {
                let tally = tallies.entry(attribute.clone()).or_default();
                *tally.votes.entry(count).or_insert(0) += 1;
                if count >= agree && !found.contains(&(attribute.clone(), value.clone())) {
                    tally.missed += 1;
                    tally.values.entry(value.clone()).or_default()[2] += 1;
                    if tally.false_negatives.len() < EXAMPLES {
                        tally.false_negatives.push(example(text, &displayed(said, attribute, value), count));
                    }
                }
            }
            for (attribute, value) in found {
                let count = votes.get(&(attribute.clone(), value.clone())).copied().unwrap_or(0);
                let tally = tallies.entry(attribute.clone()).or_default();
                if count >= agree {
                    tally.hits += 1;
                    tally.values.entry(value.clone()).or_default()[0] += 1;
                } else {
                    tally.wrong += 1;
                    tally.values.entry(value.clone()).or_default()[1] += 1;
                    if tally.false_positives.len() < EXAMPLES {
                        tally.false_positives.push(example(text, &displayed(emitted, attribute, value), count));
                    }
                }
            }
        }
        let closed = |name: &str| SCHEMA.attribute(name).is_some_and(|attribute| !attribute.values.is_empty());
        let attributes: BTreeMap<&String, Value> = tallies
            .iter()
            .map(|(name, tally)| {
                let precision = tally.hits as f64 / (tally.hits + tally.wrong).max(1) as f64;
                let recall = tally.hits as f64 / (tally.hits + tally.missed).max(1) as f64;
                log(&format!("score {name} labels={} hits={} wrong={} missed={} precision={precision:.3} recall={recall:.3}", tally.hits + tally.missed, tally.hits, tally.wrong, tally.missed));
                let values: BTreeMap<&String, Value> = if closed(name) { tally.values.iter().map(|(value, [hits, wrong, missed])| (value, json!({"hits": hits, "wrong": wrong, "missed": missed}))).collect() } else { BTreeMap::new() };
                (name, json!({"labels": tally.hits + tally.missed, "hits": tally.hits, "wrong": tally.wrong, "missed": tally.missed, "precision": precision, "recall": recall,
                              "votes": tally.votes, "values": values, "false_positives": tally.false_positives, "false_negatives": tally.false_negatives}))
            })
            .collect();
        let report = json!({
            "prompt": prompt, "texts": kept.len(), "agree": agree,
            "models": directories.iter().zip(&rejected).zip(&claimed).zip(&panel).map(|(((directory, rejected), claimed), [agreed, own, majority])| json!({
                "answers": directory, "claims": claimed, "rejected": rejected, "rest_majority": majority,
                "precision_vs_rest": *agreed as f64 / (*own).max(1) as f64, "recall_vs_rest": *agreed as f64 / (*majority).max(1) as f64})).collect::<Vec<_>>(),
            "invalid_rule_claims": invalid, "attributes": attributes,
        });
        std::fs::write(report_path, serde_json::to_string_pretty(&report).unwrap()).unwrap_or_else(|error| panic!("cannot write {report_path}: {error}"));
    });
}
