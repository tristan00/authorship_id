use claimcore::*;
use std::sync::LazyLock;

const OFFSET: &str = r"(?:gmt|utc) ?[+\-−] ?\d{1,2}(?:[:.][0-5]\d)?";
const LONG: &str = r"(?:eastern|central|mountain|pacific|atlantic|alaska|hawaii|east coast|west coast)(?: standard| daylight)? time(?: ?zone)?";
const CODES: &str = "est|edt|cst|cdt|mst|mdt|pst|pdt|akst|akdt|hst|gmt|utc|bst|ist|cet|cest|eet|eest|wet|msk|aest|aedt|acst|acdt|awst|nzst|nzdt|jst|kst|sgt|hkt|pht|wib|sast|brt|ast|adt|nst|ndt";
const STRICT: &str = "est|edt|cst|cdt|mst|mdt|pst|pdt|akst|hst|gmt|utc|bst|ist|cet|cest|eet|eest|aest|aedt|acst|awst|nzst|nzdt|jst|kst|sgt";
const NAMED: &str = r"(?:eastern|central|mountain|pacific|atlantic|alaska|hawaii)(?: standard| daylight)?(?: time)?(?: ?zone)?";
const BARE: &str = "est|edt|cst|cdt|mst|mdt|pst|pdt|gmt|utc|bst|cet|cest|eet|aest|aedt|awst|nzst";
const CLOSED: &str = r"(?![\w+\-−:])";
const QUALIFIER: &str = r"(?:(usda|hardiness|growing|gardening|planting|garden|plant|climate) )?";
const NUMBER: &str = r"(?<![-–/~])(?<![-–/] )(\d{1,2})([ab])?\b(?!\s*(?:-|–|/|to|or|and)\s*\d)";
const SPOKEN: &[&str] = &["english", "german", "french", "spanish", "italian", "russian", "portuguese", "dutch", "swedish", "norwegian", "danish", "finnish", "polish", "greek", "turkish",
    "arabic", "chinese", "japanese", "korean", "vietnamese", "persian", "hungarian", "czech", "slovak", "romanian", "bulgarian", "serbian", "croatian", "ukrainian", "lithuanian", "latvian",
    "estonian", "icelandic", "thai", "indonesian"];
const ACCENTS: &[&str] = &["american", "british", "scottish", "irish", "welsh", "australian", "aussie", "kiwi", "new zealand", "canadian", "south african", "indian", "southern",
    "northern", "midwestern", "midwest", "boston", "new york", "jersey", "new jersey", "texan", "texas", "cajun", "appalachian", "country", "yorkshire", "scouse", "geordie",
    "cockney", "london", "mancunian", "manc", "brummie", "glaswegian", "west country", "northern irish", "rp", "posh", "mexican", "brazilian", "filipino", "jamaican", "caribbean",
    "nigerian", "african", "eastern european", "slavic", "quebecois", "québécois", "french canadian", "newfoundland", "minnesotan", "minnesota", "wisconsin",
    "chicago", "philly", "baltimore", "pittsburgh", "californian", "california", "east coast", "west coast", "northeastern", "new england", "maine", "kentucky", "tennessee",
    "georgia", "alabama", "louisiana", "southern us", "standard american", "general american", "transatlantic",
    "estuary", "lancashire", "liverpool", "liverpudlian", "birmingham", "welsh valleys", "dublin", "cork", "belfast", "glasgow", "edinburgh", "highland", "south london",
    "east london", "north london", "essex", "midlands", "northern english", "southern english", "upper midwest", "valley girl", "hispanic", "latino", "latina", "puerto rican", "cuban",
    "colombian", "argentinian", "argentine", "chilean", "iranian", "israeli", "lebanese", "egyptian", "pakistani", "bangladeshi", "sri lankan", "nepali", "malaysian", "singaporean",
    "belarusian", "swiss", "austrian", "belgian", "flemish", "scandinavian", "ghanaian", "kenyan", "zimbabwean", "trinidadian", "bajan", "haitian", "east asian", "asian"];

static GARDEN: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:garden|gardens|gardening|gardener|plants|planting|seeds|frost|perennials?|usda|hardiness|overwinter\w*|tomatoes|bulbs|soil|zone ?\d{1,2}[ab])\b"));
static GARDEN_SUB: LazyLock<Re> = LazyLock::new(|| Re::new(r"garden|plant|veg|tomato|lawn|hort|bonsai|permaculture|homestead|fruit|succulent|cact|rose|botany|seed|herb|landscap|pepper|chili|orchid|tree|flower|perennial|native|bulb|dahlia|hosta|iris|fig|citrus|berr|composting|arboriculture"));

fn zone_code(name: &str) -> String {
    let name: String = name.chars().filter(|c| !c.is_whitespace()).map(|c| if c == '−' { '-' } else { c }).collect();
    let long = ["eastern", "central", "mountain", "pacific", "atlantic", "alaska", "hawaii", "eastcoast", "westcoast"];
    let codes = ["est", "cst", "mst", "pst", "ast", "akst", "hst", "est", "pst"];
    match long.iter().position(|word| name.starts_with(word)) {
        Some(index) => codes[index].to_string(),
        None => name,
    }
}

fn time_zone(m: &Match) -> Option<String> {
    m.first_s().map(|name| zone_code(&name))
}

fn last_zone(m: &Match) -> Option<String> {
    m.gs(m.groups()).map(|name| zone_code(&name))
}

fn accent(m: &Match) -> Option<String> {
    m.first_s().map(|name| name.replace('-', " "))
}

fn zone(m: &Match, sure: bool) -> Option<String> {
    let index = (1..=m.groups()).find(|&g| m.nonempty(g).is_some_and(|part| part.iter().all(|c| c.is_ascii_digit())))?;
    let number: f64 = m.gs(index)?.parse().ok()?;
    let letter = m.nonempty(index + 1);
    let qualified = index > 1 && m.nonempty(index - 1).is_some_and(|part| part[0].is_ascii_lowercase());
    if !(sure || letter.is_some() || qualified || GARDEN.test(m.string)) {
        return None;
    }
    let value = number + if letter == Some(&['b'][..]) { 0.5 } else { 0.0 };
    (1.0..=13.0).contains(&value).then(|| format!("{value}"))
}

fn flair_zone(m: &Match) -> Option<String> {
    let garden = m.group(1).is_some_and(|sub| GARDEN_SUB.test(sub));
    zone(m, garden)
}

pub fn rules() -> Vec<Rule> {
    let any = format!("{OFFSET}|{LONG}|{CODES}");
    let strict = format!("{OFFSET}|{LONG}|{STRICT}");
    let accents = longest_first(ACCENTS.iter().copied()).replace(r"\ ", "[- ]");
    let spoken = longest_first(ACCENTS.iter().chain(SPOKEN).copied()).replace(r"\ ", "[- ]");
    let open = r"(?:^|[.!?\n,(]\s*)";
    let subject = r"\b(?:i'm|im|i am|i live|we're|we are|we live)(?: (?:currently|now|also|based|located|living|usually|mostly|still))*";
    let gardener = r"\b(?:i'm|im|i am|we're|we are|i live|we live|i garden|we garden|i grow|we grow)(?: (?:currently|now|also|located|based|living|gardening|growing|here|right|just|squarely|firmly|solidly))*";
    let accent_lead = r"(?: (?:a|an|this|such a|quite a|bit of an?|slight|slightly|strong|heavy|heavily|thick|light|faint|noticeable|mild|very|pretty|really|super|real|definite|natural|typical|proper|broad|soft|subtle|little|lil|bit|kind of an?|kinda|sort of an?|obvious|distinct|distinctive|recognizable|recognisable|noticeably|hint of an?|touch of an?|trace of an?|lingering|residual|lovely|nice|cute))*";
    vec![
        needs(rule("time_zone", &format!(r"\bmy (?:local |current |home )?(?:time ?zone|tz)(?: is| is in| is currently| is basically|:| =| -)?(?: (?:the|in))? ({any}){CLOSED}"), time_zone, hedge()), &["zone", "tz"]),
        rule("time_zone", &format!(r"{subject} (?:in|on) (?:the )?(?:us |u\.s\. )?({strict})(?: (?:time ?zone|tz|time))?{CLOSED}"), time_zone, hedge()),
        rule("time_zone", &format!(r"\b(?:i'm|im|i am) ({OFFSET}|{BARE}){CLOSED}"), time_zone, hedge()),
        rule("time_zone", &format!(r"{open}(?:({any}) (?:time ?zone|tz)|({strict})) here\b"), time_zone, hedge()),
        rule("time_zone", &format!(r"\Ar/[a-z0-9_]+: (?:(?:time ?zone|tz):? )?({any})[\s.]*\Z"), time_zone, TAGGED),
        needs(rule("time_zone", &format!(r"(?:^|\n)[^\S\n]*[*_#>-]*[^\S\n]*(?:my )?(?:time ?zone|tz)[*_\s]*[:=-][*_\s]*({OFFSET}|{NAMED}|{CODES}){CLOSED}"), time_zone, TAGGED), &["zone", "tz"]),
        rule("time_zone", &format!(r"(?<![\w/])(?:\d{{2}} ?/ ?[mf]|[mf] ?/ ?\d{{2}}) ?/ ?({OFFSET}|{STRICT}){CLOSED}"), time_zone, TAGGED),
        rule("time_zone", &format!(r"\A(?=[^\n]{{0,200}}?(?:{FOR}|{TAG}|\][^\n]*\[))[^\n]{{0,200}}?[\[(|]\s*({OFFSET}|{STRICT})\s*(?=[\])|])"), last_zone, TAGGED),
        rule("time_zone", &format!(r"\A(?=[^\n]{{0,200}}?(?:{FOR}|{TAG}))[^\n]{{0,200}}?#({OFFSET}|{STRICT}){CLOSED}"), last_zone, TAGGED),
        rule("time_zone", &format!(r"{TAG}[^\S\n]*[,/|-]?[^\S\n]*({OFFSET}|{STRICT}){CLOSED}"), last_zone, TAGGED),
        needs(rule("hardiness_zone", &format!(r"{gardener} in (?:a |the )?{QUALIFIER}zones? ?{NUMBER}"), |m| zone(m, false), hedge()), &["zone"]),
        needs(rule("hardiness_zone", &format!(r"\bmy {QUALIFIER}zone(?: is| is in| =|:| -)? (?:zone )?{NUMBER}"), |m| zone(m, false), hedge()), &["zone"]),
        needs(rule("hardiness_zone", &format!(r"{open}{QUALIFIER}zone ?{NUMBER}(?: (?:gardener|grower|gardening))? here\b"), |m| zone(m, false), hedge()), &["zone"]),
        needs(rule("hardiness_zone", &format!(r"\Ar/([a-z0-9_]+): (?:[^\n]*?[^\w\n])?{QUALIFIER}zones? ?{NUMBER}"), flair_zone, TAGGED), &["zone"]),
        needs(rule("hardiness_zone", &format!(r"(?:^|\n)[^\S\n]*(?:[^\n,]{{0,60}},[^\S\n]*)?{QUALIFIER}zone ?(\d{{1,2}})([ab])(?=[^\S\n]*(?:$|\n|[,.;:)(]|-\s))"), |m| zone(m, true), hedge()), &["zone"]),
        rule("hardiness_zone", &format!(r"\Ar/([a-z0-9_]+): (?:[^\n]*?[^\w\n])?()(?<![-–/~])(?<![-–/] )(\d{{1,2}})([ab])\b(?!\s*(?:-|–|/|to|or|and)\s*\d|\w)"), |m| m.group(1).is_some_and(|sub| GARDEN_SUB.test(sub)).then(|| zone(m, true)).flatten(), TAGGED),
        needs(rule("accent", &format!(r"\bi (?:have|got|speak with|talk with|still have|definitely have|apparently have|do have|have got|'ve got|ve got|kinda have|kind of have|naturally have){accent_lead} ({spoken}) accent\b"), accent, hedge()), &["accent"]),
        needs(rule("accent", &format!(r"\bmy (?:(?:slight|strong|heavy|thick|light|faint|noticeable|mild|natural|native|own|broad|soft|subtle|real|normal|regular|everyday|thick|obvious|lingering|residual)\s+)*({accents}) accent\b(?! (?:impression|impersonation|voice|is fake|is terrible))"), accent, hedge()), &["accent"]),
    ]
}
