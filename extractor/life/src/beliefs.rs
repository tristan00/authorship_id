use crate::shared::{self, *};
use claimcore::*;

const UNSTATED: &str = "ex-religious (religion unstated)";
const JW: &str = "ex-jehovah's witness";

static LEFT: &Tab = &[
    ("christian", "ex-christian"), ("christianity", "ex-christian"), ("baptist", "ex-christian"), ("catholic", "ex-catholic"), ("catholicism", "ex-catholic"), ("the catholic church", "ex-catholic"),
    ("muslim", "ex-muslim"), ("moslem", "ex-muslim"), ("islam", "ex-muslim"), ("mormon", "ex-mormon"), ("mormonism", "ex-mormon"), ("lds", "ex-mormon"), ("mo", "ex-mormon"),
    ("the lds church", "ex-mormon"), ("the mormon church", "ex-mormon"), ("jw", JW), ("jehovah's witness", JW), ("the jehovah's witnesses", JW), ("evangelical", "ex-evangelical"),
    ("vangelical", "ex-evangelical"), ("pentecostal", "ex-evangelical"), ("evangelicalism", "ex-evangelical"), ("jew", "ex-jewish"), ("jewish", "ex-jewish"), ("judaism", "ex-jewish"),
    ("hindu", "ex-hindu"), ("hinduism", "ex-hindu"), ("religious", UNSTATED), ("religion", UNSTATED), ("my religion", UNSTATED), ("the faith", UNSTATED), ("my faith", UNSTATED),
    ("organized religion", UNSTATED), ("organised religion", UNSTATED),
];
static UPBRINGING: &Tab = &[
    ("roman catholic", "catholic"), ("catholic", "catholic"), ("christian", "christian (unspecified)"), ("southern baptist", "baptist"), ("baptist", "baptist"), ("lutheran", "lutheran"),
    ("methodist", "methodist"), ("presbyterian", "presbyterian"), ("evangelical", "evangelical / pentecostal"), ("pentecostal", "evangelical / pentecostal"), ("mormon", "latter-day saint"),
    ("lds", "latter-day saint"), ("jehovah's witness", "jehovah's witness"), ("jehovah's witnesses", "jehovah's witness"), ("jw", "jehovah's witness"), ("greek orthodox", "orthodox christian"),
    ("russian orthodox", "orthodox christian"), ("eastern orthodox", "orthodox christian"), ("orthodox jewish", "jewish"), ("orthodox jew", "jewish"), ("orthodox", "orthodox christian"),
    ("anglican", "anglican / episcopalian"), ("episcopal", "anglican / episcopalian"), ("episcopalian", "anglican / episcopalian"), ("church of england", "anglican / episcopalian"),
    ("muslim", "muslim"), ("islamic", "muslim"), ("jewish", "jewish"), ("hindu", "hindu"), ("buddhist", "buddhist"), ("religious", "religious (unspecified)"),
    ("secular", "secular / non-religious"), ("atheist", "secular / non-religious"), ("non-religious", "secular / non-religious"), ("nonreligious", "secular / non-religious"),
    ("non religious", "secular / non-religious"), ("irreligious", "secular / non-religious"), ("without religion", "secular / non-religious"), ("with no religion", "secular / non-religious"),
    ("without any religion", "secular / non-religious"),
];

const LABEL: &str = r"(christian|catholic|muslim|moslem|mormon|lds|mo|jw|jehovah's witness|evangelical|vangelical|pentecostal|baptist|jew|jewish|hindu|religious)";
const LEFT_FAITH: &str = r"(christianity|catholicism|the catholic church|islam|mormonism|the lds church|the mormon church|the jehovah's witnesses|judaism|hinduism|evangelicalism|organi[sz]ed religion|my religion|religion|the faith|my faith)";
const NOT_PLACE: &str = r"(?! (?:school|schools|church|churches|priest|nun|friends?|family|families|parents|members?|community|subreddit|sub|forum|country|countries|area|town|city|neighbou?rhood|culture|part|region|kids?|mom|dad|mother|father)\b)";
const MODS: &str = r"(?:(?:very|strict|strictly|devout|devoutly|super|fairly|pretty|strongly|deeply|heavily|conservative|fundamentalist|traditional|practicing|practising|religious|staunch|hardcore|culturally|nominally|mostly|loosely),? )*";
const FILL: &str = r"(?: (?!he\b|she\b|they\b|you\b|his\b|her\b|their\b|your\b|my\b|was\b|is\b|are\b|were\b|kids?\b|children\b|son\b|daughter\b|wife\b|husband\b|partner\b|not\b|never\b)[\w-]+){0,3}";

fn faith_of(table: &Tab) -> String {
    let mut words = keys(table);
    words.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()));
    alternation(words)
}

fn former() -> Vec<Rule> {
    let label = format!(r"(?:ex[- ]?{LABEL}|(?:former|formerly|lapsed|recovering) (?:an? )?{LABEL})\b{NOT_PLACE}");
    vec![
        r("former_religion", &format!(r"(?:i(?<=\bi)(?:'m| am|m| m|'ve been| have been)|{AS}) (?:an? )?(?:(?!not\b|never\b|no\b|an?\b)[\w-]+ ){{0,2}}?(?:an? )?{label}"), |m| get(LEFT, m.first()), self_hedge()),
        r("former_religion", &format!(r"(?:\A{flair}|[.!?\n(])\W*(?:(?:a|an|another|also|fellow|proud|closeted|happily|cradle) )*{label}(?: (?:here|myself)\b|(?: too)?[ \t]*(?:[.!,|]|\n|\Z))|\|[ \t]*ex[- ]?{LABEL}[ \t]*(?:\||\n|\Z)", flair = claimcore::flair!()), |m| get(LEFT, m.first()), self_hedge()),
        r("former_religion", &format!(r"i(?<=\bi)(?:'ve| have)?(?: (?!not\b|never\b|almost\b|nearly\b|havent\b|didnt\b|dont\b|cant\b|wont\b|could\b|would\b|should\b|might\b|will\b|want\b|wanted\b|wanna\b|can\b|cannot\b)\w+){{0,2}}? (?:left|deconverted from|walked away from|renounced|abandoned|apostati[sz]ed from) {LEFT_FAITH}\b"), |m| get(LEFT, m.first()), self_hedge()),
        r("former_religion", r"i(?<=\bi)(?:'ve| have)? (?:(?!not\b|never\b|no\b|havent\b|hadnt\b|didnt\b|dont\b|cant\b|wont\b|almost\b|nearly\b)\w+ )?deconverted\b(?! from\b)", constant(UNSTATED), self_hedge()),
    ]
}

fn upbringing() -> Vec<Rule> {
    let faith = faith_of(UPBRINGING);
    let lead = format!(r"(?:i(?<=\bi)(?: was| were| got|'m| am|'ve been| have been| had been|'d been){FILL}(?: born and)? (?:raised|brought up)|i(?<=\bi){FILL} grew up|we(?<=\bwe) (?:were|all|both)(?: \w+)? (?:raised|brought up)|we(?<=\bwe)(?: \w+)? grew up|(?:\A{flair}|[.!?\n(:*]) ?(?:was |also )?(?:born and raised|raised|grew up|brought up)|a(?<=\ba)s (?:someone|a [\w-]+ (?:person|woman|man|guy|girl|kid))(?: who was| that was)? (?:raised|brought up)|a(?<=\ba)s someone (?:who|that) grew up|(?:d(?<=\bd)espite|a(?<=\ba)fter|s(?<=\bs)ince|m(?<=\bm)y) being (?:raised|brought up)|h(?<=\bh)aving been (?:raised|brought up))", flair = claimcore::flair!());
    let tail = format!(r"(?: (?:as )?(?:an? )?{MODS}({faith})\b{NOT_PLACE}| in (?:a |an |the )?{MODS}({faith})(?: [\w-]+)? (?:family|household|house|home|church|faith|tradition|environment|congregation|denomination|cult)\b| in the (church of england)\b| by (?:a |an |my )?{MODS}({faith}) (?:parents|family|mom|dad|mother|father|grandparents)\b)");
    vec![
        r("religious_upbringing", &format!(r"{lead}{tail}"), |m| get(UPBRINGING, m.first()), self_hedge()),
        r("religious_upbringing", r"i(?<=\bi) (?:wasn't|was not|wasnt) (?:raised|brought up) (?:religious(?:ly)?|in a religious (?:family|household|home))\b", constant("secular / non-religious"), self_hedge()),
    ]
}

pub fn build() -> Vec<Rule> {
    timed("life.beliefs", || {
        let mut rules = shared::scoped_rules(former());
        rules.extend(shared::scoped_rules(upbringing()));
        log(&format!("life beliefs rules={}", rules.len()));
        rules
    })
}
