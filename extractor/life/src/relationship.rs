use crate::shared::*;
use claimcore::*;

pub const FOND: &str = concat!(
    r"(?:sweet|lovely|loving|beautiful|gorgeous|pretty|hot|sexy|naughty|amazing|wonderful|awesome|dear|dearest|darling|current|new|supportive|incredible|poor|long[- ]?term|live[- ]in|beloved|own|big|",
    r"little|cute|cuck(?:old)?|kinky|horny|slutty|shy|petite|busty|curvy|thick|chubby|young|younger|older|patient|perfect|handsome|lucky|silly|sleepy|grumpy|crazy|lazy|jealous|loyal|faithful|now|second|2nd|third|3rd|",
    r"\d{2} ?[mf]?|\(\d{2} ?[mf]?\)|\d+[- ]?(?:months?|years?|yrs?|weeks?)|\d{2}[- ]?(?:yo|y/o|years?[- ]old)|(?:\w+[- ])?year[- ]old)"
);
pub const SPOUSE: &str = r"(wife|husband|hubby|hubs|wifey|spouse|wifes|husbands|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)";
pub const BARE: &str = r"(wife|wifey|hubby|husband|fianc[ée]e?|spouse|missus)";
pub const OPENING: &str = r"(?:^\W*|[\n.!?]\s*|[\]\)]\s*|[-|:]\s+)";
pub const TAIL: &str = concat!(
    r"(?! (?:to (?:the|this|that|it|my (?:job|work|career))|by|about|in terms|aback|care|seriously|advantage|in (?:a|an|the|this|that|it|some|conversation|discussion|debate|activities|activity|work)|handedly|digit|file|minded|out|away|back|off|over|up|",
    r"with (?:the|this|that|it|work))\b)"
);
pub const KIN: &str = r"(?:brother|sister|son|daughter|dad|mom|mum|father|mother|cousin|friend|friends|uncle|aunt|boss|neighbou?r|roommate|buddy|bro|sis|ex|former|future|dream|next|last|previous|first|late|dead|imaginary|fake|virtual|ai|old|then|best|own)";
pub const FOLLOW: &str = concat!(
    r"(?=\s*(?:[.,!;:)(/\n]|$|\d|[mf]\s?\d{2}\b|(?:and|but|with|for|since|in|here|now|again|too|af|m|f|male|female|man|woman|guy|girl|gal|lady|dude|mom|mum|mother|dad|father|parent|bbw|milf|dilf|couple)\b",
    r"|\w+ (?:with|and|from|in|looking|seeking|here|male|female|man|woman|guy|girl|mom|dad)\b))"
);
pub const SOLO_AD: &str = r"^\W*(?:(?:\d{2}\s*[\]\)]?\s*)?[\[\(]?\s*(?:m|f|t|nb|tm|tf|mtf|ftm)\s*4\s*(?:[mfatr]|me|nb)\w*\s*[\]\)]?|\d{2}\s*(?:[mf]|yo|y/o|yrs?|years? old)\b|[mf]\s*\d{2}\b)";
pub const COUPLE_ADS: [&str; 3] = [
    r"^\W*(?:(?:\d{2}\s*(?:[mf]\s*)?(?:/\s*\d{2}\s*(?:[mf]\s*)?)?)?[\[\(]?\s*(?:mf|fm)\s*4\s*[mfat]\w*|(?:\d{2}\s*)?[\[\(]?\s*mf\s*\d{2}\b|(?:(?!the |a |this |that |every |each |any |no )\w+ )?couple (?:looking|seeking|here|from|in|\d{2})\b)",
    r"^\W*[\[\(]?(?:\d{2}\s*[mf]|[mf]\s*\d{2})\s*[/&+,]?\s*(?:\d{2}\s*[mf]|[mf]\s*\d{2})\b|^\W*(?:(?!the |a |this |that |every |each |any |no )\w+ )?couple (?:we|our)\b|^[^\n]*\b(?:mf|fm|m/f|f/m) couple (?:looking|seeking|here|from|in)\b",
    r"(?:couple(?<=\bcouple) here|we(?<=\bwe)(?:'re| are) an? (?:\w+ )?couple)\b(?! (?:of|days?|weeks?|months?|years?|hours?|minutes?|games?|more|points?|times?|steps?|levels?)\b)",
];

regex!(OTHERS, r"(?:^|\W)(?:your|ur|her|his|their|a|an|some|someone's|whose|ex|future|dream|trophy|of|another|every|any|no|perfect|ideal|ex-|good|loyal|cuck|friends?|friend's)\W*$");
regex!(YOU, r"\byou\b");
regex!(ATTACHED, r"\b(?:married|wife|husband|hubby|my bf|my gf|my boyfriend|my girlfriend|my partner|couple|taken|engaged|with (?:a |my )?(?:gf|bf|girlfriend|boyfriend))\b");
regex!(HEAD, r"\s*[^\n]*(?:\n\s*[^\n]*)?");
regex!(SOLICIT, r"\b(?:looking for|seeking|searching for|in search of)\b");
regex!(FRIENDLY, r"\b(?:friends?|friendship|frds?|bros?|buddy|buddies|pals?|penpals?|talk|chat|chatting|game|gaming|vent)\b");
regex!(UNPARTNERED, r"\b(?:wife|husband|hubby|my bf|my gf|my boyfriend|my girlfriend|my partner|engaged|fianc[ée]e?)\b");
regex!(NEVER_LEAD, r"(?:^|[.!?\n,;(]|\band|\bbut|\bi|\bi've|\bi have|\bi'm|\bim|\bi am|\bstill|\b(?:and|but) have)\s*$");
regex!(BREAK_LEAD, r"(?:^|[.!?\n]\s*)(?:i )?(?:just |recently |finally )?$");
regex!(STATUS_LEAD, r"(?:\b(?:as|being|i'm|im|i am|just|a fellow|as a fellow) an? |^\W*|[\n.!?]\s*|\b\d{2}\s*[mf]?\s*,?\s*|[\]\)]\s*)(?:(?!not|un|never|ex|former|soon|my|your|his|her|their|the|every|each|any|married)[\w-]+ ){0,2}$");
regex!(SPEAKER, r"\b(?:i|i'm|im|i've)\b");
regex!(OPENER, r"\bop(?:'s)?\b");
regex!(HUSBAND_WORD, r"\b(?:husband|hubby|hubs)\b");
regex!(WIFE_WORD, r"\b(?:wife|wifey|missus|mrs)\b");
regex!(NEGATION, r"\b(?:not|never|no)\b|n't\b");
regex!(UNMARRIED, r"(?:not |un)married");

static FOREIGN_SPOUSES: &Tab = &[
    ("esposa", MARRIED), ("mujer", MARRIED), ("marido", MARRIED), ("esposo", MARRIED), ("femme", MARRIED), ("mari", MARRIED), ("frau", MARRIED), ("mann", MARRIED), ("kone", MARRIED), ("mand", MARRIED),
    ("vrouw", MARRIED), ("man", MARRIED), ("żona", MARRIED), ("moglie", MARRIED), ("marito", MARRIED), ("hustru", MARRIED), ("ehemann", MARRIED), ("ehefrau", MARRIED), ("gatte", MARRIED), ("gattin", MARRIED), ("époux", MARRIED),
    ("épouse", MARRIED), ("echtgenoot", MARRIED), ("echtgenote", MARRIED),
    ("prometida", ENGAGED), ("prometido", ENGAGED), ("noiva", ENGAGED), ("noivo", ENGAGED), ("verlobte", ENGAGED), ("verlobter", ENGAGED), ("verloofde", ENGAGED), ("fiancé", ENGAGED), ("fiancée", ENGAGED),
    ("novia", DATING), ("novio", DATING), ("namorada", DATING), ("namorado", DATING), ("copine", DATING), ("copain", DATING), ("freundin", DATING), ("freund", DATING), ("kæreste", DATING), ("kjæreste", DATING),
    ("vriendin", DATING), ("vriend", DATING), ("partner", DATING), ("partnerin", DATING), ("pareja", DATING), ("compagnon", DATING), ("compagne", DATING), ("conjoint", DATING),
    ("conjointe", DATING), ("partenaire", DATING), ("compagno", DATING), ("compagna", DATING), ("ragazza", DATING), ("ragazzo", DATING), ("fidanzata", DATING), ("fidanzato", DATING), ("lebensgefährte", DATING),
    ("lebensgefährtin", DATING), ("sambo", DATING), ("flickvän", DATING), ("pojkvän", DATING),
];

static FOREIGN_STATUSES: &Tab = &[
    ("casad", MARRIED), ("solte", "single"), ("divor", "divorced"), ("compr", ENGAGED), ("noiv", ENGAGED), ("noiva", ENGAGED), ("noivo", ENGAGED), ("verhe", MARRIED), ("singl", "single"), ("ledig", "single"), ("gesch", "divorced"), ("verlo", ENGAGED),
    ("verge", DATING), ("marié", MARRIED), ("célib", "single"), ("fianc", ENGAGED), ("en co", DATING), ("sposa", MARRIED), ("fidan", DATING), ("żonat", MARRIED), ("zamęż", MARRIED), ("mężat", MARRIED),
    ("rozwi", "divorced"), ("zaręc", ENGAGED), ("w zwi", DATING), ("getro", MARRIED), ("vrijg", "single"), ("женат", MARRIED), ("замуж", MARRIED), ("холос", "single"), ("разве", "divorced"), ("в отн", DATING),
    ("separ", "separated"), ("sépar", "separated"), ("viuda", "widowed"), ("viudo", "widowed"), ("viúva", "widowed"), ("viúvo", "widowed"), ("viuva", "widowed"), ("viuvo", "widowed"), ("verwi", "widowed"), ("pacsé", DATING),
    ("veuve", "widowed"), ("veuf", "widowed"), ("vedov", "widowed"), ("gift", MARRIED), ("singe", "single"), ("skilt", "divorced"), ("skild", "divorced"), ("forlo", ENGAGED), ("förlo", ENGAGED), ("متزوج", MARRIED),
];

static GOT: &Tab = &[("married", MARRIED), ("engaged", ENGAGED), ("divorced", "divorced")];

fn bare(m: &Match) -> V {
    if !SELF.test(m.string) || YOU.test_in(m.string, back(m, 60), m.start()) || OTHERS.test_in(m.string, back(m, 14), m.start()) {
        None
    } else {
        kept(m, MARRIED)
    }
}

fn seeking(m: &Match) -> V {
    if ATTACHED.test(m.string) {
        None
    } else {
        stated(m, &FUTURE, || Some("single"))
    }
}

fn soliciting(m: &Match) -> V {
    let s = m.string;
    let head = HEAD.at(s, 0).map_or(0, |h| h.end());
    if ATTACHED.test(s) || COUPLED.test(s) || PAIRED.test_in(s, 0, head) || WRITING.test(s) || !SOLICIT.test_in(s, 0, head) || FRIENDLY.test_in(s, 0, head) {
        None
    } else {
        Some("single")
    }
}

fn partnered(m: &Match) -> V {
    if m.group(1).map_or(false, |g| eq(g, "partner")) && WRITING.test(m.string) {
        None
    } else {
        owned(m, SPOUSES, 1)
    }
}

fn bare_spouse(m: &Match) -> V {
    if mine(m) {
        owned(m, SPOUSES, 1)
    } else {
        None
    }
}

fn lead_status(m: &Match) -> V {
    if SCOPED.test_in(m.string, back(m, 30), m.start()) {
        None
    } else if UNMARRIED.test(m.text()) {
        Some("single")
    } else if contains(m.text(), "not ") {
        None
    } else {
        get(STATUSES, m.group(1))
    }
}

fn unpartnered(m: &Match) -> V {
    let text = m.text();
    let lead: Option<&Re> = if starts_at(text, 0, "never") {
        Some(&NEVER_LEAD)
    } else if starts_at(text, 0, "broke up with") && !ends_at(text, text.len(), " me") {
        Some(&BREAK_LEAD)
    } else {
        None
    };
    if let Some(lead) = lead {
        if !lead.test_in(m.string, back(m, 24), m.start()) {
            return None;
        }
    }
    if spoken(m) && !UNPARTNERED.test_in(m.string, m.end(), m.string.len()) {
        Some("single")
    } else {
        None
    }
}

fn status_person(m: &Match) -> V {
    if !STATUS_LEAD.test_in(m.string, back(m, 60), m.start()) || THIRD.test_in(m.string, sentence(m).0, m.start()) {
        return None;
    }
    let status = get(STATUSES, m.group(1))?;
    stated(m, &FUTURE, || kept(m, status))
}

fn the_spouse(m: &Match) -> V {
    let s = m.string;
    let group = m.group(1)?;
    let other: &Re = if starts_at(group, 0, "hub") { &WIFE_WORD } else { &HUSBAND_WORD };
    let (a, b) = sentence(m);
    if !SELF.test_in(s, a, b) || OPENER.test(s) || other.test(s) || THIRD.test_in(s, a, m.start()) || ENDED.test(s) {
        return None;
    }
    stated(m, &FUTURE, || kept(m, MARRIED))
}

fn listed_status(m: &Match) -> V {
    if NEGATION.test(m.text()) || SCOPED.test_in(m.string, back(m, 30), m.start()) {
        None
    } else {
        get(STATUSES, m.group(1))
    }
}

fn foreign_status(m: &Match) -> V {
    let key: Vec<char> = match m.first() {
        Some(found) => found.to_vec(),
        None => {
            let text = m.text();
            let mut rest = text;
            for _ in 0..2 {
                match rest.iter().position(|&c| c == ' ') {
                    Some(p) => rest = &rest[p + 1..],
                    None => break,
                }
            }
            rest.to_vec()
        }
    };
    let short = &key[..key.len().min(5)];
    Some(get(FOREIGN_STATUSES, Some(short)).unwrap_or(DATING))
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let LEAD = format!(r"(?:{ME} (?:a |an )?|\bas an? |\b\d{{2}}\s*(?:[mf]|male|female|yo|y/o|years? old)?\b\W*(?:and )?|\b[mf]\s?\d{{2}}\b\W*(?:and )?)");
    let LEAD_STATUS = format!(r"(?:recently |newly |happily |also |still |currently |now |not |un)?(single\b{FOLLOW}|(?:taken|attached)\b{FOLLOW}|married|divorced|separated|widowed|engaged)\b(?! (?:men|women|people|guys|girls|moms|dads|mothers|fathers|parents|couples|folks|life|ladies|ones|friends|or|vs|status|sex|player|file|use|cock)\b)(?!-){TAIL}");
    let BARE_TAIL = format!(r"(?:(?:re)?post\W*|update\W*)?(?:{FOND}\s+){{0,3}}{BARE}(?:'s)?\b")
        + r"(?=\s*(?:\(|\d{2}|[.,!](?!\w))|\s+(?!(?:wanted|needed|material|for|search|hunt|swap|request|appreciation|experience|goals|vibes|energy|wanna|of|or|vs|who|that|culture|beaters?|pics?|photos?|share|sharing)\b)[a-z])";
    let spouse_anchors = ["wife", "hubby", "husband", "fianc", "spouse", "missus"];
    let status_anchors = ["single", "taken", "attached", "married", "divorced", "separated", "widowed", "engaged"];
    let mut rules = vec![
        r("relationship_status", &format!(r"(?:my(?<=\bmy)|our(?<=\bour))\s*(?:\(\d{{2}} ?[mf]?\) ?)?(?:{FOND}[ ,]+){{0,3}}{SPOUSE}(?:'s)?\b(?![- ]?to[- ]be|(?:'s)? (?:in crime|at the time|back then|in (?:high school|college)|died|passed)\b|(?<=partner) (?:subreddits?|subs|communit(?:y|ies)|sites?|compan(?:y|ies)|organi[sz]ations?|programs?|brands?|channels?|servers?|stores?|shops?|schools?|agenc(?:y|ies)|networks?|pages?|firms?|businesses|universit(?:y|ies)|institutions?)\b)"), partnered, TAGGED),
        needs(r("relationship_status", &format!(r"(?:^|[\n.!?]\s*|\]\s*){BARE_TAIL}"), bare_spouse, TAGGED), &spouse_anchors),
        needs(r("relationship_status", &format!(r"\b\d{{2}}\s*[mf]?\b\W*{BARE_TAIL}"), bare_spouse, TAGGED), &spouse_anchors),
        r("relationship_status", &format!(r"my (?<=\bmy )(?!{KIN}\b)(?!(?:business|lab|dance|tennis|study|writing|rp|gym|workout|sparring|accountability|training|climbing|golf|chess|duo|game|gaming|trading|research|project|work|running|hiking|language|practice|debate|doubles|play)\b)(?!x-)[a-z]+[ -](wife|husband|hubby|fianc[ée]e?|girlfriend|boyfriend|gf|bf|partner)\b(?!'s (?:friend|brother|sister|ex))"), partnered, TAGGED),
        r("relationship_status", &format!(r"my (?<=\bmy )(?:{FOND}[ ,]+){{1,2}}(?!{KIN}\b)(?!(?:business|lab|dance|tennis|study|writing|rp|gym|workout|sparring|accountability|training|climbing|golf|chess|duo|game|gaming|trading|research|project|work|running|hiking|language|practice|debate|doubles|play)\b)(?!x-)[a-z]+[ -](wife|husband|hubby|fianc[ée]e?|girlfriend|boyfriend|gf|bf|partner)\b(?!'s (?:friend|brother|sister|ex))"), partnered, TAGGED),
        r("relationship_status", &format!(r"(?:i (?<=\bi )(?:do |also |already |currently |now |even )?(?:have|got|have got)|i've (?<=\bi've )(?:also |now |even )?got|and (?<=\band )(?:also |now )?have) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))"), |m| if starts_at(m.text(), 0, "and") && !SPEAKER.test_in(m.string, sentence(m).0, m.start()) { None } else { owned(m, SPOUSES, 1) }, self_hedge()),
        r("relationship_status", &format!(r"i (?<=\bi )(?:do |also |already |currently )?(?:have|got) (?:a|an) (?:{FOND} )?(wife|husband|spouse|girlfriend|boyfriend|gf|bf|partner|significant other|fianc[ée]e?)\b(?! (?:material|for|who (?:isn't|is not)))"), |m| owned(m, SPOUSES, 1), self_hedge()),
        needs(r("relationship_status", r"\b(?:me and|and i|with|i and) the (wife|missus|mrs|hubby|wifey)\b|\bthe (wife|missus|mrs|hubby|wifey) and (?:i|me)\b|\bme (?:and|&) (?:my )?(hubby|wife|husband|missus|misses|mrs|wifey|hubs)\b", |m| if free(m) { get(SPOUSES, m.first()) } else { None }, TAGGED), &["wife", "missus", "mrs", "hubby", "husband", "misses", "hubs"]),
        r("relationship_status", r"(?<!')\b(?:mi|minha|meu|mon|ma|meine|mein|meiner|meinem|meinen|min|mijn|moja|mia|mio) (esposa|marido|esposo|mujer|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|hustru|ehemann|ehefrau|gatte|gattin|époux|épouse|echtgenoot|echtgenote|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|kjæreste|vriendin|vriend|partner|partnerin|pareja|compagnon|compagne|conjoint|conjointe|partenaire|compagno|compagna|ragazza|ragazzo|fidanzata|fidanzato|lebensgefährte|lebensgefährtin|sambo|flickvän|pojkvän|prometida|prometido|noiva|noivo|verlobte|verlobter|verloofde|fiancé|fiancée)\b",
          |m| get(FOREIGN_SPOUSES, m.group(1)), TAGGED),
        r("relationship_status", concat!(r"\b(?:мо[яейюи]\w*) (жен[аыеуой]\w*|муж\w*)|\bmo(?:j|ja|jego|jej|jemu|im|ją) (mąż|męża|mężem|mężowi|żony|żonie|żoną|żonę)\b|\b(eşim|karım|kocam(?!an))\w*",
          r"|\b(asawa|mister|misis) ko\b|\baking (asawa)\b|\bmer[ie] (wife|biwi|patni|husband|pati)\b|\b(istri|suami)(?:ku| saya| aku)\b|\bminha (mulher)\b",
          r"|\b(زوجتي|زوجي)|\b(אשתי|בעלי)(?! חיים)"),
          constant(MARRIED), TAGGED),
        needs(r("relationship_status", concat!(r"\b(?:my|our) (?:own |happy |long |current |second |strong |healthy |lovely |wonderful |great |good |sexless |open |\d+[- ]year )?marriage\b|\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|many|several) years (?:of marriage|married)\b",
          r"|\b(?:since|when|after|before) (?:we|i) got married\b|\b(?:we|i)(?:'ve| have) been (?:happily )?married\b(?! before)"), constant(MARRIED), self_hedge()), &["marri"]),
        needs(r("relationship_status", concat!(r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\b(?:she|he) (?:left|dumped) me\b",
          r"|\bi broke up with (?:my|the|him|her)\b|\bwe (?:just |recently |finally |officially )?(?:broke up|broken up|split up)\b|\b(?:my|our) (?:\w+ )?(?:fianc[ée]e?|gf|bf|girlfriend|boyfriend|partner) and i (?:just |recently |finally )?(?:broke up|split up|split|separated|called it quits)\b|\b(?:she|he) broke up with me\b|\bforever alone\b|\bbeen single (?:for|since)\b|\bterminei (?:o |meu )(?:namoro|relacionamento)\b|\bterminei com (?:o |meu )?(?:ex|namorad[oa])\b|\btermin[eé] (?:la|mi|una) relación\b|\bmi relación (?:de \d+ años )?terminó\b|\bterminé con mi (?:novi[oa]|pareja)\b|\bj'ai rompu avec\b|\b(?:i'm|im|i am) (?:a )?single (?:mom|mum|mother|dad|father|parent)\b"),
          |m| stated(m, &STATED, || Some("single")), TAGGED), &["single", "unattached", "not seeing", "not dating", "left me", "dumped me", "broke", "broken", "split", "separated", "quits", "alone", "termin", "relación", "rompu"]),
        r("relationship_status", &(format!(r"{ME} (?:happily |currently |still |also |newly |recently |now |officially |finally |legally )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|unmarried|not married)\b") + TAIL), |m| scoped(m, STATUSES), TAGGED),
        needs(r("relationship_status", &format!(r"(?<!every){LEAD}{LEAD_STATUS}"), lead_status, TAGGED), &status_anchors),
        needs(r("relationship_status", &format!(r"(?<!every){OPENING}{LEAD_STATUS}"), lead_status, TAGGED), &status_anchors),
        r("relationship_status", concat!(r"\b(?:i'm|im|i am|we're|we are|we've been|i've been|i have been|we have been) (?:\(?\d{2} ?[mf]\)? )?(?:happily |currently |exclusively |casually |now )?dating (?:for|since|someone|a |an |another|this|each other|him|her)\b",
          r"|\bi (?:have |'ve )?(?:recently |just |finally )?(?:entered|got into|started|began) (?:a |an )(?:new |serious |committed |long[- ]distance |relationship )?relationship\b"), |m| stated(m, &FUTURE, || kept(m, DATING)), TAGGED),
        needs(r("relationship_status", r"\bi (?:just |recently |finally )?(?:started|began) dating (?:a |an |this |someone|somebody|him\b|her\b|my )", |m| if COUPLED.test(m.string) || BROKEN.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, DATING)) }, TAGGED), &["dating"]),
        r("relationship_status", &format!(r"{ME} (?:(?!(?:not|never)\b)\w+ )?in an? (?:[\w-]+ ){{1,3}}relationship\b(?! with (?:food|my (?:body|food|mom|dad|parents|family|job|work)|money|alcohol|god|jesus))"), |m| stated(m, &FUTURE, || Some(DATING)), TAGGED),
        needs(r("relationship_status", r"\b[mf]4[mfat]\w*\]?\s*(?:-\s*)?(?:\d{2}\s*)?(?:-\s*)?(single|married|divorced|separated|widowed|engaged|taken)\b|\b(?<![^,/|( ])(?<![^,/|(] )(married|divorced|separated|widowed|verheiratet|vergeben|geschieden|mariée?|divorcée?|casad[oa]|divorciad[oa]|sposat[oa]|getrouwd|gescheiden)\s*(?:[,/|)]|(?:and|et|und|y|e|en)\b)|\bmarital status\W*(single|married|divorced|separated|widowed|engaged)\b",
          |m| if free(m) { get(STATUSES, m.first()) } else { None }, TAGGED), &["single", "married", "divorc", "separated", "widowed", "engaged", "taken", "verheiratet", "vergeben", "geschieden", "marié", "casad", "sposat", "getrouwd", "gescheiden", "marital"]),
        r("relationship_status", r"\b(?:we(?:'re| are)|we got|we've been|now) (?:now |happily |both |finally |officially |just |recently |still )?married\b|\b(?:i'm|im|i am) (?:\w+ )?married to (?:a|an|my|the love|someone|him|her|\w+ (?:man|woman|guy|girl))\b", constant(MARRIED), Some(&*SCOPED)),
        needs(r("relationship_status", concat!(r"\b(?:as|being|i'm|im|i am|we're|we are|just|a fellow|as a fellow) an? (?:(?!single|not|un|never|ex|former|soon)[\w-]+ ){0,2}married (?:man|guy|woman|lady|dad|mom|mum|father|mother|couple|person|male|female|gal|dude|bi|white|black|latina|latino|asian|professional|parent)\b",
          r"|\bfellow married (?:man|guy|woman|lady|dad|mom|mum|father|mother|person|parent)\b"), |m| stated(m, &FUTURE, || kept(m, MARRIED)), TAGGED), &["married"]),
        r("relationship_status", r"\bmy (?:ex[- ]?(?:wife|husband|hubby|spouse|husbands|wifes)|divorce)\b|\b(?:after|since|during|before|post|through|finalized) (?:my|our|the) divorce\b|\b(?:i|we) (?:got|were|are|'re|am|'m) (?:\w+ )?divorced\b|\b(?:recently|newly|twice|freshly) divorced\b|\bdivorcee\b",
          constant("divorced"), Some(&*SCOPED)),
        needs(r("relationship_status", concat!(r"\b(?:recently|newly|happily|still|forever|freshly|blissfully|proudly|totally|currently) single\b|\b(?:i have|i've got|i got|i'm|im|with) no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|relationship|spouse|so)\b",
          r"|\b(?<![^,; ])(?<![^,;] )no (?:partner|gf|bf|girlfriend|boyfriend|wife|husband|spouse)\s*[,;&]|\b(?<!you )(?<!he )(?<!she )(?<!they )(?<!u )(?:don't|do not|dont) (?:currently |even |really )?have (?:a |an )?(?:girlfriend|boyfriend|gf|bf|partner|significant other|wife|husband|spouse)\b",
          r"|\b(?:у меня нет|я не) (?:сейчас )?(?:отношений|девушки|парня|жены|мужа|замужем|женат)"), constant("single"), Some(&*CONDITIONAL)), &["single", "no ", "don't", "do not", "dont", "у меня нет", "я не"]),
        r("relationship_status", concat!(r"\b(?:estoy|soy) (?:felizmente |recién |recien |ya |también |tambien |todavía |todavia |aún |aun )?(casad[oa]|solter[oa]|divorciad[oa]|comprometid[oa]|separad[oa]|viud[oa])\b|\bestoy (?:en una relación|de novi[oa])\b|\b(?:sou|estou) (?:felizmente |recém |recem |já |ja |também |tambem |ainda )?(casad[oa]|solteir[oa]|divorciad[oa]|noiv[oa]|separad[oa]|viúv[oa]|viuv[oa])\b|\bestou (?:numa|em uma) relação\b",
          r"|\b(?:ich|und|aber) bin (?:glücklich |auch |schon |noch |wieder |jetzt |mittlerweile |inzwischen |frisch |seit \w+ (?:jahren|monaten) )?(verheiratet|single|ledig|geschieden|verlobt|vergeben|verwitwet)\b|\bje suis (?:heureusement |aussi |déjà |toujours |encore |actuellement |maintenant )?(mariée?|célibataire|divorcée?|fiancée?|en couple|pacsée?|séparée?|veuve|veuf)\b|\bsono (?:felicemente |già |anche |ancora )?(sposat[oa]|single|fidanzat[oa]|divorziat[oa]|separat[oa]|vedov[oa])\b",
          r"|\bjestem (żonaty|zamężna|mężatką|singlem|singielką|rozwiedzion[ya]|zaręczon[ya]|w związku)\b|\bik ben (?:al |ook |nog |gelukkig )?(getrouwd|single|vrijgezel|gescheiden|verloofd)\b|\b(?:jeg er|jag är) (?:også |också |lykkeligt |lyckligt |nu )?(gift|single|singel|skilt|skild|forlovet|förlovad)\b|\bя (женат|замужем|холост|разведен[а]?|в отношениях)\b|\b(?:انا|أنا) (متزوج)"),
          foreign_status, Some(&*SCOPED)),
        r("relationship_status", r"\b(?:i|we) (?:just |recently |finally )?got (married|engaged|divorced)\b|\bi (?:just |recently |finally )?(divorced) (?:my|him|her|in\b|last\b|a few\b|\d)|\b(married) (?:for )?(?:\d+|a few|many|almost|over|nearly|about) (?:\w+ )?years\b",
          |m| get(GOT, m.first()), hedge()),
        needs(r("relationship_status", concat!(r"\bi (?:just |recently |finally |actually |also )?married (?:my|her|him|a|an|the (?:love|man|woman|girl|guy)|someone|one)\b|(?:^|[\n.!?]\s*)(?:wife|hubby|husband|hubs|wifey) (?:and|&) i\b",
          r"|(?:\bi'm|\bim|\bi am|\b\d{2}\s*[mf]?|\bstuck|\btrapped|\bunhappy|\bhappy) (?:\w+ )?in (?:an?|this|my) (?:open |sexless |unhappy |happy |loveless |\w+ )?marriage\b|\b(?:my|our) wedding (?:ring|band|anniversary|vows)\b"),
          |m| if ENDED.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, MARRIED)) }, TAGGED), &["married", "and i", "& i", "marriage", "wedding", "anniversary"]),
        needs(r("relationship_status", concat!(r"\b(?:i|we) (?:just |recently |finally )?(?:re-?married|married (?:in|on|last|this|young|at|back|\d|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december))\b|\b(?:and|but) (?:just |recently |finally )?got married\b|\bthe (?:person|man|woman|guy|girl|one|love of my life) i (?:married|'m married to|am married to)\b|\b(?:and|but) (?:currently|now|happily|also) married to (?:a|an|my|the|someone|him|her)\b|\bwe(?:'re| are) an? (?:\w+ )?married\b(?! (?:couples?|people)\b)",
          r"|(?:^|[\n.!?,]\s*)in (?:an? (?:\w+ )?|(?:dead|open|sexless|unhappy|loveless|happy|straight|bad|abusive) )marriage\b(?!\s*,)|\b(?:we're|we are|we've been|we have been|we went|we started|we're going|i'm|im|i am) (?:\w+ )?(?:in|to|doing|going to) marriage (?:counseling|counselling|therapy)\b",
          r"|(?:^|[\n/|]\s*)married\s*[.!]?\s*(?:\n|$)|\bwith (?:the )?(?:wife|hubby|husband) (?:and|&) (?:the |our |my )?(?:\d+ |two |three |four )?(?:kids?|kiddos?|children|sons?|daughters?|boys|girls|baby)\b"),
          |m| if ENDED.test(m.string) || !SELF.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, MARRIED)) }, TAGGED), &["married", "marriage", "wife", "hubby", "husband"]),
        needs(r("relationship_status", &format!(r"{AS} an? (?:(?!(?:future|good|bad|perfect|trophy|second|ex|not)\b)\w+ )?(?:wife|husband|married (?:man|woman|guy|lady|person|dad|mom|mum|father|mother))\b(?! (?:material|is|was|would|should|and mother|and father)\b)"), |m| if ENDED.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, MARRIED)) }, TAGGED), &["wife", "husband", "married"]),
        r("relationship_status", r"\bmy late (?:wife|husband|hubby|spouse|partner)\b|\b(?:i lost|since i lost|after i lost|after losing|since losing) my (?:wife|husband|hubby|spouse)\b|\bmy (?:wife|husband|hubby|spouse) (?:passed away|died|passed)\b", |m| stated(m, &STATED, || Some("widowed")), TAGGED),
        r("relationship_status", r"\bmy (?:estranged|separated) (?:wife|husband|hubby|spouse)\b|\bmy (?:stbx\w*|soon[- ]to[- ]be[- ]ex(?:[- ]\w+)?)\b|\b(?:we're|we are|we've been|we have been|we recently|we just) (?:\w+ )?separated\b", |m| stated(m, &STATED, || Some("separated")), TAGGED),
        r("relationship_status", r"(?:^\W*(?:\d{2}\s*)?(?:[\[\(]\w+[\]\)]\s*)?(?:(?!he |she |they |you |who |we |got |get |not |never |was |were |be |been |is |are |any |only |all )\w+ )?married\b(?! (?:men|women|people|guys|couples|folks|life|cock|or)\b))", |m| kept(m, MARRIED), TAGGED),
        needs(r("relationship_status", r"^[^\n]*?\b[mf]4[mfat]\w*[^\n]*?(?<![\w-])(?<!for )(?<!seeking )(?<!a )(?<!an )(?<!with )(?<!want )(?<!to )(?<!no )(?<!not )(?<!my )(?<!your )(?<!her )(?<!his )(?<!their )married (?:man|male|guy|dude|dad|daddy|woman|female|lady|gal|mom|mum|milf|dilf|bi|white|black|asian|latina|latino|professional|father|mother|wife|husband|hubby|m|f|\d{2})\b(?!s\b|'s\b)", |m| kept(m, MARRIED), TAGGED), &["married"]),
    ];
    for pattern in COUPLE_ADS {
        rules.push(r("relationship_status", pattern, couple, TAGGED));
    }
    rules.extend([
        r("relationship_status", r"\b(gf|bf|boyfriend|girlfriend|jowa|partner) ko\b", |m| owned(m, SPOUSES, 1), TAGGED),
        r("relationship_status", r"my (?<=\bmy )(?:current |new |\d+[- ](?:year|month)[- ]?(?:old )?|long[- ]distance |long[- ]term )?relationship\b(?! (?:with (?!(?:my )?(?:bf|gf|boyfriend|girlfriend|partner|husband|wife)\b)|status|history|goals|life|skills|issues|anxiety|advice|problems? with|coach)\b)",
          |m| if ENDED.test(m.string) || BROKEN.test(m.string) || COUPLED.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, DATING)) }, TAGGED),
        r("relationship_status", concat!(r"\bi(?:'ve| have)? never (?:had|been in) (?:a |an )?(?:real |serious |proper |actual )?(?:girlfriend|boyfriend|gf|bf|relationship|partner)\b|\bi(?:'ve| have)? never (?:dated|been on a date|been kissed)\b",
          r"|\b(?:ich|hab|habe|hatte) (?:(?!er |sie |du |ihr |es )\S+ ){0,4}?(?:noch nie|noch keine|nie) (?:im leben )?(?:eine )?(?:freundin|beziehung)\b|\bnunca (?:he )?(?:tuve|tenido) (?:novi[oa]|pareja)\b|\bnunca tive (?:namorad[oa]|relacionamento)\b|\bjamais eu de (?:copine|copain|petite amie|petit ami)\b"), seeking, TAGGED),
        r("relationship_status", r"\bmy (?:\w+ )?(?:gf|bf|girlfriend|boyfriend|fianc[ée]e?|partner) (?:of \w+ (?:years?|months?) )?(?:just |recently |finally )?(?:broke up with|dumped|left|ghosted) me\b|\b(?:i|i just|i recently) got dumped\b", |m| stated(m, &STATED, || Some("single")), TAGGED),
        r("relationship_status", r"looking for (?<=\blooking for )(?:a |an |my )?(?:\w+ )?(?:ltr|long[- ]term relationship|relationship|girlfriend|boyfriend|gf|bf|wife|husband|soulmate|life partner)\b", seeking, self_hedge()),
        r("relationship_status", SOLO_AD, soliciting, TAGGED),
        r("relationship_status", r"hub(?<![\w'-]hub)(?:by|bie)(?:'s)?(?![\w'-])(?! material| hole)|hubs and i\b", bare, self_hedge()),
        needs(r("relationship_status", r"never (?<=\bnever )(?:been )?(?:married|dated)\b(?! (?:a|an|the|someone|anyone|him|her|them|my|your)\b)|broke up (?<=\bbroke up )w(?:ith (?:my|him|her)\b|(?:/|ith)? me\b)|(?:my(?<=\bmy)|our(?<=\bour)) (?:\w+ )?(?:gf|bf|girlfriend|boyfriend|partner|fianc[ée]e?) (?:of \w+ (?:years?|months?) )?(?:breaking up with|leaving|dumping) me\b",
          unpartnered, TAGGED), &["never", "broke up", "breaking up", "leaving me", "dumping me"]),
        needs(r("relationship_status", r"\b(?:i|i've|i have|im|i'm|i am) (?:just |recently |finally )?(?:got|gotten|getting) out of an? (?:[\w-]+ ){0,2}relationship\b", |m| stated(m, &FUTURE, || kept(m, "single")), TAGGED), &["out of a"]),
        needs(r("relationship_status", r"\bwe(?:'re| are) (?:now |finally |officially |happily |recently |just )?engaged\b", |m| stated(m, &FUTURE, || kept(m, ENGAGED)), TAGGED), &["engaged"]),
        needs(r("relationship_status", r"\b(?:the |this )?(?:woman|man|girl|guy|person|lady|someone|gal|dude) (?:\(\d{2} ?[mf]?\) )?(?:that |who )?(?:i'm|im|i am|i've been|i have been) (?:currently |now |casually )?(?:dating|seeing)\b",
          |m| if ENDED.test(m.string) || BROKEN.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, DATING)) }, TAGGED), &["dating", "seeing"]),
        needs(r("relationship_status", r"\b(?:me and|me & ) my (?:man|girl|guy|woman|lady|boo|bae)\b|\bmy (?:man|girl|guy|woman|lady|boo|bae) (?:and|&) i\b", |m| if BROKEN.test(m.string) { None } else { kept(m, DATING) }, TAGGED), &["me and", "me & ", " and i", " & i"]),
        needs(r("relationship_status", r"(?:(?<=\w) ?\(|(?<=[\w)\]]),)\s*single\b(?=\s*[),.]|\s+and\b)", |m| if ATTACHED.test(m.string) || THIRD.test_in(m.string, sentence(m).0, m.start()) { None } else { kept(m, "single") }, TAGGED), &["single"]),
        needs(r("relationship_status", r"\bmy (?!future |soon )(?:\w+ )ex[- ]?(?:wife|husband|hubby|spouse)\b", |m| if spoken(m) { Some("divorced") } else { None }, TAGGED), &["ex"]),
        needs(r("relationship_status", r"\b(?:i'm|im|i am) (?:(?:already|just|actually|technically|currently|recently|newly|happily|so|totally|definitely|very|completely|literally|basically|still) ){1,2}(engaged|separated|divorced|in a relationship|single|married)\b|\bmy (?:recent )?engagement\b(?! (?:ring|rings|photos?|party|shoot|announcement|ceremony)\b)",
          |m| { let status = get(STATUSES, m.group(1)).unwrap_or(ENGAGED); stated(m, &FUTURE, || kept(m, status)) }, TAGGED), &["engage", "separated", "divorced", "relationship", "single", "married"]),
        needs(r("relationship_status", r"\b(single|divorced|separated|widowed|married) (?:man|guy|woman|lady|dad|mom|mum|father|mother|person|male|female|gal|dude|parent|mama|daddy|mommy|milf|dilf|gilf|fella|grandpa|grandma|granny|chick|girl|boy|gentleman|wife|husband|hubby)\b(?!s\b|'s\b)", status_person, TAGGED), &["single", "divorced", "separated", "widowed", "married"]),
        needs(r("relationship_status", r"the (?<=\bthe )(wife|wifey|missus|hubby)\b(?!'s (?:family|parents|side|friends?)\b|(?:'s)? (?:of|in (?:the|this|that|a)|who|that|and husband|and the husband|material)\b|-)", the_spouse, TAGGED), &["wife", "missus", "hubby"]),
        needs(r("relationship_status", &format!(r"wish(?<=\bwish)(?:ed)? (?:that )?my (?:{FOND}[ ,]+){{0,3}}(wife|husband|hubby|wifey|spouse)\b(?= (?:would|could|was|were|did|had|liked|loved|wanted|knew|understood|cared|let|enjoyed|got|felt|saw|thought|made|gave)\b)"), |m| owned(m, SPOUSES, 1), TAGGED), &["wish"]),
        needs(r("relationship_status", &(format!(r#"{ME} (?:an? )?(?:(?:(?:[\w'"-]+ ){{0,2}}[\w'"-]+, ?){{1,8}}(?:and |& )?|(?:[\w-]+ ){{1,2}}(?:and|&) |(?:(?!(?:hardly|barely|scarcely|nearly|likely|unlikely|only)\b)\w+ly ){{1,2}})(?:\w+ly )?(single|married|engaged|divorced|separated|widowed)\b(?! (?:men|women|people|guys|girls|moms|dads|mothers|fathers|parents|couples|folks|life|ladies|ones|friends|or|vs|status|sex|player|file|use|cock)\b)(?!-)"#) + TAIL), listed_status, TAGGED), &status_anchors),
        needs(r("relationship_status", r"i (?<=\bi )(?:\w+ly |also |now |still )am (?:\w+ly )?(single|married|engaged|divorced|separated|widowed)\b(?! (?:men|women|people|guys|girls|couples|folks|life|or)\b)", listed_status, TAGGED), &status_anchors),
        needs(r("relationship_status", r"\b(?:i'm|im|i am|i've been|i have been) (?:currently |now |casually |also |still )?seeing (?:someone|somebody|(?:a|this) (?:\w+ )?(?:girl|guy|man|woman|lady|boy|dude|gal|person))\b(?!'s| (?:who|that|tomorrow|tonight|next|later|about|for (?:a|the) first)\b)", |m| if BROKEN.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, DATING)) }, TAGGED), &["seeing"]),
        needs(r("relationship_status", r"\bi (?:just |recently |finally |eventually )?(?:ended|left) (?:my|a) (?:[\w-]+ ){0,2}relationship\b", |m| stated(m, &FUTURE, || kept(m, "single")), TAGGED), &["relationship"]),
        needs(r("relationship_status", r"\b(?:i'm|im|i am)(?: \w+){0,3} (?:of|to|with) being single\b|\bi(?:'ve| have) (?:\w+ )?been single\b", |m| if NEGATION.test(m.text()) { None } else { stated(m, &FUTURE, || kept(m, "single")) }, TAGGED), &["single"]),
        needs(r("relationship_status", r"(?:\b\d{2}\s*[mf]?|\b(?:straight|bi|gay|male|female|man|woman|guy|girl|[mf]))\b[\W_]*with (?:a |my )?(gf|bf|girlfriend|boyfriend)\b", |m| if BROKEN.test(m.string) { None } else { owned(m, SPOUSES, 1) }, TAGGED), &["with"]),
        needs(r("relationship_status", &format!(r"{ME} (?:(?!(?:not|never|no)\b)(?![a-z]+(?:ing|ed)\b)[\w-]+ ){{1,3}}in an? (?:(?!(?:not|never|no)\b)[\w-]+ ){{0,3}}relationship\b(?! with (?:food|my (?:body|food|mom|dad|parents|family|job|work)|money|alcohol|god|jesus))"), |m| if COUPLED.test(m.string) { None } else { stated(m, &FUTURE, || kept(m, DATING)) }, TAGGED), &["relationship"]),
    ]);
    rules
}
