use crate::*;
use claimcore::*;
use std::sync::LazyLock;

static SPOKEN: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(claimcore::flair!(), r"\W*(?:i'm|im|i am)\b")));
static MEASURE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\s*(?:(?!in\b){UNITS}\b|\d{{1,2}}\s?s\b|(?:a|per) (?:year|season|week|month)\b|away\b|(?:fee|fees|deal|transfer|contract|budget|views|plays|streams|subscribers|followers)\b)")));
static HERE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\W{0,2}(?:here|hmu|lmk|dm me)\b"));
static THIS_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bthis $"));
static MY_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bmy\s?[\(\[]$"));
static AGE_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bage\s*[:=-]\s*$"));
static UNIT_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\s*{UNITS}")));
static ADDRESSED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:you|your|u|ur)\b"));
static LEADING_AGE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(claimcore::flair!(), r"\W{0,3}\d{2}(?![\d%.,'/:-])")));
static LEADING_TAG: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(claimcore::flair!(), r"(?:\W*\d{2},?\s|\W*[\[\(]\d{2}[\]\)])")));
static DEGREES: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:\(\s*-?\d|°|degrees\b)|\s+(?:there|outside|inside|indoors)\b"));
static FLAIR: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"^", claimcore::flair!(), r"([^\n?]{1,60})$")));
static FLAIR_WORD: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w-])(non[- ]?binary|enby|agender|genderfluid|genderqueer|demigirl|demiboy|bigender|transfem|transmasc|trans (?:woman|girl|man|guy|frau)|transwoman|transman|mtf|ftm|male|female|lesbian|gay|bisexual|bi|pansexual|asexual|aroace|queer|demisexual|omnisexual|sapphic)(?![\w-])"));
static FLAIR_TOKEN: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\W\d_]+"));
static FLAIR_FILLER: LazyLock<Re> = LazyLock::new(|| Re::new(r"^(?:non|binary|enby|agender|genderfluid|genderqueer|demigirl|demiboy|bigender|transfem|transmasc|trans|transgender|woman|girl|man|guy|frau|transwoman|transman|mtf|ftm|male|female|lesbian|gay|bisexual|bi|pansexual|asexual|aroace|ace|aro|queer|demisexual|omnisexual|sapphic|fem|femme|masc|cis|he|him|his|she|her|they|them|it|its|any|all|pronouns|xe|xem|flag|pride|irl|lurker|and|or|also|proud|i|im|m|am)$"));
static FLAIR_GENDERS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("nonbinary", "nonbinary"), ("non-binary", "nonbinary"), ("non binary", "nonbinary"), ("enby", "nonbinary"), ("agender", "agender"), ("genderfluid", "genderfluid"), ("genderqueer", "genderqueer"),
    ("demigirl", "demigirl"), ("demiboy", "demiboy"), ("bigender", "bigender"), ("transfem", "transfem"), ("transmasc", "transmasc"), ("trans woman", "trans woman"), ("trans girl", "trans woman"),
    ("trans frau", "trans woman"), ("transwoman", "trans woman"), ("mtf", "trans woman"), ("trans man", "trans man"), ("trans guy", "trans man"), ("transman", "trans man"), ("ftm", "trans man"),
    ("male", "man"), ("female", "woman"),
]));
static FLAIR_ORIENTATIONS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("lesbian", "lesbian"), ("gay", "gay"), ("bisexual", "bisexual"), ("bi", "bisexual"), ("pansexual", "pansexual"), ("asexual", "asexual"), ("aroace", "asexual"), ("queer", "queer"),
    ("demisexual", "demisexual"), ("omnisexual", "omnisexual"), ("sapphic", "sapphic"),
]));
static CROWD_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r" (?:\w+ ){{0,2}}{CROWD}")));

pub fn force() {
    LazyLock::force(&FLAIR_GENDERS);
    LazyLock::force(&FLAIR_ORIENTATIONS);
    for re in [&FLAIR, &FLAIR_WORD, &FLAIR_TOKEN, &FLAIR_FILLER, &DEGREES, &SPOKEN, &MEASURE_AFTER, &HERE_AFTER, &THIS_BEFORE, &MY_BEFORE, &AGE_BEFORE, &UNIT_AFTER, &ADDRESSED, &LEADING_AGE, &LEADING_TAG, &CROWD_AFTER] {
        LazyLock::force(re);
    }
}

fn color_of(word: Option<&[char]>) -> Option<String> {
    let key = st(word?);
    ETHNICITIES.get(&key).or_else(|| COLORS.get(&key)).map(|v| v.to_string())
}

fn attached(lowered: &[char], end: usize, start: usize, automatic: bool, found: &mut Found) {
    if let Some(color) = COLORED_AFTER.at(lowered, end) {
        if let Some(value) = color_of(color.group(1)) {
            found.set("ethnicity", value, start);
        }
    }
    if !automatic {
        if let Some(orientation) = ORIENTED_AFTER.at(lowered, end) {
            if let Some(value) = get(&ORIENTATIONS, orientation.group(1)) {
                found.set("sexual_orientation", value, start);
            }
        }
    }
}

fn looking(lowered: &[char], automatic: bool, found: &mut Found) {
    if !lowered.contains(&'4') {
        return;
    }
    for m in LOOKING.iter(lowered) {
        let start = m.start();
        let whole = m.text();
        if !(owned(lowered, start) || ((whole.contains(&'[') || whole.contains(&'(')) && start < 300 && !desired_by(lowered, start, &DESIRED))) {
            continue;
        }
        if let Some(value) = get(&POSTERS, m.group(2)) {
            found.set("gender", value, start);
        }
        attached(lowered, m.end(), start, automatic, found);
        let age = ages(either(&m, &[1, 5]));
        if let Some(age) = &age {
            found.set("age", age, start);
        }
    }
}

fn aged(lowered: &[char], automatic: bool, found: &mut Found) {
    let Some(paired) = PAIR.find(lowered) else { return };
    let played = GAME.find(lowered).map_or(lowered.len(), |m| m.start());
    for m in AGED.iter_in(lowered, paired.start().saturating_sub(8), played) {
        let start = m.start();
        if (m.group(2).map_or(false, |g| eq(g, "m")) && MEASURE_AFTER.at(&lowered[m.end()..], 0).is_some()) || DEGREES.at(&lowered[m.end()..], 0).is_some() || (m.nonempty(3).is_some() && chassis(lowered, m.start(), m.end())) {
            continue;
        }
        let (age, letter) = if m.nonempty(1).is_some() { (m.group(1), m.group(2)) } else { (m.group(4), m.group(3)) };
        let Some(age) = ages(age) else { continue };
        let bracketed = start > 0 && (lowered[start - 1] == '(' || lowered[start - 1] == '[');
        let owner = owned(lowered, start - bracketed as usize)
            || HERE_AFTER.at(&lowered[m.end()..], 0).is_some()
            || THIS_BEFORE.test(before(lowered, start, 6))
            || (bracketed && !OTHERS.test(&lowered[start.saturating_sub(25)..start - 1]) && (start < 60 || SPEAKER.test(tail_sentence(lowered, start, 80))))
            || MY_BEFORE.test(before(lowered, start, 5))
            || AGE_BEFORE.test(before(lowered, start, 8));
        if owner || (!OTHERS.test(tail_sentence(lowered, start, 24)) && FIRST.test(sentence(lowered, start, m.end()))) {
            if let Some(value) = get(&POSTERS, letter) {
                found.set("gender", value, start);
            }
        }
        if owner {
            found.set("age", &age, start);
            attached(lowered, m.end(), start, automatic, found);
        }
    }
}

fn flaired(lowered: &[char], found: &mut Found) {
    let Some(flair) = FLAIR.at(lowered, 0) else { return };
    let (start, end) = flair.span(1).unwrap();
    let tokens: Vec<_> = FLAIR_TOKEN.iter_in(lowered, start, end).collect();
    if tokens.len() > 5 || tokens.iter().any(|token| !FLAIR_FILLER.test(token.text())) {
        return;
    }
    for m in FLAIR_WORD.iter_in(lowered, start, end) {
        let word = st(m.group(1).unwrap());
        if let Some(value) = FLAIR_GENDERS.get(&word) {
            found.set("gender", *value, m.start());
        }
        if let Some(value) = FLAIR_ORIENTATIONS.get(&word) {
            found.set("sexual_orientation", *value, m.start());
        }
    }
}

pub fn tags(_text: &[char], lowered: &[char], found: &mut Found) {
    if !BOT_TEXT.test(lowered) {
        flaired(lowered, found);
    }
    if !DIGIT.test(lowered) && SPOKEN.at(lowered, 0).is_none() {
        return;
    }
    let automatic = BOT_TEXT.test(lowered);
    looking(lowered, automatic, found);
    aged(lowered, automatic, found);
    for m in WORDED.iter(lowered) {
        if owned(lowered, m.start()) && UNIT_AFTER.at(&lowered[m.end()..], 0).is_none() {
            if let Some(age) = ages(either(&m, &[1, 4])) {
                if let Some(value) = get(&GENDERS, either(&m, &[2, 3])) {
                    found.set("gender", value, m.start());
                }
                found.set("age", age, m.start());
            }
        }
    }
    for m in BRACKETED.iter(lowered) {
        if owned(lowered, m.start()) {
            if let Some(age) = ages(either(&m, &[1, 3, 6, 8])) {
                if let Some(value) = get(&GENDERS, either(&m, &[2, 4, 5, 7])) {
                    found.set("gender", value, m.start());
                }
                found.set("age", age, m.start());
            }
        }
    }
    for m in OPENING.iter(lowered) {
        if m.group(2).is_some_and(|g| g.len() == 1) && (lowered.get(m.end()) == Some(&'-') || chassis(lowered, m.start(), m.end())) {
            continue;
        }
        if let Some(value) = get(&GENDERS, either(&m, &[2, 3])) {
            found.set("gender", value, m.start());
        }
    }
    let first_line = &lowered[..line_end(lowered, 0)];
    for m in CLOSING.iter(first_line) {
        if owned(lowered, m.start()) && !ADDRESSED.test(before(lowered, m.start(), 120)) {
            if let Some(age) = ages(m.group(1)) {
                found.set("age", age, m.start());
            }
        }
    }
    if let Some(m) = START.at(lowered, 0) {
        if let Some(age) = ages(m.group(1)) {
            found.set("age", age, 0);
        }
    }
    if let Some(m) = LEADING_AGE.at(lowered, 0) {
        if let Some(color) = COLORED_AFTER.at(lowered, m.end()) {
            if let Some(value) = color_of(color.group(1)) {
                found.set("ethnicity", value, 0);
            }
        }
    }
    let tagged = (lowered[..lowered.len().min(300)].contains(&'4') && LOOKING.test_in(lowered, 0, 300))
        || AGED.test_in(lowered, 0, 120)
        || WORDED.test_in(lowered, 0, 120)
        || BRACKETED.test_in(lowered, 0, 120)
        || LEADING_TAG.at(lowered, 0).is_some()
        || YEARS_OLD.test_in(lowered, 0, 80)
        || SIZED.test_in(lowered, 0, 120)
        || COLORED.test_in(lowered, 0, 120);
    let signed = tagged || found.any("age");
    if tagged && !automatic {
        for m in ORIENTED.iter_in(lowered, 0, 1500) {
            let start = m.start();
            if !desired(lowered, start) && !PARTY.test(before(lowered, start, 24)) && !THIRD.test(tail_sentence(lowered, start, 80)) && CROWD_AFTER.at(&lowered[m.end()..], 0).is_none() {
                if let Some(value) = get(&ORIENTATIONS, m.group(1)) {
                    found.set("sexual_orientation", value, start);
                }
            }
        }
    }
    if signed {
        for m in ETHNIC.iter(lowered) {
            let start = m.start();
            if !PARTY.test(before(lowered, start, 24)) && !desired(lowered, start) && !THIRD.test(tail_sentence(lowered, start, 80)) {
                let key = either(&m, &[1, 2]).map(st).unwrap_or_default();
                let value = ETHNICITIES.get(&key).or_else(|| m.group(2).and_then(|g| COLORS.get(&st(g))));
                if let Some(value) = value {
                    found.set("ethnicity", *value, start);
                }
            }
        }
    }
}
