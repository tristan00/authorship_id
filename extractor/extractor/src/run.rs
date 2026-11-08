use crate::database::{put_string, string, Database};
use claimcore::{log, timed, Re};
use crossbeam_channel::bounded;
use std::io::{BufReader, Read};
use std::sync::LazyLock;
use std::time::Instant;

const PARTS: usize = 256;
const BATCH: usize = 1024;
const INSERT_BYTES: usize = 64 << 20;
const COMPASS_SUBREDDIT: &str = "politicalcompassmemes";
const TABLES: [&str; 3] = [
    "CREATE TABLE IF NOT EXISTS text_claims (text_sha256 FixedString(32), attribute LowCardinality(String), value String, position UInt32) ENGINE = MergeTree ORDER BY (text_sha256, attribute)",
    "CREATE TABLE IF NOT EXISTS flair_claims (subreddit String, flair String, attribute LowCardinality(String), value String) ENGINE = MergeTree ORDER BY (subreddit, flair)",
    "CREATE TABLE IF NOT EXISTS extracted_parts (part UInt16, texts UInt64, claims UInt64, seconds Float32, finished_at DateTime('UTC') DEFAULT now()) ENGINE = MergeTree ORDER BY part",
];

static MBTI: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![A-Za-z])([IE][NS][TF][JP])(?:-[AT])?(?![A-Za-z])"));
static COMPASS: LazyLock<Re> = LazyLock::new(|| Re::with(r"(?:^|[\s:-])(?:chad\s+)?(?:(auth|lib)[-\s]?)?(left|center|centre|right|centrist)\s*$", claimcore::re::I));

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

fn extract_part(database: &Database, part: usize, threads: usize) -> (u64, u64) {
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
                for (attribute, value, position) in crate::positioned(text) {
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
    database.insert("extracted_parts (part, texts, claims, seconds)", &row);
    log(&format!("part={part} texts={texts} claims={claims} seconds={seconds:.0} rate={:.0}", texts as f64 / seconds.max(1e-9)));
    (texts, claims)
}

pub fn extract(database: &Database, threads: usize, reset: bool) {
    timed("extract", || {
        if reset {
            database.command("DROP TABLE IF EXISTS text_claims");
            database.command("DROP TABLE IF EXISTS extracted_parts");
        }
        for table in TABLES {
            database.command(table);
        }
        timed("init", crate::init);
        let done: Vec<usize> = database.command("SELECT part FROM extracted_parts FORMAT TSV").lines().map(|line| line.trim().parse().unwrap()).collect();
        let todo: Vec<usize> = (0..PARTS).filter(|part| !done.contains(part)).collect();
        log(&format!("extract parts={PARTS} done={} todo={} threads={threads}", done.len(), todo.len()));
        let started = Instant::now();
        let mut texts = 0u64;
        for (index, &part) in todo.iter().enumerate() {
            texts += extract_part(database, part, threads).0;
            let elapsed = started.elapsed().as_secs_f64();
            log(&format!("progress parts={}/{} texts={texts} rate={:.0} eta_hours={:.2}", index + 1, todo.len(), texts as f64 / elapsed, elapsed / (index + 1) as f64 * (todo.len() - index - 1) as f64 / 3600.0));
        }
    });
}

fn compass(flair: &[char]) -> Option<String> {
    let found = COMPASS.find(flair)?;
    let axis = found.gs(1).unwrap_or_default().to_lowercase();
    let side = found.g(2).to_lowercase().replace("centre", "center");
    Some(match (axis.is_empty(), side.as_str()) {
        (true, "center" | "centrist") => "centrist".to_string(),
        (false, "center" | "centrist") => format!("{axis}-center"),
        (true, _) => side,
        (false, _) => format!("{axis}-{side}"),
    })
}

fn flair_claims(subreddit: &str, flair: &str) -> Vec<(String, String)> {
    let mut found: Vec<(String, String)> = crate::positioned(flair).into_iter().map(|(attribute, value, _)| (attribute, value)).collect();
    let chars: Vec<char> = flair.chars().collect();
    found.extend(MBTI.iter(&chars).map(|found| ("personality_type".to_string(), found.g(1))));
    if subreddit == COMPASS_SUBREDDIT {
        if let Some(side) = compass(&chars) {
            found.push(("political_compass".to_string(), side));
        }
    }
    found.sort();
    found.dedup();
    found
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
                for (subreddit, flair) in &batch {
                    for (attribute, value) in flair_claims(subreddit, flair) {
                        put_string(&mut out, subreddit);
                        put_string(&mut out, flair);
                        put_string(&mut out, &attribute);
                        put_string(&mut out, &value);
                        found += 1;
                    }
                }
                (batch.len() as u64, found, out)
            },
            |(count, found, out): (u64, u64, Vec<u8>)| {
                seen += count;
                claims += found;
                pending.extend_from_slice(&out);
                if pending.len() >= INSERT_BYTES {
                    database.insert("flair_claims (subreddit, flair, attribute, value)", &pending);
                    pending.clear();
                }
            },
        );
        if !pending.is_empty() {
            database.insert("flair_claims (subreddit, flair, attribute, value)", &pending);
        }
        log(&format!("flairs={seen} claims={claims} seconds={:.0}", started.elapsed().as_secs_f64()));
    });
}
