use std::collections::HashMap;

pub enum Encoding {
    Plain,
    Keys(&'static [&'static str]),
    Dictionary,
}

use Encoding::{Dictionary, Keys, Plain};

pub const RECORD_TYPES: [&str; 2] = ["comment", "post"];
pub const STATUSES: [&str; 4] = ["available", "title_only", "removed", "empty"];

const RECORDS: [(&str, &str, Encoding); 17] = [
    ("created_utc", "DateTime('UTC')", Plain),
    ("record_id", "String", Plain),
    ("record_type", "LowCardinality(String)", Keys(&RECORD_TYPES)),
    ("author", "String", Plain),
    ("subreddit", "String", Plain),
    ("author_fullname", "Nullable(String)", Plain),
    ("link_id", "String", Plain),
    ("parent_id", "Nullable(String)", Plain),
    ("author_flair_text", "Nullable(String)", Plain),
    ("link_flair_text", "Nullable(String)", Plain),
    ("post_hint", "LowCardinality(Nullable(String))", Dictionary),
    ("crosspost_parent", "Nullable(String)", Plain),
    ("is_submitter", "Nullable(Bool)", Plain),
    ("over_18", "Nullable(Bool)", Plain),
    ("is_self", "Nullable(Bool)", Plain),
    ("text_status", "LowCardinality(String)", Keys(&STATUSES)),
    ("text_sha256", "FixedString(32)", Plain),
];

const BODIES: [(&str, &str, Encoding); 3] = [("text_sha256", "FixedString(32)", Plain), ("text", "String", Plain), ("words", "UInt32", Plain)];

pub fn put_length(out: &mut Vec<u8>, mut length: usize) {
    while length >= 0x80 {
        out.push(length as u8 | 0x80);
        length >>= 7;
    }
    out.push(length as u8);
}

pub fn put_bytes(out: &mut Vec<u8>, bytes: &[u8]) {
    put_length(out, bytes.len());
    out.extend_from_slice(bytes);
}

fn take_bytes<'a>(data: &'a [u8], position: &mut usize) -> &'a [u8] {
    let (mut length, mut shift) = (0usize, 0);
    loop {
        let byte = data[*position];
        *position += 1;
        length |= usize::from(byte & 0x7f) << shift;
        if byte & 0x80 == 0 {
            break;
        }
        shift += 7;
    }
    *position += length;
    &data[*position - length..*position]
}

#[derive(Default)]
pub struct Column {
    pub nulls: Vec<u8>,
    pub data: Vec<u8>,
}

impl Column {
    pub fn string(&mut self, value: &str) {
        put_bytes(&mut self.data, value.as_bytes());
    }

    pub fn prefixed(&mut self, prefix: &str, value: &str) {
        put_length(&mut self.data, prefix.len() + value.len());
        self.data.extend_from_slice(prefix.as_bytes());
        self.data.extend_from_slice(value.as_bytes());
    }

    pub fn lower(&mut self, value: &str) {
        if value.is_ascii() {
            put_length(&mut self.data, value.len());
            self.data.extend(value.bytes().map(|byte| byte.to_ascii_lowercase()));
        } else {
            self.string(&value.to_lowercase());
        }
    }

    pub fn nullable(&mut self, value: Option<&str>) {
        self.nulls.push(value.is_none() as u8);
        self.string(value.unwrap_or(""));
    }

    pub fn flag(&mut self, value: Option<bool>) {
        self.nulls.push(value.is_none() as u8);
        self.data.push(u8::from(value == Some(true)));
    }

    pub fn u32(&mut self, value: u32) {
        self.data.extend_from_slice(&value.to_le_bytes());
    }

    fn size(&self) -> usize {
        self.nulls.len() + self.data.len()
    }
}

#[derive(Default)]
pub struct Records {
    pub rows: usize,
    pub created_utc: Column,
    pub record_id: Column,
    pub record_type: Column,
    pub author: Column,
    pub subreddit: Column,
    pub author_fullname: Column,
    pub link_id: Column,
    pub parent_id: Column,
    pub author_flair_text: Column,
    pub link_flair_text: Column,
    pub post_hint: Column,
    pub crosspost_parent: Column,
    pub is_submitter: Column,
    pub over_18: Column,
    pub is_self: Column,
    pub text_status: Column,
    pub text_sha256: Column,
}

impl Records {
    pub fn encode(&self) -> Vec<u8> {
        encode(
            self.rows,
            &RECORDS,
            &[
                &self.created_utc,
                &self.record_id,
                &self.record_type,
                &self.author,
                &self.subreddit,
                &self.author_fullname,
                &self.link_id,
                &self.parent_id,
                &self.author_flair_text,
                &self.link_flair_text,
                &self.post_hint,
                &self.crosspost_parent,
                &self.is_submitter,
                &self.over_18,
                &self.is_self,
                &self.text_status,
                &self.text_sha256,
            ],
        )
    }
}

#[derive(Default)]
pub struct Bodies {
    pub rows: usize,
    pub text_sha256: Column,
    pub text: Column,
    pub words: Column,
}

impl Bodies {
    pub fn encode(&self) -> Vec<u8> {
        encode(self.rows, &BODIES, &[&self.text_sha256, &self.text, &self.words])
    }
}

fn encode(rows: usize, schema: &[(&str, &str, Encoding)], columns: &[&Column]) -> Vec<u8> {
    let mut out = Vec::with_capacity(columns.iter().map(|column| column.size()).sum::<usize>() + rows * 4 + 4096);
    put_length(&mut out, columns.len());
    put_length(&mut out, rows);
    for ((name, kind, encoding), column) in schema.iter().zip(columns) {
        put_bytes(&mut out, name.as_bytes());
        put_bytes(&mut out, kind.as_bytes());
        match encoding {
            Plain => {
                out.extend_from_slice(&column.nulls);
                out.extend_from_slice(&column.data);
            }
            Keys(keys) => {
                let mut dictionary = Vec::new();
                keys.iter().for_each(|key| put_bytes(&mut dictionary, key.as_bytes()));
                let indexes: Vec<u32> = column.data.iter().map(|&index| u32::from(index)).collect();
                low_cardinality(&mut out, keys.len(), &dictionary, &indexes);
            }
            Dictionary => {
                let (mut seen, mut dictionary, mut indexes, mut position) = (HashMap::new(), vec![0u8], Vec::with_capacity(rows), 0);
                for &null in &column.nulls {
                    let value = take_bytes(&column.data, &mut position);
                    indexes.push(if null == 1 {
                        0
                    } else {
                        let next = seen.len() as u32 + 1;
                        *seen.entry(value).or_insert_with(|| {
                            put_bytes(&mut dictionary, value);
                            next
                        })
                    });
                }
                low_cardinality(&mut out, seen.len() + 1, &dictionary, &indexes);
            }
        }
    }
    out
}

fn low_cardinality(out: &mut Vec<u8>, count: usize, dictionary: &[u8], indexes: &[u32]) {
    let width: usize = if count <= 1 << 8 { 1 } else if count <= 1 << 16 { 2 } else { 4 };
    out.extend_from_slice(&1u64.to_le_bytes());
    out.extend_from_slice(&(width.trailing_zeros() as u64 | 1 << 9).to_le_bytes());
    out.extend_from_slice(&(count as u64).to_le_bytes());
    out.extend_from_slice(dictionary);
    out.extend_from_slice(&(indexes.len() as u64).to_le_bytes());
    for &index in indexes {
        out.extend_from_slice(&index.to_le_bytes()[..width]);
    }
}
