use crate::rules::{blocked, consolidate, first, Evidence, Step, Tallies, Vocabulary, NEED, TEXT};
use crate::schema::FLAIR;
use crate::timed;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufWriter, Write};

fn evidence(vocabulary: &mut Vocabulary, rows: &[Value]) -> Evidence {
    let mut docs: Vec<(u32, u32, Vec<u32>)> = Vec::new();
    let mut index: HashMap<&str, usize> = HashMap::new();
    for row in rows {
        let field = |position: usize| row[position].as_str().unwrap_or_else(|| panic!("row field {position} is not a string: {row}"));
        let (attribute, value, digest, subreddit, source) = (field(0), field(1), field(2), field(3), field(4));
        let time = row[5].as_u64().unwrap_or_else(|| panic!("row field 5 is not a timestamp: {row}")) as u32;
        let claim = vocabulary.claim(attribute.as_bytes(), value.as_bytes());
        let doc = *index.entry(digest).or_insert_with(|| {
            docs.push((if source == FLAIR { vocabulary.subreddits.id(subreddit) } else { TEXT }, 0, Vec::new()));
            docs.len() - 1
        });
        docs[doc].1 = docs[doc].1.max(time);
        docs[doc].2.push(claim);
    }
    let mut evidence = Evidence::default();
    for (subreddit, time, claims) in &docs {
        evidence.add(vocabulary, *subreddit, *time, claims);
    }
    evidence.finish();
    evidence
}

pub fn decide(input: &str, output: &str) {
    timed("decide file", || {
        let content = std::fs::read_to_string(input).unwrap_or_else(|error| panic!("cannot read {input}: {error}"));
        let mut vocabulary = Vocabulary::new();
        let mut tallies = Tallies::default();
        let mut results: Vec<(String, Option<Vec<Value>>)> = Vec::new();
        let mut deferred: Vec<(usize, Evidence)> = Vec::new();
        for line in content.lines().filter(|line| !line.trim().is_empty()) {
            let item: Value = serde_json::from_str(line).unwrap_or_else(|error| panic!("bad input line: {error}"));
            let author = item["author"].as_str().expect("author").to_string();
            let found = evidence(&mut vocabulary, item["rows"].as_array().expect("rows"));
            match first(&vocabulary, found, NEED, &mut tallies) {
                Step::Decided(decisions) => results.push((author, Some(decisions.iter().map(|decision| encoded(&vocabulary, decision)).collect()))),
                Step::Deferred(found) => {
                    deferred.push((results.len(), found));
                    results.push((author, None));
                }
            }
        }
        let gated = blocked(&vocabulary, &tallies);
        for (position, found) in deferred {
            results[position].1 = Some(consolidate(&vocabulary, &found, NEED, &gated).iter().map(|decision| encoded(&vocabulary, decision)).collect());
        }
        let mut writer = BufWriter::new(std::fs::File::create(output).unwrap_or_else(|error| panic!("cannot create {output}: {error}")));
        for (author, claims) in results {
            writeln!(writer, "{}", json!({"author": author, "claims": claims.unwrap()})).unwrap();
        }
        writer.flush().unwrap();
    });
}

fn encoded(vocabulary: &Vocabulary, decision: &crate::rules::Decision) -> Value {
    json!([decision.attribute(vocabulary), decision.value(vocabulary), decision.support(), decision.share(), decision.candidates(vocabulary)])
}
