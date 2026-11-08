use crate::*;
use claimcore::*;
use std::sync::LazyLock;

static SPOKEN: LazyLock<Re> = LazyLock::new(|| Re::new(r"\W*(?:i'm|im|i am)\b"));
static MEASURE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\s*(?:(?!in\b){UNITS}\b|\d{{1,2}}\s?s\b|(?:a|per) (?:year|season|week|month)\b|away\b)")));
static HERE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\W{0,2}(?:here|hmu|lmk|dm me)\b"));
static THIS_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bthis $"));
static MY_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bmy\s?[\(\[]$"));
static AGE_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bage\s*[:=-]\s*$"));
static UNIT_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\s*{UNITS}")));
static ADDRESSED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:you|your|u|ur)\b"));
static LEADING_AGE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\W{0,3}\d{2}(?![\d%.,'/:-])"));
static LEADING_TAG: LazyLock<Re> = LazyLock::new(|| Re::new(r"\W*\d{2},?\s|\W*[\[\(]\d{2}[\]\)]"));
static RANGE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:-|–|to|or)\s*\d"));
static CROWD_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r" (?:\w+ ){{0,2}}{CROWD}")));

pub fn force() {
    for re in [&SPOKEN, &MEASURE_AFTER, &HERE_AFTER, &THIS_BEFORE, &MY_BEFORE, &AGE_BEFORE, &UNIT_AFTER, &ADDRESSED, &LEADING_AGE, &LEADING_TAG, &RANGE_AFTER, &CROWD_AFTER] {
        LazyLock::force(re);
    }
}

fn body_of(word: Option<&[char]>) -> Option<String> {
    let key = st(word?);
    BODIES.get(&key).or_else(|| SHAPES.get(&key)).map(|v| v.to_string())
}

fn color_of(word: Option<&[char]>) -> Option<String> {
    let key = st(word?);
    ETHNICITIES.get(&key).or_else(|| COLORS.get(&key)).map(|v| v.to_string())
}

fn attached(lowered: &[char], end: usize, start: usize, automatic: bool, found: &mut Found) {
    if let Some(body) = ATTACHED.at(lowered, end) {
        if let Some(value) = body_of(body.group(1)) {
            found.set("body_type", value, start);
        }
    }
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

fn height(feet: &[char], inches: i64) -> String {
    rounded(((int(feet) * 12 + inches) as f64) * 2.54)
}

fn metric(m: &Match) -> String {
    match m.group(1) {
        Some(cm) if !cm.is_empty() => st(cm),
        _ => format!("1{}", st(either(m, &[2, 3]).unwrap_or(&[]))),
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
        let poster = m.group(2).unwrap_or(&[]);
        let extra = m.nonempty(3).is_some();
        let target = m.group(4).unwrap_or(&[]);
        if !automatic && eq(poster, "m") && !extra && eq(target, "m") && !CURIOUS.test_in(lowered, 0, 1500) {
            found.set("sexual_orientation", "gay", start);
        }
        if !automatic && age.is_some() && (eq(poster, "m") || eq(poster, "f")) && !extra {
            let (other, opposite) = if eq(poster, "m") { ("f", &*OPPOSITE_M) } else { ("m", &*OPPOSITE_F) };
            if eq(target, other) && !QUEER.test_in(lowered, 0, 1500) && opposite.test_in(lowered, m.end(), 1500) {
                found.set("sexual_orientation", "straight", start);
            }
        }
    }
}

fn aged(lowered: &[char], automatic: bool, found: &mut Found) {
    let Some(paired) = PAIR.find(lowered) else { return };
    for m in AGED.iter_in(lowered, paired.start().saturating_sub(8), lowered.len()) {
        let start = m.start();
        if m.group(2).map_or(false, |g| eq(g, "m")) && MEASURE_AFTER.at(&lowered[m.end()..], 0).is_some() {
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

pub fn tags(_text: &[char], lowered: &[char], found: &mut Found) {
    if !DIGIT.test(lowered) && SPOKEN.at(lowered, 0).is_none() {
        return;
    }
    let automatic = BOT_TEXT.test(lowered);
    looking(lowered, automatic, found);
    aged(lowered, automatic, found);
    for m in WORDED.iter(lowered) {
        if owned(lowered, m.start()) && UNIT_AFTER.at(&lowered[m.end()..], 0).is_none() {
            if let Some(age) = ages(either(&m, &[1, 4])) {
                found.set("gender", st(either(&m, &[2, 3]).unwrap_or(&[])), m.start());
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
    let played = GAME.find(lowered).map_or(lowered.len(), |m| m.start());
    let tagged = (lowered[..lowered.len().min(300)].contains(&'4') && LOOKING.test_in(lowered, 0, 300))
        || AGED.test_in(lowered, 0, 120)
        || WORDED.test_in(lowered, 0, 120)
        || BRACKETED.test_in(lowered, 0, 120)
        || LEADING_TAG.at(lowered, 0).is_some()
        || YEARS_OLD.test_in(lowered, 0, 80)
        || SIZED.test_in(lowered, 0, 120)
        || COLORED.test_in(lowered, 0, 120);
    let signed = tagged || found.any("age");
    let speaking = signed || SPOKEN.at(lowered, 0).is_some();
    if speaking || AD.test(line(lowered, 0)) {
        for m in DESCRIBED.iter(lowered) {
            let (s1, e1) = m.span(1).unwrap();
            let word = m.group(1).unwrap();
            let before_word = before(lowered, s1, 24);
            if (STURDY.contains(st(word).as_str()) || !(GIRTH.test(before_word) || PHALLIC.at(lowered, e1).is_some())) && !PARTY.test(before_word) && !desired(lowered, s1) {
                if let Some(value) = bodied(lowered, s1, word) {
                    found.set("body_type", value, m.start());
                }
            }
        }
        for m in SHAPED.iter(lowered) {
            let (s1, e1) = m.span(1).unwrap();
            let word = m.group(1).unwrap();
            if !WANTED.test_in(lowered, m.start().saturating_sub(20), m.start())
                && (STURDY.contains(st(word).as_str()) || !(GIRTH.test(before(lowered, s1, 24)) || PHALLIC.at(lowered, e1).is_some()))
                && !desired(lowered, s1)
            {
                if let Some(value) = bodied(lowered, s1, word) {
                    found.set("body_type", value, m.start());
                }
            }
        }
    }
    if !speaking {
        for m in METRIC.iter_in(lowered, 0, played) {
            let start = m.start();
            if (owned(lowered, start) || FIRST.test(sentence(lowered, start, m.end())) || WEIGHED.test(line(lowered, start)))
                && !desired(lowered, start)
                && !COMPARED.test(tail_sentence(lowered, start, 25))
            {
                found.set("height", metric(&m), start);
            }
        }
        for m in STATURE.iter_in(lowered, 0, played) {
            let start = m.start();
            let Some(inches) = m.nonempty(2).or(m.nonempty(3)) else { continue };
            let inches = int(inches);
            if inches < 12
                && (owned(lowered, start) || FIRST.test(sentence(lowered, start, m.end())) || WEIGHED.test(line(lowered, start)))
                && !desired(lowered, start)
                && !COMPARED.test(tail_sentence(lowered, start, 25))
                && RANGE_AFTER.at(&lowered[m.end()..], 0).is_none()
            {
                found.set("height", height(m.group(1).unwrap(), inches), start);
            }
        }
    } else {
        if tagged && !automatic {
            for m in ORIENTED.iter_in(lowered, 0, 1500) {
                let start = m.start();
                if !desired(lowered, start) && !PARTY.test(before(lowered, start, 24)) && CROWD_AFTER.at(&lowered[m.end()..], 0).is_none() {
                    if let Some(value) = get(&ORIENTATIONS, m.group(1)) {
                        found.set("sexual_orientation", value, start);
                    }
                }
            }
        }
        if signed {
            for m in ETHNIC.iter(lowered) {
                let start = m.start();
                if !PARTY.test(before(lowered, start, 24)) && !desired(lowered, start) {
                    let key = either(&m, &[1, 2]).map(st).unwrap_or_default();
                    let value = ETHNICITIES.get(&key).or_else(|| m.group(2).and_then(|g| COLORS.get(&st(g))));
                    if let Some(value) = value {
                        found.set("ethnicity", *value, start);
                    }
                }
            }
            for m in HUNG.iter(lowered) {
                let start = m.start();
                if owned(lowered, start) && !PARTY.test(before(lowered, start, 24)) && !desired(lowered, start) {
                    let value = if eq(m.group(1).unwrap(), "bwc") { "white" } else { "black" };
                    found.set("ethnicity", value, start);
                }
            }
        }
        for m in HAIRED.iter(lowered) {
            let start = m.start();
            if !FOREIGN.test(&lowered[clause(lowered, start)..start]) && !unclaimed(lowered, start) {
                if let Some(value) = get(&HAIRS, either(&m, &[1, 2])) {
                    found.set("hair_color", value, start);
                }
            }
        }
        for m in METRIC.iter_in(lowered, 0, played) {
            let start = m.start();
            if !FOREIGN.test(tail_sentence(lowered, start, 25)) {
                found.set("height", metric(&m), start);
            }
        }
        for m in STATURE.iter_in(lowered, 0, played) {
            let start = m.start();
            let inches = m.nonempty(2).or(m.nonempty(3)).map_or(0, int);
            if inches < 12 && !FOREIGN.test(tail_sentence(lowered, start, 25)) {
                found.set("height", height(m.group(1).unwrap(), inches), start);
            }
        }
    }
}
