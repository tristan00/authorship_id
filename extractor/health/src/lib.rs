mod ailments;
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
    let keep: HashSet<&str> = STRICT_KEEP.iter().copied().collect();
    let drop: HashSet<&str> = STRICT_DROP.iter().copied().collect();
    let mut tool_strict = physical_tools.filter(|name, value| value != "other physical condition" || keep.contains(name)).filter(|name, _| !drop.contains(name));
    for name in STRICT_UNSPECIFIED {
        tool_strict.insert(name.to_string(), "unspecified");
    }
    let mental = spread(MENTAL);
    let loose: HashSet<&str> = LOOSE_EXCLUDE.iter().copied().collect();
    let mental_loose = mental.filter(|name, _| !loose.contains(name));
    let mental_states = spread(MENTAL_STATES);
    let strict: HashSet<&str> = STATE_STRICT_EXCLUDE.iter().copied().collect();
    let mental_state_strict = mental_states.filter(|name, _| !strict.contains(name));
    let mental_words = mental.filter(|name, _| !["did", "add", "odd", "bed", "ed"].contains(&name));
    let drugs: &'static str = Box::leak(data_file("adhd_drugs.txt").into_boxed_str());
    let mut adhd_drugs = Ordered::default();
    for line in drugs.lines() {
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
    r"|\b(?:suspect|suspected|probably|possibly|wonder|wondering|could be|could have|do i have|self[- ]diagnosed|test(?:ed)? for|screen(?:ed)? for|rule out|ruled out|i think|i thought|i guess|i feel like|pretty sure|i believe)\b"
)));
pub static OTHERS: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"{}|\b(?:{PEOPLE})\b", OWN_HEDGE.pattern)));
static FOREIGN_SELF_HEDGE: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(
    "{}{}{}",
    SELF_HEDGE.pattern,
    r"|(?<![\w'])(?:no|nunca|jamás|ni|si|creo|quizá|quizás|tal vez|ojalá|não|nao|nem|se|acho|talvez|ne|n'|pas|jamais|nicht|kein|keine|nie|niemals|wenn|falls|ob|",
    r"vielleicht|non|mai|forse|niet|geen|nooit|misschien|jeśli|może|chyba)(?![\w'])"
)));
pub static MENTAL_TAIL: LazyLock<Re> = LazyLock::new(|| Re::new(&format!(r"\b(?:{})$", TABLES.mental.names())));
static SENSE: LazyLock<Re> = LazyLock::new(|| Re::new(r"deaf|blind|hearing|eye|sight|vision|ear\b"));
static SEEKING: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:no|not|non|looking for|seeking|want|wants|wanted|for|with|into|love|loves|like|likes)\W+(?:[\w'-]+\W+)?$"));

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
        r"|(?<![\w.])(?:i'?m |i am )?(?:1[3-9]|[2-9]\d) ?(?:[mf]|yo|y/o|years? old)?\)?,? (?:with|w/)",
    ]
    .concat()
}

pub fn had() -> String {
    format!("{SUBJECT}{}", r"(?:had|suffered from|struggled with|dealt with|lived with|battled|fought|beat|survived|overcame|was treated for|was dealing with|went through|got treated for)")
}

pub fn have() -> String {
    format!("{}|{}", have_now(), had())
}

pub const BARE: &str = r"(?:^|[.!?\n|]\s*)(?:recently |newly |just |finally |officially |formally |also |and |got |was |been )*(?:diagnosed|dx'?d) (?:with|w/)";
pub const MODIFIERS: &str = concat!(
    r"own|severe|mild|moderate|chronic|acute|stupid|damn|damned|fucking|freaking|bloody|bad|untreated|undiagnosed|diagnosed|recent|current|constant|occasional|lifelong|genetic|congenital|",
    r"hereditary|early|late|new|old|primary|secondary|crippling|debilitating|terrible|horrible|awful|pretty bad|really bad|annoying|lovely|wonderful|recurring|recurrent|persistent|ongoing|",
    r"rare|treatment[- ]resistant|clinical|major|severe chronic|medicated|unmedicated|managed|controlled|uncontrolled|diet[- ]controlled|stage \w+|grade \w+|type \w+|level \w+|chronic severe|",
    r"intermittent|episodic|silent|mild case of|bit of|bit of an?|little|minor|slight|full blown|full-blown|high[- ]functioning|combined[- ]type|inattentive[- ]type|hyperactive[- ]type|",
    r"inattentive|combined|hyperactive|textbook|diagnosed severe|late[- ]diagnosed|recently diagnosed|adult|childhood|postpartum|seasonal|crazy|insane|massive|huge|lingering|residual|newly diagnosed|",
    r"some|a lot of|lots of|serious|really|very|super|extreme|extremely|both|mostly|mainly|also"
);
pub const FOLLOWERS: &str = r"(?! (?:friend|friends|kid|kids|son|daughter|brother|sister|partner|husband|wife|mom|dad|mother|father|patient|patients|client|clients|community|people|person|research|awareness|month|day|walk|charity|foundation|society|association|group|subreddit|sub|forum)s?\b)";

pub fn gap() -> String {
    format!(r"(?:(?!(?:{PEOPLE}|not|no|never|and|but|or|if|when|because|so|that|who|which|what|where|than|to)\b)[\w'/-]+,?\s+){{0,3}}?")
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
pub const NEURO: [&str; 3] = ["adhd", "autism", "both adhd and autism"];

pub fn quoted(text: &[char], start: usize) -> bool {
    let line = &text[line_start(text, start)..start];
    let straight = line.iter().filter(|&&c| c == '"').count();
    straight % 2 == 1 || line.iter().filter(|&&c| c == '\u{201c}').count() > line.iter().filter(|&&c| c == '\u{201d}').count()
}

fn get(lex: &Lex, part: Option<&[char]>) -> Option<String> {
    part.and_then(|key| lex.get(key)).map(|value| value.to_string())
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
    let mut rules = vec![
        unquoted("physical_condition", &format!(
            r"m(?<!\wm)y (?:own |new |old |daily |current |rescue |emergency |stupid |damn |trusty |first |second |last |next |latest |recent |regular |usual |monthly |weekly |yearly |annual |\w+ (?:and )?)?({tool_names})\b(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad)s?\b)"
        ), move |m| {
            if let Some(mental) = MENTAL_TAIL.search(m.string, m.start(), m.end()) {
                if (mental.start() as isize) < m.start_of(1) {
                    return None;
                }
            }
            get(&tool_lex, m.group(1))
        }, own()),
        unquoted("physical_condition", &format!(
            r"i(?<!\wi)(?: (?:also |still |now |have to |had to |need to |always |usually |currently |sometimes |must )?(?:wear|need|use|carry|have|got|take|took|started|start|am on|was on|was put on|got put on|was prescribed|got prescribed|inject|do|did|go to|see|saw|visit)|'m (?:also |still |now |currently )?(?:on|taking|using)|'ve (?:been on|been taking|been using|started)) (?:a |an |my |the |two |both |prescription |daily )?({tool_rule_names})\b"
        ), by(tool_strict), own()),
        unquoted("physical_condition",
            r"i(?<!\wi)(?:'?m| am|'ve gone| have gone|'m going| am going)(?: (?:also|now|already|still|basically|practically|essentially|technically))* (?:legally |completely |totally |profoundly |partially |mostly )?(?:deaf|blind|hard of hearing)\b|i(?<!\wi) (?:was )?born (?:without|with(?:out)? (?:a |an |one )?(?:missing|no) )|i(?<!\wi) (?:was )?born with (?:one|only one|half an?|a missing|no) (?:arm|leg|hand|foot|kidney|eye|ear|lung)\b|i(?<!\wi) (?:lost|had amputated|had to have amputated) (?:my |both |one of my |part of my )(?:\w+ )?(?:arm|leg|hand|foot|feet|legs|arms|fingers|toes|eye|sight|vision|hearing)\b",
            |m| Some(if SENSE.test(m.text()) { "vision or hearing impairment" } else { "physical disability" }.to_string()), self_hedge()),
        unquoted("physical_condition",
            r"i(?<!\wi)(?:(?:'?m| am|'ve been| have been)(?: (?:also|still|currently|now|basically|literally|just|pretty much))*(?: (?:always|often|constantly|permanently|chronically|perpetually|frequently|usually|almost always) in(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|much|constant|chronic|daily))*| in(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|much))* (?:constant|chronic|daily|ongoing|almost constant|nearly constant|perpetual|permanent|never[- ]?ending|endless|everyday|lifelong|persistent)(?: (?:severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating))*)| live(?: (?:always|constantly|daily))? (?:in|with)(?: (?:a lot of|so much|severe|excruciating|agonizing|agonising|unbearable|terrible|horrible|significant|serious|extreme|intense|immense|crippling|debilitating|some|constant|chronic|daily|ongoing))*) pain\b(?! (?:management|clinic|meds|medications?|killers?|relief|pills?|doctors?|specialists?)\b)",
            fixed("chronic pain or fibromyalgia"), self_hedge()),
        unquoted("physical_condition", concat!(
            r"m(?<!\wm)y (?:face|skin|scalp|face skin|facial skin) (?:is|has been|gets|get|keeps|is always|is still|is getting|has gotten|tends to be|is naturally|is super|is very|is so|is really|is extremely|is quite|is pretty|is kinda|is a bit|always gets)* ?",
            r"(?:so |very |really |super |extremely |quite |pretty |kinda |a bit |naturally )?(?:dry|oily|sensitive|acne[- ]prone|prone to (?:acne|breakouts|redness|irritation)|breaking out|broken out|flaky|flaking|peeling|",
            r"itchy|irritated|inflamed|congested|dehydrated|reactive|combination)\b"
        ), fixed("skin condition"), own()),
        unquoted("physical_condition", concat!(
            r"m(?<!\wm)y (?:\w+ )?(?:back|knees?|hips?|joints|neck|shoulders?|wrists?|ankles?|feet|legs|hands|stomach|head) (?:still |always |really |constantly |also )?",
            r"(?:hurts?|aches?|(?:is |are |has been |have been |keeps |keep )?(?:hurting|aching|killing me|sore|in pain))\b"
        ), fixed("unspecified"), own()),
        unquoted("mental_condition", &format!(r"(?:{have})\s+{modifier}(?:an? )?{gap}({loose})\b{FOLLOWERS}"), by(t.mental_loose.clone()), own()),
        unquoted("mental_condition", &format!(r"{BARE}\s+{modifier}(?:an? )?{gap}({loose})\b{FOLLOWERS}"), by(t.mental_loose.clone()), others()),
        unquoted("mental_condition", r"a(?<!\wa)s an? (suicidal|depressed|anxious|paranoid|psychotic)\b",
            by(pairs(&[("suicidal", "other mental health condition"), ("depressed", "depression"), ("anxious", "anxiety"), ("paranoid", "anxiety"), ("psychotic", "schizophrenia or psychosis")])), self_hedge()),
        unquoted("mental_condition",
            r"(?:i(?<!\wi)(?: have|'ve had| was diagnosed with| got diagnosed with|'ve been diagnosed with|'m diagnosed with|'m on meds for| take meds for| was recently diagnosed with| also have| do have| have had)|d(?<!\wd)iagnosed with) (?:(?:severe|mild|moderate|chronic|clinical|diagnosed|combined[- ]type|inattentive[- ]type|bad|really bad|pretty bad|terrible|untreated|unmedicated|adult|both|some|serious) )*(add|did|ied|odd|osdd|trich|tics|insomnia|pmdd|hypomania|mania|panic attacks|anxiety attacks|binge eating|disordered eating|intrusive thoughts|suicidal thoughts|self harm|self-harm|childhood trauma|complex trauma|trauma|burnout|autistic burnout|executive dysfunction|sensory issues|gender dysphoria|separation anxiety|claustrophobia|dissociation|sleep paralysis|night terrors|a stutter|a speech impediment|stuttering|apraxia|a nervous breakdown|a mental breakdown|nervous breakdowns|emotional dysregulation)\b",
            by(t.mental.with(&[("add", "adhd"), ("bed", "eating disorder"), ("ied", "other mental health condition"), ("odd", "other mental health condition")])), own()),
        unquoted("mental_condition", &format!(r"m(?<!\wm)y {modifier}({loose})\b{FOLLOWERS}(?! (?:medication|meds)\b)"), by(t.mental_loose.clone()), own()),
        unquoted("mental_condition",
            r"m(?<!\wm)y (?:(?:own|official|formal|first|recent|new|adult|actual|initial|late) )*(adhd|autism|audhd|ocd|bpd|ptsd|cptsd|anxiety|depression|bipolar|ed|eating disorder|addiction|insomnia|tics|trich|did) (?:brain|meds|medication|diagnosis|symptoms|is|was|has|makes|gets|kicks|flares|got|took|and|so)\b",
            by(t.mental.with(&[("bipolar", "bipolar disorder"), ("ed", "eating disorder"), ("insomnia", "other mental health condition"), ("tics", "other mental health condition"),
                ("trich", "other mental health condition"), ("did", "other mental health condition")])), own()),
        unquoted("mental_condition", &format!(
            r"(?:a(?<!\wa)s(?: an?| a fellow| someone who is| a person who is| somebody with| a person with| someone with| one with)|b(?<!\wb)eing an?|m(?<!\wm)e, an?) (?:fellow |diagnosed |late[- ]diagnosed |recovering |recovered |formerly )?({loose}|{}) ?(?:person|woman|man|adult|guy|girl|individual|sufferer|patient|survivor|haver|myself|lady|dude|mom|dad|mother|father|parent|teen|kid|student|female|male|human|being)?\b",
            t.mental_state_strict.names()
        ), by(loose_states), self_hedge()),
        unquoted("mental_condition", &format!(
            r"i(?<!\wi)(?:'m|m| am| m|'ve been|ve been| have been| was| became|'m now|'m also|'m actually) (?:also |now |currently |technically |actually |literally |officially |still |pretty |very |so |really |too |super |just |severely |extremely |mildly |pretty much |basically |definitely |diagnosed |clinically |formally |medically |probably not |a diagnosed |a |an |self[- ]diagnosed |late[- ]diagnosed )*({})\b(?! (?:people|person|friend|friends|community|rights|folks|kids?|son|daughter|family|patients?|to (?:the|this|that|your|my|his|her|their|it|them|what|how|whether|any)|about|of|for(?! (?:a long time|a while|years|months|weeks|ages|decades|so long|most of my life|over|almost|nearly|the (?:past|last)|\d+))|from|by|over|with)\b)",
            feeling_states.names()
        ), by(feeling_states.clone()), own()),
        unquoted("mental_condition", &format!(
            r"(?:m(?<!\wm)y|i(?<!\wi)(?: take|'m on| am on|'ve been on| started|'m taking| am taking|'ve been taking| was put on| got put on| was prescribed| got prescribed| was given| switched to| take my| forgot my| forgot to take my| ran out of|'m out of)|p(?<!\wp)(?:rescribed me|ut me on)|g(?<!\wg)ave me|s(?<!\ws)witched me to) (?:\w+ )?(?:\d+\s?mg (?:of )?)?({})\b",
            t.adhd_drugs.names()
        ), by(t.adhd_drugs.clone()), self_hedge()),
        unquoted("mental_condition", &format!(r"\b(audhd|au/dhd)\b{FOLLOWERS}"), fixed("both adhd and autism"), others()),
        unquoted("mental_condition",
            r"\b(adhd|autism|audhd|asd|ocd|ptsd|cptsd|bpd|anxiety|depression|bipolar|insomnia) (?:brain|makes my|affects my|ruins my|means i|makes me|makes it|has made my|messes with my|fucks with my|controls my|took over my|runs my|got the better of me)\b",
            by(t.mental.with(&[("bipolar", "bipolar disorder"), ("insomnia", "other mental health condition")])), self_hedge()),
    ];
    for pattern in [
        format!(r"(?:r(?<!\wr)ecover(?:ing|ed)|i(?<!\wi)n recovery) from (?:my |an? )?({loose})\b"),
        format!(r"(?:u(?<!\wu)n(?:diagnosed|medicated|treated)|d(?<!\wd)iagnosed|c(?<!\wc)rippling|l(?<!\wl)(?:ifelong|ate[- ]diagnosed)) (?:but severe )?({loose})\b(?=[^.!?\n]*\b(?:i|my|me)\b)"),
        format!(r"^\W*(?:yep\W+|yeah\W+|also\W+|same\W+|me too\W+)?({loose})\W*$"),
        format!(r"(?:^|[.!?\n]\s*)also,? ({loose})\b(?=\W*(?:$|[.!?\n]))"),
    ] {
        rules.push(unquoted("mental_condition", &pattern, by(t.mental_loose.clone()), own()));
    }
    let caused = pairs(&[("depressed", "depression"), ("suicidal", "other mental health condition"), ("depression", "depression"), ("anxiety", "anxiety"), ("ptsd", "ptsd"),
        ("an eating disorder", "eating disorder"), ("agoraphobic", "anxiety"), ("alcoholic", "addiction"), ("addict", "addiction")]).lex();
    rules.extend([
        unquoted("mental_condition",
            r"(?:m(?<!\wm)a(?:de|kes|king)|l(?<!\wl)e(?:ft|aving)|g(?<!\wg)ave) me (?:really |so |very |super |severely |clinically |chronically )?(depressed|suicidal|depression|anxiety|ptsd|an eating disorder|agoraphobic)\b(?= *(?:$|[.!\n,;]|and\b|for (?:years|months|a long time)))|b(?<!\wb)ec(?:oming|ame|ome) an (alcoholic|addict)\b",
            move |m| get(&caused, m.first()), own()),
        unquoted("mental_condition",
            r"f(?<!\wf)or my (adhd|autism|anxiety|depression|ocd|ptsd|cptsd|bipolar|bpd|insomnia|panic attacks|panic disorder|social anxiety|mdd|gad|ed|eating disorder|addiction|alcoholism)\b",
            by(t.mental.with(&[("bipolar", "bipolar disorder"), ("ed", "eating disorder"), ("insomnia", "other mental health condition"), ("panic attacks", "anxiety")])), own()),
        unquoted("mental_condition",
            r"i(?<!\wi) (?:was|got) (?:\w+ )?(?:hospitalized|hospitalised|admitted|committed|sectioned|baker acted|5150'?d|put on a 5150|put in a psych ward|in a psych ward|in the psych ward|inpatient) (?:for|after|because of) (?:my |an? )?(depression|suicidal thoughts|a suicide attempt|suicide attempt|an overdose|psychosis|a psychotic episode|mania|a manic episode|an eating disorder|anorexia|bulimia|self harm|self-harm)\b",
            by(pairs(&[("depression", "depression"), ("suicidal thoughts", "depression"), ("a suicide attempt", "depression"), ("suicide attempt", "depression"), ("an overdose", "addiction"), ("psychosis", "schizophrenia or psychosis"),
                ("a psychotic episode", "schizophrenia or psychosis"), ("mania", "bipolar disorder"), ("a manic episode", "bipolar disorder"), ("an eating disorder", "eating disorder"), ("anorexia", "eating disorder"),
                ("bulimia", "eating disorder"), ("self harm", "other mental health condition"), ("self-harm", "other mental health condition")])), own()),
        unquoted("mental_condition",
            r"i(?<!\wi)(?:'m|m| am|'ve been| have been) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a few|several|many|over \d+|almost \d+|nearly \d+) (?:days?|weeks?|months?|years?|yrs?) (?:sober|clean|off (?:drugs|alcohol|heroin|meth|opiates|opioids|pills|booze|the booze|the drink|drinking))\b",
            fixed("addiction"), self_hedge()),
        unquoted("mental_condition",
            r"i(?<!\wi)(?:'m|m| am|'ve been|ve been| got| became) (?:so |really |literally |kinda |pretty |super |very |totally |completely |still |seriously |severely )*addicted to\b",
            fixed("addiction"), own()),
        unquoted("mental_condition",
            r"i(?<!\wi)(?:'m|m| am)(?: also| currently| still| now| back)? on (?:my |prescription |prescribed |stimulant )?(?:adhd|add) (?:meds|medications?|medicine|stimulants)\b|i(?<!\wi)(?:'m| am)? (?:take|took|started|need|taking|started taking|stopped taking) (?:my )?(?:adhd|add) (?:meds|medications?|medicine)\b",
            fixed("adhd"), own()),
        unquoted("mental_condition",
            r"m(?<!\wm)y (?:own )?(autistic|neurodivergent|adhd|audhd|dyslexic) (?:ass|self|brain|mind|side|butt|tendencies|traits|quirks|desire|desires|obsession|obsessions|experience|nature|needs|meltdowns?|hyperfixations?|hyperfocus|special interests?|stims?|stimming|logic|ways|moments?|struggles|symptoms|issues|habits)\b",
            by(pairs(&[("autistic", "autism"), ("neurodivergent", "neurodivergent, unspecified"), ("adhd", "adhd"), ("audhd", "both adhd and autism"), ("dyslexic", "dyslexia")])), own()),
        unquoted("mental_condition", &format!(r"{FOREIGN_AM}({})(?![\w'])", t.foreign_mind_states.names()), leading(&t.foreign_mind_states), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("mental_condition", &format!(r"{FOREIGN_IS}{FOREIGN_PERSON}({})(?![\w'])", t.foreign_mind_extra.names()), leading(&t.foreign_mind_extra), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("physical_condition", &format!(r"{FOREIGN_IS}{FOREIGN_PERSON}({})(?![\w'])", t.foreign_body_states.names()), leading(&t.foreign_body_states), Some(&*FOREIGN_SELF_HEDGE)),
        unquoted("mental_condition",
            r"(?:we|us)(?<!\w(?:we|us))\W+(?:fellow |other )?(autistic|adhd|adhders|neurodivergent|nd|audhd|bipolar|ocd|anxious|depressed|dyslexic) (?:people|folks|adults|women|men|girls|guys|ones|kids|types|individuals|humans)\b",
            by(pairs(&[("autistic", "autism"), ("adhd", "adhd"), ("adhders", "adhd"), ("neurodivergent", "neurodivergent, unspecified"), ("nd", "neurodivergent, unspecified"), ("audhd", "both adhd and autism"),
                ("bipolar", "bipolar disorder"), ("ocd", "ocd"), ("anxious", "anxiety"), ("depressed", "depression"), ("dyslexic", "dyslexia")])), self_hedge()),
        unquoted("mental_condition", &format!(
            r"(?:i(?<!\wi)(?: was|'ve been| got| am|'m)|g(?<!\wg)ot|w(?<!\ww)as|b(?<!\wb)een|t(?<!\wt)(?:hey|herapist)|d(?<!\wd)octor|p(?<!\wp)sychiatrist) (?:\w+ )?(?:diagnosed|dx'?d) (?:me )?(?:with|as)(?: an?)? ({})\b",
            t.mental.names()
        ), by(t.mental.clone()), others()),
        unquoted("mental_condition", &format!(
            r"i(?<!\wi) (?:also |still |do )?(?:have|have had|struggle with|deal with|live with)(?: an?)? ({})\b(?! (?:to|with|of|that|for|in)\b)",
            t.mental_words.names()
        ), by(t.mental.clone()), others()),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|automat|beep|bleep))(?![\s\S]*\b(?:{MODERATION})\b)(?![\s\S]*(?:\bu/\w|\bop\b))[\s\S]*?{BOT_SELF}"), fixed("bot"), TAGGED), &BOT_WORDS),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|beep|bleep|automat))(?![\s\S]*\b(?:{MODERATION})\b)[\s\S]*?{BOT_OWN}"), fixed("bot"), TAGGED), &BOT_WORDS),
        needs(rule("automated_account", &format!(r"^(?=[\s\S]*?(?:bot|beep|bleep|automat))(?![\s\S]*(?:\bu/\w|\bop\b))[\s\S]*?{BOT_OWN}"), fixed("bot"), TAGGED), &BOT_WORDS),
    ]);
    let personal = t.mental_state_strict.filter(|_, value| NEURO.contains(&value) || value == "neurodivergent, unspecified");
    let personal_lex = personal.lex();
    rules.push(rule("mental_condition", &PERSONAL_AD.replace("{}", &personal.names()), move |m| {
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
    });
}

pub fn english_conditions() -> Vec<(&'static str, String, &'static str)> {
    let t = &*TABLES;
    let mut known: HashSet<&str> = HashSet::default();
    for table in [&t.physical, &t.physical_states, &t.physical_tools, &t.mental, &t.mental_states, &t.mind_extra] {
        known.extend(table.keys.iter().map(|key| key.as_str()));
    }
    let wordnet: &'static str = Box::leak(data_file("wordnet_conditions.tsv").into_boxed_str());
    let mut rows: Vec<(&'static str, String, &'static str)> = t.physical.iter().map(|(name, value)| ("physical_condition", name.clone(), value)).collect();
    rows.extend(t.mental_loose.iter().map(|(name, value)| ("mental_condition", name.clone(), value)));
    rows.extend(wordnet.lines().filter_map(|line| line.split_once('\t')).filter(|(name, _)| !known.contains(name)).map(|(name, value)| ("physical_condition", name.to_string(), value)));
    rows
}
