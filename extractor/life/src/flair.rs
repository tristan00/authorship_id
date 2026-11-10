use crate::shared::*;
use claimcore::*;

const FLAIR_MODS: &str = r"(?:roman|devout|practicing|practising|proud|reformed|traditional|born again|cultural|culturally|progressive|liberal|conservative|lgbtq\+?|lgbt\+?|gay|queer|trans|bi|lesbian|closeted|happy|secular|fellow|just|very|mostly|non-?denominational|sunni|shia|orthodox|evangelical|messianic|eastern|green|classical|social|democratic|libertarian|left|right|market|eco|christian|national|radical|far|neo|centre|center|fiscally|socially|economically|us|royal|british|canadian|australian|a|an)";
const FLAIR_STOPS: &str = r"(?:[,|/•;·+&()\[\]–—:!]|\p{So}|[\x{2600}-\x{27BF}\x{1F000}-\x{1FFFF}])";
regex!(FLAIR_BEFORE, format!(r"(?:[^\n]*{FLAIR_STOPS})?[ \t]*(?:{FLAIR_MODS}[ \t]+)*"));
regex!(PREFIX, concat!(r"\A", claimcore::flair!()));
regex!(FLAIR_AFTER, format!(r"[ \t]*(?:\z|{FLAIR_STOPS}|(?:lgbtq\+?|lgbt\+?|ally|here|convert|revert|woman|man|guy|girl|mom|dad)[ \t]*(?:\z|{FLAIR_STOPS}))"));

pub fn body(s: &[char]) -> Option<usize> {
    let body = PREFIX.at(s, 0).map_or(0, |m| m.end());
    (body <= 40 && s.len() - body <= 64 && !s.contains(&'\n')).then_some(body)
}

pub fn flair(m: &Match) -> bool {
    let s = m.string;
    let Some((start, end)) = m.span(1) else { return false };
    body(s).is_some_and(|body| FLAIR_BEFORE.fullmatch(s, body, start).is_some()) && FLAIR_AFTER.at(s, end).is_some()
}
