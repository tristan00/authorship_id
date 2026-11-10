use crate::rules::{alone, h, mine, said, sh};
use crate::*;
use claimcore::*;
use std::sync::LazyLock;

const LABEL_START: &str = r"(?:^(?:r/\w+:\s*)?|(?<=[\n,;|/(\[\].!])|(?<=\band)|(?<![\w$#.,'/:+-])\d{2}\s?[mf]?\b)\s*";
const LABEL_END: &str = r"(?=\s*(?:[,;|/)\]\n.!&+]|$|and\b|with\b|w/))";
const PERSONS: &str = r"(?:guy|man|dude|male|boy|daddy|dad|bear|otter|cub|chub|bro|masc|jock|stud|bull|twink|top|bottom|vers|bi|gay|straight|str8|married|married guy|husband|female|woman|girl|lady|wife|milf|here|looking|seeking|for|4)\b";
const COUNT: &str = r"(\d{1,2}(?:\.\d{1,2})?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half a)";
const SPAN: &str = r"(years?|yrs?|months?|mos?|weeks?|wks?|days?)";

static TRANS_TEXT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:trans|transgender|mtf|ftm|transfem\w*|transmasc\w*|nonbinary|non-binary|enby|dysphoria|transition\w*|t4t|tgirl|transwoman|transman|transsexual|she/her|he/him|they/them|top surgery|bottom surgery|egg_irl|deadname\w*|hrt)\b"));
static MENOPAUSE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:menopause|menopausal|perimenopause|peri|hot flashes|hysterectomy)\b"));
static HAND_TEXT: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:hand|hands|handed|write|writing|wrote|scissors|mouse|guitar|bass|bat|bats|batting|throw|throws|throwing|pitch|pitcher|golf|clubs?|bow|knife|smudge|smudges|notebook|desk|controller|thumb|arm|draw|drawing|eat|eating|fork)\b"));
static GENITAL_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:\w+\s+)?(?:pussy|cunt|cock|dick|balls|penis|vagina|kitty|snatch|ass|asshole|hole|crotch|pubes|pubic|groin|mound|taint|bush|nuts|sack|legs|pits|armpits|face|head|talker|operator|criminal|sailing|with|at|about|enough)\b"));
static UNWANTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:looking for|seeking|want|wants|need|needs|prefer\w*|into|love|loves|like|likes|must|should|you|your|you're|ur|be|bonus|plus|for)\W+(?:\w+\W+){0,2}$"));
static WELCOME_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^.!?\n]{0,40}\b(?:welcome|wanted|preferred|a plus|bonus|encouraged|only)\b"));
static AGE_LEAD: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:r/\w+:\s*)?\W{0,3}\d{2}(?:\s?[mf])?\b"));
static YOU_HEADING: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^(?:r/\w+:\s*)?|[\n|*#]|\.\s)\W*(?:about you|you|looking for|seeking|what i(?:'m| am) looking for|my type|preferences|prefs|ideal (?:match|partner)|hard pass|limits|kinks|turn ons|must haves?|bonus(?:es)?|you should be|you are)\W{0,3}[:=-]"));
static ME_HEADING: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^(?:r/\w+:\s*)?|[\n|*#]|\.\s)\W*(?:about me|me|about myself|my stats|stats|myself)\W{0,3}[:=-]"));
static MANNER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:respectful|respect|clean|drama[- ]?free|safe|honest|kind|ddf|hygienic|hygiene|std|tested|non-?judg[a-z]*|professional|private|must|expected|both ways|keep|keeping|setting|vibe|vibes)\b"));
static PERCEIVED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:think|thinks|thought|assume|assumes|assumed|believe|believes|mistake|mistakes|mistaken|treat|treats|treated|pass|passes|passing|look|looks|act|acts|pretend\w*|wonder\w*|if)\b[^.!?\n]{0,16}$"));
static LOST: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:miss|missed|cut|cutting|chop|chopped|ruin|ruined|ruining|shave|shaved|donate|donated|lost|losing|grow|growing|grew)\s+$"));
static SERVICE_AFTER: LazyLock<Re> = LazyLock::new(|| Re::new(r"[\s,]*(?:(?:\w+ ){0,3}(?:therapist|masseur|massage|service|services)\b|(?:and |& )?(?:\w+ )?(?:fun|meet|meets|meetup|encounter|encounters|nsa|hookup|hookups|play|fwb|therapist|service|services|massage|masseur|host|hosting|respectful|professional|discreet|clean|safe|honest|kind|drama|relationship|affair|friend|friends|buddy|buddies|chat|chats|sex|connection|arrangement|ltr)\b)"));

pub fn force() {
    for re in [&TRANS_TEXT, &MENOPAUSE, &HAND_TEXT, &GENITAL_AFTER, &UNWANTED, &SERVICE_AFTER, &PERCEIVED, &LOST, &YOU_HEADING, &ME_HEADING, &AGE_LEAD, &MANNER, &WELCOME_AFTER] {
        LazyLock::force(re);
    }
}

fn wanted(m: &Match) -> bool {
    desired(m.string, m.start()) || unclaimed(m.string, m.start()) || UNWANTED.test(tail_sentence(m.string, m.start(), 60)) || addressed(&m.string[..m.start()]) || WELCOME_AFTER.at(m.string, m.end()).is_some()
}

fn addressed(prefix: &[char]) -> bool {
    match YOU_HEADING.iter(prefix).last() {
        Some(you) => ME_HEADING.iter(prefix).last().map_or(true, |me| me.start() < you.start()),
        None => false,
    }
}

fn labeled(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> crate::rules::Value {
    Box::new(move |m: &Match| {
        let text = m.string;
        if wanted(m) || THIRD.test(tail_sentence(text, m.start(), 80)) {
            return None;
        }
        let first = line(text, 0);
        let stated = AGE_LEAD.at(text, 0).is_some() || FIRST.test(sentence(text, m.start(), m.end())) || MEASURED.test(line(text, m.start())) || (first.contains(&'4') && LOOKING.test(first)) || AGED.test(first);
        if stated { value(m) } else { None }
    })
}

fn sincere(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| if PERCEIVED.test(before(m.string, m.start(), 40)) { None } else { value(m) }
}

fn kept(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m: &Match| if LOST.test(before(m.string, m.start(), 12)) { None } else { value(m) }
}

fn count(word: &[char]) -> Option<f64> {
    let word = st(word);
    let number = match word.as_str() {
        "a" | "an" | "one" => 1.0,
        "half a" => 0.5,
        "two" => 2.0,
        "three" => 3.0,
        "four" => 4.0,
        "five" => 5.0,
        "six" => 6.0,
        "seven" => 7.0,
        "eight" => 8.0,
        "nine" => 9.0,
        "ten" => 10.0,
        "eleven" => 11.0,
        "twelve" => 12.0,
        _ => word.parse().ok()?,
    };
    Some(number)
}

fn months(m: &Match) -> Option<String> {
    if !TRANS_TEXT.test(m.string) || MENOPAUSE.test(m.string) {
        return None;
    }
    let amount = count(m.group(1)?)?;
    let unit = st(m.group(2)?);
    let total = match unit.chars().next()? {
        'y' => amount * 12.0,
        'm' => amount,
        'w' => amount / 4.345,
        _ => amount / 30.4,
    };
    if (0.0..=600.0).contains(&total) { Some(format!("{}", total.round() as i64)) } else { None }
}

fn discreet(m: &Match) -> Option<String> {
    if SERVICE_AFTER.at(m.string, m.end()).is_some() || MANNER.test(sentence(m.string, m.start(), m.end())) { None } else { Some("discreet".to_string()) }
}

fn hairiness(m: &Match) -> Option<String> {
    let degree = m.group(1).map(st).unwrap_or_default();
    let word = st(m.group(2)?);
    let plus = m.nonempty(3).is_some();
    let value = match word.as_str() {
        "hairy" if plus || ["very", "pretty", "really", "quite", "super", "extremely"].contains(&degree.as_str()) => "very hairy",
        "hairy" if ["slightly", "moderately", "fairly", "a bit", "kinda", "somewhat", "relatively", "lightly", "naturally"].contains(&degree.as_str()) => "moderately hairy",
        "hairy" => "hairy",
        "trimmed" | "manscaped" | "groomed" => "trimmed",
        _ => "smooth / shaved",
    };
    if GENITAL_AFTER.at(m.string, m.end()).is_some() { None } else { Some(value.to_string()) }
}

fn beard(m: &Match) -> Option<String> {
    let size = m.group(1).map(st).unwrap_or_default();
    let value = if ["full", "big", "thick", "long", "huge", "bushy", "massive", "wizard"].iter().any(|w| size.starts_with(w)) {
        "full beard"
    } else if ["short", "trimmed", "well", "groomed", "neat", "light", "scruffy", "small", "close", "faded"].iter().any(|w| size.starts_with(w)) {
        "short / trimmed beard"
    } else {
        "beard (unspecified)"
    };
    Some(value.to_string())
}

fn face(m: &Match) -> Option<String> {
    let word = st(m.first()?);
    let value = if word.starts_with("goatee") || word.starts_with("van") {
        "goatee"
    } else if word.contains("stache") || word.starts_with("tache") {
        "mustache"
    } else if word.starts_with("stubble") || word.starts_with("scruff") || word.starts_with("five") {
        "stubble"
    } else if word.starts_with("clean") || word.starts_with("no ") {
        "clean shaven"
    } else if word.starts_with("bearded") || word == "beard" {
        "beard (unspecified)"
    } else {
        return beard(m);
    };
    Some(value.to_string())
}

fn length(m: &Match) -> Option<String> {
    let word = st(m.first()?);
    let value = if word.starts_with("long") {
        "long"
    } else if word.starts_with("short") || word.starts_with("pixie") {
        "short"
    } else if word.starts_with("buzz") {
        "buzzed"
    } else if word.starts_with("shoulder") || word.starts_with("medium") || word.starts_with("med") || word.starts_with("chin") || word.starts_with("neck") {
        "medium / shoulder-length"
    } else if word.starts_with("waist") || word.starts_with("hip") || word.starts_with("butt") || word.starts_with("bum") || word.starts_with("tailbone") {
        "waist / hip length"
    } else {
        return None;
    };
    Some(value.to_string())
}

fn handed(m: &Match) -> Option<String> {
    let word = st(m.first()?);
    let value = if word.contains("ambi") || word.contains("cross") || word.contains("mixed") {
        "ambidextrous"
    } else if word.contains("left") || word.contains("southpaw") {
        "left-handed"
    } else {
        "right-handed"
    };
    if (word.contains("lefty") || word.contains("leftie") || word.contains("righty") || word.contains("southpaw")) && !HAND_TEXT.test(sentence(m.string, m.start(), m.end())) {
        return None;
    }
    Some(value.to_string())
}

fn norwood(m: &Match) -> Option<String> {
    let stage = st(m.first()?);
    let number = match stage.as_str() {
        "i" => 1.0,
        "ii" => 2.0,
        "iii" => 3.0,
        "iv" => 4.0,
        "v" => 5.0,
        "vi" => 6.0,
        "vii" => 7.0,
        _ => stage.parse().ok()?,
    };
    if (1.0..=7.0).contains(&number) { Some(format!("{number}")) } else { None }
}

fn undertone(m: &Match) -> Option<String> {
    m.first_s()
}

fn sex(m: &Match) -> Option<String> {
    let word = st(m.first()?);
    if contains(&m.string[m.start()..(m.end() + 12).min(m.string.len())], " to afab") || contains(&m.string[m.start()..(m.end() + 12).min(m.string.len())], " to amab") {
        return None;
    }
    let value = if word.contains("intersex") {
        "intersex"
    } else if word.contains("amab") || word.contains("male") && !word.contains("female") {
        "amab"
    } else {
        "afab"
    };
    Some(value.to_string())
}

fn cis(m: &Match) -> Option<String> {
    let value = match m.group(1).map(st).as_deref() {
        Some("woman" | "girl" | "female" | "lady" | "f" | "gal") => "cis woman",
        Some("man" | "guy" | "male" | "dude" | "boy" | "m" | "bloke") => "cis man",
        _ => "cis (gender unstated)",
    };
    Some(value.to_string())
}

pub fn rules() -> Vec<Rule> {
    let mut all = Vec::new();
    all.extend(identity());
    all.extend(hair());
    all.extend(body());
    all.extend(numbers());
    all
}

fn identity() -> Vec<Rule> {
    vec![
        said("assigned_sex_at_birth", &format!(r"{IM} (?:(?:also|just|still|actually|technically|biologically|a|an) ){{0,3}}(amab|afab|intersex)\b(?![-'])(?! (?:people|folks|persons|community)\b)"), sex, h()),
        said("assigned_sex_at_birth", r"\bi (?:was|am|'m) (?:also )?(amab|afab|assigned (?:male|female) at birth)\b|\bas an? (amab|afab|intersex) (?:person|woman|man|girl|guy|individual|human|enby|nonbinary|non-binary|trans|transmasc|transfem)\b", sex, h()),
        said("assigned_sex_at_birth", r"(?:^(?:r/\w+:\s*)?|(?<=[\n(\[|/,]))\s*(?:\d{2}\s*,?\s*)?(?:(?:nb|enby|nonbinary|non-binary|genderfluid|agender|transmasc|transfem|trans|demigirl|demiboy|bigender) )?\(?(?<!a[fm]ab/)(amab|afab)\b(?! to\b)(?!\s*/\s*a[fm]ab)(?=\s*(?:[,;|/)\]\n.!]|$|(?:nb|enby|nonbinary|non-binary|genderfluid|agender|transmasc|transfem|trans|woman|man|girl|guy|person|lesbian|here|cis|demigirl|demiboy|bigender)\b))",
            alone(mine(sex)), sh()),
        said("gender", &format!(r"{IM} (?:(?:also|just|still|actually|openly|proudly|a|an) ){{0,3}}(?:trans|transgender)\b(?![-'/])(?! (?:\w+ )?(?:woman|women|girl|girls|female|lady|gal|man|men|guy|guys|boy|male|dude|fem\w*|masc\w*|people|rights|folks|kids?|community|friends?|ally|allies|issues?|inclusive|healthcare|panic|athletes?|stuff|content|porn|ftm|mtf|f2m|m2f|nb|enby|nonbinary|non-binary|lesbian|gay)\b)"), sincere(fixed("trans (unspecified)")), h()),
        said("gender", r"(?:^(?:r/\w+:\s*)?|[.!?\n] *)being (?:trans|transgender)\b(?![-'/])(?! (?:\w+ )?(?:woman|girl|man|guy|people|is|isn't)\b)|\bas an? (?:trans|transgender) (?:person|individual|human|adult|teen|kid|enby)\b", alone(fixed("trans (unspecified)")), h()),
        said("gender", &format!(r"{IM} (?:(?:also|just|still|actually|a|an) ){{0,2}}transsexual\b(?! (?:people|woman|man|women|men)\b)|\bas an? transsexual\b(?! (?:people|woman|man)\b)"), fixed("transsexual"), h()),
        said("gender", &format!(r"(?:{IM}|(?:^(?:r/\w+:\s*)?|[.!?\n] *)being) (?:an? )?(?:\d{{2}} ?(?:yo |y/o |year old )?)?(?:(?:white|black|straight|gay|bi|lesbian|young|old|het|hetero|middle aged) )?(?:cis|cisgender|cisgendered)[- ]?(?:het(?:ero)?(?:sexual)?[- ])?(woman|girl|female|lady|gal|man|guy|male|dude|boy|bloke)\b(?!'s| (?:people|perspective)\b)"), sincere(cis), h()),
        said("gender", &format!(r"{IM} (?:(?:a|also|just|100%|fully|totally) )*(?:cis|cisgender|cishet|cis het|cis-het)\b(?![-'])(?! (?:\w+ )?(?:woman|women|girl|female|lady|gal|man|men|guy|male|dude|boy|people|folks|f|m)\b)"), sincere(cis), h()),
        said("gender", r"(?:^(?:r/\w+:\s*)?|(?<=[\n(\[|/,]))\s*(?:\d{2}\s*,?\s*)?(?:cis|cisgender)[- ]?(f|m|female|male)\b(?=\s*(?:[,;|/)\]\n.!]|$))", alone(mine(cis)), sh()),
        said("gender", &format!(r"{IM} (?:(?:probably|definitely|still|just|totally) )?an egg(?=\s*(?:[.!,)]|$))"), |m: &Match| if TRANS_TEXT.test(m.string) { Some("egg".to_string()) } else { None }, h()),
        said("outness", &format!(r"{IM} (?:(?:also|still|a|an|totally|very|strictly|kinda|pretty|always|100%) )*(?:on the )?(dl|d/l|down low)\b(?! (?:with|about|on)\b)"), fixed("down low (dl)"), h()),
        said("outness", &format!(r"{LABEL_START}(?:(?:married|straight|str8|bi|gay|masc|white|black|curious|bicurious|bi-curious|discreet|closeted) )*(?<![a-z]/)(dl|down low)(?:,? (?:\w+ )?{PERSONS}|{LABEL_END})"), labeled(|m: &Match| if m.start() > 0 && m.string[m.start() - 1] == '/' { None } else { Some("down low (dl)".to_string()) }), sh()),
        said("outness", &format!(r"{IM} (?:(?:very|extremely|always|super|also|totally|100%|pretty|a) )*discre(?:et|te)\b(?![-'])"), discreet, h()),
        said("outness", r"^(?:r/\w+:\s*)?\W*(?:\d{2}\s*,?\s*[mf]?\W*)?(?:(?:very|married|bi|str8|straight|curious) )*discre(?:et|te) (?:(?:\w+) ){0,2}?(?:male|guy|man|dude|bi|bisexual|daddy|dad|bear|top|bottom|married|masc|husband)\b(?! (?:therapist|masseur|massage|service)\b)", labeled(fixed("discreet")), TAGGED),
        said("outness", &format!(r"{IM} (?:(?:still|also|very|completely|totally|deeply|a|kinda|mostly|basically|pretty|currently) )*(?:closeted|in the closet|not out (?:yet|even|to (?:almost |hardly |really )?(?:anyone|anybody|my (?:family|parents|friends|mom|dad|mum|wife|husband)|family|friends|irl)))\b(?![-'])"), fixed("closeted / not out"), h()),
        said("outness", &format!(r"{LABEL_START}(?:still )?closeted (?:\w+ )?(?:bi|bisexual|gay|trans|lesbian|guy|man|male|married|woman|girl|queer|pan|enby|nonbinary|sissy|femboy|cd|crossdresser|sub|bottom|top|husband|dad)\b"), labeled(fixed("closeted / not out")), sh()),
        said("outness", &format!(r"{LABEL_START}(?:(?:very|extremely|always|100%|super) )?discre(?:et|te)(?:{LABEL_END}|,? (?:\w+ )?{PERSONS})"), labeled(discreet), sh()),
        said("outness", &format!(r"{IM} (?:(?:also|now|fully|completely|proudly|a) )*openly (?:gay|bi|bisexual|lesbian|trans|transgender|queer|pan|pansexual|nonbinary|non-binary)\b|\bi(?:'m| am) (?:now )?out to (?:everyone|everybody|my (?:whole )?(?:family|parents|friends|mom|dad|mum)|friends and family)\b"), fixed("out / openly"), h()),
        said("handedness", &format!(r"{IM} (?:(?:also|naturally|actually|a|an|fully|totally|completely|mostly|pretty much|very|strongly) )*(left[- ]?handed|right[- ]?handed|ambidextrous|cross[- ]dominant|mixed[- ]handed|lefty|leftie|righty|southpaw|left[- ]hand(?:ed)? dominant|right[- ]hand(?:ed)? dominant)\b"), handed, h()),
        said("handedness", r"\bas an? (?:fellow )?(left[- ]?handed|right[- ]?handed|ambidextrous|lefty|leftie|southpaw)\b|\bfellow (left[- ]?handed|lefty|leftie|southpaw)\b|\bmy dominant (?:hand|side) is (?:my )?(left|right)\b", alone(handed), h()),
    ]
}

fn hair() -> Vec<Rule> {
    let look = r"(?:long|short|thick|thin|fine|curly|wavy|straight|dark|light|black|brown|blonde?|red|ginger|auburn|grey|gray|silver|white|dirty blonde?|messy|natural|naturally|very|super|really|kinda|pretty|and|layered|frizzy|shaggy|coarse|soft)";
    let lengths = r"(long|short|shoulder[- ]length|medium[- ]length|med length|chin[- ]length|neck[- ]length|waist[- ]length|hip[- ]length|butt[- ]length|bum[- ]length|tailbone[- ]length|buzzed|buzz[- ]?cut|pixie(?: cut)?)";
    vec![
        said("hair_length", &format!(r"\b(?:i have|i've got|i got|i also have|i still have|i currently have|i now have|my) (?:(?:{look}),? ){{0,3}}{lengths}(?:,? (?:{look}))* hair\b(?! (?:days?|cut|cuts|style|styles|ties?|dye|products?|routine)\b)"), alone(kept(length)), h()),
        said("hair_length", &format!(r"\bmy hair(?: is|'s| is currently| is now) (?:(?:very|super|really|pretty|quite|kinda|fairly|naturally|currently|now|still|also) )*{lengths}\b(?! (?:on|in|at|for)\b)"), kept(length), h()),
        said("hair_length", &format!(r"{IM} (?:(?:a|an|also|still|currently) )*(long|short)[- ]haired\b"), length, h()),
        said("hair_length", &format!(r"(?:^(?:r/\w+:\s*)?|(?<=[\n,;|/(])|(?<=\band))\s*(?:(?:{look}),? ){{0,3}}{lengths}(?:,? (?:{look}))* hair\b"), labeled(length), sh()),
        said("hair_length", r"\bi (?:have|'ve got|got|rock|sport) (?:a )?shaved head\b|\bi (?:always |usually |now |also |still )?shave my head\b|\bmy head is shaved\b", alone(fixed("shaved head")), h()),
        said("hair_loss", &format!(r"{IM} (?:(?:also|completely|totally|fully|now|pretty much|basically|just|a|naturally|already|mostly|nearly|almost) )*bald\b(?![-'])(?! (?:spot|spots|patch|patches|tires?|eagle|pussy|cock|dick|down there)\b)"), fixed("bald"), h()),
        said("hair_loss", r"(?<!\bno )(?<!\bnão )\b(?:sou|soy|estou|estoy) (?:\w+ )?(?:careca|calvo|calva|pelón|pelona)\b", fixed("bald"), h()),
        said("hair_loss", &format!(r"{IM} (?:(?:also|slowly|already|currently|now|just|a|definitely|rapidly|quickly|prematurely|starting to go|starting) )*(?:balding|going bald)\b|\bi (?:have|got|'ve got) (?:male pattern baldness|mpb)\b"), fixed("balding"), h()),
        said("hair_loss", &format!(r"\bmy hairline (?:is|has been|started|has started|'s|began|keeps) (?:\w+ ){{0,2}}?receding\b|\bi (?:have|'ve got|got) (?:an? )?(?:(?:slightly|slowly|bit of a|bit|mild|small) )*receding hairline\b|{IM} (?:(?:slowly|already|also) )*receding\b"), fixed("receding hairline"), h()),
        said("hair_loss", &format!(r"\bmy hair (?:is|has been|started|has started|'s|began|keeps) (?:(?:slowly|really|already|also|definitely|noticeably|starting|now) )*(?:thinning|falling out)\b|{IM} (?:(?:slowly|already|also|definitely|rapidly|starting to|now) )*(?:losing my hair|thinning)\b(?! (?:out|it)\b)|\bi (?:have|'ve got|got) (?:(?:slightly|really|very|some) )*thinning hair\b"), fixed("thinning"), h()),
        said("hair_loss", r"\bi (?:still )?(?:have|'ve got|got) (?:a )?full head of hair\b|\bi still have (?:all )?(?:of )?my hair\b|\bno hair loss (?:for me|here)\b", fixed("full head of hair"), h()),
        said("facial_hair", r"\bi (?:have|'ve got|got|also have|still have|currently have|now have|sport|rock|'m rocking|'m sporting|'m growing|keep) (?:an? |my )?(?:(full|big|thick|long|huge|bushy|massive|wizard|short|trimmed|well[- ]kept|groomed|neat|light|scruffy|small|close|faded)(?: and \w+)?,? )?(?:(?:red|black|brown|dark|grey|gray|white|ginger|blonde?|salt and pepper|nice|decent|patchy|real) )?beard\b(?! (?:oil|balm|trimmer|products?|growth)\b)", alone(beard), h()),
        said("facial_hair", r"\bi (?:have|'ve got|got|also have|still have|sport|rock|'m rocking|'m sporting|'m growing|keep) (?:an? |some )?(?:(?:little|small|thin|thick|light|neat|short|trimmed|big|nice|perpetual|permanent|bit of|bit of a) )*(goatee|van ?dyke|mustache|moustache|stache|stubble|scruff|five o'?clock shadow)\b", alone(face), h()),
        said("facial_hair", &format!(r"{IM} (?:(?:also|always|usually|currently|now|a|an) )*(clean[- ]shaven|clean[- ]shaved|bearded)\b(?! (?:men|guys|people)\b)"), face, h()),
        said("facial_hair", &format!(r"{LABEL_START}(?:(?:very|nicely|well|freshly) )?(bearded|clean[- ]shaven|clean[- ]shaved|goatee|full beard|short beard|trimmed beard|stubble|mustache|moustache)(?:,? (?:\w+ )?{PERSONS}|{LABEL_END})"), labeled(face), sh()),
    ]
}

fn body() -> Vec<Rule> {
    let degree = r"(?:(very|pretty|really|quite|super|extremely|slightly|moderately|fairly|a bit|kinda|somewhat|relatively|lightly|naturally|also|totally|completely|fully|freshly) )?";
    vec![
        said("body_hair", &format!(r"{IM} (?:(?:also|still|a|an) )*{degree}(hairy|smooth|shaved|shaven|hairless|trimmed|manscaped)\b(\++)?(?![-'])"), hairiness, h()),
        said("body_hair", &format!(r"\bi (?:have|'ve got|got) (?:an? )?{degree}(hairy)(\++)? (?:chest|body|arms|legs|back|torso|bod)\b"), alone(hairiness), h()),
        said("body_hair", &format!(r"{LABEL_START}{degree}(hairy|hairless|manscaped)(\++)?(?:,? (?:\w+ )?(?:{PERSONS}|chest|body|bod|dadbod|dad bod|chested)|{LABEL_END})"), labeled(hairiness), sh()),
        said("body_hair", &format!(r"{LABEL_START}{degree}(smooth)(\++)? (?:body|bod|chest|all over|everywhere)\b"), labeled(hairiness), sh()),
        said("body_modifications", r"\bi (?:have|'ve got|got|also have|still have|now have|have got) (?:(?:a|an|some|few|a few|several|many|lots of|a lot of|a couple|a couple of|two|three|\d+|multiple|tons of|plenty of|small|little|big|visible|full|matching|more|other|my|first|new|arm|leg|back|chest|sleeve|wrist|neck|hand|finger|ankle|rib|forearm|thigh|shoulder) )*(?:tattoos?|tats|sleeve tattoos?)\b(?! (?:artist|artists|shop|parlou?r|appointment|gun|idea|ideas|session|removal|consultation|done|planned)\b)", alone(fixed("tattoos")), h()),
        said("body_modifications", &format!(r"{IM} (?:(?:heavily|very|fully|also|quite|pretty|covered in|a|an|lightly|both|partially) )*(?:tattooed|tatted|inked)\b(?! (?:people|guys|girls|women|men|ones)\b)"), fixed("tattoos"), h()),
        said("body_modifications", &format!(r"{LABEL_START}(?:(?:heavily|very|fully|lightly) )?(?:tattooed|tatted(?: up)?|inked)(?:,? (?:\w+ )?{PERSONS}|{LABEL_END})"), labeled(fixed("tattoos")), sh()),
        said("body_modifications", r"\bi (?:have|'ve got|got|also have|still have) (?:(?:a|an|some|few|a few|several|multiple|\d+|my|both|two|three|lots of|many) )*(?:(?:nose|septum|tongue|nipple|nipples|belly|belly button|navel|lip|eyebrow|ear|ears|industrial|helix|tragus|daith|conch|cartilage|dermal|genital|facial|body) )?(?:piercings?|pierced (?:ears|nose|tongue|nipples|septum|lip|belly button|navel|eyebrow))\b|\bmy (?:ears?|nose|tongue|nipples?|septum|lip|eyebrow|belly button|navel) (?:is|are) pierced\b|\bi (?:have|got) my (?:ears|nose|tongue|nipples|septum|lip|belly button|navel) pierced\b", alone(fixed("piercings")), h()),
        said("body_modifications", r"\bi (?:have|'ve got|got) (?:(?:\w+) )?(?:gauges|gauged ears|stretched (?:ears|lobes))\b|\bmy (?:ears|lobes) (?:are )?(?:gauged|stretched)\b", alone(fixed("stretched ears / gauges")), h()),
        said("body_modifications", r"\bi (?:have|'ve got|got) a split tongue\b|\bmy split tongue\b", alone(fixed("split tongue")), h()),
        said("body_type", &format!(r"{IM} (?:(?:also|just|a|an|kinda|pretty|naturally|very) )*(hwp|height[- ]weight proportionate|pawg|slim[- ]?thic+k?)\b"), |m: &Match| {
            let word = st(m.first()?);
            Some(if word.starts_with("pawg") { "pawg" } else if word.starts_with("slim") { "slim thick" } else { "hwp (height-weight proportionate)" }.to_string())
        }, h()),
        said("body_type", &format!(r"{LABEL_START}(hwp|pawg|slim[- ]?thic+k?)(?:,? (?:\w+ )?{PERSONS}|{LABEL_END})"), labeled(|m: &Match| {
            if !MEASURED.test(line(m.string, m.start())) {
                return None;
            }
            let word = st(m.first()?);
            Some(if word.starts_with("pawg") { "pawg" } else if word.starts_with("slim") { "slim thick" } else { "hwp (height-weight proportionate)" }.to_string())
        }), sh()),
        said("body_type", &format!(r"{IM} (?:(?:also|just|kind of|kinda|pretty|a) )*(?:a )?(?:big|bigger|heavy[- ]?set) (?:guy|girl|man|dude|fella|bloke|lady|gal|woman|boy)\b(?! (?:fan|friend|deal|believer|supporter)\b)"), fixed("big / heavyset"), h()),
        said("skin_undertone", &format!(r"{IM} (?:an? )?(?:(?:very |super )?(?:fair|light|light-medium|light medium|medium|medium-tan|tan|deep|dark|olive|muted|true)[- ,/]+){{1,3}}(warm|cool|neutral)\b"), undertone, h()),
        said("skin_undertone", &format!(r"{IM} (?:an? )?(warm|cool|neutral)(?:[- ](?:leaning|toned|undertoned))?[- ](?:toned|olive|undertone|undertones|undertoned|skinned)\b|\bi (?:have|'ve got|got) (?:an? )?(?:(?:very|slightly|more of a|mostly|definitely|pretty) )*(warm|cool|neutral)[- ]?(?:undertones?|under tones?)\b|\bmy (?:skin(?:'s)? )?undertones? (?:is|are|'s|seems? to be|tends? to be) (?:(?:more|very|definitely|probably|mostly|pretty) )*(warm|cool|neutral)\b"), undertone, h()),
    ]
}

fn numbers() -> Vec<Rule> {
    vec![
        said("hrt_time", &format!(r"(?:^(?:r/\w+:\s*)?|[.!?\n,(|] *|\b(?:i'm|im|i am|been|i've been|ive been|now|just|and|but) )(?:about |almost |over |nearly |just |only |roughly |around )?(?<!years )(?<!years, )(?<!year )(?<!year, )(?<!yrs )(?<!yrs, )(?<!years and )(?<!year and )(?<![\d.]){COUNT} {SPAN} (?:on |of |into )?(?:hrt|estrogen|estradiol|testosterone)\b|(?:^(?:r/\w+:\s*)?|[.!?\n,(|] *|\b(?:i'm|im|i am|been|i've been|ive been|now|just|and|but) )(?:about |almost |over |nearly |just |only |roughly |around )?(?<![\d.]){COUNT} {SPAN} (?:on|into) (?:e|t)\b(?![-'])"), alone(months), sh()),
        said("hrt_time", &format!(r"\bi(?:'ve| have)? been on (?:hrt|e|t|estrogen|estradiol|testosterone|hormones) (?:for )?(?:about |almost |over |nearly |just |only |roughly |around )?{COUNT} {SPAN}\b"), months, h()),
        said("hrt_start_year", r"\bi(?:'ve| have)? (?:been on|started|began|first started) (?:hrt|t|e|estrogen|estradiol|testosterone|hormones) (?:in|on|since|back in) (?:(?:jan\w*|feb\w*|mar\w*|apr\w*|may|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*|spring|summer|fall|autumn|winter|late|early|mid|the end of|the start of|the beginning of)[ ,]+)*(19[89]\d|20[0-2]\d)\b",
            |m: &Match| if TRANS_TEXT.test(m.string) && !MENOPAUSE.test(m.string) { m.first_s() } else { None }, h()),
        said("iq", r"\bmy (?:tested |measured |actual |real |full[- ]scale |last |official )?iq (?:score )?(?:is|was|=|:|tested at|came (?:back|out) (?:at|as)) ?(?:about |around |like |roughly |apparently |only |a |an |just )*(\d{2,3})\b(?![\d%]|[.,]\d)|\bi (?:have|got|scored|tested at|tested|have a|got a) (?:an? )?(?:tested |measured |official )?iq (?:of |score of |at )(?:about |around |like )?(\d{2,3})\b(?![\d%]|[.,]\d)|\bi (?:have|got|scored) (?:an? )?(\d{2,3}) iq\b|\bi(?:'m| am) (?:a |an )?(\d{2,3}) iq\b", |m: &Match| {
            let score = either(m, &[1, 2, 3, 4])?;
            iq_of(score)
        }, h()),
        said("norwood_stage", r"\b(?:i'm|im|i am|i'd say i'm|i was|i'm currently|i am currently|currently|my hairline is|my hair is|i'm at|i am at|sitting at) (?:(?:about|around|a|an|like|almost|probably|maybe|currently|at|solid|still|already|now|basically|roughly|on) )*(?:norwood|nw) ?(?:stage |scale )?([1-7](?:\.5)?|i{1,3}|iv|vi{0,2})\b(?![-/.]\d| ?(?:-|to|or) ?\d)", alone(norwood), h()),
    ]
}

fn iq_of(score: &[char]) -> Option<String> {
    let score: i64 = st(score).parse().ok()?;
    if (60..=199).contains(&score) { Some(score.to_string()) } else { None }
}
