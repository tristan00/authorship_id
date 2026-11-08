mod lexicon;
mod patterns;

use claimcore::*;
use lexicon::{entry, region_code, tokens, Entry, Node, LEXICON};
use patterns::*;
use std::sync::LazyLock;

use claimcore::HEDGE as DOUBT;

const LANGUAGES: &str = "english spanish french german italian portuguese dutch swedish norwegian danish finnish polish czech slovak hungarian romanian bulgarian greek croatian serbian \
russian ukrainian turkish arabic hebrew persian farsi hindi urdu bengali punjabi tamil telugu marathi gujarati malayalam kannada chinese mandarin cantonese japanese \
korean vietnamese thai tagalog filipino indonesian malay swahili afrikaans catalan basque icelandic estonian latvian lithuanian albanian";
const FEDERAL: [&str; 4] = ["united states", "canada", "australia", "india"];
const TITLE_REGIONS: [&str; 5] = ["united states", "canada", "australia", "india", "united kingdom"];

fn spoken(word: Option<&[char]>) -> Option<String> {
    let word = st(word?);
    LANGUAGES.split(' ').any(|language| language == word).then_some(word)
}

fn nation_of(word: Option<&[char]>) -> Option<&'static str> {
    LEXICON.nations.get(&st(word?)).copied()
}

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    vec![
        rule("nationality", &loose_nation(), |m| nation_of(m.group(1)).map(String::from), hedge()),
        rule("nationality", &as_nation(), |m| nation_of(m.group(1)).map(String::from), hedge()),
        rule("nationality", &as_nation_start(), |m| nation_of(m.group(1)).map(String::from), hedge()),
        rule("native_language", &spoken_pattern(), |m| spoken(m.nonempty(1).or(m.group(2))), hedge()),
        needs(rule("native_language", r"\b(?:my )?(?:first|native|mother) (?:language|tongue) is \**(\w+)\b|\b(\w+)\** is my (?:first|native|mother) (?:language|tongue)\b|\b(?:i'm|im|i am|as) (?:also |actually )?(?:an? )?native \**(\w+)\** speaker\b|\bnative \**(\w+)\** speaker here\b|\b(?:i'm|im|i am|as) an? native speaker of \**(\w+)\b|\b(\w+)\**\s*\(native\)|\bnative(?: language)?\s*[:=-]\s*\**(\w+)\b",
            |m| spoken(m.first()), hedge()), &["native", "language", "tongue"]),
        rule("native_language", r"\b(\w+) is the only language i (?:speak|know)\b|\bas (?:a )?native (\w+ )?speakers?\b",
            |m| if m.nonempty(1).is_some() { spoken(m.group(1)) } else if let Some(two) = m.nonempty(2) { spoken(Some(strip_space(two))) } else { Some("english".to_string()) }, self_hedge()),
    ]
});

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn init() {
    timed("location init", || {
        LazyLock::force(&LEXICON);
        LazyLock::force(&RULES);
        for pattern in patterns::all() {
            pattern.test(&[]);
        }
    });
}

#[derive(Clone, Copy, PartialEq)]
enum Title {
    No,
    Yes,
    Loose,
    Bare,
}

impl Title {
    fn truthy(self) -> bool {
        self != Title::No
    }
}

struct Spot {
    start: usize,
    end: usize,
    entry: Entry,
}

fn sentence(s: &[char], start: usize) -> usize {
    last_mark(s, start, ".!?\n")
}

fn upper_at(text: &[char], at: usize) -> bool {
    isupper(&text[at..at + 1])
}

fn lower_at(text: &[char], at: usize) -> bool {
    islower(&text[at..at + 1])
}

fn line_of(text: &[char], start: usize, end: usize) -> &[char] {
    &text[line_start(text, start)..line_end(text, end)]
}

fn fits(entry: &Entry, text: &[char], start: usize, end: usize) -> bool {
    let has_lower = || line_of(text, start, end).iter().any(|&c| islower(&[c]));
    if entry.flag == "code" {
        return isupper(&text[start..end]) && has_lower();
    }
    if entry.flag == "town" && isupper(&text[start..end]) {
        return false;
    }
    if entry.flag == "1" || entry.flag == "town" {
        return upper_at(text, start) && has_lower() && !OPENING.test_in(text, 0, start) && AREA.at(text, end).is_none();
    }
    true
}

fn gap(lowered: &[char], a: usize, b: usize) -> bool {
    a < b && b - a <= 3 && lowered[a..b].iter().all(|c| matches!(c, ' ' | '.' | '\'' | '-'))
}

fn join(lowered: &[char], a: usize, b: usize) -> bool {
    if a > b {
        return false;
    }
    let mut index = a;
    while index < b && is_space(lowered[index]) {
        index += 1;
    }
    if index < b && matches!(lowered[index], ',' | '(' | '/' | '–' | '-') {
        index += 1;
    }
    while index < b && is_space(lowered[index]) {
        index += 1;
    }
    index == b
}

fn longest(words: &[(usize, usize)], index: usize, lowered: &[char], first: Option<&Node>, name: &mut Vec<char>) -> (usize, Option<Entry>) {
    let nodes = &LEXICON.nodes;
    let mut node = first;
    let mut size = 1;
    let mut best = (0, None);
    name.clear();
    name.extend_from_slice(&lowered[words[index].0..words[index].1]);
    loop {
        let Some(current) = node else {
            return best;
        };
        if let Some(found) = current.entry {
            best = (size, Some(found));
        }
        if !current.prefix || index + size == words.len() {
            return best;
        }
        let (next_start, next_end) = words[index + size];
        name.push(' ');
        name.extend_from_slice(&lowered[next_start..next_end]);
        node = nodes.get(&name[..]);
        if node.is_none() || !gap(lowered, words[index + size - 1].1, next_start) {
            return best;
        }
        size += 1;
    }
}

fn within(head: &Entry, container: &Entry) -> Option<Entry> {
    if container.kind == "region" && head.kind == "city" {
        return Some(entry(head.kind, head.value, container.value, container.country, ""));
    }
    if container.kind == "country" {
        return Some(if head.country == container.country {
            *head
        } else {
            entry(head.kind, head.value, if head.kind == "region" { head.region } else { "" }, container.country, head.flag)
        });
    }
    None
}

fn national(lowered: &[char], start: usize, node: &Node) -> bool {
    node.nation_word || node.nation_lead && LEXICON.compound_nations.iter().any(|name| lowered[start..].starts_with(name))
}

fn digit_in(s: &[char], a: usize, b: usize) -> bool {
    a < b && s[a..b].iter().any(|&c| if c.is_ascii() { c.is_ascii_digit() } else { is_decimal(c) })
}

fn occurs(s: &[char], a: usize, b: usize, words: &[&str]) -> bool {
    (a..b).any(|at| words.iter().any(|word| ends_within(s, at, b, word)))
}

fn ends_within(s: &[char], at: usize, b: usize, word: &str) -> bool {
    let mut index = at;
    for c in word.chars() {
        if index >= b || s[index] != c {
            return false;
        }
        index += 1;
    }
    true
}

fn self_lead(lowered: &[char], line: usize, start: usize) -> bool {
    digit_in(lowered, line, start) || occurs(lowered, line, start, &["just a", "i'm a", "im a", "i am a"])
}

fn mentions(text: &[char], lowered: &[char]) -> (Vec<Spot>, bool) {
    let lexicon = &*LEXICON;
    let words = tokens(lowered);
    let mut spots: Vec<Spot> = Vec::new();
    let mut nationish = false;
    let mut name: Vec<char> = Vec::new();
    let mut index = 0;
    while index < words.len() {
        let (start, stop) = words[index];
        let hashed = start > 0 && lowered[start - 1] == '#';
        let node = lexicon.nodes.get(&lowered[start..stop]);
        if let Some(found) = node {
            nationish |= national(lowered, start, found);
        } else if !hashed {
            index += 1;
            continue;
        }
        let (mut size, mut found) = longest(&words, index, lowered, node, &mut name);
        if found.is_none() && hashed {
            if let Some(squashed) = lexicon.squashed.get(&lowered[start..stop]) {
                found = Some(*squashed);
                size = 1;
            }
        }
        let Some(mut current) = found else {
            index += 1;
            continue;
        };
        let end = words[index + size - 1].1;
        if !fits(&current, text, start, end) {
            index += 1;
            continue;
        }
        for &(inner_start, inner_stop) in &words[index + 1..index + size] {
            nationish |= lexicon.nodes.get(&lowered[inner_start..inner_stop]).is_some_and(|inner| national(lowered, inner_start, inner));
        }
        if current.flag == "code" {
            if let Some(last) = spots.last() {
                if let Some(local) = region_code(last.entry.country, &lowered[start..end]) {
                    current = entry("region", local, local, last.entry.country, "code");
                }
            }
        }
        let joined = match spots.last() {
            Some(last) if matches!(current.kind, "region" | "country") && matches!(last.entry.kind, "city" | "region") && join(lowered, last.end, start) => within(&last.entry, &current),
            _ => None,
        };
        if let Some(joined) = joined {
            let last = spots.last_mut().unwrap();
            last.end = end;
            last.entry = joined;
        } else if spots.last().is_some_and(|last| last.entry.kind == "country" && matches!(current.kind, "city" | "region") && current.country == last.entry.country && join(lowered, last.end, start)) {
            let last = spots.last_mut().unwrap();
            last.end = end;
            last.entry = entry(current.kind, current.value, if current.kind == "region" { current.region } else { "" }, current.country, current.flag);
        } else {
            spots.push(Spot { start, end, entry: current });
        }
        index += size;
    }
    (spots, nationish)
}

fn asked(lowered: &[char], end: usize) -> bool {
    let stop = next_mark(lowered, end, ".!?\n");
    stop < lowered.len() && lowered[stop] == '?' && stop - end < 60 && !lowered[end..stop].iter().any(|&c| c == ',' || c == ';')
}

fn hedged(lowered: &[char], opening: usize, end: usize) -> bool {
    DOUBTED.test_in(lowered, clause(lowered, opening), opening) || asked(lowered, end)
}

const STANCE_CUES: [&[&str]; 13] = [
    &["live", "living", "reside", "moved", "relocated", "settled", "based"],
    &["live", "living", "based", "located", "residing", "reside"],
    &["here", "we", "us", "from", "my ", "our "],
    &["vivo", "vivimos", "resido", "radico", "estoy", "estamos", "moro", "moramos", "wohne", "lebe", "habite", "je vis", "je réside", "j'vis", "me trouve", "abito", "risiedo", "woon", "wonen", "aquí", "aqui", "acá", "hier", "ici", "qui"],
    &["aus", "von"],
    &["i'm", "im", "we're", "we are", "iam", " am"],
    &["from"],
    &["soy", "somos", "sou", "stamme", "je suis", "je viens", "sono di", "vengo", "kom "],
    &["grew up", "raised", "born", "brought up", "growing up", "grown up", "hail from", "spent ", "native ", "home", "birth", "motherland", "nací", "naci", "nasci", "geboren", "né", "nato", "nata"],
    &["i'm", "im", "i am"],
    &[],
    &["from"],
    &["moved", "relocated", "decided to"],
];
const AGED: usize = 10;

static CUES: LazyLock<Vec<Vec<(Vec<char>, u16)>>> = LazyLock::new(|| {
    let mut buckets: Vec<Vec<(Vec<char>, u16)>> = vec![Vec::new(); 128];
    for (index, cues) in STANCE_CUES.iter().enumerate() {
        for cue in cues.iter() {
            let word = chars(cue);
            let bucket = &mut buckets[word[0] as usize];
            match bucket.iter_mut().find(|(known, _)| *known == word) {
                Some((_, bits)) => *bits |= 1 << index,
                None => bucket.push((word, 1 << index)),
            }
        }
    }
    buckets
});

fn cued(lowered: &[char], froms: &[usize; 13], start: usize) -> u16 {
    let buckets = &*CUES;
    let low = *froms.iter().min().unwrap();
    let mut mask = 0u16;
    for at in low..start {
        let c = lowered[at];
        if c.is_ascii() {
            for (word, bits) in &buckets[c as usize] {
                if at + word.len() <= start && lowered[at..at + word.len()] == word[..] {
                    for index in 0..13 {
                        if bits >> index & 1 == 1 && froms[index] <= at {
                            mask |= 1 << index;
                        }
                    }
                }
            }
            if c.is_ascii_digit() && froms[AGED] <= at {
                mask |= 1 << AGED;
            }
        } else if is_decimal(c) && froms[AGED] <= at {
            mask |= 1 << AGED;
        }
    }
    mask
}

fn stance(lowered: &[char], start: usize, end: usize, entry: &Entry) -> Option<&'static str> {
    let opening = clause(lowered, start).saturating_sub(1);
    let stances: [(&Re, &'static str); 13] = [(&LIVE, "residence"), (&BARE, "residence"), (&HERE, "local"), (&ABROAD, "local"), (&GERMAN, "aus"), (&BEING, "being"), (&FROM, "from"), (&LEFT, "from"),
        (&ORIGIN, "origin"), (&ROLE, "being"), (&AGED_IN, "being"), (&SELF_FROM, "from"), (&MOVED, "residence")];
    let mut froms = [opening; 13];
    froms[2] = start.saturating_sub(60);
    froms[AGED] = line_start(lowered, start).max(start.saturating_sub(70));
    let mask = cued(lowered, &froms, start);
    for (index, (pattern, kind)) in stances.into_iter().enumerate() {
        if mask >> index & 1 == 0 {
            continue;
        }
        if let Some(found) = pattern.search(lowered, froms[index], start) {
            if hedged(lowered, found.start(), end) {
                return None;
            }
            if kind == "being" {
                return if LATER.at(lowered, end).is_some() { None } else { Some("residence") };
            }
            return Some(kind);
        }
    }
    let line = line_start(lowered, start);
    if let Some(found) = if digit_in(lowered, line, start) && occurs(lowered, line, start, &["from"]) { TAG_FROM.search(lowered, line, start) } else { None } {
        if TITLE.test_in(lowered, line, start) && !ASKING.test_in(lowered, line, found.start()) && !hedged(lowered, found.start(), end) {
            return Some("from");
        }
    }
    if let Some(found) = if occurs(lowered, opening, start, &["moved", "relocated", "living", "based", "located", "residing", "currently", "now"]) { LOOSE.search(lowered, opening, start) } else { None } {
        if SUBJECTIVE.test_in(lowered, sentence(lowered, start), found.start()) {
            return if hedged(lowered, found.start(), end) { None } else { Some("residence") };
        }
    }
    if entry.kind == "country" {
        if let Some(found) = WHERE.at(lowered, end) {
            if !asked(lowered, found.end()) {
                return Some(if found.has(1) { "residence" } else if found.has(2) { "from" } else { "origin" });
            }
        }
    }
    if START.test_in(lowered, start.saturating_sub(12), start) && HERE_AFTER.at(lowered, end).is_some() {
        return Some("here");
    }
    if (starts_at(lowered, end, "-based") || starts_at(lowered, end, " based")) && SELF.test_in(lowered, start.saturating_sub(20), start) {
        return Some("residence");
    }
    if let Some(found) = LOCAL.at(lowered, end) {
        if LOCAL_LEAD.test_in(lowered, start.saturating_sub(40), start) {
            return Some(if found.group(1).is_some_and(|g| eq(g, "native")) { "origin" } else { "residence" });
        }
    }
    if HOMETOWN.at(lowered, end).is_some() {
        return Some("origin");
    }
    if (starts_at(lowered, end, "-born") || starts_at(lowered, end, " born")) && BORN.test_in(lowered, start.saturating_sub(20), start)
        || (starts_at(lowered, end, " ass ") || starts_at(lowered, end, " self ")) && ends_at(lowered, start, "my ")
    {
        return Some("born");
    }
    if CITIZEN_AFTER.at(lowered, end).is_some() && CITIZEN.test_in(lowered, start.saturating_sub(30), start) {
        return Some("citizen");
    }
    None
}

fn titled(text: &[char], lowered: &[char], start: usize, end: usize, entry: &Entry) -> Title {
    let opening = line_start(lowered, start);
    let closing = line_end(lowered, end);
    let hashed = start > 0 && lowered[start - 1] == '#';
    if hashed && entry.kind != "city" {
        return Title::Yes;
    }
    if closing - opening >= 250 || !digit_in(lowered, opening, closing) || !TITLE.test_in(lowered, opening, closing) {
        return Title::No;
    }
    if hashed {
        return Title::Yes;
    }
    let asking = ASKING.test_in(lowered, opening, start);
    let span = &text[start..end];
    let unlisted = entry.flag == "1" && !(span.contains(&' ') && istitle(span));
    if unlisted
        || asking && (entry.kind == "country" || entry.flag == "1" || {
            let after = TITLE.iter_in(lowered, opening, start).map(|tag| tag.end()).fold(opening, usize::max);
            ASKING.test_in(lowered, after, start)
        })
    {
        return Title::No;
    }
    let last = LAST.at_in(lowered, end, closing).is_some();
    if entry.flag == "1" {
        return if LEAD.test_in(lowered, opening, start) || last { Title::Yes } else { Title::No };
    }
    if !(LEAD.test_in(lowered, opening, start) || last) {
        return if opening == 0 && entry.kind != "country" && upper_at(text, start) && end - start >= 5 { Title::Loose } else { Title::No };
    }
    if entry.kind == "city" && !lowered[start..end].contains(&' ') && lower_at(text, start)
        && !(NEAR.test_in(lowered, start.saturating_sub(8), start) || TAG_LEAD.test_in(lowered, opening, start))
    {
        return if last { Title::Loose } else { Title::Bare };
    }
    if asking { Title::Loose } else { Title::Yes }
}

fn placed(prefix: &str, entry: &Entry, end: usize, found: &mut Found, whole: bool) {
    let (city, region, country) = if prefix == "origin" {
        ("origin_city", "origin_region", "origin_country")
    } else {
        ("residence_city", "residence_region", "residence_country")
    };
    if entry.kind == "city" {
        found.set(city, entry.value, end);
    }
    if matches!(entry.kind, "city" | "region")
        && !entry.region.is_empty()
        && (entry.kind == "region" || entry.country != "united kingdom")
        && !(entry.kind == "city" && (ADMINISTRATIVE.test(&chars(entry.region)) || prefix == "residence" && !FEDERAL.contains(&entry.country) && entry.region != entry.value))
    {
        found.set(region, entry.region, end);
    }
    if whole {
        found.set(country, entry.country, end);
    }
}

fn nation(lowered: &[char], start: usize, entry: &Entry, kind: Option<&str>, line_end: usize, tagged: bool, found: &mut Found) {
    let country = entry.country;
    match kind {
        Some("here") => {
            found.set("nationality", country, start);
            found.set("origin_country", country, start);
            found.set("residence_country", country, start);
        }
        Some("born") => {
            found.set("origin_country", country, start);
            found.set("nationality", country, start);
        }
        Some("citizen") => found.set("nationality", country, start),
        _ => {
            if tagged && start < line_end && !ASKING.test_in(lowered, 0, start) {
                found.set("nationality", country, start);
                found.set("origin_country", country, start);
            }
        }
    }
}

pub fn places(text: &[char], lowered: &[char], found: &mut Found) {
    let nationals: Vec<(String, usize)> = found.items.iter().filter(|(a, _, _)| a == "nationality").map(|(_, v, p)| (v.clone(), *p)).collect();
    for (value, position) in nationals {
        found.set("origin_country", value, position);
    }
    let (text, lowered) = if automated(lowered) {
        let Some(copy) = REPOST.find(lowered) else {
            return;
        };
        let stop = AUTOMATED.find_from(lowered, copy.end()).map_or(lowered.len(), |m| m.start());
        (&text[copy.end()..stop], &lowered[copy.end()..stop])
    } else {
        (text, lowered)
    };
    let (spots, nationish) = mentions(text, lowered);
    if spots.is_empty() {
        return;
    }
    let first_end = line_end(lowered, 0);
    let tagged = first_end < 150 && TITLE.test_in(lowered, 0, first_end);
    let mut residence: Vec<(Entry, usize, bool)> = Vec::new();
    let mut residence_from_origin: Vec<(Entry, usize, bool)> = Vec::new();
    let mut framed: Vec<(&'static str, usize)> = Vec::new();
    let mut peoples: Vec<&'static str> = Vec::new();
    let mut opened: Vec<(&'static str, usize)> = Vec::new();
    for spot in &spots {
        let (start, end) = (spot.start, spot.end);
        let mut current = spot.entry;
        let country = current.country;
        let line = line_start(lowered, start);
        let is_nation = current.kind == "nation";
        if is_nation
            && (TAG_BEFORE.test_in(lowered, line.max(start.saturating_sub(16)), start) || TAG_AFTER.at(lowered, end).is_some())
            && !ASKING.test_in(lowered, line, start)
        {
            framed.push((country, start));
        }
        if is_nation && CLOSES.at(lowered, end).is_some() && OPENS.test_in(lowered, start.saturating_sub(40), start) && !asked(lowered, end) && !opened.iter().any(|(c, _)| *c == country) {
            opened.push((country, start));
        }
        if is_nation && NATION_HERE.at(lowered, end).is_some() && !OTHERS_LEAD.test_in(lowered, start.saturating_sub(8), start) {
            framed.push((country, start));
        }
        if current.kind == "country" && CITIZEN_OF.test_in(lowered, line.max(start.saturating_sub(40)), start) {
            framed.push((country, start));
        }
        if matches!(current.kind, "nation" | "nations") {
            if let Some(lead) = GROUP.search(lowered, start.saturating_sub(30), start) {
                if GROUP_END.at(lowered, end).is_some() && !DOUBT.test_in(lowered, clause(lowered, lead.start()).max(lead.start().saturating_sub(40)), lead.start()) {
                    framed.push((country, lead.start()));
                }
            }
        }
        if current.kind == "nations" {
            continue;
        }
        if current.kind == "foreign" {
            if COPULA.test_in(lowered, start.saturating_sub(30), start) {
                framed.push((country, start));
            }
            continue;
        }
        if current.flag == "town" {
            let kind = if TOWN_LEAD.test_in(lowered, start.saturating_sub(30), start) { stance(lowered, start, end, &current) } else { None };
            if matches!(kind, Some("residence" | "local")) || kind.is_none() && TAG_LEAD.test_in(lowered, line, start) && titled(text, lowered, start, end, &current) == Title::Yes {
                residence.push((Entry { region: "", ..current }, end, false));
            } else if matches!(kind, Some("from" | "origin" | "born")) {
                found.set("origin_city", current.value, end);
            }
            continue;
        }
        let mut kind = stance(lowered, start, end, &current);
        if is_nation {
            nation(lowered, start, &current, kind, first_end, tagged, found);
            continue;
        }
        if current.kind == "people" {
            if kind == Some("here") || PEOPLE.test_in(lowered, start.saturating_sub(30), start) {
                let region = Entry { kind: "region", ..current };
                placed("origin", &region, end, found, true);
                if !peoples.contains(&country) {
                    peoples.push(country);
                }
                residence_from_origin.push((region, end, false));
            }
            continue;
        }
        let is_country = current.kind == "country";
        if matches!(kind, Some("here" | "aus")) && is_country {
            found.set("nationality", country, start);
        }
        if is_country && (digit_in(lowered, line, start) || occurs(lowered, line, start, &["country", "born and"])) {
            if let Some(home) = HOME_COUNTRY.search(lowered, line, start) {
                if !hedged(lowered, home.start(), end) {
                    framed.push((country, start));
                }
            }
        }
        if kind == Some("aus") && is_country {
            found.set("origin_country", country, start);
        }
        if kind.is_none() && TRADE.at(lowered, end).is_some() && lowered[start.saturating_sub(8)..start].contains(&'[') {
            kind = Some("residence");
        }
        if kind.is_none() && is_country && OPENER.test_in(lowered, start.saturating_sub(30), start) && OPENER_END.at(lowered, end).is_some() {
            kind = Some("from");
        }
        if kind.is_none() && is_country && self_lead(lowered, line, start) {
            if let Some(lead) = SELF_FROM_LEAD.search(lowered, line, start) {
                if !ASKING.test_in(lowered, sentence(lowered, start), start) && !hedged(lowered, lead.start(), end) {
                    kind = Some("from");
                }
            }
        }
        if kind.is_none() && self_lead(lowered, line, start) {
            if let Some(lead) = SELF_IN_LEAD.search(lowered, line, start) {
                if !ASKING.test_in(lowered, sentence(lowered, start), start)
                    && !TRIP.test_in(lowered, lead.start(), start)
                    && !hedged(lowered, lead.start(), end)
                    && LATER.at(lowered, end).is_none()
                {
                    kind = Some("residence");
                }
            }
        }
        let mut title = if kind.is_none() { titled(text, lowered, start, end, &current) } else { Title::No };
        if title.truthy() && TRIP.test_in(lowered, start.saturating_sub(200), start + 200) {
            title = Title::No;
        }
        let foreign = !TITLE_REGIONS.contains(&country);
        if foreign && current.kind == "city" && !upper_at(text, start) {
            continue;
        }
        if foreign && (current.kind == "region" || title == Title::Loose) {
            title = Title::No;
        }
        if kind.is_none() {
            if let Some((last, last_end, _)) = residence.last() {
                if last.country == country && CHAIN.fullmatch(lowered, *last_end, start).is_some() {
                    kind = Some("residence");
                }
            }
        }
        if kind.is_none() && !title.truthy() && current.kind == "city" {
            if let Some(host) = HOSTING.search(lowered, start.saturating_sub(20), start) {
                if !hedged(lowered, host.start(), end) && LATER.at(lowered, end).is_none() {
                    kind = Some("here");
                }
            }
        }
        if kind.is_none() && !title.truthy() && current.kind == "region" && LOCATION.test_in(lowered, start.saturating_sub(30), start) {
            kind = Some("residence");
        }
        if kind.is_none() && current.kind == "city" {
            if let Some(other) = HAILS.search(lowered, start.saturating_sub(30), start) {
                if !hedged(lowered, other.start(), end) && LATER.at(lowered, end).is_none() {
                    found.set("origin_city", current.value, end);
                }
            }
        }
        if kind == Some("residence") && LIFE.at(lowered, end).is_some() {
            placed("origin", &current, end, found, true);
        }
        if foreign && current.kind == "region" && matches!(kind, Some("residence" | "local" | "aus")) {
            continue;
        }
        if kind == Some("here") && current.kind == "city" || title == Title::Bare {
            current.region = "";
        }
        if matches!(kind, Some("residence" | "aus" | "local")) || kind == Some("here") && current.flag != "1" || kind.is_none() && title.truthy() {
            let whole = current.kind == "country" || !matches!(title, Title::Loose | Title::Bare) && kind != Some("aus") && !(title.truthy() && foreign);
            residence.push((current, end, whole));
        } else if kind == Some("from") {
            let whole = current.kind == "country" || !foreign;
            placed("origin", &current, end, found, whole);
            if current.kind == "country" {
                framed.push((country, start));
            }
            residence_from_origin.push((current, end, whole));
        } else if matches!(kind, Some("origin" | "born")) {
            placed("origin", &current, end, found, true);
            if kind == Some("born") && current.kind == "country" {
                framed.push((country, start));
            }
        } else if kind == Some("citizen") && current.kind == "country" {
            framed.push((country, start));
        }
    }
    let chosen: &[(Entry, usize, bool)] = if !residence.is_empty() { &residence } else { &residence_from_origin[..residence_from_origin.len().min(1)] };
    for (current, end, whole) in chosen {
        placed("residence", current, *end, found, *whole);
    }
    if !found.any("residence_country") {
        let mut nations: Vec<String> = found.values("nationality");
        for people in &peoples {
            nations.push(people.to_string());
        }
        nations.sort();
        nations.dedup();
        if nations.len() == 1 {
            found.set("residence_country", &nations[0], 0);
        }
    }
    let questioned = lowered.contains(&'?');
    let mut frames: Vec<Frame> = frames().to_vec();
    if questioned {
        frames.extend(asked_frames());
    }
    let numeric = digit_in(lowered, 0, lowered.len());
    for (frame, gates, national, digits) in frames {
        if national && !nationish || digits && !numeric || !gates.iter().any(|gate| claimcore::contains(lowered, gate)) {
            continue;
        }
        for found_match in frame.iter(lowered) {
            let at = found_match.start();
            if !DOUBT.test_in(lowered, clause(lowered, at).max(at.saturating_sub(40)), at) {
                if let Some(country) = nation_of(found_match.first()) {
                    framed.push((country, at));
                }
            }
        }
    }
    if nationish {
        for found_match in SELF_DESCRIBED.iter(lowered) {
            let opening = sentence(lowered, found_match.start());
            let named = found_match.start_of(1) as usize;
            if !ASKING.test_in(lowered, opening, named) && !DOUBT.test_in(lowered, opening, named) {
                if let Some(country) = nation_of(found_match.group(1)) {
                    framed.push((country, found_match.start()));
                }
            }
        }
    }
    if opened.len() == 1 {
        framed.push(opened[0]);
    }
    for (country, position) in framed {
        found.set("nationality", country, position);
    }
}

fn automated(lowered: &[char]) -> bool {
    let cue = |at: usize| match lowered[at] {
        'i' => starts_at(lowered, at, "i am a bot"),
        'p' => starts_at(lowered, at, "performed automatically") || starts_at(lowered, at, "please ") || starts_at(lowered, at, "post "),
        'm' => starts_at(lowered, at, "must "),
        _ => false,
    };
    (0..lowered.len()).any(cue) && AUTOMATED.test(lowered)
}
