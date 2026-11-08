use crate::shared::{self, *};
use claimcore::*;

const FREE: &str = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|neither\b|nor\b|either\b|considering\b|becoming\b|getting\b)\w+ )?";
const FILLER: &str = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b)[\w-]+,? (?:and )?){0,2}?(?:a |an )?";
const ME: &str = r"(?:'m|m| am|am| m|'am|'?ve been|'ve always been| myself am| my self am| have been| have always been)";

static RELIGIONS: &Tab = &[
    ("christian", "christian"), ("catholic", "christian"), ("protestant", "christian"), ("mormon", "christian"), ("lds", "christian"), ("baptist", "christian"), ("methodist", "christian"),
    ("lutheran", "christian"), ("evangelical", "christian"), ("orthodox christian", "christian"), ("muslim", "muslim"), ("jew", "jewish"), ("jewish", "jewish"), ("hindu", "hindu"),
    ("buddhist", "buddhist"), ("sikh", "sikh"), ("pagan", "pagan or other religion"), ("wiccan", "pagan or other religion"), ("witch", "pagan or other religion"),
    ("spiritual", "spiritual, no religion"), ("agnostic", "agnostic"), ("atheist", "atheist"), ("presbyterian", "christian"), ("anglican", "christian"), ("episcopalian", "christian"), ("pentecostal", "christian"),
    ("adventist", "christian"), ("quaker", "christian"), ("mennonite", "christian"), ("coptic", "christian"), ("sunni", "muslim"), ("shia", "muslim"), ("shiite", "muslim"), ("moslem", "muslim"),
    ("satanist", "pagan or other religion"), ("polytheist", "pagan or other religion"), ("animist", "pagan or other religion"),
    ("taoist", "pagan or other religion"), ("jain", "pagan or other religion"), ("zoroastrian", "pagan or other religion"), ("rastafarian", "pagan or other religion"), ("luciferian", "pagan or other religion"),
    ("deist", "pagan or other religion"), ("pantheist", "pagan or other religion"), ("unitarian", "pagan or other religion"), ("shintoist", "pagan or other religion"),
    ("greek orthodox", "christian"), ("russian orthodox", "christian"), ("eastern orthodox", "christian"), ("jehovah's witness", "christian"), ("latter-day saint", "christian"), ("latter day saint", "christian"),
    ("secular humanist", "atheist"), ("humanist", "atheist"), ("nonbeliever", "atheist"), ("non-believer", "atheist"), ("athiest", "atheist"), ("christan", "christian"), ("bahai", "pagan or other religion"), ("baha'i", "pagan or other religion"),
];
static STEMS: &Tab = &[
    ("مسلم", "muslim"), ("مسيح", "christian"), ("ملحد", "atheist"), ("ate", "atheist"), ("athe", "atheist"), ("athé", "atheist"), ("musul", "muslim"), ("muzu", "muslim"), ("muslim", "muslim"), ("moslim", "muslim"),
    ("jud", "jewish"), ("jüd", "jewish"), ("juif", "jewish"), ("juive", "jewish"), ("ebre", "jewish"), ("joods", "jewish"), ("agnost", "agnostic"), ("agnóst", "agnostic"),
    ("cat", "christian"), ("kat", "christian"), ("crist", "christian"), ("christ", "christian"), ("chrét", "christian"), ("chrz", "christian"), ("evang", "christian"),
    ("krist", "christian"), ("hrist", "christian"), ("pravoslav", "christian"), ("христиан", "christian"), ("православн", "christian"), ("католи", "christian"), ("атеист", "atheist"),
    ("мусульман", "muslim"), ("müslüman", "muslim"), ("buddh", "buddhist"), ("hindu", "hindu"), ("deist", "pagan or other religion"),
];
static ISMS: &Tab = &[
    ("catholicism", "christian"), ("christianity", "christian"), ("islam", "muslim"), ("judaism", "jewish"), ("buddhism", "buddhist"), ("hinduism", "hindu"), ("sikhism", "sikh"), ("paganism", "pagan or other religion"),
    ("wicca", "pagan or other religion"), ("orthodoxy", "christian"), ("mormonism", "christian"), ("protestantism", "christian"), ("atheism", "atheist"), ("agnosticism", "agnostic"), ("christ", "christian"), ("jesus", "christian"),
    ("the catholic church", "christian"), ("the orthodox church", "christian"), ("the lds church", "christian"),
];
static POLITICS: &Tab = &[
    ("communist", "communist or far left"), ("marxist", "communist or far left"), ("socialist", "socialist or left"), ("leftist", "socialist or left"), ("liberal", "progressive or liberal"),
    ("progressive", "progressive or liberal"), ("democrat", "progressive or liberal"), ("centrist", "centrist or moderate"), ("moderate", "centrist or moderate"),
    ("conservative", "conservative or right"), ("republican", "conservative or right"), ("libertarian", "libertarian"), ("anarchist", "anarchist"),
    ("nationalist", "nationalist or far right"), ("apolitical", "apolitical"), ("lefty", "socialist or left"), ("commie", "communist or far left"),
];
static STANCES: &Tab = &[
    ("prochoice", "progressive or liberal"), ("prolife", "conservative or right"), ("antiabortion", "conservative or right"), ("anticapitalist", "socialist or left"), ("antiwoke", "conservative or right"),
    ("republicans", "conservative or right"), ("red", "conservative or right"), ("right", "conservative or right"), ("democrats", "progressive or liberal"), ("dems", "progressive or liberal"), ("blue", "progressive or liberal"),
    ("left", "socialist or left"), ("libertarian", "libertarian"), ("green", "progressive or liberal"), ("dem", "progressive or liberal"),
];
static LEAN: &Tab = &[("left", "progressive or liberal"), ("right", "conservative or right")];
static VOTED: &Tab = &[("left", "progressive or liberal"), ("right", "conservative or right"), ("republican", "conservative or right"), ("gop", "conservative or right")];
static DIETS: &Tab = &[
    ("vegan", "vegan"), ("vegetarian", "vegetarian"), ("veggie", "vegetarian"), ("pescatarian", "pescatarian"), ("pescetarian", "pescatarian"), ("keto", "keto or low carb"),
    ("halal", "halal or kosher"), ("kosher", "halal or kosher"), ("gluten free", "gluten free"), ("gluten-free", "gluten free"),
    ("low carb", "keto or low carb"), ("low-carb", "keto or low carb"), ("ketogenic", "keto or low carb"), ("carnivore", "keto or low carb"), ("plant based", "vegan"), ("plant-based", "vegan"),
    ("vegeterian", "vegetarian"), ("vegitarian", "vegetarian"),
];

const TAKEN: &str = r"(?:(?:a|an|fully|strictly|full|mostly|completely|strict) )?(vegan|vegetarian|vegeterian|vegitarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly|cheese|version|alternatives?|products?|brand|friends?|community|people|diet for)\b)";
const SMOKED: &str = r"(?:a |my |some |the |half a |a whole )?(?:weed|pot|cigs?|cigarettes?|blunts?|joints?|bowls?|spliffs?|tobacco|cigars?|pipe|dabs?|carts?|j|bud|herb|packs?|hookah|shisha|nic|nicotine)\b";
const QUIT_SPAN: &str = r"(?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes)|after (?:vaping|smoking) (?:since|for))\b";
const BRANCH: &str = r"(?:(?:us|u\.s\.|british|canadian|australian|indian|royal|israeli) )?(?:army|navy|marines|marine corps|air force|usaf|usmc|military|coast guard|national guard|air national guard|armed forces|army reserves?|navy reserves?|reserves|raf|idf|space force|airforce)\b";
const UNDECLINED: &str = r"(?:(?!never\b|almost\b|nearly\b|should\b|could\b|would\b|might\b|will\b|wanted\b|want\b|wanna\b|didn't\b|didnt\b|don't\b|dont\b|won't\b|wont\b|wouldn't\b|wish\b|hope\b|plan\b|planning\b|thinking\b|considering\b|trying\b|tried\b|not\b)[\w']+ )";
const SERVED_NOUN: &str = r"(?:us |u\.s\. )?(?:military|army|navy|marines?|marine corps|air force|airforce|usaf|usmc|coast guard|national guard|infantry|enlisted|service ?member|soldier|sailor|airman|paratrooper|infantryman)\b";
const VET: &str = r"(?:a |an )?(?:proud |disabled |combat |retired |former |old )?(?:(?:us |u\.s\. )?(?:army|navy|marine|marine corps|air force|af|usaf|military|usmc|combat|war|coast guard|national guard|gwot) )?(?:vet|veteran)\b(?! (?:tech|clinic|bill|school|student|player|gamer|member|user|fan|raider|streamer|poster|of (?:the|this))\b)";
const VA: &str = r"[^.!?\n]{0,40}?\b(?:va claim|va rating|va disability|dd-?214|c&p exam|nexus letter|service[- ]connected|100% p&t|the va\b(?! (?:area|beach|state|border|side|suburbs|region)\b))\b";

regex!(TAG_NEAR, r"(?<![\w$#.,'/:+-])(?:\d{2} ?(?:[mf]|male|female|yo|y/o|yrs?|years? old)|[mf] ?\d{2}|(?:\d{2} ?)?[\[\(]?[mf]4[mfa]\w*[\]\)]?)(?![\w'%])");
regex!(NOT_SELF, r"\b(?:if|would|wish|hope|not|never|ex|former|raised|born|for|looking|seeking|into|with|any|wants?|interfaith|than|like|non|anti|no|other|lapsed)\b|\b(?:a|an|the|by|real|some|your|his|her|their)\s+$");
regex!(LISTED_LINE, r"[ \t]*(?:[-*•]|\d+[.)])?[ \t]*(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ )?(.+)");
regex!(LISTED_ITEM, r"[ \t]*(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ )?(.+)");
regex!(SELF_NEAR, r"\b(?:i|i'm|im|i've|ive|me|my|we)\b");
regex!(OTHER_NEAR, r"\b(?:you|he|she|they|people|someone|somebody|anyone|everyone|his|her|their|your|friends?|dad|mom|father|mother|grandfather|grandpa|granddad|uncle|brother|sister|cousin|husband|wife|spouse|boyfriend|girlfriend|fiance|fiancee|partner|kids?|son|daughter)\b");
regex!(ADOPTED, r"\b(?:my|on|eating|following|follow|followed|started|adopted|switched to|stick to|stuck to|thanks to|due to|doing) (?:a |an |the )?(?:(?:strict|strictly|mostly|fully|very|nearly|almost|100%|\d+%|whole food|healthy|clean) )*\Z");
regex!(STARTED, r"\b(?:on|doing|started|start|eating|following|going|went|been|stay|staying) (?:strict |a strict |full |proper |properly |mostly |strictly )?\Z");
regex!(FOODWAY, r"vegan|vegetarian|veggie|pescatarian|pescetarian|keto|low[- ]carb|gluten[- ]free|plant[- ]based|halal|kosher|carnivore");
regex!(NOT_DIET, r" (?:diet|recipes?|friendly|meals?|food|snacks?|bread|options?|version)\b");
regex!(UNTAKEN, r"\b(?:was|were|had|stopped|quit|want|wanted|wanna|trying|try|tried|thinking|considering|closest|hard|easy|didn't|never|not|no longer|used to|if|would|should|could|might|maybe)\b");
regex!(SMOKED_BEFORE, r"\b(?:was|were|did|had|used to|back then|back in|ago|when i was)\b");
regex!(ITEM, r"[ \t]*(?:[-*•]|\d+[.)])?[ \t]*(?:[^\w\s]+[ \t]*)?(?:(?:social|occasional|heavy|daily|light|casual|regular)[ -]+)?(?:drinker ?/ ?)?");
regex!(NO_SMOKERS, r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b");
regex!(SERVICE, r"\b(?:army|navy|marines?|military|usmc|air force|national guard|coast guard|deploy\w*|enlist\w*|veterans?|va|dd-?214|gi bill|mos|ets|boot ?camp|basic training|base|platoon|squadron|battalion|nco|sergeant|sgt|corporal|cpl|soldiers?|sailors?|airmen|servicemembers?|served)\b");
regex!(COUNTED, r"\b(?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|a few|several|many|a couple of) (?:\+ |plus )?\Z");
regex!(ENTERED, format!(r"\bi {UNDECLINED}?\Z"));
regex!(WITHIN, format!(r"\bi(?:'m|'ve)? {UNDECLINED}{{1,4}}?\Z"));
regex!(PAST, r"\b(?:was|were|had|did|used to|back then|back in|ago|got out|retired|served|after)\b");
regex!(DISCHARGED, r"dd|discharge|gi bill|separat|ets|eas|career|medal|pension");
regex!(REST, r"[^.!?\n]*");
regex!(HERE_LABEL, r"(?:^|[.!?,;(] *)(?:hey,? |also |another )?(fellow |proud |disabled |combat |retired |former |ex[- ]?|prior )?((?:us |u\.s\. )?(?:army|navy|marine|marine corps|air force|af|usaf|usmc|military|coast guard|national guard|combat|war|gwot) )?(veteran|vet|marine|soldier|sailor|airman|service ?member|active duty|reservist) (?:too )?\Z");
regex!(MILITARY_WORDS, r"\b(?:va|veterans?|military|service|army|navy|marines?|air force|usmc|vso|dbq|c&p)\b");
regex!(PIPE_TAG, r"(?<![^\n|])[ \t]*(?:\d{2}[ \t]*[mf]?|[mf]|male|female)[ \t]*(?![^\n|])");
regex!(WAR_WORDS, r"\b(?:army|navy|marines?|military|air ?force|usmc|usaf|coast guard|national guard|veterans?|deploy\w*|enlist\w*|combat|infantry|platoon|battalion|boot ?camp|tours? of duty|war|afghanistan|iraq|vietnam|overseas|idf|caf|raf|soldiers?|sergeant|corporal|troops)\b");
regex!(TITLE_OTHER, r"\b(?:for|seeking|looking|want|wants|wanna|need|needs|into|with|like|love|any|your|my|her|his|their)\b");
regex!(STANCE_JOIN, r"[- ]");
regex!(RELIGION_HERE, format!(r"(?:^|[.!?,;(] *)(?:(?!former\b|ex\b|recovering\b|lapsed\b|non\b|not\b|raised\b|born\b|anti\b|i\b|you\b|he\b|she\b|they\b|we\b|every\b|all\b|any\b|the\b|my\b|your\b|his\b|her\b|their\b|some\b|most\b|other\b|many\b|no\b|but\b|and\b|so\b|yeah\b|because\b|that\b|was\b|is\b|are\b)[\w-]+ ){{0,3}}(?:[\w-]+ and )?({}) (?:(?!former\b|ex\b|non\b|not\b|community\b|friends?\b|family\b|people\b)[\w-]+ ){{0,2}}\Z", faith()));
regex!(POLITICS_HERE, format!(r"(?:^|[.!?,;(] *)(?:a |an )?(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ ){{0,2}}?({}) \Z", party()));
regex!(DIET_HERE, r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian) \Z");

fn faith() -> String {
    alternation(RELIGIONS.iter().map(|(k, _)| *k))
}

fn party() -> String {
    keys(POLITICS).join("|")
}

fn quoted(m: &Match) -> bool {
    let line = &m.string[line_start(m.string, m.start())..m.start()];
    let count = |c: char| line.iter().filter(|&&x| x == c).count();
    count('"') % 2 == 1 || count('\u{201c}') > count('\u{201d}')
}

fn labelled(m: &Match, lead: &Re, table: &Tab) -> V {
    let found = lead.search(m.string, back(m, 80), m.start())?;
    get(table, found.group(1))
}

fn lead<'a>(m: &Match<'a>) -> &'a [char] {
    &m.string[sentence_start(m)..m.start()]
}

fn rest_end(m: &Match, from: usize) -> usize {
    REST.at(m.string, from).map_or(from, |found| found.end())
}

fn profiled(m: &Match) -> V {
    let start = sentence_start(m);
    let end = rest_end(m, m.end());
    if NOT_SELF.test_in(m.string, start, m.start()) || !TAG_NEAR.test_in(m.string, start, end) {
        None
    } else {
        get(RELIGIONS, m.group(1))
    }
}

fn foreign(m: &Match) -> V {
    let text = m.text();
    let words = split_ws(text);
    let last = words.last()?;
    STEMS.iter().find(|(stem, _)| starts_at(last, 0, stem)).map(|(_, value)| *value)
}

fn listed(m: &Match) -> V {
    let text = m.string;
    let (start, end) = (m.start(), m.end());
    let group = m.text();
    let body = if start > 0 && text[start - 1] == '|' {
        let trimmed = strip_right(group, " \t");
        LISTED_ITEM.fullmatch(trimmed, 0, trimmed.len())
    } else if end < text.len() && text[end] == '|' {
        return None;
    } else {
        let trimmed = strip_right(group, " \t.!");
        LISTED_LINE.fullmatch(trimmed, 0, trimmed.len())
    };
    get(POLITICS, body?.group(1))
}

fn strip_right<'a>(s: &'a [char], set: &str) -> &'a [char] {
    let mut end = s.len();
    while end > 0 && set.contains(s[end - 1]) {
        end -= 1;
    }
    &s[..end]
}

fn side(word: &[char]) -> &'static str {
    let word: Vec<char> = word.iter().map(|&c| if c == '-' { ' ' } else { c }).collect();
    if starts_at(&word, 0, "far ") || starts_at(&word, 0, "extreme ") || starts_at(&word, 0, "radical ") {
        return if contains(&word, "left") { "communist or far left" } else { "nationalist or far right" };
    }
    if contains(&word, "left") {
        return if contains(&word, "leaning") || contains(&word, "cent") { "progressive or liberal" } else { "socialist or left" };
    }
    "conservative or right"
}

fn diet_mine(m: &Match) -> V {
    let before = lead(m);
    let group = m.text();
    let word = FOODWAY.at(group, 0)?.text();
    let framed = if word.len() < group.len() {
        !eq(word, "carnivore") && ADOPTED.test(before)
    } else {
        ["keto", "low carb", "low-carb", "carnivore"].iter().any(|w| eq(word, w)) && NOT_DIET.at(m.string, m.end()).is_none() && STARTED.test(before)
    };
    if framed && SELF_NEAR.test(before) && !OTHER_NEAR.test(before) {
        get(DIETS, Some(word))
    } else {
        None
    }
}

fn own(m: &Match) -> V {
    let before = lead(m);
    if OTHER_NEAR.test(before) || UNTAKEN.test(before) || !SELF_NEAR.test(before) {
        None
    } else {
        get(DIETS, m.group(1))
    }
}

fn current(m: &Match) -> V {
    let mut joined = lead(m).to_vec();
    joined.extend_from_slice(&m.string[m.end()..rest_end(m, m.end())]);
    if SMOKED_BEFORE.test(&joined) {
        None
    } else {
        Some("smoker or vaper")
    }
}

fn smoking_mine(m: &Match) -> V {
    let before = lead(m);
    if (SELF_NEAR.test(before) || TAG_NEAR.test(before)) && !OTHER_NEAR.test(before) {
        current(m)
    } else {
        None
    }
}

fn first_hand(m: &Match, result: &'static str) -> V {
    if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) {
        None
    } else {
        Some(result)
    }
}

fn item(m: &Match, result: &'static str) -> V {
    if ITEM.fullmatch(m.string, line_start(m.string, m.start()), m.start()).is_some() {
        Some(result)
    } else {
        None
    }
}

fn service(m: &Match) -> V {
    let start = sentence_start(m);
    if OTHER_NEAR.test_in(m.string, start, m.start()) {
        return None;
    }
    let mut joined = m.string[start..m.start()].to_vec();
    joined.extend_from_slice(&m.string[m.start()..rest_end(m, m.start())]);
    if DISCHARGED.test(m.text()) || PAST.test(&joined) {
        Some("military veteran")
    } else {
        Some("serving in the military")
    }
}

fn served(m: &Match) -> V {
    first_hand(m, "military veteran")
}

fn counted(m: &Match) -> V {
    if COUNTED.test_in(m.string, back(m, 20), m.start()) {
        served(m)
    } else {
        None
    }
}

fn entered(m: &Match) -> V {
    if ENTERED.test_in(m.string, sentence_start(m), m.start()) {
        served(m)
    } else {
        None
    }
}

fn within(m: &Match) -> V {
    if WITHIN.test_in(m.string, sentence_start(m), m.start()) {
        service(m)
    } else {
        None
    }
}

fn here_label(m: &Match) -> V {
    let found = HERE_LABEL.search(m.string, back(m, 80), m.start())?;
    let kind = found.group(3).map(st).unwrap_or_default();
    let first = found.nonempty(1).map(|g| strip_chars(g, " -")).unwrap_or(&[]);
    if kind == "vet" || kind == "veteran" || ["retired", "former", "ex", "prior"].iter().any(|w| eq(first, w)) {
        Some("military veteran")
    } else {
        Some("serving in the military")
    }
}

fn titled(m: &Match) -> V {
    let start = line_start(m.string, m.start());
    let end = line_end(m.string, m.end());
    if m.string[..start].iter().any(|c| !c.is_whitespace()) || !TAG_NEAR.test_in(m.string, start, end) || TITLE_OTHER.test_in(m.string, start, m.start()) {
        return None;
    }
    let kind = m.g(1);
    Some(if kind == "vet" || kind == "veteran" { "military veteran" } else { "serving in the military" })
}

fn profile_vet(m: &Match) -> V {
    let before = lead(m);
    if (SELF_NEAR.test(before) || TAG_NEAR.test(before)) && !OTHER_NEAR.test(before) {
        Some("military veteran")
    } else {
        None
    }
}

fn opening(word: &str) -> String {
    format!(r"{word}(?:(?<=^{word})|(?<=[.!?\n(]{word})|(?<=[.!?\n(] {word})|(?<=[.!?\n]  {word}))")
}

fn piped(m: &Match, table: &Tab) -> V {
    let (start, end) = bounds(m);
    if PIPE_TAG.test_in(m.string, start, end) {
        get(table, m.group(1))
    } else {
        None
    }
}

fn spoken_religion(m: &Match) -> V {
    get(RELIGIONS, m.first())
}

#[allow(non_snake_case)]
fn religion() -> Vec<Rule> {
    let FAITH = faith();
    let ASX = format!(r"(?:{AS}|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as)|as(?<=\bas)(?= an? (?:[\w-]+ )?[\w-]+,? (?:i|i'm|i've|i'd|i'll|im|ive|we|myself)\b))");
    let ISM = longest_first(ISMS.iter().map(|(k, _)| *k));
    vec![
        r("religion", &format!(r"i(?<=\bi){ME} {FREE}(?:a |an )?{FREE}(?:(?!non-|ex-|anti-|post-|pro-)[a-z]+-)?({FAITH})\b(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater)\b)"), |m| scoped(m, RELIGIONS), TAGGED),
        r("religion", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b|my\b|being\b|for\b|to\b|at\b|by\b|with\b|about\b)[\w-]+,? (?:and )?){{1,4}}(?:a |an )?({FAITH})\b(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater|household|family|parents)\b)"), |m| scoped(m, RELIGIONS), self_hedge()),
        r("religion", &format!(r"{ASX} an? (?:[\w-]+ ){{0,2}}?({FAITH})\b|b(?<=\bb)eing an? ({FAITH})(?:,| i\b)|being(?:(?<=^being)|(?<=[.!?\n]being)|(?<=[.!?\n] being)) (?:an? )?(?:[\w-]+ )?({FAITH})\b(?!s\b)|\b(?:we|us) ({FAITH})s\b|\bi (?:became|became a|turned|am now|'m now|have become) ({FAITH})\b"), spoken_religion, self_hedge()),
        r("religion", r"(?:أنا|انا|أني|اني) (مسلم|مسلمة|مسيحي|مسيحية|ملحد|ملحدة)", foreign, self_hedge()),
        r("religion", concat!(r"\b(?:soy|sou) (?:(?:algo|más|mais|muy|muito|bastante|como|bien|bem) ){0,3}?(católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|agnóstic[oa]|evangélic[oa])\b",
          r"|\bje suis (catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|agnostique)\b|\bich bin (katholisch|christ|christin|atheist|atheistin|muslim|muslima|jüdisch|evangelisch|agnostiker)\b",
          r"|\bjestem (katolikiem|katoliczką|ateistą|ateistką|chrześcijaninem|chrześcijanką|muzułmaninem|muzułmanką)\b|\bsono (cattolic[oa]|ateo|atea|cristian[oa]|musulman[oa]|ebre[oa])\b|\bik ben (katholiek|christen|atheïst|moslim|joods)\b",
          r"|\b(?:como|en tant que|als|come|jako) (?:un |una |um |uma |une |ein |eine )?(católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|judeu|judia|evangélic[oa]|catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|katholik(?:in)?|christ(?:in)?|atheist(?:in)?|jude|jüdin|cattolic[oa]|katolik|ateista|ateistka|chrześcijanin|chrześcijanka)\b",
          r"|\bjag är (?:(?!inte\b)\w+ )?(ateist|kristen|muslim|katolik|agnostiker|jude|judisk|buddhist|hindu)\b|\bär jag (ateist|kristen|muslim|katolik|agnostiker|jude|judisk|buddhist|hindu)\b",
          r"|\bsam (ateista|ateist|katolik|katolkinja|pravoslavac|pravoslavka|musliman|muslimanka)\b|\bя (христианка|христианин|атеист|атеистка|мусульманин|мусульманка|православный|православная|католик|католичка)\b",
          r"|(?<!\beski )\b(ateistim|müslümanım|hristiyanım|deistim|agnostiğim)\b|\bjeg er (?:(?!ikke\b)\w+ )?(ateist|kristen|muslim|katolikk|katolik|agnostiker|jøde)\b"),
          foreign, self_hedge()),
        r("religion", r"i(?<=\bi)(?: (?:also|personally|actually|just|definitely|certainly|honestly|really))?(?:'m| am|m| m) (?:also |personally |actually |just |definitely |certainly |honestly |literally )?(?:not|no|neither) (?:a |very |really |particularly |that |super |overly |at all |even |remotely |exactly |all that |terribly |the least bit )?religious(?: person)?\b|n(?<=\bn)ot(?:(?<=^not)|(?<=[.!?\n]not)|(?<=[.!?\n] not)|(?<=[.!?\n]  not)) (?:a |very |really |particularly )?religious(?: person)?\b|i(?<=\bi)(?:'m| am) (?:a )?(?:non-?religious|irreligious)\b|i(?<=\bi) (?:don't|do not|dont) (?:have|practice|follow|subscribe to|belong to|adhere to) (?:a |any )?(?:\w+ )?(?:specific |particular |organi[sz]ed |formal )?religion\b|i(?<=\bi)(?:'m| am) not (?:a )?follower of any religion\b|b(?<=\bb)eing (?:a )?non[- ]?religious\b|i(?<=\bi)(?:'m| am) (?:a |an )?(?:[\w-]+ ){1,3}(?:and )?(?:a |an )?non[- ]?religious\b|i(?<=\bi) (?:wouldn't|would not|don't|do not|dont) (?:consider|call) myself religious\b|i(?<=\bi) have no religion\b|i(?<=\bi) (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|i(?<=\bi) loathe (?:all )?religion\b|s(?<=\bs)piritual,? (?:but )?not religious\b|m(?<=\bm)ore spiritual than religious\b|я(?<=\bя) не религиозн|n(?<=\bn)o soy religios[oa]\b|i(?<=\bi)ch bin nicht religiös\b",
          |m| Some(if contains(m.text(), "god") || contains(m.text(), "loathe") { "atheist" } else { "spiritual, no religion" }), TAGGED),
        r("religion", &format!(r"i(?<=\bi)(?:'d| would| have| 've)? (?:always )?(?:consider myself|identify as|would call myself|call myself|describe myself as|consider myself to be|see myself as|view myself as|define myself as) (?:a |an )?(?:\w+ )?({FAITH})\b|(?:w(?<=\bw)e|u(?<=\bu)s) as ({FAITH})s\b|a(?<=\ba)s ({FAITH})s,? (?:we|us|our)\b|f(?<=\bf)ellow ({FAITH})s?\b"), spoken_religion, self_hedge()),
        r("religion", r"h(?<=\bh)ere\b", |m| labelled(m, &RELIGION_HERE, RELIGIONS), self_hedge()),
        r("religion", &format!(r"r(?<=\br)eligion[ \t*_]*[:=][ \t*_]*(?:(?:roman|devout|practicing|practising|non-?denominational|born again|sunni|shia) )?({FAITH})\b"), |m| get(RELIGIONS, m.group(1)), self_hedge()),
        r("religion", &format!(r"i(?<=\bi){ME} (?:an? )?(?:\w+ )?(agnostic)[- ](?:atheist|christian|theist|catholic|deist|pagan|buddhist|jew|muslim)\b"), |m| get(RELIGIONS, m.group(1)), self_hedge()),
        r("religion", &format!(r"\b(?!witch\b|spiritual\b|humanist\b)({FAITH})\b(?!'?s\b| (?:girls|guys|women|men|couples|husband|partner|family|families|people|friends?|community|folks|countries|country|ladies|dudes|boys|females|males|mythology)\b)"), profiled, self_hedge()),
        r("religion", &format!(r"\A\W*(?:\d{{2}}\s*[mf]?\W*)?(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?({FAITH}) (?:couple|guy|girl|man|woman|male|female|m|f|dad|mom|here|only)\b"), |m| get(RELIGIONS, m.group(1)), self_hedge()),
        r("religion", &format!(r"\A\W*(?:(?:yes|yep|yeah|yup|yea|well|me|personally|myself)\W+)?(?!witch\b|spiritual\b|humanist\b)(?:(?:roman|devout|practicing|practising|proud|non-?denominational|born again) )?({FAITH})[ \t]*(?:[.!]|\n|\Z|\p{{So}})"), |m| get(RELIGIONS, m.group(1)), self_hedge()),
        r("religion", &format!(r"\|[ \t]*({FAITH})[ \t]*(?=\||\n|\Z)"), |m| piped(m, RELIGIONS), self_hedge()),
        r("religion", &format!(r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:converted|reverted|came|come|returned|turned) to ({ISM})\b|i(?<=\bi)(?:'ve| have)? (?:\w+ )?joined (the catholic church|the orthodox church|the lds church)\b"),
          |m| if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) { None } else { get(ISMS, m.first()) }, self_hedge()),
        r("religion", r"i (?<=\bi )(?:\w+ )?pray (?:that )?allah\b", constant("muslim"), self_hedge()),
        r("religion", r"my (?<=\bmy )(?:relationship|walk|journey) with (?:god|christ|jesus|the lord)\b|i (?<=\bi )(?:\w+ )?(?:seek|follow|love|accepted|believe in|trust in|pray to|worship) (?:jesus|christ|the lord)\b|i (?<=\bi )(?:\w+ )?pray (?:to god|every (?:day|night|morning)|daily|the rosary)\b",
          constant("christian"), self_hedge()),
        r("religion", r"my (?<=\bmy )(?:pagan|wiccan|witchy|heathen|druid\w*|witchcraft) (?:community|path|practice|journey|beliefs|faith|spirituality|tradition|altar|craft|friends|group)\b|my (?<=\bmy )(?:altar|deities|patron (?:god|goddess|deity)|book of shadows)\b", constant("pagan or other religion"), self_hedge()),
        r("religion", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:home |local |new |old )?(church|pastor|priest|parish|congregation|mosque|masjid|imam|synagogue|shul|rabbi)\b(?! (?:friends?|youth group)\b)",
          |m| {
              if !free(m) {
                  return None;
              }
              let place = m.g(1);
              Some(if ["mosque", "masjid", "imam"].contains(&place.as_str()) { "muslim" } else if ["synagogue", "shul", "rabbi"].contains(&place.as_str()) { "jewish" } else { "christian" })
          }, self_hedge()),
    ]
}

#[allow(non_snake_case)]
fn political(LISTED: &str) -> Vec<Rule> {
    let PARTY = party();
    let ASX = format!(r"(?:{AS}|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as))");
    vec![
        r("political_identity", &format!(r"i(?<=\bi){ME} {FREE}(?:a |an )?{FREE}{FILLER}({PARTY})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|with|about|when|in terms|on|in my|of|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach)\b)"),
          |m| if quoted(m) { None } else { scoped(m, POLITICS) }, TAGGED),
        r("political_identity", &format!(r"i(?<=\bi)(?:'ve| have)? (?:always |would |'d )?(?:consider myself|identify as|would call myself|describe myself as|consider myself to be|see myself as|view myself as|viewed myself as|saw myself as|define myself as) (?:a |an )?(?:\w+ )?({PARTY})\b|i(?<=\bi)(?:'m| am) a registered (democrat|republican)\b|i(?<=\bi) (?:\w+ )?lean(?:s)? (?:more |pretty |very |slightly |a bit |a little |heavily |strongly |hard )?(?:to the |towards the |toward the |towards |toward )?(left|right|liberal|conservative|progressive|libertarian|socialist)\b(?! (?:on|against|into|over|back|forward|in)\b)"),
          |m| get(POLITICS, m.group(1)).or_else(|| get(POLITICS, m.group(2))).or_else(|| get(LEAN, m.group(3))).or_else(|| get(POLITICS, m.group(3))), self_hedge()),
        r("political_identity", &format!(r"(?:w(?<=\bw)e|u(?<=\bu)s) ({PARTY})s\b|m(?<=\bm)e and (?:every|other|fellow|all the) ({PARTY})s?\b|c(?<=\bc)ent(?:er|re)[- ](left|right)(?: \w+){{0,2}} here\b|i(?<=\bi)(?:'m| am) (?:a )?maga\b|i(?<=\bi) (?:\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(republican|gop|democrat)\b"),
          |m| {
              get(POLITICS, m.nonempty(1).or(m.group(2))).or_else(|| {
                  let key = m.nonempty(3).or(m.nonempty(4)).unwrap_or(&[]);
                  Some(get(VOTED, Some(key)).unwrap_or(if contains(m.text(), "maga") { "conservative or right" } else { "progressive or liberal" }))
              })
          }, self_hedge()),
        r("political_identity", r"\b(?:volledig |totally |completely )?(?:apolitiek|apolitisch|apolítico|apolítica|apolitico|apolitica)\b", constant("apolitical"), self_hedge()),
        r("political_identity", &format!(r"{ASX} an? (?:(?!former\b|ex\b|non\b|anti\b)(\w+) )?({PARTY})\b(?! (?:as|party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach)\b)"),
          |m| {
              if m.group(1).map_or(false, |g| eq(g, "far") || eq(g, "extreme") || eq(g, "radical")) {
                  let mut word = chars("far ");
                  word.extend_from_slice(m.group(2).unwrap_or(&[]));
                  Some(side(&word))
              } else {
                  get(POLITICS, m.group(2))
              }
          }, hedge()),
        r("political_identity", r"he(?<=\bhe)re\b", |m| labelled(m, &POLITICS_HERE, POLITICS), self_hedge()),
        r("political_identity", &format!(r"\A\W*\d{{2}} ?(?:[mf]|yo|y/o|years? old)?\W*(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?(?:(?!looking\b|seeking\b|for\b|wants?\b|with\b|ex\b|former\b|non\b|not\b|and\b|anti\b)[\w-]+ ){{0,2}}({PARTY})\b(?! (?:girls?|guys?|women|men|females?|males?|partner|wife|husband|party|media|state|city|area|town)\b)"), |m| get(POLITICS, m.group(1)), self_hedge()),
        r("political_identity", LISTED, listed, self_hedge()),
        r("political_identity", &format!(r"f(?<=\bf)ellow ({PARTY})s?\b"), |m| get(POLITICS, m.group(1)), self_hedge()),
        r("political_identity", concat!(r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly on|solidly on|squarely on|also on)[*_]* the [*_]*((?:far[- ])?(?:left|right))\b(?! (?:track|path|side of|page|way|foot|direction|answer|thing|one|place|time|hand|lane|side of history)\b)",
          r"|\b(?:i'm|im|i am|i m) (?:a |an )?(?:(?!not\b|never\b|no\b|on\b|the\b)[\w-]+ ){0,2}?((?:far|extreme|radical)[- ](?:left|right)(?:[- ]wing|[- ]leaning|ist)?|left[- ]wing|right[- ]wing|left[- ]leaning|right[- ]leaning|leftist|lefty|(?:left|right)[- ]of[- ]cent(?:er|re)|cent(?:er|re)[- ](?:left|right))\b"),
          |m| Some(side(m.nonempty(1).or(m.group(2)).unwrap_or(&[]))), self_hedge()),
        r("political_identity", concat!(r"i(?<=\bi)(?:'m| am|m| m) (?:(?!not\b|never\b|no\b)\w+ )?(?:very |strongly |firmly |staunchly |proudly |100% )?(pro[- ]?choice|pro[- ]?life|anti[- ]?abortion|anti[- ]?capitalist|anti[- ]?woke)\b|m(?<=\bm)y (pro[- ]?choice|pro[- ]?life|anti[- ]?capitalist) (?:views?|stance|ideology|beliefs|politics|values)\b",
          r"|i(?<=\bi)(?:'m| am) a (?:lifelong |registered |proud |longtime )?(dem)\b|i(?<=\bi) (?:(?!never\b|won't\b|wont\b|wouldn't\b|didn't\b|didnt\b|can't\b|cant\b)\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(?:the )?(republicans|democrats|dems|blue|red|left|right|libertarian|green)\b(?! (?:light|line|state|flag|button|card|wave|tide)\b)"),
          |m| get(STANCES, Some(&STANCE_JOIN.sub(m.first()?, "")[..])), self_hedge()),
    ]
}

#[allow(non_snake_case)]
fn diet() -> Vec<Rule> {
    let ASX = format!(r"(?:{AS}|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as))");
    vec![
        r("diet", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b|recovering\b|bad\b)[\w-]+ )?(?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b)[\w-]+ )?(vegan|vegetarian|vegeterian|vegitarian|veggie|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)"), |m| get(DIETS, m.group(1)), hedge()),
        r("diet", &format!(r"{ASX} an? (?:(?!ex\b|former\b|non\b)\w+ )?(vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)"), |m| get(DIETS, m.group(1)), hedge()),
        r("diet", concat!(r"we(?<=\bwe)(?:'re| are) (?:all |both |also |strictly )?(vegan|vegetarian|pescatarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly)\b)|(?:s(?<=\bs)oy|s(?<=\bs)ou|s(?<=\bs)ono|i(?<=\bi)ch bin|i(?<=\bi)k ben) (vegan[oa]?|vegetarian[oa]|vegetarisch|vegetarier(?:in)?|vegetariër|veganer(?:in)?)\b",
          r"|j(?<=\bj)e suis (végane?|végétarien(?:ne)?|vegan)\b|j(?<=\bj)estem (weganką|weganinem|wegetarianką|wegetarianinem)\b"),
          |m| { let word = m.first()?; get(DIETS, Some(word)).or(Some(if contains(word, "tar") { "vegetarian" } else { "vegan" })) }, self_hedge()),
        r("diet", concat!(r"i(?<=\bi)(?:'m| am| have| was diagnosed with| got diagnosed with|'ve got| also have)? (?:a )?(?:celiac|coeliac)\b|m(?<=\bm)y (?:celiac|coeliac)\b|i(?<=\bi)(?: (?:eat|am|have to (?:eat|be|stay)|keep|went|stay)|'m) (?:strictly |completely |100% )?gluten[- ]free\b|t(?<=\bt)he gf diet\b",
          r"|i(?<=\bi)(?:'m| am) (?:\w+ )?(?:gluten|wheat)[- ]intolerant\b|i(?<=\bi) (?:can't|cannot|can not|can't really) (?:have|eat|do|tolerate) (?:any )?(?:gluten|wheat)\b|i(?<=\bi) (?:\w+ )?(?:cut|cutting) out (?:\w+ and )?gluten\b"), constant("gluten free"), self_hedge()),
        r("diet", r"i(?<=\bi) (?:eat|keep|only eat|stick to|stick with|have to stick with|follow) (?:strictly )?(halal|kosher)\b|i(?<=\bi)(?:'m| am) (?:on |doing )?(?:a |strict )?(keto)\b(?! (?:friendly|recipe))|i(?<=\bi) (?:do|eat|follow|went) (keto|ketogenic|low[- ]carb)\b",
          |m| Some(if m.nonempty(1).is_some() { "halal or kosher" } else { "keto or low carb" }), self_hedge()),
        r("diet", r"i(?<=\bi) (?:don't|do not|dont) eat (meat|any meat|animal products)\b|i(?<=\bi)(?:'m| am) (?:fully |mostly |\d+% )?(plant[- ]based)\b|i(?<=\bi) eat (plant[- ]based)\b", |m| Some(if contains(m.text(), "meat") { "vegetarian" } else { "vegan" }), self_hedge()),
        r("diet", r"i(?<=\bi) (?:eat|love) meat\b|i(?<=\bi)'?m a (?:meat eater|carnivore|omnivore)\b", constant("eats everything"), hedge()),
        r("diet", r"(?:vegan|vegetarian|veggie|pescatarian|pescetarian|keto|ketogenic|low[- ]carb|gluten[- ]free|plant[- ]based|halal|kosher|carnivore)\b(?: (?:diet|lifestyle|eating pattern|way of eating|woe|regimen)\b)?", diet_mine, self_hedge()),
        r("diet", r"here(?<=\bhere)\b", |m| labelled(m, &DIET_HERE, DIETS), self_hedge()),
        r("diet", r"i(?<=\bi)(?:'ve been| went| became| turned) (vegan|vegetarian|pescatarian)\b|been(?<=\bbeen) (?:strictly |completely |fully |mostly )?(vegan|vegetarian|pescatarian|gluten[- ]free|keto|low[- ]carb)\b|went(?<=\bwent) (vegan|vegetarian|pescatarian|gluten[- ]free|keto|low[- ]carb)\b", |m| get(DIETS, m.first()), self_hedge()),
        r("diet", &format!(r"(?:b(?<=\bb)eing|b(?<=\bb)ecoming|g(?<=\bg)oing|s(?<=\bs)witched to|s(?<=\bs)witching to) {TAKEN}"), own, self_hedge()),
        r("diet", r"\A\W*(?:(?:mostly|strict|strictly|proud) )?(vegan|vegetarian|pescatarian|pescetarian)[ \t]*(?:[.!]|\n|\Z)", |m| get(DIETS, m.group(1)), self_hedge()),
    ]
}

fn smoking() -> Vec<Rule> {
    vec![
        r("smoking", concat!(r"i(?<=\bi) (?:smoke|vape)\b(?! (?:meat|out|detector|alarm)\b)|n(?<=\bn)eed to smoke\b",
          r"|i(?<=\bi)(?:'m| am)? (?:\w+ ){0,2}(?:buying|buy|bought|hitting|hit) (?:a |my )?(?:disposable |nic |nicotine )?(?:vape|juul|cigs|cigarettes|pack of (?:cigs|cigarettes|smokes))\b"), |m| first_hand(m, "smoker or vaper"), self_hedge()),
        r("smoking", &(concat!(r"i(?<=\bi)(?: |'ve | have )(?:haven't|have not|havent) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b|h(?<=\bh)ave(?:n't| not|nt) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b",
          r"|i(?<=\bi) (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|since(?<=\bsince) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|after(?<=\bafter) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b",
          r"|when(?<=\bwhen) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|i(?<=\bi)(?:'ve| have)? never smoked\b").to_string()
          + &format!(r"|day(?<=\bday)s? {QUIT_SPAN}|week(?<=\bweek)s? {QUIT_SPAN}|month(?<=\bmonth)s? {QUIT_SPAN}|year(?<=\byear)s? (?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes))\b")), constant("non-smoker"), self_hedge()),
        r("smoking", r"i(?<=\bi) (?:don't|do not|dont|never) (?:smoke|vape)\b|i(?<=\bi) quit smoking\b|i(?<=\bi) used to (?:smoke|vape)\b|i(?<=\bi)(?:'m|m| am) a non-?(?:smoker|vaper)\b|i(?<=\bi)'ve never (?:smoked|vaped)\b", constant("non-smoker"), Some(&*CONDITIONAL)),
        r("smoking", concat!(r"\b(?:i|me) (?:\w+ )?(?:smoke|smoked|vape|vaped) (?:for|to|after|before|when|every|a|cigarettes|cigs|daily)\b|\bmy (?:cigarettes?|cigs|vape|juul|pack of (?:cigs|cigarettes|smokes)|smoke break|cigarette break)\b",
          r"|\bi(?:'ve| have) been (?:smoking|vaping) (?:for|since)\b|\bi smoke (?:a|\d+|two) packs?\b|\bi (?:\w+ )?(?:drink|drink socially) and smoke\b|\bi (?:\w+ )?smoke and drink\b|\bich rauche\b(?! nicht| kein| nie)|\bwir rauchen\b|\brauchen den\b"), constant("smoker or vaper"), self_hedge()),
        r("smoking", r"non(?<=\bnon)[- ]?(?:smoker|vaper)\b|i(?<=\bi) (?:also |even |really |personally |just )?(?:don'?t|do not) (?:even |really |actually |personally |currently )?(?:smoke|vape)\b|we(?<=\bwe) don'?t (?:smoke|vape)\b", constant("non-smoker"), Some(&*NO_SMOKERS)),
        r("smoking", &format!(r"(?:i(?<=\bi)(?:'m|m| am|'ve been)|s(?<=\bs)igned,?|{AS}) (?:a |an )?(?:(?!(?:not|never|no|former|ex)\b)[\w-]+ ){{0,2}}?(?:smoker|vaper|stoner|pothead)\b"), |m| if contains(m.text(), "non") { None } else { Some("smoker or vaper") }, self_hedge()),
        r("smoking", concat!(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a few|several) (?:days?|weeks?|months?|years?)\W{0,8}(?:after|since|off|without|free from|clean from|of not) (?:vaping|smoking|nicotine|cigarettes|cigs|the vape|juul|tobacco)\b",
          r"|i(?<=\bi)(?:'ve| have)? (?:(?:finally|officially|just|also|recently) )?(?:quit|stopped|given up|kicked) (?:the )?(?:vape|vaping|juul|cigarettes|cigs|nicotine|smoking|tobacco)\b",
          r"|just(?:(?<=^just)|(?<=[.!?\n]just)|(?<=[.!?\n] just)) (?:quit|stopped|gave up) (?:smoking|vaping|cigarettes|cigs)\b|d(?<=\bd)ay \d+ (?:of no|without|of not|off) (?:smoking|vaping|nicotine|cigarettes)\b"), constant("non-smoker"), self_hedge()),
        r("smoking", concat!(r"\bi (?:(?!don't|dont|do not|don|never|wouldn't|won't|can't|cannot|used|stopped|quit|need|needed|had|did|would|could|should|might|may|want|wanted|wanna|gonna|going|tried|try)[\w']+ ){1,2}(?:smoke|vape)\b(?! (?:meat|out|detector|alarm|free|ribs|brisket|fish|salmon|turkey|pork|chicken|signals?|bombs?|screen|machine)\b)",
          r"|\bi (?:(?!don't|dont|do not|don|never|wouldn't|won't|can't|cannot|used|stopped|quit|need|needed|would|could|should|might|may|want|wanted|wanna|gonna|going|tried|try|hate|hated|smell|smelled|see|saw|watch|watched|notice|noticed|someone|somebody|people|anyone|everyone|add|added)[\w']+ ){1,3}(?:smoking|vaping)\b(?![/-]| (?:meat|ribs|brisket|out|hot|fish|salmon|turkey|pork|chicken|gun|area|section|ban|room|wood|chips|pellets)\b)",
          r"|\b(?:i'm|im|i am) (?:just |currently |still |now |literally |also )?(?:smoking|vaping)\b(?! (?:meat|ribs|brisket|out|hot|fish|salmon|turkey|pork|chicken)\b)|\bi (?:enjoy|love|like) (?:smoking|vaping)\b(?! (?:meat|ribs|brisket|fish|salmon|turkey|pork|chicken)\b)"),
          current, self_hedge()),
        r("smoking", r"i(?<=\bi) (?:also |even |really |personally |just )?(?:don't|do not|dont|don) (?:drink|do (?:any )?(?:kinds? of )?drugs|party)(?:,? (?:or |and |nor )?(?:drink|do drugs|party))*,? (?:or |and |nor )?(?:smoke|vape)\b|not(?<=\bnot) a (?:drinker or (?:a )?)?(?:smoker|vaper)\b|i(?<=\bi)(?:'re| are|'m| am) (?:both )?(?:[\w&]+, )*non-?smokers?\b|we(?<=\bwe)(?:'re| are|'m| am) (?:both )?(?:[\w&]+, )*non-?smokers?\b",
          constant("non-smoker"), Some(&*NO_SMOKERS)),
        r("smoking", concat!(r"do(?:(?<=^do)|(?<=[.!?\n*(-]do)|(?<=[.!?\n*(-] do)|(?<=•do)|(?<=• do)|(?<=[,;:] do)|(?<=[,;:]do))(?:n't|n| not|nt) (?:(?:drink|do drugs|party)(?:,? (?:or |and |nor )?(?:don't |dont )?(?:drink|do drugs|party))*,? (?:or |and |nor )?(?:don't |dont )?(?:smoke|vape)",
          r"|(?:smoke|vape),? (?:or |and |nor )?(?:don't |dont )?(?:drink|do drugs|party)|(?:smoke|vape)(?=[ \t]*(?:[,.;!\n]|$)))\b",
          r"|n(?<=\bn)o (?:drinking|drinks|drugs|alcohol|booze),? (?:and |or |nor )?no (?:smoking|smoke|cigs|cigarettes|vaping)\b|n(?<=\bn)o (?:smoking|smoke|vaping|cigs|cigarettes),? (?:and |or |nor )?no (?:drinking|drinks|drugs|alcohol|booze)\b",
          r"|non(?:(?<=, non)|(?<=,non))[- ]?smoking(?=[ \t]*(?:[,.;!\n]|$))"),
          constant("non-smoker"), Some(&*NO_SMOKERS)),
        r("smoking", &format!(r"(?:i(?<=\bi)(?:'m|m| am)|{AS}) (?:a |an )?(?:[\w-]+ ){{0,2}}?(?:former|ex)[- ]?(?:smoker|vaper|vape user)\b|i(?<=\bi) (?:\w+ )?(?:was|am|'m) never a (?:\w+ )?smoker\b"), constant("non-smoker"), self_hedge()),
        r("smoking", r"smoker(?=[ \t]*(?:[,.;/!\n]|$))", |m| item(m, "smoker or vaper"), self_hedge()),
        r("smoking", &format!(r"smok(?<=\bsmok)(?:e|ing) {SMOKED}|vap(?<=\bvap)(?:e|ing) {SMOKED}|roll(?<=\broll)(?:ing)? {SMOKED}|light(?<=\blight)(?:ing)? up {SMOKED}|puff(?<=\bpuff)(?:s|ing)? (?:on )?{SMOKED}"), smoking_mine, self_hedge()),
    ]
}

fn veteran_if_service(m: &Match) -> V {
    if SERVICE.test(m.string) {
        Some("military veteran")
    } else {
        None
    }
}

fn military() -> Vec<Rule> {
    vec![
        r("military_status", &(format!(r"i(?<=\bi){ME} (?:currently |still )?(?:in|serving in|enlisted in) the (?:us |u\.s\. )?(?:army|navy|marines|air force|airforce|military|national guard|coast guard|marine corps|reserves|space force)\b|i(?<=\bi){ME} (?:on )?active duty\b")
          + &format!(r"|i(?<=\bi){ME} (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service ?member|infantryman|paratrooper)\b(?! (?:biolog|scien|life\b|ecolog|mammal))|i(?<=\bi){ME} (?:currently )?(?:deployed|stationed)\b")
          + r"|my(?<=\bmy) (?:unit|platoon|squadron|battalion|deployment|chain of command|first sergeant|drill sergeant|commanding officer|nco|squad leader)\b"), |m| first_hand(m, "serving in the military"), self_hedge()),
        r("military_status", &(format!(r"i(?<=\bi){ME} (?:a |an )?(?:former|retired|ex[- ]?) ?(?:soldier|marine|sailor|airman|service ?member|military|army|navy|paratrooper|infantryman)\b|my(?<=\bmy) (?:time|years|service) in the (?:army|navy|military|marines|corps|marine corps|service|air force|national guard)\b|i(?<=\bi)(?:'m| am) prior service\b")
          + &format!(r"|i(?<=\bi)(?:{ME}| was) {VET}|{AS} {VET}|when(?<=\bwhen) i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|i(?<=\bi) (?:served|was) (?:\w+ )?in the (?:forces|army|navy|marines|air force|military|coast guard|marine corps)\b|i(?<=\bi) served (?:my country|\d+ years|overseas|(?:two|three|four|\d) tours)\b")
          + r"|i(?<=\bi) (?:got out of|retired from|separated from) the (?:army|navy|marines|air force|military|service)\b|army(?<=\barmy) retiree\b|navy(?<=\bnavy) retiree\b|military(?<=\bmilitary) retiree\b|marine(?<=\bmarine) retiree\b|air(?<=\bair) force retiree\b|usmc(?<=\busmc) retiree\b|coast(?<=\bcoast) guard retiree\b"
          + r"|retired(?<=\bretired) (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force|military|usmc)\b"
          + &format!(r"|my(?<=\bmy)\b{VA}|i(?<=\bi)(?:'ve| have| was| got| am|'m)?\b{VA}")), constant("military veteran"), self_hedge()),
        r("military_status", r"\d(?<!\w\d)\d{1,2} ?% (?:p&t|sc|service[- ]connected)\b", constant("military veteran"), self_hedge()),
        r("military_status", concat!(r"i(?<=\bi) (?:went to boot ?camp|went through (?:boot ?camp|basic(?: training)?)|did basic(?: training)?|got out of the (?:army|navy|marines|military|air force|service|guard|corps)|was (?:honorably |medically )?discharged|",
          r"was (?:a|an) (?:\w+ )?(?:soldier|marine|sailor|airman|medic|paratrooper|infantryman|nco)|was (?:a |an )?(?:\w+ )?(?:officer|sergeant|corporal|specialist) in the (?:army|navy|marines|air force|military))\b",
          r"|(?:i(?<=\bi) did|i(?<=\bi) spent|i(?<=\bi) served|a(?<=\ba)fter|m(?<=\bm)y) (?:\d+|two|three|four|five|six|eight|ten|twelve|fifteen|twenty) (?:years|yrs) (?:in|of) (?:the )?(?:army|navy|marines|military|air force|service|active duty|marine corps|guard|reserves)\b"),
          veteran_if_service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:(?!on |at |my |so |to |no |in |an )[a-z]{{2}} |army |air )?(?:national )?guard(?:sman|swoman)?\b(?! (?:duty at|dog)\b)|i(?<=\bi){ME} (?:a |an )?(?:reservist|guardsman|guardswoman)\b|i(?<=\bi){ME} (?:in|with) the (?:\w+ )?(?:reserves?|guard)\b"),
          constant("serving in the military"), self_hedge()),
        r("military_status", r"my (?<=\bmy )(?:va |disability |combined |current )?(?:rating|claim|c&p|dbq|vso|gi bill|tricare|dd-?214|va benefits|va healthcare|va doctor|va appointment|pact act)\b",
          |m| if MILITARY_WORDS.test(m.string) { Some("military veteran") } else { None }, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:\w+ )?(?:officer|medic|nco|sergeant|corporal|private|specialist|pilot|mechanic|engineer|nurse|soldier|infantryman|linguist|analyst|doctor|chaplain) in the (?:army|navy|marines|air force|military|national guard|coast guard|reserves?|space force)\b"),
          constant("serving in the military"), self_hedge()),
        r("military_status", &(r"i(?<=\bi) (?:\w+ )?served (?:\w+ )?(?:in (?:combat)|overseas|(?:\d+|two|three|four|five|six|eight|ten|twenty) (?:years|yrs|tours)|my (?:time|country|contract|enlistment))\b".to_string()
          + r"|i(?<=\bi) (?:did|'ve done|have done|had) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b"
          + &format!(r"|i(?<=\bi)(?:'m|m| am) (?:using|running|on) (?:the |my )?(?:gi bill|post[- ]9/11)\b|i(?<=\bi) (?:used|use) (?:the |my )?gi bill\b|i(?<=\bi){ME} (?:a |an )?(?:[\w-]+ ){{1,3}}(?:and )?(?:a )?(?:war|combat|army|navy|marine|air force|military|disabled|retired|coast guard) (?:vet|veteran)\b")
          + r"|i(?<=\bi) (?:was|spent) (?:\w+ ){1,3}in the (?:army|navy|marines|air force|military|coast guard|marine corps|national guard)\b"), veteran_if_service, self_hedge()),
        r("military_status", concat!(r"fellow(?<=\bfellow) (?:veterans|vets|servicemembers|service members)\b",
          r"|(?:a(?<=\ba)fter|s(?<=\bs)ince|w(?<=\bw)hen|b(?<=\bb)efore|o(?<=\bo)nce) (?:i )?(?:got out|getting out|ets(?:'d|ed)?|i separated|separating|i was discharged)\b|my(?<=\bmy) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b|\d(?<!\w\d)\d* deployments\b"),
          veteran_if_service, self_hedge()),
        r("military_status", concat!(r"my(?<=\bmy) (?:(?!coding\b|code\b|data\b|fitness\b|web\b|ux\b|dev\b|design\b)\w+ )?(?:mos|afsc|ets|eas|dd-?214|dd 214|discharge papers|deployments?|tdy|duty station|first sergeant|drill sergeant|drill instructor|platoon sergeant|squad leader|nco|ncoic|commanding officer|bah|les|dog tags|cac card|basic training|boot camp|bootcamp|ait|tech school|bct|meps|enlistment|re-?enlistment|reenlistment|chain of command|battalion|platoon|brigade|regiment|time in service|military service|(?:military|army|navy|naval|marine|air force|usmc|coast guard) (?:career|medals|pension)|military id|military records?|troops|soldiers|sailors|airmen|marines)\b",
          r"|i(?<=\bi) (?:(?!never\b|didn't\b|didnt\b|won't\b|wont\b|wouldn't\b|almost\b|nearly\b)\w+ )?(?:enlisted|reenlisted|re-enlisted|deployed (?:to|overseas|twice|with|for)|pcs'd|pcsed|ets'd|etsed|separated from the|was commissioned|got commissioned|commissioned as|shipped out to (?:basic|boot camp|bootcamp)|graduated (?:basic|boot camp|bootcamp|ait|ocs|bct))\b"), service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi) (?:was|got) (?:\w+ )?(?:stationed|deployed)\b|w(?<=\bw)h(?:en|ile) i was (?:\w+ )?(?:stationed|deployed|in (?:the )?{BRANCH}|on active[- ]duty|active[- ]duty|enlisted|in boot ?camp|in basic training)"), served, self_hedge()),
        r("military_status", &format!(r"(?:j(?<=\bj)oined|e(?<=\be)nlisted in|e(?<=\be)nlisted into|w(?<=\bw)ent into|l(?<=\bl)eft|d(?<=\bd)eployed with|d(?<=\bd)ischarged from|m(?<=\bm)edically retired from|s(?<=\bs)erved with) (?:the )?{BRANCH}"), entered, self_hedge()),
        r("military_status", &format!(r"(?:y(?<=\by)ears?|y(?<=\by)rs?|d(?<=\bd)ecades?) (?:(?:in|of service in|serving in|with|of active[- ]duty in|on active[- ]duty in) (?:the )?{BRANCH}|(?:of )?(?:military|active[- ]duty|naval|army|navy|marine corps|air force) service\b)|(?:y(?<=\by)ears?|y(?<=\by)rs?) (?:of )?active[- ]duty\b"), counted, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi)n(?:to)? the {BRANCH}(?! (?:blue|painter|surplus|times|store|green|issue|knife|boots?|jacket|style|museum|industrial|base)\b)"), within, self_hedge()),
        r("military_status", r"her(?<=\bher)e\b", here_label, self_hedge()),
        r("military_status", r"\A\W*(?:(?:proud|disabled|combat|retired|army|navy|marine|air force|usmc|military) )?(?:vet|veteran)[ \t]*(?:[.!]|\n|\Z)", constant("military veteran"), self_hedge()),
        r("military_status", r"(?<=, )(?:a )?(?:(?:proud|disabled|combat|retired|army|navy|marine|military) )?(?:vet|veteran)(?=[ \t]*(?:[,.;/!\n]|$))", profile_vet, self_hedge()),
        r("military_status", r"i(?<=\bi) did (?:my|a|two|three|four|\d+) (?:army |navy |marine |military |combat |overseas )?tours?\b|i(?<=\bi) was in (?:a|an|the) (?:\w+ ){0,2}(?:infantry|artillery|armor|armored|cavalry|airborne|naval|army|military|national guard) (?:unit|battalion|regiment|company|division|platoon|brigade|squadron)\b", veteran_if_service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:currently |still )?with the {BRANCH}"), service, self_hedge()),
        r("military_status", r"g(?<=\bg)ot out in (?:'?\d{2}|\d{4})\b|\d(?<!\w\d)\d*\+? ?(?:years|yrs) (?:of )?(?:military|infantry|usmc|army|navy|marines|active duty|air force)(?=[ \t]*(?:[.,;!?\n]|$))", served, self_hedge()),
        r("military_status", r"\b(?:i'm|i am|im) (?:\w+ ){0,3}?(?:to|for) (?:navy |army |marine |air force |usaf |coast guard )?(?:boot ?camp|basic training|bmt|meps)\b", constant("serving in the military"), self_hedge()),
        r("military_status", &format!(r"(?:i(?<=\bi){ME}|w(?<=\bw)e(?:'re| are)) (?:(?!not\b|never\b|no\b|ex\b|former\b)\w+ )?(?:active[- ]duty )?military\b(?! (?:brat|spouse|wife|husband|family|families|kids?|child|history|style|grade|time|base|town|housing|vehicles?|surplus|discount|fan|buff|nerd|enthusiast)\b)"), service, self_hedge()),
        r("military_status", r"(?:army|navy|marine|air ?force|usaf|usmc|military|coast guard|national guard) (?:medic )?(guy|man|dude|boy|bro|vet|veteran)\b", titled, self_hedge()),
        r("military_status", r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?served\b(?! (?:as (?:a |an )?(?:juror|judge|witness|president|chair\w*|treasurer|secretary|member|volunteer|board|mayor)|(?:on|in) (?:a |the )?(?:jury|board|committee|council|church)|food|drinks?|dinner|lunch|breakfast|tables|customers|people|him|her|them|it|time|my time|a sentence|papers|coffee|beer|alcohol|up|with (?:a|an) (?:warrant|subpoena|papers))\b)", |m| if WAR_WORDS.test(m.string) { served(m) } else { None }, self_hedge()),
        r("military_status", &(format!(r"i(?<=\bi)(?:{ME} (?:also |actually |too |now |technically )?(?:a |an )?(?:(?:\d+[\w-]*|years?|yrs?|old|year-old|female|male|proud|actual|real|retired|disabled|combat|gen|generation) ){{0,4}}(?:and )?(?:a |an )?(?:vet|veteran)(?=[^\w ]|$| (?:and|so|myself|too|who|but|with|from)\b)")
          + &format!(r"|{ME} (?:a |an )?(?:former|retired|ex|prior)[- ]?{SERVED_NOUN}|(?:'m| am)? (?:\w+ )?(?:got out of|got out|retired from|separated from|discharged from) (?:the )?(?:army|navy|marines|air force|military|usaf|usmc|coast guard|national guard|marine corps)\b")
          + r"| was (?:(?:surface|active[- ]duty|prior|enlisted|reserve) )?(?:military|usaf|usmc|army|navy|marines|air force|coast guard|national guard|infantry|prior service|prior enlisted)\b(?! (?:brat|kids?|child|wife|husband|spouse|family|base|town|housing|style|green|blue|issue|surplus)\b))"), served, self_hedge()),
        r("military_status", r"w(?<=\bw)e (?:(?:military|army|navy|marine|combat|disabled|old|us) )?(?:vets|veterans)\b|(?:v(?<=\bv)ets|v(?<=\bv)eterans) (?:like|such as) (?:me|myself)\b", served, self_hedge()),
        r("military_status", &format!(r"{AS} (?:an? )?(?:former|ex|retired|prior)[- ]?{SERVED_NOUN}"), served, self_hedge()),
        r("military_status", &format!(r"{former} {SERVED_NOUN}|{retired} {SERVED_NOUN}|{prior} {SERVED_NOUN}|{ex}[- ]?{SERVED_NOUN}|{was} in the {BRANCH}|{also} an? (?:\w+ )?(?:vet|veteran)\b(?! (?:player|gamer|member|user|fan|of (?:the|this))\b)", former = opening("former"), retired = opening("retired"), prior = opening("prior"), ex = opening("ex"), was = opening("was"), also = opening("also")), served, self_hedge()),
        r("military_status", r"\A\W*\d{2}\s*[mf]?\W*(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?(?:[\w-]+ ){0,2}(?:(?:us |u\.s\. )?(?:army|navy|marine|air force|usaf|usmc|military|combat|coast guard) )?(?:vet|veteran)\b", served, self_hedge()),
    ]
}

#[allow(non_snake_case)]
fn gated(rules: Vec<Rule>, LISTED: &str) -> Vec<Rule> {
    let politics = keys(POLITICS);
    let religions = keys(RELIGIONS);
    let mut grouped = politics.clone();
    grouped.extend(["maga", "gop", "cent"]);
    let digits: Vec<&str> = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"].to_vec();
    let military_prefix = format!(r"i(?<=\bi){ME} (?:currently |still )?(?:in|serving in");
    let gates: Vec<(&str, Vec<&str>)> = vec![
        (LISTED, politics.clone()),
        (r"h(?<=\bh)ere", religions),
        (r"he(?<=\bhe)re", politics.clone()),
        (r"her(?<=\bher)e", vec!["vet", "marine", "soldier", "sailor", "airman", "service", "active duty", "reservist"]),
        (r"here(?<=\bhere)", vec!["veg", "pesc"]),
        (r"\b(?:volledig ", vec!["apol"]),
        (r"(?:w(?<=\bw)e|u(?<=\bu)s) (communist", grouped),
        (r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly", vec!["left", "right"]),
        (r"i(?<=\bi)(?: |'ve | have )(?:haven't", vec!["smok", "vap", "cig", "nicotine"]),
        (r"\bi (?:(?!don't|dont|do not|don|never", vec!["smok", "vap"]),
        (r"\b(?:\d+|one|two", vec!["vap", "smok", "nicotine", "cig", "juul", "tobacco"]),
        (r"\b(?:i|me) (?:\w+ )?(?:smoke", vec!["smok", "vap", "cig", "juul", "rauch"]),
        (r"we(?<=\bwe)(?:'re| are) (?:all |both |also |strictly )?(vegan", vec!["veg", "pesc", "vég", "weg"]),
        (r"\b(?!witch\b|spiritual", digits),
        (r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:converted", vec!["convert", "revert", "came to", "come to", "turned to", "joined the"]),
        (r"(?:i(?<=\bi)(?:'m|m| am)|as(?:", vec!["smoker", "vaper", "vape user"]),
        (&military_prefix, vec!["army", "navy", "marine", "air force", "military", "guard", "reserves", "space force", "active duty", "soldier", "sailor", "airman", "service",
            "infantry", "paratrooper", "deploy", "stationed", "unit", "platoon", "squadron", "battalion", "chain of command", "sergeant", "commanding officer", "nco", "squad leader"]),
    ];
    rules
        .into_iter()
        .map(|entry| match gates.iter().find(|(prefix, _)| entry.re.pattern.starts_with(prefix)) {
            Some((_, anchors)) => needs(entry, anchors),
            None => entry,
        })
        .collect()
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let PARTY = party();
    let LISTED = format!(r"(?<![^\n|])[ \t]*(?:(?:[-*•]|\d+[.)])[ \t]*)?(?:[\w-]+ )?(?:{PARTY})[ \t.!]*(?![^\n|])");
    let mut rules = shared::scoped_rules(religion());
    rules.extend(shared::scoped_rules(political(&LISTED)));
    rules.extend(shared::scoped_rules(diet()));
    rules.extend(shared::scoped_rules(smoking()));
    rules.extend(shared::scoped_rules(military()));
    gated(rules, &LISTED)
}
