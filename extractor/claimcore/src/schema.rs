use crate::re::Re;
use crate::text::*;
use std::sync::LazyLock;

pub const YEAR: i64 = 2026;
pub static CLUB: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+(?:football club|f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?)$"));
pub static BRACKETED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+[(\[][^)\]]*[)\]]?\s*$"));
pub const VAGUE: &str = "this that the these those my our his her their him them it its he she they one game games movie movies film films show shows book books series song songs album albums character characters team teams player players author authors artist artists band bands music";
pub const NEURO: [&str; 4] = ["adhd", "autism", "both adhd and autism", "neurodivergent, unspecified"];

pub fn fan_value(attribute: &str, text: &[char]) -> Option<Vec<char>> {
    let mut text = BRACKETED.sub(text, "");
    if starts_at(&text, 0, "the ") {
        text.drain(..4);
    }
    if attribute == "sports_team" {
        text = CLUB.sub(&text, "");
    }
    let vague: Vec<&str> = VAGUE.split(' ').collect();
    if split_ws(&text).iter().any(|word| !vague.contains(&st(word).as_str())) {
        Some(text)
    } else {
        None
    }
}

pub fn canonical(attribute: &str, value: &str) -> Option<(String, String)> {
    if attribute == "drinking" {
        return None;
    }
    if attribute == "birth_year" {
        let year: i64 = value.parse().ok()?;
        return Some(("age".to_string(), (YEAR - year).to_string()));
    }
    if attribute == "mental_condition" && NEURO.contains(&value) {
        return Some(("neurotype".to_string(), value.to_string()));
    }
    Some((attribute.to_string(), value.to_string()))
}
