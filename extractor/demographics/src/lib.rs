mod looks;
mod rules;
mod tags;
mod traits;

use claimcore::*;
use std::collections::HashSet;
use std::sync::LazyLock;

pub use rules::rules;
pub use tags::tags;

pub const IM: &str = r"i(?<!\wi)(?:'m|m| am|am| m|'am|'?ve been|'ve always been)";
pub const UNITS: &str = r"(?:years? ago|yrs? ago|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|times|percent|%|lbs?|kgs?|pounds|miles|km|cm|dollars|bucks|k\b|grand|hp|mph|degrees|feet|ft|inches|in\b(?!\s+(?!(?:a|an|the|few|couple|two|three|four|five|six|weeks?|months?|years?|days?|hours?|minutes?|length|girth|long|thick|wide|tall|cut|uncut|soft|hard|erect)\b)[a-z]{3,})|seconds|secs?|euros?|points|pts|ounces|oz|inch)";
pub static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:my|his|her|their|our|your|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|fianc\w*|spouse|ex|friend|son|daughter|brother|sister|mom|dad|mother|",
    r"father|dom|sub|guy|girl|man|woman|someone|somebody|with|e\.g|eg|example|like|for|to|and|older|younger|current|new|another|this|that|the)\W*$"
)));
pub static SELF: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:\b(?:i|me|myself|i'm|im|i am|ich|moi|yo|as|bin)(?:\s+an?)?|^)\W*$"));

const BASE_GENDERS: &[(&str, &str)] = &[
    ("guy", "man"), ("man", "man"), ("dude", "man"), ("male", "man"), ("boy", "man"), ("bloke", "man"), ("lad", "man"), ("gentleman", "man"), ("dad", "man"), ("father", "man"),
    ("husband", "man"), ("hubby", "man"), ("mum", "woman"), ("mom", "woman"), ("mother", "woman"), ("wife", "woman"), ("woman", "woman"), ("women", "woman"), ("girl", "woman"), ("female", "woman"),
    ("lady", "woman"), ("gal", "woman"), ("chick", "woman"), ("girlie", "woman"), ("dilf", "man"), ("m", "man"), ("f", "woman"), ("nb", "nonbinary"), ("non-binary", "nonbinary"),
    ("nonbinary", "nonbinary"), ("enby", "nonbinary"), ("genderfluid", "genderfluid"), ("agender", "agender"), ("genderqueer", "genderqueer"),
    ("trans woman", "trans woman"), ("transwoman", "trans woman"), ("trans girl", "trans woman"), ("transgirl", "trans woman"), ("tgirl", "trans woman"), ("ts girl", "trans woman"), ("mtf", "trans woman"),
    ("trans man", "trans man"), ("transman", "trans man"), ("trans guy", "trans man"), ("ftm", "trans man"),
];
const KINSHIP: &[(&str, &str)] = &[
    ("son", "man"), ("brother", "man"), ("uncle", "man"), ("nephew", "man"), ("grandpa", "man"), ("grandfather", "man"), ("granddad", "man"), ("grandad", "man"), ("stepdad", "man"), ("widower", "man"),
    ("boyfriend", "man"), ("daughter", "woman"), ("sister", "woman"), ("aunt", "woman"), ("niece", "woman"), ("grandma", "woman"), ("grandmother", "woman"), ("granny", "woman"),
    ("stepmom", "woman"), ("widow", "woman"), ("girlfriend", "woman"), ("housewife", "woman"), ("mommy", "woman"), ("bro", "man"), ("twink", "man"), ("femboy", "man"),
    ("daddy", "man"), ("milf", "woman"), ("hotwife", "woman"), ("sahm", "woman"), ("sahd", "man"),
];
const PLURALS: &[(&str, &str)] = &[
    ("men", "man"), ("guys", "man"), ("dudes", "man"), ("males", "man"), ("dads", "man"), ("fathers", "man"), ("husbands", "man"),
    ("women", "woman"), ("girls", "woman"), ("ladies", "woman"), ("females", "woman"), ("moms", "woman"), ("mothers", "woman"), ("wives", "woman"),
];
const ROLES: &[(&str, &str)] = &[
    ("bwc", "man"), ("bbc", "man"), ("bull", "man"), ("stud", "man"), ("boi", "man"), ("jock", "man"), ("bear", "man"), ("cub", "man"), ("king", "man"),
    ("cougar", "woman"), ("gilf", "woman"), ("domme", "woman"), ("queen", "woman"), ("bbw", "woman"), ("sis", "woman"),
];
pub static GENDERS: LazyLock<Table> = LazyLock::new(|| [BASE_GENDERS, KINSHIP, PLURALS, ROLES].iter().flat_map(|t| t.iter()).map(|(k, v)| (k.to_string(), *v)).collect());
pub static GENDER_WORDS: LazyLock<String> = LazyLock::new(|| {
    let kin = KINSHIP.iter().map(|(k, _)| *k).collect::<Vec<_>>().join("|");
    format!(r"(?<!\btrans )(?<!\btrans-)(?<!\btransgender )(?<!\bcis )(?<!\bcis-)(?<!\bcisgender )(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|(?<=\ba )women|girl|female|lady|gal|chick|bull|stud|boi|cougar|gilf|domme|{kin})")
});
pub const ADJECTIVES: &str = concat!(
    r"(?:(?:\d{2}[- ]?(?:years?|yrs?|y/?o)(?:[- ]old)?|single|married|straight|gay|bi|bisexual|white|black|asian|latino|latina|hispanic|indian|young|old|older|middle[- ]aged|",
    r"tall|short|fat|chubby|skinny|fit|average|normal|regular|grown|divorced|disabled|autistic|working|stay[- ]at[- ]home|new|first[- ]time|",
    r"american|british|canadian|australian|christian|muslim|jewish|catholic|retired|lonely|horny|shy|curvy|petite|busy|proud) ){0,3}"
);
pub static ORIENTATIONS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("gay", "gay"), ("lesbian", "lesbian"), ("bisexual", "bisexual"), ("bi", "bisexual"), ("pansexual", "pansexual"), ("pan", "pansexual"), ("asexual", "asexual"), ("ace", "asexual"),
    ("queer", "queer"), ("straight", "straight"), ("heterosexual", "straight"), ("hetero", "straight"), ("homosexual", "gay"), ("aroace", "asexual"), ("aro-ace", "asexual"), ("str8", "straight"),
    ("heteroflexible", "heteroflexible"), ("hetero-flexible", "heteroflexible"), ("aegosexual", "aegosexual"), ("androsexual", "androsexual"), ("cishet", "straight"),
]));
const BASE_ETHNICITIES: &[(&str, &str)] = &[
    ("white", "white"), ("caucasian", "white"), ("black", "black"), ("african american", "black"), ("asian", "asian"), ("east asian", "east asian"), ("southeast asian", "southeast asian"),
    ("south east asian", "southeast asian"), ("south asian", "south asian / desi"), ("desi", "south asian / desi"), ("latino", "latino / latina"), ("latina", "latino / latina"),
    ("latinx", "latino / latina"), ("chicano", "latino / latina"), ("chicana", "latino / latina"), ("hispanic", "hispanic"), ("arab", "arab / middle eastern"),
    ("middle eastern", "arab / middle eastern"), ("persian", "persian / iranian"), ("iranian", "persian / iranian"), ("native american", "indigenous"), ("indigenous", "indigenous"),
    ("aboriginal", "indigenous"), ("first nations", "indigenous"), ("mestizo", "mestizo / mestiza"), ("mestiza", "mestizo / mestiza"), ("pacific islander", "pacific islander"),
    ("samoan", "pacific islander"), ("polynesian", "pacific islander"), ("tongan", "pacific islander"), ("north african", "north african"), ("amazigh", "north african"),
    ("ashkenazi", "jewish (ethnic)"), ("sephardic", "jewish (ethnic)"), ("mizrahi", "jewish (ethnic)"),
    ("mixed", "mixed"), ("mixed race", "mixed"), ("biracial", "mixed"), ("bi-racial", "mixed"), ("multiracial", "mixed"), ("multi-racial", "mixed"), ("multiethnic", "mixed"), ("multi-ethnic", "mixed"), ("mixed-race", "mixed"),
];
pub static ETHNIC_KEYS: LazyLock<Vec<&'static str>> = LazyLock::new(|| BASE_ETHNICITIES.iter().map(|(k, _)| *k).collect());
pub static ETHNICITIES: LazyLock<Table> = LazyLock::new(|| table(BASE_ETHNICITIES));
const REGION_BEFORE: &str = r"(?<!\beast )(?<!\beast-)(?<!\bsouth )(?<!\bsouth-)(?<!\bsoutheast )(?<!\bnorth )";
pub static ETHNIC_JOINED: LazyLock<String> = LazyLock::new(|| format!("{REGION_BEFORE}(?:{})", alternation(ETHNIC_KEYS.iter().copied())));
pub static ETHNIC_NAMES: LazyLock<String> = LazyLock::new(|| format!("{REGION_BEFORE}(?:{})", escaped_longest(ETHNIC_KEYS.iter().copied())));
const BODIES_LIST: &[(&str, &str)] = &[
    ("skinny", "slim / skinny"), ("very thin", "slim / skinny"), ("underweight", "slim / skinny"), ("thin", "slim / skinny"), ("slim", "slim / skinny"), ("slender", "slim / skinny"), ("lean", "slim / skinny"), ("athletic", "fit / athletic"),
    ("muscular", "muscular"), ("fit", "fit / athletic"), ("buff", "muscular"), ("jacked", "muscular"), ("toned", "fit / athletic"),
    ("average", "average"), ("average build", "average"), ("curvy", "curvy"), ("thick", "thick"), ("chubby", "chubby"), ("overweight", "overweight"),
    ("fat", "fat"), ("heavy", "big / heavyset"), ("heavyset", "big / heavyset"), ("heavy-set", "big / heavyset"), ("bbw", "bbw"), ("plus size", "plus size"), ("plus-size", "plus size"),
    ("obese", "obese"), ("morbidly obese", "obese"), ("petite", "petite"), ("slim thick", "slim thick"), ("slim-thick", "slim thick"), ("slim thicc", "slim thick"), ("slimthick", "slim thick"),
];
pub static BODIES: LazyLock<Table> = LazyLock::new(|| table(BODIES_LIST));
const SHAPES_LIST: &[(&str, &str)] = &[
    ("muscled", "muscular"), ("shredded", "muscular"), ("thicc", "thick"), ("chub", "chubby"), ("chunky", "chubby"), ("dadbod", "dad bod"), ("dad bod", "dad bod"), ("dad-bod", "dad bod"), ("beefy", "muscular"), ("stocky", "stocky"),
    ("hourglass", "curvy"), ("rellenita", "chubby"), ("gordita", "chubby"), ("flaca", "slim / skinny"), ("tiny", "petite"), ("ripped", "muscular"), ("toned", "fit / athletic"), ("jock", "fit / athletic"), ("ssbbw", "bbw"),
];
pub static SHAPES: LazyLock<Table> = LazyLock::new(|| table(SHAPES_LIST));
pub static BODY_ALL: LazyLock<String> = LazyLock::new(|| longest_first(BODIES_LIST.iter().chain(SHAPES_LIST.iter()).map(|(k, _)| *k)));
pub static BODY_WORDS: LazyLock<String> = LazyLock::new(|| {
    escaped_longest(BODIES_LIST.iter().chain(SHAPES_LIST.iter()).map(|(k, _)| *k).filter(|k| !["average", "heavy", "tiny", "thick", "very thin"].contains(k)))
});
pub static HAIRS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("blonde", "blonde"), ("blond", "blonde"), ("brown", "brown / brunette"), ("brunette", "brown / brunette"), ("black", "black"), ("red", "red / ginger"), ("ginger", "red / ginger"), ("auburn", "auburn"), ("a redhead", "red / ginger"),
    ("redhead", "red / ginger"), ("a ginger", "red / ginger"), ("grey", "grey / greying"), ("gray", "grey / greying"), ("greying", "grey / greying"), ("graying", "grey / greying"),
    ("white", "white"), ("silver", "grey / greying"), ("pink", "pink"), ("purple", "purple"), ("strawberry blonde", "strawberry blonde"), ("strawberry blond", "strawberry blonde"),
    ("blue", "blue"), ("teal", "teal"), ("turquoise", "teal"), ("salt and pepper", "salt and pepper"), ("salt n' pepper", "salt and pepper"), ("a blonde", "blonde"),
]));
pub const FREE: &str = r#"(?:(?!(?:not|never|no|with|for|to|than|like|and|or|that|who|this|the|my|his|her|your|their|our|a|an|in|on|at|from|about|by|into|fan|friend|friends)\b)[\w'"”-]+ )"#;
pub static COLORS: LazyLock<Table> = LazyLock::new(|| table(&[("ebony", "black"), ("wasian", "mixed"), ("blk", "black")]));
pub static OTHER_ETHNIC: LazyLock<String> = LazyLock::new(|| {
    format!("{REGION_BEFORE}(?:{})", escaped_longest(ETHNIC_KEYS.iter().copied().chain(["ebony", "wasian", "blk"]).filter(|w| !["white", "black", "mixed"].contains(w))))
});
pub const PERSON: &str = r"(?:m|f|male|female|guy|girl|man|woman|dude|bro|boy|top|bottom|bull|daddy|dad|mom|milf|wife|hubby|couple|here|stud|twink|bear|femboy|sub|dom|\d{2})\b";
pub static STATURE: LazyLock<Re> = LazyLock::new(|| Re::new(r#"([4-7])(?<![\w.$'][4-7])(?:\s?(?:'|ft|foot|feet)\s?(\d{1,2})?|["”](?=\d)(\d{1,2}))\s?(?:"|”|''|in\b|inches)?(?![\d'"”])"#));
pub static GIRTH: LazyLock<Re> = LazyLock::new(|| Re::new(r#"(?:hung|cock|dick|bbc|bwc|length|inch\w*|uncut|cut|shaved|girthy|veiny|long|(?<!')(?<!'\d)\d\s?["”+]+)\W*(?:\w+\W+)?$"#));
pub static PARTY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:my|his|her|their|our|your|you|you're|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|for|with|like|seeking|looking|want|wants|someone|be)\W+(?:\w+\W+)?$"));
pub static HAIRED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w-])(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bperfect )(?:(blonde?|brunette|redhead|ginger|bald|shaved head)|(?:(?:long|short|thick|thin|curly|straight|wavy|natural|naturally|graying|greying|dark|light|shorter|longer|messy|medium|shaggy|buzzed|shoulder[- ]length)\s+)*(brown|black|red|auburn|grey|gray|white|silver|pink|blue|purple|green|teal|turquoise|lavender|salt and pepper|salt n' pepper)(?:ish)?\s+(?:(?:curly|wavy|straight|long|short|thick)\s+)?hairs?\b)(?![\w-])"));
pub static ORIENTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:(?<![\w-])|(?<=\s-))(?<!\bbe )(?<!\bfor )(?<!\bsome )(?<!\bwith )(?<!\binto )(?<!\bother )(?<!\bhosting )(?<!\bfrom )(bi|bisexual|straight|str8|gay|lesbian|pansexual|hetero)(?![\w-])(?! (?:men|women|guys|girls|porn|couples?|friendly|friends?|people|community|rights|marriage|bars?|clubs?|curious|or|and (?:\w+ )?(?:men|women|guys|girls|gay|straight|bi|bisexual|lesbian|trans|queer|people|couples?)|to|up|talk|ahead|away|forward|out|ones)\b)"));
pub static CURIOUS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:bi|bisexual|bicurious|bi-curious|curious|straight|str8|dl|down low|married|taken|wife|girlfriend|gf|hetero)\b"));
pub static METRIC: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w.,])(?:(1[4-9]\d|2[01]\d)\s?cm\b|1[.,]([4-9]\d)\s?c?m\b|1m([4-9]\d)\b)"));
pub static SHAPED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w-])(slim|slender|skinny|athletic|muscular|chubby|chub|chunky|curvy|bbw|stocky|beefy|toned|dadbod|dad[- ]bod|plus[- ]size|obese|overweight|jock|(?<!slim )(?<!skinny )fit(?=\s*(?:[,.!/|)]|$)))(?![\w-])"));
pub static PHALLIC: LazyLock<Re> = LazyLock::new(|| Re::new(r" (?:\w+ )?(?:cock|dick|penis|bwc|bbc|shaft|uncut|load|meat|wood|ropes|creamy|cumming|girth)\b"));
pub static STURDY: LazyLock<HashSet<&'static str>> = LazyLock::new(|| ["athletic", "fit", "muscular", "muscled", "shredded", "jacked", "buff", "toned", "ripped", "stocky", "overweight", "obese", "dadbod", "dad bod", "bbw", "jock"].into_iter().collect());
pub const MONTHS: &str = "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december";
pub static DIGIT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d"));
pub static PAIR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d\d"));
pub static COUNTED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{MONTHS}|level|lvl|day|number|no|chapter|episode|season|page|version|room|unit|size|model|wife|husband|gf|bf|girlfriend|boyfriend|son|daughter|mom|dad)\W*$")));
pub static GAME: LazyLock<Re> = LazyLock::new(|| Re::new(r"\n[^\S\n]*\^\([^\n]*\)[^\S\n]*$"));
pub static AD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:[mf]4[mfat]\w*|dms?|snap|sc|kik|tele|telegram|hmu|horny|sext|sexting|bwc|bbc|cock|dick|pussy|fwb|nsa|hookup|host|hosting|discreet|bator|goon|gooner|trade|nudes|bi|gay|str8|daddy|milf|sissy|femboy|twink|bull|cuck|hotwife|bbw|onlyfans|kinky|naughty)\b"));
pub static YEARS_OLD: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w$])\d{2}\s?(?:yo|y/o)\b"));
pub static THIRD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:she|he|her|his|they|their|him|them)\b|\b(?:my|our|your) (?:\w+ )?(?:wife|husband|hubby|gf|bf|girlfriend|boyfriend|partner|son|daughter|kid|baby|mom|mother|dad|father|brother|sister|friend|dog|cat|puppy)\b"));
pub static WANTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:you|your|be|in|for|not|no|if|want|wants|like|love|seeking|looking|lover|into)\W+(?:\w+\W+)?$"));
pub static FOREIGN: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:looking for|seeking|want|wants|you|your|under|over|than|at least|taller|shorter|between|she|he|her|his|wife|husband|gf|bf)\b"));
pub static CLOSING: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\(\[](\d{2})[\)\]][^\w\n]*(?:\n|$)"));
pub static START: LazyLock<Re> = LazyLock::new(|| Re::new(r"^\W{0,3}(\d{2})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)"));
pub const BODY_NOUNS: &str = r"(?:build|built|body|bod|frame|figure|shape|girl|guy|woman|man|boy|boi|bro|bull|stud|jock|twink|femboy|sub|dom|cub|otter|bottom|top|vers|bear|daddy|milf|hotwife|wife|husband|hubby|mom|mum|dad|grandpa|grandma|lady|gal|chick|dude|male|female|married|single|f|m|here|latina|latino|black|white|asian|blonde|brunette|boyfriend|girlfriend|bf|gf|breeder|slut|sissy|cuck|queen|king|baddie|babe|teen|mommy)\b";
pub const CROWD: &str = r"(?:guys|girls|women|men|ladies|tops|bottoms|bulls|bros|dudes|couples|people|queens|wives|moms|milfs|daddies|bears|twinks|chicks|females|males|chasers)\b";
pub const DESIRED_PATTERN: &str = r"n't\b|\bain'?t\b|\b(?<!-)(?:looking|look for|seeking|thing for|searching for|prefer\w*|pref|into|love|loves|like|likes|interested in|any|bonus|must|not|isn't|no|if|you|your|you're|ur)\b";
pub static DESIRED: LazyLock<Re> = LazyLock::new(|| Re::new(DESIRED_PATTERN));
pub static DESCRIBED: LazyLock<Re> = LazyLock::new(|| Re::new(&(r"(?:^|[\s,.!/(|+-])(?<!slim )(?<!skinny )(?<!body )(?<!% )(?<!\dg )(thin|lean|fit|muscled|shredded|jacked|buff|fat|tiny|average|ripped|hourglass|rellenita|gordita|flaca)".to_string()
    + &format!(r"(?! (?:\w+ ){{0,2}}{CROWD})(?= (?:\w+ ){{0,2}}?{BODY_NOUNS}| (?:and |but |with |w/ |af\b|asf\b|\d)|[\s,.!/)|]*$|\s*[,/|.!&+])"))));
pub static WANTING: LazyLock<Re> = LazyLock::new(|| Re::new(&(r"\b(?:want|wants|wish|wished|need|needs)\b|".to_string() + DESIRED_PATTERN)));
pub static ETHNIC: LazyLock<Re> = LazyLock::new(|| {
    let other = &*OTHER_ETHNIC;
    Re::new(&format!(r"(?<![\w-])(?:(white|black|mixed)(?=\s*(?:[,.!/|)&+]|$|\d)|[^\S\n]*\n|(?<!mixed) (?:with|w/|w) | (?:\w+ ){{0,2}}?{BODY_NOUNS}|\s*{PERSON})|({other}))(?![\w-])(?! (?:\w+ ){{0,2}}{CROWD})"))
});

pub static POSTERS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("m", "man"), ("f", "woman"), ("w", "woman"), ("fb", "woman"), ("fu", "woman"), ("futa", "woman"), ("tf", "trans woman"), ("tm", "trans man"),
    ("nb", "nonbinary"), ("wm", "man"), ("mwm", "man"), ("swm", "man"), ("dwm", "man"), ("bm", "man"), ("wf", "woman"),
]));
pub static LOOKING: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![a-z0-9])(?:[\[\(]?(\d{2})(?:\s*/\s*\d{2})?[\]\)]?\s*)?[\[\(]?\s*(nb|mtf|ftm|tf|tm|futa|fb|fu|[mf])((?:[mf]|/\w+)*)\s*4\s*((?:[mfatr]|me|nb|[a-z](?=[a-z/]*\s*[\]\)]))[a-z/]*)\s*[\]\)]?(?:\s*[-–|:#]?\s*[\[\(]?(\d{2})(?!\d))?"));
pub static AGED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?=[\dmfwsdbtn])(?<![\w$£€#'/:+-])(?<![\w,]\.)(?<!\d,)(?:(\d{2})(?:\s?[/\\|-]?|,)\s?((?:[smd]?w|b)m|wf|mtf|ftm|tf|tm|fb|nb|[mf])(?:(?<=m)f(?![\w'])|(?<=f)m(?![\w']))?|((?:[smd]?w|b)m|tf|tm|fb|nb|[mfw])\s?[/'.,-]?\s?(\d{2})(?:[mfa](?![\w'])|(?<=m\d\d)f\d{2}(?![\w'])|(?<=f\d\d)m\d{2}(?![\w']))?)(?!(?!_)[\w'%]|[-/]\d|-[a-z]\d)"));
pub static SENTENCE: LazyLock<Re> = LazyLock::new(|| Re::new(r"[.!?\n]"));
pub static INTENSE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:very|so|too|really|super|extremely|quite|v)\s+$"));
pub static ATTACHED: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\w\n]*(?:(?!(?:for|any|need|needs|want|wants|seeking|looking|into|like|likes|love|loves)\b)[a-z]+ )??(fit|thick|thicc|chub|chubby|chunky|curvy|slim|skinny|slender|athletic|muscular|toned|stocky|petite|bbw|lean)\b(?!['-])(?! \d| (?:\w+ ){0,2}(?:cock|dick|penis|bwc|bbc|shaft|meat|load|uncut|inch\w*)\b)"));
pub static COLORED_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\w\n]*(?:(?!(?:for|any|need|needs|want|wants|seeking|looking|into|like|likes|love|loves|and|or|with)\b)[a-z]+ )?(white|black|blk|mixed)\b(?!['-])"));
pub static ORIENTED_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"[^\w\n]*(?:(?!(?:for|any|need|needs|want|wants|seeking|looking|into|like|likes|love|loves|and|or|with|not|no)\b)[a-z]+ )?(straight|str8|bi|bisexual|gay|pansexual)\b(?!['-]| to\b)(?! (?:\w+ ){{0,2}}{CROWD})")));
pub static FIRST: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|me|my|myself|mine)\b"));
pub const LETTERED: &str = r"(?<![\w$£€#'/:+-])(?:\d{2}\s?[mf]|[mf]\s?\d{2})(?![\w'%])";
pub static WEIGHED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"(?<![\w.])\d{{2,3}}\s?(?:kg|kgs|kilos?|lbs?|pounds)\b|{LETTERED}")));
pub static MEASURED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"(?<![\w.$'])[4-7]\s?(?:'|ft|foot|feet)|(?<![\w.])(?:1[4-9]\d|2[01]\d)\s?cm\b|{LETTERED}|\bweight\s*[:=-]")));
pub static SPEAKER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i am|me|my name is)\b"));
pub static WORDED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"(?=[\dmf])(?<![\w$#.,'/:+-])(?:(\d{{2}})\s?(?:yo|y/o|yrs?|years?(?: old)?)?(?:\s*/\s*|[\s,]*){ADJECTIVES}\(?(male|female)\)?|(male|female)(?:\s*/\s*|[\s,]*)(\d{{2}}))(?![\w'%])")));
pub static BRACKETED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?=[\d(\[mf])(?<![\w$#.,'/:+-])(?:(\d{2})\s?[\(\[]\s*([mf])\s*[\)\]]|[\(\[](\d{2})[\)\]]\s?(m|f|male|female)\b|([mf])\s?[\(\[](\d{2})[\)\]]|[\(\[]([mf])[\)\]]\s?(\d{2})\b)"));
pub static ANATOMY: LazyLock<Table> = LazyLock::new(|| table(&[
    ("cock", "man"), ("dick", "man"), ("penis", "man"), ("balls", "man"), ("foreskin", "man"), ("bwc", "man"), ("bbc", "man"), ("pussy", "woman"), ("vagina", "woman"), ("clit", "woman"), ("tits", "woman"), ("boobs", "woman"), ("breasts", "woman"), ("pregnant", "woman"),
]));
pub static HUNG: LazyLock<Re> = LazyLock::new(|| Re::new(r"(b[wb]c)(?<![\w-]b[wb]c)(?![\w-])"));
pub static COMPARED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:is|was|are|were|be|being|than|of|to|from|between|claims|claimed|like|avg|average|mine's|mines|u|ur|you|your|you're|she|he|her|his|they|their|wife|husband|gf|bf|under|over|at least|taller|shorter|e\.g)\b"));
pub static QUEER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:bi|bisexual|bicurious|bi-curious|curious|gay|lesbian|pan|pansexual|queer|homo|trans|tgirl|ts|cd|crossdresser|sissy|femboy|twink|m4m|f4f|mm|ff|mmf|ffm|couple|couples|rp|roleplay|role-play|role play|session|story|plot|character|characters|fantasy|scenario|kik|discord)\b"));
pub static OPPOSITE_M: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:woman|women|girl|girls|female|females|lady|ladies|wife|gf|girlfriend|milf|milfs|mom|moms|pussy|boobs|tits|her|she)\b"));
pub static OPPOSITE_F: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:man|men|guy|guys|male|males|husband|bf|boyfriend|daddy|cock|dick|him|he)\b"));
pub static SIZED: LazyLock<Re> = LazyLock::new(|| Re::with(r"(?<![\w.$'])[4-7]\s?(?:'|ft)\s?\d{1,2}\b.{0,30}?\b\d{2,3}\s?(?:lbs?|kg|pounds)\b", claimcore::re::S));
pub static GREETED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|[.!?\n,;:(] *|\b(?:hey|hi|hello|yo|sup)\W+(?:\w+\W+)?)$"));
pub static NOWADAYS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i was|i started at|started at|i got \w+ at|when i was|since i was) (?:about |around )?(?:\d{1,2}|[a-z]+)\b[^.!?\n]{0,40}?,? (?:and |but |i'm |im |i am )*$"));
pub static NAMED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i'm|im|i am|my name is|my name's) [a-z]+$"));
pub static COLORED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:white|black|asian|latino|latina|hispanic|indian|arab|mixed)[,\s]+(\d{2})\b(?![\d%.,]\d|\s*(?:min|mins|minutes|hours|days|years|yrs|percent|k|m|lbs|kg|inch|inches|cm)\b)"));
pub static OPENING: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|\n)\W*(?:(\d{2})\s?(?:yo|y/o|yrs?|years? old)?[\s,]+(?:[a-z]+\s){0,2}?(m|f|male|female|guy|girl|man|woman|dude|bro|wife|mom|milf|hotwife|dad|daddy|bwc|bbc|bull|twink|femboy|stud)\b(?!')|(?:a\s)?(?:[a-z]+\s)?(wife|milf|hotwife|mom|mum|mommy|daddy|dad|bro|guy|girl|woman|man|lady)(?:\s+of\s+\d|[\s,]*(\d{2}))\b(?=[\s,.!]|$))"));
pub static WORDY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\w"));
pub static LOAD: LazyLock<Re> = LazyLock::new(|| Re::new(r#"(?:\b(?:under|over|than|lose|losing|lost|gain|gained|gaining|by|of|an?|the|another|extra|to|from|bench|squat|lift|lifting|carry|carrying)\s*|(?<!['’"”])(?<!['’"”]\d)(?<![a-z]\d)[-–/\d]\s*)\W?$"#));
pub const BOUNDARY: &str = r"\b(?:because|cause|cuz|coz|cos|bc|since|and|but|so|although|though|as)\b";
pub static ASKED: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^.!?\n,;]{0,40}\?"));
pub static LIMIT: LazyLock<Re> = LazyLock::new(|| Re::with(&format!(r"(?:{})(?!.*{BOUNDARY})", HEDGE.pattern), claimcore::re::S));
pub static SELF_LIMIT: LazyLock<Re> = LazyLock::new(|| Re::with(&format!(r"(?:{})(?!.*{BOUNDARY})", SELF_HEDGE.pattern), claimcore::re::S));

pub fn escaped_longest<'a>(words: impl IntoIterator<Item = &'a str>) -> String {
    let mut escaped: Vec<String> = words.into_iter().map(escape).collect();
    escaped.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    escaped.dedup();
    escaped.join("|")
}

pub fn tail_sentence(s: &[char], start: usize, width: usize) -> &[char] {
    let window = &s[start.saturating_sub(width)..start];
    &window[last_mark(window, window.len(), ".!?\n")..]
}

pub fn owned(lowered: &[char], start: usize) -> bool {
    let before = tail_sentence(lowered, start, 24);
    SELF.test(before) || (start < 60 && !OTHERS.test(before)) || !WORDY.test(before)
}

pub fn bodied(text: &[char], start: usize, word: &[char]) -> Option<String> {
    if (eq(word, "skinny") || eq(word, "thin")) && INTENSE.test_in(text, start.saturating_sub(12), start) {
        return Some("slim / skinny".to_string());
    }
    let key = st(word);
    BODIES.get(&key).or_else(|| SHAPES.get(&key)).map(|v| v.to_string())
}

pub fn desired(lowered: &[char], start: usize) -> bool {
    WANTING.test(tail_sentence(lowered, start, 80))
}

pub fn desired_by(lowered: &[char], start: usize, pattern: &Re) -> bool {
    pattern.test(tail_sentence(lowered, start, 80))
}

pub fn unclaimed(lowered: &[char], start: usize) -> bool {
    let prefix = &lowered[last_mark(lowered, start, ".!?\n")..start];
    match WANTING.iter(prefix).last() {
        Some(wanted) => !FIRST.test_in(prefix, wanted.end(), prefix.len()),
        None => false,
    }
}

pub fn sentence(text: &[char], start: usize, end: usize) -> &[char] {
    &text[last_mark(text, start, ".!?\n")..next_mark(text, end, ".!?\n")]
}

pub fn line(text: &[char], start: usize) -> &[char] {
    &text[line_start(text, start)..line_end(text, start)]
}

pub fn ages(value: Option<&[char]>) -> Option<String> {
    let value = value?;
    if value.is_empty() || !isascii(value) {
        return None;
    }
    let number = py_int(value)?;
    if (13..=90).contains(&number) {
        Some(st(value))
    } else {
        None
    }
}

pub fn either<'a>(m: &Match<'a>, groups: &[usize]) -> Option<&'a [char]> {
    for &g in groups {
        if let Some(v) = m.nonempty(g) {
            return Some(v);
        }
    }
    m.group(*groups.last().unwrap())
}

pub fn get(t: &Table, key: Option<&[char]>) -> Option<String> {
    lookup(t, key)
}

pub fn init() {
    timed("demographics init", || {
        LazyLock::force(&rules::RULES);
        for re in [&OTHERS, &SELF, &STATURE, &GIRTH, &PARTY, &HAIRED, &ORIENTED, &CURIOUS, &METRIC, &SHAPED, &PHALLIC, &DIGIT, &PAIR, &COUNTED, &GAME, &AD, &YEARS_OLD, &THIRD, &WANTED, &FOREIGN, &CLOSING, &START,
            &DESIRED, &DESCRIBED, &WANTING, &ETHNIC, &LOOKING, &AGED, &SENTENCE, &INTENSE, &ATTACHED, &COLORED_AFTER, &ORIENTED_AFTER, &FIRST, &WEIGHED, &MEASURED, &SPEAKER, &WORDED, &BRACKETED,
            &HUNG, &COMPARED, &QUEER, &OPPOSITE_M, &OPPOSITE_F, &SIZED, &GREETED, &NOWADAYS, &NAMED, &COLORED, &OPENING, &WORDY, &LOAD, &ASKED, &LIMIT, &SELF_LIMIT] {
            LazyLock::force(re);
        }
        tags::force();
        traits::force();
        looks::force();
        rules::force();
        LazyLock::force(&STURDY);
    });
}
