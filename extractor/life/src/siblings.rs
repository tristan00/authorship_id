use crate::relationship::SPEAKER;
use crate::shared::*;
use claimcore::*;

const NUMBER: &str = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)";
const SIBLING: &str = r"(?:child|kid|sibling|daughter|son|sister|brother|girl|boy)";

regex!(TWIN_LEAD, r"\b(?:found|find|meet|met|lost|long lost|evil|internet|reddit|style|fashion|celebrity|spirit|soul|book|gym|cat|dog|separated at birth)\s+(?:\w+\s+)?$");
regex!(FAMILY, r"\b(?:siblings?|brothers?|sisters?|family|parents|mom|dad|mum|mother|father|grandchildren|cousins)\b");
regex!(ANSWERED, r"\b(?:you|you're|youre|u|ur|he|she|they|his|her|their|it)\b");

fn order(m: &Match) -> V {
    let text = m.text();
    if contains(text, "only") || contains(text, "no siblings") {
        Some("only child")
    } else if contains(text, "middle") {
        Some("middle")
    } else if contains(text, "youngest") || contains(text, "baby") || contains(text, "last") {
        Some("youngest")
    } else if contains(text, "twin") || contains(text, "triplet") {
        Some("twin")
    } else {
        Some("oldest")
    }
}

fn mine(m: &Match) -> V {
    let (a, b) = sentence(m);
    if THIRD.test_in(m.string, a, m.start()) || !starts_at(m.text(), 0, "i") && (!SPEAKER.test_in(m.string, a, b) || THIRD.test_in(m.string, a, b)) {
        None
    } else {
        stated(m, &FUTURE, || kept(m, order(m)?))
    }
}

fn twin(m: &Match) -> V {
    if TWIN_LEAD.test_in(m.string, back(m, 24), m.start()) || ANSWERED.test_in(m.string, clause(m.string, m.start()), m.start()) {
        None
    } else {
        stated(m, &FUTURE, || kept(m, "twin"))
    }
}

#[allow(non_snake_case)]
pub fn build() -> Vec<Rule> {
    let OLD = format!(r"(?:(?:oldest|eldest) (?:{SIBLING}|of {NUMBER}\b|in (?:my|our|the) family)|first[- ]?born)");
    let YOUNG = format!(r"(?:youngest (?:{SIBLING}|of {NUMBER}\b|in (?:my|our|the) family)|baby of (?:the|my|our) family|last[- ]born)");
    let FRAME = r"(?:\bi(?:'m| am|m|'ve always been| was| grew up as| grew up)|\bim|\bas|\bbeing|\bgrowing up as)";
    vec![
        needs(r("birth_order", &format!(r"^r/\w+:\s*(?:[^\n|]*\|\s*)?(?:only child|(?:oldest|eldest|youngest|middle) (?:child|of {NUMBER}))\s*(?:$|[|\n])|(?:^|[\n.!?]\s*)(?:\w+ )?only child here\b|\b\d{{2}}\s*[mf]\s+(?:only|middle|oldest|youngest) child\b"), |m| kept(m, order(m)?), TAGGED), &["only", "oldest", "eldest", "youngest", "middle"]),
        needs(r("birth_order", &format!(r"{FRAME} (?:(?:actually|also|technically|literally|basically|just|still) )?(?:the |an? |also the |also an? )?(?:only (?:child|kid)\b(?! (?:policy|syndrome|in|at|on|who|that|from|to|left|there|here|among|with|around|for)\b)|{OLD}|{YOUNG}|middle (?:{SIBLING}|of {NUMBER}\b))|\bi have no (?:siblings|brothers or sisters)\b"), mine, self_hedge()),
          &["only", "oldest", "eldest", "first", "youngest", "baby of", "last", "middle", "no siblings", "brothers or sisters"]),
        needs(r("birth_order", &format!(r"{FRAME} the (?:oldest|eldest|youngest)(?: one)?\b(?=\s*(?:[,.!;:)\n]|$|(?:and|but|so|(?:out )?of (?:us|them|my|the|all))\b))"), |m| { let (a, b) = sentence(m); if FAMILY.test_in(m.string, a, b) { mine(m) } else { None } }, self_hedge()), &["oldest", "eldest", "youngest"]),
        needs(r("birth_order", &format!(r"(?:^|[\n,;(|]\s*)(?:the )?(?:oldest|eldest|youngest|middle) (?:of {NUMBER} (?:siblings|kids|children|brothers|sisters)|(?:child|sibling)(?: of {NUMBER})?)\b"), mine, TAGGED), &["oldest", "eldest", "youngest", "middle"]),
        needs(r("birth_order", r"\b(?:i'm|im|i am|i was born|as|being) (?:an? |the )?(?:identical |fraternal |older |younger |oldest |youngest )?(?:twin|triplet)\b(?![\w-]| (?:flame|flames|bed|beds|size|peaks|cities|turbo|engine|of|to|soul|set|fin|citizen|mom|moms|mum|mums|mommy|mama|mother|dad|daddy|father|parent|brothers|sisters|boys|girls|babies)\b)", |m| if starts_at(m.text(), 0, "as") || starts_at(m.text(), 0, "being") { mine(m) } else { twin(m) }, self_hedge()), &["twin", "triplet"]),
        needs(r("birth_order", r"\b(?:my (?:(?:identical|fraternal) twin|(?:(?:older|younger|little|big) )?twin (?:brother|sister|sibling|bro|sis)(?:'s)?|twin (?:and|&) i)|me and my (?:identical |fraternal )?twin)\b(?![\w'-]| \w*\d| (?:sisters|brothers|siblings|boys|girls|sons|daughters|babies|toddlers|kids|beds?|flames?|size|xl|engine|peaks|cities|turbo|mattress|set|pack|stroller|pregnancy|bedroom|room|tubs?|blades?|sheets?|frames?)\b)", twin, TAGGED), &["twin"]),
    ]
}
