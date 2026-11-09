use crate::shared::*;
use claimcore::*;

const COUNT: &str = r"(\d{1,2}(?:\.5)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty)";
const ABOUT: &str = r"(?:almost |nearly |over |about |around |roughly |just over |just under |more than |going on |like |well over )?";
const PARTNER: &str = r"(?:wife|husband|hubby|partner|boyfriend|girlfriend|bf|gf|fianc[ée]e?|spouse|so|man|girl)";
const YEAR: &str = r"(19[5-9]\d|20[0-2]\d)";
const WORDS: [(&str, f64); 18] = [
    ("a", 1.0), ("an", 1.0), ("one", 1.0), ("two", 2.0), ("three", 3.0), ("four", 4.0), ("five", 5.0), ("six", 6.0), ("seven", 7.0), ("eight", 8.0), ("nine", 9.0), ("ten", 10.0),
    ("eleven", 11.0), ("twelve", 12.0), ("fifteen", 15.0), ("twenty", 20.0), ("thirty", 30.0), ("forty", 40.0),
];

regex!(LATER, r"\b(?:was|were|had|had been|been married before)\s+(?:\w+\s+)?$");
regex!(SPLIT, r"\bdivorc|\bseparat(?:ed|ion)\b|\bwidow|\bex[- ]?(?:wife|husband|hubby|partner|bf|gf|boyfriend|girlfriend)\b");
regex!(PAIR, r"\b(?:wife|husband|hubby|partner|boyfriend|girlfriend|bf|gf|married|marriage|spouse|fianc\w*)\b");
regex!(OTHERS, r"\b(?:he|she|they|you|u|his|her|their|your|ur|parents|mom|dad|mum|grandparents|friends?|sister|brother|op)\b");

fn span(m: &Match) -> Option<f64> {
    let number = st(m.group(1)?);
    let unit = st(m.group(3)?);
    let mut years = WORDS.iter().find(|(word, _)| *word == number).map(|(_, n)| *n).or_else(|| number.parse().ok())?;
    if m.nonempty(2).is_some() || m.nonempty(4).is_some() {
        years += 0.5;
    }
    if unit.starts_with("mo") {
        years /= 12.0;
    }
    (years >= 0.25 && years <= 70.0).then_some(years)
}

fn current(m: &Match) -> bool {
    let start = sentence_start(m);
    spoken(m) && !ENDED.test(m.string) && !BROKEN.test(m.string) && !SPLIT.test(m.string) && !LATER.test_in(m.string, back(m, 24), m.start()) && !OTHERS.test_in(m.string, start, m.start())
}

fn length(m: &Match) -> Option<String> {
    if current(m) && !STATED.test_in(m.string, back(m, 30), m.start()) {
        span(m).map(|years| years.to_string())
    } else {
        None
    }
}

fn labelled(m: &Match) -> Option<String> {
    let (a, b) = sentence(m);
    if SELF.test_in(m.string, a, b) && PAIR.test(m.string) {
        length(m)
    } else {
        None
    }
}

fn started(m: &Match) -> Option<String> {
    if current(m) && !STATED.test_in(m.string, back(m, 30), m.start()) {
        m.first_s()
    } else {
        None
    }
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
    let WE = format!(r"(?:\b(?:i|we)(?:'ve| have)?|\bmy (?:\w+ )?{PARTNER}(?: \([^)\n]{{1,10}}\))? and i(?: \([^)\n]{{1,10}}\))?(?:'ve| have)?|\b(?:he|she) and i(?:'ve| have)?) been (?:happily |officially |now )?");
    let TOGETHER = format!(r"(?:married|together|dating|with (?:my (?:\w+ )?{PARTNER}|him|her))");
    let BOTH = format!(r"(?:{WE}{TOGETHER}|\b(?:i'm|im|i am|we're|we are) (?:happily )?married)");
    let LABEL = r"(?:(?<![^\n.!?,;(|/-])|(?<=[\n.!?,;(|/-] )|\b(?:and|but|happily) )";
    vec![
        needs(rule("relationship_length", &format!(r"{BOTH} (?:for )?{SPAN}"), length, self_hedge()), &["married", "together", "dating", "with"]),
        needs(rule("relationship_length", &format!(r"{LABEL}(?:been )?(?:married|together) (?:for )?{SPAN}"), labelled, TAGGED), &["married", "together"]),
        needs(rule("relationship_length", &format!(r"{LABEL}{SPAN} (?:together|married|of marriage)\b(?! (?:before|ago|earlier)\b)"), labelled, TAGGED), &["together", "married", "marriage"]),
        needs(rule("relationship_start_year", &format!(r"{WE}{TOGETHER} since {YEAR}\b|{LABEL}(?:married|together) since {YEAR}\b|\b(?:i|we) (?:got )?married in {YEAR}\b"), started, self_hedge()), &["since", "married in"]),
        needs(r("relationship_status", &format!(r"(?:\b(?:i|we)(?:'ve| have)?|\bmy (?:\w+ )?(?:boyfriend|girlfriend|bf|gf|partner) and i(?:'ve| have)?) been (?:together|dating) (?:for )?{SPAN}"), steady, self_hedge()), &["together", "dating"]),
    ]
}
