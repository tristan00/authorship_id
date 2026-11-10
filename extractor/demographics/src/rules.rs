use crate::*;
use claimcore::*;
use std::sync::{LazyLock, OnceLock};

pub(crate) type Value = Box<dyn Fn(&Match) -> Option<String> + Send + Sync>;

static ORIENTATION_RANGE: OnceLock<(usize, usize)> = OnceLock::new();
static RETURNED: LazyLock<Re> = LazyLock::new(|| Re::new(r",? (?:i|i'm|im)\b"));
static OPENED_LINE: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^(?:r/\w+:\s*)?|[.!?\n] *)$"));
static TWO_DIGITS: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<!\d)\d\d(?!\d)"));
static LETTER_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w'/+-])[mf](?![\w'/+-])"));
static SPEAKER_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^(?:r/\w+:\s*)?\W*|\b(?:sou|soy|eu|yo|je suis|moi)\W{1,2})\(?$"));
static NONSPACE: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\s,(|/]"));
static POINTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:that|it|which|this)(?:'s| is| was)\s*$"));
static ARROW: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:-+>|/)"));
static LIKENED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:as \w+|(?:re[- ]?)?imagined|depicted|portrayed|drawn|written|cast|played|dressed|dressing|disguised|treated|seen|reborn|reincarnated|born|raised)\W*$"));
static LEADING_OK: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\s*[,.!)\]]?\s*(?:\n|$)|\s*,|\s*[\[(#|/–&-]|\s*[.!]\s*(?:i|i'm|im)\b|[,\s]+(?:[\w/]+ ){{0,2}}(?:here|looking|seeking|lmk|hmu|dm|dms)\b|[,\s]+(?:i|i'm|im|i've|and|but|now|years?|yrs?|yo|y/o|år|ans|años|anos|jahre|anni|who|feeling|felt|need|needing|want|wanting|wanna|just|still|today|tonight|too|anyone|old|drop)\b|[,\s]+(?:[\w/]+ ){{0,2}}?(?:chub|hairy|masc|uncut|redhead|xxl|smooth|verbal|otter|hung|vers|inch|inches|single|married|bi|gay|straight|thick|horny|from|uk|usa|us|enby|nb|trans|ftm|mtf|slim|fit|skinny|chubby|curvy|tall|short|white|black|asian|latino|latina|hispanic|{PERSON})")));
static HANDICAP: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:handicap|hcp|hdcp)\b"));
static FOREIGN_GENDERS: LazyLock<Table> = LazyLock::new(|| {
    let mut map = Table::new();
    for word in MALE_FOREIGN {
        map.insert(word.to_string(), "man");
    }
    for word in FEMALE_FOREIGN {
        map.insert(word.to_string(), "woman");
    }
    map.insert("erkeğim".to_string(), "man");
    map.insert("kadınım".to_string(), "woman");
    map
});
const MALE_FOREIGN: &[&str] = &["hombre", "chico", "muchacho", "señor", "papá", "padre", "esposo", "homem", "rapaz", "menino", "pai", "marido", "homme", "mec", "gars", "garçon", "papa", "père", "mann", "junge", "kerl", "vater",
    "uomo", "ragazzo", "papà", "jongen", "vader", "kille", "mężczyzną", "facetem", "chłopakiem", "ojcem", "tatą", "парень", "мужчина", "хлопець", "чоловік", "ladka", "mard", "cowok", "pria", "lelaki", "راجل", "رجل", "ولد"];
const FEMALE_FOREIGN: &[&str] = &["mujer", "chica", "muchacha", "señora", "mamá", "madre", "esposa", "mulher", "moça", "menina", "garota", "mãe", "femme", "fille", "maman", "mère", "frau", "mädchen", "mutter", "donna", "ragazza", "mamma",
    "vrouw", "meisje", "moeder", "kvinna", "tjej", "kobietą", "dziewczyną", "matką", "mamą", "девушка", "женщина", "дівчина", "жінка", "ladki", "aurat", "cewek", "perempuan", "wanita", "بنت", "امرأة", "ست"];
const NEGATED: &str = r"(?!(?:no|não|nao|pas|nicht|kein|keine|niet|geen|inte|nie|не|non|nunca|jamais)\b)";
const OWNERS: &str = r"(?!(?:tuo|tua|tu|su|sus|seu|sua|ton|ta|votre|ma|mon|mi|meu|minha|mio|mia|dein|deine|mein|meine|jouw|je|mijn|din|ditt|min|mitt|twoja|twój|mój|moja)\b)";
static ROMANCE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:que|para|com|con|não|por|una|uma|um|est|é|és|pour|avec|je|eu|yo|sou|soy|muy|mais|más|aqui|aquí|ici)\b"));
const HOMBRE: &str = r"h(?<!\wh) ?(\d{2})\)?(?![\w'%])";
static OPENED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^(?:r/\w+:\s*)?|[.!?,:\n]|\b(?:soy|sou|sono|je suis)(?: un| una| um| uma| une)?) *$"));
const NOUNED: &str = r"(h(?<!\wh)(?:omme|ombre|omem)|f(?<!\wf)emme|m(?<!\wm)(?:ujer|ulher)|u(?<!\wu)omo|d(?<!\wd)onna) (?:de|di) (\d{2})\b(?! ?(?:kg|cm|€|%))";
static BORN: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:(?<![^\W_])i was |(?<![^\W_])(?:^(?:r/\w+:\s*)?|[.!?\n]) *)$"));
static CONFESSED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"{IM} (?:just |also |kinda |a bit |a little |a |an )?$")));
static CURIOUSLY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:guy|girl|man|woman|male|female|dude|bottom|top|vers|here|m\b|f\b|[,.!|/])"));
static ASIDE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:(?<!\bgood )(?<!\bgood-)looking|seeking|want|wants|than|taller|shorter|you|he|she|his|her|my|like|into|for)\b"));
const PAIRED: &str = r"(?:^(?:r/\w+:\s*)?\W*|\b(?:i|me|ich|myself|moi|yo|i've|i'm|im|i am|i was)\s*)(?:[\[\(]\s*([mfw])\s*[,/]\s*(\d{2})\s*[\]\)]|[\[\(]\s*(\d{2})\s*[,/]\s*([mfw])\s*[\]\)])";
const TRAILING: &str = r"(?:^(?:r/\w+:\s*)?|[\s.!?(\[])([mf])\s?(\d{2})\W*$|(?:^(?:r/\w+:\s*)?|[\s.!?(\[])(\d{2})(?:\s?(f)| (m))\W*$";
static HAILED: LazyLock<Re> = LazyLock::new(|| {
    let names = &*ETHNIC_JOINED;
    Re::new(&format!(r"(?:^(?:r/\w+:\s*)?|[.!?,;(] *|(?<![\w.])\d{{2}} )({names}) $"))
});
static ALIKE: LazyLock<Re> = LazyLock::new(|| {
    let names = &*ETHNIC_JOINED;
    Re::new(&format!(r"\b({names}) (?:\w+ )?(?:girl|guy|woman|man|lady|gal|dude|boy|bro|chick|women|men|girls|guys|ladies) $"))
});
const TALL: &str = r"(?:[4-7]\s?(?:'|ft|foot|feet)\s?(?:\d{1,2}(?![\d.]))?|1[4-9]\d\s?cm\b|1[.,][4-9]\d\s?m\b)";
const STAT_GAP: &str = r"(?:\s*[,/|]\s*|\s+-\s+|\s+)";
const COUPLED: &str = r"^(?:r/\w+:\s*)?\W*(\d{2})([mf])\s?[/&+]?\s?\d{2}(?!\2)[mf]\b";

static BUMP: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:pregnan\w*|baby|babies|bumps?|bumpers?|due|trimester|newborn|postpartum|ttc|stm|weeks?|wks?|mom|mum|mama|loss|losses|miscarriage|ivf|rainbow)\b"));

pub static RULES: LazyLock<Vec<Rule>> = LazyLock::new(build);

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub(crate) fn h() -> Option<&'static Re> {
    Some(&*LIMIT)
}

pub(crate) fn sh() -> Option<&'static Re> {
    Some(&*SELF_LIMIT)
}

fn golfed(m: &Match) -> bool {
    (0..=m.groups()).filter_map(|g| m.span(g)).any(|(_, end)| HANDICAP.at(m.string, end).is_some())
}

pub(crate) fn said(attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static, limit: Option<&'static Re>) -> Rule {
    let value = move |m: &Match| if attribute == "age" && golfed(m) { None } else { value(m) };
    let Some(limit) = limit else { return rule(attribute, pattern, value, TAGGED) };
    let asked = !["age", "gender", "height", "body_weight"].contains(&attribute);
    rule(attribute, pattern, move |m: &Match| {
        let text = m.string;
        let start = m.start();
        if limit.test_in(text, clause(text, start).max(start.saturating_sub(40)), start) || (asked && ASKED.at(text, m.end()).is_some()) {
            return None;
        }
        value(m)
    }, TAGGED)
}

pub(crate) fn mine(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| if owned(m.string, m.start()) { value(m) } else { None })
}

fn spoken(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| {
        let prefix = tail_sentence(m.string, m.start(), 80);
        if THIRD.test(prefix) || POINTER.test(prefix) || !(owned(m.string, m.start()) || SPEAKER.test(prefix)) {
            return None;
        }
        value(m)
    })
}

fn listed(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| {
        let last = m.lastindex().map_or(m.start(), |g| m.start_of(g).max(0) as usize);
        if ASIDE.test_in(m.string, m.start() + 2, last) { None } else { value(m) }
    })
}

pub(crate) fn personal(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| {
        let text = m.string;
        let first = line(text, 0);
        if FIRST.test(sentence(text, m.start(), m.end())) || MEASURED.test(line(text, m.start())) || (first.contains(&'4') && LOOKING.test(first)) || AGED.test(first) {
            value(m)
        } else {
            None
        }
    })
}

pub(crate) fn alone(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| if THIRD.test(tail_sentence(m.string, m.start(), 80)) { None } else { value(m) })
}

fn plain(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> Value {
    Box::new(move |m: &Match| if LIKENED.test(before(m.string, m.start(), 40)) { None } else { value(m) })
}

fn trailed(m: &Match) -> bool {
    !GAME.test(m.string) && !m.text().contains(&'?') && !OTHERS.test(before(m.string, m.start() + 1, 24)) && !(m.nonempty(1).is_some() && chassis(m.string, m.start(), m.end()))
}

fn age_of(groups: &'static [usize]) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| ages(either(m, groups))
}

fn first_age(m: &Match) -> Option<String> {
    ages(m.first())
}

fn table_of(t: &'static LazyLock<Table>, groups: &'static [usize]) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| get(t, either(m, groups))
}

fn feet_inches(feet: Option<&[char]>, inches: Option<&[char]>) -> Option<String> {
    let inches = match inches.filter(|i| !i.is_empty()) {
        Some(stated) => py_int(stated)?,
        None => 0,
    };
    let total = py_int(feet?)? * 12 + inches;
    if inches < 12 && total <= 86 {
        Some(rounded(total as f64 * 2.54))
    } else {
        None
    }
}

fn kilos(amount: f64, unit: &[char]) -> f64 {
    amount * if unit.first() == Some(&'k') { 1.0 } else { 0.4536 }
}

fn body_lookup(word: Option<&[char]>) -> Option<String> {
    let key = st(word?);
    BODIES.get(&key).or_else(|| SHAPES.get(&key)).map(|v| v.to_string())
}

pub(crate) fn fixed_map(pairs: &[(&str, &'static str)], word: &[char]) -> Option<&'static str> {
    pairs.iter().find(|(k, _)| eq(word, k)).map(|(_, v)| *v)
}

fn build() -> Vec<Rule> {
    let mut all = age();
    all.extend(gender());
    let start = all.len();
    all.extend(orientation());
    ORIENTATION_RANGE.set((start, all.len())).ok();
    all.push(rule("gender", r"lesbian", |m: &Match| {
        let (a, b) = *ORIENTATION_RANGE.get().unwrap();
        let lesbian = RULES[a..b].iter().any(|entry| entry.re.iter(m.string).any(|found| (entry.value)(&found).as_deref() == Some("lesbian")));
        if lesbian { Some("woman".to_string()) } else { None }
    }, TAGGED));
    all.extend(ethnicity());
    all.extend(height());
    all.extend(weight());
    all.extend(body_type());
    all.extend(hair_color());
    all.extend(crate::traits::rules());
    all.extend(crate::looks::rules());
    all
}

fn age() -> Vec<Rule> {
    let pointed = pointed();
    let ethnic_names = &*ETHNIC_NAMES;
    vec![
        said("age", &format!(r"{IM} (?:(?:only|just|now|turning|currently|also|still|already|literally|actually|finally|officially|technically|basically|a|an) )*(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs|y))?(?![\w%'/+-]|[.,:]\d)(?!\s*{UNITS}|\s*(?:and|or|-)\s*\d)"), age_of(&[1]), h()),
        said("age", r"as(?<!\was) an? (?:(?!(?:not|no|with|for|to|than|like|and|or|that|who)\b)[\w-]+ ){0,2}?(\d{2})(?:[- ]?(?:years?|yrs?|yr)[- ]?old|\s?(?:yo|y/o))\b", age_of(&[1]), h()),
        said("age", r"\bthis (\d{2}) ?(?:years?[- ]old|yrs?[- ]old|yo|y/o) (?:has|is|will|would|can|still|needs|wants|loves|could)\b|\bme,? an? (\d{2}) ?(?:years?[- ]old|yrs?[- ]old|yo|y/o)\b|\ban? (\d{2}) ?(?:years?[- ]old|yrs?[- ]old|yo|y/o) (?:[\w-]+ ){0,2}?like me\b", age_of(&[1, 2, 3]), h()),
        said("age", r"\b(?:(?:we're|we are) (?:both|only|just|now)|we both are|(?:my \w+|\w+) and i are(?: both)?|me and (?:my )?\w+ are(?: both)?) (\d{2})\b(?!\s*(?:and|or|-|&)\s*\d)(?!\s*(?:%|percent|minutes|mins|hours|days|weeks|months|years? (?:ago|in|into|of|together|married)|miles|km|feet|ft|lbs?|kg|dollars|bucks|k\b))", age_of(&[1]), h()),
        said("age", r"(?:\bi(?:'ve| have)? |^(?:r/\w+:\s*)?|[.!?\n] )(?:(?:just|recently|finally|also|only|officially) )*(?:turned|(?<![\w ])turning|(?<=[.!?\n] )turning) (\d{2})\b(?! (?:years|minutes|weeks|percent|%))", age_of(&[1]), h()),
        said("age", &format!(r"{IM} (?:a |an )?(?:(?!not\b|never\b)[a-z]+ ){{0,3}}?(\d{{2}})[\s-]?(?:yo|y/o|y\.o\.?|years? old|yr old|year-old)\b"), age_of(&[1]), h()),
        said("age", r"(?:^(?:r/\w+:\s*)?|[.!?\n] *)(\d{2}) (?:years? old|yo|y/o) (?:here|male|female|guy|girl|man|woman|m|f)\b", age_of(&[1]), h()),
        said("age", r"(?:^(?:r/\w+:\s*)?|[.!?\n] *)at (\d{2})(?: years? old)?,? (?:now|i|i'm|im)\b|\bfreshly (\d{2})\b", age_of(&[1, 2]), h()),
        said("age", r"\bmy age (?:is |\(|of )(\d{2})\b|\bage\s*[:=]\s*(\d{2})\b(?!\s*[-–]\s*\d|\s+to\s+\d)|(?=age\W)(?<!\bof )(?<!\bat )(?<!\bby )(?<!\buntil )(?<!\btill )(?<!\bsince )(?<!\bfrom )(?<!\bbefore )(?<!\bafter )(?<!\bto )(?<!@)(?<!\bover )(?<!\bunder )(?<!\blegal )(?<!\bsame )(?<!\bthe )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\btheir )\bage\s?[\(\[]?(\d{2})[\)\]]?(?![\w+-])(?!\s*(?:and|or|to|-|\+|/)\s*\d|\+|\s*(?:and|or) (?:up|older|over|above|under|below)\b)",
            |m: &Match| if GAME.test(m.string) { None } else { ages(either(m, &[1, 2, 3])) }, h()),
        said("age", r"(\d{2}) here\b(?! (?:in|at|for|since|and|or|is|are|was)\b)", |m: &Match| if GREETED.test_in(m.string, m.start().saturating_sub(24), m.start()) { ages(m.group(1)) } else { None }, sh()),
        said("age", &format!(r"now(?<![a-z]now) (?:i'm |im |i am |(at) )?(\d{{2}})\b(?![\d%/'-]|[.,]\d)(?!\s*{UNITS})"),
            |m: &Match| if NOWADAYS.test_in(m.string, m.start().saturating_sub(80), m.start()) || (m.nonempty(1).is_some() && RETURNED.at(&m.string[m.end()..], 0).is_some()) { ages(m.group(2)) } else { None }, sh()),
        said("age", r"(\d{2}) now(?:\)|\W*$)", |m: &Match| {
            let two = before(m.string, m.start(), 2);
            if eq(two, ", ") || eq(two, " (") || eq(slice(m.string, m.start() as isize - 1, m.start() as isize), "(") { ages(m.group(1)) } else { None }
        }, sh()),
        said("age", r"(?:me|myself) at (\d{2})\b(?![\d.,%/'-])", |m: &Match| if OPENED_LINE.test(before(m.string, m.start(), 3)) { ages(m.group(1)) } else { None }, sh()),
        said("age", r", (\d{2}),", |m: &Match| if NAMED.test_in(m.string, m.start().saturating_sub(30), m.start()) { ages(m.group(1)) } else { None }, sh()),
        said("birth_year", r"born in (?:((?:19[3-9]\d)|(?:200\d)|(?:201[0-2]))\b|'(\d{2})\b|([3-9]\d)\b(?![\d,.%]))", |m: &Match| {
            if !BORN.test_in(m.string, m.start().saturating_sub(40), m.start()) {
                return None;
            }
            match (m.nonempty(1), m.nonempty(2), m.nonempty(3)) {
                (Some(year), _, _) => Some(py_int(year)?.to_string()),
                (None, Some(short), _) => match py_int(short)? {
                    year @ 0..=12 => Some((2000 + year).to_string()),
                    year @ 30..=99 => Some((1900 + year).to_string()),
                    _ => None,
                },
                (None, None, Some(decade)) => Some((1900 + py_int(decade)?).to_string()),
                (None, None, None) => unreachable!("born in matched without a year"),
            }
        }, h()),
        said("age", &format!(r"^(?:r/\w+:\s*)?(?=[\s\S]*?[^\W\d_])(?:(?![$#+£€'.])\W){{0,2}}[\[\(]?(\d{{2}})[\]\)]?(?=[\s,.!\]…]|$|(?<=\))[a-z])(?!\s+[^\x00-\x{{24f}}]|!\?|\s+(?!yrs?\b|years?\b|[a-z]+ous\b)[a-z]{{2,}}s\b|\s+(?:years?|yrs?|yr)\b(?!\s+old\b)|(?<=\d)\s+straight\b|\s*{UNITS}|[.,:/]\d|\s*[-–/x+]\s*\d|\s*(?:and|or|to|-)\s+\d|\.\s*\d|\s+(?:of|out|times|people|years? (?:ago|of)|is|was|isn't|wasn't|would|will|more|minutes|seconds|percent|k|point|points|roll|eur|euros?|usd|tl|rs|kr|pln|kilo|кило|лет|psi|cents?|g|mg|ml|hz|fps|gb|mb|tb|mm|rpm|bpm|ppm|dpo|total|million|mill|billion|thousand|gig|gigs|new|हज़ार|{MONTHS})\b)"),
            |m: &Match| if GAME.test(m.string) || !(AD.test_in(m.string, 0, 300) || m.text().iter().any(|c| *c == '(' || *c == '[') || LEADING_OK.at(m.string, m.end()).is_some()) { None } else { ages(m.group(1)) }, TAGGED),
        said("age", r"\b(?:i|me|i'm|im|i am|myself|ich)\b[^.!?\n()]{0,25}\((\d{2})[),]", age_of(&[1]), sh()),
        said("age", r"(?=\d\d)(?<!\bis )(?<!\bwas )(?<!\bare )(?<!\bwere )(?<!\bof )(?<!\bthan )(?<!\bunder )(?<!\bover )(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bnearly )(?<!\balmost )(?<!\babout )(?<!\baround )(?<!\bthat )(?<!\bfamous )(?:^(?:r/\w+:\s*)?|(?<=[\s(\[,]))(\d{2})\s?(?:yo|y/o|y\.o\.?|yr old|year old|years old|yrs old)\b(?! (?:aunt|uncle|grandma|grandpa|grandmother|grandfather|film|movie|bottle|game|song|album|show|book|tree|building|son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat|car|house|man|woman|guy|male|female|friend|wife|husband|girls|boys|guys|men|women|kids|people|and (?:above|up|over|older|under|below)|or (?:older|younger|above|over|under))\b)",
            spoken(age_of(&[1])), sh()),
        said("age", r"(?:^(?:r/\w+:\s*)?|\n)[^\S\n]*[>*•\\-]{0,2}[^\S\n]*(\d{2})\s*,\s*(?:[mf]\b|male\b|female\b|[4-7]\s?['’]\s?\d|\d{2,3}\s?(?:lbs?|kg|cm)\b)|^(?:r/\w+:\s*)?\W*(\d{2})[- ]?jährige[rn]?\b", age_of(&[1, 2]), sh()),
        said("age", r"me(?<!\wme)\s*[:=-][^\S\n]*[>*•\\-]{0,2}[^\S\n]*(\d{2})\s*,\s*(?:[mf]\b|male\b|female\b|[4-7]\s?['’]\s?\d|\d{2,3}\s?(?:lbs?|kg|cm)\b)|me(?<!\wme)\s*[-:=]\s*(\d{2})\b(?!\s*(?:%|[-/:.]\d))", age_of(&[1, 2]), sh()),
        said("age", r"mit(?<!\wmit) (\d{2}) jahren\b|(\d{2}) éves (?:vagyok|leszek)\b|a(?<!\wa) mis (\d{2})(?: años)?\b(?! (?:jours|días|dias|minutes|heures|semaines|mois)\b)", first_age, sh()),
        said("age", r"\b(?:tengo|tenho) (\d{2})(?: (?:años|anos))?\b|\bj'ai (\d{2})(?: ans)?\b(?!\s+(?!ans\b)[a-zà-ÿ]{2,})|\bya[sş] ?:? ?(\d{2})\b|\b(\d{2}) jahre alt\b|\bich bin (\d{2})\b", first_age, sh()),
        said("age", PAIRED, age_of(&[2, 3]), TAGGED),
        said("age", TRAILING, |m: &Match| if trailed(m) { ages(either(m, &[2, 3])) } else { None }, TAGGED),
        said("age", r"^(?:r/\w+:\s*)?\W*(\d{2})\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot) )*(?:male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bottom|top|sub|dom|cuck|virgin|couple)\b", age_of(&[1]), TAGGED),
        said("age", r"\b(?:ho|imam|mam|j'ai|tengo|tenho|jestem|tinc|heb) (\d{2}) ?(?:anni|godina|godine|lat|lata|ans|años|anos|jaar|anys)\b|(?:^(?:r/\w+:\s*)?|[.!?,\n] *)(?:homme|femme) de (\d{2}) ans\b|^(?:r/\w+:\s*)?\W*(\d{2}) ?(?:lat|lata|anni|ans|años|anos|godina|jahre)\b", first_age, TAGGED),
        needs(said("age", r"(?:soy|sou|sono|je suis|eu sou)\b[^.!?\n]{0,40}?\b(?:de|di) (\d{2}) (?:años|anos|ans|anni)\b|(?:hoje|agora|ahora|ya) (?:com|con|tengo|tenho) (\d{2}) (?:anos|años)\b|мне (\d{2})\b|(?:main|mai) (\d{2}) (?:saal |sal )?(?:ka|ki) (?:hoon|hu|hun|hoo)\b|ik ben (\d{2})(?: jaar)?\b(?! (?:kg|kilo|cm|euro|keer|minuten|uur))|(\d{2}) yaşındayım\b",
            |m: &Match| if isalpha(slice(m.string, m.start() as isize - 1, m.start() as isize)) { None } else { first_age(m) }, sh()),
            &["años", "anos", "ans", "anni", "мне", "main ", "mai ", "ik ben", "yaşındayım"]),
        said("age", r"^(?:r/\w+:\s*)?\W*(?:vrouw|homme|femme|mujer|hombre|chica|chico|frau|mann|mulher|homem)\W{1,3}(\d{2})\b", age_of(&[1]), sh()),
        said("age", &pointed, age_of(&[1]), sh()),
        said("age", COUPLED, age_of(&[1]), TAGGED),
        said("age", r"^(?:r/\w+:\s*)?\W{0,3}(\d{2}) ?(?:y|yr|yrs)\b(?!\s*(?:old|ago|of|later|in|and|or|to|-)\b)", age_of(&[1]), TAGGED),
        said("age", r"(?=\d\d ?y)(?<![\w$#.,'/:+-])(?<!\ba )(?<!\ban )(?<!\bmy )(?<!\bthe )(?<!\bhis )(?<!\bher )(\d{2}) ?(?:y|yr|yrs) (?:guy|girl|man|woman|dude|male|female|bbc|bwc|m|f)\b", age_of(&[1]), sh()),
        said("age", &format!(r#"^(?:r/\w+:\s*)?[^\n]{{0,80}}?(?=\d\d)(?<![\w$#£€.,'/:+*-])(?<!\bover )(?<!\bunder )(?<!\bfirst )(?<!\bthan )(?<!\blike )(?<!\bin )(?<!\bat )(?<!\bto )(?<!\bfor )(?<!\bwith )(?<!\bof )(?<!\bmax )(?<!\babout )(?<!\baround )(?<!\blast )(?<!\bnext )(?<!\bevery )(?<!\bonly )(?<!\btop )(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bmy )(?<!\byour )(?<!\bis )(?<!\bare )(?<!\bwas )(?<!\bby )(?<!\bfrom )(?<!\bafter )(?<!\bsince )(\d{{2}})(?![\w%'/:+*-]|[.,]\d|\s*{UNITS}|\s*(?:-|to|or|and)\s*\d|\s*(?:inch|in\b|\"|”|cm|mm|lbs?|kg|min|mins|k\b|m\b|hr|hrs|yrs? ago|guys|people|men|women|girls|hours|years|nudes|pics|videos|times|days|weeks|months|users|members|followers|upvotes|likes|million|billion|thousand|transactions|trades|dms|messages|followers|usd|eur|gbp|budget|1st|2nd|3rd))"#),
            |m: &Match| {
                let text = m.string;
                let first = &text[..line_end(text, 0)];
                if AD.test_in(text, 0, 300) && !COUNTED.test_in(text, 0, m.start_of(1) as usize) && TWO_DIGITS.count(first) == 1 && !GAME.test(text) { ages(m.group(1)) } else { None }
            }, TAGGED),
        said("age", &format!(r#"(?<![\w.'\"/$#%+:–-])(?<!\d,)(?:[mf]\s?/\s?)?(\d{{2}})(?:\s?(?:yo|y/o|yrs?|years? old))?{STAT_GAP}(?:(?:[mf]|male|female|{ethnic_names})\s*[,/|]?\s*)?{TALL}"#),
            alone(|m: &Match| if desired(m.string, m.start()) { None } else { ages(m.group(1)) }), TAGGED),
        said("age", &format!(r"^(?:r/\w+:\s*)?[^\n\d]{{0,120}}\n(?:[^\S\n]*\n)*[^\S\n]*[>*•\\-]{{0,2}}[^\S\n]*(\d{{2}})(?=[\s,.!:)]|$)(?!\s*{UNITS}|\s*(?:-|to|or|and|x)\s*\d|[.,:]\d|\s+(?:guys|people|men|women|girls|hours|years|nudes|pics|videos|times|days|weeks|months|minutes|mins|of|out|percent)\b)"),
            |m: &Match| if AD.test_in(m.string, 0, 300) && !GAME.test(m.string) { ages(m.group(1)) } else { None }, TAGGED),
    ]
}

fn pointed() -> String {
    let gender_words = &*GENDER_WORDS;
    format!(r"this(?<=\bthis) (\d{{2}}) ?(?:yo|y/o|yr old|year old|years old)? (?:[a-z]+ ){{0,2}}?{gender_words}\b")
}

fn foreign_self() -> String {
    let mut words: Vec<&str> = MALE_FOREIGN.iter().chain(FEMALE_FOREIGN.iter()).copied().chain(["erkeğim", "kadınım"]).collect();
    words.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    words.dedup();
    let foreign_gender = words.join("|");
    format!(r"(?:(?:soy|sou|sono|saya|je suis|jestem|jag är|ich bin|ik ben|aku|eu sendo|yo siendo) (?:{NEGATED}{OWNERS}[^\W\d_]+ ){{0,2}}?|(?:я|انا|أنا) |(?:eu|yo|moi|ich|io|ik|jag), |(?:main|mai) (?:bhi |ek )?(?=\w+ h(?:u|oon|un|oo)\b)|(?:als|como|som) (?=(?:mann|frau|hombre|mujer|homem|mulher|kvinna|vrouw)(?![\w-])(?! (?:de|da|do|di|von|der|des)\b))|en tant que (?=homme|femme))({foreign_gender})(?![\w-])")
}

fn transgender(m: &Match) -> Option<String> {
    let value = get(&GENDERS, m.first())?;
    if eq(m.first()?, "ftm") && BUMP.test(m.string) { None } else { Some(value) }
}

fn gender() -> Vec<Rule> {
    let gender_words = &*GENDER_WORDS;
    let foreign_self = foreign_self();
    let pointed = pointed();
    vec![
        said("gender", &format!(r"\b(?:{I}|as|being|just) (?:an? )?(?:{FREE}){{0,2}}?(?:trans|transgender) (woman|girl|female|lady|man|guy|boy|male|dude)\b"),
            |m: &Match| { let w = m.group(1).unwrap_or(&[]); Some(if ["woman", "girl", "female", "lady"].iter().any(|x| eq(w, x)) { "trans woman" } else { "trans man" }.to_string()) }, h()),
        said("gender", PAIRED, table_of(&POSTERS, &[1, 4]), TAGGED),
        said("gender", &format!(r"{IM} (?:(?:also|just|only|still|actually|literally|already|genuinely|honestly|proudly|really|definitely|obviously|basically|simply) )?(?:an? |the )?{ADJECTIVES}{gender_words}\b(?! (?:friend|friends|of|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent)\b)(?!'s)"), group(&GENDERS, 1), h()),
        said("gender", &format!(r"{IM} (?:just |only |also |still |actually |literally |really |definitely |obviously |simply |basically )?(?:an? |the |one )(?:{FREE}|[\w'-]+, |and ){{0,6}}?{gender_words}\b(?! (?:friend|friends|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff|dad|mom|mother|father|parent|energy|moment|problem)\b)(?!'s)"), group(&GENDERS, 1), h()),
        said("gender", &format!(r"^(?:r/\w+:\s*)?(?:[^\w\[]*\[[^\]\n]*\])*+\W*(?:#\w+\W+)*(?:(?!(?:the|this|that|any|every|a|an|my|your|his|her|our|their|some|dated|date|dating|met|meet|seeing|with|for|looking|seeking|want|wants|need|needs)\b)[a-z]+ ){{0,3}}?{gender_words}\b(?= (?:here|looking|seeking|searching|for|4)\b)"), group(&GENDERS, 1), TAGGED),
        said("gender", &format!(r"{IM} (?:an? )?{FREE}{{0,3}}?in (his|her) (?:early |mid |late )?(?:\d0'?s|teens|twenties|thirties|forties|fifties|sixties|seventies)\b"),
            |m: &Match| m.group(1).map(|g| if eq(g, "his") { "man" } else { "woman" }.to_string()), h()),
        needs(said("gender", r"\b(?:an? |for an? )?(?:[\w'-]+ )?(girl|guy|woman|man|lady|gal|dude|bloke|women|men|ladies|girls|guys|dudes) like (?:me|myself|us)\b|\bhelp an? (?:\w+ )?(girl|gal|guy|dude|lady|bro|sister|sis) out\b",
            alone(table_of(&GENDERS, &[1, 2])), TAGGED), &["like me", "like myself", "like us", "help a"]),
        said("gender", &format!(r"(?=as )(?<!\byou )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bme )\bas an? (?:fully )?{ADJECTIVES}{gender_words}\b(?!'s| of\b)"), alone(plain(group(&GENDERS, 1))), h()),
        said("gender", &format!(r"(?:(?:^(?:r/\w+:\s*)?|[.!?,;:(\n]) *|\b(?:i|me|myself|and|but|so|even)\s+)as an? {FREE}{{1,3}}?{gender_words}\b(?!'s| of\b)"), alone(plain(group(&GENDERS, 1))), h()),
        said("gender", &format!(r"\bbeing an? {FREE}{{0,2}}?{gender_words},? (?:i|i'm|im|myself)\b|(?:^(?:r/\w+:\s*)?|[.!?\n] *)just (?:an?|your|ur|another|some) {FREE}{{0,3}}?{gender_words}(?: (?:with|who|from|in|trying|looking|that|next|doing|living|and)\b|\s*[.!?…,]|\s*$)"), table_of(&GENDERS, &[1, 2]), h()),
        said("gender", r"i(?<!\wi)(?:'m|m| am) (?:an? \d{2}[ -]?(?:yo|y/o|years?[ -]old|yrs?[ -]old) )?([mf])(?=[\s,.!)/]|$)(?!\s*\*)|^(?:r/\w+:\s*)?\W*([mf]|male|female)\W*$", table_of(&GENDERS, &[1, 2]), TAGGED),
        said("gender", r"(?:^(?:r/\w+:\s*)?|[\s,(\]])(milf|hotwife|bull|twink|femboy|cougar|gilf|dilf|domme)(?: here| looking| seeking| loves| needs| wants| for| 4\b)", group(&GENDERS, 1), sh()),
        said("gender", &format!(r"(?:^(?:r/\w+:\s*)?|[.!?,;] *)(?:an? )?{FREE}{{0,2}}?{gender_words} here\b"), group(&GENDERS, 1), h()),
        said("gender", &format!(r#"(?<![\w.'\"/$#%+:-]){TALL}(?:\"|'')?(?: tall)?(?:{STAT_GAP}(?:and )?\d{{2,3}}\s?(?:lbs?|kg|pounds|#))?{STAT_GAP}(?:and )?(male|female)\b"#),
            alone(|m: &Match| if desired(m.string, m.start()) { None } else { get(&GENDERS, m.group(1)) }), sh()),
        said("gender", r"(?:^(?:r/\w+:\s*)?|\n)[^\S\n]*(?:\\?[-*>]+[^\S\n]*)?(?:\*\*)?(?:\d+\.\s*)?(?:sex or gender|gender|sex)(?: (?:&|and|/) age)?(?:\*\*)?\s*[:=-]\s*(?:\*\*)?\s*(male|female|man|woman|m|f|non-binary|nonbinary)\b", group(&GENDERS, 1), TAGGED),
        said("gender", &format!(r"{IM} (?:also |just |still |actually )?(?:a |an )?(non-binary|nonbinary|enby|genderfluid|agender|genderqueer|trans woman|transwoman|trans girl|trans man|transman|trans guy|mtf|ftm)\b(?! (?:people|rights|friend|kids))"), transgender, h()),
        said("gender", r"(?:^(?:r/\w+:\s*)?|(?<=[\s,(\]]))(?<!\bis )(?<!\bwas )(?<!\bsize )[\(\[]\s*([mf])\s*[\)\]]", group(&GENDERS, 1), TAGGED),
        said("gender", r"[\(\[](?<![^\s,(\]][\(\[])(?<!\bthe [\(\[])(?<!\ba [\(\[])(?<!\ban [\(\[])\s*(male|female)\s*[\)\]]|\b(?:i|me|myself)\s*\((?:an? )?(?:[\w ]+, )?(male|female|guy|girl|man|woman|dude|lady)\)", mine(table_of(&GENDERS, &[1, 2])), TAGGED),
        said("gender", r"(?=\d\d)(?<![\w$#.,'/:+-])(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(\d{2})[ -]?(?:years?[ -]old|yrs?[ -]old|yo|y/o) (male|female|man|woman|guy|girl|dude|lady)\b(?! (?:friend|friends|coworker|patient|client|customer|relative|cousin|neighbor|neighbour)\b)",
            spoken(|m: &Match| if ages(m.group(1)).is_some() { get(&GENDERS, m.group(2)) } else { None }), sh()),
        said("gender", r"(?<![\w'])(?<!\bthe )(?<!\bthis )(?<!\bthat )(?<!\bfor )(?<!\bmarried )(?<!\bany )(?<!\bevery )[\(\[]?(female|male|guy|girl|woman|man|dude|lady|f|m)(?: in (?:my |her |his )?(?:early |mid |late )?\d0'?s)? here\b|\bfellow (?:\w+ )?(dude|guy|woman|man|lady|girl|mom|dad) here\b", |m: &Match| if desired(m.string, m.start()) { None } else { get(&GENDERS, either(m, &[1, 2])) }, TAGGED),
        said("gender", r"^(?:r/\w+:\s*)?\W*\d{2}\s*,?\s+(?:(?:single|married|white|black|asian|latino|latina|hispanic|indian|tall|short|fit|chubby|bi|straight|gay|hung|older|young|discreet|horny|local|cute|shy|sexy|thick|petite|curvy|clean|ddf|attractive|handsome|hot|bicurious|curious|dl|masc|fem|hairy|smooth|bearded|tattooed|inked|muscular|athletic|slim|skinny|average|kinky|naughty|lonely|bored|verbal) )*(male|female|guy|girl|man|woman|dude|lady|queen|king|bbw|milf|stud|bull|twink|femboy|daddy|bro|boy|boi|jock|bear|cub|dad)\b", group(&GENDERS, 1), TAGGED),
        said("gender", r"(?:^(?:r/\w+:\s*)?|[\s,(\[])(t4[mfat]|ts girl|tgirl|trans girl|transgirl|mtf|ftm|trans guy|transman|transwoman)\b|^(?:r/\w+:\s*)?\W*(agender|non-?binary|enby|genderfluid|genderqueer)\b|\b(domme|dominatrix|mistress)\b(?= (?:here|looking|seeking|available|for)\b)",
            alone(mine(|m: &Match| {
                if question(m.string, m.end()) {
                    return None;
                }
                if m.nonempty(1).is_some() {
                    return transgender(m);
                }
                if let Some(g2) = m.nonempty(2) {
                    return GENDERS.get(&st(g2).replace("nonbinary", "non-binary")).map(|v| v.to_string());
                }
                Some("woman".to_string())
            })), sh()),
        said("gender", r"(?:^(?:r/\w+:\s*)?|\n)\W*(?:1[3-9]|[2-9]\d)(?: ?(?:yo|y/o|yrs?(?: old)?|years? old))?[\s,.]+(?:(?!(?:not|no|with|for|to|than|like|and|or|that|who|this|the|my|his|her|your|their|our|a|an|in|on|at|from|about|by|into|of)\b)[a-z'-]+,? ){0,4}?(guy|man|dude|male|boy|lad|bloke|woman|girl|female|lady|gal|chick|twink|femboy|bro|jock|cub|daddy|dad|milf|wife|husband|hubby|mom)\b(?= (?:here|looking|seeking|for|from|in|into|needs?|wants?|with)\b|\s*[,.!]|\s*$)",
            |m: &Match| if AD.test_in(m.string, 0, 300) { get(&GENDERS, m.group(1)) } else { None }, TAGGED),
        said("gender", TRAILING, |m: &Match| if trailed(m) { get(&GENDERS, either(m, &[1, 4, 5])) } else { None }, TAGGED),
        said("gender", &format!(r"[^\w-](?=[sjiaeymckяاأ])(?:{foreign_self}|(erkeğim|kadınım)(?![\w-]))"), |m: &Match| get(&FOREIGN_GENDERS, m.first()), h()),
        said("gender", &format!(r"^(?:r/\w+:\s*)?\W*(?:{foreign_self}|(erkeğim|kadınım)(?![\w-])|(vrouw|homme|femme|mujer|hombre|chica|chico|frau|mann|mulher|homem)\W{{1,3}}\d{{2}}\b)"), |m: &Match| get(&FOREIGN_GENDERS, m.first()), h()),
        said("gender", NOUNED, |m: &Match| if OPENED.test(&m.string[..m.start()]) { get(&FOREIGN_GENDERS, m.group(1)) } else { None }, h()),
        said("gender", HOMBRE, |m: &Match| if ages(m.group(1)).is_some() && ROMANCE.test(m.string) && SPEAKER_BEFORE.test(&m.string[..m.start()]) { Some("man".to_string()) } else { None }, TAGGED),
        said("gender", r"\b(?:we|us|we're|we are) (?:as |fellow |other |older |younger |black |white |gay |straight |trans |single |married |tall |short )?(men|women|guys|girls|ladies|dudes|females|males|moms|dads|mothers|fathers|wives|husbands)\b", group(&GENDERS, 1), h()),
        said("gender", r"^(?:r/\w+:\s*)?\W*([mf])(?:\s*[|/\\]\s*(?=\w)|\s+(?:for [mf]\b|looking|seeking))", group(&GENDERS, 1), TAGGED),
        said("gender", &pointed, |m: &Match| if ages(m.group(1)).is_some() { get(&GENDERS, m.group(2)) } else { None }, sh()),
        said("gender", COUPLED, |m: &Match| if ages(m.group(1)).is_some() { get(&POSTERS, m.group(2)) } else { None }, TAGGED),
        said("gender", r"^(?:r/\w+:\s*)?\W*(?:bi|gay|str8|straight|married|single|horny|hung|young|older|mature|curious|bicurious|discreet|dl) ([mf])\b(?! ?\d)(?!')", group(&GENDERS, 1), TAGGED),
        said("gender", r"^(?:r/\w+:\s*)?[^\n]{0,80}?(?=[mf])(?<![\w'/+.(*-])(?<!\bfor )(?<!\bseeking )(?<!\bwant )(?<!\bany )(?<!\bthe )(?<!\ba )(?<!\b4 )(?<!\bor )(?<!\band )(?<!\bno )(?<!\bsingle )(?<!\bas )(?<!\bin )(?<!\bonly )([mf])(?![\w'/+*.)-]|\s*(?:4|for|or|and|&|only|to)\b)",
            |m: &Match| {
                let text = m.string;
                let first = &text[..line_end(text, 0)];
                let from = (m.end_of(1) as usize - m.start()).min(first.len());
                if AD.test_in(text, 0, 300) && !LETTER_AFTER.test(&first[from..]) && !GAME.test(text) && !desired(text, m.start_of(1) as usize) { get(&GENDERS, m.group(1)) } else { None }
            }, TAGGED),
    ]
}

fn orientation() -> Vec<Rule> {
    vec![
        said("sexual_orientation", &format!(r"{IM} [^.!?\n;]{{0,40}}?(?:,\s*(?:and\s+)?|\s+and\s+)(gay|straight|bi|bisexual|lesbian|pansexual|asexual)(?=\s*(?:[,.!;&/)]|and\b|$|\n))"), listed(group(&ORIENTATIONS, 1)), sh()),
        said("sexual_orientation", r"\b(gay|lesbian|bi|bisexual|pansexual|asexual|aroace|aro-ace|ace|straight|str8|queer)(?: (?:guy|girl|man|woman|male|female|dude|bro|boy|couple|bottom|top|bear|twink|femboy|wife|husband|dad|mom))? here\b", group(&ORIENTATIONS, 1), sh()),
        said("sexual_orientation", &format!(r"{IM} (?:(?:also|just|still) )?(?:a |an )?(?:(?:\d{{2}}[- ]?(?:years?|yr)[- ]old|cis|single|married|black|white|asian|trans|young|old|older|proud|openly|also|both|totally|fully) )*(gay|lesbian|bisexual|bi|pansexual|asexual|queer|straight|heterosexual|homosexual|heteroflexible|hetero-flexible|aegosexual|androsexual|cishet)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|men|women|guys|people|porn|marriage|ally|rights|shooter|a)\b)"), group(&ORIENTATIONS, 1), h()),
        said("sexual_orientation", &format!(r"{IM} (?:an? )?(?:(?!\w+ing\b|gonna\b|be\b|go\b|get\b|setting\b){FREE}){{0,3}}?(gay|lesbian|bisexual|bi|pansexual|asexual|aroace|aro-ace|queer|straight|heterosexual|homosexual|heteroflexible|aegosexual|androsexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|friends|men|women|guys|girls|people|porn|marriage|ally|rights|shooter|a|content|stuff|scene|community|culture|sex)\b)"), group(&ORIENTATIONS, 1), h()),
        said("sexual_orientation", &format!(r"{IM} (?:(?:also|just|still|pretty|very|kinda|a bit) )*sexually fluid\b"), fixed("fluid"), h()),
        said("sexual_orientation", r"^(?:r/\w+:\s*)?(?:[^\w\[]*\[[^\]\n]*\])*+\W*(?:#\w+\W+)*(?:[a-z]+ ){0,2}?(gay|bi|bisexual|straight|str8|lesbian|pansexual) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|husband|dad|daddy|bear|bro|boy|woman|man|male|female|twink|femboy|bottom|top|chub|stud|dude|couple|sub|dom|jock|cub|bull|babe|teen|queen|slut|sissy|boi|bbw|milf|lady|gal|mom|vers|otter)\b(?! (?:friend|friends|porn)\b)", group(&ORIENTATIONS, 1), TAGGED),
        said("sexual_orientation", r"as(?<!\was) an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer|heteroflexible|aegosexual|androsexual)\b(?! (?:up|out|forward|away|from|to|into|after|back|down|ahead|through|off|on|in|at|for|with|couple|people|community|friend|friends|ally|rights|men|women|guys|porn|bar|club|marriage|man|woman|guy|girl|person|male|female|dude|boy)\b)", group(&ORIENTATIONS, 1), h()),
        said("sexual_orientation", r"(?:^(?:r/\w+:\s*)?|\n)\W*(?:\d{2}\s*(?:[mf]|yo|y/o)?|[mf]\s?\d{2}|[\(\[]\d{2}[\)\]])[\s,]+(?:(?!(?:i|was|not|never|used)\b)[a-z]+[\s,]+){0,2}?(straight|str8|bi|bisexual|gay|lesbian|hetero|pan)\b(?! (?:men|women|guys|girls|porn|couple|friend))", group(&ORIENTATIONS, 1), TAGGED),
        said("sexual_orientation", r"as(?<!\was) an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude|couple|boy)\b", group(&ORIENTATIONS, 1), h()),
        said("sexual_orientation", r"(?:^(?:r/\w+:\s*)?|[.!?,;] *)(gay|lesbian|bi|bisexual|straight|pansexual) (?:\w+ )?(?:male|female|guy|girl|man|woman|dude|couple) here\b", group(&ORIENTATIONS, 1), h()),
        said("sexual_orientation", r"bi(?<![\w-]bi)[- ]?curious\b", |m: &Match| {
            let start = m.start();
            let previous = slice(m.string, start as isize - 1, start as isize);
            if CONFESSED.test_in(m.string, start.saturating_sub(30), start) || (NONSPACE.at(previous, 0).is_none() && CURIOUSLY.at(m.string, m.end()).is_some()) { Some("bi-curious".to_string()) } else { None }
        }, sh()),
    ]
}

fn ethnicity() -> Vec<Rule> {
    let joined = &*ETHNIC_JOINED;
    let ethnic_names = &*ETHNIC_NAMES;
    let stat = format!(r#"(?:\d{{2}}(?:\s?(?:yo|y/o|yrs?|years? old|[mf]))?|[mf]\s?\d{{2}}|{TALL}(?:\"|'')?|\d{{2,3}}\s?(?:lbs?|kg|pounds))"#);
    let anchors: Vec<&str> = {
        let mut keys: Vec<&str> = ETHNIC_KEYS.to_vec();
        keys.sort();
        keys
    };
    vec![
        said("ethnicity", &format!(r"{IM} [^.!?\n;]{{0,40}}?(?:,\s*(?:and\s+)?|\s+and\s+)({joined})(?=\s*(?:[,.!;&/)]|and\b|$))"), listed(group(&ETHNICITIES, 1)), sh()),
        said("ethnicity", &format!(r"{IM} (?:an? (?:(?!(?:non|not|honorary|fan|huge|big|{ethnic_names})\b){FREE}){{0,5}}|half |half-|also |\d{{2}},? )?({joined})(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself|lady)|-american)?(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|bag|over|about|feelings|up|with)\b)"), group(&ETHNICITIES, 1), h()),
        said("ethnicity", &format!(r"(?=as )(?<!\bsuch )(?<!\bsame )(?<!\bdressed )(?<!\btreated )(?<!\bseen )\bas an? (?:(?!(?:non|not|honorary|{ethnic_names})\b)\w+ )?({joined})\b(?!-)(?! (?:people|folks|community|communities|culture|food|neighborhood|area|country|family|friend|friends|men|women|guys|girls|kids|person's)\b)(?!'s)"), group(&ETHNICITIES, 1), h()),
        said("ethnicity", &format!(r"(?:i(?<!\wi)(?:'m|m| am)|a(?<!\wa)s) (?:just |also |only )?(?:a |an )?(?:(?!\w+ing\b){FREE}|an? ){{0,4}}?({joined}) (?:man|woman|guy|girl|person|male|female|dude|american|lady|mom|dad|mother|father|kid|teen|boy|bro|immigrant|canadian|british|australian|bottom|top|chub|bear|daddy|stud|bull|twink|femboy)\b"), group(&ETHNICITIES, 1), sh()),
        said("ethnicity", &format!(r"\b(?:i'm|im|i am|as an?|a)? ?half[- ]({joined})[,/ ]+(?:and )?half[- ]({joined})\b|\bethnically (?:{joined}) ?(?:/|and|&) ?(?:{joined})\b"), fixed("mixed"), h()),
        said("ethnicity", r"\bwe (black|white|asian|latina|latino|hispanic|indian|desi|arab|indigenous|native) (?:women|men|people|folks|girls|guys)\b|\b(?:soy|sou|je suis) (?:una? (?:mujer|hombre|chica|chico|homem|mulher) |uma? (?:mulher|homem) |une? (?:femme|homme|fille|mec) )?(latino|latina|negro|negra|blanco|blanca|branco|branca|preto|preta|blanc|blanche|noir|noire)\b|\b(white) ?boi\b|\b(?:i'm|im|i am|i m) (?:(?!(?:not|so|very|too|pretty|a|an|the|all|just|also|still|really|more|less|half|like|fully|mostly|part)\b)[a-z]+ )?(?<!\beast )(?<!\bsouth )(?<!\bsoutheast )(black|white|asian|latina|latino|hispanic|mixed|biracial|desi)(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|bag|over|about|feelings|up|with|and \w+ing)\b)",
            |m: &Match| {
                let word = m.first()?;
                fixed_map(&[("negro", "black"), ("negra", "black"), ("preto", "black"), ("preta", "black"), ("noir", "black"), ("noire", "black"), ("blanco", "white"), ("blanca", "white"), ("branco", "white"), ("branca", "white"), ("blanc", "white"), ("blanche", "white"), ("native", "indigenous")], word)
                    .map(|v| v.to_string()).or_else(|| get(&ETHNICITIES, Some(word)))
            }, sh()),
        said("ethnicity", &format!(r"^(?:r/\w+:\s*)?(?:[^\w\[]*\[[^\]\n]*\])*+\W*(?:#\w+\W+)*(?:[a-z]+ ){{0,2}}?({joined}) (?:[a-z]+ ){{0,2}}?(?:girl|guy|woman|man|boy|boi|bro|lady|gal|chick|dude|male|female|milf|mom|wife|dad|daddy|bottom|top|sub|dom|twink|femboy|bull|stud|slut|babe|teen|queen|king|bbw|cuck|couple|body|bod|ass|booty|butt|tits|boobs)\b(?! (?:\w+ )?(?:cock|dick))(?=(?: \w+)? (?:here|looking|seeking|wanting|needing|for|ready|with|needs|wants|available)\b|\s*[,.!]|\s*$)"), group(&ETHNICITIES, 1), TAGGED),
        needs(said("ethnicity", r"here\b(?<=\bhere)", |m: &Match| HAILED.search(m.string, m.start().saturating_sub(40), m.start()).and_then(|named| get(&ETHNICITIES, named.group(1))), h()), &anchors),
        needs(said("ethnicity", r"like(?<=\blike) (?:me|myself|us)\b", |m: &Match| ALIKE.search(m.string, m.start().saturating_sub(50), m.start()).and_then(|named| get(&ETHNICITIES, named.group(1))), TAGGED), &anchors),
        said("ethnicity", &format!(r#"(?<![\w.'\"/$#%+:-]){stat}{STAT_GAP}(?:(?!(?:non|not|and|or|to|with|for|of|in|at|from|the|a|an|my|your|his|her|their|our|south|east|southeast|middle|native|pacific|half|long|short|dark|light)\b)[a-z]+ )?({ethnic_names})(?![\w-])(?! (?:\w+ )?{PARTNERS})(?!\s*/\s*(?:{ethnic_names})\b| (?:{ethnic_names}|hair|eyes|skin|haired|eyed|skinned)\b)(?! (?:\w+ ){{0,2}}(?:guys|girls|women|men|ladies|people|couples|cock|dick|cocks|dicks|tops|bottoms|bulls|only|preferred|pref)\b)"#),
            alone(|m: &Match| if desired(m.string, m.start_of(1) as usize) { None } else { get(&ETHNICITIES, m.group(1)) }), TAGGED),
        said("ethnicity", &format!(r#"(?:^(?:r/\w+:\s*)?|[\n,|]|\s-)\s*({ethnic_names})(?![\w-])(?!\s*/\s*(?:{ethnic_names})\b){STAT_GAP}{stat}(?![\w'\"%])"#),
            alone(|m: &Match| if desired(m.string, m.start_of(1) as usize) { None } else { get(&ETHNICITIES, m.group(1)) }), TAGGED),
        said("ethnicity", &format!(r"^(?:r/\w+:\s*)?\W*(?:[a-z]+ ){{0,2}}?({joined})(?= (?:here|looking|seeking|wanting|needing|hmu|ready|available)\b)"), group(&ETHNICITIES, 1), TAGGED),
    ]
}

fn height() -> Vec<Rule> {
    vec![
        said("height", &format!(r#"{IM} [^.!?\n;]{{0,40}}?(?<=[\s,/])([4-7])\s?(?:'|ft|foot|feet)\s?(?:and )?(1[01]|0?\d)?\s?(?:\"|''|in\b|inches)?(?!\d|\.\d|')(?! (?:away|from|deep|long|wide)\b)"#),
            listed(|m: &Match| feet_inches(m.group(1), m.group(2))), h()),
        said("height", r#"height(?<!\wheight)(?:\s*[:=-]|(?<=\bmy height) is)\s*(?:(1[4-9]\d|2[01]\d)\s?cm|([4-7])\s?(?:'|ft|foot|feet)\s?(?:(1[01]|0?\d)(?!\d))?)|(?:f(?<!\wf)or me|m(?<!\wm)e|i(?<!\wi)'m|i(?<!\wi)m|i(?<!\wi) am) at ([4-7])\s?(?:'|ft)\s?(1[01]|0?\d)?(?!\d|\.\d)|([4-7])(?<![\w.][4-7])\s?,\s?(\d{1,2})\s?(?:\"|”|'')?\s*tall\b"#,
            |m: &Match| match m.nonempty(1) {
                Some(cm) => Some(st(cm)),
                None => feet_inches(either(m, &[2, 4, 6]), either(m, &[3, 5, 7])),
            }, h()),
        said("height", &format!(r#"(?:{IM}|i(?<!\wi) stand|standing at) (?:only |about |around |almost |nearly |barely |like |just |a )?([4-7])\s*(?:'|ft|foot|feet|f(?=\s*tall\b))\s*(?:and )?(1[01]|0?\d)?\s*(?:\"|''|in\b|inches)?(?!\d|\.\d)(?! (?:away|from|deep|long|wide)\b)"#),
            |m: &Match| feet_inches(m.group(1), m.group(2)), h()),
        said("height", &format!(r"{IM} (?:only |about |around |almost |nearly |barely |like |just |at )?(1[4-9]\d|2[01]\d)\s*cm\b|{IM} (?:only |about |around |almost |nearly |barely |like |just )?1[.,]([4-9]\d)\s?m\b"),
            |m: &Match| match m.nonempty(1) {
                Some(cm) => Some(st(cm)),
                None => Some(format!("1{}", st(m.group(2).unwrap_or(&[])))),
            }, h()),
        said("height", r#"as(?<!\was)(?<!\bsuch as) an? ([4-7])\s?(?:'|ft|foot)\s?(\d{1,2})?\s?(?:\"|''|in\b)?\s?(?:\w+ )?(?:man|woman|guy|girl|male|female|dude|lady|person|boy|bro)\b|(?:and|but)(?<!\wand)(?<!\wbut) am ([4-7])'\s?(\d{1,2})?(?![\d.'])"#,
            |m: &Match| feet_inches(either(m, &[1, 3]), either(m, &[2, 4])), h()),
        said("height", r"([4-7])(?<![\w.$'][4-7])[.,](1[01]|\d)\s?(?:ft|feet|foot|f|height)\b", alone(|m: &Match| feet_inches(m.group(1), m.group(2))), h()),
        said("height", &format!(r#"{IM} (?:like |about |around |only |just |roughly |almost |nearly )?([4-7])[.,](1[01]|\d)(?![\d.,/%'\"”])(?! ?(?:inch|in\b|cm|mm|kg|kgs|lbs?|pounds|k\b|m\b|million|mil|percent|stars?|out of|gpa))"#),
            |m: &Match| feet_inches(m.group(1), m.group(2)), h()),
    ]
}

fn weight() -> Vec<Rule> {
    vec![
        said("body_weight", &format!(r"\bi (?:weigh|weight|'m at|am at|'m currently at|'m currently)\s+(?:about |around |roughly |almost |like |just under |over |under )?(\d{{2,3}}(?:\.\d)?)\s*(lbs?|pounds|kg|kgs|kilos)\b|{IM} (?:an? )?(\d{{2,3}})\s*(lbs?|pounds|kg|kgs)\b"),
            |m: &Match| {
                let amount = py_float(either(m, &[1, 3])?)?;
                let weight = kilos(amount, either(m, &[2, 4])?);
                if (35.0..=250.0).contains(&weight) { Some(rounded(weight)) } else { None }
            }, h()),
        said("body_weight", r"(?:^(?:r/\w+:\s*)?|[\s,|/(~@])(\d{2,3})(?:ish)?\s?(lbs?|pounds|kg|kgs|kilos?)\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain|gained|more|less|bag|bags|box|dumbbells?|plates?|bench|squat|deadlift|worth))",
            personal(alone(|m: &Match| {
                if LOAD.test_in(m.string, m.start().saturating_sub(16), m.start() + 1) || ARROW.at(&m.string[m.end()..], 0).is_some() {
                    return None;
                }
                let weight = kilos(py_float(m.group(1)?)?, m.group(2)?);
                if (35.0..=250.0).contains(&weight) { Some(rounded(weight)) } else { None }
            })), sh()),
        said("body_weight", r#"[4-7](?<![\w.$'][4-7])\s?(?:'|ft)\s?\d{1,2}(?:\"|”|'')?\s*[,/]?\s+(\d{3})(?:\s?(?:lbs?|pounds))?(?![\w.%/'\"”])"#,
            alone(|m: &Match| {
                let weight = py_int(m.group(1)?)? as f64 * 0.4536;
                if weight <= 250.0 && !WANTING.test(tail_sentence(m.string, m.start(), 80)) { Some(rounded(weight)) } else { None }
            }), sh()),
    ]
}

fn body_type() -> Vec<Rule> {
    let body_all = &*BODY_ALL;
    let body_words = &*BODY_WORDS;
    let stat = format!(r#"(?:\d{{2}}(?:\s?(?:yo|y/o|yrs?|years? old|[mf]))?|[mf]\s?\d{{2}}|{TALL}(?:\"|'')?|\d{{2,3}}\s?(?:lbs?|kg|pounds))"#);
    vec![
        said("body_type", &format!(r"{IM} [^.!?\n;]{{0,40}}?(?:,\s*(?:and\s+)?|\s+and\s+)(?:am\s+)?(?:very |pretty |quite |kinda |kind of |a bit |a little |fairly |super )?({body_all})(?=\s*(?:[,.!;&/)]|and\b|but\b|af\b|asf\b|so\b|lol\b|my\b|i\b|$|\n))"),
            listed(|m: &Match| {
                let (s1, _) = m.span(1)?;
                let word = m.group(1)?;
                if !STURDY.contains(st(word).as_str()) && GIRTH.test_in(m.string, s1.saturating_sub(24), s1) { None } else { bodied(m.string, s1, word) }
            }), sh()),
        said("body_type", r"^(?:r/\w+:\s*)?(?:[^\w\[]*\[[^\]\n]*\])*+\W*(?:#\w+\W+)*(?:[a-z]+ )?(chubby|chub|curvy|thick|thicc|petite|slim|skinny|fat|bbw|ssbbw|athletic|muscular|fit|stocky|toned|slender|tiny|ripped|jacked|buff|lean|beefy|chunky) (?:[a-z]+ ){0,2}?(?:girl|guy|wife|milf|mom|dad|daddy|bear|bro|boy|woman|man|hotwife|latina|latino|twink|femboy|bottom|top|sub|dom|jock|cub|stud|bull|babe|teen|queen|slut|sissy|boi|baddie|mommy|lady|gal|chick|dude)\b(?! (?:\w+ )?(?:cock|dick))",
            |m: &Match| body_lookup(m.group(1)), TAGGED),
        said("body_type", r"\b(?:an? )?(slim|slender|skinny|athletic|muscular|fit|chubby|chub|chunky|curvy|thick|thicc|petite|bbw|ssbbw|stocky|beefy|ripped|toned|fat|tiny|average|obese|overweight) (?:\w+ )?(?:girl|guy|woman|man|lady|boy|dude|bro|wife|mom|milf|dad|daddy|bear|hotwife|chick|gal|teen|mommy|momma|babe|slut|bottom|twink|femboy)(?: like me\b| here\b)",
            |m: &Match| body_lookup(m.group(1)), TAGGED),
        said("body_type", r"\bmy (?:\w+ )?curves\b", fixed("curvy"), sh()),
        said("body_type", &format!(r#"(?<![\w.'\"/$#%+:-]){stat}{STAT_GAP}(?:and )?(?:(?:very|pretty|super|quite|slightly|kinda|fairly) )?({body_words})(?![\w'-])(?! (?:\w+ ){{0,2}}(?:{CROWD}|cock|dick|cocks|dicks|penis|bwc|bbc|shaft|uncut|cut)\b)"#),
            alone(|m: &Match| {
                let s1 = m.start_of(1) as usize;
                if desired(m.string, s1) { None } else { bodied(m.string, s1, m.group(1)?) }
            }), TAGGED),
        said("body_type", &format!(r"{IM} (?:(?:very|really|pretty|quite|a bit|kinda|kind of|super|too|so|a little|slightly|fairly|relatively|somewhat|reasonably|naturally|extremely|rather|extra|also|still|now|currently|just|only|actually|literally|definitely|honestly|basically|always|a|an) )*(?:(?!average\b)({body_all})|(average)(?= (?:build|body|bod|size|weight|frame|shape)\b|\s*[,.!;)]|$| and\b))\b(?! (?:fan|deal|part|news|on|in|for|of|to|time|enough|mood|chance|mess|game|difference|problem|issue|plus|day|week|month|year|joe|student|height|amount|number|smoker|drinker|sleeper|user|eater|lifter|hitter|metal|vaper|breather|snorer|gamer|reader|duty|load|equipment|traffic)s?\b)"),
            |m: &Match| {
                let last = m.lastindex()?;
                bodied(m.string, m.start_of(last) as usize, either(m, &[1, 2])?)
            }, h()),
        said("body_type", r"(?:^(?:r/\w+:\s*)?|[\s,|/])(bbw|curvy|petite|chubby|athletic|muscular|slim)\s*(?:f|female|woman|girl|m|male|guy|here)\b",
            mine(|m: &Match| if desired(m.string, m.start_of(1) as usize) { None } else { get(&BODIES, m.group(1)) }), sh()),
        said("body_type", &format!(r"\b(?:{I}|bod|body|build|frame) (?:\w+ )?on the (slim|slimmer|thin|thinner|skinny|skinnier|lean|leaner|heavy|heavier|big|bigger|large|larger|chubby|chubbier|curvy|curvier|thick|thicker) side\b"),
            |m: &Match| {
                let word = m.group(1)?;
                Some(fixed_map(&[("slim", "slim / skinny"), ("slimmer", "slim / skinny"), ("thin", "slim / skinny"), ("thinner", "slim / skinny"), ("skinny", "slim / skinny"), ("skinnier", "slim / skinny"), ("lean", "slim / skinny"), ("leaner", "slim / skinny"), ("curvy", "curvy"), ("curvier", "curvy"), ("thick", "thick"), ("thicker", "thick"), ("chubby", "chubby"), ("chubbier", "chubby")], word).unwrap_or("big / heavyset").to_string())
            }, h()),
        said("body_type", r"\b(?:my|this|with a|with my) (?:\w+ )?(curvy|chubby|thick|thicc|petite|fat|skinny|slim|athletic|muscular|fit|tiny|bbw|plus[- ]size|average|toned|slender|dad|chunky|stocky|ripped|jacked|buff|lean|beefy|muscled|shredded|thin|heavy|overweight) (?:body|build|frame|figure|bod|self)\b|\b(slim|athletic|average|avg|ave|normal|slender|muscular|stocky|heavy|thin|fit|curvy|chubby|thick|thicc|petite|tiny)(?: and (?:fit|toned|athletic|slim))? buil[dt]\b|\bbuilt like an hourglass\b|\bextra (thicc|thick)\b",
            |m: &Match| {
                let Some(word) = m.nonempty(1).or(m.nonempty(2)).or(m.group(3)) else { return Some("curvy".to_string()) };
                if eq(word, "thicc") || eq(word, "thick") {
                    return Some("thick".to_string());
                }
                fixed_map(&[("tiny", "petite"), ("dad", "dad bod"), ("avg", "average"), ("ave", "average"), ("normal", "average"), ("stocky", "stocky"), ("heavy", "chubby")], word)
                    .map(|v| v.to_string()).or_else(|| body_lookup(Some(word)))
            }, TAGGED),
        said("body_type", r"\b(?:my|this|these) (?:\w+ ){0,2}?(chubby|chunky|curvy|thick|thicc|skinny|slim|petite|muscular|toned|athletic),? (?:(?:and |, ?)?\w+ ){0,2}?(?:ass|booty|butt|belly|tummy|thighs|tits|boobs|bod|body|self|curves|figure|frame|pussy)\b",
            |m: &Match| {
                let word = m.group(1)?;
                fixed_map(&[("chunky", "chubby"), ("thick", "thick"), ("thicc", "thick"), ("toned", "fit / athletic")], word).map(|v| v.to_string()).or_else(|| get(&BODIES, Some(word)))
            }, TAGGED),
    ]
}

fn hair_color() -> Vec<Rule> {
    vec![
        said("hair_color", &format!(r"(?:{IM}|\bmy hair(?: is|'s)) (?:(?:already|slowly|now|also|just|prematurely|definitely|finally|starting to|started) )*(gr[ae]ying|going gr[ae]y|turning gr[ae]y|going silver|going white|turning white)\b"),
            |m: &Match| Some(if eq(m.first()?, "going white") || eq(m.first()?, "turning white") { "white" } else { "grey / greying" }.to_string()), h()),
        said("hair_color", r"\bmy (?:(?:long|short|messy|lovely|beautiful|natural|naturally|thick|thin|fine|dark|light|bright|curly|wavy|straight|dirty|platinum|golden|honey|sandy|dyed|bleached|new|current|real|own|frizzy|greasy|shoulder[- ]length|graying|greying|medium) ){0,3}(strawberry blonde?|blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green|salt and pepper) hair\b|\bi have (?:long |short |curly |natural )?(strawberry blonde?|blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green|salt and pepper) hair\b",
            table_of(&HAIRS, &[1, 2]), h()),
        needs(said("hair_color", &format!(r"{IM} (?:an? )?{FREE}{{0,2}}?(red|ginger|blonde?|brown|black|dark|grey|gray|white)[- ]?(?:haired|headed)\b|\bi(?<!\wi) (?:just |recently |finally |also )?dyed my hair (?:\w+ )?(pink|blue|purple|green|teal|turquoise|lavender)\b"),
            |m: &Match| {
                if let Some(dyed) = m.nonempty(2) {
                    return get(&HAIRS, Some(dyed));
                }
                let word = m.group(1)?;
                if let Some(v) = fixed_map(&[("dark", "black"), ("ginger", "red / ginger")], word) {
                    return Some(v.to_string());
                }
                HAIRS.get(&st(word).replace("blond", "blonde").replace("blondee", "blonde")).map(|v| v.to_string())
            }, h()), &["haired", "headed", "dyed my hair"]),
        said("hair_color", &format!(r"{IM} (?:a |an |naturally |going |also |still |just |actually |really |completely |totally |literally |basically |already )*(blonde|blond|brunette|redhead|a redhead|ginger|a ginger)\b(?! (?:joke|moment|people)\b)"), group(&HAIRS, 1), h()),
        needs(said("hair_color", &format!(r"\b(?:i'm|im|i am|i m) (?:still |also |just |actually |really |naturally )?(?:a |an )?(?:(?!not\b|never\b|no\b)\w+ ){{0,2}}?(red ?head|redhead|ginger|blonde|blond|brunette)\b|(?:^(?:r/\w+:\s*)?|[\s,|/(])(red ?head|redhead|brunette)\b(?= (?:\w+ )?(?:here|bitch|boy|girl|guy|babe|milf|wife|mom|looking|f\b|m\b))|\b(?:i (?:actually |also |still |now )?have|i've got|i got|my) (?:long |short |thick |thin |curly |straight |wavy |natural |graying |greying |dark |light |bright |{FREE}){{0,3}}?(strawberry blonde?|blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green|teal|salt and pepper)(?: buzz cut| curly| wavy| straight)? hair\b"),
            alone(|m: &Match| HAIRS.get(&st(either(m, &[1, 2, 3])?).replace(' ', "")).map(|v| v.to_string())), sh()), &["red", "ginger", "blond", "brunette", "hair"]),
    ]
}

pub fn force() {
    for re in [&LEADING_OK, &LIKENED, &HANDICAP, &BUMP, &RETURNED, &OPENED_LINE, &TWO_DIGITS, &LETTER_AFTER, &SPEAKER_BEFORE, &NONSPACE, &POINTER, &ARROW, &ROMANCE, &OPENED, &BORN, &CONFESSED, &CURIOUSLY, &ASIDE, &HAILED, &ALIKE] {
        LazyLock::force(re);
    }
    LazyLock::force(&FOREIGN_GENDERS);
}
