use crate::re::Re;
use crate::text::*;
use std::sync::LazyLock;

pub static CLUB: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+(?:football club|f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?)$"));
pub static BRACKETED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+[(\[][^)\]]*[)\]]?\s*$"));
pub const VAGUE: &str = "this that the these those my our his her their him them it its he she they one game games movie movies film films show shows book books series song songs album albums character characters team teams player players author authors artist artists band bands music n/a na none idk tbd tba nothing null nil insert etc whatever anything all everything other others various misc unknown";

pub fn fan_value(attribute: &str, text: &[char]) -> Option<Vec<char>> {
    let mut text = BRACKETED.sub(text, "");
    if starts_at(&text, 0, "the ") {
        text.drain(..4);
    }
    if attribute == "sports_team" {
        text = CLUB.sub(&text, "");
    }
    let vague: Vec<&str> = VAGUE.split(' ').collect();
    if text.iter().any(|c| c.is_alphanumeric()) && split_ws(&text).iter().any(|word| !vague.contains(&st(word).as_str())) {
        Some(text)
    } else {
        None
    }
}
