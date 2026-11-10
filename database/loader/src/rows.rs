use crate::native::{Bodies, Records};
use serde::de::{Deserializer, Error, Visitor};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::borrow::Cow;
use std::fmt;

const UNAVAILABLE: [&str; 5] = [
    "[deleted]",
    "[removed]",
    "[ Removed by Reddit ]",
    "[ Removed by moderator ]",
    "[ Removed by Reddit on account of violating the [content policy](/help/contentpolicy). ]",
];

pub fn space(c: char) -> bool {
    matches!(c, '\t'..='\r' | '\x1c'..='\x1f' | ' ' | '\u{85}' | '\u{a0}' | '\u{1680}' | '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' | '\u{205f}' | '\u{3000}')
}

fn nonblank(text: &str) -> bool {
    text.chars().any(|c| !space(c))
}

fn words(text: &str) -> u32 {
    let (mut count, mut inside) = (0, false);
    for c in text.chars() {
        let blank = space(c);
        count += u32::from(!blank && !inside);
        inside = !blank;
    }
    count
}

pub struct Text<'a>(Cow<'a, str>);

impl<'de: 'a, 'a> Deserialize<'de> for Text<'a> {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct Seen;
        impl<'de> Visitor<'de> for Seen {
            type Value = Cow<'de, str>;
            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("a string")
            }
            fn visit_borrowed_str<E: Error>(self, value: &'de str) -> Result<Self::Value, E> {
                Ok(Cow::Borrowed(value))
            }
            fn visit_str<E: Error>(self, value: &str) -> Result<Self::Value, E> {
                Ok(Cow::Owned(value.to_owned()))
            }
            fn visit_string<E: Error>(self, value: String) -> Result<Self::Value, E> {
                Ok(Cow::Owned(value))
            }
        }
        deserializer.deserialize_str(Seen).map(Text)
    }
}

pub struct Created(u32);

fn integer(text: &str) -> Option<u32> {
    let text = text.trim_matches(space);
    let (negative, digits) = match text.as_bytes().first() {
        Some(b'-') => (true, &text[1..]),
        Some(b'+') => (false, &text[1..]),
        _ => (false, text),
    };
    if digits.is_empty() || digits.starts_with('_') || digits.ends_with('_') || digits.contains("__") || !digits.bytes().all(|byte| byte.is_ascii_digit() || byte == b'_') {
        return None;
    }
    let value = digits.bytes().filter(|&byte| byte != b'_').try_fold(0u64, |total, byte| total.checked_mul(10)?.checked_add(u64::from(byte - b'0')))?;
    if negative && value != 0 {
        None
    } else {
        u32::try_from(value).ok()
    }
}

impl<'de> Deserialize<'de> for Created {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct Seen;
        impl Visitor<'_> for Seen {
            type Value = u32;
            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("created_utc as an int, float, numeric string or bool within UInt32")
            }
            fn visit_bool<E: Error>(self, value: bool) -> Result<u32, E> {
                Ok(u32::from(value))
            }
            fn visit_u64<E: Error>(self, value: u64) -> Result<u32, E> {
                u32::try_from(value).map_err(|_| E::custom(format!("created_utc {value} outside UInt32")))
            }
            fn visit_i64<E: Error>(self, value: i64) -> Result<u32, E> {
                u32::try_from(value).map_err(|_| E::custom(format!("created_utc {value} outside UInt32")))
            }
            fn visit_f64<E: Error>(self, value: f64) -> Result<u32, E> {
                let whole = value.trunc();
                if (0.0..=f64::from(u32::MAX)).contains(&whole) {
                    Ok(whole as u32)
                } else {
                    Err(E::custom(format!("created_utc {value} outside UInt32")))
                }
            }
            fn visit_str<E: Error>(self, value: &str) -> Result<u32, E> {
                integer(value).ok_or_else(|| E::custom(format!("created_utc {value:?} is not an integer within UInt32")))
            }
        }
        deserializer.deserialize_any(Seen).map(Created)
    }
}

pub enum Slot<T> {
    Missing,
    Null,
    Value(T),
}

impl<T> Default for Slot<T> {
    fn default() -> Self {
        Slot::Missing
    }
}

impl<'de, T: Deserialize<'de>> Deserialize<'de> for Slot<T> {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        Ok(Option::<T>::deserialize(deserializer)?.map_or(Slot::Null, Slot::Value))
    }
}

impl<T> Slot<T> {
    fn get(self) -> Option<T> {
        match self {
            Slot::Value(value) => Some(value),
            _ => None,
        }
    }

    fn nullable(self, key: &str) -> Option<T> {
        match self {
            Slot::Missing => panic!("record has no {key}"),
            Slot::Null => None,
            Slot::Value(value) => Some(value),
        }
    }

    fn required(self, key: &str) -> T {
        self.nullable(key).unwrap_or_else(|| panic!("record has null {key}"))
    }
}

fn text<'a>(slot: Option<&'a Text>) -> Option<&'a str> {
    slot.map(|value| &*value.0)
}

#[derive(Deserialize)]
struct Comment<'a> {
    #[serde(default)]
    created_utc: Slot<Created>,
    #[serde(borrow, default)]
    id: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author: Slot<Text<'a>>,
    #[serde(borrow, default)]
    subreddit: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author_fullname: Slot<Text<'a>>,
    #[serde(borrow, default)]
    link_id: Slot<Text<'a>>,
    #[serde(borrow, default)]
    parent_id: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author_flair_text: Slot<Text<'a>>,
    #[serde(borrow, default)]
    post_hint: Slot<Text<'a>>,
    #[serde(borrow, default)]
    crosspost_parent: Slot<Text<'a>>,
    #[serde(default)]
    is_submitter: Slot<bool>,
    #[serde(borrow, default)]
    body: Slot<Text<'a>>,
}

#[derive(Deserialize)]
struct Post<'a> {
    #[serde(default)]
    created_utc: Slot<Created>,
    #[serde(borrow, default)]
    id: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author: Slot<Text<'a>>,
    #[serde(borrow, default)]
    subreddit: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author_fullname: Slot<Text<'a>>,
    #[serde(borrow, default)]
    author_flair_text: Slot<Text<'a>>,
    #[serde(borrow, default)]
    link_flair_text: Slot<Text<'a>>,
    #[serde(borrow, default)]
    post_hint: Slot<Text<'a>>,
    #[serde(borrow, default)]
    crosspost_parent: Slot<Text<'a>>,
    #[serde(default)]
    over_18: Slot<bool>,
    #[serde(default)]
    is_self: Slot<bool>,
    #[serde(borrow, default)]
    selftext: Slot<Text<'a>>,
    #[serde(borrow, default)]
    title: Slot<Text<'a>>,
}

fn parse<'a, T: Deserialize<'a>>(line: &'a [u8]) -> T {
    sonic_rs::from_slice(line).unwrap_or_else(|error| panic!("cannot parse record: {error}: {}", String::from_utf8_lossy(&line[..line.len().min(500)])))
}

pub fn add(line: &[u8], comment: bool, records: &mut Records, bodies: &mut Bodies) {
    if comment {
        let raw: Comment = parse(line);
        let body = raw.body.required("body");
        let id = raw.id.required("id");
        records.created_utc.u32(raw.created_utc.required("created_utc").0);
        records.record_id.prefixed("t1_", &id.0);
        records.record_type.data.push(0);
        records.author.string(&raw.author.required("author").0);
        records.subreddit.lower(&raw.subreddit.required("subreddit").0);
        records.author_fullname.nullable(text(raw.author_fullname.get().as_ref()));
        records.link_id.string(&raw.link_id.required("link_id").0);
        records.parent_id.nullable(text(raw.parent_id.nullable("parent_id").as_ref()));
        records.author_flair_text.nullable(text(raw.author_flair_text.nullable("author_flair_text").as_ref()));
        records.link_flair_text.nullable(None);
        records.post_hint.nullable(text(raw.post_hint.get().as_ref()));
        records.crosspost_parent.nullable(text(raw.crosspost_parent.get().as_ref()));
        records.is_submitter.flag(raw.is_submitter.get());
        records.over_18.flag(None);
        records.is_self.flag(None);
        content(true, "", &body.0, records, bodies);
    } else {
        let raw: Post = parse(line);
        let body = raw.selftext.required("selftext");
        let title = raw.title.required("title");
        let id = raw.id.required("id");
        records.created_utc.u32(raw.created_utc.required("created_utc").0);
        records.record_id.prefixed("t3_", &id.0);
        records.record_type.data.push(1);
        records.author.string(&raw.author.required("author").0);
        records.subreddit.lower(&raw.subreddit.required("subreddit").0);
        records.author_fullname.nullable(text(raw.author_fullname.get().as_ref()));
        records.link_id.prefixed("t3_", &id.0);
        records.parent_id.nullable(None);
        records.author_flair_text.nullable(text(raw.author_flair_text.nullable("author_flair_text").as_ref()));
        records.link_flair_text.nullable(text(raw.link_flair_text.nullable("link_flair_text").as_ref()));
        records.post_hint.nullable(text(raw.post_hint.get().as_ref()));
        records.crosspost_parent.nullable(text(raw.crosspost_parent.get().as_ref()));
        records.is_submitter.flag(None);
        records.over_18.flag(raw.over_18.nullable("over_18"));
        records.is_self.flag(raw.is_self.nullable("is_self"));
        content(false, &title.0, &body.0, records, bodies);
    }
    records.rows += 1;
}

fn content(comment: bool, title: &str, body: &str, records: &mut Records, bodies: &mut Bodies) {
    let removed = UNAVAILABLE.contains(&body) || UNAVAILABLE.contains(&title);
    let body = if UNAVAILABLE.contains(&body) { "" } else { body };
    let title = if UNAVAILABLE.contains(&title) { "" } else { title };
    let text = match (nonblank(title), nonblank(body)) {
        (true, true) => Cow::Owned(format!("{title}\n\n{body}")),
        (true, false) => Cow::Borrowed(title),
        (false, true) => Cow::Borrowed(body),
        (false, false) => Cow::Borrowed(""),
    };
    let status = if !comment && !title.is_empty() && body.is_empty() {
        1
    } else if !text.is_empty() {
        0
    } else if removed {
        2
    } else {
        3
    };
    let digest = Sha256::digest(text.as_bytes());
    records.text_status.data.push(status);
    records.text_sha256.data.extend_from_slice(&digest);
    if !text.is_empty() {
        bodies.text_sha256.data.extend_from_slice(&digest);
        bodies.text.string(&text);
        bodies.words.u32(words(&text));
        bodies.rows += 1;
    }
}
