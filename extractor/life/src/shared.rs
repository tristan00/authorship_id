use claimcore::*;

pub type V = Option<&'static str>;
pub type Tab = [(&'static str, &'static str)];

macro_rules! regex {
    ($name:ident, $pattern:expr) => {
        pub static $name: std::sync::LazyLock<claimcore::Re> = std::sync::LazyLock::new(|| claimcore::Re::new(&$pattern));
    };
}
pub(crate) use regex;

pub const MARRIED: &str = "married";
pub const DATING: &str = "in a relationship";
pub const SEEING: &str = "dating / seeing someone";
pub const COMMON_LAW: &str = "common-law / de facto";
pub const ENGAGED: &str = "engaged";

pub const ME: &str = r"i(?<!\wi)(?:'m|m| am|am| m|'am|'?ve been|'ve always been)";
pub const AS: &str = concat!(
    r#"as(?:(?<=^as)|(?<=[\n.!?,;:(\"*\[\]-]as)|(?<=[\n.!?,;:(\"*\[\]-] as)|(?<=[\n.!?,;:(\"*\[\]-]  as)|(?<=\band as)|(?<=\bbut as)|(?<=\bso as)|(?<=\bme as)|(?<=\bmyself as)|(?<=\bthat as)|(?<=\bthis as)"#,
    r"|(?<=\bspeaking as)|(?<=\beven as)|(?<=\bjust as)|(?<=\bsay as)|(?<=\bsaid as)|(?<=\bi as))"
);

regex!(NEAR, r#"\b(?:be|become|becoming|imagine|pretend|roleplay|rp|future|someday|dream|wish|if i (?:ever )?(?:had|have|get|got|find)|when i (?:have|get|find))[\s'\"*_]+(?:\w+[\s'\"*_]+)?$"#);
regex!(SCOPED, r#"\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$"#);
regex!(STATED, r#"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|act like|until|once|used to|when i was|back when|no longer|never|not)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$"#);
regex!(FUTURE, r#"(?:\b(?:if|wish|unless|whether|pretend(?:ing)?|imagine|as if|until|once|when|someday|one day|would|want to|wanna|hope to|plan to|planning to|used to|never|not|cannot)|n't)[\s'\"*_]+(?:\w+[\s'\"*_]+)?$"#);
regex!(WAS, r"\b(?:he|she|they|you|u) (?:was|were)\s+$");
regex!(CONDITIONAL, r"\b(?:if|would|wish)\b");

regex!(ENDED, r"\b(?:i'm|i am|im|we're|we are|we got|i got) (?:now |recently |newly |legally |finally |officially )?(?:divorced|separated)\b|\b(?:my|our) divorce\b|\bmy ex[- ]?(?:wife|husband|hubby|spouse)\b|\bnow ex\b|\bmy (?:late|deceased) (?:wife|husband)\b|\bi(?:'m| am) (?:a )?widow(?:er|ed)?\b");
regex!(BROKEN, r"\b(?:broke up with me|dumped me|(?:she|he) left me|we (?:just |recently |finally )?(?:broke up|broken up|split up)|i (?:just |finally )?broke up with (?:him|her|my)|since (?:the|our|my) break ?up|after (?:the|our|my) break ?up)\b");
regex!(WRITING, r"\b(?:rp|roleplay|role play|role-play|writing|literate|kinks?|plot|para)\b");
regex!(THIRD, r"\b(?:he|she|they|you|u|his|her|their|your|ur)\b");
regex!(COUPLED, r"\b(?:married|wife|husband|hubby|hotwife)\b");
regex!(SELF, r"\b(?:i|me|my|we|our|us|i'm|im|i've)\b");

pub static SPOUSES: &Tab = &[
    ("wife", MARRIED), ("husband", MARRIED), ("hubby", MARRIED), ("wifey", MARRIED), ("spouse", MARRIED), ("missus", MARRIED), ("mrs", MARRIED), ("hubs", MARRIED), ("wifes", MARRIED),
    ("husbands", MARRIED), ("hubbys", MARRIED), ("girlfriend", DATING), ("boyfriend", DATING), ("gf", DATING), ("bf", DATING), ("partner", DATING), ("significant other", DATING), ("misses", MARRIED),
    ("fiance", ENGAGED), ("fiancé", ENGAGED), ("fiancee", ENGAGED), ("fiancée", ENGAGED), ("jowa", DATING),
];
pub static STATUSES: &Tab = &[
    ("single", "single"), ("married", MARRIED), ("engaged", ENGAGED), ("divorced", "divorced"), ("separated", "separated"), ("widowed", "widowed"), ("a widow", "widowed"),
    ("a widower", "widowed"), ("in a relationship", DATING), ("taken", DATING), ("attached", DATING), ("partnered", DATING),
    ("verheiratet", MARRIED), ("vergeben", DATING), ("geschieden", "divorced"), ("marié", MARRIED), ("mariée", MARRIED), ("divorcé", "divorced"), ("divorcée", "divorced"), ("casado", MARRIED), ("casada", MARRIED),
    ("divorciado", "divorced"), ("divorciada", "divorced"), ("sposato", MARRIED), ("sposata", MARRIED), ("getrouwd", MARRIED), ("gescheiden", "divorced"),
];

pub fn get(table: &Tab, key: Option<&[char]>) -> V {
    let key = key?;
    table.iter().find(|(k, _)| eq(key, k)).map(|(_, v)| *v)
}

pub fn keys(table: &Tab) -> Vec<&'static str> {
    table.iter().map(|(k, _)| *k).collect()
}

pub fn back(m: &Match, width: usize) -> usize {
    m.start().saturating_sub(width)
}

pub fn free(m: &Match) -> bool {
    !NEAR.test_in(m.string, back(m, 40), m.start())
}

pub fn spoken(m: &Match) -> bool {
    let line = &m.string[line_start(m.string, m.start())..m.start()];
    let count = |c: char| line.iter().filter(|&&x| x == c).count();
    free(m) && count('"') % 2 == 0 && count('\u{201c}') <= count('\u{201d}')
}

pub fn owned(m: &Match, table: &Tab, number: usize) -> V {
    if !spoken(m) || WAS.test_in(m.string, back(m, 10), m.start()) {
        return None;
    }
    let value = get(table, m.group(number));
    if value == Some(MARRIED) && ENDED.test(m.string) || value == Some(DATING) && BROKEN.test(m.string) {
        return None;
    }
    value
}

pub fn kept(m: &Match, result: &'static str) -> V {
    if spoken(m) {
        Some(result)
    } else {
        None
    }
}

pub fn stated(m: &Match, hedge: &Re, value: impl FnOnce() -> V) -> V {
    if hedge.test_in(m.string, back(m, 30), m.start()) {
        None
    } else {
        value()
    }
}

pub fn scoped(m: &Match, table: &Tab) -> V {
    if SCOPED.test_in(m.string, back(m, 30), m.start()) {
        None
    } else {
        get(table, m.group(1))
    }
}

pub fn bounds(m: &Match) -> (usize, usize) {
    (line_start(m.string, m.start()), line_end(m.string, m.end()))
}

pub fn sentence(m: &Match) -> (usize, usize) {
    (last_mark(m.string, m.start(), ".!?\n"), next_mark(m.string, m.end(), ".!?\n"))
}

pub fn sentence_start(m: &Match) -> usize {
    last_mark(m.string, m.start(), ".!?\n")
}

pub fn mine(m: &Match) -> bool {
    let (a, b) = bounds(m);
    SELF.test_in(m.string, a, b)
}

pub fn r(attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> V + Send + Sync + 'static, hedge: Hedge) -> Rule {
    rule(attribute, pattern, move |m| value(m).map(str::to_string), hedge)
}

pub fn constant(result: &'static str) -> impl Fn(&Match) -> V + Send + Sync + 'static {
    move |_| Some(result)
}

pub fn is_hedge(hedge: Hedge) -> bool {
    hedge.map_or(false, |h| std::ptr::eq(h, &*HEDGE) || std::ptr::eq(h, &*SELF_HEDGE))
}

pub fn scoped_rules(rules: Vec<Rule>) -> Vec<Rule> {
    rules
        .into_iter()
        .map(|entry| {
            if !is_hedge(entry.hedge) {
                return entry;
            }
            let Rule { attribute, re, gate, value, .. } = entry;
            let pets = attribute == "pets";
            let wrapped: ValueFn = Box::new(move |m: &Match| {
                if FUTURE.test_in(m.string, back(m, 30), m.start()) {
                    None
                } else if pets || spoken(m) {
                    value(m)
                } else {
                    None
                }
            });
            Rule { attribute, re, gate, value: wrapped, hedge: TAGGED }
        })
        .collect()
}
