use crate::{data_file, timed};
use serde::Deserialize;
use std::collections::{BTreeMap, HashSet};
use std::sync::LazyLock;

const KINDS: [&str; 4] = ["one", "set", "number", "marker"];
const SLOT: &str = "{text}";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Prompt {
    pub opening: String,
    pub closing: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Attribute {
    pub name: String,
    #[serde(default)]
    pub prompt: Option<String>,
    pub kind: String,
    pub describe: String,
    #[serde(default)]
    pub values: Vec<String>,
    #[serde(default)]
    pub unit: Option<String>,
    #[serde(default)]
    pub low: Option<f64>,
    #[serde(default)]
    pub high: Option<f64>,
    #[serde(default)]
    pub precision: Option<f64>,
    #[serde(default)]
    pub anchor: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Schema {
    pub prompts: BTreeMap<String, Prompt>,
    pub attributes: Vec<Attribute>,
}

#[derive(Default)]
pub struct Parsed {
    pub claims: Vec<(String, String)>,
    pub rejected: Vec<&'static str>,
}

pub static SCHEMA: LazyLock<Schema> = LazyLock::new(|| timed("schema", || Schema::parse(&data_file("schema.json"))));

pub fn squeeze(text: &str) -> String {
    text.trim().trim_matches(|c: char| "*_`\"'".contains(c)).to_lowercase().split_whitespace().collect::<Vec<_>>().join(" ")
}

fn key(name: &str) -> String {
    squeeze(name).replace([' ', '-'], "_")
}

fn rounded(number: f64, precision: f64) -> String {
    let value = (number / precision).round() * precision;
    let decimals = if precision >= 1.0 { 0 } else { (-precision.log10()).ceil() as usize };
    format!("{value:.decimals$}")
}

impl Attribute {
    pub fn normal(&self, value: &str) -> Option<String> {
        let value = squeeze(value);
        if self.kind == "number" {
            let number: f64 = value.parse().ok()?;
            return (self.low? ..= self.high?).contains(&number).then(|| rounded(number, self.precision.unwrap()));
        }
        if self.values.is_empty() {
            return (!value.is_empty()).then_some(value);
        }
        self.values.iter().find(|allowed| **allowed == value).cloned()
    }

    fn line(&self) -> String {
        let answer = if self.kind == "number" {
            format!("a number in {}", self.unit.as_deref().unwrap())
        } else if self.values.is_empty() {
            "in the writer's own words".to_string()
        } else {
            format!("one of: {}", self.values.join(" | "))
        };
        let several = if self.kind == "set" { "; several lines allowed" } else { "" };
        format!("- {}: {} ({answer}{several})\n", self.name, self.describe)
    }

    fn check(&self, schema: &Schema) {
        let name = &self.name;
        assert!(!name.is_empty() && *name == key(name), "attribute name {name:?} is not snake_case");
        assert!(KINDS.contains(&self.kind.as_str()), "{name}: kind {:?} is not one of {KINDS:?}", self.kind);
        match (&self.prompt, self.kind == "marker") {
            (Some(prompt), false) => assert!(schema.prompts.contains_key(prompt), "{name}: prompt {prompt:?} is not defined"),
            (None, true) => assert!(!self.values.is_empty(), "{name}: a marker needs its values"),
            _ => panic!("{name}: a marker has no prompt and every other attribute has one"),
        }
        assert!(!self.describe.trim().is_empty(), "{name}: describe is empty");
        let numeric = [self.unit.is_some(), self.low.is_some(), self.high.is_some(), self.precision.is_some()];
        if self.kind == "number" {
            assert!(numeric.iter().all(|&set| set), "{name}: a number needs unit, low, high and precision");
            assert!(self.values.is_empty(), "{name}: a number has no values");
            assert!(self.low.unwrap() < self.high.unwrap() && self.precision.unwrap() > 0.0, "{name}: bad range or precision");
        } else {
            assert!(numeric.iter().all(|&set| !set), "{name}: unit, low, high and precision are for numbers");
            assert!(self.anchor.is_none(), "{name}: only a number can have an anchor");
        }
        if let Some(anchor) = &self.anchor {
            assert!(schema.attributes.iter().any(|other| other.name == *anchor && other.kind == "number"), "{name}: anchor {anchor:?} is not a number attribute");
        }
        let mut seen = HashSet::new();
        for value in &self.values {
            assert!(*value == squeeze(value) && !value.contains('|') && !value.is_empty(), "{name}: value {value:?} must be lowercase, trimmed and free of |");
            assert!(seen.insert(value), "{name}: value {value:?} is listed twice");
        }
    }
}

impl Schema {
    pub fn parse(text: &str) -> Schema {
        let schema: Schema = serde_json::from_str(text).unwrap_or_else(|error| panic!("claim_extraction/schema.json does not parse: {error}"));
        let mut names = HashSet::new();
        for attribute in &schema.attributes {
            attribute.check(&schema);
            assert!(names.insert(&attribute.name), "attribute {} is defined twice", attribute.name);
        }
        for (name, prompt) in &schema.prompts {
            assert!(schema.attributes.iter().any(|attribute| attribute.prompt.as_deref() == Some(name)), "prompt {name} has no attributes");
            assert_eq!((prompt.opening.clone() + &prompt.closing).matches(SLOT).count(), 1, "prompt {name} must contain {SLOT} exactly once");
        }
        schema
    }

    pub fn attribute(&self, name: &str) -> Option<&Attribute> {
        self.attributes.iter().find(|attribute| attribute.name == name)
    }

    pub fn normal(&self, name: &str, value: &str) -> Option<String> {
        self.attribute(name)?.normal(value)
    }

    pub fn template(&self, prompt: &str) -> String {
        let parts = self.prompts.get(prompt).unwrap_or_else(|| panic!("no prompt named {prompt} in the schema"));
        let mut out = parts.opening.clone();
        self.attributes.iter().filter(|attribute| attribute.prompt.as_deref() == Some(prompt)).for_each(|attribute| out.push_str(&attribute.line()));
        out.push_str(&parts.closing);
        out
    }

    pub fn parse_answer(&self, prompt: &str, text: &str, answer: &str) -> Parsed {
        let haystack = squeeze(text);
        let mut parsed = Parsed::default();
        for line in answer.lines() {
            let line = line.trim().trim_start_matches(['-', '*', ' ']);
            if line.is_empty() || squeeze(line) == "none" {
                continue;
            }
            let parts: Vec<&str> = line.splitn(3, '|').map(str::trim).collect();
            if parts.len() < 3 {
                parsed.rejected.push("format");
                continue;
            }
            let name = key(parts[0]);
            let Some(attribute) = self.attributes.iter().find(|attribute| attribute.prompt.as_deref() == Some(prompt) && attribute.name == name) else {
                parsed.rejected.push("attribute");
                continue;
            };
            let Some(value) = attribute.normal(parts[1]) else {
                parsed.rejected.push("value");
                continue;
            };
            let quote = squeeze(parts[2]);
            if quote.is_empty() || !haystack.contains(&quote) {
                parsed.rejected.push("quote");
                continue;
            }
            let claim = (attribute.name.clone(), value);
            if !parsed.claims.contains(&claim) {
                parsed.claims.push(claim);
            }
        }
        parsed
    }
}
