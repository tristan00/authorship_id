use crate::lexicon::LEXICON;
use crate::nation_of;
use crate::patterns::S_NATION;
use claimcore::*;
use std::sync::LazyLock;

const GROUPS: &[&str] = &[
    "jewish", "ashkenazi", "sephardic", "sephardi", "mizrahi", "arab", "kurdish", "european", "scandinavian", "nordic", "slavic", "celtic", "middle eastern",
    "south asian", "east asian", "southeast asian", "native american", "indigenous", "romani", "latin american", "caribbean", "west indian", "polynesian",
];
const STEM: &str = r"(?:\b(?:i'm|im|i am|iam|i'?ve always been|i'?ve been)|\bam|(?<!himself )(?<!herself )(?<!themselves )(?<!identifies )(?<!identified )(?<!known )(?<!seen )(?<!described )(?<!considered )(?<!treated )(?<!labeled )\bas an?|(?:^|[.!?\n]\s*)being)";
const SOFT: &str = r"(?:(?:also|actually|just|technically|originally|both|all|partly|partially|mostly|mainly|largely|ethnically) )*";
const KIN: &str = r"(?:family|parents|ancestors|grandparents|mom|mum|mother|dad|father|(?:mom|mum|mother|dad|father)'s (?:side|family)|(?:maternal|paternal) (?:side|family|grandparents))";
const ANCESTRY: &str = r"(?:descent|heritage|ancestry|origin|origins|extraction|roots|background|blood|stock)";
const ENDED: &str = r"(?=\s*(?:$|[.,!;:)\n(]|and\b|but\b|so\b|too\b|though\b|myself\b))";

static ORIGIN: LazyLock<String> = LazyLock::new(|| format!("{}|{}", &*S_NATION, longest_first(GROUPS.iter().copied())));

static COUNTRIES: LazyLock<String> = LazyLock::new(|| {
    let names: Vec<String> = LEXICON.nodes.iter().filter(|(_, node)| node.entry.is_some_and(|entry| entry.kind == "country" && entry.flag.is_empty())).map(|(name, _)| name.iter().collect()).collect();
    longest_first(names.iter().map(|name| name.as_str()))
});

fn origin(word: Option<&[char]>) -> Option<String> {
    let word = word?;
    nation_of(Some(word)).map(String::from).or_else(|| {
        let name = st(word);
        GROUPS.contains(&name.as_str()).then_some(name)
    })
}

fn country(word: Option<&[char]>) -> Option<String> {
    LEXICON.nodes.get(word?).and_then(|node| node.entry).filter(|entry| entry.kind == "country").map(|entry| entry.country.trim_start_matches("the ").to_string())
}

pub fn rules() -> Vec<Rule> {
    let origin_names = &*ORIGIN;
    let countries = &*COUNTRIES;
    vec![
        needs(rule("heritage", &format!(
            r"(?:{STEM} {SOFT}(?:an? )?(?:(?!(?:fan|fans|lot|bit|couple|bunch|member|part|friend|friends|group|mix|with|to|for|married|dating|around|surrounded|one|some|many|most|all|proud)\b)(?!\w+ing\b)[\w-]+ ){{0,2}}?|(?:^|\n)\s*|[,;]\s*(?:but|though|and) )of (?:(?:mixed|partial|partly|part|half|some|mostly|primarily|predominantly|mainly|largely|full|pure|direct|recent) )?({origin_names})(?:[- ](?:american|canadian|british|australian))? {ANCESTRY}\b(?![\w-]| (?:sites?|month|food|cuisine|festivals?|films?|movies?|music|stories|story|products?|brands?|dishes|recipes?|people|men|women|folks|communit(?:y|ies)|kids|children|students|friends|famil(?:y|ies)|girls|guys|man|woman|person|individuals))"
        ), |m| origin(m.group(1)), hedge()), &["descent", "heritage", "ancestry", "origin", "extraction", "roots", "background", "blood", "stock"]),
        needs(rule("heritage", &format!(
            r"{STEM} {SOFT}(?:half|part|partly|partially|a quarter|quarter|one quarter|\d/\d|\d{{1,2}}(?:\.\d+)?\s?%)[- ]?({origin_names})(?![\w-])"
        ), |m| origin(m.group(1)), hedge()), &["half", "part", "quarter", "/", "%"]),
        needs(rule("heritage", &format!(
            r"{STEM} {SOFT}half[- ][\w-]+(?: [\w-]+)?\s*(?:[,/&+x]\s*)?(?:and\s+)?half[- ]({origin_names})(?![\w-])"
        ), |m| origin(m.group(1)), hedge()), &["half"]),
        needs(rule("heritage", &format!(
            r"{STEM} {SOFT}ethnically (?:an? )?(?:half[- ])?({origin_names})(?![\w-])|{STEM} {SOFT}({origin_names}) by (?:descent|blood|heritage|ancestry|ethnicity|background|origin)\b"
        ), |m| origin(m.first()), hedge()), &["ethnically", " by "]),
        needs(rule("heritage", &format!(
            r"(?:{STEM} |\bfellow )(?:(?:also|actually|just|a|an|proud|(?:first|second|third|\d(?:st|nd|rd|th))[- ]gen(?:eration)?) )*({origin_names})[- ](american|canadian|australian|brit|british)\b"
        ), |m| origin(m.group(1)).filter(|value| nation_of(m.group(2)) != Some(value.as_str())), hedge()), &["american", "canadian", "australian", "brit"]),
        needs(rule("heritage", &format!(
            r"\bmy (?:whole |entire |immediate |extended )?{KIN}(?: (?:both|all))? (?:is|are|was|were|came|come|comes|immigrated|emigrated|hails?|originated)(?: (?:originally|all|both|here|over))* (?:from|out of) (?:the )?({countries})(?![\w-])"
        ), |m| country(m.group(1)), hedge()), &["from", "out of"]),
        needs(rule("heritage", &format!(
            r"\bmy {KIN}(?: (?:both|all))? (?:is|are|was|were)(?: (?:both|all|also|originally|full|fully))* ({origin_names}){ENDED}"
        ), |m| origin(m.group(1)), hedge()), &["my "]),
        needs(rule("heritage", &format!(
            r"\bmy (?:own )?({origin_names}) (?:heritage|ancestry|roots|side|background|blood|ancestors|descent|genes|dna|great[- ]grandparents)\b|\b({origin_names}) on (?:my|both) (?:mom|mum|mother|dad|father|maternal|paternal)(?:'s|s)? sides?\b"
        ), |m| origin(m.first()), hedge()), &["heritage", "ancestry", "roots", "side", "background", "blood", "ancestors", "descent", "genes", "dna", "grandparents"]),
        needs(rule("heritage", &format!(
            r"\bi (?:also |do )?have (?:some |a lot of |a bit of |partial |distant |strong )?({origin_names}) (?:heritage|ancestry|roots|blood|ancestors)\b|{STEM} [^.!?\n]{{0,30}}?\bwith (?:some |partial |strong )?({origin_names}) (?:heritage|ancestry|roots|blood)\b"
        ), |m| origin(m.first()), hedge()), &["heritage", "ancestry", "roots", "blood", "ancestors"]),
    ]
}
