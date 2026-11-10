use crate::shared::*;
use claimcore::*;

const COUNT: &str = r"(\d{1,2}(?:\.5)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty)";
const ABOUT: &str = r"(?:almost |nearly |over |about |around |roughly |just over |just under |more than |going on |like |well over )?";

regex!(LATER, r"\b(?:was|were|had|had been|been married before)\s+(?:\w+\s+)?$");
regex!(SPLIT, r"\bdivorc|\bseparat(?:ed|ion)\b|\bwidow|\bex[- ]?(?:wife|husband|hubby|partner|bf|gf|boyfriend|girlfriend)\b");
regex!(OTHERS, r"\b(?:he|she|they|you|u|his|her|their|your|ur|parents|mom|dad|mum|grandparents|friends?|sister|brother|op)\b");

fn current(m: &Match) -> bool {
    let start = sentence_start(m);
    spoken(m) && !ENDED.test(m.string) && !BROKEN.test(m.string) && !SPLIT.test(m.string) && !LATER.test_in(m.string, back(m, 24), m.start()) && !OTHERS.test_in(m.string, start, m.start())
}

fn steady(m: &Match) -> V {
    if COUPLED.test(m.string) || !current(m) {
        None
    } else {
        stated(m, &STATED, || Some(DATING))
    }
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let SPAN = format!(r"{ABOUT}{COUNT}( and a half)?\+? ?(years?|yrs?|months?|mos?)(?:\s*(?:and|&) (a half|6 months))?\b");
    vec![
        needs(r("relationship_status", &format!(r"(?:\b(?:i|we)(?:'ve| have)?|\bmy (?:\w+ )?(?:boyfriend|girlfriend|bf|gf|partner) and i(?:'ve| have)?) been (?:together|dating) (?:for )?{SPAN}"), steady, self_hedge()), &["together", "dating"]),
    ]
}
