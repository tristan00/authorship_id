use crate::shared::*;
use claimcore::*;

const CHILD: &str = concat!(
    r"(sons?|daughters?|kids?|kiddos?|children|child|toddlers?|twins|triplets|step-?kids|step-?sons?|step-?daughters?|newborn|infant|teenagers?|teen|little ones?|babies|baby|bub|bubba|",
    r"first ?born|lo|dc|dcs|bio kids|youngest|oldest|eldest|middle child|offspring|bairns?|sprogs?|tweens?|preteens?|pre-teens?|preschoolers?|kindergart(?:e)?ners?|(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth) graders?)"
);
const AGE: &str = r"(?:\d+|one|two|three|four|five|six)[- ]?(?:yo|y/o|yr|yrs|years?|months?|mo|m/o|weeks?|wk|wks)?(?:[- ]old)?";
const YEARS: &str = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)";
const NOT_CHILD: &str = concat!(
    r"(?:rescues?|fosters?|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|horses?|pony|birds?|cars?|trucks?|vans?|bikes?|house|home|laptop|computer|pc|phone|tv|account|self|body|brother|sister|cousin|nephew|niece|friend|student|students|",
    r"client|patient|boyfriend|girlfriend|bf|gf|husband|wife|grand\w*|mattress|bed|couch|boat|shoes|iphone|ipad|tablet|macbook|build|rig|tires?|battery|knees?|back|hips?)"
);
const ORDINAL: &str = r"(?:first|second|third|fourth|1st|2nd|3rd|4th)";
const KID_NOUN: &str = concat!(
    r"(?:kids?|kiddos?|children|child|sons?|daughters?|toddlers?|teens|teenagers|newborn|infant|twins|triplets|stepkids|step-?sons?|step-?daughters?|grandkids|grandchildren|",
    r"(?:1[0-7]|[1-9]|one|two|three|four|five|six|seven|eight|nine|ten)(?:[.,]5| 1/2| and a half)?[- ]?(?:years?|yrs?|y/o|yo|months?|mos?|weeks?|wks?)[- ]?olds?)"
);
const KID_COUNT: &str = r"(?:(?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|my|our|several|multiple) )?";
const KID_WORDS: &str = r"(?:(?!(?:no|any|not|never|to|been|seen|met|heard|watched|known|taught|worked|told|asked|other|those|these|the|this|that|your|his|her|their|some|many|lots|plenty|more|enough|of|with|in|at|for|on|by|from|about|like|as|until|till|since|when|after|before|and|or|but|so|then|than)\b)(?![a-z]+ed\b)[a-z\d-]+ ){0,2}";
const KID_AFTER: &str = r"\b(?!'s|'| (?:of|in law|in-law|in (?:my|the|our|his|her|class|school)|at|who|that|from|come|came|ask|asked|tell|told|say|said|walk|walked|run|ran|on|over|when|someday|before|edition|dogs?|cats?|pups?|puppy|car|house|laptop|phone)\b)";

regex!(INFANT, concat!(
    r"months? old|weeks? old|\d+ ?(?:mo|m/o|wks?)\b|nappies|nappy|diapers?|crib|cot\b|formula|feeds?\b|feeding|daycare|nursery|pediatrician|paediatrician|newborn|toddler|teething|breastfe|bottle|sleep regression|stroller|pram|onesie|bassinet|car seat|",
    r"kindergarten|preschool|school|daughter|son\b|mama|mommy|crawl|walking|talking|nap|\bborn\b|birth|pregnan|labou?r|deliver|milk|pump|nurs|ultrasound|\bob\b|\bweeks\b|\bmonths\b|teeth|tooth|\bcry|sleep"
));
regex!(PARENT_LEAD, format!(r"(?:{ME} an? |\bas an? |\bbeing an? |^\W*|[\n.!?]\s*|\b\d{{2}}\s*[mf]?\s*[,-]?\s*|[\]\)]\s*|[-|:]\s+|\b[mf]4[mfat]\w*\s*)(?:(?!my |his |her |your |their |our |the |a )[\w,-]+ ){{0,3}}$"));
regex!(ROMANTIC, r"\b(?:bf|gf|boyfriend|girlfriend|husband|hubby|wife|daddy|sex|sexy|cock|dick|pussy|fuck\w*|kiss\w*|cuddl\w*|horny|nsfw|lover|honey|babe|dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?)\b");
regex!(PAST, r"\b(?:was|were|been)\s+(?:\w+\s+)?$");
regex!(PRONOUN, r"\b(?:he|she|him|her|his|they|them|their)\b");
regex!(FIRST, r"\b(?:i|we)\b[^.!?\n]{0,40}$");
regex!(TEACHING, r"\b(?:teach|teacher|class|classroom|students?|school|nanny|babysit\w*|camp|coach\w*|daycare|work)\b");
regex!(LISTED, r"(?:^|[,;:]\s*|\b(?:single|married|divorced|no partner|no pets|no debt|\d{2}\s*[mf]?)\s*[,;&/]\s*(?:and )?)$");
regex!(BABY_LEAD, r"(?:^|[.!?\n]\s*|\b(?:and|but|so|when|while|until|because|since|for|with|myself and|me and) )$");
regex!(NEGATED, r"\b(?:no|não|nao|non) $");
regex!(THINGS, r"\b(?:dogs?|cats?|pups?|puppy|puppies|kittens?|kitty|pets?|horses?|birds?|fish|rabbits?|bunny|car|cars|truck|bike|phone|laptop|pc|build|tattoo|hair|order|package|account|plant|plants|vet|spay\w*|neuter\w*)\b");
regex!(BIRTH_VERB, r" (?:was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b");
regex!(BIRTH_LEAD, r"\b(?:had|have|with|after|since|before|for|from|than|during) $");
regex!(AWAITED, r"\b(?:to|wanna|until|till|before|once|planning on|plan on) (?:have|having)\s+$");
regex!(DUE, r"(?:'s)? (?:is |was )?due\b");
regex!(HAD_KIDS, r"\b(?:you|u|he|she|they|who|people|parents|someone|her|him|his|their)\b");
regex!(LEADING, r"(?:^|[.!?\n,;]\s*|\band |\bbut )(?:also |now |still |already )?$");
regex!(OTHERS_PARENT, r"\b(?:my|his|her|their|your|our|the|whose|he|she|they|you)\b");
regex!(TEEN_AGE, r"\d|year");
regex!(SIBLING, r"\s*(?:brother|sister|sibling|cousin|friend|aunt|uncle|niece|nephew|grand|memor|and)");
regex!(NO_MORE, r"(?:,| and|;) no\b");

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
        Some("has children")
    } else {
        None
    }
}

fn parenting(m: &Match) -> V {
    let s = m.string;
    if BABY_LEAD.test_in(s, back(m, 14), m.start()) && INFANT.test(s) && SELF.test(s) && !ROMANTIC.test(s) {
        kept(m, "has children")
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
        kept(m, "has children")
    } else {
        None
    }
}

fn child(m: &Match) -> V {
    let s = m.string;
    let word = st(m.group(1).unwrap_or(&[]));
    if !spoken(m) || AWAITED.test_in(s, back(m, 24), m.start()) || DUE.at(s, m.end()).is_some() {
        return None;
    }
    if ["baby", "babies", "bub", "bubba", "lo", "dc", "dcs"].contains(&word.as_str()) && !INFANT.test(s) && (word != "baby" || ROMANTIC.test(s)) {
        return None;
    }
    if word == "teen" && !TEEN_AGE.test(m.text()) {
        return None;
    }
    if ["youngest", "oldest", "eldest", "middle child"].contains(&word.as_str()) && SIBLING.at(s, m.end()).is_some() {
        return None;
    }
    Some("has children")
}

fn raising(m: &Match) -> V {
    let text = m.text();
    if !starts_at(text, 0, "i") && !starts_at(text, 0, "we") && !LEADING.test_in(m.string, back(m, 16), m.start()) {
        return None;
    }
    if HAD_KIDS.test_in(m.string, sentence(m).0, m.start()) {
        None
    } else {
        stated(m, &FUTURE, || kept(m, "has children"))
    }
}

fn parent_label(m: &Match) -> V {
    if OTHERS_PARENT.test_in(m.string, clause(m.string, m.start()), m.start()) {
        None
    } else {
        stated(m, &FUTURE, || kept(m, "has children"))
    }
}

fn has_children(m: &Match) -> V {
    stated(m, &FUTURE, || kept(m, "has children"))
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let QUALIFIER = format!(r"(?:{AGE}|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|own|beautiful|sweet|precious|amazing|wonderful|lovely|darling|sick|")
        + r"autistic|adhd|disabled|adopted|adoptive|biological|bio|step|older|younger|toddler|infant|teen|two|lil|wee|sweet)";
    let parents = ["mom", "mum", "mother", "dad", "father", "parent", "mama"];
    vec![
        r("parental_status", &format!(r"(?:my (?<=\bmy )|our (?<=\bour ))(?:{QUALIFIER}[- ,]+){{0,3}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|cups?|tits|boobs|sister|brother|face|fever|shower)\b)"), child, TAGGED),
        r("parental_status", &(format!(r"\b(?:my|our) (?!(?:future|dream|unborn|imaginary|dog|cat|pup|puppy|fur|furry|kitty|bunny|plant|pet|god|ex|friends?|neighbou?rs?|sisters?|brothers?|cousins?|boyfriends?|girlfriends?|wife|husband|partner|aunt|uncle|boss|inner|little|baby|big|good)\b)[a-z]+ ")
            + &format!(r"(?:{QUALIFIER}[- ,]+){{0,2}}{CHILD}(?:'s)?\b(?! (?:of|in law|in-law|self|selves|hood|years?|sister|brother|face|fever|shower)\b)")),
          |m| if m.group(1).map_or(false, |g| eq(g, "baby") || eq(g, "babies") || eq(g, "child")) { None } else { child(m) }, TAGGED),
        r("parental_status", r"the (?<=\bthe )(?:kids|kiddos|little ones?|toddler|twins|baby|babies|newborn)\b(?! (?:in|at|from|of|who|that|these|those|they|i|we|you)\b)",
          |m| if FIRST.test_in(m.string, back(m, 44), m.start()) && !TEACHING.test(m.string) { kept(m, "has children") } else { None }, TAGGED),
        r("parental_status", concat!(r"\b(?:i|we) (?:also |both |still |even |do |did |already |now )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:twins|triplets|kids|children)\b(?! (?:of|in|at|who|that)\b)",
          r"|\bpregnant with (?:number|#|baby|no\.?) ?\d\b"), |m| if FUTURE.test_in(m.string, back(m, 30), m.start()) { None } else if contains(m.text(), "pregnant") { Some("expecting a child") } else { Some("has children") }, TAGGED),
        r("parental_status", concat!(r"\b(?:i|we)(?:'ve| have)? (?:also |both |still |even |do |did |already |now )?(?:have|had|got|have got|raised|am raising|are raising|delivered) (?:only |just )?(?:\d+|a|an|one|two|three|four|five|six|seven|eight|twins|my) (?:[a-z\d-]+ ){0,2}",
          r"(?:kids?|children|child|sons?|daughters?|boys|girls|toddlers?|babies|baby|teens|teenagers|newborn|stepkids|stepsons?|stepdaughters?|grandkids|grandchildren)\b(?! (?:of|in law|sister|brother|face|fever|shower|bump|cousin|niece|nephew|over|before|when|someday)\b)"),
          has_children, TAGGED),
        r("parental_status", &(format!(r"(?:{ME}|{AS}) (?:a|an) (?:(?!dog|cat|pet|plant|fur|cool|den|house|god|team|group|band|boat|bonus|stage|foster|wine|soccer|hockey|horse|bunny|plant|chicken)\w+ )?(?:mom|mum|mommy|mama|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather|grandparent|nana|granny)\b")
            + r"(?! (?:of|to) (?:a|my|\d+|two|three) (?:dogs?|cats?|pets?|plants?|fur)| figure| friend| to (?:my|a|all) (?:dogs?|cats?|pets?))"), has_children, TAGGED),
        needs(r("parental_status", r"(?<!dog )(?<!cat )(?<!fur )(?<!pet )(?<!plant )\b(?:mom|mum|mama|mommy|mother|dad|father|parent) (?:of|to) (?:\d+|one|two|three|four|five|six|seven|twins|triplets|a (?:\w+ )?(?:boy|girl|son|daughter|toddler|newborn|baby|teen|teenager|preteen|kiddo|\d+))\b(?! (?:dogs?|cats?|pets?|fur))", has_children, TAGGED), &["mom", "mum", "mama", "mother", "dad", "father", "parent"]),
        needs(r("parental_status", r"\b(?:married|single|divorced|working|busy|tired|new|young|proud|first[- ]time|exhausted|stay[- ]at[- ]home|full[- ]time|solo|widowed|separated|older|hot|bored|lonely|bi|pervy|horny|sexy|naughty|boy|girl|twin|homeschool(?:ing)?|toddler|teen|preemie|nicu|autism|special needs|military|working[- ]class)[- ]?(?:dad|mom|mum|father|mother|mama|mommy|parent)\b(?!s| bod| jokes?| energy| vibes| groups?| friends?| life| figure)",
          |m| if PARENT_LEAD.test_in(m.string, back(m, 60), m.start()) { has_children(m) } else { None }, TAGGED), &["dad", "mom", "mum", "father", "mother", "mama", "parent"]),
        r("parental_status", r"^\W*[\[\(]?(?:\d{2}\s*[mf]?|[mf]\s*\d{2})[\]\)]?\W*(?:(?!dog|cat|fur|plant|pet|bonus|step|soccer|hockey|boy|girl)\w+\s+){0,2}(?:mom|mum|mother|mommy|mama|dad|father)\b(?!s| bod| jeans| energy| vibes| jokes?)", |m| kept(m, "has children"), TAGGED),
        r("parental_status", &(format!(r"\b\d{{2}}\s*[mf]?\s*,?\s*(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)|\bthe (?:kids|kiddos|children|twins|baby|little ones?) and (?:i|me)\b|\b(?:me|myself) (?:and|&) the (?:kids|kiddos|children|twins|baby|little ones?)\b|\bfellow (?:(?!dog|cat|pet|plant|fur|boy|girl)[\w-]+ ){{0,2}}(?:parent|mom|mum|dad|mother|father|mama)s?\b|\b(?:my|our) (?:wife|husband|hubby|partner|spouse) (?:and|&) (?:our |my |the )?(?:\d+ |two |three |four )?{CHILD}\b")
            + r"|\b(?<![^\n.!? ])(?<![^\n.!?] )(?:the )?(?:wife|husband|hubby) (?:and|&) (?:the )?(?:\d+ |two |three )?(?:kids?|children|sons?|daughters?|boys|girls)\b|\b(?:i (?:also |already )?have|i've got|i got) an? (?:wife|husband|hubby) (?:and|&) (?:\d+|a|two|three|four|five) (?:kids?|children|sons?|daughters?|boys|girls)\b|\b(?:i (?:do |also |already )?have|i've got|we (?:do |also |already )?have|we've got) (?:a|an|one|two|three|\d) (?:1[0-7]|\d|one|two|three|four|five|six|seven|eight|nine|ten)(?!\d)(?: 1/2| and a half)?(?:[- ]?(?:year|yr|month|week|wk)s?[- ]?olds?|yo)\b(?! (?:dog|cat|pup|puppy|kitten|horse|car|house|laptop|computer|phone))"),
          |m| kept(m, "has children"), TAGGED),
        r("parental_status", &format!(r"\b(?:my|our) (\d+|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?(yo|y/o|year[- ]old|yr[- ]old|month[- ]old|week[- ]old)s?(?= (?!(?:{NOT_CHILD})\b)[a-z]+\b|[.,!?;)])"),
          |m| if m.group(2).map_or(false, |u| starts_at(u, 0, "y")) && m.group(1).map_or(false, |n| isdigit(n) && py_int(n).map_or(false, |v| v > 17)) { None } else { kept(m, "has children") }, TAGGED),
        r("parental_status", &format!(r"my (?<=\bmy )(?:now[- ]|almost[- ]|nearly[- ]|just[- ]turned[- ])?{YEARS}[- ]?(?:(years?|yrs?|months?|weeks?|wks?)[- ]olds?|(yo|y/o|mo|mos|m/o))\b(?! (?:{NOT_CHILD})\b)"), aged, TAGGED),
        r("parental_status", r"\bno (?:kids|children)\b(?! (?:allowed|please|zone|menu|under|in|at|on|were|are|will))|\b(?:keine kinder|sin hijos|sem filhos|sans enfants?|geen kinderen|senza figli|ingen børn|inga barn)\b",
          |m| if LISTED.test_in(m.string, 0, m.start()) || NO_MORE.at(m.string, m.end()).is_some() || SELF.test_in(m.string, back(m, 40), m.start()) { Some("no children") } else { None }, Some(&*CONDITIONAL)),
        r("parental_status", concat!(r"\b(?:i'm|im|i am) (?:currently |now |almost |nearly |only |just |about |officially )?\d{1,2}(?:\+\d)? ?(?:w|wks?|weeks?)(?: along| pregnant|(?: and)? \d ?d(?:ays?)?)?\b(?! (?:sober|clean|out|post|into|off|postpartum|in|of|until|from|ago|later|since|after|before|without|free|smoke|nicotine|vape))",
          r"|\b\d{1,2} ?(?:weeks?|wks?) along\b|\bwe(?:'re| are) (?:having|expecting) (?:a baby|twins|a boy|a girl|our (?:first|second|third|rainbow)|another|baby)\b|\bi(?:'m| am) having (?:a baby|twins|my (?:first|second|third) (?:baby|child))\b|\b(?:my|our) (?:due date|anatomy scan|nipt|nt scan|gender reveal|baby shower|glucose test)\b"),
          |m| stated(m, &FUTURE, || Some("expecting a child")), TAGGED),
        r("parental_status", concat!(r"\b(?:meine?[nmrs]?|mein|unser\w*|mi|mis|mon|ma|mes|notre|nuestr[oa]s?|noss[oa]s?|onze|nostr[oaie]|meu|minha|meus|minhas|mijn|moja|moje|mój|mio|mia|mie|miei)\s+(?:(?!inner)\w+\s+)?(?:tochter|sohn|kinder|kindern|kind(?! of)|kids|söhne|söhnen|töchter|töchtern|hijo|hija|hijos|hijas|fils|fille|filles|enfants|enfant|filho|filha|filhos|filhas|zoon|zonen|dochter|dochters|kinderen|córka|syn|dzieci|figlio|figlia|figli|figlie|bimba|bimbo|bambin[oaie])\b|\bnos (?:enfants|filles|fils)\b",
          r"|\b(?:ich habe|ich hab|wir haben|tengo|tenemos|j'ai|nous avons|eu tenho|tenho|temos|ik heb|wij hebben|we hebben|ho|abbiamo|jeg har|vi har|jag har) (?:(?:eine?n?|zwei|drei|vier|un|una|dos|tres|une|deux|trois|um|uma|dois|três|een|twee|drie|due|tre|to|fire|två|fyra|\d) (?:\w+ )?|des |dei )?",
          r"(?:tochter|töchter|sohn|söhne|kinder|kind|hijos?|hijas?|fils|filles?|enfants?|filhos?|filhas?|kinderen|zoon|zonen|dochters?|figli|figlio|figlia|børn|barn|unger|døtre|sønner|söner|döttrar|søn|sønn|datter|dotter)\b"),
          |m| if NEGATED.test_in(m.string, back(m, 5), m.start()) { None } else { stated(m, &FUTURE, || Some("has children")) }, TAGGED),
        r("parental_status", r"\b(?:min|mitt|mina|mit|mine|vores|våra|vår|vårt) (?:(?:lille|lilla|store|stora|yngste|ældste|eldste|äldsta|yngsta|to|tre|två) )?(?:son|søn|sønn|dotter|datter|døtre|döttrar|söner|sønner|barn|børn|unger|mindste|ældste|eldste|yngste|äldsta|yngsta)\b|\b(?:a |az )?(?:fiam|lányom|gyerekem|gyerekeim|kisfiam|kislányom)\b|\b(?:můj|moje|mého|mojí) (?:syn|dcera|děti|dítě|dceru|syna)\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) meu\b|\b(?:fiul|fiica|copiii|copilul|băiatul|fetița) (?:meu|mea|mei)\b|\b(?:mi|mis) (?:niño|niña|niños|niñas|bebé|nene|nena)\b",
          |m| stated(m, &FUTURE, || Some("has children")), TAGGED),
        r("parental_status", r"(?<=[,;:]) ?child[- ]?free\b(?=\s*(?:[,;.&/)\n]|$|and\b))|^\W*child[- ]?free\b(?=\s*(?:[,;.&/)\n]|$))", constant("no children"), TAGGED),
        r("parental_status", r"\b(?:i|we) (?:have|got) no (?:kids|children|child)\b|\bno (?:kids|children) (?:yet|of (?:my|our) own|here|for me)\b|\b(?:i|we) (?:don't|do not|dont) have (?:any )?(?:kids|children) (?:yet|of (?:my|our) own)\b|\bi(?:'ve| have) no (?:kids|children)\b",
          constant("no children"), Some(&*CONDITIONAL)),
        r("parental_status", r"\b(?:estoy|estou|je suis|ich bin|sono|ik ben|jestem|jeg er|jag är)(?: (?!(?:pas|plus|jamais|nicht|nie|kein\w*|no|non|não|nao|nunca|niet|geen|ikke|inte)\b)[\w.]+){0,3}? (?:embarazada|grávida|gravida|enceinte|schwanger|incinta|zwanger|gravid|w ciąży)\b|\bbin (?:\w+ )?in der \d{1,2}\.? ?ssw\b|\bя беременна\b|\bhamileyim\b|\bbuntis ako\b", |m| stated(m, &FUTURE, || Some("expecting a child")), TAGGED),
        r("parental_status", concat!(r"\b(?:i'm|im|i am) (?:\d+ ?(?:weeks?|months?) )?post[- ]?partum\b|\bmy post[- ]?partum\b|\b\d+ ?(?:weeks?|months?|days?) post[- ]?partum\b|\b(?:since|after|when|before) (?:giving birth|i gave birth|(?:having|i had) my (?:\w+ )?(?:baby|son|daughter|kids?|child|children|first|second|third|twins|lo|youngest|oldest|little))\b|\bi gave birth\b|\bmy last pregnancy\b",
          r"|\bmy (?:c-section|c section|labor and delivery|birth story|epidural|maternity leave|paternity leave)\b|\bi(?:'m| am)? (?:still |exclusively |currently )?(?:breastfeeding|breastfed|ebf)\b|\bbreastfeeding my\b|\bnursing my (?:son|daughter|baby)\b"), |m| stated(m, &FUTURE, || Some("has children")), TAGGED),
        r("parental_status", concat!(r"\b(?:i'm|im|i am) (?:currently |now |finally |also )?(?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+(?:\+\d)? ?(?:weeks?|wks?|months?) pregnant\b|\b(?:i'm|im|i am|we're|we are) expecting(?= (?:a baby|our|my|twins|baby|a little|a boy|a girl|in|again)\b|[.!,]|$)",
          r"|\bmy (?:first |second |third |current |\d+(?:st|nd|rd|th) )?pregnancy\b|\bthis pregnancy\b|\bmy (?:first|second|third) trimester\b|\b(?:my|our) (?:unborn|baby bump)\b|\bpregnant with (?:my|our) (?:first|second|third|\d|rainbow|twins|baby)\b|\bbaby (?:#|number )?\d on the way\b|\b(?:our|my) baby on the way\b|\b(?:i|we) (?:have|'ve got|got) (?:a|another) baby on the way\b",
          r"|\b(?:i'm|im|i am) due (?:in|next|this|any day|soon)\b|\bmy scheduled induction\b|\bcurrently pregnant\b|\bpregnant currently\b|\b(?:i'm|im|i am) currently \d+ ?(?:weeks|wks)\b"),
          |m| if PAST.test_in(m.string, back(m, 20), m.start()) { None } else { stated(m, &FUTURE, || Some("expecting a child")) }, TAGGED),
        needs(r("parental_status", concat!(r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\b(?:i'm|im|i am|we're|we are|as an?) (?:\w+,? )?child[- ]?free\b|\bno kids of my own\b|\bi(?:'ve| have) never had (?:kids|children)\b|\bwe (?:don't|do not|dont) have (?:any )?(?:kids|children)\b",
          r"|\b(?:i'm|im|i am) (?:not a (?:mom|mum|mother|dad|father|parent)|childless)\b|\bchild-?free (?:here|by choice)\b|\bno kids here\b|\bwe(?:'re| are) (?:a )?dinks?\b",
          r"|\b(?:i|we) (?:love |enjoy )?being (?:kid|child)[- ]?free\b|\b(?:i|we) (?:can't|cannot|can not|couldn't|could not|wasn't able to|weren't able to|was never able to|am not able to) (?:have (?:kids|children|a baby|babies|a child)|conceive)\b",
          r"|\bneither of us (?:is|are|can|was|were) (?:able to )?(?:have|has) (?:kids|children)\b|\bi(?:'m| am) infertile\b|\b(?:ich habe|ich hab|wir haben) (?:noch |gar |auch )?keine? (?:kind|kinder)\b|\b(?:je n'ai|nous n'avons) pas d'enfants?\b|\bno (?:tengo|tenemos) hijos?\b|\bn[ãa]o (?:tenho|temos) filhos?\b|\bnon (?:ho|abbiamo) figli\b|\b(?:ik|wij|we) (?:heb|hebben) geen kinderen\b|\b(?:jeg|vi) har ingen børn\b|\b(?:jag|vi) har inga barn\b|\b(?:nemám|nemáme) (?:\w+ )?děti\b|\bděti nemám\b|\bje ne suis pas (?:père|mère)\b",
          r"|\bi (?:also |still |just |really |even |currently |personally |myself |actually )(?:don't|do not|dont) have (?:any )?(?:kids|children|a kid|a child)\b|\bi (?:\w+ )?(?:don't|do not|dont|never) (?:ever )?want(?:ed)? (?:any )?(?:kids|children)\b|\bi (?:also )?never (?:married or )?had (?:any )?(?:kids|children)\b|\b(?:i'm|im|i am|i ain't|i aint) (?:not |never )having (?:any )?(?:kids|children)\b|\bno dependents\b"),
          constant("no children"), Some(&*CONDITIONAL)), &["kid", "child", "mom", "mum", "mother", "dad", "father", "parent", "dink", "bab", "conceive", "infertile", "kind", "enfant", "hijo", "filho", "figli", "børn", "barn", "děti", "père", "mère", "dependents"]),
        r("parental_status", concat!(r"\b(?:after|before|since) (?:i had|having) (?:my|our) (?:first|second|third|son|daughter|kids?|children|baby|babies)\b",
          r"|\bbefore i (?:got|became|was) pregnant (?:the first time|with (?:my|our))\b|\bafter my (?:first|second|third|last|previous|\d+(?:st|nd|rd|th)) pregnancy\b|\bwhen (?:i|we) had (?:my|our) (?:first|second|son|daughter|kids?|baby)\b"), has_children, TAGGED),
        r("parental_status", concat!(r"\b(?:after|since|before) (?:just )?having (?:a |my |our |\d |two |three |four |the )?(?:\w+ )?(?:baby|babies|kids?|children|child|twins|son|daughter)\b|\bafter (?:having )?baby\b|\bafter i had my (?:\w+ )?(?:baby|son|daughter|kids?|first|second|third|twins)\b",
          r"|\b\d+ ?(?:years?|yrs?) post[- ]?partum\b|\b(?:i'm|im|i am) \d+ ?(?:weeks?|months?|wks?|mos?) pp\b|\b(?:my|both of my|all of my|each of my|all my|both my) (?:\w+ )?pregnancies\b|\b(?:i|since i|after i|when i) (?:just |recently |finally )?became a (?:\w+ )?(?:mom|mum|mother|dad|father|parent)\b",
          r"|\b(?:we|i) (?:just |recently )?had (?:a|our|my) (?:\w+ )?(?:baby|child|son|daughter)\b(?! (?:shower|of|in))|\b(?:married|divorced|single|separated|widowed) (?:with|w/) (?:(?:\d+|one|two|three|four|five|a|an) )?(?:(?!no\b)\w+ )?(?:kids?|kiddos?|children|child|sons?|daughters?|boys|girls|toddlers?|teens|babies|baby)\b",
          r"|\b(?<![^\n,;:(|/ ])(?<![^\n,;:(|/] )(?:\d|two|three|four|five) (?:kids|children|teens|kinder|kinderen|hijos|enfants|filhos|figli|børn|dzieci|děti)\b|\bkids\s*:\s*[1-9]",
          r"|\b(?:i was|i got|i had to be) induced\b|\bmy waters? broke\b|\bi was in labou?r\b|\b(?:both|all) (?:of )?my (?:births|deliveries|labou?rs)\b|\bi(?: had|'ve had| have had) (?:two |three |\d |a |an )?(?:c-?sections?|vaginal births?|home births?|natural births?|unmedicated births?)\b"), has_children, TAGGED),
        r("parental_status", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:two|three|four|five|\d|twin|little|baby|eldest|oldest|youngest|middle|teenage|fourth|third|second|first) (?:(?:little|teenage|baby|twin|young|younger|older|grown|adult) )?(boys|girls|boy|girl)\b", child, TAGGED),
        r("parental_status", r"(?:baby|toddler|kiddo|lo|bub) (?:is|was|has|had|decided|needs|got|will|sleeps|slept|woke|wakes|just|still|started|loves|hates|refuses|won't|doesn't|did|turned|takes|eats|arrived|came)\b", parenting, TAGGED),
        r("parental_status", &format!(r"(?:my (?<=\bmy )|our (?<=\bour )){ORDINAL}(?: one| two| three)?(?=[.,!?;)]|$| (?:and|but|at|in|i|we|he|she|they|it|was|is|had|has|took|came|arrived|weighed|needed|cried|slept|sleeps|loved|hated|refused|turned|started|didn't|did|wasn't|isn't|got)\b)"), birth_order, TAGGED),
        needs(r("parental_status", &(format!(r"(?:(?:i(?<=\bi)|we(?<=\bwe))(?:'ve| have)? (?:also |both |still |even |do |did |already |now |currently |usually |only )?(?:have|had|got|raised|birthed)")
            + &format!(r"|(?:have|had|got|raised)(?<![\w'-]have)(?<![\w'-]had)(?<![\w'-]got)(?<![\w'-]raised)) {KID_COUNT}{KID_WORDS}{KID_NOUN}{KID_AFTER}")), raising, TAGGED),
          &["kid", "child", "son", "daughter", "toddler", "teen", "newborn", "infant", "twin", "triplet", "step", "grand", "old"]),
        needs(r("parental_status", &format!(r"{ME} (?:\w+,? ){{1,3}}and an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band)\w+ )?(?:mom|mum|mother|dad|father|parent)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur))|\b\d{{2}}\s*(?:yo|y/o|years? old|year-old|yr old|yrs old)\s*,?\s*(?:(?!dog|cat|pet|plant|fur|boy|girl)\w+ )?(?:mom|mum|dad|mama|mother|father)\b(?!s| bod| jokes?| energy| vibes)"),
          parent_label, TAGGED), &parents),
        needs(r("parental_status", r"\b(?:as|being) an? (?:(?!dog|cat|pet|plant|fur|god|team|house|den|foster|soccer|hockey|boat|band|bonus|future|good|bad)\w+ )?(?:mom|mum|mother|dad|father|parent|mama|mommy)\b(?! (?:of|to) (?:a |my |\d+ |two |three )?(?:dogs?|cats?|pets?|plants?|fur)| figure| friend)",
          |m| { let (a, b) = sentence(m); if SELF.test_in(m.string, a, b) { parent_label(m) } else { None } }, TAGGED), &parents),
    ]
}
