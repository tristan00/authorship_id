use crate::database::{put_string, string, Database};
use claimcore::{log, timed, Origin, Re};
use crossbeam_channel::bounded;
use std::collections::{HashMap, HashSet};
use std::hash::{DefaultHasher, Hash, Hasher};
use std::io::{BufReader, Read};
use std::sync::LazyLock;
use std::time::Instant;

const PARTS: usize = 256;
const BATCH: usize = 1024;
const INSERT_BYTES: usize = 64 << 20;
const GATED: [&str; 2] = ["occupation", "location"];
const SHARE: f64 = 0.05;
const MOTHER_CLAIMS: [(&str, &str); 2] = [("gender", "trans man"), ("assigned_sex_at_birth", "afab")];
const FTM_FLAIRS: u64 = 5;
const FTM_SHARE: f64 = 0.5;
const TABLES: [&str; 4] = [
    "CREATE TABLE IF NOT EXISTS claim_attributes (attribute String, kind String, anchor String, precision Float64, unit String) ENGINE = MergeTree ORDER BY attribute",
    "CREATE TABLE IF NOT EXISTS text_claims (text_sha256 FixedString(32), attribute LowCardinality(String), value String, position UInt32) ENGINE = MergeTree ORDER BY (text_sha256, attribute)",
    "CREATE TABLE IF NOT EXISTS flair_claims (subreddit String, flair String, attribute LowCardinality(String), value String) ENGINE = MergeTree ORDER BY (subreddit, flair)",
    "CREATE TABLE IF NOT EXISTS extracted_parts (part UInt16, texts UInt64, claims UInt64, seconds Float32, build String, finished_at DateTime('UTC') DEFAULT now()) ENGINE = MergeTree ORDER BY part",
];

static MBTI: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![A-Za-z])([IE][NS][TF][JP])(?:-[AT])?(?![A-Za-z])"));

fn range(part: usize) -> String {
    let low = format!("text_sha256 >= unhex('{part:02x}{}')", "00".repeat(31));
    if part + 1 < PARTS {
        format!("{low} AND text_sha256 < unhex('{:02x}{}')", part + 1, "00".repeat(31))
    } else {
        low
    }
}

fn bodies(reader: &mut impl Read) -> Option<([u8; 32], String)> {
    let mut digest = [0u8; 32];
    let mut filled = 0;
    while filled < 32 {
        let read = reader.read(&mut digest[filled..]).unwrap();
        if read == 0 {
            assert!(filled == 0, "truncated digest");
            return None;
        }
        filled += read;
    }
    Some((digest, string(reader).expect("missing text after digest")))
}

fn parallel<T: Send, R: Send>(threads: usize, produce: impl FnOnce(crossbeam_channel::Sender<Vec<T>>) + Send, work: impl Fn(Vec<T>) -> R + Sync, mut consume: impl FnMut(R)) {
    let (tasks, inbox) = bounded::<Vec<T>>(threads * 4);
    let (results, outbox) = bounded::<R>(threads * 4);
    std::thread::scope(|scope| {
        scope.spawn(move || produce(tasks));
        for _ in 0..threads {
            let inbox = inbox.clone();
            let results = results.clone();
            let work = &work;
            scope.spawn(move || {
                for batch in inbox {
                    results.send(work(batch)).unwrap();
                }
            });
        }
        drop(results);
        for result in outbox {
            consume(result);
        }
    });
}

fn extract_part(database: &Database, part: usize, threads: usize, build: &str) -> (u64, u64) {
    let started = Instant::now();
    let filter = range(part);
    if database.command(&format!("SELECT count() FROM text_claims WHERE {filter}")).trim() != "0" {
        database.command(&format!("DELETE FROM text_claims WHERE {filter}"));
    }
    let mut stream = BufReader::with_capacity(1 << 20, database.stream(&format!("SELECT text_sha256, text FROM bodies WHERE {filter} FORMAT RowBinary")));
    let (mut texts, mut claims, mut pending) = (0u64, 0u64, Vec::with_capacity(INSERT_BYTES + (1 << 20)));
    parallel(
        threads,
        move |tasks| {
            let mut batch = Vec::with_capacity(BATCH);
            while let Some(row) = bodies(&mut stream) {
                batch.push(row);
                if batch.len() == BATCH {
                    tasks.send(std::mem::replace(&mut batch, Vec::with_capacity(BATCH))).unwrap();
                }
            }
            if !batch.is_empty() {
                tasks.send(batch).unwrap();
            }
        },
        |batch: Vec<([u8; 32], String)>| {
            let mut out = Vec::with_capacity(batch.len() * 16);
            let mut found = 0u64;
            for (digest, text) in &batch {
                for (attribute, value, position, origin) in crate::positioned(text) {
                    let Some(value) = crate::contracted(&attribute, &value, origin, || digest[..crate::ID_CHARS / 2].iter().map(|byte| format!("{byte:02x}")).collect()) else { continue };
                    out.extend_from_slice(digest);
                    put_string(&mut out, &attribute);
                    put_string(&mut out, &value);
                    out.extend_from_slice(&(position as u32).to_le_bytes());
                    found += 1;
                }
            }
            (batch.len() as u64, found, out)
        },
        |(count, found, out): (u64, u64, Vec<u8>)| {
            texts += count;
            claims += found;
            pending.extend_from_slice(&out);
            if pending.len() >= INSERT_BYTES {
                database.insert("text_claims (text_sha256, attribute, value, position)", &pending);
                pending.clear();
            }
        },
    );
    if !pending.is_empty() {
        database.insert("text_claims (text_sha256, attribute, value, position)", &pending);
    }
    let seconds = started.elapsed().as_secs_f64();
    let mut row = Vec::with_capacity(32);
    row.extend_from_slice(&(part as u16).to_le_bytes());
    row.extend_from_slice(&texts.to_le_bytes());
    row.extend_from_slice(&claims.to_le_bytes());
    row.extend_from_slice(&(seconds as f32).to_le_bytes());
    put_string(&mut row, build);
    database.insert("extracted_parts (part, texts, claims, seconds, build)", &row);
    log(&format!("part={part} texts={texts} claims={claims} invalid={} seconds={seconds:.0} rate={:.0}", crate::invalid(), texts as f64 / seconds.max(1e-9)));
    (texts, claims)
}

fn build() -> String {
    timed("build", || {
        let mut hasher = DefaultHasher::new();
        std::fs::read(std::env::current_exe().unwrap()).unwrap().hash(&mut hasher);
        let mut files: Vec<_> = std::fs::read_dir(claimcore::DATA).unwrap().map(|entry| entry.unwrap().path()).filter(|path| path.is_file()).collect();
        files.sort();
        for path in files {
            path.file_name().hash(&mut hasher);
            std::fs::read(&path).unwrap().hash(&mut hasher);
        }
        format!("{:016x}", hasher.finish())
    })
}

pub fn extract(database: &Database, threads: usize) {
    timed("extract", || {
        let build = build();
        for table in TABLES {
            database.command(table);
        }
        let stale: u64 = database.command(&format!("SELECT count() FROM extracted_parts WHERE build != '{build}' FORMAT TSV")).trim().parse().unwrap();
        if stale > 0 {
            log(&format!("extract build={build} stale_parts={stale} dropping text_claims"));
            database.command("DROP TABLE text_claims");
            database.command("DROP TABLE extracted_parts");
            for table in TABLES {
                database.command(table);
            }
        }
        timed("init", crate::init);
        let done: Vec<usize> = database.command("SELECT part FROM extracted_parts FORMAT TSV").lines().map(|line| line.trim().parse().unwrap()).collect();
        let todo: Vec<usize> = (0..PARTS).filter(|part| !done.contains(part)).collect();
        log(&format!("extract build={build} parts={PARTS} done={} todo={} threads={threads}", done.len(), todo.len()));
        let started = Instant::now();
        let mut texts = 0u64;
        for (index, &part) in todo.iter().enumerate() {
            texts += extract_part(database, part, threads, &build).0;
            let elapsed = started.elapsed().as_secs_f64();
            log(&format!("progress parts={}/{} texts={texts} rate={:.0} eta_hours={:.2}", index + 1, todo.len(), texts as f64 / elapsed, elapsed / (index + 1) as f64 * (todo.len() - index - 1) as f64 / 3600.0));
        }
    });
}

fn flair_claims(flair: &str) -> Vec<(String, String, Origin)> {
    let mut found: Vec<(String, String, Origin)> = crate::positioned(flair).into_iter().map(|(attribute, value, _, origin)| (attribute, value, origin)).collect();
    let chars: Vec<char> = flair.chars().collect();
    let mbti = std::panic::Location::caller();
    found.extend(MBTI.iter(&chars).map(|found| ("mbti_type".to_string(), found.g(1).to_lowercase(), mbti)));
    found.sort();
    found.dedup_by(|a, b| a.0 == b.0 && a.1 == b.1);
    found
}

type Claim = (String, String, String, String);

fn put_claim(out: &mut Vec<u8>, (subreddit, flair, attribute, value): &Claim) {
    put_string(out, subreddit);
    put_string(out, flair);
    put_string(out, attribute);
    put_string(out, value);
}

fn mothered(bare: Vec<Claim>, ftm_flairs: &HashMap<String, (u64, u64)>) -> Vec<Claim> {
    timed("mothered", || {
        let mothering: HashSet<&str> = ftm_flairs
            .iter()
            .filter(|(_, (flairs, dated))| *flairs >= FTM_FLAIRS && *dated as f64 >= FTM_SHARE * *flairs as f64)
            .map(|(subreddit, _)| subreddit.as_str())
            .collect();
        let total = bare.len();
        let kept: Vec<Claim> = bare.into_iter().filter(|(subreddit, _, _, _)| !mothering.contains(subreddit.as_str())).collect();
        let mut named: Vec<&&str> = mothering.iter().collect();
        named.sort();
        log(&format!("ftm share={FTM_SHARE} held={total} kept={} subreddits={} {named:?}", kept.len(), mothering.len()));
        kept
    })
}

fn gated(held: Vec<Claim>, flairs: &HashMap<String, u64>) -> Vec<Claim> {
    timed("gate", || {
        let mut yielding: HashMap<(&str, &str), HashSet<&str>> = HashMap::new();
        for (subreddit, flair, attribute, _) in &held {
            yielding.entry((subreddit.as_str(), attribute.as_str())).or_default().insert(flair.as_str());
        }
        let open: HashSet<(String, String)> = yielding
            .into_iter()
            .filter(|((subreddit, _), found)| found.len() as f64 >= SHARE * flairs[*subreddit] as f64)
            .map(|((subreddit, attribute), _)| (subreddit.to_string(), attribute.to_string()))
            .collect();
        let total = held.len();
        let kept: Vec<Claim> = held.into_iter().filter(|(subreddit, _, attribute, _)| open.contains(&(subreddit.clone(), attribute.clone()))).collect();
        log(&format!("gate share={SHARE} held={total} kept={} subreddits_open={}", kept.len(), open.len()));
        kept
    })
}

pub fn flairs(database: &Database, threads: usize) {
    timed("flairs", || {
        for table in TABLES {
            database.command(table);
        }
        timed("init", crate::init);
        database.command("TRUNCATE TABLE flair_claims");
        let started = Instant::now();
        let mut stream = BufReader::with_capacity(1 << 20, database.stream("SELECT DISTINCT subreddit, assumeNotNull(author_flair_text) FROM records WHERE author_flair_text != '' FORMAT RowBinary"));
        let (mut seen, mut claims, mut pending) = (0u64, 0u64, Vec::with_capacity(INSERT_BYTES + (1 << 20)));
        let (mut held, mut counts): (Vec<Claim>, HashMap<String, u64>) = (Vec::new(), HashMap::new());
        let (mut bare, mut ftm_flairs): (Vec<Claim>, HashMap<String, (u64, u64)>) = (Vec::new(), HashMap::new());
        parallel(
            threads,
            move |tasks| {
                let mut batch = Vec::with_capacity(BATCH);
                while let Some(subreddit) = string(&mut stream) {
                    batch.push((subreddit, string(&mut stream).expect("missing flair")));
                    if batch.len() == BATCH {
                        tasks.send(std::mem::replace(&mut batch, Vec::with_capacity(BATCH))).unwrap();
                    }
                }
                if !batch.is_empty() {
                    tasks.send(batch).unwrap();
                }
            },
            |batch: Vec<(String, String)>| {
                let mut out = Vec::new();
                let mut found = 0u64;
                let mut gate = Vec::new();
                let mut subreddits: HashMap<String, u64> = HashMap::new();
                let mut mothers: HashMap<String, (u64, u64)> = HashMap::new();
                let mut uncertain = Vec::new();
                for (subreddit, flair) in &batch {
                    *subreddits.entry(subreddit.clone()).or_default() += 1;
                    let lowered = claimcore::lower(&flair.chars().collect::<Vec<char>>());
                    let plain = demographics::ftm(&lowered) && !demographics::trans_cued(&lowered);
                    if demographics::ftm(&lowered) {
                        let entry = mothers.entry(subreddit.clone()).or_default();
                        entry.0 += 1;
                        entry.1 += demographics::dated(&lowered) as u64;
                    }
                    for (attribute, value, origin) in flair_claims(&format!("r/{subreddit}: {flair}")) {
                        let Some(value) = crate::contracted(&attribute, &value, origin, || format!("r/{subreddit}: {flair}")) else { continue };
                        let claim = (subreddit.clone(), flair.clone(), attribute, value);
                        if GATED.contains(&claim.2.as_str()) {
                            gate.push(claim);
                        } else if plain && MOTHER_CLAIMS.contains(&(claim.2.as_str(), claim.3.as_str())) {
                            uncertain.push(claim);
                        } else {
                            put_claim(&mut out, &claim);
                            found += 1;
                        }
                    }
                }
                (batch.len() as u64, found, out, gate, subreddits, mothers, uncertain)
            },
            |(count, found, out, gate, subreddits, mothers, uncertain): (u64, u64, Vec<u8>, Vec<Claim>, HashMap<String, u64>, HashMap<String, (u64, u64)>, Vec<Claim>)| {
                seen += count;
                claims += found;
                held.extend(gate);
                bare.extend(uncertain);
                for (subreddit, number) in subreddits {
                    *counts.entry(subreddit).or_default() += number;
                }
                for (subreddit, (flairs, dated)) in mothers {
                    let entry = ftm_flairs.entry(subreddit).or_default();
                    entry.0 += flairs;
                    entry.1 += dated;
                }
                pending.extend_from_slice(&out);
                if pending.len() >= INSERT_BYTES {
                    database.insert("flair_claims (subreddit, flair, attribute, value)", &pending);
                    pending.clear();
                }
            },
        );
        for claim in gated(held, &counts) {
            put_claim(&mut pending, &claim);
            claims += 1;
        }
        for claim in mothered(bare, &ftm_flairs) {
            put_claim(&mut pending, &claim);
            claims += 1;
        }
        if !pending.is_empty() {
            database.insert("flair_claims (subreddit, flair, attribute, value)", &pending);
        }
        log(&format!("flairs={seen} claims={claims} invalid={} seconds={:.0}", crate::invalid(), started.elapsed().as_secs_f64()));
    });
}

pub fn attributes(database: &Database) {
    timed("attributes", || {
        database.command("DROP TABLE IF EXISTS claim_attributes");
        database.command(TABLES[0]);
        let mut out = Vec::new();
        for attribute in &claimcore::contract::SCHEMA.attributes {
            put_string(&mut out, &attribute.name);
            put_string(&mut out, &attribute.kind);
            put_string(&mut out, attribute.anchor.as_deref().unwrap_or(""));
            out.extend_from_slice(&attribute.precision.unwrap_or(f64::NAN).to_le_bytes());
            put_string(&mut out, attribute.unit.as_deref().unwrap_or(""));
        }
        database.insert("claim_attributes (attribute, kind, anchor, precision, unit)", &out);
        log(&format!("attributes={}", claimcore::contract::SCHEMA.attributes.len()));
    });
}
