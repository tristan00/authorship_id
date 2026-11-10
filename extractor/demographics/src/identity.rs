use crate::rules::{alone, h, mine, said, sh};
use crate::*;
use claimcore::*;
use std::sync::LazyLock;

static TRANS_TEXT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:trans|transgender|mtf|ftm|transfem\w*|transmasc\w*|nonbinary|non-binary|enby|dysphoria|transition\w*|t4t|tgirl|transwoman|transman|transsexual|she/her|he/him|they/them|top surgery|bottom surgery|egg_irl|deadname\w*|hrt)\b"));
static PERCEIVED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:think|thinks|thought|assume|assumes|assumed|believe|believes|mistake|mistakes|mistaken|treat|treats|treated|pass|passes|passing|look|looks|act|acts|pretend\w*|wonder\w*|if)\b[^.!?\n]{0,16}$"));

pub fn force() {
    for re in [&TRANS_TEXT, &PERCEIVED] {
        LazyLock::force(re);
    }
}

fn sincere(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| if PERCEIVED.test(before(m.string, m.start(), 40)) { None } else { value(m) }
}

fn cis(m: &Match) -> Option<String> {
    let value = match m.group(1).map(st).as_deref() {
        Some("woman" | "girl" | "female" | "lady" | "f" | "gal") => "cis woman",
        Some("man" | "guy" | "male" | "dude" | "boy" | "m" | "bloke") => "cis man",
        _ => "cis (gender unstated)",
    };
    Some(value.to_string())
}

pub fn rules() -> Vec<Rule> {
    vec![
        said("gender", &format!(r"{IM} (?:(?:also|just|still|actually|openly|proudly|a|an) ){{0,3}}(?:trans|transgender)\b(?![-'/])(?! (?:\w+ )?(?:woman|women|girl|girls|female|lady|gal|man|men|guy|guys|boy|male|dude|fem\w*|masc\w*|people|rights|folks|kids?|community|friends?|ally|allies|issues?|inclusive|healthcare|panic|athletes?|stuff|content|porn|ftm|mtf|f2m|m2f|nb|enby|nonbinary|non-binary|lesbian|gay)\b)"), sincere(fixed("trans (unspecified)")), h()),
        said("gender", concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n] *)being (?:trans|transgender)\b(?![-'/])(?! (?:\w+ )?(?:woman|girl|man|guy|people|is|isn't)\b)|\bas an? (?:trans|transgender) (?:person|individual|human|adult|teen|kid|enby)\b"), alone(fixed("trans (unspecified)")), h()),
        said("gender", &format!(r"{IM} (?:(?:also|just|still|actually|a|an) ){{0,2}}transsexual\b(?! (?:people|woman|man|women|men)\b)|\bas an? transsexual\b(?! (?:people|woman|man)\b)"), fixed("transsexual"), h()),
        said("trans_status", &format!(r"{IM} (?:a |an |also |now |just )?(?:detrans|detransitioner|detransitioned|detransitioning)\b|\bi (?:have |'ve |had )?(?:recently |since |already |eventually )?detransitioned\b|\bas an? detrans(?:itioner)?\b"), fixed("detransitioned"), h()),
        said("gender", &format!(r"(?:{IM}|(?:^{flair}|[.!?\n] *)being) (?:an? )?(?:\d{{2}} ?(?:yo |y/o |year old )?)?(?:(?:white|black|straight|gay|bi|lesbian|young|old|het|hetero|middle aged) )?(?:cis|cisgender|cisgendered)[- ]?(?:het(?:ero)?(?:sexual)?[- ])?(woman|girl|female|lady|gal|man|guy|male|dude|boy|bloke)\b(?!'s| (?:people|perspective)\b)", flair = claimcore::flair!()), sincere(cis), h()),
        said("gender", &format!(r"{IM} (?:(?:a|also|just|100%|fully|totally) )*(?:cis|cisgender|cishet|cis het|cis-het)\b(?![-'])(?! (?:\w+ )?(?:woman|women|girl|female|lady|gal|man|men|guy|male|dude|boy|people|folks|f|m)\b)"), sincere(cis), h()),
        said("gender", concat!(r"(?:^", claimcore::flair!(), r"|(?<=[\n(\[|/,]))\s*(?:\d{2}\s*,?\s*)?(?:cis|cisgender)[- ]?(f|m|female|male)\b(?=\s*(?:[,;|/)\]\n.!]|$))"), alone(mine(cis)), sh()),
        said("gender", &format!(r"{IM} (?:(?:probably|definitely|still|just|totally) )?an egg(?=\s*(?:[.!,)]|$))"), |m: &Match| if TRANS_TEXT.test(m.string) { Some("egg".to_string()) } else { None }, h()),
    ]
}

