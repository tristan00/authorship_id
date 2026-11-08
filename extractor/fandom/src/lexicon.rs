use claimcore::*;
use rustc_hash::{FxHashMap, FxHashSet};
use std::sync::LazyLock;
use unicode_normalization::char::canonical_combining_class;
use unicode_normalization::UnicodeNormalization;

pub type Map<V> = FxHashMap<&'static str, V>;

#[derive(Clone, Copy)]
pub struct Entry {
    pub attribute: &'static str,
    pub value: &'static str,
    pub links: u32,
    pub cased: bool,
    pub common: bool,
}

pub const ATTRIBUTES: [&str; 9] = ["sports_team", "athlete", "artist", "author", "character", "franchise", "video_game", "creator", "celebrity"];
pub const SHORT_KEY: usize = 3;
pub const FAMOUS_SITELINKS: u32 = 40;
pub const TITLES: [&str; 2] = ["franchise", "video_game"];

const NFL_TEAMS_2025: &str = "arizona cardinals;atlanta falcons|Falcons;baltimore ravens|Ravens;buffalo bills|Bills;carolina panthers;chicago bears|Bears;cincinnati bengals|Bengals;cleveland browns|Browns;
dallas cowboys|Cowboys;denver broncos|Broncos;detroit lions|Lions;green bay packers|Packers;houston texans|Texans;indianapolis colts|Colts;jacksonville jaguars|Jaguars;
kansas city chiefs|Chiefs;las vegas raiders|oakland raiders|Raiders;los angeles chargers|Chargers;los angeles rams|Rams;miami dolphins|Dolphins;minnesota vikings|Vikings;
new england patriots|Patriots;new orleans saints|Saints;new york giants|Giants;new york jets|Jets;philadelphia eagles|Eagles;pittsburgh steelers|Steelers;
san francisco 49ers|49ers;seattle seahawks|Seahawks;tampa bay buccaneers|Buccaneers;tennessee titans|Titans;washington commanders|Commanders";
const NBA_TEAMS_2025: &str = "atlanta hawks|Hawks;boston celtics|Celtics;brooklyn nets|Nets;charlotte hornets|Hornets;chicago bulls|Bulls;cleveland cavaliers|Cavaliers;dallas mavericks|Mavericks;
denver nuggets|Nuggets;detroit pistons|Pistons;golden state warriors|Warriors;houston rockets|Rockets;indiana pacers|Pacers;la clippers|los angeles clippers|Clippers;
los angeles lakers|Lakers;memphis grizzlies|Grizzlies;miami heat;milwaukee bucks|Bucks;minnesota timberwolves|Timberwolves;new orleans pelicans|Pelicans;new york knicks|Knicks;
oklahoma city thunder;orlando magic;philadelphia 76ers|76ers;phoenix suns|Suns;portland trail blazers|trail blazers|Blazers;sacramento kings|Kings;san antonio spurs|Spurs;
toronto raptors|Raptors;utah jazz;washington wizards|Wizards";
const MLB_TEAMS_2025: &str = "arizona diamondbacks|Diamondbacks;atlanta braves|Braves;baltimore orioles|Orioles;boston red sox|red sox;chicago cubs|Cubs;chicago white sox|white sox;
cincinnati reds|Reds;cleveland guardians|Guardians;colorado rockies|Rockies;detroit tigers|Tigers;houston astros|Astros;kansas city royals|Royals;los angeles angels|Angels;
los angeles dodgers|Dodgers;miami marlins|Marlins;milwaukee brewers|Brewers;minnesota twins|Twins;new york mets|Mets;new york yankees|Yankees;athletics|oakland athletics;
philadelphia phillies|Phillies;pittsburgh pirates|Pirates;san diego padres|Padres;san francisco giants|Giants;seattle mariners|Mariners;st. louis cardinals|Cardinals;
tampa bay rays|Rays;texas rangers|Rangers;toronto blue jays|blue jays|Jays;washington nationals|Nationals";
const NHL_TEAMS_2025: &str = "anaheim ducks|Ducks;boston bruins|Bruins;buffalo sabres|Sabres;calgary flames|Flames;carolina hurricanes|Hurricanes;chicago blackhawks|Blackhawks;
colorado avalanche|Avalanche;columbus blue jackets|blue jackets;dallas stars|Stars;detroit red wings|red wings;edmonton oilers|Oilers;florida panthers|Panthers;
los angeles kings|Kings;minnesota wild;montreal canadiens|Canadiens;nashville predators|Predators;new jersey devils|Devils;new york islanders|Islanders;
new york rangers|Rangers;ottawa senators|Senators;philadelphia flyers|Flyers;pittsburgh penguins|Penguins;san jose sharks|Sharks;seattle kraken|Kraken;
st. louis blues|Blues;tampa bay lightning|Lightning;toronto maple leafs|maple leafs|Leafs;utah mammoth|utah hockey club;vancouver canucks|Canucks;
vegas golden knights|golden knights;washington capitals|Capitals;winnipeg jets|Jets";
const MLS_TEAMS_2025: &str = "atlanta united;austin fc;charlotte fc;chicago fire fc;fc cincinnati;colorado rapids;columbus crew;d.c. united|dc united;fc dallas;houston dynamo;inter miami;la galaxy;
los angeles fc;minnesota united;cf montréal|cf montreal;nashville sc;new england revolution;new york city fc;new york red bulls;orlando city;philadelphia union;
portland timbers|Timbers;real salt lake;san diego fc;san jose earthquakes;seattle sounders|Sounders;sporting kansas city;st. louis city sc;toronto fc;vancouver whitecaps|Whitecaps";
const PREMIER_LEAGUE_TEAMS_2025: &str = "arsenal|Arsenal;aston villa;bournemouth|Bournemouth;brentford|Brentford;brighton & hove albion|brighton and hove albion;burnley|Burnley;
chelsea|Chelsea;crystal palace;everton|Everton;fulham|Fulham;leeds united;liverpool|Liverpool;manchester city;manchester united;
newcastle united;nottingham forest;sunderland|Sunderland;tottenham hotspur;west ham united;wolverhampton wanderers";
const LA_LIGA_TEAMS_2025: &str = "deportivo alavés|Alavés;athletic bilbao|athletic club;atlético madrid|atletico madrid;fc barcelona|Barcelona;celta vigo;elche|Elche;
espanyol|Espanyol;getafe|Getafe;girona|Girona;levante|Levante;mallorca|Mallorca;osasuna|Osasuna;rayo vallecano;real betis|Betis;real madrid;real oviedo;real sociedad;
sevilla|Sevilla;valencia|Valencia;villarreal|Villarreal";
const SERIE_A_TEAMS_2025: &str = "atalanta|Atalanta;bologna|Bologna;cagliari|Cagliari;como|Como;cremonese|Cremonese;fiorentina|Fiorentina;genoa|Genoa;hellas verona|Verona;inter milan|internazionale;
juventus|Juventus;lazio|Lazio;lecce|Lecce;ac milan|Milan;napoli|Napoli;parma|Parma;pisa|Pisa;as roma|Roma;sassuolo|Sassuolo;torino|Torino;udinese|Udinese";
const BUNDESLIGA_TEAMS_2025: &str = "fc augsburg|Augsburg;union berlin;werder bremen|Bremen;borussia dortmund|Dortmund;eintracht frankfurt;sc freiburg|Freiburg;hamburger sv;1. fc heidenheim|Heidenheim;
tsg hoffenheim|Hoffenheim;1. fc köln|fc köln|fc koln;rb leipzig|Leipzig;bayer leverkusen|Leverkusen;mainz 05;borussia mönchengladbach|mönchengladbach;
bayern munich|bayern münchen;fc st. pauli|St. Pauli;vfb stuttgart|Stuttgart;vfl wolfsburg|Wolfsburg";
const LIGUE_1_TEAMS_2025: &str = "angers|Angers;auxerre|Auxerre;stade brestois;le havre;rc lens|Lens;lille|Lille;lorient|Lorient;olympique lyonnais;olympique de marseille|Marseille;
metz|Metz;as monaco|Monaco;nantes|Nantes;ogc nice;paris fc;paris saint-germain;stade rennais;strasbourg|Strasbourg;toulouse|Toulouse";
const IPL_TEAMS_2025: &str = "chennai super kings;delhi capitals;gujarat titans;kolkata knight riders;lucknow super giants;mumbai indians;punjab kings;rajasthan royals;
royal challengers bengaluru|royal challengers bangalore;sunrisers hyderabad";
const TEAMS: [&str; 11] = [NFL_TEAMS_2025, NBA_TEAMS_2025, MLB_TEAMS_2025, NHL_TEAMS_2025, MLS_TEAMS_2025, PREMIER_LEAGUE_TEAMS_2025, LA_LIGA_TEAMS_2025, SERIE_A_TEAMS_2025,
    BUNDESLIGA_TEAMS_2025, LIGUE_1_TEAMS_2025, IPL_TEAMS_2025];

pub fn leak(s: String) -> &'static str {
    Box::leak(s.into_boxed_str())
}

fn leaked_file(name: &str) -> &'static str {
    leak(data_file(name))
}

fn rows(name: &str) -> impl Iterator<Item = &'static str> {
    leaked_file(name).lines().skip(1)
}

pub fn attribute_name(name: &str) -> &'static str {
    ATTRIBUTES.iter().copied().find(|a| *a == name).unwrap_or_else(|| leak(name.to_string()))
}

pub fn is_word_char(c: char) -> bool {
    if c.is_ascii() {
        c.is_ascii_alphanumeric() || c == '_'
    } else {
        is_word(c)
    }
}

pub fn is_letter(c: char) -> bool {
    if c.is_ascii() {
        c.is_ascii_alphabetic()
    } else {
        is_word(c) && !is_decimal(c)
    }
}

pub fn two_letters(s: &[char]) -> bool {
    s.windows(2).any(|pair| is_letter(pair[0]) && is_letter(pair[1]))
}

pub fn word_spans(s: &[char]) -> Vec<(usize, usize)> {
    let mut spans = Vec::new();
    let mut index = 0;
    while index < s.len() {
        if is_word_char(s[index]) {
            let start = index;
            while index < s.len() && is_word_char(s[index]) {
                index += 1;
            }
            spans.push((start, index));
        } else {
            index += 1;
        }
    }
    spans
}

pub fn joined_words(s: &[char]) -> String {
    let mut out = String::with_capacity(s.len());
    for (a, b) in word_spans(s) {
        if !out.is_empty() {
            out.push(' ');
        }
        out.extend(&s[a..b]);
    }
    out
}

pub fn folded(s: &str) -> String {
    if s.is_ascii() {
        return s.to_string();
    }
    s.nfkd().filter(|&c| canonical_combining_class(c) == 0).collect()
}

pub fn folded_chars(s: &[char]) -> Vec<char> {
    if s.iter().all(|c| c.is_ascii()) {
        return s.to_vec();
    }
    s.iter().copied().nfkd().filter(|&c| canonical_combining_class(c) == 0).collect()
}

pub fn has_digit(s: &str) -> bool {
    s.chars().any(|c| isdigit(&[c]))
}

fn team_entries() -> Vec<(&'static str, Vec<&'static str>)> {
    let mut entries = Vec::new();
    for block in TEAMS {
        let joined: &'static str = leak(block.replace('\n', ""));
        for piece in joined.split(';') {
            let piece = piece.trim();
            if piece.is_empty() {
                continue;
            }
            let mut forms = piece.split('|');
            let head = forms.next().unwrap();
            entries.push((head, forms.collect()));
        }
    }
    entries
}

fn str_words(s: &str) -> Vec<String> {
    let chars: Vec<char> = s.chars().collect();
    word_spans(&chars).into_iter().map(|(a, b)| chars[a..b].iter().collect()).collect()
}

pub struct Lexicon {
    pub plain: Map<Vec<Entry>>,
    pub cased: Map<Vec<Entry>>,
    pub film_plain: Map<Vec<Entry>>,
    pub film_cased: Map<Vec<Entry>>,
    pub raised: Map<Vec<Entry>>,
    pub sentence_cased: Map<Vec<Entry>>,
    pub team_words: Map<&'static str>,
    pub team_span: usize,
    pub author_of_book: Map<&'static str>,
    pub series_of_game: Map<&'static str>,
    pub places: FxHashSet<&'static str>,
}

fn read(name: &str, plain: &mut Map<Vec<Entry>>, cased: &mut Map<Vec<Entry>>, order: &mut Vec<&'static str>) {
    for line in rows(name) {
        let mut fields = line.split('\t');
        let key = fields.next().unwrap();
        let attribute = attribute_name(fields.next().unwrap());
        let value = fields.next().unwrap();
        let links: u32 = fields.next().unwrap().parse().unwrap();
        let surfaces = fields.next().unwrap();
        let common = fields.next().unwrap() == "1";
        let size = key.chars().count();
        if !surfaces.is_empty() {
            let keychars: Vec<char> = key.chars().collect();
            let entry = Entry { attribute, value, links, cased: true, common: common || size <= SHORT_KEY && !(has_digit(key) && two_letters(&keychars)) };
            for surface in surfaces.split('|') {
                let list = cased.entry(surface).or_insert_with(|| {
                    order.push(surface);
                    Vec::new()
                });
                list.push(entry);
            }
        }
        if surfaces.is_empty() || (attribute == "video_game" && common && key.strip_prefix("the ").unwrap_or(key).contains(' ')) {
            plain.entry(key).or_default().push(Entry { attribute, value, links, cased: false, common: common || size <= SHORT_KEY });
        }
    }
}

fn lowered_static(s: &'static str) -> &'static str {
    if s.bytes().all(|b| b.is_ascii() && !b.is_ascii_uppercase()) {
        return s;
    }
    let low = s.to_lowercase();
    if low == s {
        s
    } else {
        leak(low)
    }
}

fn team_words(clubs_file: &str) -> Map<&'static str> {
    let mut words: FxHashMap<String, Vec<String>> = FxHashMap::default();
    let mut word_order: Vec<String> = Vec::new();
    let mut places: FxHashMap<String, Vec<String>> = FxHashMap::default();
    let mut place_order: Vec<String> = Vec::new();
    fn add(map: &mut FxHashMap<String, Vec<String>>, order: &mut Vec<String>, key: String, head: String) {
        let list = map.entry(key.clone()).or_insert_with(|| {
            order.push(key);
            Vec::new()
        });
        if !list.contains(&head) {
            list.push(head);
        }
    }
    for (head, aliases) in team_entries() {
        let tokens = str_words(head);
        let last = tokens.last().unwrap().clone();
        let mut forms: Vec<&str> = vec![head];
        forms.extend(aliases.iter().copied());
        forms.push(&last);
        for form in forms {
            let key = str_words(&folded(form)).join(" ").to_lowercase();
            let mut variants = vec![key.clone()];
            if key.ends_with('s') && !key.contains(' ') && key.chars().count() > 4 {
                let mut shorter = key.clone();
                shorter.pop();
                variants.push(shorter);
            }
            for variant in variants {
                add(&mut words, &mut word_order, variant, head.to_lowercase());
            }
        }
        if tokens.len() > 1 {
            let key = str_words(&folded(&tokens[..tokens.len() - 1].join(" "))).join(" ").to_lowercase();
            add(&mut places, &mut place_order, key, head.to_lowercase());
        }
    }
    let mut table: Map<&'static str> = FxHashMap::default();
    for line in rows(clubs_file) {
        let mut fields = line.split('\t');
        let key = fields.next().unwrap();
        fields.next();
        let value = fields.next().unwrap();
        table.insert(key, value);
    }
    for key in &word_order {
        let heads = &words[key];
        let value = if heads.len() == 1 { leak(heads[0].clone()) } else { leak(key.clone()) };
        table.insert(leak(key.clone()), value);
    }
    for key in &place_order {
        let heads = &places[key];
        if heads.len() == 1 && !words.contains_key(key) {
            table.insert(leak(key.clone()), leak(heads[0].clone()));
        }
    }
    table
}

fn pairs(name: &str) -> Map<&'static str> {
    let mut table: Map<&'static str> = FxHashMap::default();
    for line in rows(name) {
        let (a, b) = line.split_once('\t').unwrap();
        table.insert(a, b);
    }
    table
}

fn titled_first(surface: &str) -> String {
    let low = surface.to_lowercase();
    capitalize(&low)
}

pub fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => {
            let mut out: String = title_char(first);
            out.push_str(&chars.as_str().to_lowercase());
            out
        }
    }
}

pub fn title_char(c: char) -> String {
    match c {
        '\u{1c4}' | '\u{1c5}' | '\u{1c6}' => "\u{1c5}".to_string(),
        '\u{1c7}' | '\u{1c8}' | '\u{1c9}' => "\u{1c8}".to_string(),
        '\u{1ca}' | '\u{1cb}' | '\u{1cc}' => "\u{1cb}".to_string(),
        '\u{1f1}' | '\u{1f2}' | '\u{1f3}' => "\u{1f2}".to_string(),
        'ß' => "Ss".to_string(),
        _ => c.to_uppercase().collect(),
    }
}

pub fn title(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut previous = false;
    for c in s.chars() {
        if previous {
            out.extend(c.to_lowercase());
        } else {
            out.push_str(&title_char(c));
        }
        previous = is_cased(c);
    }
    out
}

fn build() -> Lexicon {
    let mut teams: FxHashMap<String, Vec<String>> = FxHashMap::default();
    for (head, aliases) in team_entries() {
        let mut variants: Vec<String> = Vec::new();
        for alias in std::iter::once(head).chain(aliases.iter().copied()) {
            for form in [alias.to_string(), folded(alias)] {
                if !variants.contains(&form) {
                    variants.push(form);
                }
            }
        }
        for variant in variants {
            let tokens = str_words(&variant);
            let single = tokens.iter().filter(|t| t.to_lowercase() != "the").count() == 1;
            if !(single && variant == variant.to_lowercase()) {
                let list = teams.entry(tokens.join(" ").to_lowercase()).or_default();
                let head = head.to_lowercase();
                if !list.contains(&head) {
                    list.push(head);
                }
            }
        }
    }
    let mut plain: Map<Vec<Entry>> = FxHashMap::default();
    for (key, values) in teams {
        if values.len() == 1 {
            plain.entry(leak(key)).or_default().push(Entry { attribute: "sports_team", value: leak(values[0].clone()), links: 0, cased: false, common: false });
        }
    }
    let mut cased: Map<Vec<Entry>> = FxHashMap::default();
    let mut order: Vec<&'static str> = Vec::new();
    read("knowledge.tsv", &mut plain, &mut cased, &mut order);
    let mut film_plain: Map<Vec<Entry>> = FxHashMap::default();
    let mut film_cased: Map<Vec<Entry>> = FxHashMap::default();
    let mut film_order = Vec::new();
    read("films.tsv", &mut film_plain, &mut film_cased, &mut film_order);
    let nonword: FxHashSet<&'static str> = rows("nonword_titles.tsv").collect();
    let mut raised: Map<Vec<Entry>> = FxHashMap::default();
    let mut sentence_cased: Map<Vec<Entry>> = FxHashMap::default();
    let mut sentence_order: Vec<&'static str> = Vec::new();
    for &surface in &order {
        let entries = &cased[surface];
        let spaced = surface.contains(' ');
        let low = lowered_static(surface);
        let surface_chars: Vec<char> = surface.chars().collect();
        let titles: Vec<Entry> = entries.iter().copied().filter(|e| TITLES.contains(&e.attribute) && !e.common).collect();
        let famous: Vec<Entry> = titles.iter().copied().filter(|e| e.links >= FAMOUS_SITELINKS).collect();
        if !spaced && titled_first(surface) == surface && !famous.is_empty() {
            raised.insert(low, famous);
        } else if !spaced && has_digit(surface) && two_letters(&surface_chars) && !titles.is_empty() {
            raised.entry(low).or_insert(titles);
        } else if nonword.contains(low) && !titles.is_empty() {
            raised.entry(low).or_insert(titles);
        }
        if spaced {
            let mut chars = surface.chars();
            let first = chars.next().unwrap();
            let mut form = first.to_string();
            form.push_str(&chars.as_str().to_lowercase());
            if form != surface && !cased.contains_key(form.as_str()) {
                let artists: Vec<Entry> = entries.iter().copied().filter(|e| e.attribute == "artist").collect();
                if !artists.is_empty() {
                    let form = leak(form);
                    sentence_cased.entry(form).or_insert_with(|| {
                        sentence_order.push(form);
                        Vec::new()
                    }).extend(artists);
                }
            }
        }
    }
    let mut lexicon = Lexicon {
        plain,
        cased,
        film_plain,
        film_cased,
        raised,
        sentence_cased,
        team_words: FxHashMap::default(),
        team_span: 0,
        author_of_book: pairs("book_authors.tsv"),
        series_of_game: pairs("game_series.tsv"),
        places: rows("gazetteer.tsv").map(|line| line.split('\t').next().unwrap()).collect(),
    };
    lexicon.team_words = team_words("clubs.tsv");
    lexicon.team_span = lexicon.team_words.keys().map(|k| k.matches(' ').count() + 1).max().unwrap_or(0);
    lexicon
}

pub static LEXICON: LazyLock<Lexicon> = LazyLock::new(|| timed("fandom lexicon", build));

pub fn team(name: &[char]) -> Option<&'static str> {
    let key = joined_words(&folded_chars(name)).to_lowercase();
    let key = key.strip_prefix("the ").unwrap_or(&key);
    LEXICON.team_words.get(key).copied()
}

pub struct Node {
    pub key: &'static str,
    pub prefix: bool,
    pub plain: Option<&'static Vec<Entry>>,
    pub film_plain: Option<&'static Vec<Entry>>,
    surfaces: Vec<(u8, &'static str, &'static Vec<Entry>)>,
}

pub const CASED: u8 = 0;
pub const RAISED: u8 = 1;
pub const SENTENCE: u8 = 2;
pub const FILM_CASED: u8 = 3;

impl Node {
    pub fn surface(&self, table: u8, surface: &str) -> Option<&'static Vec<Entry>> {
        self.surfaces.iter().find(|(t, s, _)| *t == table && *s == surface).map(|(_, _, e)| *e)
    }
}

pub struct Index {
    slots: FxHashMap<u64, u32>,
    nodes: Vec<Node>,
}

pub enum Probe {
    Absent,
    Prefix,
    Entry(&'static Node),
}

const PREFIX_ONLY: u32 = u32::MAX;

pub fn hash_key(key: &str) -> u64 {
    use std::hash::Hasher;
    let mut hasher = rustc_hash::FxHasher::default();
    hasher.write(key.as_bytes());
    hasher.write_u8(0xff);
    hasher.finish()
}

fn word_lowered(surface: &'static str) -> &'static str {
    if surface.bytes().all(|b| b.is_ascii() && !b.is_ascii_uppercase()) {
        return surface;
    }
    let low = surface.split(' ').map(|word| word.to_lowercase()).collect::<Vec<_>>().join(" ");
    if low == surface {
        surface
    } else {
        leak(low)
    }
}

fn build_index(lex: &'static Lexicon) -> Index {
    let mut position: FxHashMap<&'static str, usize> = FxHashMap::default();
    let mut nodes: Vec<Node> = Vec::new();
    let mut node = |key: &'static str, nodes: &mut Vec<Node>| -> usize {
        *position.entry(key).or_insert_with(|| {
            nodes.push(Node { key, prefix: false, plain: None, film_plain: None, surfaces: Vec::new() });
            nodes.len() - 1
        })
    };
    for (key, entries) in &lex.plain {
        let index = node(key, &mut nodes);
        nodes[index].plain = Some(entries);
    }
    for (key, entries) in &lex.film_plain {
        let index = node(key, &mut nodes);
        nodes[index].film_plain = Some(entries);
    }
    for (table, map) in [(CASED, &lex.cased), (RAISED, &lex.raised), (SENTENCE, &lex.sentence_cased), (FILM_CASED, &lex.film_cased)] {
        for (surface, entries) in map {
            let index = node(word_lowered(surface), &mut nodes);
            nodes[index].surfaces.push((table, surface, entries));
        }
    }
    let mut slots: FxHashMap<u64, u32> = FxHashMap::with_capacity_and_hasher(nodes.len() * 2, Default::default());
    for (index, entry) in nodes.iter().enumerate() {
        if let Some(previous) = slots.insert(hash_key(entry.key), index as u32) {
            panic!("lexicon hash collision {} {}", nodes[previous as usize].key, entry.key);
        }
    }
    for key in lex.plain.keys().chain(lex.cased.keys()).chain(lex.film_plain.keys()).chain(lex.film_cased.keys()) {
        let low = lowered_static(key);
        let ends = low.char_indices().filter(|&(_, c)| c == ' ').map(|(i, _)| i).chain(std::iter::once(low.len()));
        for end in ends {
            let prefix = &low[..end];
            match slots.get(&hash_key(prefix)).copied() {
                None => {
                    slots.insert(hash_key(prefix), PREFIX_ONLY);
                }
                Some(PREFIX_ONLY) => {}
                Some(index) => {
                    if nodes[index as usize].key == prefix {
                        nodes[index as usize].prefix = true;
                    }
                }
            }
        }
    }
    Index { slots, nodes }
}

pub static INDEX: LazyLock<Index> = LazyLock::new(|| timed("fandom index", || build_index(&LEXICON)));

pub fn probe(key: &str) -> Probe {
    let index: &'static Index = &INDEX;
    match index.slots.get(&hash_key(key)).copied() {
        None => Probe::Absent,
        Some(PREFIX_ONLY) => Probe::Prefix,
        Some(slot) => {
            let node = &index.nodes[slot as usize];
            if node.key != key {
                Probe::Prefix
            } else if node.prefix {
                Probe::Entry(node)
            } else {
                Probe::Absent
            }
        }
    }
}
