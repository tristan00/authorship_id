use claimcore::*;
use std::collections::{HashMap, HashSet};
use std::hash::{BuildHasherDefault, Hasher};
use std::sync::LazyLock;
use unicode_normalization::char::canonical_combining_class;
use unicode_normalization::UnicodeNormalization;

#[derive(Clone, Copy, PartialEq, Debug)]
pub struct Entry {
    pub kind: &'static str,
    pub value: &'static str,
    pub region: &'static str,
    pub country: &'static str,
    pub flag: &'static str,
}

pub fn entry(kind: &'static str, value: &'static str, region: &'static str, country: &'static str, flag: &'static str) -> Entry {
    Entry { kind, value, region, country, flag }
}

const COUNTRY_ALIASES: &[(&str, &[&str])] = &[
    ("united states", &["usa", "u.s.", "u.s.a.", "america", "the states", "united states of america", "estados unidos", "eeuu", "ee.uu."]),
    ("united kingdom", &["uk", "u.k.", "britain", "great britain"]), ("new zealand", &["nz", "aotearoa"]), ("ireland", &["eire", "republic of ireland"]),
    ("netherlands", &["holland"]), ("czech republic", &["czechia"]), ("bosnia and herzegovina", &["bosnia"]), ("north macedonia", &["macedonia"]),
    ("turkey", &["türkiye", "turkiye"]), ("saudi arabia", &["ksa"]), ("united arab emirates", &["uae", "emirates"]), ("china", &["mainland china"]),
    ("south korea", &["korea", "s. korea"]), ("vietnam", &["viet nam"]), ("myanmar", &["burma"]), ("philippines", &["pinas"]), ("trinidad and tobago", &["trinidad"]),
    ("ivory coast", &["côte d'ivoire", "cote d'ivoire"]), ("democratic republic of the congo", &["drc", "dr congo"]), ("republic of the congo", &["congo"]),
    ("germany", &["deutschland"]), ("spain", &["españa", "espana"]), ("italy", &["italia"]), ("switzerland", &["schweiz", "suisse", "svizzera"]), ("austria", &["österreich", "osterreich"]),
    ("sweden", &["sverige"]), ("norway", &["norge"]), ("denmark", &["danmark"]), ("finland", &["suomi"]), ("poland", &["polska"]), ("mexico", &["méxico"]), ("brazil", &["brasil"]),
];

pub const DEMONYMS: &[(&str, &str)] = &[
    ("american", "united states"), ("canadian", "canada"), ("british", "united kingdom"), ("brit", "united kingdom"), ("english", "united kingdom"), ("scottish", "united kingdom"),
    ("welsh", "united kingdom"), ("irish", "ireland"), ("australian", "australia"), ("aussie", "australia"), ("kiwi", "new zealand"), ("new zealander", "new zealand"),
    ("german", "germany"), ("french", "france"), ("spanish", "spain"), ("spaniard", "spain"), ("italian", "italy"), ("portuguese", "portugal"), ("dutch", "netherlands"), ("belgian", "belgium"),
    ("swiss", "switzerland"), ("austrian", "austria"), ("swedish", "sweden"), ("swede", "sweden"), ("norwegian", "norway"), ("danish", "denmark"), ("dane", "denmark"),
    ("finnish", "finland"), ("icelandic", "iceland"), ("polish", "poland"), ("czech", "czech republic"), ("slovak", "slovakia"), ("hungarian", "hungary"), ("romanian", "romania"),
    ("bulgarian", "bulgaria"), ("greek", "greece"), ("croatian", "croatia"), ("serbian", "serbia"), ("slovenian", "slovenia"), ("bosnian", "bosnia and herzegovina"),
    ("albanian", "albania"), ("ukrainian", "ukraine"), ("russian", "russia"), ("belarusian", "belarus"), ("lithuanian", "lithuania"), ("latvian", "latvia"), ("estonian", "estonia"),
    ("armenian", "armenia"), ("turkish", "turkey"), ("israeli", "israel"), ("palestinian", "palestine"), ("lebanese", "lebanon"), ("jordanian", "jordan"), ("syrian", "syria"),
    ("iraqi", "iraq"), ("iranian", "iran"), ("persian", "iran"), ("saudi", "saudi arabia"), ("emirati", "united arab emirates"), ("egyptian", "egypt"), ("moroccan", "morocco"),
    ("algerian", "algeria"), ("tunisian", "tunisia"), ("nigerian", "nigeria"), ("ghanaian", "ghana"), ("kenyan", "kenya"), ("ethiopian", "ethiopia"), ("south african", "south africa"),
    ("ugandan", "uganda"), ("indian", "india"), ("pakistani", "pakistan"), ("bangladeshi", "bangladesh"), ("sri lankan", "sri lanka"), ("nepali", "nepal"), ("nepalese", "nepal"),
    ("afghan", "afghanistan"), ("chinese", "china"), ("taiwanese", "taiwan"), ("japanese", "japan"), ("korean", "south korea"), ("vietnamese", "vietnam"), ("thai", "thailand"),
    ("cambodian", "cambodia"), ("malaysian", "malaysia"), ("singaporean", "singapore"), ("indonesian", "indonesia"), ("filipino", "philippines"), ("filipina", "philippines"),
    ("pinoy", "philippines"), ("pinay", "philippines"), ("mexican", "mexico"), ("guatemalan", "guatemala"), ("honduran", "honduras"), ("salvadoran", "el salvador"), ("cuban", "cuba"),
    ("jamaican", "jamaica"), ("dominican", "dominican republic"), ("haitian", "haiti"), ("puerto rican", "puerto rico"), ("colombian", "colombia"), ("venezuelan", "venezuela"),
    ("ecuadorian", "ecuador"), ("peruvian", "peru"), ("bolivian", "bolivia"), ("chilean", "chile"), ("argentinian", "argentina"), ("argentine", "argentina"), ("uruguayan", "uruguay"),
    ("brazilian", "brazil"),
    ("scot", "united kingdom"), ("northern irish", "united kingdom"), ("kazakh", "kazakhstan"), ("uzbek", "uzbekistan"), ("mongolian", "mongolia"), ("burmese", "myanmar"),
    ("laotian", "laos"), ("maltese", "malta"), ("cypriot", "cyprus"), ("luxembourgish", "luxembourg"), ("montenegrin", "montenegro"), ("macedonian", "north macedonia"),
    ("moldovan", "moldova"), ("azerbaijani", "azerbaijan"), ("azeri", "azerbaijan"), ("qatari", "qatar"), ("kuwaiti", "kuwait"), ("bahraini", "bahrain"), ("omani", "oman"),
    ("yemeni", "yemen"), ("libyan", "libya"), ("sudanese", "sudan"), ("somali", "somalia"), ("rwandan", "rwanda"), ("tanzanian", "tanzania"), ("zimbabwean", "zimbabwe"),
    ("zambian", "zambia"), ("cameroonian", "cameroon"), ("senegalese", "senegal"), ("congolese", "democratic republic of the congo"), ("angolan", "angola"),
    ("nicaraguan", "nicaragua"), ("costa rican", "costa rica"), ("panamanian", "panama"), ("trinidadian", "trinidad and tobago"), ("bahamian", "bahamas"), ("barbadian", "barbados"),
    ("paraguayan", "paraguay"), ("slovene", "slovenia"), ("slovakian", "slovakia"), ("hong konger", "hong kong"), ("hongkonger", "hong kong"), ("mozambican", "mozambique"),
    ("malagasy", "madagascar"), ("namibian", "namibia"), ("malawian", "malawi"), ("ivorian", "ivory coast"), ("malian", "mali"), ("liberian", "liberia"), ("eritrean", "eritrea"),
    ("mauritian", "mauritius"), ("fijian", "fiji"), ("bhutanese", "bhutan"), ("maldivian", "maldives"), ("kyrgyz", "kyrgyzstan"), ("tajik", "tajikistan"), ("turkmen", "turkmenistan"),
    ("kosovar", "kosovo"), ("belizean", "belize"), ("guyanese", "guyana"), ("surinamese", "suriname"), ("salvadorean", "el salvador"),
];

const US_STATES: &[(&str, &str)] = &[
    ("alabama", "al"), ("alaska", "ak"), ("arizona", "az"), ("arkansas", "ar"), ("california", "ca"), ("colorado", "co"), ("connecticut", "ct"), ("delaware", "de"), ("florida", "fl"),
    ("georgia", "ga"), ("hawaii", "hi"), ("idaho", "id"), ("illinois", "il"), ("indiana", "in"), ("iowa", "ia"), ("kansas", "ks"), ("kentucky", "ky"), ("louisiana", "la"), ("maine", "me"),
    ("maryland", "md"), ("massachusetts", "ma"), ("michigan", "mi"), ("minnesota", "mn"), ("mississippi", "ms"), ("missouri", "mo"), ("montana", "mt"), ("nebraska", "ne"), ("nevada", "nv"),
    ("new hampshire", "nh"), ("new jersey", "nj"), ("new mexico", "nm"), ("new york", "ny"), ("north carolina", "nc"), ("north dakota", "nd"), ("ohio", "oh"), ("oklahoma", "ok"),
    ("oregon", "or"), ("pennsylvania", "pa"), ("rhode island", "ri"), ("south carolina", "sc"), ("south dakota", "sd"), ("tennessee", "tn"), ("texas", "tx"), ("utah", "ut"),
    ("vermont", "vt"), ("virginia", "va"), ("washington", "wa"), ("west virginia", "wv"), ("wisconsin", "wi"), ("wyoming", "wy"),
];

const US_STATE_DEMONYMS: &[(&str, &str)] = &[
    ("alabamian", "alabama"), ("alaskan", "alaska"), ("arizonan", "arizona"), ("arkansan", "arkansas"), ("californian", "california"), ("coloradan", "colorado"), ("connecticuter", "connecticut"),
    ("delawarean", "delaware"), ("floridian", "florida"), ("hawaiian", "hawaii"), ("idahoan", "idaho"), ("illinoisan", "illinois"), ("hoosier", "indiana"), ("iowan", "iowa"), ("kansan", "kansas"),
    ("kentuckian", "kentucky"), ("louisianian", "louisiana"), ("mainer", "maine"), ("marylander", "maryland"), ("bay stater", "massachusetts"), ("michigander", "michigan"),
    ("minnesotan", "minnesota"), ("mississippian", "mississippi"), ("missourian", "missouri"), ("montanan", "montana"), ("nebraskan", "nebraska"), ("nevadan", "nevada"),
    ("new hampshirite", "new hampshire"), ("new jerseyan", "new jersey"), ("new mexican", "new mexico"), ("new yorker", "new york"), ("north carolinian", "north carolina"),
    ("north dakotan", "north dakota"), ("ohioan", "ohio"), ("oklahoman", "oklahoma"), ("oregonian", "oregon"), ("pennsylvanian", "pennsylvania"), ("rhode islander", "rhode island"),
    ("south carolinian", "south carolina"), ("south dakotan", "south dakota"), ("tennessean", "tennessee"), ("texan", "texas"), ("utahn", "utah"), ("vermonter", "vermont"),
    ("virginian", "virginia"), ("washingtonian", "washington"), ("west virginian", "west virginia"), ("wisconsinite", "wisconsin"), ("wyomingite", "wyoming"),
];

const CA_PROVINCE_DEMONYMS: &[(&str, &str)] = &[
    ("albertan", "alberta"), ("british columbian", "british columbia"), ("manitoban", "manitoba"), ("new brunswicker", "new brunswick"), ("newfoundlander", "newfoundland and labrador"),
    ("nova scotian", "nova scotia"), ("ontarian", "ontario"), ("quebecer", "quebec"), ("quebecker", "quebec"), ("québécois", "quebec"), ("saskatchewanian", "saskatchewan"),
];

const REGION_ALIASES: &[(&str, &[&str])] = &[
    ("california", &["cali", "socal", "norcal", "southern california", "northern california"]), ("new jersey", &["jersey"]), ("washington", &["washington state"]),
    ("district of columbia", &["dc", "d.c.", "washington dc", "washington d.c."]), ("quebec", &["québec"]), ("newfoundland and labrador", &["newfoundland"]),
    ("new south wales", &["nsw"]), ("queensland", &["qld"]), ("bavaria", &["bayern"]), ("north rhine-westphalia", &["nrw"]), ("saxony", &["sachsen"]), ("hesse", &["hessen"]),
    ("thuringia", &["thüringen"]), ("jammu and kashmir", &["kashmir"]), ("catalonia", &["catalunya"]), ("andalusia", &["andalucía", "andalucia"]),
    ("basque country", &["país vasco"]), ("canary islands", &["canarias"]), ("sicily", &["sicilia"]), ("sardinia", &["sardegna"]), ("tuscany", &["toscana"]),
    ("lombardy", &["lombardia"]),
];

const CITY_ALIASES: &[(&str, &str)] = &[
    ("nyc", "new york city"), ("la", "los angeles"), ("l.a.", "los angeles"), ("sf", "san francisco"), ("philly", "philadelphia"), ("vegas", "las vegas"),
    ("okc", "oklahoma city"), ("slc", "salt lake city"), ("bombay", "mumbai"), ("calcutta", "kolkata"), ("cdmx", "mexico city"),
    ("kl", "kuala lumpur"), ("saigon", "ho chi minh city"), ("kiev", "kyiv"), ("odessa", "odesa"), ("münchen", "munich"), ("roma", "rome"),
    ("milano", "milan"), ("wien", "vienna"), ("lisboa", "lisbon"), ("rio", "rio de janeiro"), ("atl", "atlanta"), ("chi", "chicago"),
    ("nola", "new orleans"), ("pdx", "portland"), ("htx", "houston"), ("kc", "kansas city"),
];
const ENGLISH_NAMES: &[(&str, &str)] = &[("bangalore", "bengaluru"), ("cologne", "köln"), ("seville", "sevilla")];
const COUNTRY_CODES: &[(&str, &str)] = &[("us", "united states")];
const US_CENSUS_REGIONS: &[&str] = &["northeast", "midwest", "south", "west", "new england", "mid-atlantic", "east north central", "west north central", "south atlantic", "east south central",
    "west south central", "mountain", "pacific"];
const CANADA_CODES: &[(&str, &str)] = &[("ab", "alberta"), ("bc", "british columbia"), ("mb", "manitoba"), ("nb", "new brunswick"), ("nl", "newfoundland and labrador"), ("ns", "nova scotia"),
    ("nt", "northwest territories"), ("nu", "nunavut"), ("on", "ontario"), ("pe", "prince edward island"), ("qc", "quebec"), ("sk", "saskatchewan"), ("yt", "yukon")];
const AUSTRALIA_CODES: &[(&str, &str)] = &[("nsw", "new south wales"), ("vic", "victoria"), ("qld", "queensland"), ("sa", "south australia"), ("wa", "western australia"), ("tas", "tasmania"),
    ("nt", "northern territory"), ("act", "australian capital territory")];

pub const CONTINENTS: &str = "africa african america americas american antarctica asia asian europe european oceania";
const DEITIES: &str = "god gods goddess jesus christ allah buddha heaven hell satan lord paradise";
const DIRECTIONS: &str = "north south east west northern southern eastern western northeastern northwestern southeastern southwestern central upstate downstate rural coastal middle sw se nw ne northeast northwest southeast southwest downtown uptown metro inner outer far deep";

fn region_codes() -> Vec<(&'static str, Vec<(&'static str, &'static str)>)> {
    vec![
        ("united states", US_STATES.iter().map(|&(name, code)| (code, name)).collect()),
        ("canada", CANADA_CODES.to_vec()),
        ("australia", AUSTRALIA_CODES.to_vec()),
    ]
}

pub fn region_code(country: &str, code: &[char]) -> Option<&'static str> {
    let table: &[(&str, &str)] = match country {
        "united states" => return US_STATES.iter().find(|(_, c)| eq(code, c)).map(|(name, _)| *name),
        "canada" => CANADA_CODES,
        "australia" => AUSTRALIA_CODES,
        _ => return None,
    };
    table.iter().find(|(c, _)| eq(code, c)).map(|(_, name)| *name)
}

pub fn token_char(c: char) -> bool {
    if c.is_ascii() {
        c.is_ascii_alphanumeric()
    } else {
        is_alnum(c)
    }
}

pub fn tokens(s: &[char]) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    let mut index = 0;
    while index < s.len() {
        if token_char(s[index]) {
            let start = index;
            while index < s.len() && token_char(s[index]) {
                index += 1;
            }
            out.push((start, index));
        } else {
            index += 1;
        }
    }
    out
}

pub fn key(name: &str) -> String {
    let lowered: Vec<char> = name.to_lowercase().chars().collect();
    tokens(&lowered).iter().map(|&(a, b)| st(&lowered[a..b])).collect::<Vec<_>>().join(" ")
}

fn plain(name: &str) -> String {
    name.nfkd().filter(|&c| canonical_combining_class(c) == 0).collect()
}

struct Interner(HashMap<String, &'static str>);

impl Interner {
    fn get(&mut self, s: &str) -> &'static str {
        if let Some(found) = self.0.get(s) {
            return found;
        }
        let leaked: &'static str = Box::leak(s.to_string().into_boxed_str());
        self.0.insert(s.to_string(), leaked);
        leaked
    }
}

#[derive(Default)]
struct Ordered {
    items: Vec<(String, Entry)>,
    index: HashMap<String, usize>,
}

impl Ordered {
    fn put(&mut self, name: String, value: Entry) {
        match self.index.get(&name) {
            Some(&at) => self.items[at].1 = value,
            None => {
                self.index.insert(name.clone(), self.items.len());
                self.items.push((name, value));
            }
        }
    }

    fn setdefault(&mut self, name: String, value: Entry) {
        if !self.index.contains_key(&name) {
            self.put(name, value);
        }
    }

    fn get(&self, name: &str) -> Entry {
        self.items[self.index[name]].1
    }
}

#[derive(Default, Clone, Copy)]
pub struct Fx(u64);

impl Hasher for Fx {
    fn write(&mut self, bytes: &[u8]) {
        for &byte in bytes {
            self.add(byte as u64);
        }
    }

    fn write_u32(&mut self, n: u32) {
        self.add(n as u64);
    }

    fn write_u64(&mut self, n: u64) {
        self.add(n);
    }

    fn write_usize(&mut self, n: usize) {
        self.add(n as u64);
    }

    fn finish(&self) -> u64 {
        self.0
    }
}

impl Fx {
    fn add(&mut self, n: u64) {
        self.0 = (self.0.rotate_left(5) ^ n).wrapping_mul(0x517c_c1b7_2722_0a95);
    }
}

pub type FxMap<V> = HashMap<Box<[char]>, V, BuildHasherDefault<Fx>>;

#[derive(Default, Clone, Copy)]
pub struct Node {
    pub entry: Option<Entry>,
    pub prefix: bool,
    pub nation_word: bool,
    pub nation_lead: bool,
}

pub struct Lexicon {
    pub nodes: FxMap<Node>,
    pub squashed: FxMap<Entry>,
    pub nations: HashMap<String, &'static str>,
    pub nation_names: Vec<String>,
    pub compound_nations: Vec<Vec<char>>,
}

fn gazetteer(strings: &mut Interner) -> Ordered {
    let data = data_file("gazetteer.tsv");
    let mut loaded = Ordered::default();
    for line in data.split('\n').skip(1) {
        if line.is_empty() {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        if fields[1] == "country" && fields[0] != fields[2] && fields[2].split(' ').any(|word| word == fields[0]) {
            continue;
        }
        let kind = strings.get(fields[1]);
        let value = strings.get(&plain(fields[2]));
        let region = strings.get(&plain(fields[3]));
        let country = strings.get(fields[4]);
        let flag = strings.get(fields[5]);
        loaded.put(fields[0].to_string(), entry(kind, value, region, country, flag));
    }
    loaded
}

fn places(strings: &mut Interner) -> Ordered {
    let mut loaded = gazetteer(strings);
    let mut found = Ordered::default();
    for &(name, _) in US_STATES {
        found.put(key(name), entry("region", name, name, "united states", ""));
    }
    for &(country, aliases) in COUNTRY_ALIASES {
        for name in aliases {
            found.put(key(name), entry("country", country, "", country, ""));
        }
    }
    for &(region, aliases) in REGION_ALIASES {
        let base = loaded.get(&key(region));
        for name in aliases {
            found.put(key(name), Entry { flag: "", ..base });
        }
    }
    for &(alias, city) in CITY_ALIASES {
        let base = loaded.get(&key(city));
        found.put(key(alias), Entry { flag: if alias.chars().count() <= 2 { "code" } else { "" }, ..base });
    }
    for &(name, local) in ENGLISH_NAMES {
        let base = loaded.get(&key(local));
        found.put(key(name), entry(base.kind, name, base.region, base.country, ""));
    }
    for (country, codes) in region_codes() {
        for (code, name) in codes {
            found.setdefault(code.to_string(), entry("region", name, name, country, "code"));
        }
    }
    for &(code, country) in COUNTRY_CODES {
        found.put(code.to_string(), entry("country", country, "", country, "code"));
    }
    for &name in US_CENSUS_REGIONS {
        found.put(key(name), entry("region", name, name, "united states", "1"));
    }
    for (name, value) in found.items {
        loaded.put(name, value);
    }
    loaded
}

fn foreign(strings: &mut Interner) -> Vec<(String, &'static str)> {
    let data = data_file("demonyms.tsv");
    let mut ordered = Ordered::default();
    for line in data.lines().skip(1) {
        let mut parts = line.split('\t');
        let name = parts.next().unwrap();
        let country = strings.get(parts.next().unwrap());
        ordered.put(name.to_string(), entry("foreign", country, "", country, ""));
    }
    ordered.items.into_iter().map(|(name, value)| (name, value.country)).collect()
}

fn build() -> Lexicon {
    let mut strings = Interner(HashMap::new());
    let places = places(&mut strings);
    let foreign = foreign(&mut strings);
    let nations: Vec<(String, &'static str)> = {
        let mut ordered: Vec<(String, &'static str)> = Vec::new();
        for &(name, country) in DEMONYMS {
            let k = key(name);
            match ordered.iter_mut().find(|(n, _)| *n == k) {
                Some(slot) => slot.1 = country,
                None => ordered.push((k, country)),
            }
        }
        ordered
    };
    let directions: HashSet<&str> = DIRECTIONS.split(' ').collect();
    let continents: HashSet<&str> = CONTINENTS.split(' ').collect();
    let deities: HashSet<&str> = DEITIES.split(' ').collect();
    let mut lexicon = Ordered::default();
    for (name, country) in &foreign {
        lexicon.put(name.clone(), entry("foreign", country, "", country, ""));
    }
    for (name, country) in &nations {
        lexicon.put(format!("{name}s"), entry("nations", country, "", country, ""));
    }
    for (name, value) in &places.items {
        let bare = name.strip_prefix("the ").unwrap_or(name);
        if !directions.contains(name.as_str()) && !deities.contains(bare) && !(matches!(value.kind, "city" | "region") && (continents.contains(bare) || demographics::ETHNICITIES.contains_key(bare))) {
            lexicon.put(bare.to_string(), *value);
        }
    }
    for &(name, region) in US_STATE_DEMONYMS {
        lexicon.put(key(name), entry("people", region, region, "united states", ""));
    }
    for &(name, region) in CA_PROVINCE_DEMONYMS {
        lexicon.put(key(name), entry("people", region, region, "canada", ""));
    }
    for (name, country) in &nations {
        lexicon.put(name.clone(), entry("nation", country, "", country, ""));
    }
    for (name, country) in &nations {
        for suffix in ["man", "woman", "men", "women"] {
            lexicon.put(format!("{name}{suffix}"), entry("nation", country, "", country, ""));
        }
    }
    let mut squashed = HashMap::new();
    let mut prefixes = HashSet::new();
    for (name, value) in &lexicon.items {
        if name.contains(' ') && !matches!(value.kind, "nation" | "nations" | "people") {
            squashed.insert(name.replace(' ', ""), *value);
        }
        let parts: Vec<&str> = name.split_whitespace().collect();
        for size in 1..=name.matches(' ').count() {
            prefixes.insert(parts[..size.min(parts.len())].join(" "));
        }
    }
    let mut nodes: FxMap<Node> = FxMap::default();
    for (name, value) in lexicon.items {
        nodes.entry(chars(&name).into()).or_default().entry = Some(value);
    }
    for name in prefixes {
        nodes.entry(chars(&name).into()).or_default().prefix = true;
    }
    for (name, _) in &nations {
        match name.split_once(' ') {
            Some((first, _)) => nodes.entry(chars(first).into()).or_default().nation_lead = true,
            None => nodes.entry(chars(name).into()).or_default().nation_word = true,
        }
    }
    Lexicon {
        compound_nations: nations.iter().filter(|(name, _)| name.contains(' ')).map(|(name, _)| chars(name)).collect(),
        nation_names: nations.iter().map(|(name, _)| name.clone()).collect(),
        nations: nations.into_iter().collect(),
        nodes,
        squashed: squashed.into_iter().map(|(name, value): (String, Entry)| (chars(&name).into(), value)).collect(),
    }
}

pub static LEXICON: LazyLock<Lexicon> = LazyLock::new(|| timed("location lexicon", build));
