use crate::quoted;
use claimcore::*;
use std::sync::LazyLock;

const DRUGS: &[&str] = &[
    "adderall", "addy", "vyvanse", "elvanse", "ritalin", "concerta", "focalin", "medikinet", "methylphenidate", "lisdexamfetamine", "dexedrine", "dextroamphetamine", "strattera",
    "atomoxetine", "qelbree", "viloxazine", "intuniv", "guanfacine", "clonidine", "modafinil", "armodafinil", "provigil", "nuvigil", "wellbutrin", "bupropion",
    "lexapro", "escitalopram", "zoloft", "sertraline", "prozac", "fluoxetine", "paxil", "paroxetine", "celexa", "citalopram", "luvox", "fluvoxamine", "trintellix",
    "vortioxetine", "viibryd", "vilazodone", "effexor", "venlafaxine", "cymbalta", "duloxetine", "pristiq", "desvenlafaxine", "fetzima", "remeron", "mirtazapine",
    "trazodone", "trazadone", "auvelity", "spravato", "amitriptyline", "nortriptyline", "buspirone", "buspar", "hydroxyzine", "vistaril", "propranolol",
    "xanax", "alprazolam", "klonopin", "clonazepam", "ativan", "lorazepam", "valium", "diazepam",
    "abilify", "aripiprazole", "seroquel", "quetiapine", "latuda", "lurasidone", "risperdal", "risperidone", "zyprexa", "olanzapine", "vraylar", "cariprazine", "rexulti",
    "caplyta", "invega", "clozapine", "clozaril", "haldol", "geodon", "lithium", "lamictal", "lamotrigine", "depakote", "topamax", "topiramate", "trileptal",
    "oxcarbazepine", "tegretol", "carbamazepine", "keppra", "levetiracetam", "briviact", "vimpat", "lacosamide", "xcopri", "gabapentin", "neurontin", "pregabalin",
    "lyrica", "zonisamide", "ambien", "zolpidem", "lunesta", "belsomra", "quviviq", "prazosin",
    "ozempic", "wegovy", "semaglutide", "rybelsus", "mounjaro", "zepbound", "tirzepatide", "tirz", "zep", "sema", "saxenda", "victoza", "liraglutide", "trulicity",
    "retatrutide", "metformin", "insulin", "humalog", "novolog", "lantus", "tresiba", "levemir", "jardiance", "farxiga", "januvia", "phentermine", "contrave",
    "ocrevus", "kesimpta", "briumvi", "tysabri", "tecfidera", "vumerity", "copaxone", "aubagio", "gilenya", "mavenclad", "mayzent", "zeposia", "lemtrada", "rituximab",
    "humira", "adalimumab", "hyrimoz", "yuflyma", "remicade", "infliximab", "inflectra", "stelara", "skyrizi", "entyvio", "rinvoq", "xeljanz", "cimzia", "enbrel",
    "dupixent", "xolair", "cosentyx", "taltz", "tremfya", "omvoh", "otezla", "cibinqo", "olumiant", "benlysta", "nucala", "fasenra", "tezspire",
    "mesalamine", "lialda", "asacol", "pentasa", "budesonide", "azathioprine", "methotrexate", "plaquenil", "hydroxychloroquine", "prednisone", "prednisolone",
    "estradiol", "progesterone", "prometrium", "testosterone", "spironolactone", "spiro", "finasteride", "dutasteride", "minoxidil", "bicalutamide", "cyproterone",
    "letrozole", "anastrozole", "tamoxifen", "clomid", "clomiphene", "slynd", "yaz", "yasmin", "sprintec", "depo provera", "norethindrone", "dienogest", "visanne",
    "orilissa", "myfembree", "levothyroxine", "synthroid", "liothyronine", "cytomel", "hrt", "trt", "birth control",
    "eliquis", "apixaban", "xarelto", "rivaroxaban", "warfarin", "lisinopril", "losartan", "amlodipine", "metoprolol", "atenolol", "bisoprolol", "carvedilol",
    "ivabradine", "candesartan", "furosemide", "atorvastatin", "lipitor", "rosuvastatin", "crestor", "simvastatin", "midodrine", "fludrocortisone",
    "omeprazole", "prilosec", "pantoprazole", "protonix", "esomeprazole", "nexium", "famotidine", "pepcid", "sucralfate", "ondansetron", "zofran", "linzess",
    "zyrtec", "cetirizine", "claritin", "loratadine", "allegra", "fexofenadine", "xyzal", "ketotifen", "cromolyn", "montelukast", "singulair",
    "tramadol", "oxycodone", "percocet", "hydrocodone", "norco", "toradol", "celebrex", "meloxicam", "naproxen", "tizanidine", "cyclobenzaprine", "flexeril", "baclofen",
    "sumatriptan", "imitrex", "rizatriptan", "ubrelvy", "nurtec", "aimovig", "emgality", "ajovy", "qulipta",
    "suboxone", "subutex", "buprenorphine", "methadone", "naltrexone", "vivitrol", "antabuse", "sublocade",
    "accutane", "isotretinoin", "absorica", "tretinoin", "doxycycline", "minocycline", "truvada", "descovy", "biktarvy", "fluconazole", "valtrex", "valacyclovir",
    "allopurinol", "colchicine", "chantix", "varenicline", "reta", "foundayo", "orforglipron", "augmentin", "amoxicillin", "unisom", "paracetamol", "acetaminophen",
    "tylenol", "ibuprofen", "advil", "benadryl", "repatha", "irbesartan", "lactulose", "differin", "dayvigo", "nexplanon",
];
const DOSE: &str = r"\d*\.?\d+\s?(?:mg|mcg|ml|iu)\b";

static FRAME: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"(?:i(?<!\wi)(?:'m|m| am)(?: (?:currently|now|also|still|back|only|just|already|finally))* (?:on|taking|using|prescribed|medicated with)",
    r"|i(?<!\wi)(?: (?:currently|now|also|still|only|just|already|actually|do|regularly))* (?:take|use)",
    r"|i(?<!\wi)(?:'ve| have)(?: (?:also|now|just|only|recently|finally|currently))* been (?:on|taking|using|prescribed)",
    r"|i(?<!\wi)(?:'ve|ve| have)?(?: (?:just|recently|finally|also|then|eventually|originally))* (?:started(?: on| taking| with)?|switched (?:over )?(?:from [\w-]+(?: [\w-]+)? )?to|got put on|got prescribed|was put on|was prescribed)",
    r"|i(?<!\wi)(?:'m|m| am) (?:(?:almost|nearly|about|over|more than|just over|only|now|currently) )*(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|a few|a couple of|several) (?:days?|weeks?|months?|years?|yrs?) (?:in )?on",
    r"|i(?<!\wi)\b(?:(?!\b(?:who|that|which|anyone|someone|anybody|somebody|you|he|she|they|we|people|everyone)\b)[^.!?\n]){0,60}? and (?:then |also |eventually |finally |recently )?(?:started(?: on| taking)?|switched (?:over )?to|got put on|was put on)",
    r"|(?:p(?<!\wp)ut|s(?<!\ws)tarted|s(?<!\ws)witched|k(?<!\wk)ept|k(?<!\wk)eep|p(?<!\wp)rescribed) me (?:back )?(?:on|to)?",
    r"|m(?<!\wm)y (?:doctor|dr|psychiatrist|psych|gp|pcp|neurologist|dermatologist|derm|rheumatologist|endocrinologist|endo|obgyn|gyno|cardiologist|gastro|oncologist|np) (?:\w+ )?prescribed",
    r"|(?:^", claimcore::flair!(), r"|\n\s*|[.!?]\s+)(?:just |recently )?(?:started(?: on| taking)?|been on|been taking|currently on|currently taking)",
    r"|(?:^", claimcore::flair!(), r"|\n\s*|[.!?]\s+)(?:(?:almost|nearly|about|over|more than) )?(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten) (?:days?|weeks?|months?|years?) on)\b",
)));

static ITEM: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(
    r"\s*(?:(?:my|a|an|the|some|low[- ]dose|high[- ]dose|generic|daily|oral|compounded|injectable|liquid|rx)\s+|{DOSE}(?:\s+of)?\s+)*({})(?![\w-])(?:\s*{DOSE})?",
    longest_first(DRUGS.iter().copied())
)));

static PRIOR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:suggest(?:ed|s)?|recommend(?:ed|s)?|advised?|wanted|wants?|said|says|told me|asked|insist(?:ed|s)?|should|could|may|might|can|planning|plans?|offered|tried|refused|decided) (?:that |me |to )*\Z"));

static LINK: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:\([^()\n]{1,40}\)\s*)?(?:\s+for\s+(?:my\s+)?[\w/-]+(?=\s+(?:and|&|plus)\s))?(?:,\s*(?:and\s+|&\s+)?|\s+(?:and|&|plus)\s+|\s*[/+&]\s*)"));

pub fn init() {
    LazyLock::force(&FRAME);
    LazyLock::force(&ITEM);
    LazyLock::force(&LINK);
    LazyLock::force(&PRIOR);
}

pub fn medications(lowered: &[char], found: &mut Found) {
    for frame in FRAME.iter(lowered) {
        let mut at = frame.end();
        let mut items = Vec::new();
        while let Some(item) = ITEM.at(lowered, at) {
            at = item.end();
            items.push(item.g(1));
            match LINK.at(lowered, at) {
                Some(link) => at = link.end(),
                None => break,
            }
        }
        if items.is_empty() || quoted(lowered, frame.start()) || hedged(lowered, frame.start(), at, hedge()) || PRIOR.test_in(lowered, frame.start().saturating_sub(30), frame.start()) {
            continue;
        }
        for item in items {
            found.set("medications", item, frame.start());
        }
    }
}
