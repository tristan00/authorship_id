mod generation;
mod identity;
mod rules;
mod tags;

use claimcore::*;
use std::sync::LazyLock;

pub use rules::rules;
pub use tags::tags;

const IDENTITIES: [&str; 9] = ["man", "woman", "nonbinary", "genderfluid", "agender", "genderqueer", "bigender", "demiboy / demigirl", "xenogender"];
const SPLIT: [(&str, Option<&str>, Option<&str>); 15] = [
    ("cis woman", Some("woman"), Some("cis")),
    ("cis man", Some("man"), Some("cis")),
    ("cis", None, Some("cis")),
    ("cis (gender unstated)", None, Some("cis")),
    ("trans woman", Some("woman"), Some("trans")),
    ("trans man", Some("man"), Some("trans")),
    ("trans", None, Some("trans")),
    ("trans (unspecified)", None, Some("trans")),
    ("transsexual", None, Some("trans")),
    ("transfem", None, Some("trans")),
    ("transmasc", None, Some("trans")),
    ("questioning", None, Some("questioning")),
    ("egg", None, Some("questioning")),
    ("demiboy", Some("demiboy / demigirl"), None),
    ("demigirl", Some("demiboy / demigirl"), None),
];

static FTM: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![a-z0-9])ftm(?![a-z0-9])"));
static MOTHERING: LazyLock<Re> = LazyLock::new(|| {
    Re::new(concat!(
        r"(?<![a-z0-9])(?:pregnan[a-z]*|baby|babies|bumps?|bumpers?|stm|miscarriages?|due(?! to)|toddlers?|daycare|nursing|breast ?pump[a-z]*|exclusively pumping|maternity|breastmilk|milk supply|c-sec|epidural|(?:our|your|the|their|his|her) lo|sleep train[a-z]*|contact nap[a-z]*|first[- ]time (?:mom|mum|mother|mama|parent)s?|ftm to (?:a|an|my)|newborn|postpartum|pp|ppa|ppd|ttc|ivf|iui|nicu|preemie|placenta|trimester|edd|due date|breastfe[a-z]*|ebf|formula|c ?-?section|moms?|mommies|mum|mums|mama|my (?:son|daughter|ds|dd|lo|little one))(?![a-z0-9])",
        r"|(?<![a-z0-9])\d{1,2} ?(?:w|wks?|weeks?)(?: pregnant| along)?(?:\+?\d)?(?![a-z0-9])|(?<![a-z0-9])\d{1,2}(?:\.\d)? ?(?:months?|mos?|weeks?|wks?|wo) old(?![a-z0-9])"
    ))
});
static MOTHER_DATES: LazyLock<Re> = LazyLock::new(|| {
    Re::new(r"(?<![0-9])\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?(?![0-9])|(?<![a-z])(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? (?:\d{1,2}|20\d\d|['‘’]\d\d)(?![0-9])|(?<![0-9])20[0-3]\d(?![0-9])")
});
static TRANS_CUES: LazyLock<Re> = LazyLock::new(|| {
    Re::new(concat!(
        r"(?<![a-z0-9])(?:trans(?:gender[a-z]*|g[eê]n[eé]ro|genre|sexual[a-z]*|sexuel(?:le)?|sexuell|sex|exual(?:es)?|essuale|m[ae]n|mann|mand|male|masc[a-z]*|fem[a-z]*|female|frau|guys?|boys?|girls?|wom[ae]n|kvinn[ae]|person|persoon|people|bians?|ness|phob[a-z]*|med[a-z]*|misogyn[a-z]*|identit[ée]|z|erke[a-zğ]*)?s?|he/[a-z]+|they/[a-z]+|testosterone|hrt|t ?shots?|top surgery|binder|dysphoria|pre-?t|post-?t|on t|[mft]{1,3}4[mfat]{1,3}|cis|afab|amab|gender affirm[a-z]*",
        r"|born (?:a |as a )?(?:woman|female|girl)|post-?op|pre-?op|phallo[a-z]*|meta|mastectomy|packer)(?![a-z0-9])|(?<![a-z0-9])t ?[:=]|⚧"
    ))
});

pub fn ftm(lowered: &[char]) -> bool {
    FTM.test(lowered)
}

static FERTILITY: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![a-z0-9])(?:ivf|iui|ttc|fet|retrievals?|stims?|embryos?|transfers?)(?![a-z0-9])"));

pub fn trans_cued(lowered: &[char]) -> bool {
    TRANS_CUES.test(lowered) || (lowered.contains(&'💉') && !FERTILITY.test(lowered))
}

pub fn dated(lowered: &[char]) -> bool {
    (MOTHERING.test(lowered) || MOTHER_DATES.test(lowered)) && !trans_cued(lowered)
}

fn mothered(lowered: &[char]) -> bool {
    FTM.test(lowered) && MOTHERING.test(lowered) && !trans_cued(lowered)
}

pub fn settle(lowered: &[char], found: &mut Found) {
    if mothered(lowered) {
        found.items.retain(|(attribute, value, _, _)| !(attribute == "gender" && value == "trans man"));
    }
    let mut split = Vec::new();
    for (attribute, value, position, origin) in std::mem::take(&mut found.items) {
        if attribute != "gender" || IDENTITIES.contains(&value.as_str()) {
            found.items.push((attribute, value, position, origin));
            continue;
        }
        let (_, gender, status) = SPLIT.iter().find(|(stated, _, _)| *stated == value).unwrap_or_else(|| panic!("gender value {value:?} has no identity or trans status"));
        split.extend(gender.map(|gender| ("gender", gender, position, origin)));
        split.extend(status.map(|status| ("trans_status", status, position, origin)));
    }
    for (attribute, value, position, origin) in split {
        found.put(attribute, value, position, origin);
    }
}

pub(crate) const IM: &str = r"i(?<!\wi)(?:'m|m| am|am| m|'am|'?ve been|'ve always been)";
pub(crate) const SPAN: &str = r"\s?(?:years?|yrs?|y)\s+(?:sober|clean|married|divorced|separated|together|widowed|single|celibate|abstinent|out|outside|in|into|on|off|post|past|from|behind|ahead|before|after|later|since|with|vegan|vegetarian|[a-z]+[- ]free|older|younger|apart|strong|outdated)\b";
pub(crate) const UNITS: &str = r"(?:years? ago|yrs? ago|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|times|percent|%|lbs?|kgs?|pounds|miles|km|cm|dollars|bucks|k\b|grand|hp|mph|degrees|feet|ft|inches|in\b(?!\s+(?!(?:a|an|the|few|couple|two|three|four|five|six|weeks?|months?|years?|days?|hours?|minutes?|length|girth|long|thick|wide|tall|cut|uncut|soft|hard|erect)\b)[a-z]{3,})|seconds|secs?|euros?|points|pts|ounces|oz|inch)";
pub(crate) static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:a|an|said|got|it's|its|costs?|paid|worth) $|\b(?:my|his|her|their|our|your|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|fianc\w*|spouse|ex|friend|son|daughter|brother|sister|mom|dad|mother|",
    r"father|dom|sub|guy|girl|man|woman|someone|somebody|with|e\.g|eg|example|like|for|to|and|older|younger|current|new|another|this|that|the)\W*$"
)));
pub(crate) static SELF: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"(?:\b(?:i|me|myself|i'm|im|i am|ich|moi|yo|as|bin)(?:\s+an?)?|^", claimcore::flair!(), r")\W*$")));

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
pub(crate) static GENDERS: LazyLock<Table> = LazyLock::new(|| [BASE_GENDERS, KINSHIP, PLURALS, ROLES].iter().flat_map(|t| t.iter()).map(|(k, v)| (k.to_string(), *v)).collect());
pub(crate) static GENDER_WORDS: LazyLock<String> = LazyLock::new(|| {
    let kin = KINSHIP.iter().map(|(k, _)| *k).collect::<Vec<_>>().join("|");
    format!(r"(?<!\btrans )(?<!\btrans-)(?<!\btransgender )(?<!\bcis )(?<!\bcis-)(?<!\bcisgender )(?<!\bcisgendered )(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|(?<=\ba )women|girl|female|lady|gal|chick|bull|stud|boi|cougar|gilf|domme|{kin})")
});
pub(crate) const ADJECTIVES: &str = concat!(
    r"(?:(?:\d{2}[- ]?(?:years?|yrs?|y/?o)(?:[- ]old)?|single|married|straight|gay|bi|bisexual|white|black|asian|latino|latina|hispanic|indian|young|old|older|middle[- ]aged|",
    r"tall|short|fat|chubby|skinny|fit|average|normal|regular|grown|divorced|disabled|autistic|working|stay[- ]at[- ]home|new|first[- ]time|",
    r"american|british|canadian|australian|christian|muslim|jewish|catholic|retired|lonely|horny|shy|curvy|petite|busy|proud) ){0,3}"
);
pub(crate) static ORIENTATIONS: LazyLock<Table> = LazyLock::new(|| table(&[
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
pub(crate) static ETHNIC_KEYS: LazyLock<Vec<&'static str>> = LazyLock::new(|| BASE_ETHNICITIES.iter().map(|(k, _)| *k).collect());
pub static ETHNICITIES: LazyLock<Table> = LazyLock::new(|| table(BASE_ETHNICITIES));
const REGION_BEFORE: &str = r"(?<!\beast )(?<!\beast-)(?<!\bsouth )(?<!\bsouth-)(?<!\bsoutheast )(?<!\bnorth )";
pub(crate) static ETHNIC_JOINED: LazyLock<String> = LazyLock::new(|| format!("{REGION_BEFORE}(?:{})", alternation(ETHNIC_KEYS.iter().copied())));
pub(crate) static ETHNIC_NAMES: LazyLock<String> = LazyLock::new(|| format!("{REGION_BEFORE}(?:{})", escaped_longest(ETHNIC_KEYS.iter().copied())));
pub(crate) const FREE: &str = r#"(?:(?!(?:not|never|no|with|for|to|than|like|and|or|that|who|this|the|my|his|her|your|their|our|a|an|in|on|at|from|about|by|into|fan|friend|friends)\b)[\w'"”-]+ )"#;
pub(crate) static COLORS: LazyLock<Table> = LazyLock::new(|| table(&[("ebony", "black"), ("wasian", "mixed"), ("blk", "black")]));
pub(crate) static OTHER_ETHNIC: LazyLock<String> = LazyLock::new(|| {
    format!("{REGION_BEFORE}(?:{})", escaped_longest(ETHNIC_KEYS.iter().copied().chain(["ebony", "wasian", "blk"]).filter(|w| !["white", "black", "mixed"].contains(w))))
});
pub(crate) const PERSON: &str = r"(?:m|f|male|female|guy|girl|man|woman|dude|bro|boy|top|bottom|bull|daddy|dad|mom|milf|wife|hubby|couple|here|stud|twink|bear|femboy|sub|dom|\d{2})\b";
pub(crate) static PARTY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:my|his|her|their|our|your|you|you're|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|for|with|like|seeking|looking|want|wants|someone|be)\W+(?:\w+\W+)?$"));
pub(crate) static ORIENTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:(?<![\w-])|(?<=\s-))(?<!\bbe )(?<!\bfor )(?<!\bsome )(?<!\bwith )(?<!\binto )(?<!\bother )(?<!\bhosting )(?<!\bfrom )(?<!\bgo )(?<!\bgoes )(?<!\bwent )(?<!\bgoing )(?<!\bcome )(?<!\bcame )(?<!\bhead )(?<!\bheaded )(?<!\[)(bi|bisexual|straight|str8|gay|lesbian|pansexual|hetero)(?![\w-])(?! (?:outside|in|into|home|back|down|from|through|off|men|women|guys|girls|porn|couples?|friendly|friends?|people|community|rights|marriage|bars?|clubs?|curious|or|and (?:\w+ )?(?:men|women|guys|girls|gay|straight|bi|bisexual|lesbian|trans|queer|people|couples?)|to|up|talk|ahead|away|forward|out|ones)\b)"));
pub(crate) const MONTHS: &str = "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december";
pub(crate) static DIGIT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d"));
pub(crate) static PAIR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d\d"));
pub(crate) static COUNTED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{MONTHS}|level|lvl|day|number|no|chapter|episode|season|page|version|room|unit|size|model|wife|husband|gf|bf|girlfriend|boyfriend|son|daughter|mom|dad)\W*$")));
pub(crate) static GAME: LazyLock<Re> = LazyLock::new(|| Re::new(r"\n[^\S\n]*\^\([^\n]*\)[^\S\n]*$"));
pub(crate) static AD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:[mf]4[mfat]\w*|dms?|snap|sc|kik|tele|telegram|hmu|horny|sext|sexting|bwc|bbc|cock|dick|pussy|fwb|nsa|hookup|host|hosting|discreet|bator|goon|gooner|trade|nudes|bi|gay|str8|daddy|milf|sissy|femboy|twink|bull|cuck|hotwife|bbw|onlyfans|kinky|naughty)\b"));
pub(crate) static YEARS_OLD: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![\w$])\d{2}\s?(?:yo|y/o)\b"));
pub(crate) static THIRD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:she|he|her|his|they|their|him|them)\b|\b(?:my|our|your) (?:\w+ )?(?:wife|husband|hubby|gf|bf|girlfriend|boyfriend|partner|son|daughter|kid|baby|mom|mother|dad|father|brother|sister|friend|dog|cat|puppy)\b"));
pub(crate) static CLOSING: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\(\[](\d{2})[\)\]][^\w\n]*(?:\n|$)"));
pub(crate) static START: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"^", claimcore::flair!(), r"\W{0,3}(\d{2})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)")));
pub(crate) const PARTNERS: &str = r"(?:girlfriend|boyfriend|gf|bf|partner|friend|friends|ex|neighbor|neighbour|coworker|boss)\b";
pub(crate) const BODY_NOUNS: &str = r"(?:build|built|body|bod|frame|figure|shape|girl|guy|woman|man|boy|boi|bro|bull|stud|jock|twink|femboy|sub|dom|cub|otter|bottom|top|vers|bear|daddy|milf|hotwife|wife|husband|hubby|mom|mum|dad|grandpa|grandma|lady|gal|chick|dude|male|female|married|single|f|m|here|latina|latino|black|white|asian|blonde|brunette|boyfriend|girlfriend|bf|gf|breeder|slut|sissy|cuck|queen|king|baddie|babe|teen|mommy)\b";
pub(crate) const CROWD: &str = r"(?:guys|girls|women|men|ladies|tops|bottoms|bulls|bros|dudes|couples|people|queens|wives|moms|milfs|daddies|bears|twinks|chicks|females|males|chasers)\b";
pub(crate) const DESIRED_PATTERN: &str = r"n't\b|\bain'?t\b|\b(?<!-)(?:looking|look for|seeking|thing for|searching for|prefer\w*|pref|into|love|loves|like|likes|interested in|any|bonus|must|not|isn't|no|if|you|your|you're|ur)\b";
pub(crate) static DESIRED: LazyLock<Re> = LazyLock::new(|| Re::new(DESIRED_PATTERN));
pub(crate) static WANTING: LazyLock<Re> = LazyLock::new(|| Re::new(&(r"\b(?:want|wants|wish|wished|need|needs)\b|".to_string() + DESIRED_PATTERN)));
pub(crate) static ETHNIC: LazyLock<Re> = LazyLock::new(|| {
    let other = &*OTHER_ETHNIC;
    Re::new(&format!(r"(?<![\w-])(?:(white|black|mixed)(?=\s*(?:[,.!/|)&+]|$)|[^\S\n]*\n|(?<!mixed) (?:with|w/|w) | (?:\w+ ){{0,2}}?{BODY_NOUNS}|\s*{PERSON})|({other}))(?![\w-])(?! (?:\w+ ){{0,2}}{CROWD})(?! (?:\w+ )?{PARTNERS})"))
});

pub(crate) static POSTERS: LazyLock<Table> = LazyLock::new(|| table(&[
    ("m", "man"), ("f", "woman"), ("w", "woman"), ("fb", "woman"), ("fu", "woman"), ("futa", "woman"), ("tf", "trans woman"), ("tm", "trans man"),
    ("nb", "nonbinary"), ("wm", "man"), ("mwm", "man"), ("swm", "man"), ("dwm", "man"), ("bm", "man"), ("wf", "woman"),
]));
pub(crate) static LOOKING: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?<![a-z0-9'’])(?:[\[\(]?(\d{2})(?:\s*/\s*\d{2})?[\]\)]?\s*)?[\[\(]?\s*(nb|mtf|ftm|tf|tm|futa|fb|fu|[mf])((?:[mf]|/\w+)*)\s*4\s*((?:[mfatr]|me|nb|[a-z](?=[a-z/]*\s*[\]\)]))[a-z/]*)\s*[\]\)]?(?:\s*[-–|:#]?\s*[\[\(]?(\d{2})(?!\d))?"));
pub(crate) static AGED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?=[\dmfwsdbtn])(?<![\w$£€#'/:+-])(?<![\w,]\.)(?<!\d,)(?:(\d{2})(?:\s?[/\\|-]?|,)\s?((?:[smd]?w|b)m|wf|mtf|ftm|tf|tm|fb|nb|[mf])(?:(?<=m)f(?![\w'])|(?<=f)m(?![\w']))?|((?:[smd]?w|b)m|tf|tm|fb|nb|[mfw])\s?[/'.,]?\s?(\d{2})(?:[mfa](?![\w'])|(?<=m\d\d)f\d{2}(?![\w'])|(?<=f\d\d)m\d{2}(?![\w']))?)(?!(?!_)[\w'%]|[-/]\d|-[a-z]\d)"));
pub(crate) static COLORED_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\w\n]*(?:(?!(?:for|any|need|needs|want|wants|seeking|looking|into|like|likes|love|loves|and|or|with)\b)[a-z]+ )?(white|black|blk|mixed)\b(?!['-])"));
pub(crate) static ORIENTED_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"[^\w\n]*(?:(?!(?:for|any|need|needs|want|wants|seeking|looking|into|like|likes|love|loves|and|or|with|not|no)\b)[a-z]+ )?(straight|str8|bi|bisexual|gay|pansexual)\b(?!['-]| to\b)(?! (?:\w+ ){{0,2}}{CROWD})")));
pub(crate) static FIRST: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|me|my|myself|mine)\b"));
pub(crate) static SPEAKER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i|i'm|im|i am|me|my name is)\b"));
pub(crate) static WORDED: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"(?=[\dmf])(?<![\w$#.,'/:+-])(?:(\d{{2}})\s?(?:yo|y/o|yrs?|years?(?: old)?)?(?:\s*/\s*|[\s,]*){ADJECTIVES}\(?(male|female)\)?|(male|female)(?:\s*/\s*|[\s,]*)(\d{{2}}))(?![\w'%])")));
pub(crate) static BRACKETED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?=[\d(\[mf])(?<![\w$#.,'/:+-])(?:(\d{2})\s?[\(\[]\s*([mf])\s*[\)\]]|[\(\[](\d{2})[\)\]]\s?(m|f|male|female)\b|([mf])\s?[\(\[](\d{2})[\)\]]|[\(\[]([mf])[\)\]]\s?(\d{2})\b)"));
pub(crate) static SIZED: LazyLock<Re> = LazyLock::new(|| Re::with(r"(?<![\w.$'])[4-7]\s?(?:'|ft)\s?\d{1,2}\b.{0,30}?\b\d{2,3}\s?(?:lbs?|kg|pounds)\b", claimcore::re::S));
pub(crate) static GREETED: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,;:(] *|\b(?:hey|hi|hello|yo|sup)\W+(?:\w+\W+)?)$")));
pub(crate) static NOWADAYS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i was|i started at|started at|i got \w+ at|when i was|since i was) (?:about |around )?(?:\d{1,2}|[a-z]+)\b[^.!?\n]{0,40}?,? (?:and |but |i'm |im |i am )*$"));
pub(crate) static NAMED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:i'm|im|i am|my name is|my name's) [a-z]+$"));
pub(crate) static COLORED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:white|black|asian|latino|latina|hispanic|indian|arab|mixed)[,\s]+(\d{2})\b(?![\d%.,]\d|\s*(?:min|mins|minutes|hours|days|years|yrs|percent|k|m|lbs|kg|inch|inches|cm)\b)"));
pub(crate) static OPENING: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(r"(?:^", claimcore::flair!(), r"|\n)\W*(?:(\d{2})\s?(?:yo|y/o|yrs?|years? old)?[\s,]+(?:(?!(?:is|was|are|the|a|an|my|your|his|her|their|and|or|of|for|to|with)\b)[a-z]+\s){0,2}?(m|f|male|female|guy|girl|man|woman|dude|bro|wife|mom|milf|hotwife|dad|daddy|bwc|bbc|bull|twink|femboy|stud)\b(?!')|(?:a\s)?(?:(?!trans\b)[a-z]+\s)?(wife|milf|hotwife|mom|mum|mommy|daddy|dad|bro|guy|girl|woman|man|lady)(?:\s+of\s+\d|[\s,]*(\d{2}))\b(?=[\s,.!]|$))")));
pub(crate) static WORDY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\w"));
static CAR_FLAIR: LazyLock<Re> = LazyLock::new(|| Re::new(r"^r/(?:bmw\w*|[efg]\d{2}\w*|cars|cartalk\w*|autos):"));
static CHASSIS_BEFORE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:bmw|m[1-8]|x[1-7]|z[1-8]|[eg]\d{2}|\d{3}(?:i|d|e|xi|xd|ci|is))\b|(?:'\d{2}|\b(?:19|20)\d{2})[\s,/|(-]*$"));
static CHASSIS_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\s,/|-]*(?:m[1-8]|x[1-7]|z[1-8]|i[3-8]|m?\d{3}(?:i|d|e|xi|xd|ci|is)|[eg]\d{2}|[1-8] ?series|xdrive|sdrive|competition|comp|touring|gran coupe|m ?sport|lci|zcp|[56]mt|swap\w*|engine)\b"));

pub(crate) fn escaped_longest<'a>(words: impl IntoIterator<Item = &'a str>) -> String {
    let mut escaped: Vec<String> = words.into_iter().map(escape).collect();
    escaped.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    escaped.dedup();
    escaped.join("|")
}

pub(crate) fn tail_sentence(s: &[char], start: usize, width: usize) -> &[char] {
    let window = &s[start.saturating_sub(width)..start];
    &window[last_mark(window, window.len(), ".!?\n")..]
}

pub(crate) fn owned(lowered: &[char], start: usize) -> bool {
    let before = tail_sentence(lowered, start, 24);
    SELF.test(before) || (start < opening(lowered) + 60 && !OTHERS.test(before)) || !WORDY.test(before)
}

pub(crate) fn desired(lowered: &[char], start: usize) -> bool {
    WANTING.test(tail_sentence(lowered, start, 80))
}

pub(crate) fn desired_by(lowered: &[char], start: usize, pattern: &Re) -> bool {
    pattern.test(tail_sentence(lowered, start, 80))
}

pub(crate) fn chassis(lowered: &[char], start: usize, end: usize) -> bool {
    CAR_FLAIR.at(lowered, 0).is_some() || CHASSIS_BEFORE.test(before(lowered, start, 16)) || CHASSIS_AFTER.at(lowered, end).is_some()
}

pub(crate) fn sentence(text: &[char], start: usize, end: usize) -> &[char] {
    &text[last_mark(text, start, ".!?\n")..next_mark(text, end, ".!?\n")]
}

pub(crate) fn ages(value: Option<&[char]>) -> Option<String> {
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

pub(crate) fn either<'a>(m: &Match<'a>, groups: &[usize]) -> Option<&'a [char]> {
    for &g in groups {
        if let Some(v) = m.nonempty(g) {
            return Some(v);
        }
    }
    m.group(*groups.last().unwrap())
}

pub(crate) fn get(t: &Table, key: Option<&[char]>) -> Option<String> {
    lookup(t, key)
}

pub fn init() {
    timed("demographics init", || {
        LazyLock::force(&rules::RULES);
        for re in [&OTHERS, &SELF, &PARTY, &ORIENTED, &DIGIT, &PAIR, &COUNTED, &GAME, &AD, &YEARS_OLD, &THIRD, &CLOSING, &START, &DESIRED, &WANTING, &ETHNIC, &LOOKING, &AGED, &COLORED_AFTER, &ORIENTED_AFTER, &FIRST, &SPEAKER, &WORDED, &BRACKETED, &SIZED, &GREETED, &NOWADAYS, &NAMED, &COLORED, &OPENING, &WORDY, &CAR_FLAIR, &CHASSIS_BEFORE, &CHASSIS_AFTER] {
            LazyLock::force(re);
        }
        tags::force();
        identity::force();
        rules::force();
    });
}
