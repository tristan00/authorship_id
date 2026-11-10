use crate::*;
use std::collections::HashMap;
use std::sync::LazyLock;

const ATTRIBUTE: &str = "school_attended";
const LONGEST: usize = 8;
const VERB: &str = r"\bi(?: (?:also|just|recently|finally|actually|originally|eventually|currently|now|still))? ";
const AM: &str = r"\b(?:i'm|im|i am)(?: (?:also|just|currently|now|still|actually|officially))? ";
const DEGREE: &str = r"(?:undergrad|undergraduate|bachelor'?s|bachelors|masters?|master's|phd|ph\.d|doctorate|mba|bsc|ba|bs|ms|msc|ma|jd|md|llb|llm|btech|b\.tech|mtech|degree|diploma|residency|postdoc|grad school|graduate school|law school|med school)";

pub(crate) struct School {
    value: &'static str,
    common: bool,
}

pub(crate) static SCHOOLS: LazyLock<HashMap<&'static str, School>> = LazyLock::new(|| {
    timed("work.schools", || {
        let data: &'static str = Box::leak(data_file("schools.tsv").into_boxed_str());
        data.lines()
            .skip(1)
            .map(|line| {
                let mut parts = line.split('\t');
                let (key, value, common) = (parts.next().unwrap(), parts.next().unwrap(), parts.nth(1).unwrap());
                (key, School { value, common: common == "1" })
            })
            .collect()
    })
});

static STATED: LazyLock<Re> = LazyLock::new(|| {
    Re::new(concat!(
        r"\s*(?:$|[.,!;:)(\n]|\s-\s|\b(?:and|but|so|since|now|currently|atm|rn|lol|too|myself|where|which|in|as|majoring|studying|on (?:a )?(?:full )?scholarship|if (?:that|it) (?:helps|matters)|",
        r"for (?:undergrad|undergraduate|grad school|graduate school|college|uni|university|law school|med school|my (?:undergrad|degree|bachelor'?s|masters?|master's|phd|mba)|a (?:year|semester|couple|few)|\d|two|three|four|five)\b))"
    ))
});
static ROLE: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?: [a-z&-]+){0,2}? (?:(alum|alumnus|alumna|alumni|grad|graduate)|student|undergrad|freshman|sophomore|junior|senior|[123]l)\b"));
static SIGNED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?: [a-z&-]+)? (?:alum|alumnus|alumna|grad|graduate)(?: here\b|(?=\s*(?:$|[.,!;:)(\n])))|,? (?:class of '?(?:19|20)?\d\d|'(?:[0-2]\d|9\d))(?=\s*(?:$|[.,!;:)(|\n]))"));
static GERUND: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+[a-z]+ing\b"));
static HERE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bhere\b"));
static FIRST: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i've|ive|my|me)\b"));

fn spans(text: &[char], start: usize) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    let mut i = start;
    while out.len() < LONGEST && i < text.len() && is_word(text[i]) {
        let a = i;
        while i < text.len() && is_word(text[i]) {
            i += 1;
        }
        out.push((a, i));
        let gap = i;
        while i < text.len() && i - gap < 3 && matches!(text[i], ' ' | '-' | ',' | '\'' | '&' | '.' | '/') {
            i += 1;
        }
    }
    out
}

fn named(text: &[char], start: usize) -> Option<(&'static School, usize, bool)> {
    let found = spans(text, start);
    for size in (1..=found.len()).rev() {
        let key = found[..size].iter().map(|&(a, b)| st(&text[a..b])).collect::<Vec<_>>().join(" ");
        if let Some((_, entry)) = SCHOOLS.get_key_value(key.as_str()) {
            let cased = original(text).is_some_and(|raw| found[..size].iter().all(|&(a, _)| is_upper_char(raw[a])));
            return Some((entry, found[size - 1].1, cased));
        }
    }
    None
}

fn followed(m: &Match, strong: bool) -> Option<String> {
    let text = m.string;
    let (entry, end, cased) = named(text, m.end())?;
    if entry.common && !(strong && cased) || STATED.at(text, end).is_none() && !(strong && GERUND.at(text, end).is_some()) || question(text, end) {
        return None;
    }
    Some(entry.value.to_string())
}

fn role(m: &Match) -> Option<String> {
    let text = m.string;
    let (entry, end, cased) = named(text, m.end())?;
    let found = ROLE.at(text, end)?;
    let sentence = next_mark(text, found.end(), ".!?\n");
    if entry.common && !(cased && found.group(1).is_some()) || question(text, found.end()) || starts_at(text, m.start(), "as") && !FIRST.test_in(text, found.end(), sentence) {
        return None;
    }
    Some(entry.value.to_string())
}

fn signed(m: &Match) -> Option<String> {
    let text = m.string;
    let (entry, end, cased) = named(text, m.end())?;
    let found = SIGNED.at(text, end)?;
    let line = (line_start(text, m.start()), line_end(text, found.end()));
    if entry.common && !cased || !(HERE.test_in(text, end, found.end()) || FIRST.test_in(text, line.0, line.1)) {
        return None;
    }
    Some(entry.value.to_string())
}

pub(crate) fn rules() -> Vec<Rule> {
    let strong = [
        format!(r"{VERB}(?:graduated|graduate) from (?:the )?"),
        format!(r"{VERB}(?:attend|attended|transferred to|transfered to|studied at|study at|enrolled at|enrolled in) (?:the )?"),
        format!(r"{VERB}(?:go|went|attend|attended|transferred) to (?:school|college|uni|university|grad school|graduate school|law school|med school|undergrad) at (?:the )?"),
        format!(r"{VERB}(?:studied|study) (?:[\w-]+ ){{1,3}}?at (?:the )?"),
        format!(r"{VERB}(?:did|completed|finished|got|earned|received|have|hold) (?:my |a |an |both )?(?:[\w'-]+ ){{0,2}}?{DEGREE}(?: degree)? (?:at|from) (?:the )?"),
        format!(r"{AM}(?:attending|studying at|enrolled at|enrolled in|an? (?:[\w'-]+ ){{0,3}}?(?:student|undergrad|freshman|sophomore|junior|senior|alum|alumnus|alumna|graduate|grad) (?:here )?(?:at|of|from)) (?:the )?"),
        r"(?:^(?:r/\w+:\s*)?|[.!?\n]\s*)(?:currently |now )?(?:studying|enrolled) at (?:the )?".to_string(),
        r"\bmy (?:current )?(?:uni|university|college|school|alma mater)(?:'s| is| was) (?:the )?".to_string(),
    ];
    let weak = [
        format!(r"{VERB}(?:go|went) to (?:the )?"),
        format!(r"{AM}at (?:the )?"),
        format!(r"{AM}an? (?:[\w'-]+ ){{0,3}}?student (?:here )?in (?:the )?"),
        r"(?:^(?:r/\w+:\s*)?|\n)[^\w\n]*(?:university|uni|college|school|alma mater|education)[^\w\n]{0,4}?[:=][^\w\n]{0,4}(?:the )?".to_string(),
    ];
    let mut out: Vec<Rule> = Vec::new();
    for pattern in &strong {
        out.push(said(ATTRIBUTE, pattern, Box::new(|m| followed(m, true)), &SELF_HEDGE));
    }
    for pattern in &weak {
        out.push(said(ATTRIBUTE, pattern, Box::new(|m| followed(m, false)), &SELF_HEDGE));
    }
    let roles = r"\b(?:i'm|im|i am|as) (?:an? )(?:current |proud |former |recent |fellow )?(?=[^\n.!?,]{2,60}?\b(?:alum|alumnus|alumna|alumni|grad|graduate|student|undergrad|freshman|sophomore|junior|senior|[123]l)\b)";
    out.push(needs(said(ATTRIBUTE, roles, Box::new(role), &SELF_HEDGE), &["alum", "grad", "student", "freshman", "sophomore", "junior", "senior", "1l", "2l", "3l"]));
    let lines = r"(?:^(?:r/\w+:\s*)?|[\n(|•]\s*|[.!?]\s+)(?:an? |fellow |proud |another )?(?=[^\n.!?]{2,60}?(?:\b(?:alum|alumnus|alumna|grad|graduate|class of)\b|'\d\d\b))";
    out.push(needs(said(ATTRIBUTE, lines, Box::new(signed), &SELF_HEDGE), &["alum", "grad", "class of", "'1", "'2", "'9"]));
    out
}
