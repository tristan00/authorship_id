use crate::flair::body;
use crate::shared::*;
use claimcore::*;

const STOP: &str = r"(?:not|no|of|for|to|with|and|or|but|like|about|in|on|at|by|from|the|a|an|his|her|their|your|my|our|this|that|these|those|some|any|dating|seeing|married|into|attracted|friends?|talking|either|between|mistyped|typed|called|named|than|more|less|fans?|he|she|they|you|it|is|was|are|were|looking|going|gonna|trying|reading|asking|sure|unsure|bringing|thinking|wondering|considering|torn|mentioning|curious|interested|questioning|getting|guessing|deciding)";
const SEP: &str = r"[\s,/&+;|()\[\]-]*(?:(?:and|with|plus|w/)\s*(?:an?\s+)?)?";
const MBTI: &str = r"[iex][nsx][tfx][jpx]";
const TOKEN: &str = concat!(
    r"(?:[ie][ns][tf][jp](?:-[at])?|[1-9]\s?w\s?[1-9x]|(?:sp|sx|so)\s?[/>]\s?(?:sp|sx|so)(?:\s?[/>]\s?(?:sp|sx|so))?|(?:sp|sx|so)[1-9](?:w[1-9])?|type\s[1-9]|[1-9]{3}|enneagram|tritype|socionics|",
    r"(?:ili|lii|ile|iei|iee|eie|eii|esi|ese|sei|sli|sle|lsi|lse)(?:-\w+)?)"
);
const LOVE: &str = r"(acts? of service|physical touch|touch|words of affirmation|affirmations?|quality time|gift[- ]giving|giving gifts|receiving gifts|gifts)";

static LOVES: &Tab = &[
    ("acts of service", "acts of service"), ("act of service", "acts of service"), ("physical touch", "physical touch"), ("touch", "physical touch"), ("words of affirmation", "words of affirmation"),
    ("affirmation", "words of affirmation"), ("affirmations", "words of affirmation"), ("quality time", "quality time"), ("gift giving", "gift giving"), ("gift-giving", "gift giving"),
    ("giving gifts", "gift giving"), ("receiving gifts", "gift giving"), ("gifts", "gift giving"),
];

const ADVERB: &str = r"(?:(?:also|actually|definitely|now|still|just|literally|basically|totally|clearly|obviously|proudly)[ \t]+)?";

fn adj() -> String {
    format!(r"(?:(?!{STOP}\b)[a-z0-9][\w'-]*[ \t]+)")
}

fn as_lead() -> String {
    format!(r"(?<!\bme )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bus )(?<!\bit )(?<!\bthis )(?<!\bthat ){AS}")
}

fn self_lead() -> String {
    let (adj, as_lead) = (adj(), as_lead());
    format!(r"{ME}[ \t]+{ADVERB}(?:an?\s+)?{adj}{{0,2}}|{as_lead}\s+an?\s+{adj}{{0,2}}|(?:^{flair}|[\n.!?,;]\s*|\bme\s+)being\s+(?:an?\s+)?{adj}{{0,2}}", flair = claimcore::flair!())
}

fn typo_lead() -> String {
    format!(
        r"(?:{}|\bi\s+(?:always\s+|usually\s+|consistently\s+|mostly\s+|also\s+)?(?:test|tested|type|typed|got|get|score|scored)(?:\s+myself)?(?:\s+out)?(?:\s+as)?\s+(?:an?\s+)?|\bmy\s+(?:mbti|myers[- ]briggs|enneagram|enneatype|tritype|(?:instinctual\s+)?stacking|instinctual variant|socionics|personality|type|typology|core type|results?)(?:\s+(?:type|types|result|results))?\s*(?:is\s+|are\s+|:\s*|-\s*|=\s*|–\s*|\(\s*)?|\bme\s*[:=–-]\s*)",
        self_lead()
    )
}

regex!(FLAIR_TYPO, format!(r"\W*(?:(?:{TOKEN}|:[\w-]+:){SEP})*"));
regex!(TYPO, format!("(?:{})(?:{TOKEN}{SEP})*$", typo_lead()));
regex!(ALTERNATIVE, format!(r"(?:{TOKEN})\s*,?\s*(?:/|\bor\b|\bvs\.?)\s*(?:an?\s+)?$"));
regex!(TYPO_AFTER, format!(r"(?:{SEP}{TOKEN})*[ \t]*,?[ \t]*(?:you|your|you're|u|ur)\b"));
regex!(LISTED, format!(r"{MBTI}(?:-[at])?s?\s*(?:,|\band\b)\s*(?:and\s+)?$"));
regex!(LOVE_LEAD, format!(concat!(
    r"\bmy\s+(?:(?:primary|main|biggest|top|first|#1|number one|number 1|strongest|own|second|other|two|2)\s+){{0,2}}love\s+languages?\s*",
    r"(?:(?:is|are|=|:|-|–|would be|has always been|have always been|has to be|include|includes)\s*)?(?:(?:definitely|probably|mostly|mainly|both|totally|100%|very much|def|also)\s+)?",
    r"(?:{LOVE}\s*(?:,|and|&|\+|/|or)?\s*(?:and\s+)?)*$"
), LOVE = LOVE));
regex!(LOVE_AFTER, format!(r"(?:\s*(?:,|and|&|\+|/)\s*(?:and\s+)?{LOVE})*\s*(?:is|are|=|-|–)\s+(?:(?:definitely|probably|totally|also|both|really|100%|very much)\s+)?my\s+(?:(?:primary|main|biggest|top|first|#1|strongest|own)\s+)?love\s+languages?\b"));

fn chained(m: &Match, lead: &Re, after: &Re) -> bool {
    let s = m.string;
    let start = last_mark(s, m.start(), ".!?").max(m.start().saturating_sub(240));
    lead.search(s, start, m.start()).map_or(false, |found| {
        !HEDGE.test_in(s, clause(s, found.start()).max(found.start().saturating_sub(40)), m.start()) && after.at(s, m.end()).is_none()
    })
}

fn alone(m: &Match) -> bool {
    !ALTERNATIVE.test_in(m.string, m.start().saturating_sub(40), m.start())
}

fn flaired(m: &Match) -> bool {
    let s = m.string;
    body(s).is_some_and(|start| FLAIR_TYPO.fullmatch(s, start, m.start()).is_some()) && !s.contains(&'?') && TYPO_AFTER.at(s, m.end()).is_none()
}

fn typed(m: &Match) -> bool {
    chained(m, &TYPO, &TYPO_AFTER) && alone(m) || flaired(m)
}

fn mbti(m: &Match) -> Option<String> {
    (typed(m) && !LISTED.test_in(m.string, m.start().saturating_sub(40), m.start())).then(|| m.g(1))
}

fn typology() -> Vec<Rule> {
    let after = format!(r"(?!\s*(?:/|or\b|vs\b)\s*(?:an?\s+)?{TOKEN})");
    let listed = format!(r"(?!s?\s*(?:,|and\b)\s*(?:and\s+)?(?:an?\s+)?{MBTI}(?![a-z]))");
    vec![
        rule("mbti_type", &format!(r"(?<![\w'/-])({MBTI})(?:-[at])?(?![\w']){after}{listed}"), mbti, hedge()),
        rule("mbti_type", &format!(r"(?:^{flair}|[\n.!?])\W*(?:(?:a\s+)?fellow\s+)?({MBTI})(?:-[at])?\s+here\b", flair = claimcore::flair!()), |m| Some(m.g(1)), hedge()),
    ]
}

fn loving(m: &Match) -> V {
    let s = m.string;
    let start = last_mark(s, m.start(), ".!?\n").max(m.start().saturating_sub(200));
    if LOVE_LEAD.test_in(s, start, m.start()) || LOVE_AFTER.at(s, m.end()).is_some() {
        get(LOVES, m.group(1))
    } else {
        None
    }
}

fn social() -> Vec<Rule> {
    vec![
        needs(r("love_language", &format!(r"(?<![\w-]){LOVE}(?![\w-])"), loving, hedge()), &["love language"]),
    ]
}

pub fn build() -> Vec<Rule> {
    timed("life.traits", || {
        let mut rules = typology();
        rules.extend(social());
        log(&format!("life traits rules={}", rules.len()));
        rules
    })
}
