use crate::shared::*;
use claimcore::*;

const FULL_SIGN: &str = r"(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|saggitarius|sagitarius|capricorn|aquarius|pisces)";
const ANY_SIGN: &str = r"(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|saggitarius|sagitarius|saggi|sagg|sag|capricorn|cap|aquarius|aqua|pisces|♈|♉|♊|♋|♌|♍|♎|♏|♐|♑|♒|♓)[\x{fe0e}\x{fe0f}]?";
const PLACE: &str = r"(?:sun|moon|rising|ascendant|asc|venus|mars|mercury|jupiter|saturn|uranus|neptune|pluto|chiron|lilith|midheaven|mc|north node|south node|stellium|☉|☀|🌞|☽|☾|🌙|↑)[\x{fe0e}\x{fe0f}]?";
const OTHER_PLACE: &str = r"(?![\s-]*(?:sun|moon|rising|ascendant|asc|venus|mars|mercury|jupiter|saturn|uranus|neptune|pluto|placements?|stellium|season|energy|man|woman|men|women|people|traits?)\b)";
const STOP: &str = r"(?:not|no|of|for|to|with|and|or|but|like|about|in|on|at|by|from|the|a|an|his|her|their|your|my|our|this|that|these|those|some|any|dating|seeing|married|into|attracted|friends?|talking|either|between|mistyped|typed|called|named|than|more|less|fans?|he|she|they|you|it|is|was|are|were|looking|going|gonna|trying|reading|asking|sure|unsure)";
const SEP: &str = r"[\s,/&+;|()\[\]-]*(?:(?:and|with|plus|w/)\s*(?:an?\s+)?)?";
const MBTI: &str = r"[ie][ns][tf][jp]";
const TOKEN: &str = concat!(
    r"(?:[ie][ns][tf][jp](?:-[at])?|[1-9]\s?w\s?[1-9x]|(?:sp|sx|so)\s?[/>]\s?(?:sp|sx|so)(?:\s?[/>]\s?(?:sp|sx|so))?|(?:sp|sx|so)[1-9](?:w[1-9])?|type\s[1-9]|[1-9]{3}|enneagram|tritype|socionics|",
    r"(?:ili|lii|ile|iei|iee|eie|eii|esi|ese|sei|sli|sle|lsi|lse)(?:-\w+)?)"
);
const CODE: &str = r"(ili|lii|ile|iei|iee|eie|eii|esi|ese|sei|sli|sle|lsi|lse|see|lie)";
const ATTACH: &str = r"(anxious(?:[- ]preoccupied)?|preoccupied|(?:dismissive|dismissing)(?:[- ]avoidant)?|avoidant|fearful(?:[- ]avoidant)?|disorgani[sz]ed|secure)";
const IDENTITY: &str = r"(therian|otherkin|fictionkin|alterhuman|polymorphkin|furry)";
const INTRO: &str = r"(introvert|introverted|extrovert|extroverted|extravert|extraverted|ambivert|ambiverted|omnivert|omniverted)";
const DEGREE: &str = r"(?:huge|big|total|massive|extreme|shy|introverted|extroverted|social|natural|true|classic|major|hardcore|very|pretty|really|quite|super|extremely|so|totally|truly|mostly|naturally|definitely|also|such|kind of|kinda|sort of|more of|a bit of|bit of|very much|the|an?)";
const LOVE: &str = r"(acts? of service|physical touch|touch|words of affirmation|affirmations?|quality time|gift[- ]giving|giving gifts|receiving gifts|gifts)";
const HOUSE: &str = r"(gryffindor|hufflepuff|ravenclaw|slytherin)";

static SIGNS: &Tab = &[
    ("aries", "aries"), ("taurus", "taurus"), ("gemini", "gemini"), ("cancer", "cancer"), ("leo", "leo"), ("virgo", "virgo"), ("libra", "libra"), ("scorpio", "scorpio"),
    ("sagittarius", "sagittarius"), ("saggitarius", "sagittarius"), ("sagitarius", "sagittarius"), ("saggi", "sagittarius"), ("sagg", "sagittarius"), ("sag", "sagittarius"),
    ("capricorn", "capricorn"), ("cap", "capricorn"), ("aquarius", "aquarius"), ("aqua", "aquarius"), ("pisces", "pisces"),
    ("♈", "aries"), ("♉", "taurus"), ("♊", "gemini"), ("♋", "cancer"), ("♌", "leo"), ("♍", "virgo"), ("♎", "libra"), ("♏", "scorpio"), ("♐", "sagittarius"), ("♑", "capricorn"),
    ("♒", "aquarius"), ("♓", "pisces"),
];
static ENNEAGRAM: &Tab = &[("1", "type 1"), ("2", "type 2"), ("3", "type 3"), ("4", "type 4"), ("5", "type 5"), ("6", "type 6"), ("7", "type 7"), ("8", "type 8"), ("9", "type 9")];
static STYLES: &Tab = &[
    ("anxious", "anxious"), ("anxious-preoccupied", "anxious"), ("anxious preoccupied", "anxious"), ("preoccupied", "anxious"), ("anxiously", "anxious"),
    ("avoidant", "avoidant"), ("dismissive", "avoidant"), ("dismissing", "avoidant"), ("dismissive-avoidant", "avoidant"), ("dismissive avoidant", "avoidant"),
    ("dismissing-avoidant", "avoidant"), ("dismissing avoidant", "avoidant"), ("avoidantly", "avoidant"),
    ("fearful", FEARFUL), ("fearful-avoidant", FEARFUL), ("fearful avoidant", FEARFUL), ("disorganized", FEARFUL), ("disorganised", FEARFUL),
    ("secure", "secure"), ("securely", "secure"),
];
const FEARFUL: &str = "fearful avoidant / disorganized";
static SOCIAL: &Tab = &[
    ("introvert", "introvert"), ("introverted", "introvert"), ("extrovert", "extrovert"), ("extroverted", "extrovert"), ("extravert", "extrovert"), ("extraverted", "extrovert"),
    ("ambivert", "ambivert"), ("ambiverted", "ambivert"), ("omnivert", "omnivert"), ("omniverted", "omnivert"),
];
static LOVES: &Tab = &[
    ("acts of service", "acts of service"), ("act of service", "acts of service"), ("physical touch", "physical touch"), ("touch", "physical touch"), ("words of affirmation", "words of affirmation"),
    ("affirmation", "words of affirmation"), ("affirmations", "words of affirmation"), ("quality time", "quality time"), ("gift giving", "gift giving"), ("gift-giving", "gift giving"),
    ("giving gifts", "gift giving"), ("receiving gifts", "gift giving"), ("gifts", "gift giving"),
];
static HOUSES: &Tab = &[("gryffindor", "gryffindor"), ("hufflepuff", "hufflepuff"), ("ravenclaw", "ravenclaw"), ("slytherin", "slytherin")];

const ADVERB: &str = r"(?:(?:also|actually|definitely|now|still|just|literally|basically|totally|clearly|obviously|proudly)[ \t]+)?";
const THIRD: &str = r"\b(?:he|she|him|his|her|hers|they|them|their|you|your|ur|bf|gf|boyfriend|girlfriend|husband|hubby|wife|partner|mom|mum|dad|mother|father|son|daughter|sister|brother|friend|baby|kid|child|crush)\b";

fn adj() -> String {
    format!(r"(?:(?!{STOP}\b)[a-z0-9][\w'-]*[ \t]+)")
}

fn as_lead() -> String {
    format!(r"(?<!\bme )(?<!\bhim )(?<!\bher )(?<!\bthem )(?<!\bus )(?<!\bit )(?<!\bthis )(?<!\bthat ){AS}")
}

fn self_lead() -> String {
    let (adj, as_lead) = (adj(), as_lead());
    format!(r"{ME}[ \t]+{ADVERB}(?:an?\s+)?{adj}{{0,2}}|{as_lead}\s+an?\s+{adj}{{0,2}}|(?:^|[\n.!?,;]\s*|\bme\s+)being\s+(?:an?\s+)?{adj}{{0,2}}")
}

fn astro_lead() -> String {
    format!(
        r"(?:{}|\bi(?:\s+(?:also|only|just|actually|do|still|too))?(?:\s+have|\s+got|'ve got|ve got|\s+have got)\s+(?:an?\s+|my\s+)?|\bmy\s+(?:own\s+)?(?:(?:natal|birth)\s+)?(?:chart|big (?:three|3)|placements|signs)?\s*(?:is\s+|are\s+|:\s*|-\s*|=\s*|–\s*)?|\bme\s*[:=–-]\s*)",
        self_lead()
    )
}

fn typo_lead() -> String {
    format!(
        r"(?:{}|\bi\s+(?:always\s+|usually\s+|consistently\s+|mostly\s+|also\s+)?(?:test|tested|type|typed|got|get|score|scored)(?:\s+myself)?(?:\s+out)?(?:\s+as)?\s+(?:an?\s+)?|\bmy\s+(?:mbti|myers[- ]briggs|enneagram|enneatype|tritype|(?:instinctual\s+)?stacking|instinctual variant|socionics|personality|type|typology|core type|results?)(?:\s+(?:type|types|result|results))?\s*(?:is\s+|are\s+|:\s*|-\s*|=\s*|–\s*|\(\s*)?|\bme\s*[:=–-]\s*)",
        self_lead()
    )
}

fn strict_item() -> String {
    format!(r"(?:(?:\d{{1,2}}(?:st|nd|rd|th)?\s?h(?:ouse)?\s+)?{ANY_SIGN}[ \t-]{{0,2}}{PLACE}|{PLACE}(?:\s+sign)?(?:\s+is\s+in|\s+is|\s+in|:|\s*=|\s+-)?\s+(?:an?\s+)?{FULL_SIGN})")
}

fn item() -> String {
    format!(r"(?:{}|{PLACE})", strict_item())
}

regex!(ASTRO, format!("(?:{})(?:{}{SEP})*$", astro_lead(), item()));
regex!(OPENING, format!(r"^\W*{}{SEP}(?:{}{SEP})*$", strict_item(), item()));
regex!(BARE_START, r"^\W*$");
regex!(NEXT_ITEM, format!("{SEP}{}", strict_item()));
regex!(THIRDS, THIRD);
regex!(TYPO, format!("(?:{})(?:{TOKEN}{SEP})*$", typo_lead()));
regex!(TRI, format!(r"(?:(?:{})(?:{TOKEN}{SEP})+|\bmy\s+tritype\s*(?:is\s+|:\s*|-\s*|=\s*)?)$", typo_lead()));
regex!(KINSHIP, format!(r"(?:{ME}[ \t]+{ADVERB}|{}\s+|(?:^|[\n.!?,;]\s*|\bme\s+)being\s+)(?:an?\s+)?(?:{}|(?:and|&|,)[ \t]+(?:an?[ \t]+)?){{0,4}}(?:{IDENTITY}[\s,/&+]*(?:(?:and|but|also)\s+)*(?:an?\s+)?{}{{0,2}})*$", as_lead(), adj(), adj()));
regex!(ALTERNATIVE, format!(r"(?:{TOKEN})\s*,?\s*(?:/|\bor\b|\bvs\.?)\s*(?:an?\s+)?$"));
regex!(ASTRO_AFTER, format!(r"(?:{SEP}{})*(?:[ \t-]*(?:'s\s+)?(?:(?:wo)?man\s+|guy\s+|girl\s+)?(?:bf|gf|boyfriend|girlfriend|husband|hubby|wife|partner|friends?|mom|mum|dad|mother|father|sons?|daughters?|sister|brother|crush|ex|coworker|boss|kids?|baby|child|cousin|aunt|uncle|people|folks|men|women|guys|girls|energy|season|transit|placements?|natives?|traits?|compatibility)\b|[ \t]*,?[ \t]*(?:you|your|you're|u|ur)\b)", item()));
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

fn opening(m: &Match) -> bool {
    let s = m.string;
    let listed = OPENING.test_in(s, 0, m.start()) || BARE_START.test_in(s, 0, m.start()) && NEXT_ITEM.at(s, m.end()).is_some();
    listed && !THIRDS.test_in(s, 0, next_mark(s, m.end(), ".!?\n")) && !HEDGE.test_in(s, 0, m.start()) && ASTRO_AFTER.at(s, m.end()).is_none()
}

fn alone(m: &Match) -> bool {
    !ALTERNATIVE.test_in(m.string, m.start().saturating_sub(40), m.start())
}

fn placed(m: &Match) -> V {
    if chained(m, &ASTRO, &ASTRO_AFTER) || opening(m) {
        get(SIGNS, m.group(1))
    } else {
        None
    }
}

fn typed(m: &Match) -> bool {
    chained(m, &TYPO, &TYPO_AFTER) && alone(m)
}

fn mbti(m: &Match) -> Option<String> {
    (typed(m) && !LISTED.test_in(m.string, m.start().saturating_sub(40), m.start())).then(|| m.g(1))
}

fn adjacent(core: u32, wing: u32) -> bool {
    core.abs_diff(wing) == 1 || core + wing == 10 && (core == 1 || core == 9)
}

fn wing(m: &Match) -> V {
    let core = m.group(1).and_then(|g| g.first()).and_then(|c| c.to_digit(10))?;
    let side = m.group(2).and_then(|g| g.first()).and_then(|c| c.to_digit(10))?;
    if adjacent(core, side) && typed(m) {
        get(ENNEAGRAM, m.group(1))
    } else {
        None
    }
}

fn core(m: &Match) -> V {
    if typed(m) {
        get(ENNEAGRAM, m.group(1))
    } else {
        None
    }
}

fn stacking(m: &Match) -> Option<String> {
    let (first, second) = (m.g(1), m.g(2));
    (first != second && typed(m)).then(|| format!("{first}/{second}"))
}

fn center(digit: char) -> Option<u8> {
    match digit {
        '8' | '9' | '1' => Some(0),
        '2' | '3' | '4' => Some(1),
        '5' | '6' | '7' => Some(2),
        _ => None,
    }
}

fn tritype(m: &Match) -> Option<String> {
    let digits = m.text();
    let mut centers: Vec<u8> = digits.iter().filter_map(|&c| center(c)).collect();
    centers.sort();
    centers.dedup();
    if centers.len() == 3 && chained(m, &TRI, &TYPO_AFTER) && alone(m) {
        Some(st(digits))
    } else {
        None
    }
}

fn plain(m: &Match) -> V {
    let shouted = m.span(1).and_then(|(a, b)| original(m.string).map(|text| st(&text[a..b]) == "LEO"));
    if shouted == Some(true) {
        None
    } else {
        get(SIGNS, m.group(1))
    }
}

fn kin(m: &Match) -> V {
    if KINSHIP.test_in(m.string, last_mark(m.string, m.start(), ".!?\n").max(m.start().saturating_sub(120)), m.start()) {
        get(IDENTITIES, m.group(1))
    } else {
        None
    }
}

static IDENTITIES: &Tab = &[("therian", "therian"), ("otherkin", "otherkin"), ("fictionkin", "fictionkin"), ("alterhuman", "alterhuman"), ("polymorphkin", "polymorphkin"), ("furry", "furry")];

fn astrology() -> Vec<Rule> {
    let places = [
        ("sun_sign", r"(?:sun(?![\w'])|☉|☀|🌞)", "sun", ["sun", "☉", "☀", "🌞"]),
        ("moon_sign", r"(?:moon(?![\w'])|☽|☾|🌙)", "moon", ["moon", "☽", "☾", "🌙"]),
        ("rising_sign", r"(?:(?:rising|ascendant|asc)(?![\w'])|↑)", "rising|ascendant", ["rising", "ascendant", "asc", "↑"]),
    ];
    let mut rules = Vec::new();
    for (attribute, place, words, anchors) in places {
        rules.push(needs(r(attribute, &format!(r"(?<![\w'])(?:{ANY_SIGN})[ \t-]{{0,2}}{place}"), placed, hedge()), &anchors));
        rules.push(needs(r(attribute, &format!(r"(?<![\w'])(?:{words})(?:\s+sign)?(?:\s+is\s+in|\s+is|\s+in|:|\s*=|\s+-)?\s+(?:an?\s+)?{FULL_SIGN}(?![\w']){OTHER_PLACE}"), placed, hedge()), &anchors));
        rules.push(needs(r(attribute, &format!(r"(?:^|[\n.!?])\W*(?:(?:a\s+)?fellow\s+)?(?:{ANY_SIGN})[ \t-]{{0,2}}{place}\s+here\b"), |m| get(SIGNS, m.group(1)), hedge()), &anchors));
    }
    let adj = adj();
    rules.push(r(
        "sun_sign",
        &format!(r"(?:{ME}|{})\s+(?:also\s+)?an?\s+{adj}{{0,2}}{FULL_SIGN}(?!\s*,?\s*(?:you|your|you're|u|ur)\b)(?=\s*(?:[^\w\s'-]|$|(?:and|but|so|too|myself|here|lol|haha|btw|though|tho|also|sun|woman|man|girl|guy|female|male|through)\b))", as_lead()),
        plain,
        hedge(),
    ));
    rules.push(r(
        "sun_sign",
        &format!(r"\bmy\s+(?:(?:sun|star|zodiac|astrological|astrology|western|tropical|birth)\s+)?sign(?:\s+is|:|\s*=|\s+-)?\s+(?:an?\s+)?{FULL_SIGN}(?![\w']){OTHER_PLACE}"),
        |m| get(SIGNS, m.group(1)),
        hedge(),
    ));
    rules.push(r("sun_sign", &format!(r"(?:^|[\n.!?])\W*(?:a\s+)?fellow\s+{FULL_SIGN}\s+here\b"), |m| get(SIGNS, m.group(1)), hedge()));
    rules.push(r("sun_sign", &format!(r"(?:^|\n)[^\w\n]*(?:zodiac|star|sun|astrological)\s+sign\s*[:=-]\s*{FULL_SIGN}(?![\w'])"), |m| get(SIGNS, m.group(1)), hedge()));
    rules
}

fn typology() -> Vec<Rule> {
    let after = format!(r"(?!\s*(?:/|or\b|vs\b)\s*(?:an?\s+)?{TOKEN})");
    let listed = format!(r"(?!s?\s*(?:,|and\b)\s*(?:and\s+)?(?:an?\s+)?{MBTI}(?![a-z]))");
    vec![
        rule("mbti_type", &format!(r"(?<![\w'/-])({MBTI})(?:-[at])?(?![\w']){after}{listed}"), mbti, hedge()),
        rule("mbti_type", &format!(r"(?:^|[\n.!?])\W*(?:(?:a\s+)?fellow\s+)?({MBTI})(?:-[at])?\s+here\b"), |m| Some(m.g(1)), hedge()),
        r("enneagram_type", &format!(r"(?<![\w'/.,-])([1-9])\s?w\s?([1-9])(?![\w']){after}"), wing, hedge()),
        r("enneagram_type", r"(?<![\w'/.,-])(?:type\s+)?([1-9])\s+with\s+an?\s+(?:(?:strong|slight|heavy|big|small)\s+)?([1-9])[\s-]?wing\b", wing, hedge()),
        r("enneagram_type", &format!(r"(?<![\w'/])(?:sp|sx|so)([1-9])(?:w[1-9])?(?![\w']){after}"), core, hedge()),
        needs(r("enneagram_type", &format!(r"\b(?:enneagram\s+)?type\s+([1-9])(?![\w'.,])(?!\s*diabet){after}"), core, hedge()), &["enneagram", "enneatype"]),
        r("enneagram_type", r"\bmy\s+(?:enneagram|enneatype)(?:\s+type)?\s*(?:is\s+|:\s*|-\s*|=\s*)?(?:an?\s+)?(?:type\s+)?([1-9])(?![\w'.,])", |m| get(ENNEAGRAM, m.group(1)), hedge()),
        rule("instinctual_variant", &format!(r"(?<![\w'/])(sp|sx|so)\s?[/>]\s?(sp|sx|so)(?:\s?[/>]\s?(?:sp|sx|so))?(?![\w']){after}"), stacking, hedge()),
        needs(
            rule("enneagram_tritype", r"(?<![\w'.,/:$#£€-])[1-9][1-9][1-9](?![\w'.,/:%-])", tritype, hedge()),
            &["tritype", "enneagram", "w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8", "w9", "sx/", "sp/", "so/", "/sx", "/sp", "/so"],
        ),
        rule("socionics_type", &format!(r"\bmy\s+socionics(?:\s+type)?\s*(?:is\s+|:\s*|-\s*|=\s*)?(?:an?\s+)?{CODE}(?![a-z])"), |m| Some(m.g(1)), hedge()),
        needs(rule("socionics_type", &format!(r"(?:{ME}|{})\s+(?:an?\s+)?{CODE}(?:-\w+)?(?![\w'])", as_lead()), |m| Some(m.g(1)), hedge()), &["socionics"]),
    ]
}

fn attachment() -> Vec<Rule> {
    let degree = r"(?:(?:very|pretty|super|really|extremely|more|mostly|strong|strongly|severe|severely|classic|textbook|definite|naturally|definitely|quite|fairly|so)\s+)";
    vec![
        r("attachment_style", &format!(r"\bi\s+(?:have|'ve got|ve got|probably have|definitely have|tend to have|lean)\s+(?:an?\s+|the\s+)?{degree}*{ATTACH}\s+attachment"), |m| get(STYLES, m.group(1)), hedge()),
        r("attachment_style", &format!(r"\bmy\s+(?:attachment\s+style\s+(?:is\s+|:\s*)(?:an?\s+)?{degree}*{ATTACH}|{ATTACH}\s+attachment)"), |m| get(STYLES, m.group(1).or(m.group(2))), hedge()),
        r("attachment_style", &format!(r"{ME}\s+{degree}?(securely|anxiously|avoidantly)\s+attached"), |m| get(STYLES, m.group(1)), hedge()),
        r("attachment_style", &format!(r"{ME}\s+(?:an?\s+)?{degree}?(fearful[- ]avoidant|dismissive[- ]avoidant|anxious[- ]preoccupied)(?![\w-])"), |m| get(STYLES, m.group(1)), hedge()),
        needs(r("attachment_style", &format!(r"{ME}\s+(?:an?\s+)?fa(?![\w'-])"), constant(FEARFUL), hedge()), &["avoidant", "attach"]),
    ]
}

fn identity() -> Vec<Rule> {
    vec![
        r("identity_community", &format!(r"(?<![\w'-]){IDENTITY}(?![\w'-])(?!\s+(?:friends?|animals?|bab(?:y|ies)|creatures?|pets?|thing|ones?|kids?|companions?|family|tail|ears)\b)"), kin, hedge()),
        r("identity_community", &format!(r"(?:^|[\n.!?])\W*(?:(?:a\s+)?fellow\s+)?(?:(?!(?:my|your|his|her|their|the|a|an|no|not)\b)[\w-]+\s+){{0,2}}{IDENTITY}\s+here\b"), |m| get(IDENTITIES, m.group(1)), hedge()),
        r("identity_community", r"\bmy\s+(?:own\s+|main\s+|current\s+|new\s+|first\s+|old\s+)?fursonas?\b", constant("furry"), hedge()),
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

fn sorted(m: &Match) -> V {
    if THIRDS.test_in(m.string, last_mark(m.string, m.start(), ".!?\n"), m.start()) {
        None
    } else {
        get(HOUSES, m.first())
    }
}

fn social() -> Vec<Rule> {
    let intro = ["introvert", "extrovert", "extravert", "ambivert", "omnivert"];
    let houses = ["gryffindor", "hufflepuff", "ravenclaw", "slytherin"];
    let after = r"(?![\w'-])(?!\s+(?:friends?|partners?|husband|wife|boyfriend|girlfriend|types?|kids?|son|daughter|crush)\b)";
    vec![
        needs(r("introversion", &format!(r"{ME}\s+(?:{DEGREE}\s+){{0,4}}{INTRO}{after}"), |m| get(SOCIAL, m.group(1)), hedge()), &intro),
        needs(r("introversion", &format!(r"{}\s+an?\s+(?:{DEGREE}\s+){{0,2}}{INTRO}{after}", as_lead()), |m| get(SOCIAL, m.group(1)), hedge()), &intro),
        needs(r("introversion", &format!(r"\bi\s+(?:would\s+|'d\s+)?(?:consider|call|describe|see|identify)\s+(?:myself\s+)?(?:as\s+)?(?:{DEGREE}\s+){{0,3}}{INTRO}{after}"), |m| get(SOCIAL, m.group(1)), hedge()), &intro),
        needs(r("introversion", &format!(r"(?:^|[\n.!?])\W*(?:(?:a|fellow|another|shy|big|huge|total|extreme|introverted|extroverted)\s+){{0,2}}{INTRO}\s+here\b"), |m| get(SOCIAL, m.group(1)), hedge()), &intro),
        needs(r("introversion", &format!(r"(?:^|\n)[ \t*_-]*(?:(?:an?|total|huge|big|massive|extreme|shy|introverted|extroverted|proud)\s+){{0,2}}{INTRO}[ \t*_.!]*(?:\n|$)"), |m| get(SOCIAL, m.group(1)), hedge()), &intro),
        needs(r("love_language", &format!(r"(?<![\w-]){LOVE}(?![\w-])"), loving, hedge()), &["love language"]),
        needs(r("hogwarts_house", &format!(r"{ME}\s+(?:(?:a|an|such a|definitely|totally|proud|true|total|full|100%|die[- ]hard|always|also|been)\s+){{0,3}}{HOUSE}(?![\w'-])(?!\s+(?:common room|house|scarf|colou?rs?|fan|merch|robes?|quidditch|students?)\b)"), |m| get(HOUSES, m.group(1)), hedge()), &houses),
        needs(r("hogwarts_house", &format!(r"(?:^|[\n.!?])\W*(?:(?:a|fellow|proud|another)\s+){{0,2}}{HOUSE}s?\s+here\b|(?:^|\n)\W*(?:a\s+)?proud\s+{HOUSE}\b"), |m| get(HOUSES, m.first()), hedge()), &houses),
        needs(r("hogwarts_house", &format!(r"\b(?:a\s+)?proud\s+{HOUSE}\b(?!\s+(?:fans?|parents?|mom|mum|dad|kids?|family)\b)|\|[ \t]*{HOUSE}(?:[ \t]*[\p{{So}}\x{{fe0f}}])*(?=[ \t]*(?:\||\n|$))|(?<![^\n|])[ \t]*{HOUSE}(?:[ \t]*[\p{{So}}\x{{fe0f}}])*[ \t]*\|"), sorted, hedge()), &houses),
        needs(r("hogwarts_house", &format!(r"\bmy\s+(?:hogwarts\s+)?house\s+(?:is|=|:)\s+(?:definitely\s+)?{HOUSE}|\bi\s+(?:always\s+)?(?:got|get|was|am|'m|'ve been|have been)\s+(?:always\s+)?sorted\s+(?:into\s+|in\s+)?{HOUSE}|\b(?:pottermore|the sorting hat|the quiz|wizarding world)\s+(?:always\s+)?(?:sorted|put|puts|placed)\s+me\s+(?:in|into)\s+{HOUSE}"), |m| get(HOUSES, m.first()), hedge()), &houses),
    ]
}

pub fn build() -> Vec<Rule> {
    timed("life.traits", || {
        let mut rules = astrology();
        rules.extend(typology());
        rules.extend(attachment());
        rules.extend(identity());
        rules.extend(social());
        log(&format!("life traits rules={}", rules.len()));
        rules
    })
}
