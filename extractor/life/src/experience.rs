use crate::relationship::{HEADER, LOOSE_FOLLOW, SEXUAL, SPEAKER};
use crate::shared::*;
use claimcore::*;

const ADVERBS: &str = r"(?:(?:still|also|technically|completely|totally|literally|basically|just|kinda|kind of|sort of|pretty much|currently|now|very much|100%|fully|actually|honestly|unfortunately|sadly|proudly|happily|a proud|an? \d{2} (?:years? old|yo|y/o)|\d{2} ?(?:[mf]|years? old|yo|y/o)? ?(?:and|&|,)) )*";
const NOT_VIRGIN: &str = r"(?! (?:ass|hole|pussy|cock|mouth|throat|feet|skin|hair|olive|islands?|atlantic|media|mobile|games?|river|australia|america|airlines?|money|galactic|radio|trains|wool|forest|soil|territory|birth|mary|queen|suicides|records|megastore|voyages|plus|orbit|hyperloop|cola|active|to)\b)";
const KINKY_FOLLOW: &str = r"(?:bull|dom|domme|top|bottom|lover|couple|guy|man|woman|girl|lady|sub|switch|daddy|male|female|vers|hotwife|cuck|unicorn|third|mistress|master|swinger|gent|gentleman|stud|cpl|twink|femboy|virgin|bwc|bbc|hung)";

regex!(EXPLICIT, r"\b(?:[mft]4[mfat]\w*|sex\w*|kinks?|kinky|bdsm|hotwi\w+|cuck\w*|swing(?:er|ers|ing)|threesomes?|3some|nsfw|horny|fwb|hook ?ups?|submissive|domme|cock|dick|pussy|bwc|bbc|cum|cumming|nudes?|anal|fuck\w*|virgin\w*|erotic|bondage|unicorn|play partner)\b");
regex!(WANTED, r"\b(?:prefer\w*|pref|looking for|seeking|want|wants|bonus|plus if|ok if|okay if|must be|sana|if you(?:'re| are))\s+(?:\w+\s+)?$");
regex!(AGED, r"\b\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b");
regex!(FILIPINO, r"\b(?:i|i'm|im|me|my|ako|ko|aq|akin|sakin)\b");
regex!(NOT_SEXUAL, r"\b(?:trader|trading|driver|driving|player|owner|developer|programmer|engineer|nurse|teacher|investor|hiker|climber|runner|cook|chef|flying|pilot|sailor|traveller|traveler|gamer|coder|swimmer|diver|rider|shooter|hunter|fisherman|camper)\b");

fn kind(m: &Match) -> V {
    let text = m.text();
    if contains(text, "kissless") {
        Some("kissless virgin")
    } else if contains(text, "inexperienced") {
        Some("inexperienced")
    } else if contains(text, "experienced") {
        Some("experienced")
    } else if contains(text, "celiba") {
        Some("celibate")
    } else if contains(text, "sexually active") {
        Some("sexually active")
    } else if contains(text, "nbsb") {
        Some("nbsb (no boyfriend since birth)")
    } else if contains(text, "new") || contains(text, "first") || contains(text, "noob") {
        Some("new to this / first timer")
    } else {
        Some("virgin")
    }
}

fn own(m: &Match) -> V {
    if THIRD.test_in(m.string, sentence_start(m), m.start()) {
        None
    } else {
        stated(m, &STATED, || kept(m, kind(m)?))
    }
}

fn sexual(m: &Match) -> V {
    let (a, b) = sentence(m);
    if SEXUAL.test(m.string) && !NOT_SEXUAL.test_in(m.string, a, b) {
        own(m)
    } else {
        None
    }
}

fn explicit(m: &Match) -> V {
    if EXPLICIT.test(m.string) {
        own(m)
    } else {
        None
    }
}

fn filipino(m: &Match) -> V {
    let (a, b) = sentence(m);
    if FILIPINO.test_in(m.string, a, b) && !WANTED.test_in(m.string, back(m, 30), m.start()) {
        own(m)
    } else {
        None
    }
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let NOT = r"(?!(?:not|no|never|nor|longer|a|an)\b)";
    vec![
        needs(r("sexual_experience", &format!(r"{ME} {ADVERBS}(?:an? )?(?:{NOT}[\w-]+ )?(?:kissless )?virgin\b{NOT_VIRGIN}"), own, self_hedge()), &["virgin"]),
        needs(r("sexual_experience", &format!(r"\b(?:and|but|&) (?:i'm |im |i am )?still an? (?:kissless )?virgin\b{NOT_VIRGIN}|\bas an? (?:{NOT}[\w-]+ )?(?:kissless )?virgin,? (?:i|i'm|im|i've|my|myself)\b|(?:^|[\n.!?]\s*)(?:kissless )?virgin here\b"),
          |m| if SPEAKER.test_in(m.string, sentence(m).0, m.end()) || AGED.test_in(m.string, sentence(m).0, m.start()) || contains(m.text(), "virgin here") { own(m) } else { None }, self_hedge()), &["virgin"]),
        needs(r("sexual_experience", &format!(r"{HEADER}(?:[\w-]+ ){{0,2}}?(?:kissless )?virgin{LOOSE_FOLLOW}{NOT_VIRGIN}"), |m| if spoken(m) { kind(m) } else { None }, TAGGED), &["virgin"]),
        needs(r("sexual_experience", r"\b(?:я|мне \d+ (?:лет|год|года)),? (?:\w+ )?девственни(?:к|ца)\b", |m| stated(m, &STATED, || Some("virgin")), TAGGED), &["девственни"]),
        needs(r("sexual_experience", r"\b(?:sou|soy|je suis|sono|ich bin|jestem)(?: (?:ainda|todavía|todavia|aún|aun|encore|toujours|ancora|noch|wciąż|nadal))? (?:una? )?(?:virgem|virgen|vierge|puceau|pucelle|vergine|jungfrau|dziewicą|prawiczkiem)\b", |m| stated(m, &STATED, || Some("virgin")), TAGGED), &["virg", "vierge", "puce", "jungfrau", "dziewic", "prawicz"]),
        needs(r("sexual_experience", &format!(r"{ME} (?:(?:pretty|very|quite|so|super|completely|totally|fairly|somewhat|a bit|kinda|relatively|still|sexually|also|rather|extremely|really) ){{0,2}}inexperienced\b(?! (?:in|with|at|when it comes to) (?!bed\b|sex\b|the bedroom\b|this\b|kink|bdsm|men\b|women\b|guys\b|girls\b))"), sexual, self_hedge()), &["inexperienced"]),
        needs(r("sexual_experience", &format!(r"{HEADER}(?:[\w-]+ ){{0,2}}?(?:very |sexually )?(?:inexperienced|experienced) {KINKY_FOLLOW}\b|(?:^|[\n.!?]\s*)(?:(?:very|well|sexually) )?(?:inexperienced|experienced) {KINKY_FOLLOW} (?:here|looking|seeking|for|from|in)\b|(?:^|[\n.!?]\s*)(?:(?:very|well|sexually) )?experienced with (?:couples|women|men|girls|guys|both)\b"), |m| if spoken(m) { sexual(m) } else { None }, TAGGED), &["experienced"]),
        needs(r("sexual_experience", &format!(r"{ME} (?:(?:very|well|quite|sexually|also|pretty|really|super|highly|fairly|an|a) ){{0,2}}experienced(?: {KINKY_FOLLOW}\b|(?=\s*(?:[,.!;:)\n]|$|(?:and|but|so|too|here|with (?:women|men|couples|girls|guys|both)|in (?:bed|the lifestyle|kink|bdsm))\b)))"), sexual, self_hedge()), &["experienced"]),
        needs(r("sexual_experience", concat!(r"\b(?:i'm|im|i am|we're|we are) (?:(?:very|pretty|totally|completely|still|fairly|relatively|also|quite|brand) ){0,2}new to (?:this|all this|all of this|kink|bdsm|the lifestyle|swinging|cuckolding|hotwifing|anal|bottoming|topping|sex|gay sex|the scene)(?=\s*(?:[,.!;:)\n]|$|(?:and|but|so|stuff|kind|world|thing|scene|lifestyle|lol|haha|please|too|myself)\b))",
          r"|\b(?:i'm|im|i am|we're|we are) (?:an? |a total |a complete )?(?:newbie|noob|first[- ]timers?)(?=\s*(?:[,.!;:)\n]|$|(?:and|but|so|here|looking)\b))|(?:^|[\n.!?]\s*)(?:newbie|first[- ]timer) here\b"), explicit, self_hedge()), &["new to", "newbie", "noob", "first timer", "first-timer"]),
        needs(r("sexual_experience", &format!(r"{ME} (?:(?:currently|also|still|now|happily|voluntarily|basically|pretty much|completely|intentionally|very|fully|choosing to be) ){{0,2}}celibate\b|\bmy celibacy\b|\b(?:i'm|im|i am|i've been|i have been) (?:currently |now )?(?:practicing|practising|choosing) celibacy\b"), |m| if contains(m.text(), "celibacy") && !SPEAKER.test(m.string) { None } else { own(m) }, self_hedge()), &["celiba"]),
        needs(r("sexual_experience", r"\bnbsb\b(?!\s*(?:na|daw|siya|sila|ba|is|are|ok|okay|preferred|welcome|plus|a plus|jackpot|bonus|pls|please|only|or not)\b)", filipino, TAGGED), &["nbsb"]),
        needs(r("sexual_experience", &format!(r"{ME} (?:(?:very|quite|also|still|currently|now) )?sexually active\b"), own, self_hedge()), &["sexually active"]),
    ]
}
