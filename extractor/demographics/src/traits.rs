use crate::rules::{alone, h, mine, personal, said, sh};
use crate::*;
use claimcore::*;
use std::sync::LazyLock;

const EYE: &str = r"((?:blue|brown|green|hazel|grey|gray|amber)(?:ish|y)?(?:(?:\s?[-/]\s?|\s)(?:blue|brown|green|hazel|grey|gray|amber)(?:ish)?){0,2})";
const PAIR_EYE: &str = r"(blue|brown|green|hazel|grey|gray|amber)(?:ish|y)?(?:\s?[-/]\s?|\s|\s(?:and|or|to)\s)(blue|brown|green|hazel|grey|gray|amber)(?:ish)?";
const EYE_ADJ: &str = r"(?:(?:light|dark|deep|bright|big|pretty|piercing|striking|sparkling|baby|ice|icy|crystal|beautiful|clear|pale|natural|very|really|steel|sky|ocean|pure|warm|plain|boring|dull) )*";
const CURL: &str = r"(straight|wavy|curly|coily|kinky)";
const HAIR_ADJ: &str = r"(?:(?:long|short|thick|thin|fine|natural|naturally|very|super|really|dark|light|black|brown|blonde?|blondish|brownish|red|ginger|auburn|grey|gray|shoulder[- ]length|medium|medium[- ]length|messy|big|frizzy|loose|tight|kinda|slightly|pretty|extremely|coarse|soft|dirty|and),? )*";
const HAIR_TAIL: &str = r"(?:,?(?: and)? (?:long|short|thick|thin|fine|dark|light|black|brown|blonde?|blondish|brownish|red|ginger|auburn|grey|gray|straight|wavy|curly|coarse|heavy|frizzy|messy|natural))*";
const GEN: &str = r"(millennial|millenial|milennial|gen[- ]?z-?er|gen[- ]?z|zoomer|gen[- ]?x-?er|gen[- ]?x|gen[- ]?y|xennial|zillennial|zillenial|boomer|baby boomer|gen[- ]?alpha|gen[- ]?jones|generation (?:x|y|z|alpha|jones))";
const GEN_AFTER: &str = r"(?![-'])(?! (?:kids?|parents?|stuff|humou?r|thing|things|music|culture|mindset|energy|brain|vibes?|style|era|tastes?|problems?|trope|nostalgia|bait|household|home|house|money|memes?|shooter|shooters|games?|logic|films?|movies?|shows?|songs?|bands?|books?|characters?|icons?|staples?|classics?)\b)";
const EXPRESSION: &str = r"(femboy|femboi|sissy|tomboy|butch|femme|masc|crossdresser|cross-dresser|crossdressor|cd|androgynous|gnc|gender[- ]non[- ]?conforming)";
const ROMANTIC: &str = r"(aromantic|aro-ace|aroace|aro ace|aro/ace|demiromantic|demi-romantic|demiaroace|demi-aroace|demiaro|biromantic|bi-romantic|panromantic|pan-romantic|homoromantic|homo-romantic|heteroromantic|hetero-romantic|greyromantic|grayromantic|grey-romantic|gray-romantic|greyaro|grayaro)";
const HAD: &str = r"\bi(?:'ve| have)? (?:(?:just|recently|finally|already|also|successfully) )*(?:had|got|underwent)";
const NUM: &str = r"(\d{1,2}(?:[.,]\d{1,2})?)(?:\s?(?:and )?(1/2|½|1/4|¼|3/4|¾))?";
const INCH: &str = r#"\s?-?\s?(inches|inch|in\b|"|”|''|incher|cm)"#;
const PHALLUS: &str = r"(?:cock|dick|penis|bwc|bbc|shaft|member|dong|schwanz|uncut|cut|meat|tool|pp|johnson|dicc)\b";
const PHALLUS_ADJ: &str = r"(?:(?:and |, ?|& ?|of |with )?(?:thick|fat|girthy|uncut|cut|hard|veiny|big|white|black|brown|hairy|throbbing|circumcised|uncircumcised|shaved|smooth|curved|hung|very|rock|long|massive|huge|nice|meaty|juicy|pierced|horny|bald|clean|erect|average|small|tiny|little|decent|good|beautiful|pretty|latino|asian|desi|indian)[\s,]+){0,5}";
const POUNDS: &str = r"(lbs?|pounds|kgs?|kilos?|kilograms|stone|st)";
const BRA_CUP: &str = r"(aa|dddd|ddd|dd|ff|gg|hh|jj|kk|[a-eg-k])";
const LETTER_SIZE: &str = r"(xxs|xs|xl|xxl|xxxl|[2-6]x|[2-6]xl|x-large|extra large|extra small|xx-large)";

static EYES: LazyLock<Table> = LazyLock::new(|| table(&[("blue", "blue"), ("brown", "brown"), ("green", "green"), ("hazel", "hazel"), ("grey", "gray"), ("gray", "gray"), ("amber", "amber")]));
static CURLS: LazyLock<Table> = LazyLock::new(|| table(&[("straight", "straight (type 1)"), ("wavy", "wavy (type 2)"), ("curly", "curly (type 3)"), ("coily", "coily (type 4)"), ("kinky", "coily (type 4)"),
    ("1", "straight (type 1)"), ("2", "wavy (type 2)"), ("3", "curly (type 3)"), ("4", "coily (type 4)")]));
static TONES: LazyLock<Table> = LazyLock::new(|| table(&[("fair", "fair / pale"), ("pale", "fair / pale"), ("light", "light"), ("medium", "medium / tan"), ("tan", "medium / tan"), ("tanned", "medium / tan"),
    ("olive", "olive"), ("brown", "brown"), ("dark", "dark / deep"), ("darker", "dark / deep"), ("deep", "dark / deep")]));
static EXPRESSIONS: LazyLock<Table> = LazyLock::new(|| table(&[("femboy", "femboy"), ("femboi", "femboy"), ("sissy", "sissy"), ("tomboy", "tomboy"), ("butch", "butch"), ("femme", "femme"), ("masc", "masc"),
    ("crossdresser", "crossdresser"), ("cross-dresser", "crossdresser"), ("crossdressor", "crossdresser"), ("cd", "crossdresser"), ("androgynous", "androgynous"), ("gnc", "gender non-conforming"),
    ("gender non-conforming", "gender non-conforming"), ("gender nonconforming", "gender non-conforming"), ("gender non conforming", "gender non-conforming"), ("gender-non-conforming", "gender non-conforming")]));
static BARIATRIC: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:bariatric|gastric|sleeve|bypass|wls|vsg|rny|lap band|weight loss surgery)\b"));
static TRANSY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:trans|transgender|mtf|ftm|transfem|transmasc|transfemme|nonbinary|non-binary|enby|estradiol|dysphoria|transition|transitioning|transitioned|t4t|tgirl|transwoman|transman|transsexual|spiro|spironolactone|bica|bicalutamide|cypro|cyproterone|deadname|deadnamed|clocked|voice training|binder|she/her|he/him|they/them|top surgery|bottom surgery|ffs|srs|grs)\b"));
static SHOD: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:feet|foot|shoes?|sneakers|boots|rings?|gloves?|footpass|hats?|helmets?|bikes?|frames?|condoms?|wheels?|skis?|board|boards)\b"));
static PRONOUN_END: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:[\)\]|,;.!\n]|$|-|(?:here|pronouns|prns|and)\b)"));
static NARRATED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:has|is|was|had|does|wears)\b"));
static HAIRY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:hair|curls?|porosity|wash day|curly girl)\b"));
static SOFT_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:\w+\s+)?(?:soft|flaccid|limp|girth|around|wide|circumference|thick\b(?!\s+\w*\s*(?:cock|dick|penis|bwc|bbc)))"));
static ENDOWED: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"(?:\b(?:i|i've|ive) (?:have|got|'ve got|ve got|have got|'m packing|am packing|'m sporting|am sporting|measure|measured)|\bmy|\bi'm|\bim|\bi am|\bhung|\bhung with|\bsporting|\bpacking|\bme)",
    r"(?: (?:a|an|about|around|roughly|nearly|almost|just|only|over|under|like|maybe|solid|nice|thick|fat|big|decent|average|hard|rock|exactly|barely|very|well|hung|uncut|cut|bwc|bbc|girthy|juicy|curved|massive|huge|long))* $"
)));
static LISTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|[\n(\[\]|,/;:.!?-])\s*$"));
static WITH: LazyLock<Re> = LazyLock::new(|| Re::new(r"\bw(?:ith|/) (?:an? )?(?:(?:thick|fat|big|hard|long|girthy|nice|huge|massive|uncut|cut|juicy|curved) )*$"));
static PHALLIC_TEXT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:cock|dick|penis|bwc|bbc|uncut|girth|girthy|hung|erect|circumcised)\b"));
static UNIT_IN_LINE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\d\s*(kgs?|kilos?|lbs?|pounds)\b"));
static STAT_LINE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:cw|gw|hw|current weight|goal weight|weight|lbs?|kgs?|pounds)\b"));
static WEIGHTY: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:lose|losing|lost|weight|weigh|weighed|calories|cals|deficit|scale|tirz\w*|zep\w*|sema\w*|ozempic|wegovy|mounjaro|glp-?1|reta\w*|diet|cw|gw|sw)\b"));
static PRONOUNED: LazyLock<Re> = LazyLock::new(|| {
    let token = r"(?:she|he|they|it|xe|ze|zie|fae|ey|ve|any|all|her|him|them|its|hers|his|xem|xir|xyr|xey|zir|zim|zem|hir|faer|faeself|em|eir|ver|vis|ae|aer|star|moon|void|thon)";
    Re::new(&format!(r"(?<![\w/])({token}(?:\s?/\s?{token})+(?:\s+pronouns)?|any pronouns)(?![\w/])"))
});
static PRONOUN_SAID: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:\bmy pronouns(?: are| r| is)?|\bpronouns[*_\s]*(?:are|[:=-])[*_]*|\bi (?:use|go by|prefer|'m fine with|am fine with|answer to)|\b(?:i'm|im|i am) [^.!?\n]{0,60}?)\s*[\(\[]?\s*$"));
static PRONOUN_LABEL: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|[\n(\[|,;:-]|(?<![\w.$#/])\d{2})\s*$"));
static PRONOUN_HERE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*[\)\]]?\s*(?:here|pronouns|prns)\b"));
static SKIN_TYPED: LazyLock<Re> = LazyLock::new(|| {
    let word = r"(?:oily|dry|combination|combo|combi|normal|sensitive|acne[- ]?prone|reactive|dehydrated|easily irritated|breakout[- ]prone|very|super|really|extremely|quite|pretty|slightly|somewhat|kinda|naturally|severely|mostly|leaning|and|or|but|to|a bit|a little|af|asf)";
    Re::new(&format!(r"\b(?:i(?:'ve| have)? (?:(?:also|just|still|really|do|actually|always|naturally|currently) )*(?:have|got)|i've always had|(?:i'm|im|i am|as) an?|my)\s+((?:{word}[\s,/&+-]*){{1,8}})skin\b(?!\s*(?:care|routine|tone|color|colour|products?|doctor|cancer|tags?|issues?|problems?|conditions?|in (?:fortnite|game)))|\b(?:my skin(?: type)?(?: is|'s| has always been| tends to be| can be| gets| is naturally)|skin type[*_\s]*[:=-][*_]*)\s+((?:{word}[\s,/&+-]*){{1,8}})"))
});
static SKIN_WORDS: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(oily|dry|combination|combo|combi|normal|sensitive|reactive|acne[- ]?prone)\b"));
static SKIN_TYPES: LazyLock<Table> = LazyLock::new(|| table(&[("oily", "oily"), ("dry", "dry"), ("combination", "combination"), ("combo", "combination"), ("combi", "combination"), ("normal", "normal"),
    ("sensitive", "sensitive"), ("reactive", "sensitive"), ("acne-prone", "acne-prone"), ("acne prone", "acne-prone"), ("acneprone", "acne-prone")]));

fn eye(m: &Match) -> Option<String> {
    let phrase = st(m.first()?);
    if phrase.contains("hazel") {
        return Some("hazel".to_string());
    }
    let first = ["blue", "brown", "green", "grey", "gray", "amber"].iter().filter_map(|c| phrase.find(c).map(|i| (i, *c))).min()?;
    EYES.get(first.1).map(|v| v.to_string())
}

fn second_eye(m: &Match) -> Option<String> {
    let first = get(&EYES, either(m, &[1, 3]))?;
    let second = get(&EYES, either(m, &[2, 4]))?;
    if first == second { None } else if second == "hazel" { Some(first) } else { Some(second) }
}

fn porosity(m: &Match) -> Option<String> {
    let level = m.first_s()?;
    Some(if level == "normal" { "medium".to_string() } else { level })
}

fn curl(m: &Match) -> Option<String> {
    get(&CURLS, m.first())
}

fn told(m: &Match) -> bool {
    desired(m.string, m.start()) || NARRATED.test(tail_sentence(m.string, m.start(), 80))
}

fn plain(lowered: &[char], start: usize, end: usize) -> bool {
    !SELF_LIMIT.test_in(lowered, clause(lowered, start).max(start.saturating_sub(40)), start) && !question(lowered, end)
}

fn generation(m: &Match) -> Option<String> {
    let key: String = st(m.first()?).chars().filter(|c| c.is_alphanumeric()).collect();
    let key = key.trim_start_matches("generation").to_string();
    let value = match key.as_str() {
        "millennial" | "millenial" | "milennial" | "millennials" | "millenials" | "geny" | "y" => "millennial",
        "genz" | "genzer" | "genzers" | "zoomer" | "zoomers" | "z" => "gen z",
        "genx" | "genxer" | "genxers" | "x" => "gen x",
        "xennial" | "xennials" => "xennial",
        "zillennial" | "zillenial" | "zillennials" => "zillennial",
        "boomer" | "babyboomer" | "boomers" => "boomer",
        "genalpha" | "alpha" => "gen alpha",
        "genjones" | "jones" => "gen jones",
        _ => return None,
    };
    Some(value.to_string())
}

fn romantic(m: &Match) -> Option<String> {
    let key = st(m.first()?);
    let value = if key.starts_with("demi") {
        "demiromantic"
    } else if key.starts_with("grey") || key.starts_with("gray") {
        "grayromantic"
    } else if key.starts_with("bi") {
        "biromantic"
    } else if key.starts_with("pan") {
        "panromantic"
    } else if key.starts_with("homo") {
        "homoromantic"
    } else if key.starts_with("hetero") {
        "heteroromantic"
    } else {
        "aromantic"
    };
    Some(value.to_string())
}

fn transitioned(value: &'static str) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| if TRANSY.test(m.string) { Some(value.to_string()) } else { None }
}

fn surgery(m: &Match) -> Option<String> {
    if !TRANSY.test(m.string) {
        return None;
    }
    let word = st(m.first()?);
    let value = match word.as_str() {
        "top surgery" => "top surgery",
        "ffs" | "facial feminization" | "facial feminisation" | "facial feminization surgery" | "facial feminisation surgery" => "facial feminization",
        "hysterectomy" | "orchiectomy" | "orchi" | "orchidectomy" => "hysterectomy / orchiectomy",
        _ => "bottom surgery",
    };
    Some(value.to_string())
}

fn length(number: &[char], fraction: Option<&[char]>, unit: &[char]) -> Option<String> {
    let mut amount = py_float(&st(number).replace(',', ".").chars().collect::<Vec<_>>())?;
    amount += match fraction.map(st).as_deref() {
        Some("1/2") | Some("½") => 0.5,
        Some("1/4") | Some("¼") => 0.25,
        Some("3/4") | Some("¾") => 0.75,
        _ => 0.0,
    };
    if eq(unit, "cm") {
        if !(8.0..=30.0).contains(&amount) {
            return None;
        }
        amount /= 2.54;
    }
    if (2.0..=11.0).contains(&amount) { Some(format!("{amount:.1}")) } else { None }
}

fn endowed(m: &Match, explicit: bool) -> bool {
    let text = m.string;
    let start = m.start();
    if THIRD.test(tail_sentence(text, start, 80)) || desired(text, start) || SOFT_AFTER.at(text, m.end()).is_some() {
        return false;
    }
    let prefix = tail_sentence(text, start, 50);
    if ENDOWED.test(prefix) {
        return true;
    }
    let listed = LISTED.test(before(text, start, 4));
    if explicit || !(listed || WITH.test(prefix)) {
        return false;
    }
    let first = line(text, 0);
    MEASURED.test(line(text, start)) || (first.contains(&'4') && LOOKING.test(first)) || AGED.test(first) || (listed && FIRST.test(sentence(text, start, m.end())))
}

fn kilograms(amount: &[char], unit: &[char]) -> Option<f64> {
    let amount = py_float(&st(amount).replace(',', ".").chars().collect::<Vec<_>>())?;
    let unit = st(unit);
    Some(if unit.starts_with('k') {
        amount
    } else if unit.starts_with("st") {
        amount * 6.35
    } else {
        amount * 0.4536
    })
}

fn starting(m: &Match, stat: bool) -> Option<String> {
    let text = m.string;
    let amount = m.group(1)?;
    let row = line(text, m.start());
    let unit: Vec<char> = match m.nonempty(2).or(m.nonempty(3)) {
        Some(unit) => unit.to_vec(),
        None => match UNIT_IN_LINE.find(row) {
            Some(found) if stat => found.group(1)?.to_vec(),
            _ => {
                let context = if stat { STAT_LINE.test(row) } else { WEIGHTY.test(sentence(text, m.start(), m.end())) };
                if py_int(amount)? >= 150 && context { chars("lbs") } else { return None }
            }
        },
    };
    let kilos = kilograms(amount, &unit)?;
    if (40.0..=320.0).contains(&kilos) { Some(rounded(kilos)) } else { None }
}

fn lost(m: &Match) -> Option<String> {
    for (a, b) in [(1, 2), (3, 4), (5, 6)] {
        if let (Some(amount), Some(unit)) = (m.nonempty(a), m.nonempty(b)) {
            let kilos = kilograms(amount, unit)?;
            return if (1.0..=250.0).contains(&kilos) { Some(rounded(kilos)) } else { None };
        }
    }
    None
}

fn bra(m: &Match) -> Option<String> {
    let band = py_int(m.group(1)?)?;
    if (28..=48).contains(&band) { Some(format!("{band}{}", st(m.group(2)?))) } else { None }
}

fn clothing(m: &Match) -> Option<String> {
    if SHOD.test(sentence(m.string, m.start(), m.end())) {
        return None;
    }
    let size = st(m.first()?);
    let value = match size.as_str() {
        "small" => "s".to_string(),
        "medium" => "m".to_string(),
        "large" => "l".to_string(),
        "x-large" | "extra large" => "xl".to_string(),
        "xx-large" => "xxl".to_string(),
        "extra small" => "xs".to_string(),
        _ if size.chars().next()?.is_ascii_digit() && !size.ends_with('x') && !size.ends_with("xl") => {
            if py_int(&chars(size.split('/').next()?))? > 30 {
                return None;
            }
            format!("size {size}")
        }
        _ => size,
    };
    Some(value)
}

fn shoe(m: &Match) -> Option<String> {
    let amount = py_float(&st(m.first()?).replace(',', ".").chars().collect::<Vec<_>>())?;
    if (3.0..=50.0).contains(&amount) { Some(format!("{amount}")) } else { None }
}

pub fn rules() -> Vec<Rule> {
    let mut all = Vec::new();
    all.extend(appearance());
    all.extend(identity());
    all.extend(measures());
    all
}

fn appearance() -> Vec<Rule> {
    let tone_mod = r"(?:(?:very|super|really|naturally|quite|pretty|slightly|somewhat|kinda|kind of|a bit|fair|pale|light|olive|warm|cool|neutral|medium|golden|yellow|pink)[- ,/]+)*";
    let tone = r"(fair|pale|light|olive|tan|tanned|brown|dark|darker|deep|medium)";
    vec![
        said("eye_color", &format!(r"\b(?:i have|i've got|i got|i also have|my) {EYE_ADJ}{EYE} eyes\b"), alone(eye), h()),
        said("eye_color", &format!(r"\b(?:i have|i've got|i got|i also have|my) {EYE_ADJ}{PAIR_EYE} eyes\b|\bmy eyes are (?:(?:a|very|really|more|light|dark|bright|deep|pale|naturally|kinda|sort of) )*{PAIR_EYE}\b"), alone(second_eye), h()),
        said("eye_color", &format!(r"\bi (?:have|was born with|'ve got|got) (?:(?:central|sectoral|complete|partial|mild|slight) )?heterochromia\b|{IM} heterochromatic\b|\bmy heterochromia\b"), fixed("heterochromia"), h()),
        said("eye_color", &format!(r"\bmy eyes are (?:(?:a|very|really|more|light|dark|bright|deep|pale|naturally|kinda|sort of) )*{EYE}\b(?![-/])"), eye, h()),
        said("eye_color", &format!(r"{IM} (?:a |an )?{FREE}{{0,2}}?{EYE}[- ]eyed\b"), eye, h()),
        said("eye_color", &format!(r"\bw(?:ith|/)? {EYE_ADJ}{EYE} eyes\b"), alone(|m: &Match| {
            let first = line(m.string, 0);
            if !told(m) && (MEASURED.test(line(m.string, m.start())) || AGED.test(first) || (first.contains(&'4') && LOOKING.test(first))) { eye(m) } else { None }
        }), sh()),
        said("eye_color", &format!(r"(?:^|(?<=[\n,;|/().:])|(?<=\band))\s*{EYE_ADJ}{EYE}(?: eyes\b|[- ]eyed\b)"), personal(alone(|m: &Match| if told(m) { None } else { eye(m) })), sh()),
        said("hair_type", &format!(r"(?:\b(?:i have|i've got|i got|i also have|my)|(?<=, )have|(?<=\band )have) {HAIR_ADJ}{CURL}{HAIR_TAIL} hair\b"), alone(curl), h()),
        said("hair_type", &format!(r"\bmy hair(?: is|'s| has always been| is naturally) (?:(?:naturally|very|super|really|pretty|quite|kinda|kind of|extremely|so|also|thick|thin|fine|long|short|and|more|mostly),? )*{CURL}\b(?! (?:now|again|after|when|because)\b)"), curl, h()),
        said("hair_type", r"(?<![\w.$/#+-])([1-4])[abc](?:\s?[/-]\s?[1-4]?[abc])*(?: (?:type|curly|wavy|coily|kinky|curls|waves|coils|hair|ringlets))+\b|\bhair(?: type)?\s*(?:is|:|=|-)\s*(?:type\s*)?([1-4])[abc]\b", personal(alone(|m: &Match| if desired(m.string, m.start()) { None } else { curl(m) })), sh()),
        said("skin_type", &format!(r"\bi(?:'ve| have)? (?:(?:still|also|always|now|currently|really|just|recently|constantly|often|easily) )*(?:have|get|struggle with|suffer from|deal with|'ve had|have had|battle|fight) (?:(?:really|very|super|bad|severe|hormonal|cystic|adult|persistent|mild|moderate|chronic|constant|stubborn|terrible|horrible|some|a lot of|lots of|frequent) )*(?:acne|breakouts|pimples|cystic acne)\b(?! (?:scars?|marks?|scarring)\b)(?! (?:on|in|around) (?:my )?(?:balls|butt|ass|scalp|groin|thighs|legs|vulva|labia|penis|dick|nipples?|armpits?)\b)|{IM} (?:(?:very|super|really|extremely|so|also|still|quite|pretty) )*(?:acne[- ]?prone|prone to (?:acne|breakouts))\b"), fixed("acne-prone"), h()),
        said("hair_type", &format!(r"(?:^|(?<=[\n,;|/().:])|(?<=\band))\s*(?:(?:long|short|thick|thin|fine|coarse|heavy|frizzy|dark|light|black|brown|blonde?|red|medium|shoulder[- ]length),? )*{CURL}{HAIR_TAIL} hair\b"), personal(alone(|m: &Match| if told(m) { None } else { curl(m) })), sh()),
        said("hair_strand_width", r"\b(?:i have|i've got|i got|my) (?:(?:very|super|really|extremely|naturally|thin|long|short|straight|wavy|curly|and|thick|soft|dark|light|black|brown|blonde?)[, ]+)*(fine|coarse)(?:[, ]+(?:and |but )?(?:very |super )?(?:thin|thick|straight|wavy|curly|soft|dense|long|short|dark|light|black|brown|blonde?))* (?:hair|strands)\b", alone(|m: &Match| m.first_s()), h()),
        said("hair_strand_width", r"\bmy (?:hair )?strands (?:are|is) (?:(?:very|super|really|extremely|naturally|pretty|quite) )*(fine|coarse|medium)\b|\bhair(?: type)?[*_\s]*[:=-][*_\s]*(?:[\w-]+[, ]+){0,3}?(fine|coarse)\b", personal(alone(|m: &Match| m.first_s())), h()),
        said("hair_strand_width", r"\bmy (?:hair(?: strands)?|strands)(?: is| are|'s) (?:(?:very|super|really|extremely|naturally|pretty|quite|on the) )*(coarse|fine(?=,? (?:and |but )?(?:thin|straight|wavy|curly|soft|flat|limp|silky|thick|low|high|dense)\b))", |m: &Match| m.first_s(), h()),
        needs(said("hair_strand_width", r"\b(fine|medium|coarse)(?:[- ]to[- ](?:fine|medium|coarse))? (?:strands?|texture|width|thickness|strand width|strand thickness)\b|\b(?:strand (?:width|thickness|size|type)|strands|texture|thickness)\s*[:=-]\s*(fine|medium|coarse)\b",
            personal(alone(|m: &Match| if HAIRY.test(m.string) { m.first_s() } else { None })), sh()), &["hair", "porosity", "strand"]),
        needs(said("hair_density", r"\b((?:low|lower|medium|high|higher)(?:[- ](?:to[- ])?(?:low|medium|high))?)[- ]density\b|\bdensity\s*[:=-]\s*(low|medium|high)\b",
            personal(alone(|m: &Match| {
                if !HAIRY.test(m.string) {
                    return None;
                }
                let level = st(m.first()?);
                if level.ends_with("high") || level.ends_with("higher") { Some("high / thick".to_string()) } else if level.ends_with("low") || level.ends_with("lower") { Some("low".to_string()) } else { Some("medium".to_string()) }
            })), sh()), &["density"]),
        said("hair_density", r"(?:^|(?<=[\n,;|/().:])|(?<=\band))\s*(?:(?:naturally|very|super|really|relatively|quite|fairly|long|short|medium|straight|wavy|curly|dark|light|black|brown|blonde?|gray|grey|red|layered|fine|soft)[, ]+)*thick(?:[, ]+(?:and )?(?:straight|wavy|curly|dark|light|black|brown|blonde?|gray|grey|red|layered|long|short))* hair\b",
            personal(alone(|m: &Match| if told(m) { None } else { Some("high / thick".to_string()) })), sh()),
        said("hair_density", r"\b(?:i have|i've got|i got|my) (?:(?:very|super|really|extremely|naturally|relatively|quite|fairly|pretty|long|short|straight|wavy|curly|coarse|dark|black|brown|blonde?|and|so),? )*thick(?:,? (?:and )?(?:[a-z]+ )?)? hair\b|\bmy hair(?: is|'s) (?:(?:very|super|really|extremely|naturally|pretty|quite|so|also|long|and),? )*thick\b(?! (?:now|again)\b)",
            alone(fixed("high / thick")), h()),
        said("hair_porosity", r"\b(?:i have|i've got|i got|my hair(?: is|'s)?|my|i'm|im|i am)(?: [\w-]+){0,3}? (low|high|mixed|medium|normal)[- ]porosity\b", alone(porosity), h()),
        said("hair_porosity", r"\bporosity\s*(?:is|[:=-])\s*(low|high|mixed|medium|normal)\b|(?:^|(?<=[\n,;|.(/]))\s*(low|high|mixed|medium|normal)[- ]porosity\b", personal(alone(porosity)), sh()),
        said("skin_tone", &format!(r"\b(?:i have|i've got|i got|my) {tone_mod}{tone}[- ](?:skin|skinned|complexion|skin tone)\b(?!\s*(?:care|routine|people|folks|girls|guys|women|men))"), alone(|m: &Match| get(&TONES, m.first())), h()),
        said("skin_tone", &format!(r"{IM} (?:(?:very|super|really|naturally|quite|pretty|so|also|a|an|kinda|kind of|more|fairly|relatively|extremely) )*{tone_mod}{tone}[- ](?:skin|skinned|complexion|toned)\b(?! (?:people|folks|girls|guys|women|men)\b)|{IM} (?:(?:very|super|really|naturally|quite|pretty|so|also|kinda|fairly|extremely|incredibly|ghostly) )*(pale|tanned)\b(?! (?:with|from|after|in|and shaking)\b)"),
            |m: &Match| get(&TONES, m.first()), h()),
        said("skin_tone", &format!(r"(?:^|(?<=[\n,;|/().:])|(?<=\band))\s*{tone_mod}{tone}[- ](?:skin|skinned|complexion)\b(?!\s*(?:care|routine|people|folks|girls|guys|women|men))"), personal(alone(|m: &Match| if told(m) { None } else { get(&TONES, m.first()) })), sh()),
        said("skin_tone", r"\b(?:i'm|im|i am|sou|soy|ako ay|ako'y) (?:(?:a|an|medyo|bit|kinda|kind of|pretty|very|naturally) )*(moreno|morena)\b(?! (?:valley|family)\b)", fixed("moreno / morena"), h()),
        said("skin_tone", r"(?:^|(?<=[\n,;|/(]))\s*(?:(?:light|dark|cute|chinito|tall|chubby|slim) )?(moreno|morena)(?=\s*(?:[,;|/)\n.!]|$|na\b|and\b|&|with\b|guy\b|girl\b|man\b|woman\b|male\b|female\b|here\b))", personal(alone(|m: &Match| if told(m) { None } else { Some("moreno / morena".to_string()) })), sh()),
        said("skin_tone", r"\b(?:i'm|im|i am) (fair|light|light-medium|medium|tan|deep)[- ](?:to[- ])?(?:medium[- ])?(?:neutral|warm|cool|olive)\b", |m: &Match| get(&TONES, Some(&chars(&st(m.group(1)?).replace("light-medium", "light")))), h()),
        said("skin_tone", r"\b(?:i'm|im|i am) (?:an? )?(?:(?:fair|light|light-medium|medium|tan|deep|neutral|warm|cool|muted|leaning|true|cool-leaning|warm-leaning|neutral-warm|neutral-cool)[- ,/]+){1,4}(olive)\b(?! (?:oil|tree|garden|green|branch)\b)|\b(?:i'm|im|i am) (?:an? )?(olive)(?=[- ](?:skin|skinned|toned|complexion|undertones?)\b)", fixed("olive"), h()),
    ]
}

fn identity() -> Vec<Rule> {
    vec![
        said("generation", &format!(r"{IM} (?:(?:also|just|still|technically|basically|literally|actually|definitely|officially|a|an|the|proud|proudly|young|younger|old|older|elder|early|mid|middle|late|core|geriatric|ancient|baby|oldest|youngest|tail[- ]end|solidly|firmly|squarely|elderly|part of|one of those|very|on the cusp of|considered|an elder|an older|an early|a late|a young|an old) )*{GEN}\b{GEN_AFTER}"), generation, h()),
        said("generation", &format!(r"\bas an? (?:(?:young|younger|old|older|elder|early|late|fellow|proud|middle|core) )?{GEN}\b{GEN_AFTER}(?!['’]s)"), generation, h()),
        said("generation", &format!(r"(?:^|[.!?,;(\n] *|\bfellow )(?:(?:young|younger|old|older|elder|early|late) )?{GEN} here\b"), generation, sh()),
        said("generation", r"\b(?:we|us|fellow) (?:(?:older|younger|elder|early|late|old|young) )?(millennials|millenials|gen ?zers|gen ?xers|boomers|zoomers|xennials|zillennials|gen z|gen x)\b(?! (?:who|that)\b)", generation, h()),
        said("gender_expression", &format!(r"{IM} (?:(?:also|just|still|a|an|the|proud|proudly|cute|little|lil|pretty|submissive|sub|shy|horny|young|white|black|asian|latino|chubby|skinny|slim|petite|curvy|thick|soft|feminine|girly|slutty|naughty|needy|caged|good|total|hairy|smooth|bi|gay|straight|trans|cis|lesbian|nonbinary|non-binary|enby|fem|bottom|top|kinda|very|super|more|really|mostly|sweet|obedient|dommy|bratty|nerdy|closeted|secret|discreet|virgin) )*{EXPRESSION}\b(?![-'/])(?! (?:for|about|when|with|of|like|porn|content|captions?|hypno|stuff|ones?)\b)"),
            group(&EXPRESSIONS, 1), h()),
        said("gender_expression", &format!(r"(?:^|[\s,(\[|])(?:(?:\d{{2}}|cute|young|horny|sub|submissive|shy|chubby|slim|skinny|white|black|asian|latino|bi|gay|straight|trans|feminine|girly|slutty|curious|closeted|discreet),? )*(femboy|femboi|sissy|crossdresser|cd|tomboy|butch|masc) (?:(?:bottom|top|boy|guy|girl|slut|bitch|bi|gay|sub) )?(?:here|looking|seeking|needs?|wants?|for|4|available)\b"),
            mine(alone(|m: &Match| if desired(m.string, m.start()) { None } else { get(&EXPRESSIONS, m.group(1)) })), sh()),
        said("gender_expression", &format!(r"{IM} (?:an? )?stud(?: lesbian| dyke)\b|(?:^|[\n(\[|/,] *)stud lesbian\b|\bstud(?=/(?:butch|masc|lesbian|wlw)\b)"), mine(alone(fixed("stud"))), h()),
        said("gender_expression", &format!(r"\bas an? (?:[\w-]+ )?{EXPRESSION}\b(?!['’]s)(?! (?:porn|content|captions?)\b)"), group(&EXPRESSIONS, 1), h()),
        said("romantic_orientation", &format!(r"{IM} (?:(?:also|just|still|a|an|probably|definitely|actually|proudly|kinda|sort of|kind of|very|pretty|somewhat|more) )*(?:(?!not\b|never\b|no\b)[\w-]+ ){{0,2}}?(?:{ROMANTIC}|(aro))\b(?![-/])"), romantic, h()),
        said("romantic_orientation", &format!(r"(?:^|[\n(\[|/,]|\band\b)\s*{ROMANTIC}\b(?! (?:people|folks|community|ones|persons?|representation|characters?|flags?|spectrum|facts?|is|isn't|means|are)\b)|{ROMANTIC} (?:asexual|ace|lesbian|gay|bisexual|woman|man|girl|guy|person|enby)\b"), mine(alone(romantic)), sh()),
        said("romantic_orientation", &format!(r"\bas an? (?:[\w-]+ )?{ROMANTIC}\b(?! (?:people|folks)\b)"), romantic, h()),
        said("transition_care", r"\b(?:i(?:'m| am|m)|i've been|ive been|i have been) (?:(?:currently|now|still|finally|also|officially|just) )*on (?:hrt|estrogen|estradiol|testosterone|t|e|hormones)\b(?! (?:mobile|time|track|the|my|a)\b)|\bi (?:started|began|have been taking|'ve been taking|am taking|'m taking) (?:taking )?(?:hrt|estrogen|estradiol|testosterone|t|e)\b(?! (?:mobile|time|the|my|a)\b)",
            transitioned("hormone therapy"), h()),
        said("transition_care", r"(?:^|[.!?\n,(] *|\b(?:i'm|im|i am|been) )(?:about |almost |over |nearly )?(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an) (?:years?|yrs?|months?|mos?|weeks?|wks?) (?:(?:on |of |into )?hrt|(?:on|of|into) (?:e|t|estrogen|testosterone|estradiol))\b", transitioned("hormone therapy"), h()),
        said("transition_care", &format!(r"{HAD} (?:my |an? )?(top surgery|bottom surgery|srs|grs|gcs|vaginoplasty|phalloplasty|phallo|metoidioplasty|meta|ffs|facial femini[sz]ation(?: surgery)?|hysterectomy|orchiectomy|orchidectomy|orchi)\b"), surgery, h()),
        said("transition_care", &format!(r"{IM} (?:still |currently |very |completely )?pre[- ]?(?:transition|hrt|t|e|everything)\b"), transitioned("pre-transition"), h()),
        said("transition_care", &format!(r"{IM} (?:a |an |also |now |just )?(?:detrans|detransitioner|detransitioned|detransitioning)\b|\bi (?:have |'ve |had )?(?:recently |since |already |eventually )?detransitioned\b|\bas an? detrans(?:itioner)?\b"), fixed("detransitioned"), h()),
        said("transition_care", &format!(r"{IM} (?:(?:still|currently|now|also|finally|officially|a|an|\d+ (?:days?|weeks?|months?|years?)) )*(pre|post)[- ]?op\b(?! (?:diet|liquid|bariatric|gastric|sleeve|bypass|wls|vsg|rny)\b)|(?:^|[\n(\[|,] *)(pre|post)[- ]?op (?:trans|transgender|transsexual|mtf|ftm|tgirl|ts)\b(?! (?:women|men|folks|people|girls|guys|persons)\b)"),
            alone(mine(|m: &Match| if TRANSY.test(m.string) && !BARIATRIC.test(m.string) { Some(format!("{}-op", st(either(m, &[1, 2])?))) } else { None })), h()),
        said("transition_care", r"\bi (?:was|am|'m|got|went|have been|'ve been) (?:put |started |also |still |currently )?on (?:puberty |hormone |t |e )?blockers\b|\bi (?:took|take|started|was given) (?:puberty |hormone )?blockers\b", transitioned("puberty blockers"), h()),
        said("transition_care", r"\bi(?:'ve| have| had)? (?:(?:already|also|just|recently|finally|been) )*(?:had|got|done|did|started|doing|getting) (?:my |some |a few |\d+ )?(?:sessions? of |rounds? of |treatments? of )?(?:laser hair removal|electrolysis)\b", transitioned("hair removal"), h()),
        said("transition_care", r"\bi(?:'ve| have|'m| am)? (?:(?:already|also|just|recently|finally|been|currently|still) )*(?:doing|did|started|practicing|practising|working on|taking) (?:my )?voice (?:training|therapy|lessons)\b|\bi (?:had|got) (?:my )?(?:vfs|voice feminization surgery|voice feminisation surgery)\b", transitioned("voice training"), h()),
    ]
}

fn measures() -> Vec<Rule> {
    vec![
        said("penis_size", &format!(r#"(?<![\w.,'"”/$#+-]){NUM}{INCH}(?:\s+(?:long|hard|erect))?[\s,]+{PHALLUS_ADJ}{PHALLUS}|(?<![\w.,'"”/$#+-]){NUM}{INCH}(?:\s+(?:long|hard|erect))?,? (?:and|with|w/|&) (?:good |great |nice |a lot of |some |lots of |decent |very )?(?:girth|girthy|thick)\b|(?<![\w.,'"”/$#+-]){NUM}\s?-?\s?(inches|inch)(?:\s+(?:long|hard|erect|cut|uncut))?(?=\s*(?:[.!,;)\n]|$|and\b|&))"#),
            |m: &Match| {
                let bare = m.nonempty(9).is_some();
                if !endowed(m, bare) || (bare && !(PHALLIC_TEXT.test(m.string) || AD.test_in(m.string, 0, 300))) {
                    return None;
                }
                length(either(m, &[1, 4, 7])?, m.nonempty(2).or(m.nonempty(5)).or(m.nonempty(8)), either(m, &[3, 6, 9])?)
            }, sh()),
        said("penis_size", &format!(r"\bme mide (?:unos |como |casi )?{NUM}\s?(cm)\b"), |m: &Match| if desired(m.string, m.start()) { None } else { length(m.group(1)?, m.nonempty(2), m.group(3)?) }, h()),
        said("penis_size", &format!(r#"\b(?:my|i have an?|i've got an?) (?:[\w-]+ ){{0,2}}?(?:cock|dick|penis|member|shaft|bwc|bbc|pp)(?: is| measures| size is|'s)? (?:about |around |roughly |almost |nearly |just under |just over |over |like |a solid |a nice |only |exactly |maybe )*{NUM}{INCH}(?![\w'"”])"#),
            |m: &Match| if THIRD.test(tail_sentence(m.string, m.start(), 80)) || desired(m.string, m.start()) || SOFT_AFTER.at(m.string, m.end()).is_some() { None } else { length(m.group(1)?, m.nonempty(2), m.group(3)?) }, h()),
        said("penis_size", &format!(r#"\b(?:i'm|im|i am|i measure|i measured|hung) (?:about |around |roughly |nearly |almost |only |just |a |an |over |like |at )*{NUM}\s?-?\s?(inches|inch|incher|cm|(?:"|”|'')(?=\s*(?:cut|uncut|hard|erect|long|thick|girth|and thick|bwc|bbc)\b))(?:\s+(?:long|hard|erect|uncut|cut))?(?![\w'"”])(?! (?:taller|shorter|away|from|tall|short|smaller|bigger|in height|wide)\b)"#),
            |m: &Match| if PHALLIC_TEXT.test(m.string) && !desired(m.string, m.start()) && !THIRD.test(tail_sentence(m.string, m.start(), 80)) && SOFT_AFTER.at(m.string, m.end()).is_none() { length(m.group(1)?, m.nonempty(2), m.group(3)?) } else { None }, h()),
        said("bra_size", &format!(r"\b(?:bra size|cup size|bra)\s*(?:is|:|=|-)?\s*(?:an? |a size |size |about |around |usually |now )*(\d{{2}}) ?{BRA_CUP}\b(?!['-])"), alone(bra), h()),
        said("bra_size", &format!(r"\b(?:i(?:'m| am|m) (?:(?:a|an|now|currently|naturally|only|barely|like|about|around|almost|technically|actually|still|natural|full) )+|i wear an? |i(?:'m| am) wearing an? |i fit (?:in|into) an? )(\d{{2}}){BRA_CUP}\b(?!['-])(?! (?:years?|yo|y/o)\b)"), bra, h()),
        said("bra_size", r"(?<![\w.$#/-])(\d{2}) ?(aa|dddd|ddd|dd|ff|gg|hh|[a-k]) ?(?:cups?|bra|tits|titties|boobs|breasts|bust)\b", mine(alone(|m: &Match| if desired(m.string, m.start()) { None } else { bra(m) })), sh()),
        said("bra_size", r"\b(?:i(?:'m| am|m) (?:an? |now an? |like an? |a natural |naturally an? )|i have |i wear an? |my )(aa|dddd|ddd|dd|ff|gg|hh|[a-k])[- ]cups?\b", |m: &Match| Some(format!("{} cup", m.first_s()?)), h()),
        said("bra_size", r"(?:^|(?<=[\n,;|/(]))\s*(\d{2})(aa|dddd|ddd|dd|ff|gg|hh|[a-e])\s*(?=[,;|/)\n]|$)", personal(alone(|m: &Match| if told(m) { None } else { bra(m) })), sh()),
        said("clothing_size", &format!(r"\bi (?:usually |normally |typically |generally |always |mostly |currently |now |can |only )?(?:wear|fit into|fit in) (?:an? |the |in |into )?(?:size |sz )?(?:{LETTER_SIZE}|(?<=size )(s|m|l|small|medium|large))\b(?![-'/])(?! (?:shoes?|feet|boots?|sneakers?)\b)"), clothing, h()),
        said("clothing_size", &format!(r"{IM} (?:a |an |usually a |normally a |typically a |now a |currently a |about a |like a )?(?:size |sz )(\d{{1,2}}(?:/\d{{1,2}})?|xxs|xs|s|m|l|xl|xxl|xxxl|[2-6]x)\b(?![-'/.])(?! (?:shoes?|feet|foot|boots?|sneakers?|in shoes|in men's|shoe)\b)|{IM} (?:an? |usually an? |typically an? )?{LETTER_SIZE}\b(?![-'/])(?=\s*(?:[,.;!)\n]|$|in\b|size\b|and\b|or\b|(?:shirts?|tops?|pants|jeans|dress|hoodies?|t-?shirts?|tees)\b))|{IM} (?:an? |usually an? |typically an? )?(small|medium|large)(?= in (?:\w+ ){{0,2}}?(?:clothes|shirts?|tops?|pants|jeans|everything|dresses|hoodies|jackets|t-shirts|tees|scrubs|men's|women's)\b| size\b)"), clothing, h()),
        said("clothing_size", r"\b(?:my (?:dress|clothing|clothes|jean|jeans|pant|pants|shirt|top) size(?: is|:)?|(?:dress|clothing|clothes|jean|pant|shirt|top) size\s*[:=-])\s*(?:an? |a size |size |usually |about |around )*(\d{1,2}(?:/\d{1,2})?|xxs|xs|s|m|l|xl|xxl|xxxl|[2-6]x|small|medium|large)\b", alone(clothing), h()),
        said("shoe_size", r"\bmy shoe size(?: is|'s)?\s*(?:is |about |around |usually |an? |size )*(?:(?:us|uk|eu|men's|mens|women's|womens|ladies) )?(\d{1,2}(?:[.,]5)?)\b(?![.,]\d|%)|\bshoe size\s*[:=-]\s*(?:(?:us|uk|eu|men's|mens|women's|womens|ladies) )?(\d{1,2}(?:[.,]5)?)\b(?![.,]\d|%)", alone(shoe), h()),
        said("shoe_size", r"\bi(?:'m| am|m| wear| take| have| got| need| buy) (?:(?:an?|a size|size|about|around|usually|like|typically|normally) )*(?:(?:us|uk|eu|men's|mens|women's|womens|ladies) )?(\d{1,2}(?:[.,]5)?)(?:w| wide)?(?: (?:us|uk|eu|men's|mens|women's|womens))? (?:in )?(?:shoes?|sneakers|boots|trainers|shoe size)\b", shoe, h()),
        said("shoe_size", r"\b(?:my|i have|i've got|i got) (?:(?:size|us|uk|eu|men's|women's) )+(\d{1,2}(?:[.,]5)?)(?:w| wide)? (?:feet|shoes?|sneakers|boots)\b", shoe, h()),
        said("starting_weight", r"(?<![\w/])(?<!\ba )(?<!\bthe )(?<!\byour )(?<!\bhis )(?<!\bher )(?<!\btheir )(?<!\bof )(?:sw|starting weight|start weight|starting wt|start wt)\s*(?:was|is|of|:|=|-|~)?\s*(?:about |around |roughly |~)?(\d{2,3}(?:[.,]\d)?)\s*(lbs?|pounds|kgs?|kilos?)?\b(?!\s*(?:mg|mcg|ml|%|cm|in\b))",
            alone(|m: &Match| starting(m, true)), sh()),
        said("starting_weight", r"(?:\bi(?:'ve| have)? |(?:^|[.!?\n]) *)(?:(?:originally|initially|first) )?(?:started (?:out )?(?:at|around|about)|went from|gone from|dropped from|came down from|got down from)\s+(?:about |around |roughly |~)?(\d{2,3}(?:[.,]\d)?)(?!\d)\s*(lbs?|pounds|kgs?|kilos?)?(?!\s*(?:mg|mcg|µg|ug|ng|iu|ml|units?|%|k\b|calories|cals?|kcal|steps|mhz|ghz|hz|bpm|mph|km|miles|dollars|usd|points|pts|ft|feet|cm|in\b|inches|days|weeks|months|years|hours|minutes|lpa|per|a day|/))(?:\s*\([^)\n]{0,20}\))?(?:\s*(?:to|->|→|down to)\s*(?:about |around |~)?\d{2,3}(?:[.,]\d)?\s*(lbs?|pounds|kgs?|kilos?)?)?",
            alone(|m: &Match| starting(m, false)), sh()),
        said("weight_lost", &format!(r"(?:\bi(?:'ve|ve| have| had)?\s+|(?:^|[.!?\n])\s*)(?:(?:already|just|finally|officially|now|since|recently|also|so far|successfully|managed to|been able to|actually|even|have|total)\s+)*(?:lost|dropped|shed)\s+(?:about |around |over |almost |nearly |roughly |like |a total of |more than |close to |just over |just under |~|exactly |another |an additional )?(\d{{1,3}}(?:[.,]\d)?)\s*\+?\s*{POUNDS}\b(?! (?:of (?:muscle|water)|in (?:a |one )?(?:day|week)))"),
            alone(lost), h()),
        said("weight_lost", r"\b(?:i'm|im|i am)\s+(?:(?:now|currently|officially|finally|already|just|about|around|over)\s+)*down\s+(?:about |around |over |almost |nearly |~)?(\d{1,3}(?:[.,]\d)?)\s*(lbs?|pounds|kgs?|kilos?)\b|(?:^|[.!?\n])\s*(?:(?:now|currently|officially)\s+)?down\s+(?<![\d.,])(\d{1,3}(?:[.,]\d)?)\s*(lbs?|pounds|kgs?|kilos?)\b|(?:^|[.!?\n(,]\s*|\b(?:i'm|im|i am|and|at|now|officially|over|almost|nearly)\s+)(?<![\d.,])(\d{1,3}(?:[.,]\d)?)\+?\s*(lbs?|pounds|kgs?|kilos?)\s+(?:down|lost)\b(?! (?:by|from|for|to)\b)",
            alone(|m: &Match| if desired(m.string, m.start()) { None } else { lost(m) }), h()),
    ]
}

pub fn listed(lowered: &[char], found: &mut Found) {
    if lowered.contains(&'/') || contains(lowered, "pronoun") {
        for m in PRONOUNED.iter(lowered) {
            let (start, end) = (m.start(), m.end());
            let tail = tail_sentence(lowered, start, 90);
            let said = PRONOUN_SAID.test(tail);
            let labeled = ((PRONOUN_LABEL.test(before(lowered, start, 3)) && PRONOUN_END.at(lowered, end).is_some()) || PRONOUN_HERE.at(lowered, end).is_some()) && owned(lowered, start);
            if !(said || labeled) || THIRD.test(tail_sentence(lowered, start, 80)) || !plain(lowered, start, end) {
                continue;
            }
            for value in pronouns(m.group(1).unwrap_or(&[])) {
                found.set("pronouns", value, start);
            }
        }
    }
    if contains(lowered, "skin") {
        for m in SKIN_TYPED.iter(lowered) {
            let (start, end) = (m.start(), m.end());
            if !plain(lowered, start, end) || THIRD.test(tail_sentence(lowered, start, 80)) {
                continue;
            }
            let run = m.first().unwrap_or(&[]);
            let values: Vec<&str> = SKIN_WORDS.iter(run).filter_map(|w| SKIN_TYPES.get(&st(w.group(1).unwrap_or(&[])).replace("acne prone", "acne-prone").replace("acneprone", "acne-prone")).copied()).collect();
            let typed = values.iter().any(|v| *v != "normal");
            for value in values {
                if value != "normal" || typed {
                    found.set("skin_type", value, start);
                }
            }
        }
    }
}

fn pronouns(set: &[char]) -> Vec<&'static str> {
    let text = st(set).replace(" pronouns", "");
    let tokens: Vec<&str> = text.split('/').map(str::trim).collect();
    if text == "any pronouns" {
        return vec!["any pronouns"];
    }
    let gendered = tokens.iter().all(|t| ["he", "she", "him", "her", "his", "hers"].contains(t));
    let feminine = tokens.iter().all(|t| ["she", "her", "hers"].contains(t));
    let masculine = tokens.iter().all(|t| ["he", "him", "his"].contains(t));
    if (gendered && !feminine && !masculine) || (tokens.iter().all(|t| ["any", "all"].contains(t)) && !set.ends_with(&chars("pronouns"))) {
        return Vec::new();
    }
    let mut values = Vec::new();
    for token in tokens {
        let value = match token {
            "she" | "her" | "hers" => "she/her",
            "he" | "him" | "his" => "he/him",
            "they" | "them" => "they/them",
            "it" | "its" => "it/its",
            "any" | "all" => "any pronouns",
            "xe" | "xem" | "xir" | "xyr" | "xey" => "xe/xem",
            "fae" | "faer" | "faeself" => "fae/faer",
            "ze" | "zie" | "zir" | "zim" | "zem" | "hir" => "ze/zir",
            "ey" | "em" | "eir" => "ey/em",
            _ => "neopronouns (other or unnamed)",
        };
        if !values.contains(&value) {
            values.push(value);
        }
    }
    values
}

pub fn force() {
    for re in [&NARRATED, &BARIATRIC, &SHOD, &PRONOUN_END, &TRANSY, &HAIRY, &SOFT_AFTER, &ENDOWED, &LISTED, &WITH, &PHALLIC_TEXT, &UNIT_IN_LINE, &STAT_LINE, &WEIGHTY, &PRONOUNED, &PRONOUN_SAID, &PRONOUN_LABEL, &PRONOUN_HERE, &SKIN_TYPED, &SKIN_WORDS] {
        LazyLock::force(re);
    }
    for t in [&EYES, &CURLS, &TONES, &EXPRESSIONS, &SKIN_TYPES] {
        LazyLock::force(t);
    }
}
