use crate::*;

static HOMEMAKER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:housewife|househusband|house husband|home ?maker|home ?keeper|domestic engineer|tradwife|stay[- ]at[- ]home (?:wife|husband))\b"));

pub(crate) const BUSINESS_OWNER: &str = "business owner";

pub(crate) fn homemaking(m: &Match) -> Option<String> {
    Some(if HOMEMAKER.test(m.text()) { "homemaker / housewife" } else { "stay-at-home parent" }.to_string())
}

#[track_caller]
fn stated(attribute: &'static str, pattern: &str, value: &'static str) -> Rule {
    rule(attribute, pattern, scoped(fixed(value)), self_hedge())
}

pub fn rules() -> Vec<Rule> {
    timed("work.standing", || {
        let mut rules = Vec::new();
        let hours = |kind: &str| {
            format!(concat!(r"\b(?:i|i'm|im|i am)(?: (?:currently|now|also|still|already|only))* (?:work|working) (?:a )?{kind}[- ]?time\b|",
                r"(?:^", claimcore::flair!(), r"|[,;.!\n(]\s*|\band )(?:currently |now |also )?(?:work|working) {kind}[- ]?time\b|",
                r"\bi (?:currently |now |also )?work (?:at|for|in) (?:a |an |the )?(?:[\w'-]+ ){{1,3}}{kind}[- ]?time\b"), kind = kind)
        };
        rules.push(stated("employment_status", &hours("full"), "employed full-time"));
        rules.push(stated("employment_status", &hours("part"), "part-time"));
        rules.push(stated("employment_status", concat!(r"\bi (?:was |got |have been |'ve been |just got |recently got )(?:just |recently )?(?:laid off|let go|made redundant)\b(?! (?:in|back in|from (?:my|a) (?:previous|old|last|first))\b)|",
            r"\bi (?:just |recently )got fired\b|\bi (?:just |recently )?(?:quit|lost) my (?:job|position)(?: (?:last|this) (?:week|month))?\s*(?:$|[.,!;])"), "unemployed"));
        rules.push(stated("employment_status", r"\b(?:i'm|im|i am) (?:currently |now |also |still )?(?:home |out )?on disability\b|\bi (?:can't|cannot|can not) work (?:due to|because of) (?:my )?(?:disabilit|health|illness|chronic)", "disabled / unable to work"));
        rules.push(stated("employment_status", concat!(r"\b(?:i'm|im|i am) (?:an? )?(?:full[- ]?time |part[- ]?time )?freelance\b|(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? )?freelance [\w-]+(?: [\w-]+)? here\b"), "self-employed / freelance"));
        let employed = [
            r"\b(?:i'm|im|i am) (?:currently |now |still |also |gainfully |happily |thankfully |luckily |finally )*employed\b(?! (?:full[- ]?time|part[- ]?time|by (?:my|the) (?:mom|dad|parents|family))\b)(?=\s*(?:$|[.,!;:)(\n-]|\b(?:and|but|so|now|at|as|by|in|with|for|again|too|lol|which|since|though)\b))",
            r"\b(?:i'm|im|i am|as) an? (?:\w+ )?working professional\b|\Ar/\w+: (?:an? )?working professional\b",
            concat!(r"(?<!when )(?<!once )(?<!until )(?<!before )\bi (?:currently |now |also |still |already |do )?have an? (?:steady |stable |good |decent |real |regular |normal |day |paying |well[- ]paying |great )?job\b",
                r"(?! (?:interview|offer|application|to do|for you|opening|posting|lined up|fair|description|title|hunting|search)\b)(?=\s*(?:$|[.,!;:)(\n-]|\b(?:and|but|so|now|at|as|in|with|that|which|lol|too|though)\b))"),
        ];
        for pattern in employed {
            rules.push(stated("employment_status", pattern, "employed (hours unstated)"));
        }
        rules.push(stated("employment_status", r"\b(?:i'm|im|i am) (?:currently |now |also |gainfully )?employed full[- ]?time\b", "employed full-time"));
        rules.push(stated("employment_status", r"\b(?:i'm|im|i am) (?:currently |now |also |only )?employed part[- ]?time\b", "part-time"));
        rules.push(stated("employment_status", concat!(r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |still |also |just )?(?:on|out on|home on) (?:my |a |an )?(?:(?:paid|unpaid|extended|long[- ]term|short[- ]term|indefinite) )?",
            r"(?:maternity|paternity|parental|medical|sick|stress|disability|mat|bereavement|family) leave\b"), "on leave"));
        rules.push(stated("employment_status", r"\b(?:i'm|im|i am) (?:currently |now |still |also )?(?:on|taking|in|doing|having) (?:a|my) (?:\w+ )?gap year\b(?!\s*(?:next|in (?:20|the fall|september)))|\bgap year student here\b", "gap year"));
        rules.push(stated("employment_status", concat!(r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still )?(?:an? |the )?(?:full[- ]time|unpaid|primary|family|main|sole|24/7) (?:carer|caregiver)\b|",
            r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still )?(?:his|her|their|my (?:\w+'s)) (?:full[- ]time |unpaid |primary |main |sole |only )?(?:carer|caregiver)\b|",
            r"\b(?:i'm|im|i am) (?:currently |now |also |still )?(?:an? |the )?(?:carer|caregiver) (?:for|to) (?:my|our) (?:\w+ )?(?:mom|mum|mother|dad|father|parents?|husband|wife|partner|son|daughter|child|kids|children|grandma|grandmother|grandpa|grandfather|brother|sister|spouse|nan|nana)\b"), "carer / caregiver"));
        rules.push(stated("employment_status", concat!(r"\b(?:i'm|im|i am) (?:currently |now |still |also |just )?(?:an? )?(?:(?:first|second|third|fourth|1st|2nd|3rd|4th)[- ]year |union |mature[- ]age |registered )?",
            r"(?:(?:electrical|electrician|plumbing|plumber|carpentry|carpenter|hvac|welding|welder|mechanic|machinist|lineman|pipefitter|ironworker|sparky|joiner|tattoo|chef|baker|butcher|hairdressing|hairdresser|barber|diesel|auto|elevator|boilermaker|bricklayer|roofer|sheet metal|millwright|fitter|industrial) )?",
            r"apprentice(?: (?:electrician|plumber|carpenter|mechanic|lineman|welder|hairdresser|chef|machinist|joiner|sparky|technician|pipefitter|ironworker|tattoo artist|tattooer|baker|butcher|barber|lineworker|boilermaker|bricklayer|roofer|millwright|fitter))?\b",
            r"(?! (?:of|to|builder|rank|level|tier|in (?:training|the art))\b)|\b(?:i'm|im|i am) (?:currently |now |still |also )?(?:in|on|doing|halfway through|(?:\w+ ){1,3}into) (?:an? |my )(?:[\w-]+ ){0,2}?apprenticeship\b"), "apprentice"));

        rules
    })
}
