use crate::database::{put_string, text, Database};
use crate::rules::{blocked, consolidate, first, Attribute, Evidence, Step, Tallies, Vocabulary, TEXT};
use crate::{log, parallel, timed};
use crossbeam_channel::{bounded, Receiver, Sender};
use std::collections::HashMap;
use std::time::Instant;

const PARTS: u64 = 256;
const INSERT_BYTES: usize = 64 << 20;
const BATCH_ROWS: usize = 1 << 16;
const BUCKET_SHIFT: u32 = 104;
const STREAMS: usize = 8;
const EXCLUDED: &str = "'', '[deleted]', '[removed]', 'AutoModerator'";
const KEY: &str = "reinterpretAsUInt128(substring(text_sha256, 1, 16))";
const OUTPUTS: &str = "CREATE TABLE author_attributes_next (attribute String, kind String) ENGINE = MergeTree ORDER BY attribute";
const CLAIMS: &str = "CREATE TABLE author_claims_next (author String, attribute LowCardinality(String), value String) ENGINE = MergeTree ORDER BY (author, attribute)";
const SCHEMA: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../claim_extraction/schema.json");

struct TextClaims {
    keys: Vec<u128>,
    starts: Vec<u32>,
    claims: Vec<u32>,
    buckets: Vec<u32>,
}

#[derive(Default)]
struct Part {
    keys: Vec<u128>,
    starts: Vec<u32>,
    claims: Vec<u32>,
    pairs: Vec<(Vec<u8>, Vec<u8>)>,
}

fn load_part(database: &Database, part: usize, parts: usize) -> Part {
    let edge = |index: usize| format!("unhex('{:02x}{}')", index * 256 / parts, "00".repeat(31));
    let filter = if part + 1 < parts { format!("text_sha256 >= {} AND text_sha256 < {}", edge(part), edge(part + 1)) } else { format!("text_sha256 >= {}", edge(part)) };
    let mut rows = database.rows(&format!("SELECT text_sha256, attribute, value FROM text_claims WHERE {filter} ORDER BY text_sha256 FORMAT RowBinary"));
    let (mut found, mut ids, mut key, mut previous) = (Part::default(), HashMap::new(), Vec::new(), [0u8; 32]);
    while !rows.done() {
        let sha: [u8; 32] = rows.fixed();
        if found.keys.is_empty() || sha != previous {
            assert!(found.keys.is_empty() || sha > previous, "text claims are not ordered by digest");
            let digest = u128::from_be_bytes(sha[..16].try_into().unwrap());
            assert!(found.keys.last().map_or(true, |&last| digest > last), "digest prefix collision");
            found.keys.push(digest);
            found.starts.push(found.claims.len() as u32);
            previous = sha;
        }
        key.clear();
        key.extend_from_slice(rows.bytes());
        let split = key.len();
        key.extend_from_slice(rows.bytes());
        let next = found.pairs.len() as u32;
        let id = *ids.entry(key.clone()).or_insert_with(|| {
            found.pairs.push((key[..split].to_vec(), key[split..].to_vec()));
            next
        });
        found.claims.push(id);
    }
    found
}

impl TextClaims {
    fn load(database: &Database, vocabulary: &mut Vocabulary, threads: usize) -> TextClaims {
        let found: Vec<Part> = std::thread::scope(|scope| {
            let handles: Vec<_> = (0..threads).map(|part| scope.spawn(move || load_part(database, part, threads))).collect();
            handles.into_iter().map(|handle| handle.join().unwrap()).collect()
        });
        let (mut keys, mut starts, mut claims) = (Vec::new(), Vec::new(), Vec::new());
        for part in found {
            let remap: Vec<u32> = part.pairs.iter().map(|(attribute, value)| vocabulary.claim(attribute, value)).collect();
            assert!(keys.last().zip(part.keys.first()).map_or(true, |(last, first)| last < first), "text claim parts overlap");
            let offset = claims.len() as u32;
            keys.extend_from_slice(&part.keys);
            starts.extend(part.starts.iter().map(|start| start + offset));
            claims.extend(part.claims.iter().map(|&claim| remap[claim as usize]));
            assert!(claims.len() < u32::MAX as usize, "too many text claims for u32 offsets");
        }
        starts.push(claims.len() as u32);
        let mut buckets = Vec::with_capacity((1 << (128 - BUCKET_SHIFT)) + 1);
        let mut index = 0usize;
        for bucket in 0..=(1u128 << (128 - BUCKET_SHIFT)) {
            while index < keys.len() && keys[index] >> BUCKET_SHIFT < bucket {
                index += 1;
            }
            buckets.push(index as u32);
        }
        log(&format!("text claims texts={} claims={} distinct={}", keys.len(), claims.len(), vocabulary.claim_count()));
        TextClaims { keys, starts, claims, buckets }
    }

    fn find(&self, key: u128) -> usize {
        let bucket = (key >> BUCKET_SHIFT) as usize;
        let (low, high) = (self.buckets[bucket] as usize, self.buckets[bucket + 1] as usize);
        low + self.keys[low..high].iter().position(|&found| found == key).expect("claimed record digest missing from text claims")
    }

    fn claims(&self, index: usize) -> &[u32] {
        &self.claims[self.starts[index] as usize..self.starts[index + 1] as usize]
    }
}

struct FlairClaims {
    ids: HashMap<Vec<u8>, u32>,
    pairs: Vec<(u32, Vec<u32>)>,
}

impl FlairClaims {
    fn load(database: &Database, vocabulary: &mut Vocabulary) -> FlairClaims {
        let mut rows = database.rows("SELECT subreddit, flair, attribute, value FROM flair_claims FORMAT RowBinary");
        let (mut ids, mut pairs) = (HashMap::new(), Vec::<(u32, Vec<u32>)>::new());
        let (mut key, mut attribute) = (Vec::new(), Vec::new());
        while !rows.done() {
            let subreddit = text(rows.bytes());
            key.clear();
            key.extend_from_slice(subreddit.as_bytes());
            key.push(0);
            key.extend_from_slice(rows.bytes());
            let id = *ids.entry(key.clone()).or_insert_with(|| {
                pairs.push((vocabulary.subreddits.id(&subreddit), Vec::new()));
                pairs.len() as u32 - 1
            });
            attribute.clear();
            attribute.extend_from_slice(rows.bytes());
            let claim = vocabulary.claim(&attribute, rows.bytes());
            pairs[id as usize].1.push(claim);
        }
        log(&format!("flair claims flairs={} subreddits={}", pairs.len(), vocabulary.subreddits.len()));
        FlairClaims { ids, pairs }
    }
}

#[derive(Default)]
struct Batch {
    authors: Vec<(String, u32, u32)>,
    texts: Vec<(u128, u32)>,
    flairs: Vec<(u32, u32)>,
}

#[derive(Default)]
struct Done {
    rows: Vec<u8>,
    authors: u64,
    decided: u64,
    tied: Vec<u32>,
    tallies: Tallies,
    deferred: Vec<(String, Evidence)>,
}

fn count_tied(counts: &mut HashMap<u32, u64>, tied: Vec<u32>) {
    for name in tied {
        *counts.entry(name).or_default() += 1;
    }
}

fn bounds() -> HashMap<String, (f64, f64)> {
    let text = std::fs::read_to_string(SCHEMA).unwrap_or_else(|error| panic!("cannot read {SCHEMA}: {error}"));
    let schema: serde_json::Value = serde_json::from_str(&text).unwrap_or_else(|error| panic!("{SCHEMA} does not parse: {error}"));
    let attributes = schema["attributes"].as_array().unwrap_or_else(|| panic!("{SCHEMA} has no attributes list"));
    let found: HashMap<String, (f64, f64)> = attributes.iter().filter_map(|attribute| Some((attribute["name"].as_str()?.to_string(), (attribute["low"].as_f64()?, attribute["high"].as_f64()?)))).collect();
    log(&format!("schema ranges={}", found.len()));
    found
}

fn attributes(database: &Database) -> Vec<Attribute> {
    let ranges = timed("schema ranges", bounds);
    let mut rows = database.rows("SELECT attribute, kind, anchor, precision, unit FROM claim_attributes ORDER BY attribute FORMAT RowBinary");
    let mut found = Vec::new();
    while !rows.done() {
        let (name, kind, anchor) = (text(rows.bytes()), text(rows.bytes()), text(rows.bytes()));
        let precision = f64::from_le_bytes(rows.fixed());
        let range = ranges.get(&name).copied();
        found.push(Attribute { name, kind, anchor, precision, unit: text(rows.bytes()), range });
    }
    assert!(!found.is_empty(), "claim_attributes is empty; claim extraction publishes it");
    log(&format!("claim attributes={}", found.len()));
    found
}

fn publish(database: &Database, attributes: &[Attribute]) {
    database.command("DROP TABLE IF EXISTS author_attributes_next");
    database.command(OUTPUTS);
    let mut out = Vec::new();
    let mut published = 0;
    for attribute in attributes.iter().filter(|attribute| attribute.kind != "marker" && attribute.anchor.is_empty()) {
        put_string(&mut out, &attribute.name);
        put_string(&mut out, &attribute.kind);
        published += 1;
    }
    database.insert("author_attributes_next (attribute, kind)", &out);
    database.command("CREATE TABLE IF NOT EXISTS author_attributes AS author_attributes_next");
    database.command("EXCHANGE TABLES author_attributes_next AND author_attributes");
    database.command("DROP TABLE author_attributes_next");
    log(&format!("author attributes={published}"));
}

fn quoted(text: &str) -> String {
    format!("'{}'", text.replace('\\', "\\\\").replace('\'', "\\'"))
}

fn ranges(database: &Database) -> Vec<String> {
    let mut rows = database.rows(&format!("SELECT DISTINCT author FROM records WHERE cityHash64(author) % 1000 = 0 AND author NOT IN ({EXCLUDED}) ORDER BY author FORMAT RowBinary"));
    let mut sample = Vec::new();
    while !rows.done() {
        sample.push(text(rows.bytes()));
    }
    let mut edges: Vec<String> = (1..STREAMS).filter_map(|part| sample.get(sample.len() * part / STREAMS).map(|edge| quoted(edge))).collect();
    edges.dedup();
    let lows = std::iter::once(None).chain(edges.iter().map(Some));
    let highs = edges.iter().map(Some).chain(std::iter::once(None));
    lows.zip(highs)
        .map(|bounds| match bounds {
            (None, None) => String::from("1"),
            (Some(low), None) => format!("author >= {low}"),
            (None, Some(high)) => format!("author < {high}"),
            (Some(low), Some(high)) => format!("author >= {low} AND author < {high}"),
        })
        .collect()
}

fn records_query(range: &str) -> String {
    format!(
        "SELECT author, toUInt32(created_utc), {KEY} AS key, key IN claimed_keys AS claimed, \
         (subreddit, ifNull(author_flair_text, '')) IN (SELECT subreddit, flair FROM flair_claims) AS flaired, \
         if(flaired, subreddit, '') AS flair_subreddit, if(flaired, ifNull(author_flair_text, ''), '') AS flair \
         FROM records WHERE {range} AND author NOT IN ({EXCLUDED}) AND (claimed OR flaired) ORDER BY author FORMAT RowBinary"
    )
}

fn close(batch: &mut Batch, author: &[u8]) {
    batch.authors.push((text(author), batch.texts.len() as u32, batch.flairs.len() as u32));
}

fn produce(database: &Database, flairs: &FlairClaims, range: &str, tasks: Sender<Batch>) {
    let started = Instant::now();
    let mut rows = database.rows(&records_query(range));
    let (mut current, mut key) = (Vec::new(), Vec::new());
    let mut batch = Batch::default();
    let mut count = 0usize;
    while !rows.done() {
        let author = rows.bytes();
        if author != current.as_slice() {
            if count > 0 {
                close(&mut batch, &current);
                if batch.texts.len() + batch.flairs.len() >= BATCH_ROWS {
                    tasks.send(std::mem::take(&mut batch)).unwrap();
                }
            }
            current.clear();
            current.extend_from_slice(author);
        }
        count += 1;
        let time = u32::from_le_bytes(rows.fixed());
        let sha: [u8; 16] = rows.fixed();
        let [claimed, flaired]: [u8; 2] = rows.fixed();
        key.clear();
        key.extend_from_slice(rows.bytes());
        key.push(0);
        key.extend_from_slice(rows.bytes());
        if claimed == 1 {
            batch.texts.push((u128::from_be_bytes(sha), time));
        }
        if flaired == 1 {
            batch.flairs.push((*flairs.ids.get(&key).expect("flaired record missing from flair claims"), time));
        }
    }
    if count > 0 {
        close(&mut batch, &current);
        tasks.send(batch).unwrap();
    }
    let seconds = started.elapsed().as_secs_f64();
    log(&format!("records streamed range={range:?} rows={count} seconds={seconds:.1} rate={:.0}", count as f64 / seconds));
}

fn newest<K: Ord + Copy>(found: &mut [(K, u32)]) -> impl Iterator<Item = (K, u32)> + '_ {
    found.sort_unstable();
    found.chunk_by(|left, right| left.0 == right.0).map(|run| run[run.len() - 1])
}

fn evidence(vocabulary: &Vocabulary, texts: &TextClaims, flairs: &FlairClaims, shas: &mut [(u128, u32)], pairs: &mut [(u32, u32)]) -> Evidence {
    let mut evidence = Evidence::default();
    for (sha, time) in newest(shas) {
        evidence.add(vocabulary, TEXT, time, texts.claims(texts.find(sha)));
    }
    for (pair, time) in newest(pairs) {
        let (subreddit, claims) = &flairs.pairs[pair as usize];
        evidence.add(vocabulary, *subreddit, time, claims);
    }
    evidence.finish();
    evidence
}

fn work(vocabulary: &Vocabulary, texts: &TextClaims, flairs: &FlairClaims, mut batch: Batch) -> Done {
    let mut done = Done::default();
    let (mut text_start, mut flair_start) = (0usize, 0usize);
    for (author, text_end, flair_end) in std::mem::take(&mut batch.authors) {
        let (text_end, flair_end) = (text_end as usize, flair_end as usize);
        let found = evidence(vocabulary, texts, flairs, &mut batch.texts[text_start..text_end], &mut batch.flairs[flair_start..flair_end]);
        (text_start, flair_start) = (text_end, flair_end);
        done.authors += 1;
        match first(vocabulary, found, &mut done.tallies) {
            Step::Decided(decisions, tied) => {
                for decision in &decisions {
                    decision.encode(vocabulary, &author, &mut done.rows);
                }
                done.decided += decisions.len() as u64;
                done.tied.extend(tied);
            }
            Step::Deferred(found) => done.deferred.push((author, found)),
        }
    }
    done
}

fn write(database: &Database, outbox: Receiver<Vec<u8>>) {
    let (started, mut waited, mut inserts, mut bytes) = (Instant::now(), 0f64, 0u64, 0usize);
    let mut pending = Vec::with_capacity(INSERT_BYTES + (1 << 20));
    let mut flush = |pending: &mut Vec<u8>| {
        let insert = Instant::now();
        database.insert("author_claims_next (author, attribute, value)", pending);
        waited += insert.elapsed().as_secs_f64();
        inserts += 1;
        bytes += pending.len();
        pending.clear();
    };
    for rows in outbox {
        pending.extend_from_slice(&rows);
        if pending.len() >= INSERT_BYTES {
            flush(&mut pending);
        }
    }
    if !pending.is_empty() {
        flush(&mut pending);
    }
    log(&format!("written inserts={inserts} bytes={bytes} insert_seconds={waited:.1} seconds={:.1}", started.elapsed().as_secs_f64()));
}

pub fn run(database: &Database, threads: usize) {
    timed("consolidate", || {
        let finished: u64 = database.command("SELECT count() FROM extracted_parts").trim().parse().unwrap();
        assert!(finished >= PARTS, "claim extraction has not finished every part: {finished}/{PARTS}");
        let described = timed("claim attributes", || attributes(database));
        let mut vocabulary = Vocabulary::new(&described);
        database.command("DROP TABLE IF EXISTS claimed_keys");
        database.command("CREATE TABLE claimed_keys (key UInt128) ENGINE = Set SETTINGS persistent = 0");
        let (texts, filters) = std::thread::scope(|scope| {
            let keys = scope.spawn(|| timed("claimed keys", || database.command(&format!("INSERT INTO claimed_keys SELECT {KEY} FROM text_claims"))));
            let filters = scope.spawn(|| timed("author ranges", || ranges(database)));
            let texts = timed("load text claims", || TextClaims::load(database, &mut vocabulary, threads));
            keys.join().unwrap();
            (texts, filters.join().unwrap())
        });
        let flairs = timed("load flair claims", || FlairClaims::load(database, &mut vocabulary));
        let vocabulary = vocabulary;
        database.command("DROP TABLE IF EXISTS author_claims_next");
        database.command(CLAIMS);
        let (rows, outbox) = bounded::<Vec<u8>>(threads * 4);
        let (mut tallies, mut deferred, mut authors, mut decided, mut tied) = (Tallies::default(), Vec::new(), 0u64, 0u64, HashMap::new());
        std::thread::scope(|scope| {
            scope.spawn(|| write(database, outbox));
            timed("first pass", || {
                let streams = |tasks: Sender<Batch>| {
                    std::thread::scope(|inner| {
                        for range in &filters {
                            let (tasks, flairs) = (tasks.clone(), &flairs);
                            inner.spawn(move || produce(database, flairs, range, tasks));
                        }
                    });
                };
                parallel(threads, streams, |batch| work(&vocabulary, &texts, &flairs, batch), |done: Done| {
                    rows.send(done.rows).unwrap();
                    tallies.merge(done.tallies);
                    deferred.extend(done.deferred);
                    authors += done.authors;
                    decided += done.decided;
                    count_tied(&mut tied, done.tied);
                });
            });
            log(&format!("first pass authors={authors} decided={decided} deferred={}", deferred.len()));
            let gated = timed("flair gate", || blocked(&vocabulary, &tallies));
            timed("second pass", || {
                let chunk = deferred.len().div_ceil(threads * 8).max(1);
                parallel(
                    threads,
                    |tasks| {
                        let mut deferred = deferred.into_iter().peekable();
                        while deferred.peek().is_some() {
                            tasks.send(deferred.by_ref().take(chunk).collect::<Vec<_>>()).unwrap();
                        }
                    },
                    |items: Vec<(String, Evidence)>| {
                        let (mut out, mut count, mut names) = (Vec::new(), 0u64, Vec::new());
                        for (author, found) in &items {
                            let (decisions, tied) = consolidate(&vocabulary, found, &gated);
                            for decision in decisions {
                                decision.encode(&vocabulary, author, &mut out);
                                count += 1;
                            }
                            names.extend(tied);
                        }
                        (out, count, names)
                    },
                    |(out, count, names): (Vec<u8>, u64, Vec<u32>)| {
                        rows.send(out).unwrap();
                        decided += count;
                        count_tied(&mut tied, names);
                    },
                );
            });
            drop(rows);
        });
        database.command("CREATE TABLE IF NOT EXISTS author_claims AS author_claims_next");
        database.command("EXCHANGE TABLES author_claims_next AND author_claims");
        database.command("DROP TABLE author_claims_next");
        database.command("DROP TABLE claimed_keys");
        timed("author attributes", || publish(database, &described));
        let mut tied: Vec<(&str, u64)> = tied.into_iter().map(|(name, count)| (vocabulary.attribute(name), count)).collect();
        tied.sort_unstable();
        for (attribute, count) in &tied {
            log(&format!("no plurality attribute={attribute} authors={count}"));
        }
        log(&format!("no plurality authors={}", tied.iter().map(|entry| entry.1).sum::<u64>()));
        log(&format!("author claims authors={authors} rows={decided}"));
    });
}
