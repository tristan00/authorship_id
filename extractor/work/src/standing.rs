use crate::*;

const NOW: &str = r"(?:(?:currently|now|also|still|mostly|mainly|primarily|actually|only|just|usually|normally|permanently|fully|thankfully|luckily|basically|both|full[- ]?time|part[- ]?time) )*";
const SUBJECT: &str = r"(?<!when )(?<!whenever )(?<!if )\bi";
const NOT_WHEN: &str = r"(?<!when )(?<!whenever )(?<!if )(?<!while )(?<!once )(?<!until )(?<!minute )";
const AM: &str = r"(?<!when )(?<!whenever )(?<!if )(?:i'm|im|i am|i've been|ive been|i have been)";
const TEMPORARY: &str = r"(?!\s*(?:today|tonight|tomorrow|this (?:week|morning|afternoon|evening|weekend|month)|for (?:the|a) (?:day|week|few)|sick|(?:on )?(?:mon|tue|wed|thu|fri)|a few|\d|one day|two days|three days|four days|a couple|some days|most days|certain days|half|part of|sometimes|occasionally|once|twice))";
const NIGHTS: &str = r"(?:nights|overnights?|night ?shifts?|overnight shifts?|graveyards?(?: shifts?)?|third shift|midnights?(?: shift)?)";
const NOT_NIGHT: &str = r"(?! (?:oats|bags?|trips?|stays?|guests?|delivery|shipping|parking|camping|hikes?|flights?|bus|before|ago)\b)";
const NINE_FIVE: &str = r"(?:9[- ]?(?:to|-)[- ]?5|nine[- ]to[- ]five)";
const TWELVE: &str = r"(?:12|twelve)[- ]?(?:hour|hr|h)s? shifts";
const COUNT: &str = r"(?:(?:\d|two|three|four)(?: ?(?:-|to|or) ?\d)? )?";
const CLASS: &str = r"(?:(lower[- ]middle|upper[- ]middle|middle[- ]upper|middle|working|upper|lower)[- ]class|(blue[- ]collar)|(old money))";
const CLASS_END: &str = concat!(r"(?=\s*(?:$|[.,!;:)(/\n-]|\b(?:and|but|so|family|families|household|home|background|upbringing|roots|myself|too|now|here|guy|man|woman|person|people|american|kid|kids|lad|dude|girl|boy|",
    r"white|black|parents|folks|area|neighbou?rhood|town|in|with|from|by|at|if|though|tbh|lol|which|who|since|income|status|lifestyle|bracket|standards|according|worker|workers|i|we)\b))");
const SPECIALTY: &str = concat!(r"(?:surgery|surgical|general surgery|gen surg|neurosurgery|ortho|orthopedic|orthopaedic|medicine|internal medicine|im|family medicine|fm|family med|em|emergency medicine|er|peds|pediatric|",
    r"pediatrics|paediatric|psych|psychiatry|psychiatric|ob|obgyn|ob/gyn|ob-gyn|anesthesia|anesthesiology|anaesthetics|radiology|rads|neurology|neuro|derm|dermatology|ent|pathology|urology|ophtho|",
    r"ophthalmology|cardiology|cards|gi|oncology|heme/onc|nephrology|pulm|pulmonary|critical care|icu|pccm|endo|rheum|infectious disease|plastics|vascular|transplant|trauma|rad onc|pharmacy|dental|",
    r"medical|md|do|pgy-?\d)");
const RESIDENT_YEAR: &str = r"(?:(?:first|second|third|fourth|fifth|sixth|final|chief|senior|junior|\d(?:st|nd|rd|th))[- ]year )";

static HOMEMAKER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:housewife|househusband|house husband|home ?maker|home ?keeper|domestic engineer|tradwife|stay[- ]at[- ]home (?:wife|husband))\b"));

pub(crate) const BUSINESS_OWNER: &str = "business owner";

pub(crate) fn homemaking(m: &Match) -> Option<String> {
    Some(if HOMEMAKER.test(m.text()) { "homemaker / housewife" } else { "stay-at-home parent" }.to_string())
}

#[track_caller]
fn stated(attribute: &'static str, pattern: &str, value: &'static str) -> Rule {
    rule(attribute, pattern, scoped(fixed(value)), self_hedge())
}

fn class(m: &Match) -> Option<String> {
    let value = if m.nonempty(2).is_some() {
        "working class"
    } else if m.nonempty(3).is_some() {
        "upper class"
    } else {
        match m.gs(1)?.replace('-', " ").as_str() {
            "lower middle" => "lower middle class",
            "upper middle" | "middle upper" => "upper middle class",
            "middle" => "middle class",
            "working" | "lower" => "working class",
            "upper" => "upper class",
            _ => return None,
        }
    };
    Some(value.to_string())
}

fn school_kind(m: &Match) -> Option<String> {
    let word = m.gs(1).or_else(|| m.gs(2))?;
    Some(if word == "public" { "public school" } else { "private school" }.to_string())
}

pub fn rules() -> Vec<Rule> {
    timed("work.standing", || {
        let mut rules = Vec::new();
        let remote = [
            format!(r"{SUBJECT} {NOW}(?:work|wfh)(?: (?:fully|100%|completely|entirely))? (?:from home|at home(?! depot)|remote(?:ly)?)\b{TEMPORARY}"),
            format!(r"{SUBJECT} {NOW}wfh\b{TEMPORARY}"),
            format!(r"\b{AM} {NOW}(?:working (?:fully |100% |completely |entirely )?(?:from home|remote(?:ly)?)|wfh|(?:fully |100% |completely |permanently )?remote(?= (?:now|for (?:my|work)|at (?:my|work)|worker|employee)\b|\s*(?:$|[.,!;)\n])))\b{TEMPORARY}"),
            concat!(r"\bmy (?:job|work|role|position|gig|current job|day job|new job) is (?:fully |100% |completely |entirely |mostly |now |also )*(?:remote|wfh|work from home)\b|",
                r"\bi (?:have|got|landed|found|started) an? (?:new |good |great |fully |full[- ]?time |part[- ]?time |100% |permanent )*(?:remote|wfh|work[- ]from[- ]home) (?:job|position|role|gig)\b|",
                r"(?<!quit )(?<!lost )(?<!left )(?<!leave )(?<!from )(?<!after )\bmy (?:new |current )?(?:remote|wfh|work[- ]from[- ]home) (?:job|position|role|gig)\b|\b(?:i'm|im|i am|as) an? remote (?:worker|employee)\b").to_string(),
        ];
        for pattern in &remote {
            rules.push(stated("work_arrangement", pattern, "remote / work from home"));
        }
        let hybrid = concat!(r"(?<!when )(?<!whenever )(?<!if )\b(?:i'm|im|i am) (?:currently |now |also )?(?:fully )?hybrid(?=\s*(?:$|[.,!;:)(\n-]|\b(?:now|and|but|so|at|with|for|which)\b))|\bi (?:currently |now |also )?work (?:a )?hybrid\b(?! car)|",
            r"\bmy (?:job|role|position|work|schedule|current job) is (?:now |also )?hybrid\b|\bi (?:have|got|landed) an? (?:new )?hybrid (?:schedule|role|job|position|work schedule|arrangement)\b|",
            r"\bi (?:currently |now |also |only )?work from home (?:[1-4]|one|two|three|four) days? (?:a|per|each) week\b|\bi(?:'m| am)? (?:currently |now |only )?(?:in (?:the )?office|go (?:in|into the office)) (?:[1-4]|one|two|three|four) days? (?:a|per|each) week\b");
        rules.push(stated("work_arrangement", hybrid, "hybrid"));
        let office = format!(r"\bi (?:currently |now |also |still |actually )?work (?:in|from|out of) (?:an?|the) office\b(?! (?:job|chair|building|supply|supplies|setting|environment|side|part|department|world)\b){TEMPORARY}|")
            + concat!(r"(?<!when )(?<!whenever )(?<!if )\b(?:i'm|im|i am) (?:fully )?in[- ]office(?= (?:full[- ]?time|every ?day|5 days|five days|daily|monday|mon)\b|\s*(?:$|[.,!;)\n]))|",
                r"\bi (?:currently |now |also )?(?:work on[- ]?site|go (?:in|into the office) (?:every ?day|daily|5 days|five days|full[- ]?time)|commute (?:to|into) (?:the |an |my )office)\b|",
                r"\bmy (?:job|role|position|work) is (?:fully |100% |entirely )?(?:in[- ]office|on[- ]?site|in person)\b");
        rules.push(stated("work_arrangement", &office, "in office / on site"));

        let night = [
            format!(r"{SUBJECT} {NOW}(?:work|do|pull) (?:the |a )?{NIGHTS}\b{NOT_NIGHT}"),
            format!(r"\b{AM} {NOW}(?:working (?:the |a )?{NIGHTS}|on {NIGHTS}|on the (?:night|overnight|graveyard|third) shift|an? (?:permanent )?(?:night ?shift|overnight|graveyard|third shift) (?:\w+ )?(?:worker|nurse|rn|cna|tech|technician|guard|security|cashier|associate|stocker|operator|driver|clerk|attendant|supervisor|manager|employee|auditor|baker|doctor|medic|paramedic|emt|officer|cop|guy|girl|person))\b{NOT_NIGHT}"),
            format!(r"(?:^{flair}|[.!?\n]\s*)(?:currently |now |still |also )?(?:work|working) (?:the )?{NIGHTS}\b{NOT_NIGHT}(?! (?:is|are|was|can|could|will|would|sucks|really|makes|has|have)\b)", flair = claimcore::flair!()),
            r"\b(?:i'm|im|i am) (?:an? )?night ?shifter\b|(?<!quit )(?<!lost )(?<!left )(?<!after )(?<!last )\bmy (?:night ?shifts|overnight shifts|graveyard shifts|night ?shift (?:job|schedule|hours))\b|\bas an? night ?shift(?:er| worker| nurse)\b".to_string(),
        ];
        for pattern in &night {
            rules.push(stated("work_schedule", pattern, "night shift / overnights"));
        }
        let day = format!(r"{SUBJECT} {NOW}(?:work|do) (?:the |a )?(?:day ?shifts?|days(?=\s*(?:$|[.,!;)\n]|\b(?:and|but|so|now|at|as|while)\b))|{NINE_FIVE})\b|")
            + &format!(r"\b(?:i'm|im|i am) {NOW}(?:working (?:the |a )?(?:day ?shifts?|{NINE_FIVE})|on (?:the )?day ?shift|on days(?=\s*(?:$|[.,!;)\n]|\b(?:and|but|so|now)\b)))\b|")
            + &format!(r"\bi have an? (?:regular |normal |boring |standard |typical )?{NINE_FIVE}(?: job| office job| desk job)?\b");
        rules.push(stated("work_schedule", &day, "day shift"));
        let swing = format!(r"{SUBJECT} {NOW}(?:work|do) (?:the |a )?(?:swing|second|evening) shifts?\b|\b(?:i'm|im|i am) {NOW}(?:working (?:the |a )?(?:swing|second|evening) shifts?|on (?:the )?(?:swing|second|evening) shifts?|on swings)\b|")
            + r"(?<!after )(?<!last )\bmy swing shifts?\b";
        rules.push(stated("work_schedule", &swing, "swing shift"));
        let rotating = format!(r"{SUBJECT} {NOW}(?:work|do) (?:rotating shifts?|rotating schedules?|a rotating (?:schedule|roster|shift)|shift ?work|shifts(?! at night)(?=\s*(?:$|[.,!;)\n]|\b(?:and|but|so|at|in|as|for|now)\b))|swing rotation|fifo)\b|")
            + &format!(r"\b(?:i'm|im|i am) {NOW}(?:an? )?(?:shift ?worker|fifo(?: worker| miner)?(?=\s*(?:$|[.,!;)\n]|\b(?:and|but|so|now|in|at|on)\b))|on (?:a )?rotating (?:shifts?|schedule|roster))\b|\bas an? shift ?worker\b");
        rules.push(stated("work_schedule", &rotating, "rotating / shift work"));
        let four = format!(r"{SUBJECT} {NOW}(?:work|do|have) (?:an? )?(?:4|four)[- ]day (?:work ?)?weeks?\b(?!\s*(?:this|next|coming|ahead|because|due|thanks))|{SUBJECT} {NOW}(?:work|do) (?:4|four) (?:10s|tens)\b|")
            + &format!(r"\b(?:i'm|im|i am) {NOW}on (?:an? )?(?:4|four)[- ]day (?:work ?)?weeks?\b|\bmy (?:4|four)[- ]day (?:work ?)?weeks?\b|\bmy (?:4|four) (?:10s|tens)\b");
        rules.push(stated("work_schedule", &four, "4-day week"));
        let twelve = format!(r"{SUBJECT} {NOW}(?:work|do|pull) {COUNT}{TWELVE}\b|{SUBJECT} {NOW}(?:work|do) {COUNT}12s\b|\b(?:i'm|im|i am) {NOW}(?:working|on|doing) {COUNT}{TWELVE}\b|(?<!after )(?<!last )\bmy {TWELVE}\b");
        rules.push(stated("work_schedule", &twelve, "12-hour shifts"));

        let homeschooled = concat!(concat!(r"(?:\b(?:i was|i got|i grew up|i've been|ive been|i have been|i'm|im|i am|i myself was|i too was|we were|me and (?:my )?(?:[\w']+ ){1,3}were)|(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:was|been)|\bas (?:someone|somebody|a person|an? [\w-]+(?: [\w-]+)?) who (?:was|got))(?: (?:also|actually|mostly|partially|partly|briefly|completely|fully|entirely|technically|both|all))* "),
            r"home[- ]?(?:schooled|educated)\b|\bas an? (?:former |ex-?|fellow )?(?:home[- ]?schooled (?:kid|child|student|person|teen)|homeschooler)\b|\bi was an? home[- ]?school(?:ed)? (?:kid|child|student)\b|",
            concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? )?(?:former |ex-?)?home[- ]?schooled (?:kid|child|student) here\b"));
        rules.push(stated("schooling", homeschooled, "homeschooled"));
        let boarding = concat!(r"(?:\bi (?:also |both |actually )?|\bas (?:someone|somebody|a person|an? [\w-]+(?: [\w-]+)?) who (?:also |actually )?)(?:went to|attended|was (?:at|in|sent to)|grew up (?:in|at)|spent (?:\w+ ){1,3}(?:at|in)|got sent to) (?:an? )?(?:\w+ )?boarding schools?\b|",
            r"\b(?:i've|ive|i have) been (?:at|in) (?:an? )?boarding school\b|\b(?:i'm|im|i am) (?:currently |still )?(?:at|in) (?:an? )?boarding school\b");
        rules.push(stated("schooling", boarding, "boarding school"));
        let kinds = concat!(r"(?:\bi (?:also |both |actually |only |mostly )?|\bas (?:someone|somebody|a person|an? [\w-]+(?: [\w-]+)?) who (?:also |actually )?)(?:went to|attended|was (?:in|at|sent to|educated (?:at|in))|grew up (?:in|going to)) (?:an? |the )?",
            r"(?:(?:expensive|fancy|small|tiny|big|large|local|elite|exclusive|prestigious|strict|religious|christian|catholic|jesuit|all[- ](?:boys|girls|boy|girl)|good|bad|shitty|rural|urban|inner[- ]city|underfunded|crappy|decent|regular|normal|american) )*",
            r"(private|public|independent|prep|catholic|parochial)(?: (?:catholic|christian|religious|elementary|high|middle|primary|secondary|boarding|grade|prep))? (?:schools?|academy)\b|",
            r"\b(?:i was|i'm|im|i am|as) an? (?:former )?(private|public) school (?:kid|student|child|boy|girl)\b");
        rules.push(rule("schooling", kinds, scoped(Box::new(school_kind)), self_hedge()));

        let belong = concat!(r"\b(?:i'm|im|i am|i was|we're|we are|we were|i've always been|i have always been|i've been|i'm still|i am still|i grew up|we grew up|i was raised|i was born|i was brought up|i'm from|im from|i am from|",
            r"i come from|i came from|we come from|i belong to|i'm part of|i am part of|i'm considered|i am considered|i consider myself|my family (?:is|was|are|were)|my parents (?:are|were)|i was born into|i was raised in|i grew up in)",
            r"(?: (?:a|an|the|very|solidly|firmly|comfortably|pretty|fairly|squarely|solid|typical|humble|good|proud|relatively|financially|technically|basically|just|still|now|also|from|in|into|part of|definitely|rural|poor|struggling|actually|really|probably|considered))*? ");
        rules.push(rule("social_class", &format!(r"{belong}{CLASS}{CLASS_END}"), scoped(Box::new(class)), self_hedge()));
        rules.push(rule("social_class", &format!(r"(?:^{flair}|[.!?\n]\s*)(?:i'm |im |i am |we're |we are )?(?:proudly |also )?(?:part of|a (?:proud )?member of) the {CLASS}{CLASS_END}", flair = claimcore::flair!()), scoped(Box::new(class)), self_hedge()));
        rules.push(rule("social_class", &format!(r"(?:(?:^{flair}|[.!?\n,]\s*)|\bi(?:'m| am)? (?:[\w'-]+ ){{0,4}}?)as an? (?:proud |\w+ )?{CLASS}(?= (?:person|man|woman|guy|family|kid|american|worker|household|immigrant|parent|mom|dad|individual)\b)", flair = claimcore::flair!()), scoped(Box::new(class)), self_hedge()));

        let debt_free = format!(r"{NOT_WHEN}\b(?:i'm|im|i am|we're|we are|i've been|ive been|i have been|we've been|i became|we became)(?: (?:now|finally|officially|completely|totally|fully|entirely|100%|currently|also|still|happily|proudly|consumer))* debt[- ]free\b|")
            + concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:now |finally |officially )?debt[- ]free(?= since\b|\s*(?:$|[.!\n]))");
        rules.push(stated("financial_situation", &debt_free, "debt-free"));

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

        let residency = [
            format!(r"\b(?:i'm|im|i am|as) (?:currently |now |still |just |also )?an? {RESIDENT_YEAR}?{SPECIALTY} (?:resident|fellow|registrar)\b"),
            format!(r"\b(?:i'm|im|i am) (?:currently |now |still |just |also )?an? {RESIDENT_YEAR}(?:resident|fellow)\b(?! (?:of|in|at) (?:the )?(?:dorm|hall|building)s?\b)"),
            r"\b(?:i'm|im|i am|as) (?:currently |now |still |just |also )?an? (?:resident (?:physician|doctor|surgeon|psychiatrist|pharmacist|dentist|vet)|(?:medical|surgical|clinical) (?:resident|fellow))\b".to_string(),
            format!(r"\b(?:i'm|im|i am) (?:currently |now |still |also )?(?:in|doing|finishing|halfway through|in the middle of) (?:my |a )?(?:(?:first|second|third|fourth|fifth|final|last|\d(?:st|nd|rd|th)) year of )?(?:{SPECIALTY} )?(?:residency\b(?! (?:application|status|permit|card|visa|requirements?)\b)|{SPECIALTY} fellowship\b)"),
            concat!(r"\b(?:i'm|im|i am|as) an? pgy-?[1-8]\b|(?:^", claimcore::flair!(), r"|\n)[ \t>*#-]*pgy-?[1-8]\b").to_string(),
        ];
        for pattern in &residency {
            rules.push(stated("current_study_level", pattern, "resident / fellow"));
        }
        rules.push(stated("current_study_level", concat!(r"\b(?:i'm|im|i am|i'm currently|currently) (?:currently |still |now |also )?(?:in|at|attending|going to|enrolled (?:in|at)) (?:a |the |my )?(?:local )?community college\b|",
            r"\bi (?:currently |now |also )?(?:go to|attend) (?:a |the |my )?(?:local )?community college\b|\b(?:i'm|im|i am|as) an? community college student\b|\bcommunity college student here\b"), "community college"));
        rules
    })
}
