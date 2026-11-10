use crate::shared::*;
use claimcore::*;

const CHILD: &str = concat!(
    r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|",
    r"first ?born|lo|dc|dcs|bio kids|step-?child(?:ren)?|newborns|youngest|oldest|eldest|middle child|offspring|bairns?|sprogs?|tweens?|preteens?|pre-teens?|preschoolers?|kindergart(?:e)?ners?|(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth) graders?)"
);
const AGE: &str = r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks|y)?(?:[- ]old)?";
const YEARS: &str = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)";
const NOT_CHILD: &str = concat!(
    r"(?:rescues?|fosters?|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|horses?|pony|birds?|cars?|trucks?|vans?|bikes?|house|home|laptop|computer|pc|phone|tv|account|self|body|brother|sister|cousin|nephew|niece|friend|student|students|",
    r"client|patient|boyfriend|girlfriend|bf|gf|husband|wife|grand\w*|mattress|bed|couch|boat|shoes|iphone|ipad|tablet|macbook|build|rig|tires?|battery|knees?|back|hips?|feelings|brain|mind|heart|soul)"
);
const ORDINAL: &str = r"(?:first|second|third|fourth|1st|2nd|3rd|4th)";
const KID_NOUN: &str = concat!(
    r"(?:kids?|kiddos?|children|child|sons?|daughters?|toddlers?|teens|teenagers|newborn|infant|twins|triplets|stepkids|step-?sons?|step-?daughters?|grandkids|grandchildren|",
    r"(?:1[0-7]|[1-9]|one|two|three|four|five|six|seven|eight|nine|ten)(?:[.,]5| 1/2| and a half)?[- ]?(?:y/o|yo|(?:years?|yrs?|months?|mos?|weeks?|wks?)[- ]?olds?))"
);
const KID_COUNT: &str = r"(?:(?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|my|our|several|multiple) )?";
const KID_WORDS: &str = r"(?:(?!\d+ )(?!(?:no|any|not|never|to|been|seen|met|heard|watched|known|taught|worked|told|asked|other|those|these|the|this|that|your|his|her|their|some|many|lots|plenty|more|enough|of|with|in|at|for|on|by|from|about|like|as|until|till|since|when|after|before|and|or|but|so|then|than)\b)(?![a-z]+ed\b)[a-z\d-]+ ){0,2}";
const KID_AFTER: &str = r"\b(?!'s|'| (?:of(?! (?:my|our) own)|in law|in-law|in (?:my|the|our|his|her|class|school)|at|who|that|from|come|came|ask|asked|tell|told|say|said|walk|walked|run|ran|on|over|when|someday|before|edition|dogs?|cats?|pups?|puppy|car|house|laptop|phone|(?!and |or |plus |with )[\w-]+ (?:dogs?|cats?|pups?|puppy|puppies|kittens?|kitty))\b)";

regex!(INFANT, concat!(
    r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|\bcrib|\bcot\b|\bformula\b(?! (?:1|one)\b)|\bfeeds?\b|\bfeeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|\bbottles?\b|sleep regression|stroller|\bpram|onesie|bassinet|car seat|",
    r"kindergarten|preschool|school|daughter|\bsons?\b|\bmama\b|mommy|\bcrawl|\bnaps?\b|\bnapping|\bborn\b|birth|pregnan|\blabou?r\b|\bdelivered\b|\bmilk\b|\bpumping\b|\bnursing\b|\bnursed\b|ultrasound|\bob\b|\bteeth|\bcry|\bcries\b|\bcrying\b|sleep|\blatch|\b(?:was|is|at|around|about|turned|turns|almost|nearly|only|just|now) \d+ ?(?:months?|weeks?|mos?|wks?)\b"
));
regex!(PARENT_LEAD, format!(r"(?:{ME} an? |\bas an? |\bbeing an? |^{flair}\W*|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[\]\)]\s*|[-|:]\s+|\b[mf]4[mfat]\w*\s*)(?:(?!my |his |her |your |their |our |the |a )[\w,-]+ ){{0,3}}$", flair = claimcore::flair!()));
regex!(ROMANTIC, r"\b(?:bf|gf|boyfriend|girlfriend|husband|hubby|wife|daddy|sex|sexy|cock|dick|pussy|fuck\w*|kiss\w*|cuddl\w*|horny|nsfw|lover|honey|babe|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?)\b");
regex!(PAST, r"\b(?:was|were|been)\s+(?:\w+\s+)?$");
regex!(FLAIR, r"^r/\w+:");
regex!(LIKENED, r"\b(?:like|look|looks|looked|looking|as if|as though|someone|somebody|she|he|you|they|wife|gf|girlfriend|partner)(?:'s|'re| is| are| was)?\s+(?:\w+\s+)?$");
regex!(PRONOUN, r"\b(?:he|she|him|her|his|they|them|their)\b");
regex!(FIRST, r"\b(?:i|we)\b[^.!?\n]{0,40}$");
regex!(TEACHING, r"\b(?:teach|teacher|class|classroom|students?|school|nanny|babysit\w*|camp|coach\w*|daycare|work)\b");
regex!(LISTED, concat!(r"(?:^", claimcore::flair!(), r"|[,;:]\s*|\b(?:single|married|divorced|no partner|no pets|no debt|\d{2}\s*[mf]?)\s*[,;&/]\s*(?:and )?)$"));
regex!(BABY_LEAD, concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*|\b(?:and|but|so|when|while|until|because|since|for|with|myself and|me and) )$"));
regex!(NEGATED, r"\b(?:no|não|nao|non) $");
regex!(THINGS, r"\b(?:dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?|horses?|birds?|fish|rabbits?|bunny|car|cars|truck|bike|phone|laptop|pc|build|tattoo|hair|order|package|account|plant|plants|vet|spay\w*|neuter\w*)\b");
regex!(BIRTH_VERB, r" (?:was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b");
regex!(BIRTH_LEAD, r"\b(?:had|have|with|after|since|before|for|from|than|during) $");
regex!(AWAITED, r"\b(?:to|wanna|until|till|before|once|planning on|plan on) (?:have|having)\s+$");
regex!(DUE, r"(?:'s)? (?:is |was )?due\b");
regex!(HAD_KIDS, r"\b(?:you|u|he|she|they|who|people|parents|someone|her|him|his|their)\b");
regex!(LEADING, concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,;]\s*|\band |\bbut )(?:also |now |still |already )?$"));
regex!(OTHERS_PARENT, r"\b(?:my|his|her|their|your|our|the|whose|he|she|they|you)\b");
regex!(TEEN_AGE, r"\d|year");
regex!(SIBLING, r"\s*(?:brother|sister|sibling|cousin|friend|aunt|uncle|niece|nephew|grand|memor|and|class|student|pupil)");
regex!(CHILDLESS, r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children)\b|\bi have no kids yet\b");
regex!(KIDS_WORD, r"\b(?:kids|children|kid|child)\b");
regex!(NO_MORE, r"(?:,| and|;) no\b");
regex!(CHOSEN, r"\b(?:want|wanted|wanna|won't|wont|will not|plan|intend|enjoy|love|like|prefer|chose|choose|decided|having)\b");
regex!(UNABLE, r"\b(?:conceive|infertile|can't|cannot|can not|couldn't|could not|able)\b");
regex!(SOLO_PARENT, r"(?:single|solo|lone)[- ]?(?:mom|mum|mother|mama|dad|father|parent)|by myself|on my own|alone");
regex!(TAGGED_LINE, r"(?<![\w$#.,'/:+-])(?:\d{2} ?(?:[mf]|male|female|yo|y/o)|[mf] ?\d{2})(?![\w'%])|\b(?:married|divorced|single|separated|widowed|mom|mum|dad|wife|husband)\b");
regex!(FOR_OTHER, r"\b(?:dating|date|dated|met|meet|seeing|marry|marrying|looking for|seeking|want|wants|need|needs|find|is|was|were|be|been|like|love|into)\b");
regex!(MY_OTHER, r"\b(?:my|our) [\w-]+(?: [\w-]+)?,?\s*$");
regex!(PROUD, r"\b(?:proud|fellow|another|single|tired|exhausted|happy|lucky)\s+(?:[\w-]+\s+)?$");
regex!(RANKED, r"(?:'s\b|\s*[^\w\s]|\s*$|\s+(?:is|was|has|had|just|and|turned|turns|will|started|starts|got|gets|loves|loved|hates|said|says|asked|wants|wanted|went|goes|can|can't|could|does|doesn't|did|didn't|isn't|wasn't|would|still|now|recently|also|always|never|who|\d+|sons?|daughters?|kids?|child|boys?|girls?|one|of mine)\b)");
regex!(ORDINAL_RE, format!(r"\b{ORDINAL}\b"));
regex!(OTHER_PERSON, r"\b(?:he|she|they|you|u|his|her|their|your|ur|someone|somebody|people|(?:a|the|this|that) (?:man|woman|guy|girl|person|dude|lady))\b");
regex!(PENDING, r"\b(?:before|until|till|unless|once)\s+$");
regex!(SOMEDAY, r"\s+(?:one day|someday|some day|in the future)\b");
regex!(EXPECTED, r"\b(?<!were )(?<!was )(?<!got )(?<!became )(?:pregnant with|expecting|due with|carrying)\s+$");
regex!(LATER, r"\b(?:second|third|fourth|fifth|2nd|3rd|4th|5th)\b");
regex!(EXPECTING, r"pregnan|trimester|\b\d+ ?w(?:ee)?ks?\b|\bbump\b|due date|\bttc\b|\bivf\b|\bexpecting\b");
regex!(SUBJECT, r"\b(?:the|a|an|his|her|their|your|my|our) [\w-]+ being $");
regex!(THEN_THIRD, r"[^.!?\n,]*,\s*(?:she|he|they|you|u|people|parents|moms|mums|dads|women|men)\b");
regex!(NAMED, r"\b(?!i\b)[a-z]+ (?:was|is|became) an? (?:[\w-]+ )?$");
regex!(KIN_BEFORE, r"\b(?:my|our|his|her|their|your) (?:mom|mum|mother|dad|father|sister|brother|friend|aunt|cousin|wife|husband|neighbou?r|coworker|boss|daughter|son|grandma|grandmother)\b");

static FOREIGN_COUNTS: &Tab = &[
    ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("zwei", "2"), ("drei", "3"), ("vier", "4"), ("twee", "2"), ("drie", "3"), ("dos", "2"), ("tres", "3"), ("cuatro", "4"),
    ("deux", "2"), ("trois", "3"), ("quatre", "4"), ("dois", "2"), ("duas", "2"), ("três", "3"), ("due", "2"), ("tre", "3"), ("ein", "1"), ("eine", "1"), ("einen", "1"), ("een", "1"), ("un", "1"),
    ("une", "1"), ("uno", "1"), ("una", "1"), ("um", "1"), ("uma", "1"), ("egy", "1"), ("két", "2"), ("három", "3"),
];
const COUNT: &str = r"(?<!\d[.,])(\d|10|one|two|three|four|five|six|seven|eight|nine|ten)\b";
const FONDLY: &str = r"(?:beautiful|wonderful|amazing|awesome|young|little|small|grown|adult|teenage|lovely|precious|sweet|crazy|wild|healthy|great|gorgeous|fantastic|perfect|lil|grown-up|grown up)";

fn owner_count(m: &Match) -> V {
    let s = m.string;
    let start = sentence_start(m);
    if THIRD.test_in(s, start, m.start()) || FOR_OTHER.test_in(s, back(m, 30).max(start), m.start()) || MY_OTHER.test_in(s, back(m, 30), m.start()) || KIN_BEFORE.test_in(s, start, m.start()) {
        None
    } else {
        counted(m)
    }
}

fn adult(number: Option<&[char]>, unit: Option<&[char]>) -> bool {
    let (Some(number), Some(unit)) = (number, unit) else { return false };
    (starts_at(unit, 0, "y") || starts_at(unit, 0, "Y")) && isdigit(number) && py_int(number).map_or(false, |n| n > 17)
}

fn aged(m: &Match) -> V {
    let unit = m.nonempty(2).or(m.group(3));
    if adult(m.group(1), unit) {
        return None;
    }
    if free(m) && PRONOUN.test_in(m.string, m.end(), bounds(m).1) {
        Some(parent(m))
    } else {
        None
    }
}

fn parenting(m: &Match) -> V {
    let s = m.string;
    if BABY_LEAD.test_in(s, back(m, 14), m.start()) && INFANT.test(s) && SELF.test(s) && !ROMANTIC.test(s) {
        kept(m, parent(m))
    } else {
        None
    }
}

fn birth_order(m: &Match) -> V {
    let s = m.string;
    if BIRTH_VERB.at(s, m.end()).is_none() && !BIRTH_LEAD.test_in(s, back(m, 8), m.start()) {
        return None;
    }
    if INFANT.test(s) && !ROMANTIC.test(s) && !THINGS.test(s) {
        kept(m, parent(m))
    } else {
        None
    }
}

fn child(m: &Match) -> V {
    let s = m.string;
    let word = st(m.group(1).unwrap_or(&[]));
    if !spoken(m) || AWAITED.test_in(s, back(m, 24), m.start()) || EXPECTED.test_in(s, back(m, 24), m.start()) && !LATER.test(m.text()) || DUE.at(s, m.end()).is_some() || CHILDLESS.test(s) {
        return None;
    }
    if ["baby", "babies", "bub", "bubba", "lo", "dc", "dcs"].contains(&word.as_str()) && (!INFANT.test(s) && !ORDINAL_RE.test(m.text()) || THINGS.test_in(s, back(m, 150), (m.end() + 150).min(s.len()))) {
        return None;
    }
    if word == "teen" && !TEEN_AGE.test(m.text()) {
        return None;
    }
    if ["youngest", "oldest", "eldest", "middle child"].contains(&word.as_str()) && (SIBLING.at(s, m.end()).is_some() || THINGS.test_in(s, back(m, 150), (m.end() + 150).min(s.len())) || RANKED.at(s, m.end()).is_none() && m.text().last() != Some(&'s')) {
        return None;
    }
    Some(parent(m))
}

fn raising(m: &Match) -> V {
    let text = m.text();
    if !starts_at(text, 0, "i") && !starts_at(text, 0, "we") && !LEADING.test_in(m.string, back(m, 16), m.start()) {
        return None;
    }
    if HAD_KIDS.test_in(m.string, sentence(m).0, m.start()) {
        None
    } else {
        has_children(m)
    }
}

fn parent_label(m: &Match) -> V {
    if OTHERS_PARENT.test_in(m.string, clause(m.string, m.start()), m.start()) || SOMEDAY.at(m.string, m.end()).is_some() {
        None
    } else {
        stated(m, &FUTURE, || kept(m, parent(m)))
    }
}

fn own_history(m: &Match) -> V {
    if HAD_KIDS.test_in(m.string, sentence_start(m), m.start()) || THEN_THIRD.at(m.string, m.end()).is_some() {
        None
    } else {
        has_children(m)
    }
}

fn has_children(m: &Match) -> V {
    if PENDING.test_in(m.string, back(m, 12), m.start()) && !contains(m.text(), "had") {
        return None;
    }
    stated(m, &FUTURE, || kept(m, parent(m)))
}

fn parent(m: &Match) -> &'static str {
    let text = m.text();
    if contains(text, "grand") || contains(text, "nana") || contains(text, "granny") {
        "grandparent"
    } else if contains(text, "step") {
        "stepparent"
    } else if SOLO_PARENT.test(text) {
        "single parent"
    } else if contains(text, "foster") || contains(text, "adopt") {
        "foster / adoptive parent"
    } else {
        "parent"
    }
}

fn kidless(m: &Match) -> Option<(&'static str, &'static str)> {
    let text = m.text();
    if contains(text, "dink") {
        Some(("parent_role", "dink"))
    } else if contains(text, "free") || CHOSEN.test(text) {
        Some(("parent_role", "childfree"))
    } else if UNABLE.test(text) {
        None
    } else {
        Some(("number_of_children", "0"))
    }
}

fn no_kids(pattern: &str, check: fn(&Match) -> bool, anchors: &[&str], hedge: Hedge) -> Vec<Rule> {
    ["parent_role", "number_of_children"]
        .into_iter()
        .map(|attribute| {
            let entry = r(attribute, pattern, move |m| if check(m) { kidless(m).filter(|(a, _)| *a == attribute).map(|(_, v)| v) } else { None }, hedge);
            if anchors.is_empty() { entry } else { needs(entry, anchors) }
        })
        .collect()
}

fn counted(m: &Match) -> V {
    let words = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
    let digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"];
    let index = (1..=m.groups()).filter_map(|g| m.nonempty(g)).map(st).find_map(|number| words.iter().position(|w| *w == number).or_else(|| digits.iter().position(|d| *d == number)))?;
    stated(m, &FUTURE, || kept(m, digits[index]))
}

fn experience(m: &Match) -> V {
    let order = st(m.first()?);
    let value = match order.as_str() {
        "first" | "1st" => "first-time mom (ftm)",
        "second" | "2nd" => "second-time mom (stm)",
        _ => "third-time or later mom (3tm+)",
    };
    stated(m, &FUTURE, || kept(m, value))
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let QUALIFIER = format!(r"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|")
        + r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)";
    let parents = ["mom", "mum", "mother", "dad", "father", "parent", "mama"];
    let mut rules = vec![
        r("parent_role", &format!(r"(?:my (?<=\bmy )|our (?<=\bour ))(?:{QUALIFIER}[- ,]+){{0,3}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|cups?|tits|boobs|sister|brother|face|fever|shower)\b)"), child, TAGGED),
        r("parent_role", &(format!(r"\b(?:my|our) (?!(?:future|dream|unborn|imaginary|dog|cat|pup|puppy|fur|furry|kitty|bunny|plant|pet|god|ex|friends?|neighbou?rs?|sisters?|brothers?|cousins?|boyfriends?|girlfriends?|wife|husband|partner|aunt|uncle|boss|inner|little|baby|big|good)\b)[a-z]+ ")
            + &format!(r"(?:{QUALIFIER}[- ,]+){{0,2}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|sister|brother|face|fever|shower)\b)")),
          |m| if m.group(1).map_or(false, |g| eq(g, "baby") || eq(g, "babies") || eq(g, "child")) { None } else { child(m) }, TAGGED),
        r("parent_role", r"the (?<=\bthe )(?:kids|kiddos|little ones?|toddler|twins|baby|babies|newborn)\b(?! (?:in|at|from|of|who|that|these|those|they|i|we|you)\b)",
          |m| if FIRST.test_in(m.string, back(m, 44), m.start()) && !TEACHING.test(m.string) && !(contains(m.text(), "bab") && EXPECTING.test(m.string)) { kept(m, parent(m)) } else { None }, TAGGED),
        r("parent_role", concat!(r"\b(?:i'm|im|i am|as an?|being an?) (?:a |an )?(?:sahm|sahd|wahm|wohm|wfhm|sahp)\b|(?:^", claimcore::flair!(), r"|(?<=[.!?\n]))\W*(?:sahm|sahd|wahm|wohm) here\b|\b(?:i'm|im|i am) (?:currently |now |also |still )?(?:parenting|co-?parenting) (?:a|an|my|our|two|three|four|\d)\b"), has_children, TAGGED),
        r("parent_role", r"\b(?:i|i'm|im|i am) (?:also |still |now )?(?:raise|raised|raising) (?:my|our) (?:[\w-]+ ){0,2}(?:kids?|children|child|sons?|daughters?|boys|girls|twins)(?: \w+)? (?:by myself|alone|on my own)\b|\b(?:i'm|im|i am|and am) (?:an? )?(?:single|solo|lone)[- ]?(?:parent|mom|mum|mother|dad|father|mama)\b(?!s|'s| friends?| groups?)|\b(?:i|we) (?:am|are|'m|'re)? ?(?:a )?single[- ]parent (?:family|household)\b|\b(?:my|i'm|im|i am) (?:\w+ )?(?:single motherhood|single fatherhood)\b", has_children, TAGGED),
        r("parent_role", r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:twins|triplets|kids|children)\b(?! (?:of|in|at|who|that)\b)", has_children, TAGGED),
        r("parent_role", concat!(r"\b(?:i|we)(?:'ve| have)? (?:also |both |still |even |do |did |already |now |currently )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}",
          r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)"),
          has_children, TAGGED),
        r("parent_role", &(format!(r"(?:{ME}|{AS}) (?:a|an) (?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b")
            + r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))"), has_children, TAGGED),
        needs(r("parent_role", r"(?<!dog )(?<!cat )(?<!fur )(?<!pet )(?<!plant )\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|teenager|preteen|kiddo|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", |m| if THIRD.test_in(m.string, sentence(m).0, m.start()) || NAMED.test_in(m.string, back(m, 40), m.start()) { None } else { has_children(m) }, TAGGED), &["mom", "mum", "mama", "mother", "dad", "father", "parent"]),
        needs(r("parent_role", r"\b(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|solo|widowed|separated|older|bi|boy|girl|twin|homeschool(?:ing)?|toddler|teen|preemie|nicu|autism|special needs|military|working[- ]class)[- ]?(?:dad|mom|mum|father|mother|mama|mommy|parent)\b(?!s|'s| bod| jokes?| energy| vibes| groups?| friends?| life| figure)",
          |m| if PARENT_LEAD.test_in(m.string, back(m, 60), m.start()) && !THIRD.test_in(m.string, sentence(m).0, m.start()) { has_children(m) } else { None }, TAGGED), &["dad", "mom", "mum", "father", "mother", "mama", "parent"]),
        r("parent_role", concat!(r"^", claimcore::flair!(), r"\W*[\[\(]?(?:\d{2}\s*[mf]?|[mf]\s*\d{2})\b[\]\)]?\W*(?:(?!dog|cat|fur|plant|pet|bonus|step|soccer|hockey|boy|girl|hot|pervy|horny|sexy|naughty|(?:my|ur|your|his|her|their|our|the|a)\b)\w+\s+){0,2}(?:mom|mum|mother|mommy|mama|dad|father)\b(?!s|'s| bod| jeans| energy| vibes| jokes?)"), |m| kept(m, parent(m)), TAGGED),
        r("parent_role", &(format!(r"\b\d{{2}}\s*[mf]?\s*,?\s*(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)|\bthe (?:kids|kiddos|children|twins|baby|little ones?) and (?:i|me)\b|\b(?:me|myself) (?:and|&) the (?:kids|kiddos|children|twins|baby|little ones?)\b|\bfellow (?:(?!dog|cat|pet|plant|fur|boy|girl)[\w-]+ ){{0,2}}(?:parent|mom|mum|dad|mother|father|mama)s?\b|\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?(?:\d+ |two |three |four )?{CHILD}\b")
            + r"|\b(?<![^\n.!?: ])(?<![^\n.!?:] )(?:the )?(?:wife|husband|hubby) (?:and|&) (?:the )?(?:\d+ |two |three )?(?:kids?|children|sons?|daughters?|boys|girls)\b|\b(?:i (?:also |already )?have|i've got|i got) an? (?:wife|husband|hubby) (?:and|&) (?:\d+|a|two|three|four|five) (?:kids?|children|sons?|daughters?|boys|girls)\b|\b(?:i (?:do |also |already )?have|i've got|we (?:do |also |already )?have|we've got) (?:a|an|one|two|three|\d) (?:1[0-7]|\d|one|two|three|four|five|six|seven|eight|nine|ten)(?!\d)(?: 1/2| and a half)?(?:[- ]?(?:year|yr|month|week|wk)s?[- ]?olds?|yo)\b(?=\s*(?:[^\w\s]|$)|\s+(?:and|who|that|at|in|so|but|sons?|daughters?|boys?|girls?|kids?|child|twins|which|i|we|he|she|they|is|was|whose|toddler|with|too|as|now|already|currently|plus|myself|of|my|baby|little|&))"),
          |m| kept(m, parent(m)), TAGGED),
        r("parent_role", &format!(r"\b(?:my|our) (\d+|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?(yo|y/o|year[- ]old|yr[- ]old|month[- ]old|week[- ]old)s?(?= (?!(?:{NOT_CHILD})\b)[a-z]+\b|[.,!?;)])"),
          |m| if m.group(2).map_or(false, |u| starts_at(u, 0, "y")) && m.group(1).map_or(false, |n| isdigit(n) && py_int(n).map_or(false, |v| v > 17)) { None } else { kept(m, parent(m)) }, TAGGED),
        r("parent_role", &format!(r"my (?<=\bmy )(?:now[- ]|almost[- ]|nearly[- ]|just[- ]turned[- ])?{YEARS}[- ]?(?:(years?|yrs?|months?|weeks?|wks?)[- ]olds?|(yo|y/o|mo|mos|m/o))\b(?! (?:{NOT_CHILD})\b)"), aged, TAGGED),
        r("family_building_stage", concat!(r"\b(?:i'm|im|i am) (?:currently |now |almost |nearly |only |just |about |officially )?\d{1,2}(?:\+\d)? ?(?:w|wks?|weeks?)(?: along| pregnant|(?: and)? \d ?d(?:ays?)?)?\b(?! (?:sober|clean|out|post|into|off|postpartum|in|of|until|from|ago|later|since|after|before|without|free|smoke|nicotine|vape))",
          r"|\b\d{1,2} ?(?:weeks?|wks?) along\b|\bwe(?:'re| are) (?:having|expecting) (?:a baby|twins|a boy|a girl|our (?:first|second|third|rainbow)|another|baby)\b|\bi(?:'m| am) having (?:a baby|twins|my (?:first|second|third) (?:baby|child))\b|\b(?:my|our) (?:due date|anatomy scan|nipt|nt scan|gender reveal|baby shower|glucose test)\b"),
          |m| stated(m, &FUTURE, || Some("pregnant")), TAGGED),
        r("parent_role", concat!(r"\b(?:meine?[nmrs]?|mein|unser\w*|mi|mis|mon|ma|mes|notre|nuestr[oa]s?|noss[oa]s?|onze|nostr[oaie]|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|mie|miei)\s+(?:(?!inner)\w+\s+)?(?:tochter|sohn|kinder|kindern|kind(?! of)|kids|söhne|söhnen|töchter|töchtern|hijo|hija|hijos|hijas|fils|fille|filles|enfants|enfant|filho|filha|filhos|filhas|zoon|zonen|dochter|dochters|kinderen|córka|syn|dzieci|figlio|figlia|figli|figlie|bimba|bimbo|bambin[oaie])\b|\bnos (?:enfants|filles|fils)\b",
          r"|\b(?:ich habe|ich hab|wir haben|tengo|tenemos|j'ai|nous avons|eu tenho|tenho|temos|ik heb|wij hebben|we hebben|ho|abbiamo|jeg har|vi har|jag har) (?:(?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre|to|fire|två|fyra|\d) (?:\w+ )?|des |dei )?",
          r"(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia|børn|barn|unger|døtre|sønner|söner|döttrar|søn|sønn|datter|dotter)\b"),
          |m| if NEGATED.test_in(m.string, back(m, 5), m.start()) { None } else { stated(m, &FUTURE, || Some(parent(m))) }, TAGGED),
        r("parent_role", r"\b(?:min|mitt|mina|mit|mine|vores|våra|vår|vårt) (?:(?:lille|lilla|store|stora|yngste|ældste|eldste|äldsta|yngsta|to|tre|två) )?(?:son|søn|sønn|dotter|datter|døtre|döttrar|söner|sønner|barn|børn|unger)\b|\b(?:a |az )?(?:fiam|lányom|gyerekem|gyerekeim|kisfiam|kislányom)\b|\b(?:můj|moje|mého|mojí) (?:syn|dcera|děti|dítě|dceru|syna)\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) meu\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) (?:meu|mea|mei)\b|\b(?:mi|mis) (?:niño|niña|niños|niñas|bebé)\b",
          |m| stated(m, &FUTURE, || Some(parent(m))), TAGGED),
        r("family_building_stage", r"\b(?:estoy|estou|je suis|ich bin|sono|ik ben|jestem|jeg er|jag är)(?: (?!(?:pas|plus|jamais|nicht|nie|kein\w*|no|non|não|nao|nunca|niet|geen|ikke|inte)\b)[\w.]+){0,3}? (?:embarazada|grávida|gravida|enceinte|schwanger|incinta|zwanger|gravid|w ciąży)\b|\bbin (?:\w+ )?in der \d{1,2}\.? ?ssw\b|\bя беременна\b|\bhamileyim\b|\bbuntis ako\b", |m| stated(m, &FUTURE, || Some("pregnant")), TAGGED),
        r("parent_role", concat!(r"\b(?:i'm|im|i am) (?:\d+ ?(?:weeks?|months?) )?post[- ]?partum\b|\bmy post[- ]?partum\b|\b\d+ ?(?:weeks?|months?|days?) post[- ]?partum\b|\b(?:since|after|when|before) (?:giving birth|i gave birth|(?:having|i had) my (?:\w+ )?(?:baby|son|daughter|kids?|child|children|first|second|third|twins|lo|youngest|oldest|little))\b|\bi gave birth\b|\bmy last pregnancy\b",
          r"|\bmy (?:c-section|c section|labor and delivery|birth story|epidural|maternity leave|paternity leave)\b|\bi(?:'m| am)? (?:still |exclusively |currently )?(?:breastfeeding|breastfed|ebf)\b|\bbreastfeeding my\b|\bnursing my (?:son|daughter|baby)\b"), own_history, TAGGED),
        r("family_building_stage", concat!(r"\b(?:i'm|im|i am) (?:currently |now |finally |also )?(?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+(?:\+\d)? ?(?:weeks?|wks?|months?) pregnant\b|\b(?:i'm|im|i am|we're|we are) expecting(?= (?:a baby|our|my|twins|baby|a little|a boy|a girl|in|again)\b|[.!,]|$)",
          r"|\bmy current pregnancy\b|\bthis pregnancy\b|\bthis is my (?:first|second|third|fourth|\d(?:st|nd|rd|th)) pregnancy\b|\bcurrently expecting (?:our|my|a|baby|twins)\b|\bmy (?:first|second|third) trimester\b|\b(?:my|our) unborn (?:baby|child|son|daughter|twins)\b|\b(?:my|our) baby bump\b|\bpregnant with (?:my|our) (?:first|second|third|\d|rainbow|twins|baby)\b|\bbaby (?:#|number )?\d on the way\b|\b(?:our|my) baby on the way\b|\b(?:i|we) (?:have|'ve got|got) (?:a|another) baby on the way\b",
          r"|\b(?:i'm|im|i am) due (?:in|next|this|any day|soon)\b|\bmy scheduled induction\b|\bcurrently pregnant\b|\bpregnant currently\b|\b(?:i'm|im|i am) currently \d+ ?(?:weeks|wks)\b|\bpregnant with (?:number|#|baby|no\.?) ?\d\b"),
          |m| if PAST.test_in(m.string, back(m, 20), m.start()) || LIKENED.test_in(m.string, back(m, 24), m.start()) { None } else { stated(m, &FUTURE, || Some("pregnant")) }, TAGGED),
        r("parent_role", concat!(r"\b(?:after|before|since) (?:i had|having) (?:my|our) (?:first|second|third|son|daughter|kids?|children|baby|babies)\b",
          r"|\bbefore i (?:got|became|was) pregnant (?:the first time|with (?:my|our))\b|\bafter my (?:first|second|third|last|previous|\d+(?:st|nd|rd|th)) pregnancy\b|\bwhen (?:i|we) had (?:my|our) (?:first|second|son|daughter|kids?|baby)\b"), own_history, TAGGED),
        r("parent_role", concat!(r"\b(?:after|since|before(?= (?:just )?having (?:a|my|our|\d|two|three|four) )) (?:just )?having (?:a |my |our |\d |two |three |four |the )?(?:\w+ )?(?:baby|babies|kids?|children|child|twins|son|daughter)\b|\bafter (?:having )?baby\b|\bafter i had my (?:\w+ )?(?:baby|son|daughter|kids?|first|second|third|twins)\b",
          r"|\b\d+ ?(?:years?|yrs?) post[- ]?partum\b|\b(?:i'm|im|i am) \d+ ?(?:weeks?|months?|wks?|mos?) pp\b|\b(?:my|both of my|all of my|each of my|all my|both my) (?:\w+ )?pregnancies\b|\b(?:i|since i|after i|when i) (?:just |recently |finally )?became a (?:\w+ )?(?:mom|mum|mother|dad|father|parent)\b",
          r"|\b(?:we|i) (?:just |recently )?had (?:a|our|my) (?:\w+ )?(?:baby|child|son|daughter)\b(?! (?:shower|of|in))|\b(?!married with children\b)(?:married|divorced|single|separated|widowed) (?:for (?:\d+|a few|many|\w+) (?:years?|months?) )?(?:with|w/) (?:(?:\d+|one|two|three|four|five|a|an) )?(?:(?!no\b)\w+ )?(?:kids?|kiddos?|children|child|sons?|daughters?|boys|girls|toddlers?|teens|babies|baby)\b",
          r"|\b(?<!\d[.,])(?<![^\n,;:(|/.!? ])(?<![^\n,;:(|/.!?] )(?:\d|two|three|four|five) (?:kids|children|teens|kinder|kinderen|hijos|enfants|filhos|figli|børn|dzieci|děti)\b|\bkids\s*:\s*[1-9]",
          r"|\b(?:i was|i got|i had to be) induced\b|\bmy waters? broke\b|\bi was in labou?r\b|\b(?:both|all) (?:of )?my (?:births|deliveries|labou?rs)\b|\bi(?: had|'ve had| have had) (?:two |three |\d |a |an )?(?:c-?sections?|vaginal births?|home births?|natural births?|unmedicated births?)\b"), own_history, TAGGED),
        r("parent_role", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:two|three|four|five|\d|twin|little|baby|eldest|oldest|youngest|middle|teenage|fourth|third|second|first) (?:(?:little|teenage|baby|twin|young|younger|older|grown|adult) )?(boys|girls|boy|girl)\b", child, TAGGED),
        r("parent_role", r"(?:baby|toddler|kiddo|lo|bub) (?:is|was|has|had|decided|needs|got|will|sleeps|slept|woke|wakes|just|still|started|loves|hates|refuses|won't|doesn't|did|turned|takes|eats|arrived|came)\b", parenting, TAGGED),
        r("parent_role", &format!(r"(?:my (?<=\bmy )|our (?<=\bour )){ORDINAL}(?: one| two| three)?(?=[.,!?;)]|$| (?:and|but|at|in|i|we|he|she|they|it|was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b)"), birth_order, TAGGED),
        needs(r("parent_role", &(format!(r"(?:(?:i(?<=\bi)|we(?<=\bwe))(?:'ve| have)? (?:also |both |still |even |do |did |already |now |currently |usually |only )?(?:have|had|got|raised|birthed)")
            + &format!(r"|(?:have|had|got|raised)(?<![\w'-]have)(?<![\w'-]had)(?<![\w'-]got)(?<![\w'-]raised)) {KID_COUNT}{KID_WORDS}{KID_NOUN}{KID_AFTER}")), raising, TAGGED),
          &["kid", "child", "son", "daughter", "toddler", "teen", "newborn", "infant", "twin", "triplet", "step", "grand", "old"]),
        needs(r("parent_role", &format!(r"{ME} (?:\w+,? ){{1,3}}and an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band)\w+ )?(?:mom|mum|mother|dad|father|parent)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur))|\b\d{{2}}\s*(?:yo|y/o|years? old|year-old|yr old|yrs old)\s*,?\s*(?:(?!dog|cat|pet|plant|fur|boy|girl)\w+ )?(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)"),
          parent_label, TAGGED), &parents),
        needs(r("parent_role", r"\b(?:as|being) an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band|bonus|future|good|bad)\w+ )?(?:mom|mum|mother|dad|father|parent|mama|mommy)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur)| figure| friend)",
          |m| { let (a, b) = sentence(m); if SELF.test_in(m.string, a, b) && !OTHER_PERSON.test_in(m.string, a, m.start()) && !SUBJECT.test_in(m.string, back(m, 30), m.start()) { parent_label(m) } else { None } }, TAGGED), &parents),
        needs(r("parent_role", r"(?<![^\n,;:(|/ ])(?<![^\n,;:(|/] )(?:(?:\d|two|three|four|five) )?(?:grown|adult|young|teenage|little|small|older|younger) (?:kids|children)\b(?=\s*(?:[,;.)/&\n]|$|and\b))", |m| if SELF.test(m.string) { stated(m, &FUTURE, || kept(m, parent(m))) } else { None }, TAGGED), &["kids", "children"]),
        needs(r("parent_role", concat!(r"(?:^", claimcore::flair!(), r"|(?<=[.!?\n])\s*)with (?:\d|two|three|four|five|six|my|our) (?:(?:young|little|small|teenage|grown|adult) )?(?:kids|children|boys|girls|toddlers|teens)\b|\bwith (?:a |my |the )?(?:wife|husband|hubby) (?:and|&) (?:(?:\d|two|three|four|five) )?(?:kids?|children|boys|girls|sons?|daughters?)\b"), |m| if SELF.test(m.string) && !PRONOUN.test_in(m.string, sentence(m).0, m.start()) { stated(m, &FUTURE, || kept(m, parent(m))) } else { None }, TAGGED), &["with"]),
        r("parent_role", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:\d+ |two |three |four )?(teens|newborns|preschoolers|boys|girls)\b(?= (?:are|were|turned|just turned|is) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|both|now|almost|only)\b)|(?:my (?<=\bmy )|our (?<=\bour ))(?:\d+ |two |three |four )(teens|newborns|preschoolers)\b", child, TAGGED),
        needs(r("family_building_stage", r"\b(?:i'm|im|i am) (?:\d+ ?(?:days?|weeks?|wks?|months?|mos?) )?post[- ]?partum\b(?! (?:depression|anxiety|psychosis|ocd|rage)\b)|(?<!at )\b\d+ ?(?:days?|weeks?|wks?|months?|mos?) (?:post[- ]?partum|pp)\b(?! (?:depression|anxiety|psychosis|ocd|rage)\b)|\bi (?:just |recently )gave birth\b",
          |m| stated(m, &FUTURE, || kept(m, "postpartum")), TAGGED), &["partum", "pp", "gave birth"]),
        needs(r("family_building_stage", r"\bttc ?# ?\d\b|\bttc since\b|\band i are (?:now |currently |actively )?(?:ttc|trying to conceive|trying for a baby)\b|\b(?:i'm|im|i am|we're|we are|i've been|we've been|been|currently|we started|i started|we just started) (?:currently |actively |now |officially )?(?:ttc|trying to conceive|trying for (?:a baby|baby (?:#|number )?\d|our (?:first|second|third|rainbow)|another baby|a second|number \d|#\d))\b",
          |m| stated(m, &FUTURE, || kept(m, "trying to conceive")), TAGGED), &["ttc", "conceive", "trying for"]),
        needs(r("family_building_stage", r"\b(?:i'm|im|i am|we're|we are|i've been|we've been|currently|i just|we just) (?:currently |now |also )?(?:going through|doing|undergoing|starting|started|in the middle of) (?:ivf|iui|fertility treatments?)\b|\b(?:my|our) (?:first |second |third |next |last |current |upcoming |\d(?:st|nd|rd|th) )?(?:ivf|iui|egg retrieval|embryo transfer|frozen embryo transfer|fet)(?: cycle| journey| round| clinic| transfer)?\b(?! (?:baby|babies|son|daughter|twins|kids?|child)\b)|\b(?:ivf|fet|iui) ?# ?\d\b",
          |m| stated(m, &FUTURE, || kept(m, "ivf / assisted conception")), TAGGED), &["ivf", "iui", "fertility", "retrieval", "transfer", "fet"]),
        needs(r("family_building_stage", r"\bi (?:just |recently )?(?:had|have had|'ve had|suffered|experienced|went through) (?:a |an |my |two |three |\d )?(?:(?:early|late|missed|second|third|recent|first) )?(?:miscarriages?|mmc|chemical pregnanc(?:y|ies)|ectopic(?: pregnancy)?|stillbirth|pregnancy loss(?:es)?)\b|\bi (?:just |recently )?miscarried\b|\b(?:my|our) (?:recent |first |second |last |early |missed )?(?:miscarriage|mmc|ectopic pregnancy|stillbirth|tfmr|pregnancy loss)\b|\b\d mmcs?\b",
          |m| stated(m, &FUTURE, || kept(m, "pregnancy loss")), TAGGED), &["miscarr", "mmc", "chemical", "ectopic", "stillbirth", "loss", "tfmr"]),
        needs(r("parenting_experience", r"^r/\w*(?:bump|baby|babies|mom|mum|parent|pregnan|birth|ttc|toddler)\w*:\s*(?:[^\n]*?\|\s*)?(ftm|stm|[3-9]tm|first[- ]time mom|second[- ]time mom)\b|\b(?:i'm|im|i am) an? (stm|[3-9]tm)\b|\b(stm|[3-9]tm) due\b", |m| { let order = m.first()?; Some(if starts_at(order, 0, "f") { "first-time mom (ftm)" } else if starts_at(order, 0, "s") { "second-time mom (stm)" } else { "third-time or later mom (3tm+)" }) }, TAGGED), &["ftm", "stm", "tm", "time mom"]),
        needs(r("parent_role", r"^r/\w+:\s*(?:[^\n|]*\|\s*)?(?:(?:parent|mom|mum|dad|mother|father|mama|first[- ]time (?:mom|dad|mum)|single (?:mom|dad|parent|mum)|step-?mom|step-?dad|step-?parent|grandma|grandpa|grandparent)\s*(?:$|[|\n])|(?:mom|mum|dad|mama|father|mother|parent) (?:to|of) (?:\d|one|two|three|four|five|twins|an? \d))", |m| Some(parent(m)), TAGGED), &["parent", "mom", "mum", "dad", "mother", "father", "mama", "grand"]),
        needs(r("number_of_children", r"\b(?:ich habe|habe|hab|ik heb|tengo|tenho|j'ai|ho)(?: (?:selbst|zelf|auch|ook|también|tambem|também|aussi|anche|nur|alleen|solo|sólo))? (\d|zwei|drei|vier|twee|drie|dos|tres|cuatro|deux|trois|quatre|dois|duas|três|due|tre|ein|eine|einen|een|un|une|uno|una|um|uma)(?: \w+)? (?:kinder|kinderen|kind|kindje|hijos|hijas|hijo|hija|filhos|filhas|filho|filha|enfants|enfant|figli|figlie|figlio|figlia)\b|\b(\d|egy|két|három) gyerekem\b", |m| stated(m, &FUTURE, || get(FOREIGN_COUNTS, m.first())), TAGGED), &["kind", "hij", "filh", "enfant", "figli", "gyerek"]),
        needs(r("parenting_experience", concat!(r"\b(?:i'm|im|i am|as) an? (?:\w+ )?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)[- ]time (?:mom|mum|mama|mother|mommy)\b|(?:^", claimcore::flair!(), r"|[\n.!?]\s*)(first|second|third)[- ]time (?:mom|mum|mama|mother) here\b"),
          experience, TAGGED), &["time mom", "time mum", "time mama", "time mother"]),
        needs(r("number_of_children", &format!(r"(?:\b(?:i|we)(?:'ve| have)? (?:(?:also|both|still|already|now|only|currently|do|actually) )?(?:have|got|have got|raised|had)|\band (?:also |now )?have) (?:only |just )?{COUNT} (?:(?:{FONDLY}|special needs|autistic|biological|bio) ){{0,2}}(?:kids?|children|child|kiddos?|sons|daughters)\b(?! (?:of (?!(?:my|our) own)|in|at|who|that|from|on|to|over|come|came|visit|visiting|for|today|tonight|this|that|last|more)\b)"),
          |m| if SELF.test(m.string) && !PRONOUN.test_in(m.string, sentence_start(m), m.start()) { counted(m) } else { None }, TAGGED), &["kid", "child", "son", "daughter"]),
        needs(r("number_of_children", concat!(r"\b(?:(?:i'm|im|i am|as) an? (?:(?!(?:cat|dog|fur|pet|plant|puppy|kitty|bunny|chicken|horse|goat|bird|fish|reptile|snake|rabbit)\b)\w+ )?|(?:^", claimcore::flair!(), r"|[\n.!?:|]\s*)(?:\d{2}\s*[mf]?\s*,?\s*)?(?:proud |single )?)(?:mom|mum|mama|mother|dad|father|parent)(?:s)? (?:of|to) (\d|one|two|three|four|five|six|seven|eight|nine|ten)(?: (?:kids|children|kiddos|boys|girls|little ones|under \w+))?\b(?! (?:dogs?|cats?|pets?|fur|plants?|pups?|puppies|kittens?|\w+ (?:dogs?|cats?|pups?))\b)"),
          owner_count, TAGGED), &["mom", "mum", "mama", "mother", "dad", "father", "parent"]),
        needs(r("number_of_children", &format!(r"(?:my (?<=\bmy )|our (?<=\bour )){COUNT} (?:{FONDLY} )?(?:kids|children|kiddos|little ones)\b(?!'| of (?!(?:my|our) own)| (?:in law|in-law)\b)"), counted, TAGGED), &["kid", "child", "little ones"]),
        needs(r("number_of_children", &format!(r"(?<![^\n,;:(|/.!?])[ \t]*{COUNT} (?:{FONDLY} )?(?:kids|children|kiddos|sons|daughters)(?=\s*(?:[,;.|/)\n&]|$|and\b))|\b(?:kids|children)\s*[:=]\s*(\d)\b"), |m| if PRONOUN.test_in(m.string, line_start(m.string, m.start()), m.start()) || KIN_BEFORE.test_in(m.string, sentence_start(m), m.start()) || !SELF.test(m.string) && !TAGGED_LINE.test_in(m.string, line_start(m.string, m.start()), m.start()) && !FLAIR.test(m.string) { None } else { counted(m) }, TAGGED), &["kid", "child", "son", "daughter"]),
        needs(r("number_of_children", &format!(r"(?:\b(?:married|divorced|single|separated|widowed|(?:single|divorced|married|widowed|working|busy|solo) (?:mom|mum|dad|father|mother|parent|man|woman|guy|lady|male|female|gal|dude)|\d{{2}}\s*[mf]?|[mf]\s*\d{{2}})\s*,?\s*|(?:(?<![^\n.!?])|\A{flair})\s*)(?:with|w/) {COUNT} (?:{FONDLY} )?(?:kids|children|kiddos|child)\b", flair = claimcore::flair!()), owner_count, TAGGED), &["with", "w/"]),
        needs(r("number_of_children", &format!(r"(?:\b(?:being|and|also|just)(?: already| now)?|([,;(])) ?an? (?:(?!(?:cat|dog|fur|pet|plant|puppy|kitty|bunny|chicken|horse|goat|bird|fish|reptile|snake|rabbit)\b)[\w-]+ )?(?:mom|mum|mama|mother|dad|father|parent) (?:of|to) {COUNT}(?: (?:{FONDLY} )?(?:kids|children|kiddos|boys|girls|little ones))?\b(?! (?:dogs?|cats?|pets?|fur|plants?|pups?|puppies|kittens?|\w+ (?:dogs?|cats?|pups?))\b)|(?:(?<![^\n.!?])|\A{flair})\s*(?:(?!(?:her|his|their|your|my|our|the|another|this|that|every|any|some|each|one|no|cat|dog|fur|pet|plant|puppy|kitty|bunny|chicken|horse|goat|bird|fish|reptile|snake|rabbit)\b)[\w-]+ ){{1,2}}(?:mom|mum|mama|mother|dad|father|parent) (?:of|to) {COUNT}(?: (?:{FONDLY} )?(?:kids|children|kiddos|boys|girls|little ones))?\b(?! (?:dogs?|cats?|pets?|fur|plants?|pups?|puppies|kittens?|\w+ (?:dogs?|cats?|pups?))\b)", flair = claimcore::flair!()), |m| if m.group(1).is_some() && !SELF.test_in(m.string, sentence_start(m), m.start()) { None } else { owner_count(m) }, TAGGED), &["mom", "mum", "mama", "mother", "dad", "father", "parent"]),
        needs(r("number_of_children", &format!(r"\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?{COUNT} (?:{FONDLY} )?(?:kids|children|kiddos)\b"), counted, TAGGED), &["kid", "child"]),
        needs(r("number_of_children", r"\bboth (?:of )?(?:my|our) (?:kids|children)\b|\b(?:my|our) only (?:child|kid)\b(?![- ]free)", |m| stated(m, &FUTURE, || kept(m, if contains(m.text(), "both") { "2" } else { "1" })), TAGGED), &["both", "only"]),
        needs(r("parent_role", r"\b(?:i'm|im|i am|as) an? (?:\w+ )?(?:foster|adoptive) (?:mom|mum|mama|mother|dad|father|parent)\b|\b(?:my|our) (?:\w+ )?(?:foster|adopted) (?:son|daughter|kids?|children|child|baby|boy|girl)\b|\b(?:we|i) (?:just |recently )?adopted (?:our|my) (?:\w+ )?(?:son|daughter|kids?|children|child|baby|boy|girl)\b",
          |m| stated(m, &FUTURE, || if THINGS.test_in(m.string, sentence(m).0, sentence(m).1) { None } else { kept(m, "foster / adoptive parent") }), TAGGED), &["foster", "adopt"]),
        needs(r("parent_role", r"\b(?:boy|girl)[- ]?(?:mom|mum|mama|dad)\b(?!s\b|'s\b| (?:energy|vibes|jokes?|bod|core|aesthetic|culture|club|clothes|shoes|stuff)\b)",
          |m| if THIRD.test_in(m.string, sentence_start(m), m.start()) { None } else if PARENT_LEAD.test_in(m.string, back(m, 60), m.start()) || PROUD.test_in(m.string, back(m, 24), m.start()) { stated(m, &FUTURE, || kept(m, "boy mom / girl dad")) } else { None }, TAGGED), &["boy", "girl"]),
        needs(r("parent_role", concat!(r"\b(?:i'm|im|i am|we're|we are|as|being|now|newly|recently|officially|new)(?: (?:an?|now|officially|newly|recently|new|finally|both))* empty[- ]?nesters?\b|(?:^", claimcore::flair!(), r"|[\n.!?]\s*)(?:\d{2}\s*[mf]?\s*,?\s*)?(?:(?:new|newly|recent|happy) )?empty[- ]?nesters?\b(?! (?:are|who|that|often|tend)\b)|\b(?:my|our) (?:new )?empty nest\b"),
          |m| if SELF.test_in(m.string, sentence(m).0, sentence(m).1) || starts_at(m.text(), 0, "i") || starts_at(m.text(), 0, "we") { stated(m, &FUTURE, || kept(m, "empty nester")) } else { None }, TAGGED), &["empty"]),
    ];
    let none: &[&str] = &[];
    let kidless: [(&str, fn(&Match) -> bool, &[&str], Hedge); 7] = [
        (r"\bno (?:kids|children)\b(?! (?:allowed|please|zone|menu|under|in|at|on|were|are|will))|\b(?:keine kinder|sin hijos|sem filhos|sans enfants?|geen kinderen|senza figli|ingen børn|inga barn)\b", |m| LISTED.test_in(m.string, 0, m.start()) || NO_MORE.at(m.string, m.end()).is_some() || SELF.test_in(m.string, back(m, 40), m.start()), none, Some(&*CONDITIONAL)),
        (concat!(r"(?<=[,;:]) ?child[- ]?free\b(?=\s*(?:[,;.&/)\n]|$|and\b))|(?:^", claimcore::flair!(), r"|(?<=[.!?\n]))\W*(?:(?:voluntarily|happily|proudly|intentionally|firmly|staunchly) )?child[- ]?free\b(?=\s*(?:[,;.!&/)\n]|$))"), |_| true, none, TAGGED),
        (r"\b(?:i|we) (?:have|got) no (?:kids|children|child)\b|\bno (?:kids|children) (?:yet|of (?:my|our) own|here|for me)\b|\b(?:i|we) (?:don't|do not|dont) have (?:any )?(?:kids|children) (?:yet|of (?:my|our) own)\b|\bi(?:'ve| have) no (?:kids|children)\b", |_| true, none, Some(&*CONDITIONAL)),
        (concat!(r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\b(?:i'm|im|i am|we're|we are|as an?) (?:\w+,? )?child[- ]?free\b|\bno kids of my own\b|\bi(?:'ve| have) never had (?:kids|children)\b|\bwe (?:don't|do not|dont) have (?:any )?(?:kids|children)\b",
          r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b",
          r"|\b(?:i|we) (?:love |enjoy )?being (?:kid|child)[- ]?free\b|\b(?:i|we) (?:can't|cannot|can not|couldn't|could not|wasn't able to|weren't able to|was never able to|am not able to) (?:have (?:kids|children|a baby|babies|a child)|conceive)\b",
          r"|\bneither of us (?:is|are|can|was|were) (?:able to )?(?:have|has) (?:kids|children)\b|\bi(?:'m| am) infertile\b|\b(?:ich habe|ich hab|wir haben) (?:noch |gar |auch )?keine? (?:kind|kinder)\b|\b(?:je n'ai|nous n'avons) pas d'enfants?\b|\bno (?:tengo|tenemos) hijos?\b|\bn[ãa]o (?:tenho|temos) filhos?\b|\bnon (?:ho|abbiamo) figli\b|\b(?:ik|wij|we) (?:heb|hebben) geen kinderen\b|\b(?:jeg|vi) har ingen børn\b|\b(?:jag|vi) har inga barn\b|\b(?:nemám|nemáme) (?:\w+ )?děti\b|\bděti nemám\b|\bje ne suis pas (?:père|mère)\b",
          r"|\bi (?:also |still |just |really |even |currently |personally |myself |actually )(?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\bi (?:\w+ )?(?:don't|do not|dont|never) (?:ever )?want(?:ed)? (?:any )?(?:kids|children)\b|\bi (?:also )?never (?:married or )?had (?:any )?(?:kids|children)\b|\b(?:i'm|im|i am|i ain't|i aint) (?:not |never )having (?:any )?(?:kids|children)\b|\bno dependents\b"), |_| true, &["kid", "child", "mom", "mum", "mother", "dad", "father", "parent", "dink", "bab", "conceive", "infertile", "kind", "enfant", "hijo", "filho", "figli", "børn", "barn", "děti", "père", "mère", "dependents"], Some(&*CONDITIONAL)),
        (concat!(r"\b(?:i|we)(?:'ve| have|'d| would)? (?:(?:also|still|just|really|even|currently|personally|myself|actually|honestly|definitely|absolutely|both|already|truly|simply|ever) ){0,2}(?:don't|do not|dont|never|won't|will not|wont) (?:(?:ever|even|really|actually|currently|plan to|intend to|wanna|want to|want|wanted) ){0,2}(?:have|want|wanted|plan on having) (?:any )?(?:nor want )?(?:kids|children|a kid|a child)\b",
          r"|\b(?:i|we) (?:\w+ )?(?:enjoy|love|like|prefer|chose|choose|decided on) (?:not having|being without) (?:any )?(?:kids|children)\b|\band (?:i )?(?:also )?(?:don't|do not|dont) have (?:any )?(?:kids|children)\b"), |m| !(starts_at(m.text(), 0, "and") && !FIRST.test_in(m.string, sentence(m).0, m.start())), &["kid", "child"], Some(&*CONDITIONAL)),
        (concat!(r"(?:^", claimcore::flair!(), r"|(?<=[\n.!?])\s*)no (?:kids|children)(?=\s*(?:[.,;!\n)]|$|and\b|but\b|yet\b))"), |m| SELF.test(m.string), &["no kids", "no children"], Some(&*CONDITIONAL)),
        (r"\bi(?:'ve| have) not had (?:any )?(?:kids|children)\b|\b(?:don't|do not|dont) have any (?:of )?my own\b", |m| !(contains(m.text(), "own") && !KIDS_WORD.test_in(m.string, sentence(m).0, m.start())), &["not had", "my own"], Some(&*CONDITIONAL)),
    ];
    for (pattern, check, anchors, hedge) in kidless {
        rules.extend(no_kids(pattern, check, anchors, hedge));
    }
    rules
}
