use std::collections::{BTreeSet, HashMap};

type Set = BTreeSet<String>;

const CAP: usize = 64;
const WIDTH: usize = 3;
const COMBINATIONS: usize = 27;
const LONGEST: usize = 12;

enum Item {
    Lit(char),
    Range(char, char),
    Digit,
    Space,
    Other,
}

enum Node {
    Lit(char),
    Class(Vec<Item>, bool),
    Empty,
    Unknown,
    Group(Vec<Vec<Node>>),
    Repeat(Box<Node>, u32, u32),
}

struct Parser {
    chars: Vec<char>,
    at: usize,
}

impl Parser {
    fn peek(&self) -> Option<char> {
        self.chars.get(self.at).copied()
    }

    fn alternatives(&mut self) -> Vec<Vec<Node>> {
        let mut all = vec![self.sequence()];
        while self.peek() == Some('|') {
            self.at += 1;
            all.push(self.sequence());
        }
        all
    }

    fn sequence(&mut self) -> Vec<Node> {
        let mut items = Vec::new();
        while let Some(c) = self.peek() {
            if c == '|' || c == ')' {
                break;
            }
            let atom = self.atom();
            let atom = self.quantified(atom);
            items.push(atom);
        }
        items
    }

    fn number(&mut self) -> Option<u32> {
        let start = self.at;
        while self.peek().map_or(false, |c| c.is_ascii_digit()) {
            self.at += 1;
        }
        if self.at == start {
            None
        } else {
            self.chars[start..self.at].iter().collect::<String>().parse().ok()
        }
    }

    fn quantified(&mut self, atom: Node) -> Node {
        let (low, high) = match self.peek() {
            Some('*') => {
                self.at += 1;
                (0, u32::MAX)
            }
            Some('+') => {
                self.at += 1;
                (1, u32::MAX)
            }
            Some('?') => {
                self.at += 1;
                (0, 1)
            }
            Some('{') => {
                let save = self.at;
                self.at += 1;
                let low = self.number();
                let bounds = if self.peek() == Some(',') {
                    self.at += 1;
                    let high = self.number();
                    if self.peek() == Some('}') { Some((low.unwrap_or(0), high.unwrap_or(u32::MAX))) } else { None }
                } else if self.peek() == Some('}') && low.is_some() {
                    Some((low.unwrap(), low.unwrap()))
                } else {
                    None
                };
                match bounds {
                    Some(b) => {
                        self.at += 1;
                        b
                    }
                    None => {
                        self.at = save;
                        return atom;
                    }
                }
            }
            _ => return atom,
        };
        if matches!(self.peek(), Some('?') | Some('+')) {
            self.at += 1;
        }
        Node::Repeat(Box::new(atom), low, high)
    }

    fn escape(&mut self, class: bool) -> Item {
        let c = self.peek().unwrap_or('\\');
        self.at += 1;
        match c {
            'd' => Item::Digit,
            's' => Item::Space,
            'n' => Item::Lit('\n'),
            't' => Item::Lit('\t'),
            'r' => Item::Lit('\r'),
            'f' => Item::Lit('\x0c'),
            'v' => Item::Lit('\x0b'),
            'a' => Item::Lit('\x07'),
            'b' if class => Item::Lit('\x08'),
            'x' => {
                let hex: String = self.chars[self.at..(self.at + 2).min(self.chars.len())].iter().collect();
                self.at += 2;
                u32::from_str_radix(&hex, 16).ok().and_then(char::from_u32).map_or(Item::Other, Item::Lit)
            }
            'u' => {
                let hex: String = self.chars[self.at..(self.at + 4).min(self.chars.len())].iter().collect();
                self.at += 4;
                u32::from_str_radix(&hex, 16).ok().and_then(char::from_u32).map_or(Item::Other, Item::Lit)
            }
            c if c.is_ascii_alphanumeric() => Item::Other,
            c => Item::Lit(c),
        }
    }

    fn atom(&mut self) -> Node {
        let c = self.peek().unwrap();
        self.at += 1;
        match c {
            '.' => Node::Unknown,
            '^' | '$' => Node::Empty,
            '[' => self.class(),
            '(' => self.group(),
            '\\' => {
                let next = self.peek().unwrap_or('\\');
                if matches!(next, 'b' | 'B' | 'A' | 'Z' | 'z' | 'G') {
                    self.at += 1;
                    return Node::Empty;
                }
                if next.is_ascii_digit() {
                    self.number();
                    return Node::Unknown;
                }
                match self.escape(false) {
                    Item::Lit(c) => Node::Lit(c),
                    Item::Digit => Node::Class(vec![Item::Digit], false),
                    Item::Space => Node::Class(vec![Item::Space], false),
                    _ => Node::Unknown,
                }
            }
            c => Node::Lit(c),
        }
    }

    fn class(&mut self) -> Node {
        let mut items = Vec::new();
        let negated = self.peek() == Some('^');
        if negated {
            self.at += 1;
        }
        let mut first = true;
        while let Some(c) = self.peek() {
            if c == ']' && !first {
                self.at += 1;
                break;
            }
            first = false;
            self.at += 1;
            let item = if c == '\\' { self.escape(true) } else { Item::Lit(c) };
            if let Item::Lit(low) = item {
                if self.peek() == Some('-') && self.chars.get(self.at + 1).map_or(false, |&n| n != ']') {
                    self.at += 1;
                    let next = self.peek().unwrap();
                    self.at += 1;
                    let high = if next == '\\' {
                        match self.escape(true) {
                            Item::Lit(h) => h,
                            _ => {
                                items.push(Item::Other);
                                continue;
                            }
                        }
                    } else {
                        next
                    };
                    items.push(Item::Range(low, high));
                    continue;
                }
            }
            items.push(item);
        }
        Node::Class(items, negated)
    }

    fn group(&mut self) -> Node {
        if self.peek() == Some('?') {
            self.at += 1;
            let kind = self.peek().unwrap_or(':');
            match kind {
                ':' | '>' => {
                    self.at += 1;
                }
                '=' | '!' => {
                    self.at += 1;
                    self.alternatives();
                    self.at += 1;
                    return Node::Empty;
                }
                '<' if matches!(self.chars.get(self.at + 1), Some('=') | Some('!')) => {
                    self.at += 2;
                    self.alternatives();
                    self.at += 1;
                    return Node::Empty;
                }
                'P' | '<' => {
                    if kind == 'P' && self.chars.get(self.at + 1) == Some(&'=') {
                        while self.peek().map_or(false, |c| c != ')') {
                            self.at += 1;
                        }
                        self.at += 1;
                        return Node::Unknown;
                    }
                    while self.peek().map_or(false, |c| c != '>') {
                        self.at += 1;
                    }
                    self.at += 1;
                }
                '#' => {
                    while self.peek().map_or(false, |c| c != ')') {
                        self.at += 1;
                    }
                    self.at += 1;
                    return Node::Empty;
                }
                _ => {
                    while self.peek().map_or(false, |c| c.is_ascii_alphabetic() || c == '-') {
                        self.at += 1;
                    }
                    if self.peek() == Some(')') {
                        self.at += 1;
                        return Node::Empty;
                    }
                    self.at += 1;
                }
            }
        }
        let inner = self.alternatives();
        self.at += 1;
        Node::Group(inner)
    }
}

thread_local! {
    static CASELESS: std::cell::Cell<bool> = const { std::cell::Cell::new(true) };
}

fn fold(c: char) -> Option<char> {
    if crate::text::is_decimal(c) {
        return Some('0');
    }
    if crate::text::is_space(c) {
        return Some(' ');
    }
    let lowered = match c {
        '\u{131}' | '\u{130}' => 'i',
        '\u{212a}' => 'k',
        '\u{17f}' => 's',
        _ if !CASELESS.with(|caseless| caseless.get()) => c,
        _ => {
            if !(c.is_ascii() || c.to_lowercase().eq(c.to_uppercase())) {
                return None;
            }
            let mut it = c.to_lowercase();
            let first = it.next().unwrap_or(c);
            if it.next().is_some() {
                return None;
            }
            first
        }
    };
    Some(if crate::text::is_decimal(lowered) { '0' } else if crate::text::is_space(lowered) { ' ' } else { lowered })
}

pub fn fold_char(c: char) -> char {
    if crate::text::is_decimal(c) {
        '0'
    } else if crate::text::is_space(c) {
        ' '
    } else {
        match c {
            '\u{131}' => 'i',
            '\u{17f}' => 's',
            '\u{212a}' => 'k',
            _ => c,
        }
    }
}

fn folded(chars: &[char]) -> Option<Set> {
    chars.iter().map(|&c| fold(c).map(|f| f.to_string())).collect()
}

fn single() -> Set {
    let mut set = Set::new();
    set.insert(String::new());
    set
}

fn product(left: &Option<Set>, right: &Option<Set>) -> Option<Set> {
    let (left, right) = (left.as_ref()?, right.as_ref()?);
    if left.len() * right.len() > CAP {
        return None;
    }
    Some(left.iter().flat_map(|a| right.iter().map(move |b| format!("{a}{b}"))).collect())
}

fn charset(items: &[Item], negated: bool) -> Option<Set> {
    if negated {
        return None;
    }
    let mut found = Vec::new();
    for item in items {
        match item {
            Item::Lit(c) => found.push(*c),
            Item::Range(a, b) if (*b as u32).saturating_sub(*a as u32) < 16 && *a <= *b => {
                for code in *a as u32..=*b as u32 {
                    found.push(char::from_u32(code)?);
                }
            }
            Item::Digit => found.push('0'),
            Item::Space => found.push(' '),
            _ => return None,
        }
    }
    folded(&found)
}

fn usable(group: &Set) -> bool {
    !group.is_empty() && !group.contains("")
}

fn strength(option: &str) -> usize {
    option.chars().filter(|c| !c.is_whitespace()).map(|c| if c.is_alphabetic() { 1 } else { 2 }).sum()
}

fn quality(group: &Set) -> (usize, isize) {
    if usable(group) {
        (group.iter().map(|o| strength(o)).min().unwrap_or(0), -(group.len() as isize))
    } else {
        (0, 0)
    }
}

fn ranked(exact: &Option<Set>, groups: &[Set]) -> Vec<Set> {
    let mut all: Vec<Set> = groups.iter().cloned().collect();
    if let Some(e) = exact {
        all.push(e.clone());
    }
    all.retain(usable);
    all.sort();
    all.dedup();
    all.sort_by_key(|g| std::cmp::Reverse(quality(g)));
    all.truncate(WIDTH);
    all
}

fn either(parts: &[(Option<Set>, Vec<Set>)]) -> Vec<Set> {
    let choices: Vec<Vec<Set>> = parts.iter().map(|(e, g)| ranked(e, g)).collect();
    if choices.iter().any(|c| c.is_empty()) {
        return Vec::new();
    }
    let mut combinations: Vec<Vec<&Set>> = vec![Vec::new()];
    for options in &choices {
        let mut next = Vec::new();
        for combination in &combinations {
            for option in options {
                let mut extended = combination.clone();
                extended.push(option);
                next.push(extended);
            }
        }
        combinations = next;
        if combinations.len() > COMBINATIONS {
            let mut union = Set::new();
            for options in &choices {
                union.extend(options[0].iter().cloned());
            }
            return vec![union];
        }
    }
    combinations.into_iter().map(|c| c.into_iter().flat_map(|s| s.iter().cloned()).collect()).collect()
}

fn node(item: &Node) -> (Option<Set>, Vec<Set>) {
    match item {
        Node::Lit(c) => (folded(&[*c]), Vec::new()),
        Node::Class(items, negated) => (charset(items, *negated), Vec::new()),
        Node::Empty => (Some(single()), Vec::new()),
        Node::Unknown => (None, Vec::new()),
        Node::Group(alternatives) => branch(alternatives),
        Node::Repeat(inner, low, high) => {
            let (exact, groups) = node(inner);
            if *low == 0 {
                return (if *high == 1 { exact.map(|mut e| { e.insert(String::new()); e }) } else { None }, Vec::new());
            }
            if *low == 1 && *high == 1 {
                return (exact, groups);
            }
            if low == high && exact.is_some() {
                let mut joined = Some(single());
                for _ in 0..*low {
                    joined = product(&joined, &exact);
                }
                if joined.is_some() {
                    return (joined, groups);
                }
            }
            let mut groups = groups;
            if let Some(e) = exact {
                groups.push(e);
            }
            (None, groups)
        }
    }
}

fn branch(alternatives: &[Vec<Node>]) -> (Option<Set>, Vec<Set>) {
    if alternatives.len() == 1 {
        return sequence(&alternatives[0]);
    }
    let parts: Vec<(Option<Set>, Vec<Set>)> = alternatives.iter().map(|a| sequence(a)).collect();
    let exact = if parts.iter().all(|(e, _)| e.is_some()) {
        let union: Set = parts.iter().flat_map(|(e, _)| e.as_ref().unwrap().iter().cloned()).collect();
        if union.len() <= CAP { Some(union) } else { None }
    } else {
        None
    };
    (exact, either(&parts))
}

fn sequence(items: &[Node]) -> (Option<Set>, Vec<Set>) {
    let mut current = Some(single());
    let mut groups = Vec::new();
    let mut whole = true;
    for item in items {
        let (exact, inner) = node(item);
        groups.extend(inner);
        let joined = product(&current, &exact);
        if joined.is_none() {
            groups.push(current.take().unwrap_or_else(single));
            current = Some(exact.unwrap_or_else(single));
            whole = false;
        } else {
            current = joined;
        }
    }
    if whole {
        return (current, groups);
    }
    groups.push(current.unwrap_or_else(single));
    (None, groups)
}

fn caseless(pattern: &str, flags: u32) -> bool {
    if flags & crate::re::I != 0 {
        return true;
    }
    let chars: Vec<char> = pattern.chars().collect();
    (0..chars.len().saturating_sub(2)).any(|i| chars[i] == '(' && chars[i + 1] == '?' && chars[i + 2..].iter().take_while(|c| c.is_ascii_alphabetic()).any(|&c| c == 'i'))
}

pub fn requirements(pattern: &str, flags: u32) -> Option<Vec<Vec<Vec<String>>>> {
    CASELESS.with(|c| c.set(caseless(pattern, flags)));
    let mut parser = Parser { chars: pattern.chars().collect(), at: 0 };
    let tree = parser.alternatives();
    if parser.at < parser.chars.len() {
        return None;
    }
    let mut options = Vec::new();
    for alternative in &tree {
        let (exact, mut groups) = sequence(alternative);
        if let Some(e) = exact {
            groups.push(e);
        }
        let mut kept: Vec<Vec<String>> = groups.into_iter().filter(|g| usable(g) && g.iter().map(|o| strength(o)).min().unwrap_or(0) >= 2).map(|g| g.into_iter().collect()).collect();
        if kept.is_empty() {
            return None;
        }
        kept.sort();
        kept.dedup();
        options.push(kept);
    }
    Some(options)
}

struct Need {
    gate: Option<u32>,
    options: Option<Vec<Vec<u32>>>,
}

pub struct Literals {
    automaton: aho_corasick::AhoCorasick,
    owners: Vec<Vec<u32>>,
    needs: Vec<Need>,
    groups: usize,
}

pub fn folded_text(lowered: &[char]) -> String {
    let mut out = String::with_capacity(lowered.len() + 8);
    for &c in lowered {
        if c.is_ascii() {
            out.push(if c.is_ascii_digit() { '0' } else if matches!(c, '\t'..='\r' | '\x1c'..='\x1f') { ' ' } else { c });
        } else {
            out.push(fold_char(c));
        }
    }
    out
}

struct Builder {
    ids: HashMap<String, usize>,
    words: Vec<String>,
    owners: Vec<Vec<u32>>,
    groups: u32,
}

impl Builder {
    fn group(&mut self, words: impl IntoIterator<Item = String>) -> u32 {
        let group = self.groups;
        self.groups += 1;
        for word in words {
            let word: String = word.chars().take(LONGEST).collect();
            let id = match self.ids.get(&word) {
                Some(&id) => id,
                None => {
                    self.ids.insert(word.clone(), self.words.len());
                    self.words.push(word);
                    self.owners.push(Vec::new());
                    self.words.len() - 1
                }
            };
            if self.owners[id].last() != Some(&group) {
                self.owners[id].push(group);
            }
        }
        group
    }
}

impl Literals {
    pub fn new(patterns: &[(&str, u32, Option<&[Vec<char>]>)]) -> Literals {
        let mut builder = Builder { ids: HashMap::new(), words: Vec::new(), owners: Vec::new(), groups: 0 };
        let mut needs = Vec::new();
        for (pattern, flags, gate) in patterns {
            let options = requirements(pattern, *flags).map(|options| options.into_iter().map(|groups| groups.into_iter().map(|group| builder.group(group)).collect()).collect());
            let gate = gate.map(|anchors| builder.group(anchors.iter().map(|anchor| folded_text(anchor))));
            needs.push(Need { gate, options });
        }
        let automaton = aho_corasick::AhoCorasick::builder().kind(Some(aho_corasick::AhoCorasickKind::ContiguousNFA)).build(&builder.words).unwrap();
        Literals { automaton, owners: builder.owners, needs, groups: builder.groups as usize }
    }

    pub fn possible(&self, lowered: &[char]) -> Vec<bool> {
        let folded = folded_text(lowered);
        let mut seen: Vec<u32> = Vec::with_capacity(64);
        let mut hit = vec![false; self.groups];
        for found in self.automaton.find_overlapping_iter(&folded) {
            let id = found.pattern().as_u32();
            if !seen.contains(&id) {
                seen.push(id);
                for &group in &self.owners[id as usize] {
                    hit[group as usize] = true;
                }
            }
        }
        self.needs.iter().map(|need| {
            need.gate.map_or(true, |g| hit[g as usize]) && need.options.as_ref().map_or(true, |options| options.iter().any(|groups| groups.iter().all(|&g| hit[g as usize])))
        }).collect()
    }
}
