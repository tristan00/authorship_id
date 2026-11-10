use crate::rules::{h, said, sh};
use crate::*;
use claimcore::*;

const GEN: &str = r"(millennial|millenial|milennial|gen[- ]?z-?er|gen[- ]?z|zoomer|gen[- ]?x-?er|gen[- ]?x|gen[- ]?y|xennial|zillennial|zillenial|boomer|baby boomer|gen[- ]?alpha|gen[- ]?jones|generation (?:x|y|z|alpha|jones))";
const GEN_AFTER: &str = r"(?![-'])(?! (?:kids?|parents?|stuff|humou?r|thing|things|music|culture|mindset|energy|brain|vibes?|style|era|tastes?|problems?|trope|nostalgia|bait|household|home|house|money|memes?|shooter|shooters|games?|logic|films?|movies?|shows?|songs?|bands?|books?|characters?|icons?|staples?|classics?)\b)";

fn generation(m: &Match) -> Option<String> {
    let key: String = st(m.first()?).chars().filter(|c| c.is_alphanumeric()).collect();
    let key = key.trim_start_matches("generation").to_string();
    let value = match key.as_str() {
        "millennial" | "millenial" | "milennial" | "millennials" | "millenials" | "geny" | "y" => "millennial",
        "genz" | "genzer" | "genzers" | "zoomer" | "zoomers" | "z" => "gen z",
        "genx" | "genxer" | "genxers" | "x" => "gen x",
        "xennial" | "xennials" => "xennial",
        "zillennial" | "zillenial" | "zillennials" => "zillennial",
        "boomer" | "babyboomer" | "boomers" => "boomer",
        "genalpha" | "alpha" => "gen alpha",
        "genjones" | "jones" => "gen jones",
        _ => return None,
    };
    Some(value.to_string())
}

pub fn rules() -> Vec<Rule> {
    vec![
        said("generation", &format!(r"{IM} (?:(?:also|just|still|technically|basically|literally|actually|definitely|officially|a|an|the|proud|proudly|young|younger|old|older|elder|early|mid|middle|late|core|geriatric|ancient|baby|oldest|youngest|tail[- ]end|solidly|firmly|squarely|elderly|part of|one of those|very|on the cusp of|considered|an elder|an older|an early|a late|a young|an old) )*{GEN}\b{GEN_AFTER}"), generation, h()),
        said("generation", &format!(r"\bas an? (?:(?:young|younger|old|older|elder|early|late|fellow|proud|middle|core) )?{GEN}\b{GEN_AFTER}(?!['’]s)"), generation, h()),
        said("generation", &format!(r"(?:^{flair}|[.!?,;(\n] *|\bfellow )(?:(?:young|younger|old|older|elder|early|late) )?{GEN} here\b", flair = claimcore::flair!()), generation, sh()),
        said("generation", r"\b(?:we|us|fellow) (?:(?:older|younger|elder|early|late|old|young) )?(millennials|millenials|gen ?zers|gen ?xers|boomers|zoomers|xennials|zillennials|gen z|gen x)\b(?! (?:who|that)\b)", generation, h()),
    ]
}
