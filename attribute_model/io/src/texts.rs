use crate::database::{put_string, text, Database};
use crate::prepare::save;
use crate::{log, option, timed};
use crossbeam_channel::{bounded, Receiver};
use std::path::Path;
use std::thread;
use std::time::Instant;
use tokenizers::{Tokenizer, TruncationParams};

const TABLE: &str = "text_labeled";
const SELECTED: &str = "SELECT author, text FROM author_texts WHERE author IN text_labeled ORDER BY author, cityHash64(text) LIMIT 1 BY author SETTINGS optimize_read_in_order = 1 FORMAT RowBinary";
const BATCH: usize = 1 << 16;
const AHEAD: usize = 8;
const UPLOAD: usize = 1 << 20;

fn upload(database: &Database, authors: &[String]) {
    timed("texts upload", || {
        database.command(&format!("DROP TABLE IF EXISTS {TABLE}"));
        database.command(&format!("CREATE TABLE {TABLE} (author String) ENGINE = MergeTree ORDER BY author"));
        for chunk in authors.chunks(UPLOAD) {
            let mut body = Vec::with_capacity(chunk.len() * 16);
            chunk.iter().for_each(|author| put_string(&mut body, author));
            database.insert(TABLE, &body);
        }
    });
}

fn runs(source: &Path, authors: usize) -> Vec<(usize, usize)> {
    let manifest: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(source.join("manifest.json")).unwrap()).unwrap();
    let runs: Vec<(usize, usize)> = manifest["splits"].as_object().expect("manifest has no split ranges").values().map(|range| (range[0].as_u64().unwrap() as usize, range[1].as_u64().unwrap() as usize)).collect();
    assert_eq!(runs.iter().map(|(start, end)| end - start).sum::<usize>(), authors, "split ranges do not cover the authors");
    runs
}

fn fetch(database: &Database, authors: &[String], mut runs: Vec<(usize, usize)>, batches: crossbeam_channel::Sender<Vec<(u32, String)>>) {
    let started = Instant::now();
    let mut rows = database.rows(SELECTED);
    let mut batch = Vec::with_capacity(BATCH);
    let mut fetched = 0usize;
    while !rows.done() {
        let author = rows.bytes();
        let run = runs.iter_mut().find(|(start, end)| start < end && authors[*start].as_bytes() == author).unwrap_or_else(|| panic!("author_texts row {fetched} is {:?}, which is not the next author of any split", text(author)));
        let row = run.0 as u32;
        run.0 += 1;
        if fetched == 0 {
            log(&format!("texts first row seconds={:.1}", started.elapsed().as_secs_f64()));
        }
        batch.push((row, text(rows.bytes())));
        fetched += 1;
        if batch.len() == BATCH {
            batches.send(std::mem::replace(&mut batch, Vec::with_capacity(BATCH))).unwrap();
        }
    }
    batches.send(batch).unwrap();
    assert!(runs.iter().all(|(start, end)| start == end), "author_texts gave {fetched} texts for {} labeled authors", authors.len());
    log(&format!("texts fetched={fetched} seconds={:.1}", started.elapsed().as_secs_f64()));
}

struct Chunk {
    rows: Vec<i32>,
    lengths: Vec<u32>,
    tokens: Vec<i32>,
}

fn write(out: &Path, index: usize, chunk: &Chunk, budget: usize) {
    let mut order: Vec<i32> = (0..chunk.rows.len() as i32).collect();
    order.sort_by_key(|&text| chunk.lengths[text as usize]);
    let mut starts = Vec::with_capacity(chunk.lengths.len());
    let mut start = 0usize;
    for &length in &chunk.lengths {
        starts.push(start);
        start += length as usize;
    }
    let mut tokens = Vec::with_capacity(chunk.tokens.len());
    for &text in &order {
        tokens.extend_from_slice(&chunk.tokens[starts[text as usize]..][..chunk.lengths[text as usize] as usize]);
    }
    let mut shapes = Vec::new();
    for group in order.chunk_by(|&left, &right| chunk.lengths[left as usize] == chunk.lengths[right as usize]) {
        let length = chunk.lengths[group[0] as usize] as usize;
        assert!(length > 0, "tokenizer gave an empty text");
        let step = (budget / length).max(1);
        for start in (0..group.len()).step_by(step) {
            shapes.extend([step.min(group.len() - start) as i32, length as i32]);
        }
    }
    save(&out.join(format!("{index}.rows.npy")), "<i4", &[chunk.rows.len()], &chunk.rows);
    save(&out.join(format!("{index}.order.npy")), "<i4", &[order.len()], &order);
    save(&out.join(format!("{index}.tokens.npy")), "<i4", &[tokens.len()], &tokens);
    save(&out.join(format!("{index}.shapes.npy")), "<i4", &[shapes.len() / 2, 2], &shapes);
}

fn tokenize(tokenizer: &Tokenizer, batches: Receiver<Vec<(u32, String)>>, out: &Path, size: usize, budget: usize, authors: usize) {
    let started = Instant::now();
    let (mut index, mut texts, mut tokens, mut waited) = (0usize, 0usize, 0usize, 0f64);
    let mut chunk = Chunk { rows: Vec::with_capacity(size), lengths: Vec::with_capacity(size), tokens: Vec::new() };
    loop {
        let waiting = Instant::now();
        let batch = batches.recv().ok();
        waited += waiting.elapsed().as_secs_f64();
        let last = batch.is_none();
        if let Some(batch) = batch {
            let (rows, strings): (Vec<u32>, Vec<String>) = batch.into_iter().unzip();
            for (row, encoding) in rows.into_iter().zip(tokenizer.encode_batch_fast(strings, true).unwrap_or_else(|error| panic!("tokenizer failed: {error}"))) {
                chunk.rows.push(row as i32);
                chunk.lengths.push(encoding.get_ids().len() as u32);
                chunk.tokens.extend(encoding.get_ids().iter().map(|&id| id as i32));
            }
        }
        if chunk.rows.len() >= size || (last && !chunk.rows.is_empty()) {
            write(out, index, &chunk, budget);
            texts += chunk.rows.len();
            tokens += chunk.tokens.len();
            println!("{index} {}", chunk.rows.len());
            log(&format!("texts chunk={index} tokenized={texts} of {authors} tokens={tokens} waited={waited:.1} seconds={:.1}", started.elapsed().as_secs_f64()));
            index += 1;
            chunk.rows.clear();
            chunk.lengths.clear();
            chunk.tokens.clear();
        }
        if last {
            break;
        }
    }
    assert_eq!(texts, authors, "tokenized {texts} texts for {authors} labeled authors");
}

pub fn run(database: &Database, args: &[String]) {
    timed("texts", || {
        let source = Path::new(option(args, "--source", ""));
        let out = Path::new(option(args, "--out", ""));
        let size: usize = option(args, "--chunk", "").parse().unwrap();
        let budget: usize = option(args, "--budget", "").parse().unwrap();
        let authors: Vec<String> = serde_json::from_str(&std::fs::read_to_string(source.join("authors.json")).unwrap()).unwrap();
        let runs = runs(source, authors.len());
        let mut tokenizer = Tokenizer::from_file(option(args, "--tokenizer", "")).unwrap_or_else(|error| panic!("cannot load tokenizer: {error}"));
        tokenizer.with_truncation(Some(TruncationParams { max_length: option(args, "--max-length", "").parse().unwrap(), ..Default::default() })).unwrap();
        tokenizer.with_padding(None);
        upload(database, &authors);
        let (batches, inbox) = bounded(AHEAD);
        thread::scope(|scope| {
            scope.spawn(|| timed("texts fetch", || fetch(database, &authors, runs, batches)));
            timed("texts tokenize", || tokenize(&tokenizer, inbox, out, size, budget, authors.len()));
        });
        database.command(&format!("DROP TABLE {TABLE}"));
    });
}
