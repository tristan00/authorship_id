use crate::{allergen, own, sober_from, unquoted};
use claimcore::*;
use std::sync::LazyLock;

type Pick = &'static [(&'static str, &'static str)];

const SELF_IS: &str = r"i(?<!\wi)(?:'m|m| am|'ve always been| have always been|'ve been| have been)(?: (?:also|still|now|currently|definitely|totally|very much|actually|honestly|basically|always|kind of|kinda|pretty much|naturally|just|really|so|truly|absolutely|literally|officially|proudly|happily|generally|mostly|more of))*";
const LEAD: &str = concat!(r"(?:^", claimcore::flair!(), r"|\n|[,;|•/(+]|\b(?:and|plus)\b|&)[ \t*•>#\\-]*");
const FOLLOW: &str = r"(?= *(?:$|[\n,.;!)(/|&+]|(?:and|or|nor|here|myself|too|but|so|lol|btw|guy|gal|girl|woman|man|female|male|person|as well)\b))";
const ENDS: &str = r"(?= *(?:$|[\n,.;:!?)(/&*-]|(?:or|and|nor|but|so|because|since|though|tho|lol|lmao|haha|either|myself|personally|too|except|unless|at all|in my (?:entire |whole )?life|anymore|any more|any longer|anyway|anyways|alcohol|anything|whatsoever|now|these days|nowadays|really|ever|i|i'm|im)\b))";
const DRUGS: &str = r"alcohol|booze|drinking|weed|cannabis|marijuana|thc|pot|opioids?|opiates?|heroin|fentanyl|fent|oxy|oxycodone|oxycontin|percocets?|kratom|painkillers|pain ?pills|meth|methamphetamine|cocaine|coke|crack|adderall|amphetamines?|speed|stimulants|benzos?|benzodiazepines|xanax|klonopin|valium|ativan|nicotine|vaping|vapes?|cigarettes|cigs|smoking|tobacco|zyns?|juul|gambling|sports betting|betting|porn|pornography|sex|masturbation|gooning|video games|gaming|caffeine|coffee|energy drinks";
const ADDICTIONS: Pick = &[
    ("alcohol", "alcohol"), ("booze", "alcohol"), ("drinking", "alcohol"), ("weed", "cannabis"), ("cannabis", "cannabis"), ("marijuana", "cannabis"), ("thc", "cannabis"), ("pot", "cannabis"),
    ("opioid", "opioids"), ("opiate", "opioids"), ("heroin", "opioids"), ("fent", "opioids"), ("oxy", "opioids"), ("percocet", "opioids"), ("kratom", "opioids"), ("pain", "opioids"),
    ("meth", "stimulants"), ("cocaine", "stimulants"), ("coke", "stimulants"), ("crack", "stimulants"), ("adderall", "stimulants"), ("amphetamine", "stimulants"), ("speed", "stimulants"), ("stimulant", "stimulants"),
    ("benzo", "benzodiazepines"), ("xanax", "benzodiazepines"), ("klonopin", "benzodiazepines"), ("valium", "benzodiazepines"), ("ativan", "benzodiazepines"),
    ("nicotine", "nicotine"), ("vap", "nicotine"), ("cig", "nicotine"), ("smoking", "nicotine"), ("tobacco", "nicotine"), ("zyn", "nicotine"), ("juul", "nicotine"),
    ("gambl", "gambling"), ("betting", "gambling"), ("porn", "porn / sex"), ("sex", "porn / sex"), ("masturbat", "porn / sex"), ("goon", "porn / sex"),
    ("gam", "gaming"), ("caffeine", "caffeine"), ("coffee", "caffeine"), ("energy", "caffeine"), ("alcoholic", "alcohol"),
];
const SMOKING: Pick = &[
    ("non", "non-smoker"), ("never", "non-smoker"), ("don", "non-smoker"), ("do not", "non-smoker"),
    ("ex", "ex-smoker"), ("former", "ex-smoker"), ("quit", "ex-smoker"), ("stopped", "ex-smoker"), ("gave", "ex-smoker"), ("given", "ex-smoker"), ("used to", "ex-smoker"),
    ("social", "occasional / social smoker"), ("occasional", "occasional / social smoker"), ("casual", "occasional / social smoker"), ("light", "occasional / social smoker"), ("when i", "occasional / social smoker"),
    ("heavy", "daily / heavy smoker"), ("chain", "daily / heavy smoker"), ("daily", "daily / heavy smoker"), ("every day", "daily / heavy smoker"), ("pack", "daily / heavy smoker"), ("chimney", "daily / heavy smoker"), ("long", "daily / heavy smoker"),
    ("smok", "smoker (frequency unstated)"),
];
const DRINKING: Pick = &[
    ("too much", "heavy drinker"), ("now and then", "social / occasional drinker"), ("once in a while", "social / occasional drinker"),
    ("non", "non-drinker"), ("teetotal", "non-drinker"), ("never", "non-drinker"), ("anymore", "non-drinker"), ("alcohol", "non-drinker"),
    ("rarely", "rarely drinks"), ("hardly", "rarely drinks"), ("barely", "rarely drinks"), ("seldom", "rarely drinks"), ("much", "rarely drinks"), ("big", "rarely drinks"), ("really", "rarely drinks"), ("often", "rarely drinks"), ("a lot", "rarely drinks"),
    ("heavy", "heavy drinker"), ("heavily", "heavy drinker"), ("fish", "heavy drinker"), ("every", "heavy drinker"), ("daily", "heavy drinker"), ("functioning", "heavy drinker"),
    ("social", "social / occasional drinker"), ("occasional", "social / occasional drinker"), ("casual", "social / occasional drinker"), ("light", "social / occasional drinker"), ("moderate", "social / occasional drinker"),
    ("weekend", "social / occasional drinker"), ("special", "social / occasional drinker"), ("sometimes", "social / occasional drinker"),
    ("don", "non-drinker"), ("do not", "non-drinker"),
];
const SUBSTANCES: Pick = &[
    ("cigarette", "cigarettes / tobacco"), ("ciggies", "cigarettes / tobacco"), ("cigs", "cigarettes / tobacco"), ("pipe", "pipe / cigar"), ("cigar", "pipe / cigar"), ("zyn", "nicotine pouches / snus"), ("snus", "nicotine pouches / snus"), ("pouch", "nicotine pouches / snus"), ("dip", "nicotine pouches / snus"), ("chew", "nicotine pouches / snus"),
    ("skoal", "nicotine pouches / snus"), ("copenhagen", "nicotine pouches / snus"), ("tobacco", "cigarettes / tobacco"), ("pack", "cigarettes / tobacco"), ("marlboro", "cigarettes / tobacco"),
    ("newport", "cigarettes / tobacco"), ("rollies", "cigarettes / tobacco"), ("psychedelic", "psychedelics"), ("lsd", "psychedelics"), ("acid", "psychedelics"), ("shroom", "psychedelics"), ("psilocybin", "psychedelics"),
    ("dmt", "psychedelics"), ("microdose", "psychedelics"), ("drug", "drug-free"), ("vap", "vape"), ("juul", "vape"),
    ("weed", "cannabis"), ("pot", "cannabis"), ("cannabis", "cannabis"), ("marijuana", "cannabis"), ("thc", "cannabis"), ("dab", "cannabis"), ("joint", "cannabis"), ("edible", "cannabis"), ("stoner", "cannabis"), ("toke", "cannabis"),
];
const CONTRACEPTION: Pick = &[
    ("vasectom", "vasectomy"), ("snipped", "vasectomy"), ("tube", "tubal ligation / bisalp"), ("salping", "tubal ligation / bisalp"), ("bisalp", "tubal ligation / bisalp"), ("tubal", "tubal ligation / bisalp"),
    ("steril", "tubal ligation / bisalp"), ("iud", "iud"), ("mirena", "iud"), ("kyleena", "iud"), ("liletta", "iud"), ("paragard", "iud"), ("skyla", "iud"), ("coil", "iud"), ("nexplanon", "implant"), ("implanon", "implant"),
    ("implant", "implant"), ("depo", "injection"), ("nuvaring", "ring"), ("annovera", "ring"), ("pill", "pill"), ("birth control", "pill"),
];
const VISION: Pick = &[
    ("glasses", "glasses"), ("contact", "contact lenses"), ("near", "nearsighted"), ("short", "nearsighted"), ("myop", "nearsighted"), ("far", "farsighted"), ("long", "farsighted"), ("hyperop", "farsighted"),
    ("astigmat", "astigmatism"), ("colo", "colorblind"), ("lasik", "lasik"), ("prk", "lasik"), ("laser", "lasik"), ("cataract", "cataract"), ("glaucoma", "glaucoma"), ("keratoconus", "keratoconus"),
    ("eye", "one eye / monocular"), ("monocular", "one eye / monocular"),
];
const CHRONOTYPE: Pick = &[("not", "not a morning person"), ("never", "not a morning person"), ("night", "night owl / night person"), ("nocturnal", "night owl / night person"), ("morning", "morning person / early riser / early bird"), ("early", "morning person / early riser / early bird")];
const MENOPAUSE: Pick = &[("peri", "perimenopause"), ("menopaus", "menopausal or post")];
const DEVICES: Pick = &[
    ("cpap", "cpap"), ("bipap", "cpap"), ("apap", "cpap"), ("hearing", "hearing aid"), ("cochlear", "cochlear implant"), ("pacemaker", "pacemaker / icd"), ("defibrillator", "pacemaker / icd"),
    ("stimulator", "neurostimulator"), ("vns", "neurostimulator"), ("cane", "mobility aid"), ("walker", "mobility aid"), ("rollator", "mobility aid"), ("crutches", "mobility aid"),
    ("wheelchair", "mobility aid"), ("power chair", "mobility aid"), ("scooter", "mobility aid"),
];

static REPORTED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:people|they|he|she|someone|somebody|everyone|everybody|others|friends?|family|mom|mum|dad|wife|husband|partner|doctors?|therapist|you)\b[^.!?\n]{0,30}\b(?:say|says|said|told|tell|tells|call|calls|called|think|thinks|thought|accuse|accused|claim|claims|claimed)\b|\b(?:been|was|were|get|got|being) (?:told|called|accused)\b"));
static SEEK: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:looking for|look for|seeking|searching for|want|wants|wanted|need|needs|must|prefer|preferred|preferably|ideally|require|required|requirements?|deal ?breakers?|",
    r"about you|you are|you're|are you|you must|you should|if you|someone|somebody|anyone|partner|bonus|hoping|if|be|seek|wish|should|ask|asking)\b"
)));

static PARTNER: LazyLock<Re> = LazyLock::new(|| Re::new(r"(?:^|\n)[ \t*•>#\\-]*(?:about you|you|your|looking for|what i(?:'m| am| m) looking for|ideal (?:partner|match|person)|seeking|requirements?|must haves?|preferences?)\W{0,3}:(?:[^:\n]|\n(?![ \t]*\n))*$"));

fn pick(table: Pick) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| {
        let text: String = m.first().unwrap_or(m.text()).iter().collect();
        table.iter().find(|(key, _)| text.contains(key)).map(|(_, value)| value.to_string())
    }
}

fn listed(at: usize, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| {
        let lead = at == 0 || m.has(at);
        let start = if lead { m.first_index().map_or(m.start(), |g| m.start_of(g) as usize) } else { m.start() };
        if lead && (SEEK.test_in(m.string, last_mark(m.string, start, ".!?\n"), start) || PARTNER.test_in(m.string, 0, start)) || hedged(m.string, start, m.end(), own()) { None } else { value(m) }
    }
}

fn unreported(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| if REPORTED.test_in(m.string, clause(m.string, m.start()), m.start()) { None } else { value(m) }
}

fn blood(m: &Match) -> Option<String> {
    let sign = m.g(2);
    if m.g(1) == "a" && sign.contains(char::is_alphabetic) && m.text().starts_with(&['i']) {
        return None;
    }
    Some(format!("{}{}", m.g(1), if sign.contains('+') || sign.contains("pos") { "+" } else { "-" }))
}

const ALLERGIC: &str = r"(?:i(?<!\wi)(?:'m| am|'ve been| have been|'ve always been)(?: (?:also|very|severely|deathly|highly|super|really|extremely|mildly|slightly|quite|so|pretty|incredibly|horribly|terribly))* allergic to|i(?<!\wi) (?:also )?have (?:severe |bad |mild )?allergies to) (?:most |all |many |both )?";
const ALLERGEN: &str = r"(peanuts?|tree ?nuts|nuts|almonds|cashews|walnuts|shellfish|shrimp|eggs?|dairy|milk|gluten|wheat|soy|fish|sesame|cats?|dogs?|pollen|grass|ragweed|hay|birch|dust|dust mites|mold|mould|latex|penicillin|amoxicillin|sulfa(?: drugs)?|antibiotics|nsaids|ibuprofen|aspirin|bees|bee stings|wasps)\b";

pub fn rules() -> Vec<Rule> {
    timed("health habits", || {
        let mut rules: Vec<Rule> = (1..=3).map(|n| unquoted("allergies", &format!(r"{ALLERGIC}(?:[\w-]+(?: [\w-]+)?(?:, ?| and | & | or |/|, and )){{{n}}}{ALLERGEN}"), |m| allergen(m.first()), own())).collect();
        rules.extend([
        unquoted("addiction", &format!(r"i(?<!\wi)(?:'m|m| am| was|'ve been| have been|'ve always been| have always been)(?: (?:also|still|now|currently|so|very|really|severely|heavily|hopelessly|totally|completely|literally|basically|seriously|absolutely|kinda|kind of|pretty|super|extremely|badly|mildly|slightly|a bit|bit|definitely|honestly|chronically|fully|properly|legit|lowkey|genuinely))* (?:addicted|hooked) (?:to|on) (?:the |my )?({DRUGS})\b(?! (?:of|in|that|which|at|from|is|was)\b)"), unreported(pick(ADDICTIONS)), own()),
        unquoted("addiction", &format!(r"(?:i(?<!\wi)(?:'m|m| am)(?: (?:also|still|now|currently|basically|literally|just|definitely|honestly|totally|such))*|a(?<!\wa)s) (?:an? )?(?:(?:recovering|sober|raging|functioning|functional|high[- ]functioning|full[- ]blown|total|chronic|severe|heavy|massive|huge|daily|lifelong|serious|hopeless|absolute|complete|real|actual|legit|massive) )*(?:({DRUGS}) (?:addict|junkie)|(alcoholic))\b(?! (?:parent|mom|dad|mother|father|family|friend|husband|wife|partner|ex)s?\b)"), unreported(pick(ADDICTIONS)), own()),
        unquoted("addiction", &format!(r"(?:i(?<!\wi) (?:also |still |definitely |do |now |currently )?have|m(?<!\wm)y) (?:an? )?(?:(?:serious|severe|bad|real|huge|massive|terrible|horrible|crippling|mild|slight|nasty|raging|full[- ]blown|legit|actual|current|active|ongoing|lifelong|chronic) )*({DRUGS}) (?:addiction|dependency|dependence|use disorder)\b|i(?<!\wi) (?:take|took|am on|'m on|use|need) [\w-]+(?: [\w-]+)? for (?:my )?({DRUGS}) (?:addiction|dependency|dependence|use disorder)\b|(?:i(?<!\wi) (?:also |still |definitely |do )?have|m(?<!\wm)y) (?:an? )?(?:serious |bad |real )?(drinking|gambling) problems?\b|(?:i(?<!\wi) (?:also |still )?(?:have|struggle with|deal with)|m(?<!\wm)y) (alcoholism)\b"), unreported(pick(ADDICTIONS)), own()),
        unquoted("smoking_status", &format!(r"(?:{SELF_IS} (?:an? )?|a(?<!\wa)s an? )((?:non[- ]?|ex[- ]?|former |social |occasional |casual |light |heavy |chain[- ]?|daily |pack[- ]a[- ]day |long[- ]?time )smoker)\b|{LEAD}((?:non[- ]?|ex[- ]?|former |social |occasional |casual |light |heavy |chain[- ]?|daily |pack[- ]a[- ]day )smoker|don'?t smoke|never smoked){FOLLOW}"), listed(2, pick(SMOKING)), TAGGED),
        unquoted("smoking_status", &format!(r"(?<!when )(?<!if )(?<!whenever )i(?<!\wi)(?:'ve| have)? ((?:don'?t|do not|dont|never)(?: really)? smoke(?: cigarettes| cigs| tobacco)?|never smoked(?: cigarettes| cigs| tobacco| a cigarette)?|(?:only )?smoke (?:socially|occasionally|when i drink|when i'm drinking)|chain[- ]?smoke|(?:also |do |still |currently )?smoke (?:cigarettes|cigs|ciggies|tobacco)|smoke (?:a pack a day|a pack|daily|every day|like a chimney)|used to smoke(?: cigarettes| cigs| a pack(?: a day)?| tobacco)?|(?:don'?t|do not|dont|never) (?:drink|vape|party)(?: (?:or|and|nor|&|n) (?:drink|vape|party))? (?:or|and|nor|&|n) smoke)\b{ENDS}"), pick(SMOKING), own()),
        unquoted("smoking_status", &format!(r"i(?<!\wi)(?:'ve| have)?(?: (?:finally|officially|just|also|recently|since|already|completely))* ((?:quit|stopped|gave up|given up) (?:smoking(?: cigarettes| cigs| tobacco)?|cigarettes|cigs|tobacco))\b(?:{ENDS}|(?= (?:about|over|in|last|a few|a couple|years?|months?|weeks?|\d+|cold turkey|completely|for good|altogether|entirely|recently|already|when|after|on|at)\b))"), pick(SMOKING), own()),
        unquoted("addiction", &format!(r"(?:^{flair}|\n)[ \t*•>#-]*((?:{DRUGS})[- ]addicted)\b", flair = claimcore::flair!()), listed(0, unreported(pick(ADDICTIONS))), TAGGED),
        unquoted("recovering_from", r"(?<!when )(?<!once )(?<!time )(?<!until )(?<!till )(?<!if )(?<!while )i(?<!\wi)(?:'m|m| am)(?: (?:now|currently|also|still|completely|fully|totally|officially|happily|proudly|stone cold|stone-cold|newly))* (sober|in (?:early |long[- ]term )?sobriety)\b(?= *(?:$|[\n,.;:!)(]|(?:and|now|myself|since|for (?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|over|almost|nearly|about|several|many|the (?:last|past)))\b))", |m| sober_from(m.string), own()),
        unquoted("vision", &format!(r"{LEAD}(?:i )?(?:also |sometimes |usually |always )?wears? (glasses|contacts|contact lenses)\b"), listed(0, pick(VISION)), TAGGED),
        unquoted("allergies", &format!(r"{LEAD}(no) (?:known )?allergies{FOLLOW}"), listed(0, |m| allergen(m.first())), TAGGED),
        unquoted("smoking_status", r"i(?<!\wi)(?:'m|m| am)(?: (?:also|still|definitely))? (a smoker|a cigarette smoker)(?= *(?:$|[\n,.;!)]|(?:and|but|so|myself|too|lol|btw)\b))", pick(SMOKING), own()),
        unquoted("drinking", &format!(r"(?:{SELF_IS} (?:an? )?|a(?<!\wa)s an? )((?:non[- ]?|social |occasional |casual |light |moderate |weekend |heavy |functioning )drinker|teetotal(?:er|ler)?)\b|{LEAD}((?:(?:non[- ]?|social |occasional |casual |light |moderate |weekend ){{1,2}})drinker|teetotal(?:er|ler)?|don'?t drink(?! too\b)|don'?t smoke (?:or|and|&|n|nor) drink|zero alcohol|drinks? (?:socially|occasionally)|rarely drinks?){FOLLOW}"), listed(2, pick(DRINKING)), TAGGED),
        unquoted("drinking", &format!(r"(?<!when )(?<!if )(?<!whenever )i(?<!\wi)(?: (?:already|also|just|personally|honestly|generally|actually|usually))* ((?:don'?t|do not|dont|never) drink(?: alcohol| anymore| any more| at all)?|(?:don'?t|do not|dont|never) smoke (?:&|and|or|nor|n) drink|(?:don'?t|do not|dont) (?:really drink|drink (?:much|often|a lot|that much|very often|very much))|(?:very |pretty |only )?(?:rarely|hardly(?: ever)?|barely|seldom) drink|(?:only |also |do )?(?:smoke (?:and|&|n) )?drink (?:socially|occasionally(?: on (?:the )?weekends)?|on (?:the )?weekends|on special occasions|every now and then|once in a while)|(?:occasionally|sometimes|socially) drink|drink (?:heavily|too much|way too much|like a fish|every (?:day|night)|daily))\b(?! (?:and drive|or smoke much)\b){ENDS}"), pick(DRINKING), own()),
        unquoted("drinking", r"i(?<!\wi)(?:'m|m| am)(?: (?:really|just|also|honestly|generally))? (not (?:much of a|a big|really a) drinker)\b", pick(DRINKING), own()),
        unquoted("substance_use", &format!(r"{SELF_IS} (?:an? )?(?:(?:big|huge|daily|functional|functioning|casual|occasional|lifelong|massive|total|chronic|proud|medical|heavy|regular|habitual|weekend|recreational) )*(stoner|pothead|weed smoker|cannabis user|marijuana user|pipe smoker|cigar smoker|vaper|psychedelics user)\b|{LEAD}(pipe smoker|cigar smoker|drug[- ]free){FOLLOW}"), listed(2, pick(SUBSTANCES)), TAGGED),
        unquoted("substance_use", r"i(?<!\wi) (?:also |still |do |only |occasionally |sometimes |regularly |usually |mostly |mainly |currently |now |just )?(?:smoke (cigarettes|cigs|ciggies|a pack|marlboros?|newports?|rollies|tobacco|weed|pot|cannabis|marijuana|joints|a pipe|pipes?|cigars?)|(?:use|take|use a|dip|chew) (zyns?|snus|nicotine pouches|nic pouches|chewing tobacco|skoal|copenhagen)|vape (weed|thc|cannabis)|(vape)(?! (?:shops?|stores?|pens? (?:for|from))\b)|(?:do|take|microdose(?: on| with)?) (psychedelics|lsd|acid|shrooms|psilocybin|dmt)|(microdose))\b", pick(SUBSTANCES), own()),
        unquoted("substance_use", r"i(?<!\wi)(?: (?:don'?t|do not|dont|never) do (?:any )?(drugs)|(?:'ve| have) never (?:done|tried|taken|used) (?:any )?(drugs)|(?:'m|m| am|'ve always been| have always been)(?: completely| totally| 100%)? (drug[- ]free))\b(?! (?:but|except|besides|other than|apart)\b)", pick(SUBSTANCES), own()),
        unquoted("sexual_health_status", &format!(r"(?:{LEAD}|\b(?:i'm|im|i am|am|clean|fully|totally|100%|completely|always|strictly|also|and)\s+)(ddf|drug (?:and|&|n) disease[- ]free|(?:std|sti|std/sti|sti/std|stds|stis|disease)[- ]free|clean (?:and |& |, )?(?:recently )?tested)(?![\w-])(?! *(?:only|guys?|men|bottoms?|tops?|pls|please|required|preferred|is a must|a must|\?|bros?|partners?|fun|play|people|chat|dudes?|ppl|hookups?|sex|discreet|life|lifestyle|status)\b)"), listed(0, pick(&[("", "tested negative / std-free")])), TAGGED),
        unquoted("sexual_health_status", &format!(r"(?:{LEAD}|i(?<!\wi)(?:'m|m| am)(?: (?:also|currently|still|always))? )(hiv(?:[- ]?neg(?:ative)?\b|-(?![\w-])))"), listed(0, pick(&[("", "tested negative / std-free")])), TAGGED),
        unquoted("sexual_health_status", &format!(r"(?:{LEAD}|i(?<!\wi)(?:'m|m| am|'ve been| have been)(?: (?:also|currently|now|still|already))? )(on prep)\b(?! (?:duty|for|work|shift|cook|day|crew|team|school|time|list|station|table)\b)|i(?<!\wi) (?:take|'m taking| am taking|started|started taking) (prep)\b(?! (?:for|time|work)\b)"), listed(0, pick(&[("", "on prep")])), TAGGED),
        unquoted("sexual_health_status", r"i(?<!\wi)(?:'m|m| am)(?: (?:also|now|currently))? (hiv[- ]?(?:positive|pos\b|\+)|poz\b|hsv[- ]?[12][- ]?(?:positive|pos\b|\+)|hsv[- ]?(?:positive|pos\b|\+)|herpes[- ]?(?:positive|pos\b|\+)|hpv[- ]?(?:positive|pos\b|\+))", pick(&[("", "has an sti")]), own()),
        unquoted("sexual_health_status", r"i(?<!\wi) (?:just |recently |always |regularly )?(?:got |get )?tested (?:clean|negative for (?:everything|all|stds?|stis?))\b", pick(&[("", "tested negative / std-free")]), own()),
        unquoted("contraception", &format!(r"i(?<!\wi)(?:'ve| have)?(?: (?:already|recently|just|finally|also|since))* (?:had|got|gotten|have) (?:a |my |the )?(vasectomy|(?:bilateral )?salpingectomy|bisalp|tubal(?: ligation)?|tubes (?:tied|removed|out))\b(?! (?:consult|consultation|appointment|scheduled|next|reversal|soon|booked|factor|pregnancy|infertility|blockage|issues)\b)|i(?<!\wi) (?:got|had|have been|'ve been|was) (snipped|vasectomi[sz]ed|sterili[sz]ed)\b|i(?<!\wi)(?:'m|m| am)(?: (?:also|already|surgically))? (vasectomi[sz]ed|vasectomied|vasectomy[- ]safe|sterili[sz]ed|snipped)\b|m(?<!\wm)y (vasectomy|tubes (?:are|were) (?:tied|removed|out|gone))\b(?! (?:consult|consultation|appointment|reversal|is (?:scheduled|booked|on|tomorrow|next|coming|in))\b)|{LEAD}(vasectomy[- ]safe|vasectomi[sz]ed|vasectomied|snipped|vasectomy){FOLLOW}"), listed(5, pick(CONTRACEPTION)), TAGGED),
        unquoted("contraception", r"(?:i(?<!\wi) (?:also |currently |still |now |just )?(?:have|got)|m(?<!\wm)y|i(?<!\wi)(?:'m|m| am|'ve been| have been)(?: (?:also|currently|still|now|back))? on) (?:an? |the |my )?(?:(?:copper|hormonal|new|current) )?(iud|mirena|kyleena|liletta|paragard|skyla|copper coil|nexplanon|implanon|birth control implant|arm implant|nuvaring|annovera|depo(?:[- ]provera)?)\b(?! (?:removed|out|taken out|pulled|consult|appointment|insertion appointment)\b)", pick(CONTRACEPTION), own()),
        unquoted("contraception", r"i(?<!\wi)(?:'m|m| am|'ve been| have been)(?: (?:also|currently|still|now|back))? on (?:the )?(?:(?:birth control |mini[- ]?|combined |combination |progestin[- ]only )?(pill)|(?:hormonal )?(birth control))\b(?! (?:for (?:my|the|acne|pcos|endo)|to (?:treat|help|manage|control)|because|bc)\b)|i(?<!\wi) (?:take|'m taking| am taking) (?:the )?(?:birth control )?(pill|birth control)\b(?! (?:for|to|because)\b)", pick(CONTRACEPTION), own()),
        unquoted("contraception", r"i(?<!\wi)(?:'m|m| am)(?: currently)? not on (?:any )?(?:birth control|bc|contraception|hormonal birth control)\b|i(?<!\wi) (?:don'?t|do not|dont) use (?:any )?(?:birth control|contraception)\b", pick(&[("", "no birth control")]), own()),
        unquoted("vision", r"i(?<!\wi) (?:also |do |still |now |have to |need to |usually |always |sometimes |already |only )?(?:wear|need) (?:prescription |reading |my )?(glasses|contacts|contact lenses)\b(?! (?:of|for (?:wine|water|beer))\b)|i(?<!\wi) (?:also |do |still |now |already )?have (?:prescription |reading )?(glasses)\b(?! (?:of|for (?:wine|water|beer))\b)|m(?<!\wm)y (?:prescription |reading |new |old )?(glasses|contact lens(?:es)?)\b(?! of\b)", pick(VISION), own()),
        unquoted("vision", r"i(?<!\wi)(?:'m|m| am|'ve been| have been|'ve always been)(?: (?:also|very|extremely|severely|pretty|really|so|super|slightly|mildly|a bit|partially|totally|completely|quite|incredibly|insanely|highly|both|legally|horribly|terribly|fairly))* (near[- ]?sighted|far[- ]?sighted|myopic|hyperopic|colou?r[- ]?blind|red[- ]green colou?r[- ]?blind|blind in (?:one|my (?:left|right)) eye|monocular)\b", pick(VISION), own()),
        unquoted("vision", r"i(?<!\wi) (?:also |do |still |now )?have (?:an? )?(?:(?:slight|mild|bad|severe|high|strong|really bad|irregular|minor) )?(astigmatism|myopia|hyperopia|keratoconus|glaucoma|cataracts?|colou?r ?blindness)\b|m(?<!\wm)y (astigmatism|myopia|glaucoma|keratoconus|cataracts?)\b|i(?<!\wi) (?:had|got|'ve had|have had) (lasik|prk|laser eye surgery)\b|i(?<!\wi) (?:only )?have one (?:good |working |functioning )?(eye)\b|i(?<!\wi) (?:have|wear) a (?:glass|prosthetic) (eye)\b|i(?<!\wi) can only see (?:out of|with) one (eye)\b", pick(VISION), own()),
        unquoted("chronotype", &format!(r"{SELF_IS} (?:an? )?(?:(?:huge|big|total|natural|real|true|massive|bit of a|extreme|serious|chronic|lifelong|hardcore|complete|definite|early) )*(night ?owl|night person|nocturnal|morning person|early riser|early bird)\b(?! (?:special|discount|price|pricing|ticket|registration|deal|rate)s?\b)|{LEAD}(night ?owl|night person|morning person|early riser){FOLLOW}"), listed(2, pick(CHRONOTYPE)), TAGGED),
        unquoted("chronotype", r"i(?<!\wi)(?:'m|m| am)(?: (?:also|just|definitely|really|so|still|absolutely|totally|very much))* (not) (?:a|much of a|really a|exactly a|the biggest) morning person\b|i(?<!\wi)(?:'ve| have) (never) been a morning person\b", pick(CHRONOTYPE), own()),
        unquoted("menopause_stage", r"i(?<!\wi)(?:'m|m| am| was|'ve been| have been| (?:just |recently |have |'ve )?(?:started|entered|hit)| went into)(?: (?:also|now|currently|still|officially|finally|already|definitely|solidly|well|firmly|fully))* (?:(?:in (?:full |early |late )?|going through |entering )?(perimenopause|perimenopausal|peri-menopausal|peri[- ]menopause|menopause|menopausal|post[- ]?menopausal|post[- ]?menopause|surgical menopause|surgically menopausal)|in (?:early |late )?(peri))\b(?! (?:age|years?|symptoms|clinic|doctor)\b)", pick(MENOPAUSE), own()),
        unquoted("blood_type", r"(?:i(?<!\wi)(?:'m|m| am)(?: (?:also|type|blood type))*|m(?<!\wm)y blood(?: type| group)? (?:is|=|:)|m(?<!\wm)y blood type|b(?<!\wb)lood type:?|i(?<!\wi) have) (?:type )?(a|b|ab|o)(\+|-| ?pos\b| ?positive\b| ?neg\b| ?negative\b)(?![\w+-])(?= *(?:$|[\n,.;!)&]|(?:and|but|so|which|too|myself|here|blood|btw|lol)\b))", blood, own()),
        unquoted("blood_type", r"i(?<!\wi)(?:'m|m| am)(?: also)? (?:a |the )?(universal donor)\b", pick(&[("", "o-")]), own()),
        unquoted("sobriety_year", concat!(r"i(?<!\wi)(?:'ve| have|'m|m| am)?(?: been)? (?:sober|clean) since (?:\w+ (?:\d{1,2}(?:st|nd|rd|th)?,? )?)?(19[6-9]\d|20[01]\d|202[0-6])\b|m(?<!\wm)y (?:sobriety|sober|clean) date (?:is |was |= |: |of )?(?:\w+ (?:\d{1,2}(?:st|nd|rd|th)?,? )?|\d{1,2}[/.-]\d{1,2}[/.-])?(19[6-9]\d|20[01]\d|202[0-6])\b|(?:^", claimcore::flair!(), r"|\n)\W*(?:sober|clean|sobriety) (?:date|since):? (?:\w+ (?:\d{1,2}(?:st|nd|rd|th)?,? )?|\d{1,2}[/.-]\d{1,2}[/.-])?(19[6-9]\d|20[01]\d|202[0-6])\b"), |m| m.first_s(), own()),
        unquoted("medical_devices", r"(?:m(?<!\wm)y|i(?<!\wi)(?:'m| am)? (?:also |now |currently |still |just )?(?:use|using|wear|wearing|have|got|started|switched to|am on|on|upgraded to)) (?:a |an |the |new |first |trusty |own |electric |manual |power |rolling )?(cpap|bipap|apap|cpap machine|bipap machine|hearing aids?|cochlear implants?|pacemaker|defibrillator|spinal cord stimulator|vns|cane(?! corsos?\b)|walking cane|walker|rollator|crutches|wheelchair|power chair|mobility scooter)(?![\w-])|i(?<!\wi)(?:'m|m| am)(?: (?:also|now|currently|still|basically|technically))* an? (?:full[- ]time |part[- ]time |ambulatory |part time )?(wheelchair) user\b", pick(DEVICES), own()),
        unquoted("physical_conditions", r"i(?<!\wi)(?:'ve| have)? (?:also |still |do )?(?:have|had|was diagnosed with|got diagnosed with|been diagnosed with) (?:(?:relapsing[- ]remitting|progressive|stage (?:[1-4]|iv|i{1,3})|severe|mild|deep infiltrating) )?(ms|rrms|ppms|spms|endo)\b(?= *(?:$|[\n,.;:!)(]|(?:and|but|so|since|for|too|myself|which|lol|diagnosed|as well)\b))", pick(&[("endo", "endometriosis"), ("", "multiple sclerosis")]), own()),
        ]);
        rules
    })
}
