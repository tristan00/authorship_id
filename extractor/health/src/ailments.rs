use crate::*;
use claimcore::*;
use std::collections::HashSet as StdSet;
use std::sync::LazyLock;

const COMMON_STOP: &str = "not|no|never|neither|nor|without|and|but|or|if|when|because|so|that|who|which|what|where|why|how|whether|than|to|in|on|about|like|for|from|at|by|into|of|with|without|is|was|are|were|be|it|this";

fn stop() -> String {
    format!("{PEOPLE}|{COMMON_STOP}")
}

fn free() -> String {
    format!(r"(?:(?!(?:{})s?\b)(?![\w'-]*(?:ed|en)\b)[\w'/-]+,?\s+)", stop())
}

fn lead() -> String {
    format!(r"(?:[\s,]+(?:(?:{MODIFIERS})\b|an?\b|the\b))*[\s,]*")
}

fn owning(have: &str, mine: &str) -> String {
    let (lead, free) = (lead(), free());
    format!(
        r"(?:{have}){lead}{free}{{0,2}}|{mine}|\b(?:i've|ive|i have got){lead}|\b(?:a |as a |from a )?fellow{lead}|\b(?:i'm|i am|im) (?:on|taking) [\w-]+ for(?: my| the)?{lead}|\b(?:put|got|have) me on [\w-]+ for(?: my| the)?{lead}|\bi (?:take|took|use|need) [\w-]+(?: [\w-]+)? for(?: my| the)?{lead}|\bi (?:talked|spoke|talk|speak|went) to (?:my|a) (?:doctor|therapist|psychiatrist|psych|gp|pcp|counselor|counsellor|specialist|neurologist|doc) (?:about|for)(?: my)?{lead}"
    )
}

fn stating(being: &str) -> String {
    let (lead, free) = (lead(), free());
    format!(
        r"(?:\b(?:i'm|im|i am|i've been|ive been|i have been|i was born|i became|as(?: an?)?|{being}|me,?(?: an?)?|(?:a |as a |from a )?fellow|as someone (?:who|that)(?:'s| is))(?: (?:also|now|currently|still|technically|actually|literally|officially|basically|completely|totally|profoundly|severely|mostly|partially|fully|medically|legally|kind of|kinda|just|really|so|recently|newly|permanently|chronically|clinically|unfortunately|apparently|obviously|functionally|genetically|naturally|definitely))*{lead}{free}{{0,2}})$"
    )
}

fn carrier() -> String {
    format!(r"\bi(?<!\wi)(?:'m|m| am| have| do| was|'ve|ve)?(?: (?!(?:{PEOPLE}|we|it|it's|this|that|not|no|never|but|or|if|when|because|so|who|which|what)\b)[\w'-]+){{1,6}}?(?:,? and|,) (?:also |currently |still |now |even |i )?")
}

macro_rules! re {
    ($name:ident, $e:expr) => {
        static $name: LazyLock<Re> = LazyLock::new(|| Re::new(&$e));
    };
}

re!(OTHER_PEOPLE, r"\b(?:roommate|flatmate|housemate|coworker|colleague|classmate|child|children|kid|kids|baby|babies|toddler|infant|newborn|mom|mother|dad|father|wife|husband|son|daughter|friend|brother|sister|grandma|grandpa|grandmother|grandfather|aunt|uncle|cousin|boyfriend|girlfriend|partner|he|she|his|her|him|they|their|dog|cat|patients?|clients?|family|families|relatives)\b");
re!(MOOD_NAMES, format!(r"\b({})\b", pairs_names(MOODS)));
re!(UNNAMED, r"\bi(?<!\wi)(?:'m| am| was| got| have been|'ve been|ve been)(?: (?:officially|finally|formally|recently|just|only|also|then|eventually|late|properly))? (?:diagnosed|dx'?d)(?! (?:with|w/|as an?|as having|by|for)\b)|\bi(?<!\wi) (?:got|received|finally got|just got|recently got) (?:my|a|an|the) (?:official |formal |proper )?(?:diagnosis|dx)\b");
re!(ASSESSED, r"[\s-]*(?:assessments?|evaluations?|diagnos\w*|traits|testing|tests?|screening)\b");
re!(RELATIVE, r"\bwho(?:'s| is| was| has| had| have)(?: [\w-]+){0,2} $");
re!(POTTERY, r"\b(?:plants?|houseplants?|soil|drainage|pottery|potting|clay|kiln|glaze|pans|cooking|stove|ceramics?|succulents?)\b");
re!(NEGATED, r"\b(?:neither|nor|without|never had|don't have|do not have|not)\b(?:[\s,/-]+[\w'-]+){0,2}[\s,/-]+$");
re!(PREFIXED, r"\b(?:pre|non|anti|post)-?$");
re!(OBJECT, r"\b(?:the|this|that|about|understands?|understanding|treats?|treating|research|researching|studies|study|broader|broad|evil|normal)\s+$");
re!(POSSESSOR, format!(r"\b(?:{PEOPLE}|someone|anyone|somebody|anybody|those)(?: (?!(?:and|but|or|i|i'm|im|me|my)\b)\w+){{0,2}} (?:has|have|had|having|with|gets|got)(?: \w+){{0,2}} $"));
re!(ADDRESSED, r"\b(?:you|your|you're|u|ur)\b");
re!(GENERIC, r"\s+(?:is|are|isn't|aren't|makes|make|causes|cause|can|could|does|doesn't|means|affects|tends|presents|manifests)\b");
re!(ATTRIBUTIVE, r" +(?!(?:and|or|af|asf|myself|too|as|but|so|lol)\b)[a-z]");
re!(ASKING, r"\b(?:do|does|did|could|can|might|may|am|would|should|will|have) i\b");
re!(GENERAL, r"\b(?:the|this|that|some|much|any|no|less|more|of|such|social|performance|test|exam|post|pre|non|anti)\s+$");
re!(NAMED_OWNER, r"\b(?!(?:i|it|that|he|she|there|what|who|let|here|today|everyone|one)\x27s\b)[\w-]+(?:\x27s|s\x27)\s+$");
re!(CAUSED, r"\b(?:give|gives|giving|gave|given) (?:me|us) (?:[\w-]+ ){0,3}$");
re!(FIRST_PERSON, r"\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|myself|mine)\b");
re!(HEADS, r"\s*(?:treatments?|diagnos[ie]s|journey|management|care|awareness|meds|medications?|medicines?|drugs?|pills?|supplies|creams?|moisturi[sz]ers?|products?|routines?|complications?|experiences?|sufferers?|babies|studios?|diets?|friendly|centers?|centres?)\b");
re!(CROWD, r"\b(?:people|person|those|anyone|someone|somebody|everyone|many|most|some|others|patients|women|men|kids|children|americans|studies|research|risk|causes?|symptoms?)\b");
re!(NOUN_CUE, format!(r"(?:{})$", owning(&have_now(), &format!(r"\bmy{}{}{{0,2}}", lead(), free()))));
re!(PAST_CUE, format!(r"(?:{}){}{}{{0,2}}$", had(), lead(), free()));
re!(MIND_CUE, format!(r"(?:{}|\b(?:must|could|might|may|probably|just|it's|its|that's|thats|blame it on|blame)(?: just| probably| definitely)?(?: be)? the{})$", owning(&have(), &format!(r"\bmy{}", lead())), lead()));
re!(DROPPED, format!(r"{flair}\W*(?:also |and |but |still |now |recently |just |newly |finally |officially |got |was |been )*(?:have|got|having|suffer from|suffer with|suffering from|suffering with|struggle with|struggling with|deal with|dealing with|live with|living with|recovering from|battling|diagnosed with|dx'?d with){}{}?", lead(), free(), flair = claimcore::flair!()));
re!(DIAGNOSED, format!(r"{flair}\W*(?:recently |just |also |finally |newly |officially |formally )?(?:got |was |been )?(?:diagnosed|dx'?d)(?: as)?{}", lead(), flair = claimcore::flair!()));
re!(CAUSE, format!(r"(?:(?<=\bbecause )of|(?<=\bbc )of|(?<=\bdue )to|(?<=\bthanks )to|(?<=\bcaused )by){}{}?$", lead(), free()));
re!(KIN, format!(r"\b(?:{PEOPLE}|we|us|our)\b"));
re!(CANDIDATE, r"\b(?:someone|i|i'm|im|i've|ive|my|me|fellow|have|having|got|suffer|suffering|struggle|struggling|deal|dealing|live|living|recovering|battling|diagnosed|dx'?d|the|here|warrior|gang|squad|life|club|crew|fam)\b");
re!(HERE_BEFORE, concat!(r"(?:^", claimcore::flair!(), r"|[,;(|])\s*(?:an? )?(?:fellow |another |also |also an? |proud |former |recovering |recovered )?$"));
re!(HERE_AFTER_PHYSICAL, r" (?:here|sufferer here|patient here|survivor here|warrior here|warrior|gang|squad|life|haver here|person here|club|crew|fam)\b");
re!(HERE_AFTER_MENTAL, concat!(
    r" (?:here|person here|haver here|sufferer here|survivor here|gal here|guy here|girl here|woman here|man here|mom here|mama here|dad here|adult here|",
    r"patient here|warrior|gang|squad|club|crew|fam)\b"
));
re!(SELF_BEFORE, format!(r"\b(?:i'm|im|i am|i was|i've been|ive been|i have been|me,?)(?: (?:also|just|still|now|currently|actually|basically|really))*(?:[\s,]+(?!(?:{})\b)(?![\w'-]*ing\b)[\w'/-]+){{0,5}}?[\s,]+$", stop()));
re!(SELF_AFTER, r" (?:person|woman|man|guy|girl|gal|lady|dude|boy|kid|teen|teenager|adult|individual|human|sufferer|survivor|patient|warrior|student|female|male)(?![\w'])(?=\s*(?:[,;:.!?)(/]|$|(?:and|but|so|who|that|with|here|myself|lol|too)\b))");
re!(DUAL_CUE, format!(r"\b(?:i'm|im|i am|i've been|ive been|i have been|i became|being|myself as|identify as)(?: (?:also|now|currently|still|actually|literally|officially|just|really|so|recently|newly|clinically|definitely))*{}{}{{0,2}}$", lead(), free()));
re!(CARRIED, format!(r"{}(?:have|got|suffer from|struggle with|deal with|live with|am battling|am fighting|battling|fighting|am dealing with|dealing with|am living with|living with|am recovering from|recovering from|am suffering from|suffering from|got diagnosed with|was diagnosed with|diagnosed with){}{}{{0,2}}$", carrier(), lead(), free()));
re!(CARRIED_STATE, format!(r"(?:{c}(?:am |i'm |im )?(?:also |now |currently |still |actually |very |so |really |clinically |definitely )*|{c}am{}{}{{0,2}})$", lead(), free(), c = carrier()));
re!(CLAUSE_END, r"\s*(?:[,;:.!?)(/&+]|$|(?:and|but|so|with|too|as well|myself|lol)\b)");
re!(STATE_CUE, stating("being an?"));
re!(MIND_STATE_CUE, stating("being(?: an?)?|of us"));
re!(LINK, format!(r"\s*(?:,|&|/|\+|\band\b|\bor\b|\bplus\b|\bas well as\b|\balong with\b|\bw/)(?:\s*(?:and|&)\b)?{}", lead()));
re!(TRAIL, format!(r"\s*(?:{PEOPLE}|community|person|research|awareness|month|day|walk|{}", r"charity|foundation|society|association|group|subreddit|sub|forum|nurse|doctor|unit|ward|center|centre|clinic|risk|test|testing|screening|study|studies|lab)s?\b|'s\b"));
re!(SCOPE, r"[,;:(.!?\n]|\b(?:and|but|because|cause|cuz|bc|since|so|though|although|while|whereas)\b");
re!(ASTROLOGY, r"\b(?:\d{1,2}h|chiron|stellium|natal|lilith|aries|taurus|gemini|geminis|leo|leos|virgo|virgos|libra|libras|scorpio|scorpios|sagittarius|capricorn|capricorns|aquarius|pisces|zodiac|horoscope|astrology)\b|\b(?:in|into) cancer\b|\bcancer (?:sun|moon|rising|venus|mars|mercury|jupiter|saturn|placement|season|sign)\b|\b(?:sun|moon|rising|saturn|jupiter|venus|mars|mercury) (?:in|sign)\b");
re!(SENTENCE, r"[^.!?\n]+");
re!(POSSESSIVE_HEDGE, r"\b(?:if|whether|unless|imagine|pretend|wish|hope)\b");
re!(FOREIGN_END, r#"[.;:!?()\[\]\"\n]"#);
re!(FOREIGN_TOKEN, r"[\w'-]+|[^\w\s]");

fn pairs_names(items: &[(&str, &str)]) -> String {
    names(items.iter().map(|(key, _)| *key))
}

const SUFFIXES: [&[char]; 2] = [&['i', 't', 'i', 's'], &['p', 'h', 'o', 'b', 'i', 'a']];
const POLYSEMOUS: [&str; 3] = ["blind", "piles", "disability"];
const TROUBLES: [&str; 6] = ["problems", "issues", "trouble", "condition", "conditions", "imbalance"];
const UNSPECIFIED: [&str; 12] = ["surgery", "surgeries", "a surgery", "an operation", "an injury", "injuries", "an illness", "illness", "a disease", "an infection", "infection", "infections"];

struct Names {
    index: HashMap<Key, Vec<Vec<Key>>>,
}

impl Names {
    fn new<'a>(names: impl IntoIterator<Item = &'a str>) -> Names {
        let mut index: HashMap<Key, Vec<Vec<Key>>> = HashMap::default();
        for name in names {
            let mut tokens: Vec<Key> = name.split(' ').map(|token| token.chars().collect()).collect();
            let mut key = &tokens[0];
            for token in &tokens {
                if token.len() > key.len() {
                    key = token;
                }
            }
            let key = key.clone();
            tokens.sort();
            tokens.dedup();
            index.entry(key).or_default().push(tokens);
        }
        Names { index }
    }

    fn within<'a, I: Iterator<Item = &'a [char]>>(&self, tokens: impl Fn() -> I) -> bool {
        let mut pending: Vec<&Vec<Vec<Key>>> = Vec::new();
        for token in tokens() {
            if let Some(sets) = self.index.get(token) {
                if sets.iter().any(|set| set.len() == 1) {
                    return true;
                }
                pending.push(sets);
            }
        }
        if pending.is_empty() {
            return false;
        }
        let tokens: Vec<&[char]> = tokens().collect();
        pending.iter().any(|sets| sets.iter().any(|set| set.iter().all(|needed| tokens.contains(&needed.as_slice()))))
    }
}

fn spans<'a>(names: impl IntoIterator<Item = &'a String>) -> HashMap<Key, usize> {
    let mut longest: HashMap<Key, usize> = HashMap::default();
    for name in names {
        let first: Key = name.split(' ').next().unwrap().chars().collect();
        let size = name.matches(' ').count() + 1;
        let entry = longest.entry(first).or_insert(0);
        *entry = (*entry).max(size);
    }
    longest
}

struct Family {
    attribute: &'static str,
    nouns: Lex,
    states: Lex,
    known: HashSet<Key>,
    cue: &'static LazyLock<Re>,
    state_cue: &'static LazyLock<Re>,
    here_after: &'static LazyLock<Re>,
    suffix: (Key, &'static str),
    longest: HashMap<Key, usize>,
    both: HashSet<Key>,
}

struct Lexicons {
    families: Vec<Family>,
    ailment_keys: Lex,
    ailment_spans: HashMap<Key, usize>,
    ailment_names: Names,
    condition_names: Names,
    moods: Lex,
}

fn family(attribute: &'static str, nouns: &Ordered, states: &Ordered, cue: &'static LazyLock<Re>, state_cue: &'static LazyLock<Re>, here_after: &'static LazyLock<Re>, suffix: (&str, &'static str), stated: &Ordered) -> Family {
    let mut known = nouns.clone();
    known.extend(states);
    Family {
        attribute,
        nouns: nouns.lex(),
        states: states.lex(),
        known: known.keys.iter().map(|key| key.chars().collect()).collect(),
        cue,
        state_cue,
        here_after,
        suffix: (suffix.0.chars().collect(), suffix.1),
        longest: spans(known.keys.iter()),
        both: nouns.keys.iter().filter(|key| stated.has(key)).map(|key| key.chars().collect()).collect(),
    }
}

static LEXICONS: LazyLock<Lexicons> = LazyLock::new(|| {
    let t = &*TABLES;
    let mut known: StdSet<&str> = StdSet::new();
    for table in [&t.physical, &t.physical_states, &t.physical_tools, &t.mental, &t.mental_states, &t.mind_extra] {
        known.extend(table.keys.iter().map(|key| key.as_str()));
    }
    let wordnet_text: &'static str = Box::leak(data_file("wordnet_conditions.txt").into_boxed_str());
    let mut merged = Ordered::default();
    for name in wordnet_text.lines() {
        if !known.contains(name) {
            merged.insert(name.to_string(), "");
        }
    }
    for (organ, value) in ORGANS {
        for trouble in TROUBLES {
            merged.insert(format!("{organ} {trouble}"), value);
        }
    }
    merged.extend(&t.physical);
    for name in UNSPECIFIED {
        merged.insert(name.to_string(), "");
    }
    let conditions = inflected(&merged).filter(|name, _| !POLYSEMOUS.contains(&name));
    let physical_stated = inflected(&t.physical_states);
    let states = physical_stated.filter(|name, _| !conditions.has(name) && !POLYSEMOUS.contains(&name));
    let mut mind_base = t.mind_extra.clone();
    mind_base.extend(&t.mental_loose);
    let mind = inflected(&mind_base);
    let mind_stated = inflected(&t.mental_state_strict);
    let mind_states = mind_stated.filter(|name, _| !mind.has(name));
    let families = vec![
        family("physical_conditions", &conditions, &states, &NOUN_CUE, &STATE_CUE, &HERE_AFTER_PHYSICAL, ("itis", ""), &physical_stated),
        family("mental_and_developmental_conditions", &mind, &mind_states, &MIND_CUE, &MIND_STATE_CUE, &HERE_AFTER_MENTAL, ("phobia", ""), &mind_stated),
    ];
    let mut ailment_keys = Ordered::default();
    for (name, value) in COMMON {
        let chars: Vec<char> = name.chars().collect();
        let joined: Vec<String> = words(&chars).map(st).collect();
        ailment_keys.insert(joined.join(" "), value);
    }
    let mut condition_keys: Vec<&str> = Vec::new();
    for (table_a, table_b) in [(&conditions, &states), (&mind, &mind_states)] {
        condition_keys.extend(table_a.keys.iter().map(|key| key.as_str()));
        condition_keys.extend(table_b.keys.iter().map(|key| key.as_str()));
    }
    Lexicons {
        ailment_spans: spans(ailment_keys.keys.iter()),
        ailment_names: Names::new(ailment_keys.keys.iter().map(|key| key.as_str())),
        ailment_keys: ailment_keys.lex(),
        condition_names: Names::new(condition_keys),
        families,
        moods: pairs_lex(MOODS),
    }
});

fn pairs_lex(items: &[(&str, &'static str)]) -> Lex {
    items.iter().map(|(key, value)| (key.chars().collect(), *value)).collect()
}

const LANGUAGES: [&str; 7] = ["es", "pt", "fr", "de", "it", "nl", "pl"];
const LANGUAGE_WORDS: [&str; 7] = [
    "que los las por para pero muy una está también porque cuando tengo estoy del más como eso esto hay todo yo mi mis él ella nos",
    "que os por para mas muito uma está também porque quando tenho estou mais como isso isto tem sem tudo eu meu minha você não são",
    "que les mais très une est aussi parce quand j'ai suis comme ça cette tout je moi mes pas avec des du qui",
    "und ich nicht ist das der mit auch ein eine aber sehr habe mein meine wenn oder sich auf für noch nur wie",
    "che ma molto una anche perché quando sono più come questo tutto io mio mia della del gli il",
    "het een en ik niet voor maar ook heb mijn zijn je nog",
    "nie się jest że jak jestem mnie mój moja tak czy już po",
];
const ENGLISH_TYPES: &str = "the and is to of it you that in my this for was with but have are not be on just so what like me at they he she if do can";
const FOREIGN_CUES: [&str; 7] = [
    concat!(
        r"(?:soy|estoy) (?:una? )?(?:persona|hombre|mujer|chico|chica|tipo|alguien|paciente) (?:con|que tiene|que padece|que sufre de)|tengo|padezco(?: de)?|sufro(?: de| con)?|convivo con|vivo con|lucho contra|",
        r"me diagnosticaron(?: con| de)?|me han diagnosticado(?: con| de)?|fui diagnosticad[oa](?: con| de)?|estoy diagnosticad[oa](?: con| de)?|mis?|mí|(?:soy|estoy)(?: una?)?(?: (?:hombre|mujer|chico|chica|persona|tipo|paciente))?"
    ),
    concat!(
        r"(?:sou|estou) (?:uma? )?(?:pessoa|homem|mulher|cara|menino|menina|rapaz|garota|paciente) (?:com|que tem|que sofre de)|tenho|sofro(?: de| com)?|convivo com|vivo com|luto contra|fui diagnosticad[oa](?: com)?|",
        r"me diagnosticaram(?: com)?|meus?|minhas?|(?:sou|estou)(?: uma?)?(?: (?:homem|mulher|cara|menino|menina|rapaz|garota|pessoa|paciente))?"
    ),
    concat!(
        r"je suis (?:une? )?(?:personne|homme|femme|mec|fille|gars|patiente?) (?:avec|atteinte? (?:de|d'))|j'ai été diagnostiquée?(?: avec)?|je suis diagnostiquée?|j'ai|je souffre (?:de|d')|je vis avec|on m'a diagnostiqué|",
        r"mon|ma|mes|je suis(?: une?)?(?: (?:homme|femme|mec|fille|gars|personne|patiente?))?"
    ),
    concat!(
        r"ich bin (?:ein |eine )?(?:mensch|mann|frau|typ|person|patient|patientin) mit|(?:ich )?hab(?:e)?(?: ich)?|ich leide (?:an|unter)|leide ich (?:an|unter)|ich lebe mit|mein|meine|meinen|meinem|meiner|",
        r"(?:ich )?bin(?: ich)?(?: eine?)?(?: (?:mann|frau|typ|person|patient|patientin))?"
    ),
    concat!(
        r"sono (?:una? |un' )?(?:persona|uomo|donna|ragazzo|ragazza|paziente) (?:con|che ha|che soffre di)|sono stat[oa] diagnosticat[oa](?: con)?|ho|soffro di|convivo con|mi hanno diagnosticato|mi è stat[oa] diagnosticat[oa]|",
        r"(?:il |la |i |le )?(?:mio|mia|miei|mie)|sono(?: una?| un')?(?: (?:uomo|donna|ragazzo|ragazza|persona|paziente))?"
    ),
    r"ik ben (?:een )?(?:persoon|man|vrouw|jongen|meisje|patiënt) met|ik heb|heb ik|ik lijd aan|ik leef met|mijn|m'n|ik ben(?: een)?(?: (?:man|vrouw|jongen|meisje|persoon|patiënt))?|ben ik",
    r"mam|cierpię na|choruję na|zdiagnozowano u mnie|mój|moja|moje|jestem",
];
const FOREIGN_FILL: [&str; 7] = [
    r"un|una|el|la|los|las|mucha|mucho|muchos|muchas|algo de|un poco de|problemas de|problemas con|también|tambien|ya|severa|severo|grave|leve|fuerte",
    r"um|uma|o|a|os|as|muita|muito|problemas de|problemas com|também|tambem|já|grave|leve|forte",
    r"un|une|le|la|les|des|du|de|d'|l'|un peu de|beaucoup de|problèmes de|problèmes d'|aussi|déjà|grave|sévère|léger|légère|forte|fort",
    r"eine|einen|ein|einer|die|den|das|auch|schon|starke|starken|leichte|leichten|schwere|schweren|chronische|chronischen|probleme mit",
    r"un|una|uno|un'|il|la|lo|l'|i|le|gli|problemi di|problemi con|anche|già|grave|lieve|forte",
    r"een|de|het|ook|al|ernstige|lichte|chronische|last van|zware",
    r"też|już",
];
const FOREIGN_HEDGES: [&str; 7] = [
    r"no|nunca|jamás|ni|si|creo|creía|quizá|quizás|tal vez|ojalá|puede que|sospecho|como si",
    r"não|nao|nunca|jamais|nem|se|acho|achava|talvez|será|suspeito|como se",
    r"ne|n'|pas|jamais|si|peut-être|pense|crois|croyais|soupçonne|comme si",
    r"nicht|kein|keine|keinen|keiner|nie|niemals|wenn|falls|ob|vielleicht|glaube|denke|vermute|vermutlich|wahrscheinlich",
    r"non|mai|se|forse|credo|penso|pensavo|sospetto|come se",
    r"niet|geen|nooit|als|of|misschien|denk|geloof|vermoed|waarschijnlijk",
    r"nie|jeśli|jeżeli|może|chyba|myślę|podejrzewam",
];
const ENGLISH: u16 = 1 << 8;
const LANGUAGE_BITS: u16 = (1 << 7) - 1;
const FOREIGN_LINKS: [&str; 11] = [",", "/", "+", "&", "y", "e", "et", "und", "en", "i", "oraz"];

struct Language {
    labels: HashMap<Key, (&'static str, &'static str)>,
    longest: usize,
    cue: Re,
    hedge: Re,
    fills: HashSet<Key>,
    words: HashSet<Key>,
}

struct Foreign {
    languages: Vec<Language>,
    masks: HashMap<Key, u16>,
    links: HashSet<Key>,
}

fn keys(words: &str) -> HashSet<Key> {
    words.split_whitespace().map(|word| word.chars().collect()).collect()
}

static FOREIGN: LazyLock<Foreign> = LazyLock::new(|| {
    let t = &*TABLES;
    let text: &'static str = Box::leak(data_file("foreign_conditions.tsv").into_boxed_str());
    let mut labels: Vec<HashMap<Key, (&'static str, &'static str)>> = vec![HashMap::default(); LANGUAGES.len()];
    for line in text.lines() {
        let mut fields = line.split('\t');
        let (code, label, attribute, value) = (fields.next().unwrap(), fields.next().unwrap(), fields.next().unwrap(), fields.next().unwrap());
        if let Some(index) = LANGUAGES.iter().position(|known| *known == code) {
            labels[index].insert(label.chars().collect(), (attribute, value));
        }
    }
    let mut states: HashMap<Key, (&'static str, &'static str)> = HashMap::default();
    for table in [&t.foreign_mind_states, &t.foreign_mind_extra] {
        for (name, value) in table.iter() {
            states.insert(name.chars().collect(), ("mental_and_developmental_conditions", value));
        }
    }
    for (name, value) in t.foreign_body_states.iter() {
        states.insert(name.chars().collect(), ("physical_conditions", value));
    }
    let mut languages = Vec::new();
    for (index, table) in labels.into_iter().enumerate() {
        let mut table = table;
        for (name, pair) in &states {
            table.entry(name.clone()).or_insert(*pair);
        }
        let longest = table.keys().map(|label| label.iter().filter(|&&c| c == ' ').count() + 1).max().unwrap();
        languages.push(Language {
            labels: table,
            longest,
            cue: Re::new(&format!(r"(?<![\w'])(?:{})(?:\s+|(?<='))(?:(?:{})(?:\s+|(?<=')))*+", FOREIGN_CUES[index], FOREIGN_FILL[index])),
            hedge: Re::new(&format!(r"(?<![\w'])(?:{})(?![\w'])", FOREIGN_HEDGES[index])),
            fills: FOREIGN_FILL[index].split('|').filter(|word| !word.contains(' ')).map(|word| word.chars().collect()).collect(),
            words: keys(LANGUAGE_WORDS[index]),
        });
    }
    let mut masks: HashMap<Key, u16> = HashMap::default();
    for (index, language) in languages.iter().enumerate() {
        for word in &language.words {
            *masks.entry(word.clone()).or_default() |= 1 << index;
        }
    }
    for word in keys(ENGLISH_TYPES) {
        *masks.entry(word).or_default() |= ENGLISH;
    }
    Foreign { languages, masks, links: FOREIGN_LINKS.iter().map(|link| link.chars().collect()).collect() }
});

pub fn init() {
    LazyLock::force(&LEXICONS);
    LazyLock::force(&FOREIGN);
    for re in [&OTHER_PEOPLE, &GENERAL, &NAMED_OWNER, &MOOD_NAMES, &UNNAMED, &ASSESSED, &POSSESSOR, &ADDRESSED, &GENERIC, &ATTRIBUTIVE, &ASKING, &CAUSED, &FIRST_PERSON, &HEADS, &CROWD,
        &PAST_CUE, &DROPPED, &DIAGNOSED, &CAUSE, &KIN, &CANDIDATE, &HERE_BEFORE, &SELF_BEFORE, &SELF_AFTER, &DUAL_CUE, &CARRIED, &CARRIED_STATE, &CLAUSE_END,
        &LINK, &TRAIL, &SCOPE, &ASTROLOGY, &SENTENCE, &POSSESSIVE_HEDGE, &FOREIGN_END, &FOREIGN_TOKEN] {
        LazyLock::force(re);
    }
}

fn lookup(words: &[(usize, usize, &[char])], has: impl Fn(&[char]) -> bool, longest: &HashMap<Key, usize>, suffix: &[char]) -> Vec<(usize, usize, Key)> {
    let mut out = Vec::new();
    let mut after = 0;
    let mut buffer: Key = Vec::new();
    for index in 0..words.len() {
        let token = words[index].2;
        let span = longest.get(token);
        if span.is_none() && !(!suffix.is_empty() && token.ends_with(suffix)) {
            continue;
        }
        if index < after {
            continue;
        }
        let Some(&span) = span else {
            if token.len() > suffix.len() + 3 {
                out.push((words[index].0, words[index].1, token.to_vec()));
            }
            continue;
        };
        for size in (1..=span.min(words.len() - index)).rev() {
            buffer.clear();
            for (position, word) in words[index..index + size].iter().enumerate() {
                if position > 0 {
                    buffer.push(' ');
                }
                buffer.extend_from_slice(word.2);
            }
            if has(&buffer) {
                out.push((words[index].0, words[index + size - 1].1, buffer.clone()));
                after = index + size;
                break;
            }
        }
    }
    out
}

fn scoped(window: &[char]) -> usize {
    SCOPE.iter(window).map(|m| m.end()).max().unwrap_or(0)
}

fn unhedged(lowered: &[char], start: isize) -> bool {
    let position = if start < 0 { (lowered.len() as isize + start).max(0) as usize } else { start as usize };
    let window = &lowered[line_start(lowered, position)..position];
    let pattern: &Re = if starts_at(lowered, position, "my") { &POSSESSIVE_HEDGE } else { &OWN_HEDGE };
    !pattern.test_in(window, scoped(window), window.len())
}

fn caused(part: &[char], left: &[char], start: usize) -> Option<usize> {
    let cause = CAUSE.find(left)?;
    let size = cause.end() - cause.start();
    let main = &part[..start - size];
    let mut stop = main.len();
    while stop > 0 && is_space(main[stop - 1]) {
        stop -= 1;
    }
    let main = &main[..stop];
    let main = match main.iter().rposition(|&c| c == ' ') {
        Some(space) => &main[..space],
        None => main,
    };
    let main = &main[scoped(main)..];
    if FIRST_PERSON.test(main) && !KIN.test(main) {
        Some(size)
    } else {
        None
    }
}

re!(TRANSITIVE, r"\s+(?:it|them|this|that|these|those|the|my|your|his|her|their|all|both|some|any|its)\b");
re!(COUNTED, r"\d\s*$");
const ACUTE: [&str; 14] = ["stroke", "a stroke", "strokes", "a mini stroke", "aneurysm", "an aneurysm", "a brain aneurysm", "heart attack", "a heart attack", "heart attacks", "seizure", "a seizure", "seizures", "cardiac arrest"];
re!(HYPERBOLE, r"\b(?:thought i|felt like|feel like|feels like|feeling like|give myself|giving myself|gave myself|give me|gives me|giving me|gave me)\b[^.!?\n]*$");

fn size(m: Match) -> usize {
    m.end() - m.start()
}

fn owned(lowered: &[char], origin: usize, part: &[char], found: &mut Found, families: &[Family]) {
    if !CANDIDATE.test(part) {
        return;
    }
    let words = pieces(part);
    for family in families {
        let physical = family.attribute == "physical_conditions";
        let mental = !physical;
        let mut previous: Option<usize> = None;
        for (start, end, name) in lookup(&words, |key| family.known.contains(key), &family.longest, &family.suffix.0) {
            let noun = !family.states.contains_key(&name);
            let dual = family.both.contains(&name);
            if mental && eq(&name, "ocd") && INTENSIFIED.test(&part[..start]) {
                previous = None;
                continue;
            }
            if physical {
                if let Some(tail) = MENTAL_TAIL.search(part, start.saturating_sub(40), end) {
                    if tail.start() < start {
                        previous = None;
                        continue;
                    }
                }
            }
            let left = &part[start.saturating_sub(90)..start];
            let here = (if family.here_after.at(part, end).is_some() { HERE_BEFORE.find(left).map(size) } else { None })
                .or_else(|| if mental && SELF_AFTER.at(part, end).is_some() { SELF_BEFORE.find(left).map(size) } else { None });
            let carried = if contains(left, " and ") || contains(left, ", ") {
                (if noun { CARRIED.find(left).map(size) } else { None })
                    .or_else(|| if (dual || !noun) && CARRIED_STATE.test(left) { CLAUSE_END.at(part, end).map(size) } else { None })
            } else {
                None
            };
            let cue = (if noun { &family.cue } else { &family.state_cue }).find(left).map(size)
                .or(carried)
                .or_else(|| if dual { DUAL_CUE.find(left).map(size) } else { None })
                .or(here)
                .or_else(|| {
                    if physical && noun && family.nouns.get(&name).copied() != Some("") {
                        PAST_CUE.find(left).map(size).or_else(|| caused(part, left, start))
                    } else {
                        None
                    }
                });
            let begin: Option<isize> = match cue {
                Some(length) => Some(start as isize - length as isize),
                None => {
                    if (if noun { &DROPPED } else { &DIAGNOSED }).fullmatch(part, 0, start).is_some() {
                        Some(0)
                    } else {
                        None
                    }
                }
            };
            let chained = previous.map_or(false, |previous| LINK.fullmatch(part, previous, start).is_some());
            if (begin.is_some() || chained)
                && (here.is_some() || !noun || TRAIL.at(part, end).is_none())
                && (chained || unhedged(lowered, origin as isize + begin.unwrap()))
                && !quoted(lowered, origin + start)
                && !(physical && ACUTE.iter().any(|acute| eq(&name, acute)) && HYPERBOLE.test(left))
                && !(physical && eq(&name, "disabled") && TRANSITIVE.at(part, end).is_some())
                && !(physical && name.len() <= 3 && COUNTED.test(left))
            {
                let value = family.nouns.get(&name).or_else(|| family.states.get(&name)).copied().unwrap_or(family.suffix.1);
                if !value.is_empty() {
                    found.set(home(family.attribute, value), value, origin + start);
                }
                previous = Some(end);
            } else {
                previous = None;
            }
        }
    }
}

fn language(lowered: &[char]) -> Option<&'static Language> {
    let foreign = &*FOREIGN;
    let mut distinct: Vec<&[char]> = Vec::new();
    let mut counts = [0usize; LANGUAGES.len()];
    let mut order: Vec<usize> = Vec::new();
    let mut english = 0;
    for word in lowered.split(|&c| is_space(c)).filter(|word| !word.is_empty()) {
        let Some(&mask) = foreign.masks.get(word) else { continue };
        if mask & ENGLISH != 0 {
            english += 1;
        }
        if mask & LANGUAGE_BITS == 0 {
            continue;
        }
        if distinct.len() < 3 && !distinct.contains(&word) {
            distinct.push(word);
        }
        for index in 0..LANGUAGES.len() {
            if mask & (1 << index) != 0 {
                if counts[index] == 0 {
                    order.push(index);
                }
                counts[index] += 1;
            }
        }
    }
    if distinct.len() < 3 {
        return None;
    }
    let mut best = order[0];
    for &index in &order {
        if counts[index] > counts[best] {
            best = index;
        }
    }
    if counts[best] > english {
        Some(&foreign.languages[best])
    } else {
        None
    }
}

fn word_char(c: char) -> bool {
    if c.is_ascii() {
        c.is_ascii_alphanumeric() || c == '_'
    } else {
        is_word(c)
    }
}

fn run_char(c: char) -> bool {
    word_char(c) || matches!(c, '\'' | '/' | '+' | '-')
}

fn token_end(text: &[char], start: usize) -> usize {
    let mut index = start;
    while index < text.len() && word_char(text[index]) {
        index += 1;
    }
    while index + 1 < text.len() && text[index] == '\'' && word_char(text[index + 1]) {
        index += 1;
        while index < text.len() && word_char(text[index]) {
            index += 1;
        }
    }
    index
}

struct Spots<'a> {
    text: &'a [char],
    index: usize,
    marks: bool,
}

impl<'a> Iterator for Spots<'a> {
    type Item = (usize, usize, &'a [char]);

    fn next(&mut self) -> Option<Self::Item> {
        let text = self.text;
        while self.index < text.len() {
            let (c, start) = (text[self.index], self.index);
            if word_char(c) {
                self.index = token_end(text, start);
                return Some((start, self.index, &text[start..self.index]));
            }
            self.index += 1;
            if self.marks && matches!(c, '.' | '!' | '?' | '\n') {
                return Some((start, start + 1, &text[start..start + 1]));
            }
        }
        None
    }
}

fn spots(text: &[char], marks: bool) -> Spots<'_> {
    Spots { text, index: 0, marks }
}

fn pieces(text: &[char]) -> Vec<(usize, usize, &[char])> {
    let mut out = Vec::new();
    let mut index = 0;
    while index < text.len() {
        if !run_char(text[index]) {
            index += 1;
            continue;
        }
        let start = index;
        while index < text.len() && run_char(text[index]) {
            index += 1;
        }
        if index + 1 < text.len() && text[index] == '.' && is_decimal(text[index + 1]) {
            index += 1;
            while index < text.len() && is_decimal(text[index]) {
                index += 1;
            }
        }
        out.push((start, index, &text[start..index]));
    }
    out
}

fn runs(text: &[char]) -> impl Iterator<Item = &[char]> {
    text.split(|&c| !run_char(c)).filter(|run| !run.is_empty())
}

fn foreign(tongue: Option<&'static Language>, lowered: &[char], found: &mut Found) {
    let Some(language) = tongue else { return };
    let links = &FOREIGN.links;
    let mut buffer: Key = Vec::new();
    for m in language.cue.iter(lowered) {
        if language.hedge.test_in(lowered, clause(lowered, m.start()), m.start()) || asked(lowered, m.end()) || quoted(lowered, m.start()) {
            continue;
        }
        let stop = FOREIGN_END.find_from(lowered, m.end()).map_or(lowered.len(), |s| s.start());
        let tokens: Vec<&[char]> = FOREIGN_TOKEN.iter_in(lowered, m.end(), stop).map(|t| t.text()).collect();
        let mut index = 0;
        loop {
            let mut hit = None;
            for size in (1..=language.longest.min(tokens.len() - index)).rev() {
                buffer.clear();
                for (position, token) in tokens[index..index + size].iter().enumerate() {
                    if position > 0 {
                        buffer.push(' ');
                    }
                    buffer.extend_from_slice(token);
                }
                if let Some(pair) = language.labels.get(&buffer) {
                    hit = Some((size, *pair));
                    break;
                }
            }
            let Some((size, (attribute, value))) = hit else { break };
            if !value.is_empty() {
                found.set(home(attribute, value), value, m.start());
            }
            index += size;
            if index >= tokens.len() || !links.contains(tokens[index]) {
                break;
            }
            while index < tokens.len() && (links.contains(tokens[index]) || language.fills.contains(tokens[index])) {
                index += 1;
            }
        }
    }
}

fn pop(found: &mut Found, attribute: &str, value: &str) -> Option<usize> {
    let index = found.items.iter().position(|(a, v, _)| a == attribute && v == value)?;
    Some(found.items.remove(index).2)
}

fn words(text: &[char]) -> impl Iterator<Item = &[char]> {
    spots(text, false).map(|(_, _, word)| word)
}

pub fn ailments(lowered: &[char], found: &mut Found) {
    crate::medications::medications(lowered, found);
    let lexicons = &*LEXICONS;
    let tongue = language(lowered);
    let speaker = tongue.is_none() && FIRST_PERSON.test(lowered);
    let mooded = MOOD_NAMES.test(lowered);
    let moody = speaker && mooded;
    let sick = speaker && lexicons.ailment_names.within(|| words(lowered));
    let named = sick || mooded || SUFFIXES.iter().any(|suffix| lowered.windows(suffix.len()).any(|window| window == *suffix)) || lexicons.condition_names.within(|| runs(lowered));
    let spotted = if sick {
        let words: Vec<(usize, usize, &[char])> = spots(lowered, true).collect();
        lookup(&words, |key| lexicons.ailment_keys.contains_key(key), &lexicons.ailment_spans, &[])
    } else {
        Vec::new()
    };
    let mut cursor = 0;
    if named {
        for sentence in SENTENCE.iter(lowered) {
            let (origin, close) = (sentence.start(), sentence.end());
            let part = &lowered[origin..close];
            let mut here: Vec<(usize, usize, &Key)> = Vec::new();
            while cursor < spotted.len() && spotted[cursor].0 < close {
                here.push((spotted[cursor].0 - origin, spotted[cursor].1 - origin, &spotted[cursor].2));
                cursor += 1;
            }
            let asked = close < lowered.len() && lowered[close] == '?';
            match if asked { ASKING.find(part) } else { None } {
                Some(ask) => owned(lowered, origin, &part[..scoped(&part[..ask.start()])], found, &lexicons.families[..]),
                None => owned(lowered, origin, part, found, if asked { &lexicons.families[1..] } else { &lexicons.families[..] }),
            }
            if asked {
                continue;
            }
            let first = tongue.is_none() && FIRST_PERSON.test(part);
            let mood = first || moody && MOOD_NAMES.test(part);
            if !(mood || !here.is_empty()) || !first && CROWD.test(part) {
                continue;
            }
            let hedge = HEDGE.find(part).map(|m| m.end());
            let addressed = ADDRESSED.find(part).map(|m| m.end());
            let others = OTHER_PEOPLE.find(part).map(|m| m.start());
            for &(start, end, name) in &here {
                if others.is_some() || addressed.is_some() || hedge.map_or(false, |h| h <= start) {
                    break;
                }
                if quoted(lowered, origin + start) || NAMED_OWNER.test(&part[start.saturating_sub(30)..start]) || POSSESSOR.test_in(part, start.saturating_sub(50), start) || RELATIVE.test(&part[start.saturating_sub(30)..start]) || PREFIXED.test(&part[start.saturating_sub(6)..start]) || NEGATED.test(&part[start.saturating_sub(30)..start]) || GENERIC.at(part, end).is_some() || TRAIL.at(part, end).is_some() || HEADS.at(part, end).is_some() || name.len() <= 3 && COUNTED.test(&part[..start]) {
                    continue;
                }
                let value = lexicons.ailment_keys[name];
                if !value.is_empty() {
                    found.set("physical_conditions", value, origin + start);
                }
            }
            if !mood {
                continue;
            }
            for m in MOOD_NAMES.iter(part) {
                let at = m.start();
                if others.map_or(false, |o| o < at) || addressed.map_or(false, |a| a <= at) || hedge.map_or(false, |h| h <= at) {
                    break;
                }
                let key = m.group(1).unwrap();
                if eq(key, "ocd") && INTENSIFIED.test(&part[..at]) || NEGATED.test(&part[at.saturating_sub(30)..at]) {
                    continue;
                }
                let value = lexicons.moods[key];
                let after = m.end();
                let neuro = NEURO.contains(&value);
                if others.is_some() && !neuro {
                    continue;
                }
                if quoted(lowered, origin + at) || POSSESSOR.test_in(part, at.saturating_sub(50), at) || TRAIL.at(part, after).is_some() || ASSESSED.at(part, after).is_some()
                    || CAUSED.test_in(part, at.saturating_sub(40), at) || !first && !neuro || !neuro && GENERAL.test(&part[at.saturating_sub(20)..at])
                    || neuro && OBJECT.test(&part[at.saturating_sub(30)..at]) && !starts_at(part, after, " spectrum") || NAMED_OWNER.test(&part[at.saturating_sub(30)..at])
                {
                    continue;
                }
                let window = &part[..at];
                if OTHERS.test_in(window, scoped(window), window.len())
                    || neuro && (OWN_HEDGE.test_in(part, 0, at) || !first && GENERIC.at(part, after).is_some() || (eq(key, "autistic") || eq(key, "audhd")) && ATTRIBUTIVE.at(part, after).is_some())
                {
                    continue;
                }
                found.set("mental_and_developmental_conditions", value, origin + at);
            }
        }
    }
    if moody {
        if let Some(unnamed) = UNNAMED.find(lowered) {
            if !asked(lowered, unnamed.end()) && !HEDGE.test_in(lowered, clause(lowered, unnamed.start()), unnamed.start()) && !quoted(lowered, unnamed.start()) {
                let values: HashSet<&str> = MOOD_NAMES.iter(lowered).map(|m| lexicons.moods[m.group(1).unwrap()]).collect();
                if values.len() == 1 {
                    found.set("mental_and_developmental_conditions", values.into_iter().next().unwrap(), unnamed.start());
                }
            }
        }
    }
    foreign(tongue, lowered, found);
    if found.has("physical_conditions", "cancer") && ASTROLOGY.test(lowered) {
        pop(found, "physical_conditions", "cancer");
    }
    if found.has("physical_conditions", "pots") && POTTERY.test(lowered) {
        pop(found, "physical_conditions", "pots");
    }
    if ["type 1 diabetes", "type 2 diabetes", "lada diabetes", "prediabetes"].iter().any(|typed| found.has("physical_conditions", typed)) {
        pop(found, "physical_conditions", "diabetes (type unstated)");
    }
}
