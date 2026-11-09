use crate::database::{put_string, text, Database};
use crate::{log, option, timed};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;
use tokenizers::{Tokenizer, TruncationParams};

const TABLE: &str = "text_labeled";
const SELECTED: &str = "SELECT author, argMin(text, cityHash64(text)) FROM author_texts WHERE author IN text_labeled GROUP BY author ORDER BY author SETTINGS optimize_aggregation_in_order = 1 FORMAT RowBinary";
const BATCH: usize = 1 << 16;
const UPLOAD: usize = 1 << 20;

fn npy(path: &Path, values: &[i32]) {
    let mut header = format!("{{'descr': '<i4', 'fortran_order': False, 'shape': ({},), }}", values.len());
    while (10 + header.len() + 1) % 64 != 0 {
        header.push(' ');
    }
    header.push('\n');
    let mut out = BufWriter::with_capacity(1 << 24, File::create(path).unwrap_or_else(|error| panic!("cannot write {}: {error}", path.display())));
    out.write_all(b"\x93NUMPY\x01\x00").unwrap();
    out.write_all(&(header.len() as u16).to_le_bytes()).unwrap();
    out.write_all(header.as_bytes()).unwrap();
    for value in values {
        out.write_all(&value.to_le_bytes()).unwrap();
    }
    out.flush().unwrap();
}

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

fn encoded(tokenizer: &Tokenizer, texts: Vec<String>, lengths: &mut Vec<i32>, tokens: &mut BufWriter<File>) {
    for encoding in tokenizer.encode_batch_fast(texts, true).unwrap_or_else(|error| panic!("tokenizer failed: {error}")) {
        lengths.push(encoding.get_ids().len() as i32);
        for id in encoding.get_ids() {
            tokens.write_all(&(*id as i32).to_le_bytes()).unwrap();
        }
    }
}

pub fn run(database: &Database, args: &[String]) {
    timed("texts", || {
        let out = Path::new(option(args, "--out", ""));
        let authors: Vec<String> = serde_json::from_str(&std::fs::read_to_string(option(args, "--authors", "")).unwrap()).unwrap();
        let mut tokenizer = Tokenizer::from_file(option(args, "--tokenizer", "")).unwrap_or_else(|error| panic!("cannot load tokenizer: {error}"));
        tokenizer.with_truncation(Some(TruncationParams { max_length: option(args, "--max-length", "").parse().unwrap(), ..Default::default() })).unwrap();
        tokenizer.with_padding(None);
        upload(database, &authors);
        let mut tokens = BufWriter::with_capacity(1 << 24, File::create(out.join("tokens.bin")).unwrap());
        let mut lengths = Vec::with_capacity(authors.len());
        let mut rows = database.rows(SELECTED);
        let mut batch = Vec::with_capacity(BATCH);
        let mut index = 0;
        while !rows.done() {
            let author = text(rows.bytes());
            assert!(index < authors.len() && author == authors[index], "author_texts row {index} is {author:?}, expected {:?}", authors.get(index));
            batch.push(text(rows.bytes()));
            index += 1;
            if batch.len() == BATCH {
                encoded(&tokenizer, std::mem::replace(&mut batch, Vec::with_capacity(BATCH)), &mut lengths, &mut tokens);
                if index % (1 << 20) < BATCH {
                    log(&format!("texts tokenized={index} of {}", authors.len()));
                }
            }
        }
        encoded(&tokenizer, batch, &mut lengths, &mut tokens);
        tokens.flush().unwrap();
        assert_eq!(index, authors.len(), "author_texts gave {index} texts for {} labeled authors", authors.len());
        npy(&out.join("lengths.npy"), &lengths);
        database.command(&format!("DROP TABLE {TABLE}"));
        log(&format!("texts authors={index} tokens={}", lengths.iter().map(|&length| length as u64).sum::<u64>()));
    });
}
