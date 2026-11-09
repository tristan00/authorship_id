use crate::flair::flair;
use crate::shared::{self, *};
use claimcore::*;

const FREE: &str = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|formerly\b|lapsed\b|recovering\b|raised\b|neither\b|nor\b|either\b|considering\b|becoming\b|getting\b|to\b|from\b|visiting\b|partial\b|looking\b|seeking\b|for\b|into\b|dating\b|with\b|like\b|in\b|at\b|on\b|talking\b|about\b|than\b)\w+ )?";
const NOT_FAITH_NOUN: &str = r"(?! (?:school|music|metal|rock|rap|songs?|band|fan|history|studies|nationalists?|ethics|guilt|trauma|upbringing|hunter|hater|household|family|parents|curses?|spells?|magic|churche?s?|chapels?|cathedrals?|background|perspective|friends?|names?|heritage|culture|on|about|towards?|regarding)\b)";
const FILLER: &str = r"(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|formerly\b|lapsed\b|recovering\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b|looking\b|seeking\b|for\b|into\b|dating\b|with\b|like\b|in\b|at\b|on\b|talking\b|about\b|than\b)[\w-]+,? (?:and )?){0,2}?(?:a |an )?";
const ME: &str = r"(?:'m|m| am|am| m|'am|'?ve been|'ve always been| myself am| my self am| have been| have always been)";

static RELIGIONS: &Tab = &[
    ("christian", "christian (unspecified)"), ("catholic", "catholic"), ("protestant", "protestant (unspecified)"), ("mormon", "latter-day saint"), ("lds", "latter-day saint"), ("baptist", "baptist"), ("methodist", "methodist"),
    ("lutheran", "lutheran"), ("evangelical", "evangelical / pentecostal"), ("orthodox christian", "orthodox christian"), ("muslim", "muslim"), ("jew", "jewish"), ("jewish", "jewish"), ("hindu", "hindu"),
    ("buddhist", "buddhist"), ("pagan", "pagan"), ("wiccan", "wiccan"), ("heathen", "heathen / norse pagan"), ("druid", "druid"), ("hellenic polytheist", "hellenic polytheist"),
    ("spiritual", "spiritual"), ("agnostic", "agnostic"), ("atheist", "atheist"), ("presbyterian", "presbyterian"), ("anglican", "anglican / episcopalian"), ("episcopalian", "anglican / episcopalian"), ("pentecostal", "evangelical / pentecostal"),
    ("seventh-day adventist", "seventh-day adventist"), ("seventh day adventist", "seventh-day adventist"), ("adventist", "seventh-day adventist"), ("coptic", "orthodox christian"), ("sunni", "sunni"), ("shia", "shia"), ("shiite", "shia"), ("moslem", "muslim"),
    ("sikh", "sikh"), ("quaker", "quaker"), ("jehovah's witness", "jehovah's witness"), ("jehovah witness", "jehovah's witness"),
    ("satanist", "satanist"), ("taoist", "taoist"), ("zoroastrian", "zoroastrian"), ("rastafarian", "rastafari"), ("deist", "deist"), ("pantheist", "pantheist"), ("unitarian", "unitarian"), ("shintoist", "shinto"),
    ("greek orthodox", "orthodox christian"), ("russian orthodox", "orthodox christian"), ("eastern orthodox", "orthodox christian"), ("latter-day saint", "latter-day saint"), ("latter day saint", "latter-day saint"),
    ("secular humanist", "secular humanist"), ("humanist", "secular humanist"), ("nonbeliever", "atheist"), ("non-believer", "atheist"), ("athiest", "atheist"), ("christan", "christian (unspecified)"),
    ("apatheist", "apatheist"), ("nondenominational", "nondenominational"), ("non-denominational", "nondenominational"), ("kemetic", "kemetic"),
];
static STEMS: &Tab = &[
    ("مسلم", "muslim"), ("مسيح", "christian (unspecified)"), ("ملحد", "atheist"), ("ate", "atheist"), ("athe", "atheist"), ("athé", "atheist"), ("musul", "muslim"), ("muzu", "muslim"), ("muslim", "muslim"), ("moslim", "muslim"),
    ("jud", "jewish"), ("jüd", "jewish"), ("juif", "jewish"), ("juive", "jewish"), ("ebre", "jewish"), ("joods", "jewish"), ("agnost", "agnostic"), ("agnóst", "agnostic"),
    ("cat", "catholic"), ("kat", "catholic"), ("crist", "christian (unspecified)"), ("christ", "christian (unspecified)"), ("chrét", "christian (unspecified)"), ("chrz", "christian (unspecified)"), ("evangelisch", "protestant (unspecified)"), ("evang", "evangelical / pentecostal"),
    ("krist", "christian (unspecified)"), ("hrist", "christian (unspecified)"), ("pravoslav", "orthodox christian"), ("христиан", "christian (unspecified)"), ("православн", "orthodox christian"), ("католи", "catholic"), ("атеист", "atheist"),
    ("мусульман", "muslim"), ("müslüman", "muslim"), ("buddh", "buddhist"), ("hindu", "hindu"), ("deist", "deist"),
];
static ISMS: &Tab = &[
    ("catholicism", "catholic"), ("christianity", "christian (unspecified)"), ("islam", "muslim"), ("judaism", "jewish"), ("buddhism", "buddhist"), ("hinduism", "hindu"), ("paganism", "pagan"), ("sikhism", "sikh"),
    ("wicca", "wiccan"), ("orthodoxy", "orthodox christian"), ("mormonism", "latter-day saint"), ("protestantism", "protestant (unspecified)"), ("atheism", "atheist"), ("agnosticism", "agnostic"), ("christ", "christian (unspecified)"), ("jesus", "christian (unspecified)"),
    ("the catholic church", "catholic"), ("the orthodox church", "orthodox christian"), ("the lds church", "latter-day saint"), ("satanism", "satanist"), ("taoism", "taoist"),
];
static POLITICS: &Tab = &[
    ("communist", "communist"), ("marxist", "communist"), ("marxist-leninist", "communist"), ("socialist", "socialist"), ("leftist", "leftist"), ("liberal", "liberal"),
    ("progressive", "progressive"), ("democrat", "democrat"), ("centrist", "centrist / moderate"), ("moderate", "centrist / moderate"),
    ("conservative", "conservative"), ("republican", "republican"), ("libertarian", "libertarian"), ("anarchist", "anarchist"),
    ("nationalist", "nationalist"), ("lefty", "leftist"), ("commie", "communist"), ("democratic socialist", "democratic socialist"), ("social democrat", "social democrat"),
    ("libertarian socialist", "libertarian socialist"), ("classical liberal", "classical liberal"), ("ancap", "anarcho-capitalist"), ("anarcho-capitalist", "anarcho-capitalist"), ("anarchocapitalist", "anarcho-capitalist"), ("feminist", "feminist"), ("monarchist", "monarchist"), ("apolitical", "apolitical"), ("ancom", "anarchist"), ("demsoc", "democratic socialist"), ("socdem", "social democrat"),
];
static PAGANS: [(&str, &str, &str); 4] = [
    ("norse ", "pagan", "heathen / norse pagan"), ("hellenic ", "pagan", "hellenic polytheist"), ("hellenist ", "pagan", "hellenic polytheist"), ("hellenistic ", "pagan", "hellenic polytheist"),
];
static CRAFTS: &Tab = &[("pagan", "pagan"), ("wiccan", "wiccan"), ("witchy", "witch"), ("witchcraft", "witch"), ("heathen", "heathen / norse pagan"), ("druid", "druid"), ("druidic", "druid"), ("druidry", "druid")];
static COMPOUNDS: [(&str, &str, &str); 4] = [
    ("democratic ", "socialist", "democratic socialist"), ("social ", "democrat", "social democrat"), ("libertarian ", "socialist", "libertarian socialist"), ("classical ", "liberal", "classical liberal"),
];
static PARTIES: [&str; 9] = ["republican", "democrat", "green party", "labour", "conservative party (uk/canada)", "independent", "liberal democrats", "libertarian party", "reform uk"];
static STANCES: &Tab = &[
    ("republicans", "republican"), ("red", "republican"), ("democrats", "democrat"), ("dems", "democrat"), ("blue", "democrat"), ("green", "green party"), ("dem", "democrat"),
];
static VOTED: &Tab = &[("republican", "republican"), ("gop", "republican"), ("democrat", "democrat")];
static BRITISH: &Tab = &[("labour", "labour"), ("tory", "conservative party (uk/canada)"), ("tories", "conservative party (uk/canada)"), ("green", "green party"), ("green party", "green party"), ("independent", "independent"),
    ("lib dem", "liberal democrats"), ("lib dems", "liberal democrats"), ("libdem", "liberal democrats"), ("libdems", "liberal democrats"), ("liberal democrats", "liberal democrats"), ("reform", "reform uk"), ("reform uk", "reform uk"),
    ("libertarian party", "libertarian party"), ("labour party", "labour"), ("conservative party", "conservative party (uk/canada)"),
];
static DIETS: &Tab = &[
    ("vegan", "vegan"), ("vegetarian", "vegetarian"), ("veggie", "vegetarian"), ("keto", "keto"), ("gluten free", "gluten-free"), ("gluten-free", "gluten-free"),
    ("low carb", "low carb"), ("low-carb", "low carb"), ("ketogenic", "keto"), ("carnivore", "carnivore"), ("plant based", "plant-based"), ("plant-based", "plant-based"),
    ("vegeterian", "vegetarian"), ("vegitarian", "vegetarian"), ("pescatarian", "pescatarian"), ("pescetarian", "pescatarian"), ("flexitarian", "flexitarian"), ("halal", "halal"), ("kosher", "kosher"),
    ("low fodmap", "low fodmap"), ("low-fodmap", "low fodmap"), ("mediterranean", "mediterranean diet"), ("dairy free", "dairy free"), ("dairy-free", "dairy free"), ("sugar free", "sugar free"), ("sugar-free", "sugar free"),
];

const TAKEN: &str = r"(?:(?:a|an|fully|strictly|full|mostly|completely|strict) )?(vegan|vegetarian|vegeterian|vegitarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly|cheese|version|alternatives?|products?|brand|friends?|community|people|diet for)\b)";
const UPPERS: &str = r"(?:meth|methamphetamine|crystal meth|cocaine|coke|crack|adderall|amphetamines?|stimulants|benzos?|benzodiazepines?|xanax|klonopin|valium|ativan|alprazolam|clonazepam)\b";
const QUIT_SPAN: &str = r"(?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes)|after (?:vaping|smoking) (?:since|for))\b";
const BRANCH: &str = r"(?:(?:us|u\.s\.|british|canadian|australian|indian|royal|israeli) )?(?:army|navy|marines|marine corps|air force|usaf|usmc|military|coast guard|national guard|air national guard|armed forces|army reserves?|navy reserves?|reserves|raf|idf|space force|airforce)\b";
const UNDECLINED: &str = r"(?:(?!never\b|almost\b|nearly\b|should\b|could\b|would\b|might\b|will\b|wanted\b|want\b|wanna\b|didn't\b|didnt\b|don't\b|dont\b|won't\b|wont\b|wouldn't\b|wish\b|hope\b|plan\b|planning\b|thinking\b|considering\b|trying\b|tried\b|not\b)[\w']+ )";
const SERVED_NOUN: &str = r"(?:us |u\.s\. )?(?:military|army|navy|marines?|marine corps|air force|airforce|usaf|usmc|coast guard|national guard|infantry|enlisted|service ?member|soldier|sailor|airman|paratrooper|infantryman)\b";
const VET: &str = r"(?:a |an )?(?:proud |disabled |combat |retired |former |old )?(?:(?:us |u\.s\. )?(?:army|navy|marine|marine corps|air force|af|usaf|military|usmc|combat|war|coast guard|national guard|gwot) )?(?:vet|veteran)\b(?! (?:tech|clinic|bill|school|student|player|gamer|member|user|fan|raider|streamer|poster|of (?:the|this))\b)(?! [\w-]+ (?:fans?|players?|gamers?|members?|users?|streamers?|raiders?)\b)";
const VA: &str = r"(?:(?!\bnot\b|n't\b|\bnever\b)[^.!?\n]){0,40}?\b(?:va claim|va rating|va disability|dd-?214|c&p exam|nexus letter|service[- ]connected|100% p&t|the va\b(?! (?:area|beach|state|border|side|suburbs|region)\b))\b";

regex!(TAG_NEAR, r"(?<![\w$#.,'/:+-])(?:\d{2} ?(?:[mf]|male|female|yo|y/o|yrs?|years? old)|[mf] ?\d{2}|(?:\d{2} ?)?[\[\(]?[mf]4[mfa]\w*[\]\)]?)(?![\w'%])");
regex!(NOT_SELF, r"\b(?:if|would|wish|hope|not|never|ex|former|raised|born|for|looking|seeking|into|with|any|wants?|loves?|likes?|prefers?|dating|interfaith|than|like|non|anti|no|other|lapsed)\b|\b(?:a|an|the|by|real|some|your|his|her|their)\s+$");
regex!(LISTED_LINE, r"[ \t]*(?:[-*•]|\d+[.)])?[ \t]*(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ )?(.+)");
regex!(LISTED_ITEM, r"[ \t]*(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ )?(.+)");
regex!(SELF_NEAR, r"\b(?:i|i'm|im|i've|ive|me|my|we)\b");
regex!(OTHER_NEAR, r"\b(?:you|he|she|they|people|someone|somebody|anyone|everyone|his|her|their|your|friends?|dad|mom|father|mother|grandfather|grandpa|granddad|uncle|brother|sister|cousin|husband|wife|spouse|boyfriend|girlfriend|fiance|fiancee|partner|kids?|son|daughter)\b");
regex!(ADOPTED, r"\b(?:my|on|eating|following|follow|followed|started|adopted|switched to|stick to|stuck to|thanks to|due to|doing) (?:a |an |the )?(?:(?:strict|strictly|mostly|fully|very|nearly|almost|100%|\d+%|whole food|healthy|clean) )*\Z");
regex!(STARTED, r"\b(?:on|doing|started|start|eating|following|going|went|been|stay|staying) (?:strict |a strict |full |proper |properly |mostly |strictly )?\Z");
regex!(FOODWAY, r"vegan|vegetarian|veggie|pescatarian|pescetarian|flexitarian|keto|low[- ]carb|low[- ]fodmap|gluten[- ]free|dairy[- ]free|sugar[- ]free|plant[- ]based|halal|kosher|carnivore|mediterranean");
regex!(NOT_DIET, r" (?:diet|recipes?|friendly|meals?|food|snacks?|bread|options?|version)\b");
regex!(UNTAKEN, r"\b(?:was|were|had|stopped|quit|want|wanted|wanna|trying|try|tried|thinking|considering|closest|hard|easy|didn't|never|not|no longer|used to|if|would|should|could|might|maybe)\b");
regex!(SERVICE, r"\b(?:army|navy|marines?|military|usmc|air force|national guard|coast guard|deploy\w*|enlist\w*|veterans?|va|dd-?214|gi bill|mos|ets|boot ?camp|basic training|base|platoon|squadron|battalion|nco|sergeant|sgt|corporal|cpl|soldiers?|sailors?|airmen|servicemembers?|served)\b");
regex!(COUNTED, r"\b(?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|a few|several|many|a couple of) (?:\+ |plus )?\Z");
regex!(ENTERED, format!(r"\bi {UNDECLINED}?\Z"));
regex!(WITHIN, format!(r"\bi(?:'m|'ve)? {UNDECLINED}{{1,4}}?\Z"));
regex!(PAST, r"\b(?:was|were|had|did|used|learned|spent|back then|back in|ago|got out|retired|served|after)\b");
regex!(DISCHARGED, r"dd|discharge|gi bill|separat|ets|eas|career|medal|pension");
regex!(REST, r"[^.!?\n]*");
regex!(HERE_LABEL, r"(?:^|[.!?,;(] *)(?:hey,? |also |another )?(fellow |proud |disabled |combat |retired |former |ex[- ]?|prior )?((?:us |u\.s\. )?(?:army|navy|marine|marine corps|air force|af|usaf|usmc|military|coast guard|national guard|combat|war|gwot) )?(veteran|vet|marine|soldier|sailor|airman|service ?member|active duty|reservist) (?:too )?\Z");
regex!(MILITARY_WORDS, r"\b(?:va|veterans?|military|service|army|navy|marines?|air force|usmc|vso|dbq|c&p)\b");
regex!(PIPE_TAG, r"(?<![^\n|])[ \t]*(?:\d{2}[ \t]*[mf]?|[mf]|male|female)[ \t]*(?![^\n|])");
regex!(WAR_WORDS, r"\b(?:army|navy|marines?|military|air ?force|usmc|usaf|coast guard|national guard|veterans?|deploy\w*|enlist\w*|combat|infantry|platoon|battalion|boot ?camp|tours? of duty|war|afghanistan|iraq|vietnam|overseas|idf|caf|raf|soldiers?|sergeant|corporal|troops)\b");
regex!(TITLE_OTHER, r"\b(?:for|seeking|looking|want|wants|wanna|need|needs|into|with|like|love|any|your|my|her|his|their)\b");
regex!(RELIGION_HERE, format!(r"(?:^|[.!?,;(] *)(?:(?!former\b|ex\b|recovering\b|lapsed\b|non\b|not\b|raised\b|born\b|anti\b|i\b|you\b|he\b|she\b|they\b|we\b|every\b|all\b|any\b|the\b|my\b|your\b|his\b|her\b|their\b|some\b|most\b|other\b|many\b|no\b|but\b|and\b|so\b|yeah\b|because\b|that\b|was\b|is\b|are\b)[\w-]+ ){{0,3}}(?:[\w-]+ and )?({}) (?:(?!former\b|ex\b|non\b|not\b|community\b|friends?\b|family\b|people\b)[\w-]+ ){{0,2}}\Z", faith()));
regex!(POLITICS_HERE, format!(r"(?:^|[.!?,;(] *)(?:a |an )?(?:(?!not\b|no\b|anti\b|ex\b|non\b|former\b)[\w-]+ ){{0,2}}?({}) \Z", party()));
regex!(CHAIN, format!(r"\bi(?:'m| am|m)[ \t]+(?:an?[ \t]+)?(?:[\w-]+[ \t]+)?(?:{party})(?:(?:,|,?[ \t]+and|,?[ \t]+&|/)[ \t]*(?:an?[ \t]+)?(?:[\w-]+[ \t]+)?(?:{party}))*(?:,|,?[ \t]+and|,?[ \t]+&|/)[ \t]*(?:an?[ \t]+)?(?:(?!not\b|anti\b|ex\b|non\b|former\b)[\w-]+[ \t]+)?$", party = party()));
regex!(ADJECTIVAL, r"\bi(?:'m|m| am| m)[ \t]+(?:(?:very|pretty|fairly|quite|really|super|more|so|too|rather|relatively|kinda|kind of|somewhat|generally|mostly|extremely|a bit|a little)[ \t]+)*$");
regex!(POLITICAL, r"\b(?:politic\w*|vot\w+|left|right|democrats?|republicans?|liberals?|trump|biden|harris|government|party|parties|policy|policies|economic\w*|socially|fiscally|leftists?|socialis\w*|maga|gop|tory|tories|labour|elections?|candidates?|congress|senate|parliament|conservatives)\b");
regex!(CANNABIS, r"\b(?:weed|pot|blunts?|joints?|bowls?|spliffs?|dabs?|carts?|bud|herb|stoner|pothead|cannabis|marijuana|thc|420|ganja|kush|bongs?|toke|toking)\b");
regex!(UPPER, r"\b(?:meth|methamphetamine|cocaine|coke|crack|adderall|amphetamines?|stimulants)\b");
regex!(DIET_HERE, r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian|flexitarian) \Z");

fn ideology(m: &Match, g: usize) -> V {
    let (start, end) = m.span(g)?;
    let found = &m.string[start..end];
    COMPOUNDS.iter().find(|(prefix, base, _)| eq(found, base) && ends_at(m.string, start, prefix)).map(|(_, _, full)| *full).or_else(|| get(POLITICS, Some(found)))
}

fn sided(attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> V + Send + Sync + 'static, hedge: Hedge) -> Rule {
    let party = attribute == "party_affiliation";
    r(attribute, pattern, move |m| value(m).filter(|found| PARTIES.contains(found) == party), hedge)
}

fn quitting(m: &Match) -> V {
    let end = (m.end() + 24).min(m.string.len());
    if contains(m.text(), "never") || !CANNABIS.test(&m.string[m.start()..end]) {
        None
    } else {
        Some("cannabis")
    }
}

fn active(m: &Match) -> &'static str {
    if contains(m.text(), "guard") || contains(m.text(), "reserv") {
        "reserve / national guard"
    } else {
        "serving"
    }
}

fn branch(m: &Match) -> V {
    let word = st(m.first()?);
    if word.contains("navy") {
        Some("navy")
    } else if word.contains("air") || word == "usaf" || word == "raf" {
        Some("air force")
    } else if word.contains("marine") || word == "usmc" {
        Some("marines")
    } else if word.contains("army") {
        Some("army")
    } else if word.contains("coast") || word == "uscg" {
        Some("coast guard")
    } else {
        None
    }
}

fn faith_of(m: &Match) -> V {
    let g = m.first_index()?;
    let (start, _) = m.span(g)?;
    let found = m.group(g)?;
    PAGANS.iter().find(|(prefix, base, _)| eq(found, base) && ends_at(m.string, start, prefix)).map(|(_, _, value)| *value).or_else(|| get(RELIGIONS, Some(found)))
}

fn named(m: &Match) -> bool {
    let Some((start, end)) = m.first_index().and_then(|g| m.span(g)) else { return false };
    eq(&m.string[start..end], "christian") && original(m.string).is_some_and(|text| text[start] == 'C' && text.get(end) == Some(&' ') && text.get(end + 1).is_some_and(|c| c.is_uppercase()))
}

fn believed(m: &Match) -> V {
    if SCOPED.test_in(m.string, back(m, 30), m.start()) || named(m) {
        None
    } else {
        faith_of(m)
    }
}

fn faith() -> String {
    alternation(RELIGIONS.iter().map(|(k, _)| *k))
}

fn party() -> String {
    longest_first(keys(POLITICS))
}

fn loose(m: &Match) -> bool {
    let Some((start, end)) = m.span(1) else { return false };
    let word = &m.string[start..end];
    eq(word, "moderate") && ADJECTIVAL.test_in(m.string, start.saturating_sub(40), start) && !POLITICAL.test(m.string) && !original(m.string).is_some_and(|text| text[start].is_uppercase())
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
        faith_of(m)
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

fn side(word: &[char]) -> V {
    let word: Vec<char> = word.iter().map(|&c| if c == '-' { ' ' } else { c }).collect();
    let left = contains(&word, "left");
    let extreme = starts_at(&word, 0, "far ") || starts_at(&word, 0, "extreme ") || starts_at(&word, 0, "radical ");
    Some(if contains(&word, "cent") || contains(&word, "leaning") {
        if left { "left-leaning / centre-left" } else { "right-leaning / centre-right" }
    } else if left {
        if contains(&word, "wing") && !extreme { "left-wing" } else { "leftist" }
    } else {
        "right-wing"
    })
}

fn diet_mine(m: &Match) -> V {
    let before = lead(m);
    let group = m.text();
    let word = FOODWAY.at(group, 0)?.text();
    let framed = if word.len() < group.len() {
        ADOPTED.test(before)
    } else {
        ["keto", "low carb", "low-carb", "carnivore", "low fodmap", "low-fodmap"].iter().any(|w| eq(word, w)) && NOT_DIET.at(m.string, m.end()).is_none() && STARTED.test(before)
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

fn first_hand(m: &Match, result: &'static str) -> V {
    if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) {
        None
    } else {
        Some(result)
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
        Some("veteran")
    } else {
        Some(active(m))
    }
}

fn served(m: &Match) -> V {
    first_hand(m, "veteran")
}

fn counted(m: &Match) -> V {
    if COUNTED.test_in(m.string, back(m, 20), m.start()) {
        served(m)
    } else {
        None
    }
}

fn entered(m: &Match) -> V {
    if !ENTERED.test_in(m.string, sentence_start(m), m.start()) {
        None
    } else if contains(m.text(), "joined") || contains(m.text(), "enlisted") || contains(m.text(), "went into") {
        service(m)
    } else {
        served(m)
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
        Some("veteran")
    } else {
        Some("serving")
    }
}

fn titled(m: &Match) -> V {
    let start = line_start(m.string, m.start());
    let end = line_end(m.string, m.end());
    if m.string[..start].iter().any(|c| !c.is_whitespace()) || !TAG_NEAR.test_in(m.string, start, end) || TITLE_OTHER.test_in(m.string, start, m.start()) {
        return None;
    }
    let kind = m.g(1);
    Some(if kind == "vet" || kind == "veteran" { "veteran" } else { "serving" })
}

fn profile_vet(m: &Match) -> V {
    let before = lead(m);
    if (SELF_NEAR.test(before) || TAG_NEAR.test(before)) && !OTHER_NEAR.test(before) {
        Some("veteran")
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
    faith_of(m)
}

#[allow(non_snake_case)]
fn religion() -> Vec<Rule> {
    let FAITH = faith();
    let ASX = format!(r"(?:{AS}|as(?<=[\x{{2600}}-\x{{27BF}}\x{{1F000}}-\x{{1FFFF}}] as)|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as)|as(?<=\bas)(?= an? (?:[\w-]+ )?[\w-]+,? (?:i|i'm|i've|i'd|i'll|im|ive|we|myself)\b))");
    let ISM = longest_first(ISMS.iter().map(|(k, _)| *k));
    vec![
        r("religion", &format!(r"i(?<=\bi){ME} {FREE}(?:a |an )?{FREE}(?:(?!non-|ex-|anti-|post-|pro-|never-|not-)[a-z]+-)?({FAITH})\b{NOT_FAITH_NOUN}"), believed, TAGGED),
        r("religion", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|anti\b|ex\b|non\b|former\b|neither\b|nor\b|the\b|any\b|your\b|his\b|her\b|their\b|this\b|that\b|these\b|those\b|some\b|my\b|being\b|for\b|to\b|at\b|by\b|with\b|about\b|from\b|coming\b|visiting\b|he\b|she\b|they\b|you\b|was\b|were\b|is\b|are\b|raised\b|born\b|grew\b|up\b|formerly\b|lapsed\b|recovering\b)[\w-]+,? (?:and )?){{1,4}}(?:a |an )?({FAITH})\b{NOT_FAITH_NOUN}"), believed, self_hedge()),
        r("religion", &format!(r"{ASX} an? (?:(?!former\b|ex\b|non\b|lapsed\b|recovering\b)[\w-]+ ){{0,2}}?({FAITH})\b|b(?<=\bb)eing an? ({FAITH})(?:,| i\b)|being(?:(?<=^being)|(?<=[.!?\n]being)|(?<=[.!?\n] being)) (?:an? )?(?:[\w-]+ )?({FAITH})\b(?!s\b)(?! (?:does|doesn't|isn't|means|makes|can|should|would|will)\b)|\b(?:we|us) ({FAITH})s\b|\bi (?:became|became a|turned|am now|'m now|have become) ({FAITH})\b"), spoken_religion, self_hedge()),
        r("religion", r"(?:أنا|انا|أني|اني) (مسلم|مسلمة|مسيحي|مسيحية|ملحد|ملحدة)", foreign, self_hedge()),
        r("religion", concat!(r"(?<!\bnão )(?<!\bnao )(?<!\bno )\b(?:soy|sou) (?:(?:algo|más|mais|muy|muito|bastante|como|bien|bem|un|una|um|uma) ){0,3}?(cat[óo]lic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|agnóstic[oa]|evangélic[oa])\b",
          r"|\bje suis (catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|agnostique)\b|\bich bin (katholisch|christ|christin|atheist|atheistin|muslim|muslima|jüdisch|evangelisch|agnostiker)\b",
          r"|\bjestem (katolikiem|katoliczką|ateistą|ateistką|chrześcijaninem|chrześcijanką|muzułmaninem|muzułmanką)\b|\bsono (cattolic[oa]|ateo|atea|cristian[oa]|musulman[oa]|ebre[oa])\b|\bik ben (katholiek|christen|atheïst|moslim|joods)\b",
          r"|\b(?:como|en tant que|als|come|jako) (?:un |una |um |uma |une |ein |eine )?(católic[oa]|cristian[oa]|cristã|cristão|ateo|atea|ateu|ateia|musulmán|musulmana|judío|judía|judeu|judia|evangélic[oa]|catholique|chrétien(?:ne)?|athée|musulman(?:e)?|juif|juive|katholik(?:in)?|christ(?:in)?|atheist(?:in)?|jude|jüdin|cattolic[oa]|katolik|ateista|ateistka|chrześcijanin|chrześcijanka)\b",
          r"|\bjag är (?:(?!inte\b)\w+ )?(ateist|kristen|muslim|katolik|agnostiker|jude|judisk|buddhist|hindu)\b|\bär jag (ateist|kristen|muslim|katolik|agnostiker|jude|judisk|buddhist|hindu)\b",
          r"|\bsam (ateista|ateist|katolik|katolkinja|pravoslavac|pravoslavka|musliman|muslimanka)\b|\bя (христианка|христианин|атеист|атеистка|мусульманин|мусульманка|православный|православная|католик|католичка)\b",
          r"|(?<!\beski )\b(ateistim|müslümanım|hristiyanım|deistim|agnostiğim)\b|\bjeg er (?:(?!ikke\b)\w+ )?(ateist|kristen|muslim|katolikk|katolik|agnostiker|jøde)\b"),
          foreign, self_hedge()),
        r("religion", r"i(?<=\bi)(?: (?:also|personally|actually|just|definitely|certainly|honestly|really))?(?:'m| am|m| m) (?:also |personally |actually |just |definitely |certainly |honestly |literally )?(?:not|no|neither) (?:a |very |really |particularly |that |super |overly |at all |even |remotely |exactly |all that |terribly |the least bit )?religious(?: person)?\b|n(?<=\bn)ot(?:(?<=^not)|(?<=[.!?\n]not)|(?<=[.!?\n] not)|(?<=[.!?\n]  not)) (?:a |very |really |particularly )?religious(?: person)?\b|i(?<=\bi)(?:'m| am) (?:a )?(?:non-?religious|irreligious)\b|i(?<=\bi) (?:don't|do not|dont) (?:have|practice|follow|subscribe to|belong to|adhere to) (?:a |any )?(?:\w+ )?(?:specific |particular |organi[sz]ed |formal )?religion\b|i(?<=\bi)(?:'m| am) not (?:a )?follower of any religion\b|b(?<=\bb)eing (?:a )?non[- ]?religious\b|i(?<=\bi)(?:'m| am) (?:a |an )?(?:[\w-]+ ){1,3}(?:and )?(?:a |an )?non[- ]?religious\b|i(?<=\bi) (?:wouldn't|would not|don't|do not|dont) (?:consider|call) myself religious\b|i(?<=\bi) have no religion\b|i(?<=\bi) (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|i(?<=\bi) loathe (?:all )?religion\b|s(?<=\bs)piritual,? (?:but )?not religious\b|m(?<=\bm)ore spiritual than religious\b|я(?<=\bя) не религиозн|n(?<=\bn)o soy religios[oa]\b|i(?<=\bi)ch bin nicht religiös\b",
          |m| Some(if contains(m.text(), "god") { "atheist" } else if contains(m.text(), "spiritual") { "spiritual" } else { "not religious" }), TAGGED),
        r("religion", &format!(r"i(?<=\bi)(?:'d| would| have| 've)? (?:always )?(?:consider myself|identify as|would call myself|call myself|describe myself as|consider myself to be|see myself as|view myself as|define myself as) (?:a |an )?(?:\w+ )?({FAITH})\b|(?:w(?<=\bw)e|u(?<=\bu)s) as ({FAITH})s\b|a(?<=\ba)s ({FAITH})s,? (?:we|us|our)\b|f(?<=\bf)ellow ({FAITH})s?\b"), spoken_religion, self_hedge()),
        r("religion", r"h(?<=\bh)ere\b", |m| labelled(m, &RELIGION_HERE, RELIGIONS), self_hedge()),
        r("religion", &format!(r"r(?<=\br)eligion[ \t*_]*[:=][ \t*_]*(?:(?:roman|devout|practicing|practising|non-?denominational|born again|sunni|shia) )?({FAITH})\b"), faith_of, self_hedge()),
        r("religion", &format!(r"i(?<=\bi){ME} (?:an? )?(?:\w+ )?(agnostic)[- ](?:atheist|christian|theist|catholic|deist|pagan|buddhist|jew|muslim)\b"), |m| get(RELIGIONS, m.group(1)), self_hedge()),
        r("religion", &format!(r"\b(?!witch\b|spiritual\b|humanist\b)({FAITH})\b(?!'?s\b| (?:girls|guys|women|men|couples|husband|partner|family|families|people|friends?|community|folks|countries|country|ladies|dudes|boys|females|males|mythology)\b)"), profiled, self_hedge()),
        r("religion", &format!(r"\A\W*(?:\d{{2}}\s*[mf]?\W*)?(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?({FAITH}) (?:couple|guy|girl|man|woman|male|female|m|f|dad|mom|here|only)\b"), faith_of, self_hedge()),
        r("religion", &format!(r"\A\W*(?:(?:yes|yep|yeah|yup|yea|well|me|personally|myself)\W+)?(?!witch\b|spiritual\b|humanist\b)(?:(?:roman|devout|practicing|practising|proud|non-?denominational|born again) )?({FAITH})[ \t]*(?:[.!]|\n|\Z|\p{{So}})"), faith_of, self_hedge()),
        r("religion", &format!(r"\|[ \t]*({FAITH})[ \t]*(?=\||\n|\Z)"), |m| piped(m, RELIGIONS), self_hedge()),
        needs(r("religion", &format!(r"(?<![\w'-])({FAITH})(?![\w'-])"), |m| if flair(m) { faith_of(m) } else { None }, TAGGED), &keys(RELIGIONS)),
        r("religion", &format!(r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:converted|reverted|came|come|returned|turned) to ({ISM})\b|i(?<=\bi)(?:'ve| have)? (?:\w+ )?joined (the catholic church|the orthodox church|the lds church)\b"),
          |m| if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) { None } else { get(ISMS, m.first()) }, self_hedge()),
        r("religion", r"i (?<=\bi )(?:\w+ )?pray (?:that )?allah\b", constant("muslim"), self_hedge()),
        r("religion", r"my (?<=\bmy )(?:relationship|walk|journey) with (?:god|christ|jesus|the lord)\b|i (?<=\bi )(?:\w+ )?(?:seek|follow|love|accepted|believe in|trust in|pray to|worship) (?:jesus|christ|the lord)\b|i (?<=\bi )(?:\w+ )?pray (?:to god|every (?:day|night|morning)|daily|the rosary)\b",
          constant("christian (unspecified)"), self_hedge()),
        r("religion", r"my (?<=\bmy )(pagan|wiccan|witchy|heathen|druid|druidic|druidry|witchcraft) (?:community|path|practice|journey|beliefs|faith|spirituality|tradition|altar|craft|friends|group)\b", |m| get(CRAFTS, m.group(1)), self_hedge()),
        r("religion", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:home |local |new |old )?(church|pastor|priest|parish|congregation|mosque|masjid|imam|synagogue|shul|rabbi)\b(?! (?:friends?|youth group)\b)",
          |m| {
              if !free(m) {
                  return None;
              }
              let place = m.g(1);
              Some(if ["mosque", "masjid", "imam"].contains(&place.as_str()) { "muslim" } else if ["synagogue", "shul", "rabbi"].contains(&place.as_str()) { "jewish" } else { "christian (unspecified)" })
          }, self_hedge()),
        r("religion", &format!(r"(?:i(?<=\bi){ME}|{ASX}) (?:an? )?(?:(?:practicing|practising|devout|proud|traditional|twelver) )?(sunni|shia|shi'?ite)(?: muslim)?\b|\A\W*(?:(?:devout|practicing|practising|proud|traditional) )?(sunni|shia)(?: muslim)?[ \t]*(?:[.!]|\n|\Z)"),
          |m| Some(if contains(m.text(), "sunni") { "sunni" } else { "shia" }), self_hedge()),
        r("religion", &format!(r"i(?<=\bi)(?:'m| am| m|m) (?:also |very |quite |pretty |deeply |fairly |really |super |extremely |a |a very |a deeply )?religious(?: person| guy| girl| man| woman)?\b(?! (?:about|with|when|af|asf)\b| (?:an? )?(?:{FAITH})\b)|i(?<=\bi) (?:do |still |truly |firmly |definitely )?believe in (?:a )?god(?=[ \t]*(?:[.!,;\n]|$))|i(?<=\bi)(?:'m| am) a jain\b|a(?<=\ba)s a jain\b"),
          |m| Some(if contains(m.text(), "jain") { "jain" } else { "religious (unspecified)" }), self_hedge()),
        r("religion", &format!(r"(?:i(?<=\bi){ME}|{ASX}) (?:an? )?(?:[\w-]+ )?(?:pagan|practicing|practising|eclectic|hedge|green|kitchen|solitary|baby|hereditary|traditional|cottage|folk|wiccan|[a-z]+-quaker|buddhist|hellenic|norse)[- ]witch\b|i(?<=\bi) (?:(?!not\b|never\b|dont\b|didnt\b)\w+ )?practi[cs]e (?:\w+ )?witchcraft\b"), constant("witch"), self_hedge()),
    ]
}

#[allow(non_snake_case)]
fn political(LISTED: &str, attribute: &'static str) -> Vec<Rule> {
    let PARTY = party();
    let ASX = format!(r"(?:{AS}|as(?<=[\x{{2600}}-\x{{27BF}}\x{{1F000}}-\x{{1FFFF}}] as)|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as))");
    vec![
        sided(attribute, &format!(r"i(?<=\bi){ME} {FREE}?(?:a |an )?{FREE}?{FILLER}({PARTY})\b(?! (?:party|drama|enjoyer|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|with|about|when|in terms|on|in my|of|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach|socialism|capitalism|communism|sized|drinking)\b)"),
          |m| if quoted(m) || loose(m) || SCOPED.test_in(m.string, back(m, 30), m.start()) { None } else { ideology(m, 1) }, TAGGED),
        sided(attribute, &format!(r"i(?<=\bi)(?:'ve| have|'d| would)? (?:always |would |'d )?(?:consider myself|identify as|would call myself|call myself|describe myself as|consider myself to be|see myself as|view myself as|viewed myself as|saw myself as|define myself as) (?:a |an )?(?:\w+ )?({PARTY})\b|i(?<=\bi)(?:'m| am) a registered (democrat|republican)\b|(?:\A|[.!?\n] *)(?:a )?registered (democrat|republican)\b|i(?<=\bi) (?:\w+ )?lean(?:s)? (?:more |pretty |very |slightly |a bit |a little |heavily |strongly |hard )?(?:to the |towards the |toward the |towards |toward )?(left|right|liberal|conservative|progressive|libertarian|socialist)\b(?! (?:on|against|into|over|back|forward|in)\b)"),
          |m| ideology(m, 1).or_else(|| ideology(m, 2)).or_else(|| ideology(m, 3)).or_else(|| ideology(m, 4)).or_else(|| m.group(4).map(|g| if eq(g, "left") { "left-leaning / centre-left" } else { "right-leaning / centre-right" })), self_hedge()),
        sided(attribute, &format!(r"(?:w(?<=\bw)e|u(?<=\bu)s) ({PARTY})s\b|m(?<=\bm)e and (?:every|other|fellow|all the) ({PARTY})s?\b|c(?<=\bc)ent(?:er|re)[- ](left|right)(?: \w+){{0,2}} here\b|i(?<=\bi)(?:'m| am) (?:a )?maga\b|i(?<=\bi) (?:\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(republican|gop|democrat)\b"),
          |m| if contains(m.text(), "maga") { Some("maga / trump supporter") } else { ideology(m, 1).or_else(|| ideology(m, 2)).or_else(|| get(VOTED, m.group(4))).or_else(|| m.group(3).and_then(|_| side(m.text()))) }, self_hedge()),
        sided(attribute, &format!(r"{ASX} an? (?:(?!former\b|ex\b|non\b|anti\b)\w+ )?({PARTY})\b(?! (?:as|party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?|arts|education|college|degree|use|amount|drinker|smoker|pain|exercise|interpretation|reading|translation|estimate|side|approach|socialism|capitalism|communism|operations?|business|company|players?|users?|levels?|amounts?)\b)"),
          |m| ideology(m, 1), hedge()),
        sided(attribute, r"he(?<=\bhe)re\b", |m| labelled(m, &POLITICS_HERE, POLITICS), self_hedge()),
        sided(attribute, &format!(r"\A\W*\d{{2}} ?(?:[mf]|yo|y/o|years? old)?\W*(?:[\[\(]?[mf]4[mfat]\w*[\]\)]?\W*)?(?:(?!looking\b|seeking\b|for\b|wants?\b|with\b|ex\b|former\b|non\b|not\b|and\b|anti\b)[\w-]+ ){{0,2}}({PARTY})\b(?! (?:girls?|guys?|women|men|females?|males?|partner|wife|husband|party|media|state|city|area|town)\b)"), |m| ideology(m, 1), self_hedge()),
        sided(attribute, LISTED, listed, self_hedge()),
        needs(sided(attribute, &format!(r"(?<![\w'-])({PARTY})(?![\w'-])"), |m| if flair(m) && !eq(m.text(), "moderate") { ideology(m, 1) } else { None }, TAGGED), &keys(POLITICS)),
        needs(sided(attribute, &format!(r"(?<![\w'-])({PARTY})\b"), |m| if CHAIN.test_in(m.string, sentence_start(m), m.start()) { ideology(m, 1) } else { None }, self_hedge()), &[",", "and", "&", "/"]),
        sided(attribute, &format!(r"f(?<=\bf)ellow ({PARTY})s?\b"), |m| if quoted(m) || m.start() > 0 && "'\u{2018}".contains(m.string[m.start() - 1]) { None } else { ideology(m, 1) }, self_hedge()),
        sided(attribute, concat!(r"\b(?:i'm|im|i am|i m) [*_]*(?:on|firmly on|solidly on|squarely on|also on)[*_]* the [*_]*((?:far[- ])?(?:left|right))\b(?=[ \t*_]*(?:[.,;:!)\n]|$| (?:politically|side|wing|of (?:the )?(?:political )?spectrum|on (?:most|many|social|economic|this|that)|but|and|here|too|when|though|tho)\b))",
          r"|\b(?:i'm|im|i am|i m) (?:a |an )?(?:(?!not\b|never\b|no\b|on\b|the\b)[\w-]+ ){0,2}?((?:far|extreme|radical)[- ](?:left|right)(?:[- ]wing|[- ]leaning|ist)?|left[- ]wing(?:er)?|right[- ]wing(?:er)?|left[- ]leaning|right[- ]leaning|leftist|lefty|(?:left|right)[- ]of[- ]cent(?:er|re)|cent(?:er|re)[- ](?:left|right))\b"),
          |m| side(m.nonempty(1).or(m.group(2))?), self_hedge()),
        sided(attribute, &format!(r"{ASX} an? (?:(?!not\b|non\b|ex\b|former\b)[\w-]+ ){{0,2}}?((?:far|extreme|radical)[- ](?:left|right)(?:[- ]wing|[- ]leaning|ist)?|left[- ]wing(?:er)?|right[- ]wing(?:er)?|left[- ]leaning|right[- ]leaning|(?:left|right)[- ]of[- ]cent(?:er|re)|cent(?:er|re)[- ](?:left|right))\b"),
          |m| side(m.group(1)?), hedge()),
        sided(attribute, concat!(r"i(?<=\bi)(?:'m| am) a (?:lifelong |registered |proud |longtime )?(dem)\b|i(?<=\bi) (?:(?!never\b|won't\b|wont\b|wouldn't\b|didn't\b|didnt\b|can't\b|cant\b)\w+ )?(?:voted|vote|will vote|am voting|'m voting) (?:for )?(?:the )?(republicans|democrats|dems|blue|red|green)\b(?! (?:light|line|state|flag|button|card|wave|tide)\b)"),
          |m| get(STANCES, m.first()), self_hedge()),
        sided(attribute, r"i(?<=\bi)(?:'m| am) a (?:lifelong |registered |proud |longtime |card[- ]carrying )?(labour|tory|green party|independent|lib dem|libdem|reform uk|reform|libertarian party) (?:member|voter|supporter)\b|i(?<=\bi)(?:'m| am) a (?:\w+ )?member of the (labour party|green party|libertarian party|liberal democrats|lib dems|reform uk|conservative party)\b|i(?<=\bi)(?:'m| am) a registered (independent)\b|i(?<=\bi)(?:'m| am) a (?:lifelong |proud |card[- ]carrying )?(tory)\b|i(?<=\bi) (?:always |usually |have always |'ve always )?(?:vote|voted) (?:for )?(?:the )?(labour|tory|tories|lib dems?|libdems?|liberal democrats|reform uk)\b",
          |m| get(BRITISH, m.first()), self_hedge()),
    ]
}

#[allow(non_snake_case)]
fn diet() -> Vec<Rule> {
    let ASX = format!(r"(?:{AS}|as(?<=[\x{{2600}}-\x{{27BF}}\x{{1F000}}-\x{{1FFFF}}] as)|as(?<=\byeah as)|as(?<=\bbecause as)|as(?<=\balso as)|as(?<=\bnow as)|as(?<=\bonly as))");
    vec![
        r("diet", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b|recovering\b|bad\b|trying\b|thinking\b|considering\b|planning\b)[\w-]+ )?(?:a |an )?(?:(?!not\b|never\b|no\b|ex\b|non\b|former\b)[\w-]+ )?(vegan|vegetarian|vegeterian|vegitarian|veggie|pescatarian|pescetarian|flexitarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)"), |m| get(DIETS, m.group(1)), hedge()),
        r("diet", &format!(r"{ASX} an? (?:(?!ex\b|former\b|non\b)\w+ )?(vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)"), |m| get(DIETS, m.group(1)), hedge()),
        r("diet", concat!(r"we(?<=\bwe)(?:'re| are) (?:all |both |also |strictly )?(vegan|vegetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friendly)\b)|(?:s(?<=\bs)oy|s(?<=\bs)ou|s(?<=\bs)ono|i(?<=\bi)ch bin|i(?<=\bi)k ben) (vegan[oa]?|vegetarian[oa]|vegetarisch|vegetarier(?:in)?|vegetariër|veganer(?:in)?)\b",
          r"|j(?<=\bj)e suis (végane?|végétarien(?:ne)?|vegan)\b|j(?<=\bj)estem (weganką|weganinem|wegetarianką|wegetarianinem)\b"),
          |m| { let word = m.first()?; get(DIETS, Some(word)).or(Some(if contains(word, "tar") { "vegetarian" } else { "vegan" })) }, self_hedge()),
        r("diet", concat!(r"i(?<=\bi)(?:'m| am| have| was diagnosed with| got diagnosed with|'ve got| also have)? (?:a )?(?:celiac|coeliac)\b|m(?<=\bm)y (?:celiac|coeliac)\b|i(?<=\bi)(?: (?:eat|am|have to (?:eat|be|stay)|keep|went|stay)|'m) (?:strictly |completely |100% )?gluten[- ]free\b|t(?<=\bt)he gf diet\b",
          r"|i(?<=\bi)(?:'m| am) (?:\w+ )?(?:gluten|wheat)[- ]intolerant\b|i(?<=\bi) (?:can't|cannot|can not|can't really) (?:have|eat|do|tolerate) (?:any )?(?:gluten|wheat)\b|(?<!\bshould )(?<!\bcould )(?<!\bwould )(?<!\bcan )(?<!\bdo )(?<!\bdid )(?<!\bwill )i(?<=\bi) (?:\w+ )?(?:cut|cutting) out (?:\w+ and )?gluten\b(?! for\b)"), constant("gluten-free"), self_hedge()),
        r("diet", r"i(?<=\bi)(?:'m| am) (?:on |doing )?(?:a |strict )?(keto)\b(?! (?:friendly|recipe))|i(?<=\bi) (?:do|eat|follow|went) (keto|ketogenic|low[- ]carb)\b|(?:\A|[.!?\n] ?)been (?:doing|on|eating) (?:strict |clean |dirty |lazy )?(keto|low[- ]carb)\b(?! (?:friendly|recipe))",
          |m| Some(if contains(m.text(), "carb") { "low carb" } else { "keto" }), self_hedge()),
        r("diet", r"i(?<=\bi)(?:'m| am|'ve been| have been)? (?:(?!not\b|never\b|no\b|dont\b|didnt\b|stopped\b|quit\b|used\b|tried\b|want\b|wanted\b)\w+ )?(?:do|doing|on|following|follow|practice|practicing|eat|eating) (?:a |an |strict |mostly )?(intermittent fasting|omad|paleo|high[- ]protein)(?: diet)?\b|(?:\A|[.!?\n] ?)been (?:doing|on|eating) (?:a |strict )?(intermittent fasting|omad)\b",
          |m| { let word = m.g(1); Some(if word == "paleo" { "paleo" } else if word.starts_with("high") { "high protein" } else { "intermittent fasting" }) }, self_hedge()),
        r("diet", r"i(?<=\bi) (?:don't|do not|dont) eat (meat|any meat|animal products)\b|i(?<=\bi)(?:'m| am) (?:fully |mostly |\d+% )?(plant[- ]based)\b|i(?<=\bi) eat (plant[- ]based)\b", |m| Some(if contains(m.text(), "meat") { "vegetarian" } else { "plant-based" }), self_hedge()),
        r("diet", r"i(?<=\bi) eat meat\b|i(?<=\bi)'?m a (?:meat eater|omnivore)\b", constant("omnivore / meat eater"), hedge()),
        r("diet", r"(?:vegan|vegetarian|veggie|pescatarian|pescetarian|flexitarian|keto|ketogenic|low[- ]carb|low[- ]fodmap|gluten[- ]free|dairy[- ]free|sugar[- ]free|plant[- ]based|halal|kosher|carnivore|mediterranean)\b(?: (?:diet|lifestyle|eating pattern|way of eating|woe|regimen)\b)?", diet_mine, self_hedge()),
        r("diet", concat!(r"i(?<=\bi)(?:'m| am|'ve been| have been| went| eat| stay| keep)(?: also| completely| strictly| mostly| now| currently| fully| totally| 100%)? (dairy|sugar)[- ]free\b(?! (?:products?|versions?|options?|alternatives?|recipes?|snacks?|gum|candy|ice cream|syrups?|drinks?|soda|sweeteners?|creamer|milk|cheese)\b)",
          r"|i(?<=\bi)(?:'ve| have)? (?:(?!not\b|never\b|no\b|havent\b|hadnt\b|didnt\b|dont\b|cant\b|wont\b|almost\b|nearly\b)\w+ )?(?:quit|cut out|gave up|given up) (?:all )?(?:added |refined )?(sugar|dairy)\b(?! for\b)"), |m| Some(if contains(m.text(), "sugar") { "sugar free" } else { "dairy free" }), self_hedge()),
        r("diet", r"i(?<=\bi) (?:only |strictly |always |also |still )?(?:eat|keep) (?:strictly |only )?(halal|kosher)\b(?! (?:sometimes|occasionally|once|when|at|if)\b)", |m| get(DIETS, m.group(1)), self_hedge()),
        r("diet", concat!(r"i(?<=\bi)(?:'m| am|'ve been| have been) (?:(?!not\b|never\b|no\b|havent\b|hadnt\b|didnt\b|dont\b|cant\b|wont\b|almost\b|nearly\b)\w+ )?(?:counting (?:my )?calories|tracking (?:my )?(?:calories|macros)|doing cico|calorie counting)\b",
          r"|i(?<=\bi)(?:'ve| have)? (?:just |finally |recently )?started (?:counting|tracking) (?:my )?(?:calories|macros)|i(?<=\bi)(?:'ve| have)? (?:just |finally |recently )?started (?:calorie counting|cico)",
          r"|i(?<=\bi) (?:(?!not\b|never\b|no\b|havent\b|hadnt\b|didnt\b|dont\b|cant\b|wont\b|almost\b|nearly\b)\w+ )?(?:count|track) (?:my )?(?:calories|macros)\b(?! (?:for|when|if|on)\b)"), constant("calorie counting"), self_hedge()),
        r("diet", r"here(?<=\bhere)\b", |m| labelled(m, &DIET_HERE, DIETS), self_hedge()),
        r("diet", r"i(?<=\bi)(?:'ve been| went| became| turned) (vegan|vegetarian|pescatarian)\b|been(?<=\bbeen) (?:strictly |completely |fully |mostly )?(vegan|vegetarian|pescatarian|gluten[- ]free|keto|low[- ]carb)\b|went(?<=\bwent) (vegan|vegetarian|pescatarian|gluten[- ]free|keto|low[- ]carb)\b", |m| get(DIETS, m.first()), self_hedge()),
        r("diet", &format!(r"(?:b(?<=\bb)eing|b(?<=\bb)ecoming|g(?<=\bg)oing|s(?<=\bs)witched to|s(?<=\bs)witching to) {TAKEN}(?![,\s]+(?:you|u)\b)"), own, self_hedge()),
        r("diet", r"\A\W*(?:(?:mostly|strict|strictly|proud) )?(vegan|vegetarian|pescatarian|pescetarian|flexitarian)[ \t]*(?:[.!]|\n|\Z)", |m| get(DIETS, m.group(1)), self_hedge()),
    ]
}

fn smoking() -> Vec<Rule> {
    vec![
        r("recovering_from", &(concat!(r"i(?<=\bi)(?: |'ve | have )(?:haven't|have not|havent) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b|h(?<=\bh)ave(?:n't| not|nt) (?:smoked|vaped|had a (?:cigarette|cig|smoke))\b",
          r"|i(?<=\bi) (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|since(?<=\bsince) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|after(?<=\bafter) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b",
          r"|when(?<=\bwhen) i (?:stopped|quit|gave up) (?:smoking|vaping|cigarettes|cigs|nicotine)\b|i(?<=\bi)(?:'ve| have)? never smoked\b").to_string()
          + &format!(r"|day(?<=\bday)s? {QUIT_SPAN}|week(?<=\bweek)s? {QUIT_SPAN}|month(?<=\bmonth)s? {QUIT_SPAN}|year(?<=\byear)s? (?:(?:smoke|nicotine|vape|cigarette)[- ]free|(?:without|off) (?:smoking|vaping|nicotine|cigarettes))\b")), quitting, self_hedge()),
        r("recovering_from", r"i(?<=\bi) (?:don't|do not|dont|never) (?:smoke|vape)\b|i(?<=\bi) quit smoking\b|i(?<=\bi) used to (?:smoke|vape)\b|i(?<=\bi)(?:'m|m| am) a non-?(?:smoker|vaper)\b|i(?<=\bi)'ve never (?:smoked|vaped)\b", |m| if contains(m.text(), "quit") || contains(m.text(), "used to") { quitting(m) } else { None }, Some(&*CONDITIONAL)),
        r("recovering_from", concat!(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a few|several) (?:days?|weeks?|months?|years?)\W{0,8}(?:after|since|off|without|free from|clean from|of not) (?:vaping|smoking|nicotine|cigarettes|cigs|the vape|juul|tobacco)\b",
          r"|i(?<=\bi)(?:'ve| have)? (?:(?:finally|officially|just|also|recently) )?(?:quit|stopped|given up|kicked) (?:the )?(?:vape|vaping|juul|cigarettes|cigs|nicotine|smoking|tobacco)\b",
          r"|just(?:(?<=^just)|(?<=[.!?\n]just)|(?<=[.!?\n] just)) (?:quit|stopped|gave up) (?:smoking|vaping|cigarettes|cigs)\b|d(?<=\bd)ay \d+ (?:of no|without|of not|off) (?:smoking|vaping|nicotine|cigarettes)\b"), quitting, self_hedge()),
        r("recovering_from", &format!(r"(?:i(?<=\bi)(?:'m|m| am)|{AS}) (?:a |an )?(?:[\w-]+ ){{0,2}}?(?:former|ex)[- ]?(?:smoker|vaper|vape user)\b|i(?<=\bi) (?:\w+ )?(?:was|am|'m) never a (?:\w+ )?smoker\b"), quitting, self_hedge()),
        r("recovering_from", concat!(r"i(?<=\bi)(?:'ve| have)? (?:(?!would\b|could\b|should\b|might\b|will\b|wanna\b|want\b|never\b)\w+ )?(?:quit|stopped|gave up|given up) (?:drinking|alcohol|the booze|booze|the drink)\b(?! for (?:like |about |around |only |just )?(?:a |\d|one|two|three|four|five|six|several|some|few))(?! (?:coffee|soda|pop|tea|milk|water|juice|energy drinks?|caffeine|like that|as much|so much|during|while|until)\b)|i(?<=\bi)(?:'m| am|m) an? (?:\w+ )?(?:recovering|sober) alcoholic\b",
          r"|i(?<=\bi)(?:'m| am|'ve been| have been) (?:\w+ )?(?:sober|clean) from (?:alcohol|drinking|booze)\b|\d(?<!\w\d)\d* (?:days?|weeks?|months?|years?) (?:sober from alcohol|alcohol[- ]free|without (?:a drink|alcohol|drinking)|since my last drink)\b",
          r"|i(?<=\bi) (?:haven't|have not|havent) (?:had a drink|drank|had alcohol|had a sip of alcohol) (?:in|for|since)\b"),
          |m| first_hand(m, "alcohol"), self_hedge()),
        r("recovering_from", concat!(r"\d(?<!\w\d)\d* (?:days?|weeks?|months?|years?) (?:gamble[- ]free|gambling[- ]free|without gambling)\b|days(?<=\bdays) gamble[- ]free\b|i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:quit|stopped|gave up|given up) gambling\b|i(?<=\bi)(?:'m| am|m) an? (?:\w+ )?recovering (?:gambler|gambling addict)\b"),
          |m| first_hand(m, "gambling"), self_hedge()),
        r("recovering_from", concat!(r"\d(?<!\w\d)\d* (?:days?|weeks?|months?|years?) (?:porn[- ]free|without porn|of no porn|no porn|of nofap|nofap|no fap)\b|i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:quit|stopped|gave up|given up) (?:watching )?porn\b|i(?<=\bi)(?:'m| am|m|'ve been| have been) (?:\w+ )?porn[- ]free\b"),
          |m| first_hand(m, "porn / sex"), self_hedge()),
        r("recovering_from", concat!(r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:quit|got off|kicked|stopped|gave up|given up) (?:heroin|opioids|opiates|fentanyl|fent|oxy|oxycodone|kratom|percs|percocet)\b|i(?<=\bi)(?:'m| am|'ve been| have been) (?:\w+ )?(?:clean|sober) (?:from|off) (?:heroin|opioids|opiates|fentanyl|fent|oxy|oxycodone|kratom|percs)\b"),
          |m| first_hand(m, "opioids"), self_hedge()),
        r("recovering_from", &format!(r"i(?<=\bi)(?:'m| am|'ve been| have been) (?:(?!not\b|never\b|no\b)[\w,]+ ){{0,4}}?(?:clean|sober) (?:from|off|off of) (?:my )?{UPPERS}|\d(?<!\w\d)\d* (?:days?|weeks?|months?|years?) (?:clean|sober) (?:from|off|off of) (?:my )?{UPPERS}|i(?<=\bi)(?:'m| am) an? (?:\w+ )?(?:recovering|former|ex[- ]?) {UPPERS} (?:addict|user|head)\b|i(?<=\bi)(?:'ve| have)? (?:(?!not\b|never\b|no\b|havent\b|hadnt\b|didnt\b|dont\b|cant\b|wont\b|almost\b|nearly\b)\w+ )?(?:quit|kicked|got off|gave up|given up|beat) (?:my )?(?:meth|cocaine|crack|benzos?|benzodiazepines|xanax|klonopin)\b"),
          |m| first_hand(m, if UPPER.test(m.text()) { "stimulants" } else { "benzodiazepines" }), self_hedge()),
    ]
}

fn veteran_if_service(m: &Match) -> V {
    if SERVICE.test(m.string) {
        Some("veteran")
    } else {
        None
    }
}

fn military() -> Vec<Rule> {
    vec![
        r("military_status", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:\w+ )?(?:rotc |jrotc |afrotc |nrotc |army |navy |air force |military )?(?:cadet|midshipman)\b(?! (?:nurse|program)\b)|i(?<=\bi){ME} (?:currently |also )?in (?:rotc|jrotc|afrotc|nrotc|army rotc|navy rotc|the (?:naval|air force|military|coast guard) academy|west point)\b"),
          constant("cadet / rotc"), self_hedge()),
        r("military_status", &(format!(r"i(?<=\bi){ME} (?:currently |still )?(?:in|serving in|enlisted in) the (?:us |u\.s\. )?(?:army|navy|marines|air force|airforce|military|national guard|coast guard|marine corps|reserves|space force)\b|i(?<=\bi){ME} (?:on )?active duty\b")
          + &format!(r"|i(?<=\bi){ME} (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service ?member|infantryman|paratrooper)\b(?! (?:biolog|scien|life\b|ecolog|mammal|tech|engineer|mechanic|electrician|surveyor|corps vet|vet|veteran))|i(?<=\bi){ME} (?:currently )?(?:deployed|stationed)\b")
          + r"|my(?<=\bmy) (?:platoon|squadron|battalion|deployment|chain of command|first sergeant|drill sergeant|commanding officer|nco|squad leader)\b"), |m| first_hand(m, active(m)), self_hedge()),
        r("military_status", &(format!(r"i(?<=\bi){ME} (?:a |an )?(?:former|retired|ex[- ]?) ?(?:soldier|marine|sailor|airman|service ?member|military|army|navy|paratrooper|infantryman)\b|my(?<=\bmy) (?:time|years|service) in the (?:army|navy|military|marines|corps|marine corps|service|air force|national guard)\b|i(?<=\bi)(?:'m| am) prior service\b")
          + &format!(r"|i(?<=\bi)(?:{ME}| was) {VET}|{AS} {VET}|when(?<=\bwhen) i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|i(?<=\bi) (?:served|was) (?:\w+ )?in the (?:forces|army|navy|marines|air force|military|coast guard|marine corps)\b|i(?<=\bi) served (?:my country|\d+ years|overseas|(?:two|three|four|\d) tours)\b")
          + r"|i(?<=\bi) (?:got out of|retired from|separated from) the (?:army|navy|marines|air force|military|service)\b|army(?<=\barmy) retiree\b|navy(?<=\bnavy) retiree\b|military(?<=\bmilitary) retiree\b|marine(?<=\bmarine) retiree\b|air(?<=\bair) force retiree\b|usmc(?<=\busmc) retiree\b|coast(?<=\bcoast) guard retiree\b"
          + r"|retired(?<=\bretired) (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force|military|usmc)\b"
          + &format!(r"|my(?<=\bmy)\b{VA}|i(?<=\bi)(?:'ve| have| was| got| am|'m)?\b{VA}")), |m| if m.text().ends_with(&['a', ' ', 'v', 'e', 't']) && !SERVICE.test(m.string) { None } else { Some("veteran") }, self_hedge()),
        r("military_status", r"\d(?<!\w\d)\d{1,2} ?% (?:p&t|sc|service[- ]connected)\b", constant("veteran"), self_hedge()),
        r("military_status", concat!(r"i(?<=\bi) (?:went to boot ?camp|went through (?:boot ?camp|basic(?: training)?)|did basic(?: training)?|got out of the (?:army|navy|marines|military|air force|service|guard|corps)|was (?:honorably |medically )?discharged|",
          r"was (?:a|an) (?:\w+ )?(?:soldier|marine|sailor|airman|medic|paratrooper|infantryman|nco)|was (?:a |an )?(?:\w+ )?(?:officer|sergeant|corporal|specialist) in the (?:army|navy|marines|air force|military))\b",
          r"|(?:i(?<=\bi) did|i(?<=\bi) spent|i(?<=\bi) served|a(?<=\ba)fter|m(?<=\bm)y) (?:\d+|two|three|four|five|six|eight|ten|twelve|fifteen|twenty) (?:years|yrs) (?:in|of) (?:the )?(?:army|navy|marines|military|air force|service|active duty|marine corps|guard|reserves)\b"),
          veteran_if_service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:(?!on |at |my |so |to |no |in |an )[a-z]{{2}} |army |air )?(?:national )?guard(?:sman|swoman)?\b(?! (?:duty at|dog)\b)|i(?<=\bi){ME} (?:a |an )?(?:reservist|guardsman|guardswoman)\b|i(?<=\bi){ME} (?:in|with) the (?:\w+ )?(?:reserves?|guard)\b"),
          constant("reserve / national guard"), self_hedge()),
        r("military_status", r"my (?<=\bmy )(?:va |disability |combined |current )?(?:rating|claim|c&p|dbq|vso|gi bill|tricare|dd-?214|va benefits|va healthcare|va doctor|va appointment|pact act)\b",
          |m| if MILITARY_WORDS.test(m.string) { Some("veteran") } else { None }, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:\w+ )?(?:officer|medic|nco|sergeant|corporal|private|specialist|pilot|mechanic|engineer|nurse|soldier|infantryman|linguist|analyst|doctor|chaplain) in the (?:army|navy|marines|air force|military|national guard|coast guard|reserves?|space force)\b"),
          constant("serving"), self_hedge()),
        r("military_status", &(r"i(?<=\bi) (?:\w+ )?served (?:\w+ )?(?:in (?:combat)|overseas|(?:\d+|two|three|four|five|six|eight|ten|twenty) (?:years|yrs|tours)|my (?:time|country|contract|enlistment))\b".to_string()
          + r"|i(?<=\bi) (?:did|'ve done|have done|had) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b"
          + &format!(r"|i(?<=\bi)(?:'m|m| am) (?:using|running|on) (?:the |my )?(?:gi bill|post[- ]9/11)\b|i(?<=\bi) (?:used|use) (?:the |my )?gi bill\b|i(?<=\bi){ME} (?:a |an )?(?:[\w-]+ ){{1,3}}(?:and )?(?:a )?(?:war|combat|army|navy|marine|air force|military|disabled|retired|coast guard) (?:vet|veteran)\b")
          + r"|i(?<=\bi) (?:was|spent) (?:\w+ ){1,3}in the (?:army|navy|marines|air force|military|coast guard|marine corps|national guard)\b"), veteran_if_service, self_hedge()),
        r("military_status", concat!(r"fellow(?<=\bfellow) (?:veterans|vets|servicemembers|service members)\b",
          r"|(?:a(?<=\ba)fter|s(?<=\bs)ince|w(?<=\bw)hen|b(?<=\bb)efore|o(?<=\bo)nce) (?:i )?(?:got out|getting out|ets(?:'d|ed)?|i separated|separating|i was discharged)\b(?! of (?:prison|jail|rehab|hospital|school|college|juvie|the hospital))|my(?<=\bmy) (?:\w+ )?(?:\d+|two|three|four|five|multiple|several) (?:deployments|combat tours|tours)\b|\d(?<!\w\d)\d* deployments\b"),
          veteran_if_service, self_hedge()),
        r("military_status", concat!(r"my(?<=\bmy) (?:(?!coding\b|code\b|data\b|fitness\b|web\b|ux\b|dev\b|design\b|space\b)\w+ )?(?:mos|afsc|ets|eas|dd-?214|dd 214|discharge papers|deployments?|tdy|duty station|first sergeant|drill sergeant|drill instructor|platoon sergeant|squad leader|nco|ncoic|commanding officer|bah|dog tags|cac card|basic training|boot camp|bootcamp|ait|tech school|bct|meps|enlistment|re-?enlistment|reenlistment|chain of command|battalion|platoon|brigade|regiment|time in service|military service|(?:military|army|navy|naval|marine|air force|usmc|coast guard) (?:career|medals|pension)|military id|military records?)\b",
          r"|i(?<=\bi) (?:(?!never\b|didn't\b|didnt\b|won't\b|wont\b|wouldn't\b|almost\b|nearly\b)\w+ )?(?:enlisted|reenlisted|re-enlisted|deployed (?:to|overseas|twice|with|for)|pcs'd|pcsed|ets'd|etsed|separated from the|was commissioned|got commissioned|commissioned as|shipped out to (?:basic|boot camp|bootcamp)|graduated (?:basic|boot camp|bootcamp|ait|ocs|bct))\b"), service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi) (?:was|got) (?:\w+ )?(?:stationed|deployed)\b|w(?<=\bw)h(?:en|ile) i was (?:\w+ )?(?:stationed|deployed|in (?:the )?{BRANCH}|on active[- ]duty|active[- ]duty|enlisted|in boot ?camp|in basic training)"), served, self_hedge()),
        r("military_status", &format!(r"(?:j(?<=\bj)oined|e(?<=\be)nlisted in|e(?<=\be)nlisted into|w(?<=\bw)ent into|l(?<=\bl)eft|d(?<=\bd)eployed with|d(?<=\bd)ischarged from|m(?<=\bm)edically retired from|s(?<=\bs)erved with) (?:the )?{BRANCH}"), entered, self_hedge()),
        r("military_status", &format!(r"(?:y(?<=\by)ears?|y(?<=\by)rs?|d(?<=\bd)ecades?) (?:(?:in|of service in|serving in|with|of active[- ]duty in|on active[- ]duty in) (?:the )?{BRANCH}|(?:of )?(?:military|active[- ]duty|naval|army|navy|marine corps|air force) service\b)|(?:y(?<=\by)ears?|y(?<=\by)rs?) (?:of )?active[- ]duty\b"), counted, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi)n(?:to)? the {BRANCH}(?! (?:blue|painter|surplus|times|store|green|issue|knife|boots?|jacket|style|museum|industrial|base)\b)"), within, self_hedge()),
        r("military_status", r"her(?<=\bher)e\b", here_label, self_hedge()),
        r("military_status", r"\A\W*(?:(?:proud|disabled|combat|retired|army|navy|marine|air force|usmc|military) )?(?:vet|veteran)[ \t]*(?:[.!]|\n|\Z)", constant("veteran"), self_hedge()),
        r("military_status", r"(?<=, )(?:a )?(?:(?:proud|disabled|combat|retired|army|navy|marine|military) )?(?:vet|veteran)(?=[ \t]*(?:[,.;/!\n]|$))", profile_vet, self_hedge()),
        r("military_status", r"i(?<=\bi) did (?:my|a|two|three|four|\d+) (?:army |navy |marine |military |combat |overseas )?tours?\b|i(?<=\bi) was in (?:a|an|the) (?:\w+ ){0,2}(?:infantry|artillery|armor|armored|cavalry|airborne|naval|army|military|national guard) (?:unit|battalion|regiment|company|division|platoon|brigade|squadron)\b", veteran_if_service, self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:currently |still )?with the {BRANCH}"), service, self_hedge()),
        r("military_status", r"g(?<=\bg)ot out in (?:'?\d{2}|\d{4})\b|\d(?<!\w\d)\d*\+? ?(?:years|yrs) (?:of )?(?:military|infantry|usmc|army|navy|marines|active duty|air force)(?=[ \t]*(?:[.,;!?\n]|$))", served, self_hedge()),
        r("military_status", r"\b(?:i'm|i am|im) (?:\w+ ){0,3}?(?:to|for) (?:navy |army |marine |air force |usaf |coast guard )?(?:boot ?camp|basic training|bmt|meps)\b", constant("serving"), self_hedge()),
        r("military_status", &format!(r"i(?<=\bi){ME} (?:(?!not\b|never\b|no\b|ex\b|former\b)\w+ )?(?:active[- ]duty )?military\b(?! (?:brat|spouse|wife|husband|family|families|kids?|child|history|style|grade|time|base|town|housing|vehicles?|surplus|discount|fan|buff|nerd|enthusiast|vet|veteran|retiree)\b)"), service, self_hedge()),
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
fn branches() -> Vec<Rule> {
    let BRANCHES = r"(?:us |u\.s\. |royal |british |canadian |australian )?(army|navy|air ?force|usaf|raf|marines|marine corps|usmc|coast guard|uscg)";
    let VETS = r"(?:us |u\.s\. |royal |british |canadian |australian )?(army|navy|air ?force|usaf|raf|marines|marine|marine corps|usmc|coast guard|uscg)";
    vec![
        r("military_branch", &format!(r"(?:w(?<=\bw)hen i|i(?<=\bi))(?:{ME}| was| served| enlisted| spent (?:\w+ ){{1,3}}| did (?:\w+ ){{1,3}}) (?:(?:currently|still|active duty|on active duty) )?in(?:to)? the {BRANCHES}\b(?! (?:of|surplus|store|museum|style|boots?|jacket|green|blue|base)\b)|i(?<=\bi) (?:got out of|retired from|left|joined|enlisted in|enlisted) (?:active duty )?(?:the |in the )?{BRANCHES}\b(?! (?:of|surplus|store|museum)\b)"),
          |m| if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) { None } else { branch(m) }, self_hedge()),
        r("military_branch", &format!(r"(?:i(?<=\bi){ME} (?:a |an )?|{AS} an? )(?:proud |disabled |combat |retired |former |old )?{BRANCHES} (?:vet|veteran|retiree)\b|i(?<=\bi){ME} (?:a |an )?(?:former |retired |ex[- ]?|active duty |proud )?(marine|airman)\b(?! (?:biolog\w*|scien\w*|life|ecolog\w*|mammals?|engineer\w*|corps of|tech\w*|mechanic\w*|electrician\w*|surveyor\w*)\b)"),
          |m| if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) { None } else { branch(m) }, self_hedge()),
        r("military_branch", &format!(r"i(?<=\bi){ME} (?:a |an )?(?:(?!of\b|with\b|for\b|to\b|like\b|not\b|never\b|no\b|than\b)[\w-]+,? ){{1,6}}?{VETS} (?:vet|veteran|retiree)\b|(?:\A|[.!?\n] *)(?:\d{{2}} ?[mf]? )?(?:a |an )?(?:proud |disabled |combat |retired |former )?{VETS} (?:vet|veteran|retiree)\b|(?:s(?<=\bs)erving|s(?<=\bs)tationed) in the {BRANCHES}\b|m(?<=\bm)y (?:pension|retirement|service|time|years|career|enlistment|contract) (?:from|in|with) the {BRANCHES}\b"),
          |m| if OTHER_NEAR.test_in(m.string, sentence_start(m), m.start()) { None } else { branch(m) }, self_hedge()),
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
        (r"\b(?:\d+|one|two", vec!["vap", "smok", "nicotine", "cig", "juul", "tobacco"]),
        (r"we(?<=\bwe)(?:'re| are) (?:all |both |also |strictly )?(vegan", vec!["veg", "pesc", "vég", "weg"]),
        (r"\b(?!witch\b|spiritual", digits),
        (r"i(?<=\bi)(?:'ve| have)? (?:\w+ )?(?:converted", vec!["convert", "revert", "came to", "come to", "turned to", "joined the"]),
        (r"(?:i(?<=\bi)(?:'m|m| am)|as(?:", vec!["smoker", "vaper", "vape user"]),
        (&military_prefix, vec!["army", "navy", "marine", "air force", "military", "guard", "reserves", "space force", "active duty", "soldier", "sailor", "airman", "service",
            "infantry", "paratrooper", "deploy", "stationed", "platoon", "squadron", "battalion", "chain of command", "sergeant", "commanding officer", "nco", "squad leader"]),
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
    for attribute in ["political_ideology", "party_affiliation"] {
        rules.extend(shared::scoped_rules(political(&LISTED, attribute)));
    }
    rules.extend(shared::scoped_rules(diet()));
    rules.extend(shared::scoped_rules(smoking()));
    rules.extend(shared::scoped_rules(military()));
    rules.extend(shared::scoped_rules(branches()));
    gated(rules, &LISTED)
}
