mod ailments;
mod habits;
mod medications;
mod vocab;

pub use ailments::ailments;

use claimcore::*;
use std::sync::LazyLock;
use vocab::*;

#[derive(Default, Clone, Copy)]
pub struct Fx(u64);

impl std::hash::Hasher for Fx {
    fn write(&mut self, bytes: &[u8]) {
        for &byte in bytes {
            self.write_u64(byte as u64);
        }
    }

    fn write_u32(&mut self, value: u32) {
        self.write_u64(value as u64);
    }

    fn write_usize(&mut self, value: usize) {
        self.write_u64(value as u64);
    }

    fn write_u64(&mut self, value: u64) {
        self.0 = (self.0.rotate_left(5) ^ value).wrapping_mul(0x51_7c_c1_b7_27_22_0a_95);
    }

    fn finish(&self) -> u64 {
        self.0
    }
}

pub type FxBuild = std::hash::BuildHasherDefault<Fx>;
pub type HashMap<K, V> = std::collections::HashMap<K, V, FxBuild>;
pub type HashSet<K> = std::collections::HashSet<K, FxBuild>;

pub type Key = Vec<char>;
pub type Lex = HashMap<Key, &'static str>;

#[derive(Clone, Default)]
pub struct Ordered {
    pub keys: Vec<String>,
    pub map: std::collections::HashMap<String, &'static str>,
}

impl Ordered {
    pub fn insert(&mut self, key: String, value: &'static str) {
        if self.map.insert(key.clone(), value).is_none() {
            self.keys.push(key);
        }
    }

    pub fn setdefault(&mut self, key: String, value: &'static str) {
        if !self.map.contains_key(&key) {
            self.map.insert(key.clone(), value);
            self.keys.push(key);
        }
    }

    pub fn has(&self, key: &str) -> bool {
        self.map.contains_key(key)
    }

    pub fn iter(&self) -> impl Iterator<Item = (&String, &'static str)> {
        self.keys.iter().map(move |key| (key, self.map[key]))
    }

    pub fn extend(&mut self, other: &Ordered) {
        for (key, value) in other.iter() {
            self.insert(key.clone(), value);
        }
    }

    pub fn with(&self, pairs: &[(&str, &'static str)]) -> Ordered {
        let mut out = self.clone();
        for (key, value) in pairs {
            out.insert(key.to_string(), value);
        }
        out
    }

    pub fn filter(&self, keep: impl Fn(&str, &str) -> bool) -> Ordered {
        let mut out = Ordered::default();
        for (key, value) in self.iter() {
            if keep(key, value) {
                out.insert(key.clone(), value);
            }
        }
        out
    }

    pub fn lex(&self) -> Lex {
        self.map.iter().map(|(key, value)| (key.chars().collect(), *value)).collect()
    }

    pub fn names(&self) -> String {
        names(self.keys.iter().map(|key| key.as_str()))
    }
}

pub const PHYSICAL_ATTRIBUTE: &str = "physical_conditions";

pub fn home(attribute: &'static str, value: &str) -> &'static str {
    match value {
        "blind / low vision" | "one eye / monocular" | "colorblind" | "nearsighted" | "farsighted" | "astigmatism" | "glaucoma" | "cataract" | "keratoconus" => "vision",
        "hiv positive" | "hsv-1" | "hsv-2" | "herpes / hsv (type unstated)" | "hpv" => "sexual_health_status",
        "perimenopause" | "menopause" | "post-menopause" | "surgical menopause" => "menopause_stage",
        _ => attribute,
    }
}

pub fn spread(groups: Groups) -> Ordered {
    let mut out = Ordered::default();
    for (value, items) in groups {
        for name in *items {
            out.insert(name.to_string(), value);
        }
    }
    out
}

fn pairs(items: &[(&str, &'static str)]) -> Ordered {
    let mut out = Ordered::default();
    for (key, value) in items {
        out.insert(key.to_string(), value);
    }
    out
}

pub fn py_escape(word: &str) -> String {
    let mut out = String::with_capacity(word.len() + 4);
    for c in word.chars() {
        if "()[]{}?*+-|^$\\.&~# \t\n\r\u{b}\u{c}".contains(c) {
            out.push('\\');
        }
        out.push(c);
    }
    out
}

pub fn names<'a>(words: impl IntoIterator<Item = &'a str>) -> String {
    let mut escaped: Vec<String> = words.into_iter().map(py_escape).collect();
    escaped.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then_with(|| a.cmp(b)));
    escaped.join("|")
}

pub fn inflected(table: &Ordered) -> Ordered {
    let mut grown = table.clone();
    for (name, value) in table.iter() {
        if name.starts_with("a ") || name.starts_with("an ") {
            grown.setdefault(name.split_once(' ').unwrap().1.to_string(), value);
        }
        let chars: Vec<char> = name.chars().collect();
        let size = chars.len();
        if size >= 5 && is_alpha(chars[size - 1]) && !["s", "x", "y", "sh", "ch"].iter().any(|end| name.ends_with(end)) {
            grown.setdefault(format!("{name}s"), value);
        } else if size >= 5 && name.ends_with('y') && !"aeiou".contains(chars[size - 2]) {
            grown.setdefault(format!("{}ies", &name[..name.len() - 1]), value);
        }
    }
    grown
}

pub struct Tables {
    pub physical: Ordered,
    pub physical_states: Ordered,
    pub physical_tools: Ordered,
    pub tool_strict: Ordered,
    pub mental: Ordered,
    pub mental_loose: Ordered,
    pub mental_states: Ordered,
    pub mental_state_strict: Ordered,
    pub mental_words: Ordered,
    pub feelings: Ordered,
    pub adhd_drugs: Ordered,
    pub foreign_mind_states: Ordered,
    pub foreign_mind_extra: Ordered,
    pub foreign_body_states: Ordered,
    pub mind_extra: Ordered,
}

pub static TABLES: LazyLock<Tables> = LazyLock::new(|| {
    let physical_tools = spread(PHYSICAL_TOOLS);
    let drop: HashSet<&str> = STRICT_DROP.iter().copied().collect();
    let tool_strict = physical_tools.filter(|name, value| !value.is_empty() && !drop.contains(name) && home(PHYSICAL_ATTRIBUTE, value) == PHYSICAL_ATTRIBUTE);
    let mental = spread(MENTAL);
    let loose: HashSet<&str> = LOOSE_EXCLUDE.iter().copied().collect();
    let mental_loose = mental.filter(|name, _| !loose.contains(name));
    let mental_states = spread(MENTAL_STATES);
    let strict: HashSet<&str> = STATE_STRICT_EXCLUDE.iter().copied().collect();
    let mental_state_strict = mental_states.filter(|name, _| !strict.contains(name));
    let mental_words = mental.filter(|name, _| !["did", "add", "odd", "bed", "ed"].contains(&name));
    let drugs: &'static str = Box::leak(data_file("adhd_drugs.txt").into_boxed_str());
    let mut adhd_drugs = Ordered::default();
    for line in drugs.lines().filter(|line| !["bupropion", "clonidine", "modafinil"].contains(line)) {
        adhd_drugs.insert(line.to_string(), "adhd");
    }
    Tables {
        physical: spread(PHYSICAL),
        physical_states: spread(PHYSICAL_STATES),
        physical_tools,
        tool_strict,
        mental,
        mental_loose,
        mental_states,
        mental_state_strict,
        mental_words,
        feelings: pairs(&[("depressed", "depression")]),
        adhd_drugs,
        foreign_mind_states: spread(FOREIGN_MIND_STATES),
        foreign_mind_extra: spread(FOREIGN_MIND_EXTRA),
        foreign_body_states: spread(FOREIGN_BODY_STATES),
        mind_extra: spread(MIND_EXTRA),
    }
});

pub const PEOPLE: &str = concat!(
    r"mom|mother|mum|mommy|dad|father|daddy|wife|husband|son|daughter|kid|kids|child|children|baby|toddler|friend|friends|bestie|brother|sister|sibling|siblings|grandma|grandpa|",
    r"grandmother|grandfather|granny|nana|aunt|auntie|uncle|cousin|niece|nephew|boyfriend|girlfriend|bf|gf|partner|spouse|fiance|fiancee|fiancé|ex|roommate|coworker|boss|",
    r"he|she|his|her|him|they|their|them|dog|cat|puppy|kitten|pet|patient|client|patients|clients|student|students|parent|parents|family|people|everyone|nobody|someone's|",
    r"guy|girl|lady|man|woman|men|women|teacher|doctor|neighbor|neighbour|grandson|granddaughter|stepdad|stepmom|in-law|sil|bil|mil|fil|dh|dw|ds|dd|op|op's|u|you|your|you're|ur"
);

pub static OWN_HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(
    "{}{}",
    SELF_HEDGE.pattern,
    r"|\b(?:suspect|suspected|probably|possibly|wonder|wondering|could be|could have|do i have|self[- ]diagnosed|test(?:ed)? for|screen(?:ed)? for|assess(?:ed|ment)? for|evaluat(?:ed|ion) for|referr(?:al|ed) for|wait(?:ing)? ?list(?:ed)? for|rule out|ruled out|i think|i thought|i guess|think|thinking|thought|i feel like|pretty sure|i believe|scared|afraid|worried|terrified)\b"
)));
pub static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"{}|\b(?:{PEOPLE})\b", OWN_HEDGE.pattern)));
static FOREIGN_SELF_HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(
    "{}{}{}",
    SELF_HEDGE.pattern,
    r"|(?<![\w'])(?:no|nunca|jamás|ni|si|creo|quizá|quizás|tal vez|ojalá|não|nao|nem|se|acho|talvez|ne|n'|pas|jamais|nicht|kein|keine|nie|niemals|wenn|falls|ob|",
    r"vielleicht|non|mai|forse|niet|geen|nooit|misschien|jeśli|może|chyba)(?![\w'])"
)));
pub static MENTAL_TAIL: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{})$", TABLES.mental.names())));
static FIGURATIVE: LazyLock<Re> = LazyLock::new(|| Re::new(r"[^\n]*?(?:\b(?:lol|lmao|lmfao|rofl|xd|haha\w*|hehe\w*|clearly|apparently|i guess|i suppose|didn'?t see|did not see|didn'?t notice|missed (?:it|that|this|those|them))\b|[😅😂🤣🙈🤦])"));
pub static INTENSIFIED: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:so|really|very|pretty|super|kinda|kind of|a bit|a little|bit|too|extremely)\s+$"));
static FLAIR_HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:suspect\w*|undiagnosed|self[- ]?(?:dx|diagnosed)|possibl\w*|probabl\w*|maybe|questioning|not)\W+(?:[\w-]+\W+)?$"));
static PROXY_SUB: LazyLock<Re> = LazyLock::new(|| Re::new(r"^r/\w*(?:parent|mom|(?<!i)dad|widow|caregiv|carer|grief|loss)\w*:"));
static SEEKING: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:no|not|non|looking for|seeking|want|wants|wanted|for|with|into|love|loves|like|likes)\W+(?:[\w'-]+\W+)?$"));
static SUBSTANCE: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:(drink|drinks|drinking|drank|drunk|alcohol|alcoholic|alcoholism|booze|beer|beers|wine|liquor|vodka|whiskey|whisky|hangovers?|aa|stopdrinking)|(weed|cannabis|marijuana|thc|stoner|edibles|dabs)|",
    r"(heroin|opiates?|opioids?|fentanyl|fent|oxy|oxycodone|percs|percocets?|kratom|methadone|suboxone)|(meth|cocaine|adderall|amphetamines?|stimulants?)|(benzos?|xanax|klonopin|valium|ativan)|(gambling|gamble|gambler|betting)|(porn|nofap|fap|masturbation))\b"
)));
static BEHAVIOUR: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:gaming|video ?games?|c\.ai|character\.?ai|chatbots?|ai chats?|social media|tiktok|instagram|spotify|screen time)\b"));
const SENSES: &str = r"i(?<!\wi)(?:'?m| am|'ve gone| have gone|'m going| am going)(?: (?:also|now|already|still|basically|practically|essentially|technically))* (?:legally |completely |totally |profoundly |partially |mostly )?(deaf|blind|hard of hearing)\b|i(?<!\wi) (?:lost|had lost) (?:my |most of my |all of my |part of my )(?:\w+ )?(sight|vision|hearing)\b(?! (?:board|for|of)\b)";

pub const SUBJECT: &str = r"i(?<!\wi) (?:also |still |do |actually |now |already |too |even |definitely |literally |personally |unfortunately |both |currently |recently |just |really |apparently |obviously |basically |technically |myself |officially |finally |eventually |later |since |unfortunately also )*";

pub fn have_now() -> String {
    [
        SUBJECT,
        r"(?:have|got|get|suffer from|suffer with|struggle with|deal with|live with|battle|fight|manage|was born with|developed|contracted|have been (?:diagnosed|dx'?d?) with|got (?:diagnosed|dx'?d?) with|",
        r"was (?:also |recently |officially |formally |finally |just |eventually |later |then |initially |first |since )?(?:diagnosed|dx'?d?) with|have had|have got|am (?:diagnosed|dx'?d?) with|am being treated for|",
        r"am recovering from|am dealing with|am struggling with|am living with|am suffering from|am suffering with|am battling|am fighting)",
        r"|i(?<!\wi)(?:'ve|ve| have) (?:also |always |recently |just |finally |officially |since |now |personally |actually |unfortunately |literally |basically |definitely |still |apparently |technically |long )*(?:had|got|been (?:diagnosed|dx'?d?) with|been dealing with|been struggling with|been battling|been fighting|been living with|",
        r"been suffering from|been suffering with|been treated for|been recovering from|developed|struggled with|dealt with|suffered from|suffered with|lived with|battled|fought|survived|beaten)",
        r"|i(?<!\wi)(?:'m|m| am) (?:also |currently |still |now |actually |officially |finally |recently |just |newly |personally |technically |literally |basically |definitely |unfortunately |apparently )*(?:(?:diagnosed|dx'?d?) with|dealing with|struggling with|living with|suffering from|suffering with|being treated for|recovering from|",
        r"battling|fighting|on meds for|on medication for|in treatment for|in remission from|getting treated for|managing|medicated for|surviving|a survivor of)",
        r"|i(?<!\wi) (?:take|took|need|use|used) (?:meds|medication|medications|medicine|pills|something|treatment|a prescription|an rx) for|(?:a(?<!\wa)s |i(?<!\wi)(?:'m |m | am ))(?:someone|(?:an? )(?:[\w-]+ ){0,2}?(?:person|guy|girl|woman|man|adult|lady|female|male|mom|mum|dad|mother|father|wife|husband|teen|kid|student|individual|dude|gal|patient)) (?:who(?:'s| has| is)? (?:also |still |too )?(?:has|has had|had|suffers from|suffers with|struggles with|lives with|deals with|been diagnosed with|diagnosed with|dealt with|struggled with|lived with|suffered from|suffered with)|(?:also |still )?(?:living with|with))",
        r"|m(?<!\wm)y (?:diagnosis|diagnoses|dx|dxs) (?:is|are|of|was|were|include|includes)\b|d(?<!\wd)iagnosed me (?:with|as)",
        r"|(?<![\w.=<>~+%$#/-])(?<!bmi )(?<!over )(?<!under )(?:i'?m |i am )?(?:1[3-9]|[2-9]\d) ?(?:[mf]|yo|y/o|years? old)?\)?,? (?:with|w/)",
    ]
    .concat()
}

pub fn had() -> String {
    format!("{SUBJECT}{}", r"(?:had|suffered from|struggled with|dealt with|lived with|battled|fought|beat|survived|overcame|was treated for|was dealing with|went through|got treated for)")
}

pub fn have() -> String {
    format!("{}|{}", have_now(), had())
}

pub const BARE: &str = concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n|]\s*)(?:recently |newly |just |finally |officially |formally |also |and |got |was |been )*(?:diagnosed|dx'?d) (?:with|w/)");
pub const MODIFIERS: &str = concat!(
    r"own|severe|mild|moderate|chronic|acute|stupid|damn|damned|fucking|freaking|bloody|bad|untreated|undiagnosed|diagnosed|recent|current|constant|occasional|lifelong|genetic|congenital|",
    r"hereditary|early|late|new|old|primary|secondary|crippling|debilitating|terrible|horrible|awful|pretty bad|really bad|annoying|lovely|wonderful|recurring|recurrent|persistent|ongoing|",
    r"rare|treatment[- ]resistant|clinical|major|severe chronic|medicated|unmedicated|managed|controlled|uncontrolled|diet[- ]controlled|stage \w+|grade \w+|type \w+|level \w+|chronic severe|",
    r"intermittent|episodic|silent|mild case of|bit of|bit of an?|little|minor|slight|full blown|full-blown|high[- ]functioning|combined[- ]type|inattentive[- ]type|hyperactive[- ]type|",
    r"inattentive|combined|hyperactive|textbook|diagnosed severe|late[- ]diagnosed|recently diagnosed|adult|childhood|postpartum|seasonal|crazy|insane|massive|huge|lingering|residual|newly diagnosed|",
    r"some|a lot of|lots of|serious|really|very|super|extreme|extremely|both|mostly|mainly|also"
);
pub const FOLLOWERS: &str = r"(?! (?:friend|friends|kid|kids|son|daughter|brother|sister|partner|husband|wife|mom|dad|mother|father|mum|parent|parents|sibling|ex|boyfriend|girlfriend|bf|gf|fiance|fiancee|fiancé|spouse|roommate|coworker|boss|neighbor|neighbour|cousin|aunt|uncle|grandma|grandpa|grandmother|grandfather|niece|nephew|stepdad|stepmom|patient|patients|client|clients|community|people|person|research|awareness|month|day|walk|charity|foundation|society|association|group|subreddit|sub|forum)s?\b)";

pub fn gap() -> String {
    format!(r"(?:(?!(?:{PEOPLE}|not|no|never|neither|nor|without|and|but|or|if|when|because|so|that|who|which|what|where|than|to)\b)[\w'/-]+,?\s+){{0,3}}?")
}

pub fn modifier() -> String {
    format!(r"(?:(?:{MODIFIERS})[\s,]+){{0,3}}")
}

const FOREIGN_AM: &str = r"(?:soy|sou|je suis|ich bin|sono|jestem|ik ben|tengo|tenho|j'ai|ich habe|ho|mam|ik heb|con|com|avec|mit)\s+(?:(?:un|una|um|uma|une|ein|eine|einen|un'|een|tambien|también|também|aussi|auch|anche|też|ook|le|la|de|del|du)\s+|l')*";
const FOREIGN_IS: &str = r"(?:soy|sou|je suis|ich bin|sono|jestem|ik ben)\s+(?:(?:un|una|um|uma|une|ein|eine|un'|een|tambien|también|também|aussi|auch|anche|też|ook)\s+)*";
const FOREIGN_PERSON: &str = concat!(
    r"(?:(?:hombre|mujer|chico|chica|persona|tipo|homem|mulher|cara|rapaz|menina|menino|garota|pessoa|homme|femme|mec|fille|gars|personne|mann|frau|typ|uomo|donna|ragazzo|ragazza|",
    r"vrouw|jongen|meisje|persoon|facet|kobieta|osoba)\s+)?"
);
const BOT_SELF: &str = concat!(
    r"(?:\bi(?:'m| am)[\s^]+a[\s^]+bot\b|\bthis is a bot\b|\bperformed[\s^]+automatically\b|\bsou um bot\b|\bsoy un bot\b|\bbeep boop\b|\bbleep bloop\b|",
    r"\bthis is an? (?:automated|automatic) (?:message|response|reply|comment|process)\b|\bthis message is an automat\w+ response\b)"
);
const BOT_OWN: &str = concat!(
    r"(?:\bi[\s^]*(?:'m|[\s^]am)[\s^]+an?[\s^]+\[?bot\b(?![\s^]*,?[\s^]*and[\s^]+this[\s^]+action[\s^]+was[\s^]+performed)|\bthis is a bot\b|\bsou um bot\b|\bsoy un bot\b|\bbeep boop\b|\bbleep bloop\b|",
    r"\bthis is an? (?:automated|automatic) (?:message|response|reply|comment|process)\b|\bthis message is an automat\w+ response\b)"
);
const BOT_WORDS: [&str; 6] = [" bot", "^bot", "[bot", "beep boop", "bleep bloop", "automat"];
const MODERATION: &str = r"removed|remove|approv\w*|karma|locked|not allowed|bans?|bannable|banned|comments are disabled|filtered|blocked|block you|copy of (?:the|this|your) (?:original )?(?:post|submission)|post's original text|copia del post|salvo qui una copia";
const PERSONAL_AD: &str = r"[\[(]\s*(?:nb|[mf])[mf]?\s*4\s*(?:[mfatr]|me|nb)\w*\s*[\])][^\n]*?(?<![\w'-])({})(?![\w'-])";
pub const NEURO: [&str; 3] = ["adhd", "autism", "audhd"];

pub fn quoted(text: &[char], start: usize) -> bool {
    let line = &text[line_start(text, start)..start];
    let straight = line.iter().filter(|&&c| c == '"').count();
    straight % 2 == 1 || line.iter().filter(|&&c| c == '\u{201c}').count() > line.iter().filter(|&&c| c == '\u{201d}').count()
}

fn get(lex: &Lex, part: Option<&[char]>) -> Option<String> {
    part.and_then(|key| lex.get(key)).filter(|value| !value.is_empty()).map(|value| value.to_string())
}

fn sense(sight: bool) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| {
        let word: String = m.first()?.iter().collect();
        let seen = matches!(word.as_str(), "blind" | "sight" | "vision");
        if seen != sight || FIGURATIVE.at(m.string, m.end()).is_some() {
            return None;
        }
        Some(if sight { "blind / low vision" } else { "deaf / hard of hearing" }.to_string())
    }
}

fn number(word: &str) -> Option<f64> {
    let words = ["a", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];
    match words.iter().position(|known| *known == word) {
        Some(index) => Some(index as f64 + 1.0),
        None if word == "one" => Some(1.0),
        None => word.parse().ok(),
    }
}

pub fn sober_from(text: &[char]) -> Option<String> {
    let values = ["alcohol", "cannabis", "opioids", "stimulants", "benzodiazepines", "gambling", "porn / sex"];
    let mut named: Vec<&str> = SUBSTANCE.iter(text).filter_map(|m| (1..=values.len()).find(|&g| m.has(g)).map(|g| values[g - 1])).collect();
    named.sort();
    named.dedup();
    if named.len() == 1 { Some(named[0].to_string()) } else { None }
}

fn sober_days(m: &Match) -> Option<String> {
    let said = &m.string[last_mark(m.string, m.start(), ".!?\n")..next_mark(m.string, m.end(), ".!?\n")];
    if BEHAVIOUR.test(said) && !SUBSTANCE.test(said) {
        return None;
    }
    let count = number(&m.gs(1)?)?;
    let unit = m.gs(2)?;
    let days = match unit.trim_end_matches('s') {
        "day" => 1.0,
        "week" => 7.0,
        "month" => 30.44,
        _ => 365.25,
    };
    Some(format!("{}", (count * days).round() as i64))
}

const ALLERGENS: &[(&str, &str)] = &[
    ("peanut", "peanuts"), ("tree", "tree nuts"), ("nut", "tree nuts"), ("almond", "tree nuts"), ("cashew", "tree nuts"), ("walnut", "tree nuts"), ("shellfish", "shellfish"), ("shrimp", "shellfish"),
    ("egg", "eggs"), ("dairy", "dairy"), ("milk", "dairy"), ("gluten", "gluten / wheat"), ("wheat", "gluten / wheat"), ("soy", "soy"), ("fish", "fish"), ("sesame", "sesame"),
    ("cat", "cats"), ("dog", "dogs"), ("seasonal", "pollen / hay fever"), ("hay", "pollen / hay fever"), ("pollen", "pollen / hay fever"), ("grass", "pollen / hay fever"),
    ("ragweed", "pollen / hay fever"), ("birch", "pollen / hay fever"), ("dust", "dust / dust mites"), ("mold", "mold"), ("mould", "mold"), ("latex", "latex"),
    ("penicillin", "penicillin / antibiotics"), ("amoxicillin", "penicillin / antibiotics"), ("sulfa", "penicillin / antibiotics"), ("antibiotic", "penicillin / antibiotics"),
    ("nsaid", "nsaids"), ("ibuprofen", "nsaids"), ("aspirin", "nsaids"), ("bee", "bees / wasps"), ("wasp", "bees / wasps"), ("no", "no allergies"),
];

fn allergen(word: Option<&[char]>) -> Option<String> {
    let word: String = word?.iter().collect();
    ALLERGENS.iter().find(|(key, _)| word.starts_with(key)).map(|(_, value)| value.to_string())
}

fn recovered(m: &Match) -> Option<String> {
    let text: String = m.first()?.iter().collect();
    if text == "sober" {
        return sober_from(m.string);
    }
    let value = if text.contains("porn") || text.contains("sex") {
        "porn / sex"
    } else if text.contains("gambl") {
        "gambling"
    } else if ["heroin", "opiate", "opioid", "fentanyl", "oxy", "dope"].iter().any(|word| text.contains(word)) {
        "opioids"
    } else if ["meth", "cocaine", "coke", "crack", "adderall", "speed", "stimulant"].iter().any(|word| text.contains(word)) {
        "stimulants"
    } else if ["benzo", "xanax", "klonopin", "valium", "ativan"].iter().any(|word| text.contains(word)) {
        "benzodiazepines"
    } else if ["alcohol", "booze", "drink"].iter().any(|word| text.contains(word)) {
        "alcohol"
    } else {
        return None;
    };
    Some(value.to_string())
}

fn by(table: Ordered) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    let lex = table.lex();
    move |m| get(&lex, m.group(1))
}

fn leading(table: &Ordered) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    let lex = table.lex();
    move |m| {
        let start = m.start();
        if start > 0 {
            let c = m.string[start - 1];
            if is_alnum(c) || c == '\'' || c == '_' {
                return None;
            }
        }
        get(&lex, m.group(1))
    }
}

fn flair(lex: Lex) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| {
        let start = m.start_of(1) as usize;
        if !starts_at(m.string, 0, "r/") || FLAIR_HEDGE.test_in(m.string, start.saturating_sub(30), start) || PROXY_SUB.test_in(m.string, 0, line_end(m.string, 0)) {
            return None;
        }
        get(&lex, m.group(1))
    }
}

fn unquoted(attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static, hedge: Hedge) -> Rule {
    rule(attribute, pattern, move |m| if quoted(m.string, m.start()) { None } else { value(m) }, hedge)
}

fn own() -> Hedge {
    Some(&*OWN_HEDGE)
}

fn others() -> Hedge {
    Some(&*OTHERS)
}

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    let t = &*TABLES;
    let tool_names = t.tool_strict.names();
    let tool_strict = t.tool_strict.clone();
    let tool_lex = tool_strict.lex();
    let exclude: HashSet<&str> = TOOL_RULE_EXCLUDE.iter().copied().collect();
    let tool_rule_names = names(t.tool_strict.keys.iter().map(|k| k.as_str()).filter(|k| !exclude.contains(k)));
    let loose = t.mental_loose.names();
    let have = have();
    let gap = gap();
    let modifier = modifier();
    let mut feeling_states = t.mental_state_strict.clone();
    feeling_states.extend(&t.feelings);
    let mut loose_states = t.mental_loose.clone();
    loose_states.extend(&t.mental_state_strict);
    let feeling_lex = feeling_states.lex();
    let foreign_body = t.foreign_body_states.filter(|_, value| home(PHYSICAL_ATTRIBUTE, value) == PHYSICAL_ATTRIBUTE);
    let mut rules = vec![
        unquoted("physical_conditions", &format!(
            r"m(?<!\wm)y (?:own |new |old |daily |current |rescue |emergency |stupid |damn |trusty |first |second |last |next |latest |recent |regular |usual |monthly |weekly |yearly |annual |(?!(?:{PEOPLE})(?:'s|s)? )\w+ (?:and )?)?({tool_names})\b(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad|resistance|resistant|sensitivity|level)s?\b)"
        ), move |m| {
            if let Some(mental) = MENTAL_TAIL.search(m.string, m.start(), m.end()) {
                if (mental.start() as isize) < m.start_of(1) {
                    return None;
                }
            }
            get(&tool_lex, m.group(1))
        }, own()),
        unquoted("physical_conditions", &format!(
            r"i(?<!\wi)(?: (?:also |still |now |have to |had to |need to |always |usually |currently |sometimes |must )?(?:wear|need|use|carry|have|got|take|took|started|start|am on|was on|was put on|got put on|was prescribed|got prescribed|inject|do|did|go to|see|saw|visit)|'m (?:also |still |now |currently )?(?:on|taking|using)|'ve (?:been on|been taking|been using|started)) (?:a |an |my |the |two |both |prescription |daily )?({tool_rule_names})\b"
        ), by(tool_strict), own()),
        unquoted("physical_conditions", SENSES, sense(false), self_hedge()),
        unquoted("vision", SENSES, sense(true), self_hedge()),
        unquoted("physical_conditions",
            r"i(?<!\wi)(?:(?:'?m| am|'ve been| have been)(?: (?:also|still|currently|now|basically|literally|just|pretty much))*(?: (?:always|often|constantly|permanently|chronically|perpetually|frequently|usually|almost always) in(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|much|constant|chronic|daily))*| in(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|much))* (?:constant|chronic|daily|ongoing|almost constant|nearly constant|perpetual|permanent|never[- ]?ending|endless|everyday|lifelong|persistent)(?: (?:severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating))*)| live(?: (?:always|constantly|daily))? (?:in|with)(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|constant|chronic|daily|ongoing))*) pain\b(?! (?:management|clinic|meds|medications?|killers?|relief|pills?|doctors?|specialists?)\b)",
            fixed("chronic pain / crps"), self_hedge()),
        unquoted("mental_and_developmental_conditions", &format!(r"(?:{have})\s+{modifier}(?:an? )?{gap}({loose})\b{FOLLOWERS}"), by(t.mental_loose.clone()), own()),
        unquoted("mental_and_developmental_conditions", &format!(r"{BARE}\s+{modifier}(?:an? )?{gap}({loose})\b{FOLLOWERS}"), by(t.mental_loose.clone()), others()),
        unquoted("mental_and_developmental_conditions", r"a(?<!\wa)s an? (suicidal|depressed|anxious)\b",
            by(pairs(&[("suicidal", "suicidality"), ("depressed", "depression"), ("anxious", "anxiety")])), self_hedge()),
        unquoted("mental_and_developmental_conditions",
            r"i(?<!\wi)(?:'m|m| am)(?: (?:also|just|still))? (?:constantly|always|chronically|perpetually|naturally) anxious\b|i(?<!\wi)(?:'ve| have) always been (?:very |really |super |so |an )?anxious\b(?! (?:about|to|for|that|when|around)\b)",
            fixed("anxiety"), own()),
        unquoted("mental_and_developmental_conditions", r"i(?<!\wi)(?:'m|m| am)(?: also| diagnosed)? (?:bp ?(?:1|2|i|ii)|bipolar (?:1|2|i|ii))\b", fixed("bipolar"), own()),
        unquoted("mental_and_developmental_conditions",
            r"(?:i(?<!\wi)(?: have|'ve had| was diagnosed with| got diagnosed with|'ve been diagnosed with|'m diagnosed with|'m on meds for| take meds for| was recently diagnosed with| also have| do have| have had)|d(?<!\wd)iagnosed with) (?:(?:severe|mild|moderate|chronic|clinical|diagnosed|combined[- ]type|inattentive[- ]type|bad|really bad|pretty bad|terrible|untreated|unmedicated|adult|both|some|serious) )*(add|did|osdd|tics|pmdd|panic attacks|anxiety attacks|binge eating|suicidal thoughts|suicidal ideation)(?![\w'-])",
            by(t.mental.with(&[("add", "adhd")])), own()),
        unquoted("mental_and_developmental_conditions", &format!(r"m(?<!\wm)y {modifier}({loose})\b{FOLLOWERS}(?! (?:medication|meds)\b)"), by(t.mental_loose.clone()), own()),
        unquoted("mental_and_developmental_conditions",
            r"m(?<!\wm)y (?:(?:own|official|formal|first|recent|new|adult|actual|initial|late) )*(adhd|autism|audhd|ocd|bpd|ptsd|cptsd|anxiety|depression|bipolar|eating disorder|tics|did) (?:brain|meds|medication|diagnosis|symptoms|is|was|has|makes|gets|kicks|flares|got|took|and|so)\b",
            by(t.mental.clone()), own()),
        unquoted("mental_and_developmental_conditions", &format!(
            r"(?:a(?<!\wa)s(?: an?| a fellow| someone who is| a person who is| somebody with| a person with| someone with| one with)|b(?<!\wb)eing an?|m(?<!\wm)e, an?) (?:fellow |diagnosed |late[- ]diagnosed |recovering |recovered |formerly )?({loose}|{}) ?(?:person|woman|man|adult|guy|girl|individual|sufferer|patient|survivor|haver|myself|lady|dude|mom|dad|mother|father|parent|teen|kid|student|female|male|human|being)?\b",
            t.mental_state_strict.names()
        ), by(loose_states.clone()), self_hedge()),
        unquoted("mental_and_developmental_conditions", &format!(
            r"i(?<!\wi)(?:'m|m| am| m|'ve been|ve been| have been| was| became|'m now|'m also|'m actually) (?:also |now |currently |technically |actually |literally |officially |still |pretty |very |so |really |too |super |just |severely |extremely |mildly |pretty much |basically |definitely |diagnosed |clinically |formally |medically |probably not |a diagnosed |a |an |self[- ]diagnosed |late[- ]diagnosed )*({})\b(?! (?:people|person|friend|friends|community|rights|folks|kids?|son|daughter|family|patients?|to (?:the|this|that|your|my|his|her|their|it|them|what|how|whether|any)|about|of|for(?! (?:a long time|a while|years|months|weeks|ages|decades|so long|most of my life|over|almost|nearly|the (?:past|last)|\d+))|from|by|over|with)\b)",
            feeling_states.names()
        ), move |m| if feeling_lex.get(m.group(1)?) == Some(&"ocd") && INTENSIFIED.test(&m.string[m.start()..m.start_of(1) as usize]) { None } else { get(&feeling_lex, m.group(1)) }, own()),
        unquoted("mental_and_developmental_conditions", &format!(
            r"(?:m(?<!\wm)y|i(?<!\wi)(?: take|'m on| am on|'ve been on| started|'m taking| am taking|'ve been taking| was put on| got put on| was prescribed| got prescribed| was given| switched to| take my| forgot my| forgot to take my| ran out of|'m out of)|p(?<!\wp)(?:rescribed me|ut me on)|g(?<!\wg)ave me|s(?<!\ws)witched me to) (?:\w+ )?(?:\d+\s?mg (?:of )?)?({})\b",
            t.adhd_drugs.names()
        ), by(t.adhd_drugs.clone()), self_hedge()),
        unquoted("mental_and_developmental_conditions", &format!(r"\b(audhd|au/dhd)\b{FOLLOWERS}"), |m| if starts_at(m.string, 0, "r/") { Some("audhd".to_string()) } else { None }, others()),
        unquoted("mental_and_developmental_conditions",
            r"\b(adhd|autism|audhd|asd|ocd|ptsd|cptsd|bpd|anxiety|depression|bipolar) (?:brain|makes my|affects my|ruins my|means i|makes me|makes it|has made my|messes with my|fucks with my|controls my|took over my|runs my|got the better of me)\b",
            by(t.mental.clone()), self_hedge()),
    ];
    for pattern in [
        format!(r"(?:r(?<!\wr)ecover(?:ing|ed)|i(?<!\wi)n recovery) from (?:my |an? )?({loose})\b"),
        format!(r"(?:u(?<!\wu)n(?:diagnosed|medicated|treated)|d(?<!\wd)iagnosed|c(?<!\wc)rippling|l(?<!\wl)(?:ifelong|ate[- ]diagnosed)) (?:but severe )?({loose})\b(?=[^.!?\n]*\b(?:i|my|me)\b)"),
        format!(r"^{flair}\W*(?:yep\W+|yeah\W+|also\W+|same\W+|me too\W+)?({loose})\W*$", flair = claimcore::flair!()),
        format!(r"(?:^|[.!?\n]\s*)also,? ({loose})\b(?=\W*(?:$|[.!?\n]))"),
    ] {
        let lex = t.mental_loose.lex();
        rules.push(unquoted("mental_and_developmental_conditions", &pattern, move |m| if PROXY_SUB.test(m.string) { None } else { get(&lex, m.group(1)) }, own()));
    }
    let caused = pairs(&[("depressed", "depression"), ("suicidal", "suicidality"), ("depression", "depression"),
        ("an eating disorder", "eating disorder (unspecified)"), ("agoraphobic", "anxiety")]).lex();
    rules.extend([
        unquoted("mental_and_developmental_conditions",
            r"(?:m(?<!\wm)a(?:de|kes|king)|l(?<!\wl)e(?:ft|aving)|g(?<!\wg)ave) me (?:really |so |very |super |severely |clinically |chronically )?(depressed|suicidal|depression|an eating disorder|agoraphobic)\b(?= *(?:$|[.!\n,;]|and\b|af\b|asf\b|for (?:years|months|a long time)))",
            move |m| get(&caused, m.first()), own()),
        unquoted("mental_and_developmental_conditions",
            r"f(?<!\wf)or my (adhd|autism|anxiety|depression|ocd|ptsd|cptsd|bipolar|bpd|panic attacks|panic disorder|social anxiety|mdd|gad|eating disorder)\b",
            by(t.mental.clone()), own()),
        unquoted("mental_and_developmental_conditions",
            r"i(?<!\wi) (?:was|got) (?:\w+ )?(?:hospitalized|hospitalised|admitted|committed|sectioned|baker acted|5150'?d|put on a 5150|put in a psych ward|in a psych ward|in the psych ward|inpatient) (?:for|after|because of) (?:my |an? )?(depression|suicidal thoughts|a suicide attempt|suicide attempt|mania|a manic episode|an eating disorder|anorexia)\b",
            by(pairs(&[("depression", "depression"), ("suicidal thoughts", "suicidality"), ("a suicide attempt", "suicidality"), ("suicide attempt", "suicidality"), ("mania", "bipolar"),
                ("a manic episode", "bipolar"), ("an eating disorder", "eating disorder (unspecified)"), ("anorexia", "anorexia")])), own()),
        unquoted("recovering_from",
            r"i(?<!\wi)(?:'m|m| am|'ve been| have been)(?: now| officially| currently| finally)? (?:over |almost |nearly |about )?(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a few|several|many) (?:days?|weeks?|months?|years?|yrs?) (sober|alcohol[- ]free|off (?:alcohol|booze|the booze|the drink|drinking)|(?:clean|off) (?:from |of )?(?:heroin|opiates|opioids|fentanyl|oxy|meth|cocaine|coke|crack|adderall|benzos|xanax|klonopin)|porn[- ]?free|gambling[- ]free|gamble[- ]free)\b",
            recovered, self_hedge()),
        unquoted("recovering_from",
            r"(?:i(?<!\wi)(?:'m| am)(?: also| now| still)?|a(?<!\wa)s) an? ((?:recovering|recovered|sober|former|ex-?) ?(?:alcoholic|heroin addict|opiate addict|opioid addict|fentanyl addict|gambling addict|gambler|porn addict|sex addict|meth addict|cocaine addict|crack addict|benzo addict)|(?:alcoholic|heroin addict|opiate addict|opioid addict|meth addict) in recovery)\b|i(?<!\wi)(?:'ve| have)(?: now| officially| finally| also| just)? been (sober) (?:for|since|over|almost|nearly|about|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b|i(?<!\wi)(?:'m| am) (?:now |currently )?(?:in recovery|recovering) from (alcoholism|alcohol addiction|alcohol use disorder|opioid addiction|opiate addiction|heroin addiction|fentanyl addiction|gambling addiction|porn addiction|sex addiction|meth addiction|cocaine addiction|benzo addiction)\b|i(?<!\wi)(?:'ve| have)? (?:(?:finally|officially|just|also|recently|completely|since) )?(?:quit|stopped|gave up|given up) (drinking|alcohol|booze|the booze|the drink)\b(?! (?:like|soft|ice|iced|fizzy|soda|coffee|pop|energy|milk|juice|tea|water|caffeine|diet|coke|pepsi|monster|red bull|sugary|sweet|sugar|caffeinated|out|from|it|that|this|them|so much|as much|for(?! good\b))\b)",
            recovered, self_hedge()),
        unquoted("recovering_from",
            r"i(?<!\wi)(?:'m| am|'ve been| have been| got| was)(?: (?:now|also|still|finally|officially|completely))? (?:sober|clean) (?:from|off) (?:of )?(?:my )?(alcohol|drinking|heavy drinking|booze|benzos|xanax|meth|cocaine|heroin|opiates|gambling|porn)\b|\b(?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten) (?:days?|weeks?|months?|years?) (?:sober|clean) (?:from|off) (?:of )?(alcohol|drinking|booze|benzos)\b",
            recovered, self_hedge()),
        unquoted("sober_time",
            r"i(?<!\wi)(?:'m|m| am|'ve been| have been)(?: now| officially| currently| finally)? (?:over |almost |nearly |about )?(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a) (days?|weeks?|months?|years?|yrs?) (?:sober|clean)\b",
            sober_days, self_hedge()),
        unquoted("sober_time",
            r"i(?<!\wi)(?:'ve| have)(?: now| officially| finally| also| just)? been (?:sober|clean) (?:for )?(?:over |almost |nearly |about )?(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a) (days?|weeks?|months?|years?|yrs?)\b",
            sober_days, self_hedge()),
        unquoted("mental_and_developmental_conditions",
            r"i(?<!\wi)(?:'m|m| am)(?: also| currently| still| now| back)? on (?:my |prescription |prescribed |stimulant )?(?:adhd|add) (?:meds|medications?|medicine|stimulants)\b|i(?<!\wi)(?:'m| am)? (?:take|took|started|need|taking|started taking|stopped taking) (?:my )?(?:adhd|add) (?:meds|medications?|medicine)\b",
            fixed("adhd"), own()),
        unquoted("mental_and_developmental_conditions",
            r"m(?<!\wm)y (?:own )?(autistic|neurodivergent|adhd|audhd|dyslexic) (?:ass|self|brain|mind|side|butt|tendencies|traits|quirks|desire|desires|obsession|obsessions|experience|nature|needs|meltdowns?|hyperfixations?|hyperfocus|special interests?|stims?|stimming|logic|ways|moments?|struggles|symptoms|issues|habits)\b",
            by(pairs(&[("autistic", "autism"), ("neurodivergent", "neurodivergent (unspecified)"), ("adhd", "adhd"), ("audhd", "audhd"), ("dyslexic", "dyslexia / learning disorder")])), own()),
        unquoted("mental_and_developmental_conditions", &format!(r"{FOREIGN_AM}({})(?![\w'])", t.foreign_mind_states.names()), leading(&t.foreign_mind_states), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("mental_and_developmental_conditions", &format!(r"{FOREIGN_IS}{FOREIGN_PERSON}({})(?![\w'])", t.foreign_mind_extra.names()), leading(&t.foreign_mind_extra), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("physical_conditions", &format!(r"{FOREIGN_IS}{FOREIGN_PERSON}({})(?![\w'])", foreign_body.names()), leading(&foreign_body), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("mental_and_developmental_conditions",
            r"(?:we|us)(?<!\w(?:we|us))\W+(?:fellow |other )?(autistic|adhd|adhders|neurodivergent|nd|audhd|bipolar|ocd|anxious|depressed|dyslexic) (?:people|folks|adults|women|men|girls|guys|ones|kids|types|individuals|humans)\b",
            by(pairs(&[("autistic", "autism"), ("adhd", "adhd"), ("adhders", "adhd"), ("neurodivergent", "neurodivergent (unspecified)"), ("nd", "neurodivergent (unspecified)"), ("audhd", "audhd"),
                ("bipolar", "bipolar"), ("ocd", "ocd"), ("anxious", "anxiety"), ("depressed", "depression"), ("dyslexic", "dyslexia / learning disorder")])), self_hedge()),
        unquoted("mental_and_developmental_conditions", &format!(
            r"(?:i(?<!\wi)(?: was|'ve been| got| am|'m)|g(?<!\wg)ot|w(?<!\ww)as|b(?<!\wb)een|t(?<!\wt)(?:hey|herapist)|d(?<!\wd)octor|p(?<!\wp)sychiatrist) (?:\w+ )?(?:diagnosed|dx'?d) (?:me )?(?:with|as)(?: an?)? ({})\b",
            t.mental.names()
        ), by(t.mental.clone()), others()),
        unquoted("mental_and_developmental_conditions", &format!(
            r"i(?<!\wi) (?:also |still |do )?(?:have|have had|struggle with|deal with|live with)(?: an?)? ({})(?![\w'-])(?! (?:to|with|of|that|for|in|tech|teacher|program|class|school|course|degree|major|department|student)\b)",
            t.mental_words.names()
        ), by(t.mental.clone()), others()),
        unquoted("medical_devices",
            r"(?:m(?<!\wm)y|i(?<!\wi)(?:'m| am)? (?:also |now |currently |still |just )?(?:use|using|wear|wearing|have|got|started|switched to|am on|on|upgraded to)) (?:a |an |the |new |first |trusty )?(?:(dexcom(?: g[4-7])?|freestyle libre(?: [1-3]\+?)?|libre [1-3]\+?|libre sensors?|cgm|continuous glucose monitor|guardian sensor)|(insulin pump|omnipod(?: 5| dash)?|t[-:]?slim(?: x2)?|tandem (?:pump|mobi|t[-:]?slim)|medtronic (?:pump|minimed|6[37]0g|7[78]0g)|minimed(?: \d+g)?))(?![\w-])",
            |m| Some(if m.has(1) { "cgm" } else { "insulin pump" }.to_string()), own()),
        unquoted("allergies",
            r"i(?<!\wi)(?:'m| am|'ve been| have been|'ve always been)(?: (?:also|very|severely|deathly|highly|super|really|extremely|mildly|slightly|quite|so|pretty|incredibly|horribly|terribly))* allergic to (?:most |all |many |both )?(peanuts?|tree nuts|nuts|almonds|cashews|walnuts|shellfish|shrimp|eggs?|dairy|milk|gluten|wheat|soy|fish|sesame|cats?|dogs?|horses?|rabbits?|pet dander|dander|pollen|grass|ragweed|hay|birch|dust|dust mites|mold|mould|latex|penicillin|amoxicillin|sulfa(?: drugs)?|antibiotics|nsaids|ibuprofen|aspirin|bees|bee stings|wasps)\b|(?:m(?<!\wm)y|i(?<!\wi) (?:also |still )?(?:have|suffer from|get|deal with)(?: an?| severe| bad| terrible| mild| really bad| awful| horrible)*) (food allerg(?:y|ies)|peanut allerg(?:y|ies)|(?:tree )?nut allerg(?:y|ies)|shellfish allerg(?:y|ies)|egg allerg(?:y|ies)|dairy allerg(?:y|ies)|milk allerg(?:y|ies)|seasonal allergies|hay ?fever|pollen allerg(?:y|ies)|grass allerg(?:y|ies)|cat allerg(?:y|ies)|dog allerg(?:y|ies)|pet allerg(?:y|ies)|dust allerg(?:y|ies)|mold allerg(?:y|ies)|latex allerg(?:y|ies)|penicillin allerg(?:y|ies)|sulfa allerg(?:y|ies)|bee allerg(?:y|ies)|gluten allerg(?:y|ies)|wheat allerg(?:y|ies)|soy allerg(?:y|ies)|fish allerg(?:y|ies)|sesame allerg(?:y|ies))\b|i(?<!\wi) (?:have|got) (no) (?:known )?allergies\b|i(?<!\wi)(?:'m| am) (not) allergic to anything\b",
            |m| allergen(m.first()), own()),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|automat|beep|bleep))(?![\s\S]*\b(?:{MODERATION})\b)(?![\s\S]*(?:\bu/\w|\bop\b))[\s\S]*?{BOT_SELF}"), fixed("bot"), TAGGED), &BOT_WORDS),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|beep|bleep|automat))(?![\s\S]*\b(?:{MODERATION})\b)[\s\S]*?{BOT_OWN}"), fixed("bot"), TAGGED), &BOT_WORDS),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|beep|bleep|automat))(?![\s\S]*(?:\bu/\w|\bop\b))[\s\S]*?{BOT_OWN}"), fixed("bot"), TAGGED), &BOT_WORDS),
    ]);
    let mind = loose_states.filter(|_, value| !["anxiety", "depression"].contains(&value));
    let body = t.physical.filter(|name, value| {
        !value.is_empty() && home(PHYSICAL_ATTRIBUTE, value) == PHYSICAL_ATTRIBUTE && (name.chars().count() >= 4 || ["t1d", "t2d", "ibs", "ibd", "eds"].contains(&name)) && !["pots", "disability", "disabilities"].contains(&name)
    });
    for (attribute, table) in [("mental_and_developmental_conditions", mind), (PHYSICAL_ATTRIBUTE, body)] {
        rules.push(needs(unquoted(attribute, &format!(r"(?<![\w'/-])({})(?![\w'-]){FOLLOWERS}(?! (?:ally|allies|advocate|awareness|screeching)\b)(?! '\d\d\b)", table.names()), flair(table.lex()), own()), &["r/"]));
    }
    rules.extend(habits::rules());
    let personal = t.mental_state_strict.filter(|_, value| NEURO.contains(&value) || value == "neurodivergent (unspecified)");
    let personal_lex = personal.lex();
    rules.push(rule("mental_and_developmental_conditions", &PERSONAL_AD.replace("{}", &personal.names()), move |m| {
        if SEEKING.test_in(m.string, m.start(), m.start_of(1) as usize) {
            None
        } else {
            get(&personal_lex, m.group(1))
        }
    }, TAGGED));
    rules
});

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn init() {
    timed("health init", || {
        LazyLock::force(&RULES);
        ailments::init();
        medications::init();
    });
}

pub fn english_conditions() -> Vec<(&'static str, String, &'static str)> {
    let t = &*TABLES;
    let mut rows: Vec<(&'static str, String, &'static str)> = t.physical.iter().filter(|(_, value)| !value.is_empty()).map(|(name, value)| (home(PHYSICAL_ATTRIBUTE, value), name.clone(), value)).collect();
    rows.extend(t.mental_loose.iter().filter(|(_, value)| !value.is_empty()).map(|(name, value)| ("mental_and_developmental_conditions", name.clone(), value)));
    rows
}
