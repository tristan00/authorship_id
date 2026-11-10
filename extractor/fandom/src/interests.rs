use crate::fandom::re_split;
use aho_corasick::AhoCorasick;
use claimcore::*;
use std::sync::LazyLock;

const IM: &str = r"(?:i'm|im|i am)";
const ADV: &str = r"(?: (?:also|now|currently|still|mainly|mostly|only|just|actually|really|primarily|usually|exclusively|personally|recently|finally|already|can))*";
const OPEN: &str = r"(?:^(?:r/\w+:\s*)?|[.!?\n,(]\s*)";
const RIG_FLAIR: &str = r"\Ar/\w*(?:pc|amd|nvidia|intel|radeon|geforce|hardware|overclock|battlestation)\w*: [^\n]*?(?<![\w-])";
const HERE: &str = r"(?:a |an |just a |fellow |another |proud )?";

const LINUX: &[&str] = &["linux", "arch", "arch linux", "ubuntu", "kubuntu", "xubuntu", "lubuntu", "fedora", "debian", "linux mint", "manjaro", "nixos", "gentoo", "pop!_os", "pop os", "pop_os",
    "opensuse", "cachyos", "cachy os", "bazzite", "endeavouros", "endeavour os", "void linux", "zorin os", "elementary os", "kali linux", "garuda", "artix", "slackware", "mx linux"];
const SYSTEMS: &[&str] = &["windows", "windows 11", "windows 10", "windows 7", "windows xp", "win11", "win10", "win 11", "win 10", "macos", "mac os", "osx", "os x", "a mac", "a macbook", "mac",
    "android", "ios", "chromeos", "chrome os", "a chromebook"];
const USERS: &[&str] = &["windows", "mac", "macos", "android", "ios", "chromebook"];
const PLATFORMS: &[&str] = &["pc", "steam", "ps5", "ps4", "ps3", "psvr", "playstation", "playstation 5", "playstation 4", "xbox", "xbox one", "xbox series x", "xbox series s", "series x", "series s",
    "switch", "switch 2", "switch2", "nintendo switch", "nintendo switch 2", "steam deck", "mobile", "quest", "quest 2", "quest 3", "vr"];
const CONSOLES: &[&str] = &["pc", "ps5", "ps4", "playstation", "playstation 5", "xbox", "xbox one", "xbox series x", "xbox series s", "series x", "series s", "switch 2", "nintendo switch", "steam deck"];
const INSTRUMENTS: &[(&str, &str)] = &[("guitar", "guitar"), ("electric guitar", "guitar"), ("acoustic guitar", "guitar"), ("classical guitar", "guitar"), ("bass", "bass"), ("bass guitar", "bass"),
    ("electric bass", "bass"), ("upright bass", "violin / viola / cello"), ("double bass", "violin / viola / cello"), ("piano", "piano / keyboard"), ("keyboards", "piano / keyboard"),
    ("keys", "piano / keyboard"), ("synth", "piano / keyboard"), ("drums", "drums"), ("drum kit", "drums"), ("violin", "violin / viola / cello"), ("viola", "violin / viola / cello"),
    ("cello", "violin / viola / cello"), ("fiddle", "violin / viola / cello"), ("trumpet", "trumpet"), ("cornet", "trumpet"), ("trombone", "trombone"), ("tuba", "tuba"), ("french horn", "french horn"),
    ("horn", "french horn"), ("euphonium", "euphonium"), ("saxophone", "saxophone"), ("sax", "saxophone"), ("alto sax", "saxophone"), ("tenor sax", "saxophone"), ("baritone sax", "saxophone"),
    ("alto saxophone", "saxophone"), ("tenor saxophone", "saxophone"), ("clarinet", "clarinet"), ("bass clarinet", "clarinet"), ("flute", "flute"), ("piccolo", "flute"), ("oboe", "oboe"),
    ("bassoon", "bassoon"), ("harp", "harp"), ("banjo", "banjo"), ("mandolin", "mandolin"), ("accordion", "accordion"), ("bagpipes", "bagpipes"), ("the pipes", "bagpipes"),
    ("ukulele", "ukulele"), ("uke", "ukulele"), ("harmonica", "harmonica"), ("biwa", "biwa"), ("tabla", "tabla")];
const PLAYERS: &[(&str, &str)] = &[("guitarist", "guitar"), ("guitar player", "guitar"), ("bassist", "bass"), ("bass player", "bass"), ("pianist", "piano / keyboard"), ("piano player", "piano / keyboard"),
    ("keyboardist", "piano / keyboard"), ("drummer", "drums"), ("percussionist", "drums"), ("violinist", "violin / viola / cello"), ("cellist", "violin / viola / cello"),
    ("violist", "violin / viola / cello"), ("fiddler", "violin / viola / cello"), ("trumpeter", "trumpet"), ("trumpet player", "trumpet"), ("trombonist", "trombone"), ("trombone player", "trombone"),
    ("horn player", "french horn"), ("french horn player", "french horn"), ("tuba player", "tuba"), ("euphonium player", "euphonium"), ("saxophonist", "saxophone"), ("sax player", "saxophone"),
    ("saxophone player", "saxophone"), ("clarinetist", "clarinet"), ("clarinettist", "clarinet"), ("clarinet player", "clarinet"), ("flautist", "flute"), ("flutist", "flute"), ("flute player", "flute"),
    ("oboist", "oboe"), ("oboe player", "oboe"), ("bassoonist", "bassoon"), ("bassoon player", "bassoon"), ("harpist", "harp"), ("singer", "voice / singing"), ("vocalist", "voice / singing"),
    ("banjo player", "banjo"), ("mandolin player", "mandolin"), ("accordionist", "accordion"), ("accordion player", "accordion"), ("bagpiper", "bagpipes"), ("ukulele player", "ukulele"),
    ("uke player", "ukulele"), ("harmonica player", "harmonica"), ("tabla player", "tabla"), ("dj", "dj / production"), ("music producer", "dj / production"), ("beatmaker", "dj / production"),
    ("piano teacher", "piano / keyboard"), ("guitar teacher", "guitar"), ("violin teacher", "violin / viola / cello"), ("drum teacher", "drums"), ("voice teacher", "voice / singing"),
    ("singing teacher", "voice / singing")];
const ARTS: &[(&str, &str)] = &[("bjj", "bjj"), ("brazilian jiu jitsu", "bjj"), ("brazilian jiu-jitsu", "bjj"), ("jiu jitsu", "bjj"), ("jiu-jitsu", "bjj"), ("jiujitsu", "bjj"), ("judo", "judo"),
    ("muay thai", "muay thai"), ("boxing", "boxing"), ("kickboxing", "kickboxing"), ("mma", "mma"), ("wrestling", "wrestling"), ("karate", "karate"), ("taekwondo", "taekwondo"),
    ("tae kwon do", "taekwondo"), ("tkd", "taekwondo"), ("kendo", "kendo / fencing / hema"), ("fencing", "kendo / fencing / hema"), ("hema", "kendo / fencing / hema"), ("capoeira", "capoeira"),
    ("kung fu", "kung fu / wing chun / tai chi"), ("wing chun", "kung fu / wing chun / tai chi"), ("tai chi", "kung fu / wing chun / tai chi"), ("aikido", "aikido / jujutsu"),
    ("jujutsu", "aikido / jujutsu"), ("japanese jujutsu", "aikido / jujutsu"), ("jujitsu", "aikido / jujutsu"), ("krav maga", "krav maga"), ("krav", "krav maga"), ("escrima", "escrima / kali"),
    ("eskrima", "escrima / kali"), ("kali", "escrima / kali"), ("arnis", "escrima / kali"), ("filipino martial arts", "escrima / kali"), ("sambo", "sambo"),
    ("combat sambo", "sambo")];
const FIGHTERS: &[(&str, &str)] = &[("judoka", "judo"), ("karateka", "karate"), ("kickboxer", "kickboxing"), ("mma fighter", "mma"), ("muay thai fighter", "muay thai"), ("fencer", "kendo / fencing / hema"),
    ("bjj practitioner", "bjj"), ("boxer", "boxing")];
const PERSONS: &[(&str, &str)] = &[("ppl", "private pilot"), ("private pilot", "private pilot"), ("cpl", "commercial pilot"), ("commercial pilot", "commercial pilot"), ("atp", "airline transport pilot"),
    ("atpl", "airline transport pilot"), ("airline transport pilot", "airline transport pilot"), ("cfi", "flight instructor"), ("cfii", "flight instructor"), ("cfi-i", "flight instructor"),
    ("mei", "flight instructor"), ("flight instructor", "flight instructor"), ("certified flight instructor", "flight instructor"), ("part 107 pilot", "drone / uas"), ("remote pilot", "drone / uas"),
    ("student pilot", "student pilot")];
const CERTIFICATES: &[(&str, &str)] = &[("ppl", "private pilot"), ("ppl(a)", "private pilot"), ("private pilot license", "private pilot"), ("private pilot licence", "private pilot"),
    ("private pilot's license", "private pilot"), ("private pilot's licence", "private pilot"), ("private pilot certificate", "private pilot"), ("private pilot cert", "private pilot"),
    ("cpl", "commercial pilot"), ("cpl(a)", "commercial pilot"), ("commercial pilot license", "commercial pilot"), ("commercial pilot licence", "commercial pilot"),
    ("commercial pilot certificate", "commercial pilot"), ("commercial certificate", "commercial pilot"), ("atp", "airline transport pilot"), ("atpl", "airline transport pilot"),
    ("atp certificate", "airline transport pilot"), ("atp cert", "airline transport pilot"), ("cfi", "flight instructor"), ("cfii", "flight instructor"), ("cfi-i", "flight instructor"),
    ("mei", "flight instructor"), ("instrument rating", "instrument rating"), ("ifr rating", "instrument rating"), ("multi-engine rating", "multi-engine"), ("multi engine rating", "multi-engine"),
    ("multiengine rating", "multi-engine"), ("part 107", "drone / uas"), ("part 107 certificate", "drone / uas"), ("part 107 license", "drone / uas"), ("remote pilot certificate", "drone / uas"),
    ("student pilot certificate", "student pilot"), ("student pilot license", "student pilot"), ("student pilot licence", "student pilot")];
const CLASSES: &[(&str, &str)] = &[("technician", "technician"), ("tech", "technician"), ("t", "technician"), ("general", "general"), ("g", "general"), ("extra", "extra"),
    ("amateur extra", "extra"), ("e", "extra"), ("ae", "extra")];
const SCENES: &[(&str, &str)] = &[("goth", "goth"), ("gothic", "goth"), ("alt", "alt"), ("alternative", "alt"), ("emo", "emo"), ("metalhead", "metalhead"), ("headbanger", "metalhead"),
    ("punk", "punk"), ("punk rocker", "punk"), ("punk rock", "punk"), ("nerd", "nerd / geek"), ("geek", "nerd / geek"), ("nerdy", "nerd / geek"), ("geeky", "nerd / geek"), ("jock", "jock"),
    ("weeb", "otaku / weeb"), ("weeaboo", "otaku / weeb"), ("otaku", "otaku / weeb"), ("cowboy", "cowboy / western"), ("cowgirl", "cowboy / western"), ("western", "cowboy / western"),
    ("bimbo", "bimbo"), ("bimboi", "bimbo"), ("gym rat", "gym rat"), ("gymrat", "gym rat"), ("hippie", "hippie"), ("hippy", "hippie"), ("grunge", "grunge"), ("skater", "skater"),
    ("skateboarder", "skater"), ("nudist", "nudist / naturist"), ("naturist", "nudist / naturist")];
const LABELS: &[&str] = &["goth", "emo", "metalhead", "headbanger", "punk", "punk rocker", "nerd", "geek", "jock", "weeb", "weeaboo", "otaku", "cowboy", "cowgirl", "bimbo", "bimboi", "gym rat",
    "gymrat", "hippie", "skater", "skateboarder", "nudist", "naturist"];
const NOUNED: &[&str] = &["alt", "alternative", "gothic", "nerdy", "geeky", "hippy", "grunge", "punk rock"];
const STYLES: &[&str] = &["goth", "gothic", "alt", "alternative", "emo", "punk", "grunge", "hippie", "hippy", "skater", "western"];
const MAKES: &[&str] = &["toyota", "honda", "ford", "chevy", "chevrolet", "nissan", "subaru", "mazda", "hyundai", "kia", "bmw", "audi", "mercedes", "mercedes-benz", "benz", "vw", "volkswagen", "jeep",
    "dodge", "gmc", "tesla", "lexus", "acura", "infiniti", "volvo", "porsche", "mitsubishi", "buick", "cadillac", "chrysler", "land rover", "range rover", "fiat", "alfa romeo", "suzuki", "kawasaki",
    "yamaha", "harley", "harley davidson", "harley-davidson", "ducati", "ktm", "rivian", "polestar", "skoda", "peugeot", "renault", "citroen", "opel", "vauxhall", "mahindra", "maruti",
    "lamborghini", "ferrari", "maserati", "bentley", "scion", "pontiac"];
const MODELS: &[&str] = &["civic", "accord", "corolla", "camry", "rav4", "tacoma", "tundra", "4runner", "prius", "highlander", "f-150", "f150", "f-250", "f250", "f-350", "mustang", "bronco",
    "silverado", "camaro", "corvette", "wrx", "wrx sti", "brz", "crosstrek", "impreza", "miata", "mx-5", "mx5", "cx-5", "cx5", "cx-30", "cx-50", "mazda3", "elantra", "sonata", "ioniq 5", "ioniq 6",
    "sportage", "sorento", "grand cherokee", "cybertruck", "cr-v", "crv", "hr-v", "jetta", "gti", "tiguan", "altima", "sentra", "maxima", "370z", "350z", "g35", "g37", "gr86", "gt86", "supra",
    "celica", "mr2", "s2000", "rx-7", "rx7", "rx-8", "xterra", "land cruiser", "escalade", "mach-e", "e30", "e36", "e46", "e90", "328i", "330i", "335i", "integra", "rsx", "4 runner", "xc40", "xc60", "xc90", "ram 1500",
    "ram 2500"];
const BRANDED: &[&str] = &["bolt", "bolt euv", "soul", "fit", "leaf", "focus", "escape", "explorer", "ranger", "edge", "fusion", "frontier", "pathfinder", "outback", "forester", "beetle", "golf",
    "golf r", "passat", "m3", "m4", "m5", "a3", "a4", "s4", "q5", "sierra", "charger", "challenger", "maverick", "odyssey", "pilot", "model 3", "model y", "model s", "model x", "tucson", "santa fe",
    "telluride", "wrangler", "outlander", "lancer", "evo", "sequoia", "kona", "niro", "tahoe", "gladiator", "durango", "sienna", "ioniq", "cooper", "is350", "is250", "rx350", "wrangler", "versa",
    "rogue", "civic si", "civic type r", "type r", "zx-6r", "ninja", "mt-07", "r6", "r1", "sportster"];
const HOBBY_NAMES: &[&str] = &["reading", "books", "gaming", "video games", "videogames", "playing video games", "board games", "playing board games", "tabletop games", "ttrpgs", "dnd", "d&d",
    "dungeons and dragons", "cooking", "baking", "hiking", "camping", "fishing", "hunting", "gardening", "photography", "traveling", "travelling", "travel", "drawing", "painting", "sketching",
    "writing", "creative writing", "poetry", "writing poetry", "knitting", "crocheting", "crochet", "sewing", "quilting", "embroidery", "cross stitch", "woodworking", "pottery", "ceramics", "dancing",
    "singing", "music", "making music", "playing music", "playing guitar", "playing the guitar", "playing piano", "playing the piano", "listening to music", "watching movies", "movies", "films",
    "watching films", "anime", "watching anime", "manga", "reading manga", "working out", "weightlifting", "lifting", "lifting weights", "powerlifting", "bodybuilding", "running", "jogging",
    "cycling", "biking", "mountain biking", "swimming", "yoga", "pilates", "climbing", "rock climbing", "bouldering", "surfing", "skiing", "snowboarding", "skateboarding", "skating", "ice skating",
    "kayaking", "sailing", "golf", "golfing", "tennis", "pickleball", "basketball", "soccer", "volleyball", "chess", "playing chess", "puzzles", "jigsaw puzzles", "birdwatching", "bird watching",
    "birding", "astronomy", "stargazing", "coding", "programming", "cosplay", "cosplaying", "journaling", "scrapbooking", "calligraphy", "origami", "lego", "legos", "model building", "gunpla",
    "warhammer", "thrifting", "working on cars", "archery", "martial arts", "meditation", "going to the gym", "gym", "sports", "art", "crafts", "crafting", "arts and crafts", "diy", "fitness",
    "tv shows", "podcasts", "concerts", "going to concerts", "karaoke", "homebrewing", "horseback riding", "horse riding", "dirt biking", "off-roading", "metal detecting", "geocaching", "foraging",
    "backpacking", "road trips", "trivia", "true crime", "nature walks", "long walks", "walks", "walking", "going for walks", "video editing", "3d printing", "gambling", "watching sports"];
const HOBBY_VERBS: &[(&str, &str)] = &[("cook", "cooking"), ("bake", "baking"), ("read", "reading"), ("hike", "hiking"), ("travel", "traveling"), ("draw", "drawing"), ("paint", "painting"),
    ("write", "writing"), ("dance", "dancing"), ("sing", "singing"), ("swim", "swimming"), ("fish", "fishing"), ("garden", "gardening"), ("knit", "knitting"), ("crochet", "crocheting"),
    ("sew", "sewing"), ("camp", "camping"), ("game", "gaming"), ("ski", "skiing"), ("surf", "surfing"), ("climb", "climbing"), ("bike", "biking"), ("skate", "skating"), ("golf", "golf"),
    ("work out", "working out"), ("workout", "working out"), ("play video games", "video games"), ("play games", "gaming"), ("watch anime", "anime"), ("watch movies", "movies"),
    ("listen to music", "music"), ("play guitar", "playing guitar"), ("play the guitar", "playing guitar"), ("play piano", "playing piano"), ("play the piano", "playing piano"),
    ("play chess", "chess"), ("play golf", "golf"), ("play tennis", "tennis"), ("play pickleball", "pickleball"), ("go hiking", "hiking"), ("go fishing", "fishing"), ("go camping", "camping"),
    ("journal", "journaling"), ("lift", "lifting"), ("lift weights", "lifting weights")];
const ENTHUSIASTS: &[&str] = &["gamer", "foodie", "bookworm", "book worm", "hiker", "knitter", "crocheter", "birder", "birdwatcher", "cosplayer", "woodworker", "angler", "surfer", "skier", "snowboarder",
    "skateboarder", "boulderer", "golfer", "backpacker", "movie buff", "film buff", "bibliophile", "crafter", "quilter", "gym rat", "gearhead", "petrolhead", "car enthusiast", "car guy", "home cook",
    "yogi", "anime fan", "otaku"];
const AMATEURS: &[&str] = &["reader", "runner", "cyclist", "climber", "swimmer", "photographer", "artist", "writer", "baker", "cook", "dancer", "gardener", "traveler", "traveller", "fisherman",
    "hunter", "camper", "collector", "lifter", "painter", "musician"];

static HOBBY_LEAD: LazyLock<Re> = LazyLock::new(|| Re::new(concat!(
    r"\b(?:my (?:main |favorite |favourite |current |other |few |only )?(?:hobbies|hobby|interests|pastimes|passions)(?: (?:are|is|include|includes|consist of|would be|are mostly|are mainly))?\s*[:-]?|",
    r"(?:^|\n)\s*(?:hobbies(?: and interests)?|interests)\s*[:-]|(?:i'm|im|i am)(?: (?:really|very|also|super|heavily|big|huge|mostly|mainly|kinda|pretty|quite))* into|",
    r"i (?:really |also |absolutely |truly |just |genuinely |especially |do )?(?:love|like|enjoy|adore)(?: to)?|(?:i'm|im|i am) (?:also |really |very )?interested in|",
    r"(?<=^|[.!?\n]|[.!?\n] |[.!?\n]  )(?:also |really )?(?:love|enjoy|into)|",
    r"in my (?:free|spare|down|leisure) time,? i(?: (?:really |also |usually |mostly )?(?:like|love|enjoy)(?: to)?)?|i (?:also )?spend (?:my|most of my|a lot of my|all my) (?:free|spare) time(?: on)?)\s+"
)));
static ABOUT: LazyLock<Re> = LazyLock::new(|| Re::new(r"^\s*\w+ about\b"));
static PIECES: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s*(?:,|;|/|&|\+|\band\b|\bor\b|\bas well as\b|\bplus\b)\s*"));
static QUALIFIER: LazyLock<Re> = LazyLock::new(|| Re::new(r"\s+(?:for|with|in|on|at|about|when|whenever|every|especially|a lot|too|sometimes|as well|myself|lately|alot|so much|very much|daily|outdoors|together)\b.*$"));
static FILLER: LazyLock<Re> = LazyLock::new(|| Re::new(r"^(?:(?:also|some|a lot of|lots of|doing|going|a bit of|a little|more|mostly|mainly|really|just|to|of course)\s+)+"));
static HOBBIES: LazyLock<Table> = LazyLock::new(|| HOBBY_NAMES.iter().map(|name| (name.to_string(), *name)).collect());
static DOINGS: LazyLock<Table> = LazyLock::new(|| table(HOBBY_VERBS));
static OBJECT: LazyLock<Re> = LazyLock::new(|| Re::new(r"^\s*(?:it|this|that|these|those|you|him|her|them|me|us|my|your|his|their|our|when|how|what|being|seeing|watching you|having)\b"));
static TENTATIVE: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:minimum|recommended|recommend|requirements|budget|dream|should i|planning|thinking of|looking to|want to build|wishlist|wish list|for sale|selling|sell|wts|price|deal|chat ?gpt|vs)\b"));

static HAM: LazyLock<Re> = LazyLock::new(|| Re::new(r"\b(?:ham|hams|amateur radio|ham radio|callsign|call sign|fcc|arrl|rsgb|repeater|qso|hf|vhf|uhf|2m|70cm|baofeng|r/amateurradio|r/hamradio)\b"));

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(build);
const HOBBY_GATE: &[&str] = &["lov", "like", "enjoy", "adore", "into", "hobb", "interest", " time"];

struct Gates {
    matcher: AhoCorasick,
    rules: Vec<Option<[u64; 4]>>,
    hobbies: [u64; 4],
}

static GATES: LazyLock<Gates> = LazyLock::new(|| {
    let mut words: Vec<String> = Vec::new();
    let mut mask = |anchors: Vec<String>| {
        let mut bits = [0u64; 4];
        for word in anchors {
            let index = words.iter().position(|w| *w == word).unwrap_or_else(|| {
                words.push(word);
                words.len() - 1
            });
            bits[index / 64] |= 1 << (index % 64);
        }
        bits
    };
    let rules = RULES.iter().map(|entry| entry.gate.as_ref().map(|anchors| mask(anchors.iter().map(|a| a.iter().collect()).collect()))).collect();
    let hobbies = mask(HOBBY_GATE.iter().map(|w| w.to_string()).collect());
    assert!(words.len() <= 256);
    Gates { matcher: AhoCorasick::new(&words).unwrap(), rules, hobbies }
});

fn present(lowered: &[char]) -> [u64; 4] {
    let bytes: Vec<u8> = lowered.iter().map(|&c| if c.is_ascii() { c as u8 } else { 0x80 }).collect();
    let mut bits = [0u64; 4];
    for found in GATES.matcher.find_overlapping_iter(&bytes) {
        let index = found.pattern().as_usize();
        bits[index / 64] |= 1 << (index % 64);
    }
    bits
}

fn meets(bits: &[u64; 4], mask: &[u64; 4]) -> bool {
    (0..4).any(|i| bits[i] & mask[i] != 0)
}

fn pick(pairs: &[(&str, &str)]) -> String {
    longest_first(pairs.iter().map(|(name, _)| *name))
}

fn value_of(pairs: &'static [(&'static str, &'static str)], m: &Match) -> Option<String> {
    let mut values: Vec<&str> = Vec::new();
    for number in 1..m.groups() + 1 {
        if let Some(name) = m.nonempty(number) {
            let name = st(name);
            if let Some((_, value)) = pairs.iter().find(|(key, _)| *key == name) {
                if !values.contains(value) {
                    values.push(value);
                }
            }
        }
    }
    (!values.is_empty()).then(|| values.join("|"))
}

fn mapped(pairs: &'static [(&'static str, &'static str)]) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| value_of(pairs, m)
}

fn radio() -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    |m| if HAM.test(m.string) { value_of(CLASSES, m) } else { None }
}

fn system(m: &Match) -> Option<String> {
    let name = m.first_s()?;
    let value = if name.starts_with("win") {
        "windows"
    } else if name.contains("mac") || name.contains("os x") || name == "osx" {
        "macos"
    } else if name == "android" {
        "android"
    } else if name == "ios" {
        "ios"
    } else if name.contains("chrome") {
        "chromeos"
    } else {
        "linux"
    };
    Some(value.to_string())
}

fn platform(m: &Match) -> Option<String> {
    let names: Vec<&str> = (1..=m.groups()).filter_map(|group| m.gs(group)).map(|name| platform_of(&name)).collect();
    (!names.is_empty()).then(|| names.join("|"))
}

fn platform_of(name: &str) -> &'static str {
    if name == "steam deck" {
        "steam deck"
    } else if name == "pc" || name == "steam" {
        "pc"
    } else if name == "psvr" || name == "vr" || name.starts_with("quest") {
        "vr"
    } else if name.starts_with("ps") || name.starts_with("playstation") {
        "playstation"
    } else if name.starts_with("xbox") || name.starts_with("series") {
        "xbox"
    } else if name.contains("switch") {
        "nintendo switch"
    } else {
        "mobile"
    }
}

fn number(text: &str, low: f64, high: f64) -> Option<f64> {
    let value: f64 = text.trim_start_matches('+').parse().ok()?;
    (low..=high).contains(&value).then_some(value)
}

fn ranged(low: f64, high: f64) -> impl Fn(&Match) -> Option<String> + Send + Sync + 'static {
    move |m| {
        let index = m.first_index()?;
        let first = number(&m.gs(index)?, low, high)?;
        let value = match m.gs(index + 1).and_then(|second| number(&second, low, high)) {
            Some(second) if second > first => (first + second) / 2.0,
            _ => first,
        };
        Some(format!("{value}"))
    }
}

fn handicap(m: &Match) -> Option<String> {
    let text = m.first_s()?;
    let value = number(&text, 0.0, 54.0)?;
    let value = if text.starts_with('+') { -value } else { value };
    (value >= -5.0).then(|| format!("{value}"))
}

fn minutes(m: &Match) -> Option<String> {
    let index = m.first_index()?;
    let whole: f64 = m.gs(index)?.parse().ok()?;
    let seconds: f64 = m.gs(index + 1)?.parse().ok()?;
    let value = whole + seconds / 60.0;
    (12.0..=60.0).contains(&value).then(|| format!("{value:.2}"))
}

fn memory(m: &Match) -> Option<String> {
    let size: f64 = m.gs(2)?.parse().ok()?;
    let count: f64 = m.gs(1).map_or(Some(1.0), |count| count.parse().ok())?;
    let value = count * size;
    (2.0..=512.0).contains(&value).then(|| format!("{value}"))
}

fn listed(m: &Match) -> Option<String> {
    if TENTATIVE.test(m.string) {
        None
    } else {
        m.first_s()
    }
}

fn named(m: &Match) -> Option<String> {
    let parts: Vec<String> = (1..m.groups() + 1).filter_map(|i| m.nonempty(i).map(st)).collect();
    (!parts.is_empty()).then(|| parts.join(" "))
}

fn add(rules: &mut Vec<Rule>, attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static, anchors: &[&str]) {
    let entry = rule(attribute, pattern, value, self_hedge());
    rules.push(if anchors.is_empty() { entry } else { needs(entry, anchors) });
}

fn build() -> Vec<Rule> {
    let mut rules = Vec::new();
    let linux = longest_first(LINUX.iter().copied());
    let systems = longest_first(LINUX.iter().chain(SYSTEMS).copied());
    let users = longest_first(LINUX.iter().chain(USERS).copied());
    let os_anchors = &["linux", "arch", "ubuntu", "fedora", "debian", "manjaro", "nixos", "gentoo", "pop", "suse", "cachy", "bazzite", "endeavour", "zorin", "elementary", "garuda", "artix",
        "slackware", "windows", "win1", "mac", "os x", "osx", "android", "ios", "chrome"];
    let tools = r"(?![\w-]| (?:auto|studio|subsystem|terminal|emulator|vm|virtual|ready|keys?|defender|updates?|store|hello|explorer|commands?|server|partition|install|iso|usb|tablet|tv|apps?|version|port|release|build|side|phone|phones)\b)";
    add(&mut rules, "operating_system", &format!(r#"(?<!["“'])\bi(?:'ve been| have been|ve been)?{ADV} (?:use|using|run|running|daily drive|daily|main|switched to|moved to|migrated to|swapped to|switched over to|installed) (?:only )?({systems})\b{tools}"#), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"{OPEN}{HERE}({users}) user\b(?=\s*(?:$|[.,!;:)\n]|\b(?:here|btw|and|but|so|myself)\b))"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"\bi{ADV} (?:have|own|got|bought|use) (?:a |an |my )(?:new |used |trusty )?(mac|macbook(?: pro| air)?|imac|mac mini|mac studio|chromebook)\b(?![\w'-]| (?:and cheese|n cheese)\b)"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"\bmy ({systems}) (?:pc|laptop|desktop|machine|box|install|installation|system|setup|workstation|rig)\b"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"\b{IM}(?: (?:a|an))?(?: (?:proud|happy|longtime|long[- ]time|lifelong|full[- ]time|daily))? ({users}) user\b"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"{OPEN}{HERE}({users}) user here\b"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"\b{IM}{ADV} (?:on|using|running) ({systems})\b{tools}"), system, os_anchors);
    add(&mut rules, "operating_system", &format!(r"\b(?:eu |yo |ya )?uso (?:o |el )?({linux})\b"), system, &["uso "]);

    let perfect = format!(r"\bi(?:'ve|ve|'m|m| have| am)?{ADV}(?: been)?");
    let platforms = longest_first(PLATFORMS.iter().copied());
    let consoles = longest_first(CONSOLES.iter().copied());
    let platform_anchors = &["pc", "steam", "ps", "playstation", "xbox", "series", "switch", "mobile", "quest", "vr"];
    let after = r"\b(?![\w-]| (?:version|port|release|build|controller|exclusive|exclusives|games?)\b)";
    add(&mut rules, "gaming_platform", &format!(r"{perfect} (?:play|playing|played|game|gaming)(?: (?:mostly|mainly|only|exclusively|primarily|usually|it|this|them|everything|games|stuff))? on (?:the |my |a )?({platforms}){after}"), platform, platform_anchors);
    add(&mut rules, "gaming_platform", &format!(r"\b{IM}(?: (?:a|an))?(?: (?:proud|casual|hardcore|lifelong|long[- ]?time|filthy|full[- ]time|primarily|mainly|mostly))* ({platforms}) (?:player|gamer)\b(?!s|'s| (?:base|count|numbers|community|population)\b)"), platform, platform_anchors);
    add(&mut rules, "gaming_platform", &format!(r"{OPEN}{HERE}({platforms}) (?:player|gamer)(?: here\b|(?=\s*(?:$|[.,!;:)\n]|\b(?:and|btw|but|so|myself)\b)))"), platform, platform_anchors);
    add(&mut rules, "gaming_platform", &format!(r"\b{IM}(?: (?:currently|also|now|still|mostly|mainly|only))* on ({consoles}){after}"), platform, platform_anchors);
    add(&mut rules, "gaming_platform", &format!(r"\bi (?:mostly |mainly |only |also |usually |currently )?play (?:on )?({platforms})(?:\s*(?:,|/|&|and|or)\s*|\s+)({platforms})(?:(?:\s*(?:,|/|&|and|or)\s*|\s+)({platforms}))?{after}"), platform, platform_anchors);
    add(&mut rules, "gaming_platform", &format!(r"\b(?:on|with) my (steam deck|ps5|ps4|xbox series x|xbox series s|xbox one|xbox|nintendo switch 2|nintendo switch|switch 2|quest 3|quest 2){after}"), platform, platform_anchors);

    let instruments = pick(INSTRUMENTS);
    let instrument_anchors = &["guitar", "bass", "piano", "keys", "synth", "drum", "violin", "viola", "cello", "fiddle", "trumpet", "trombone", "tuba", "horn", "euphonium", "cornet", "sax", "clarinet",
        "flute", "oboe", "bassoon", "piccolo", "harp", "banjo", "mandolin", "accordion", "bagpipe", "pipes", "uke", "harmonica", "biwa", "tabla"];
    let player_anchors = &["ist", "player", "drummer", "singer", "vocal", "fiddler", "trumpeter", "teacher", "dj", "producer", "beatmaker", "piper"];
    let players = pick(PLAYERS);
    let item = format!(r"(?:(?:the|a little|a bit of|a lil bit of|a lil|some|a little bit of) )?({instruments})");
    let joint = r"(?:,|,? and|,? &|/|,? \+)";
    add(&mut rules, "musical_instruments", &format!(concat!(r"{} (?:play|playing|played|started playing|learning|learning to play|started learning|teach|teaching|",
        r"learned to play|learnt to play|learned how to play|learnt how to play) {}(?:{} {})?(?:{} {})?\b(?![\w-]| hero| simulator| tabs?| players?| fishing)"),
        perfect, item, joint, item, joint, item), mapped(INSTRUMENTS), instrument_anchors);
    add(&mut rules, "musical_instruments", &format!(r"\b{IM}(?: (?:a|an))?(?: (?:professional|pro|classical|classically trained|jazz|self[- ]taught|amateur|hobbyist|hobby|semi[- ]pro|session|church|gigging|bedroom|metal|rock|touring|trained|working|lead|backup|bass))* ({players})\b(?!s\b|'s| (?:friend|friends|wife|husband|girlfriend|boyfriend)\b)"), mapped(PLAYERS), player_anchors);
    add(&mut rules, "musical_instruments", &format!(r"{OPEN}{HERE}(?:\w+ )?({players}) here\b"), mapped(PLAYERS), player_anchors);
    add(&mut rules, "musical_instruments", r"\bi (?:also )?sing in (?:a |the |my )?(?:church |community |local |school |college |barbershop )?(?:choir|chorus|band|choral group)\b", |_| Some("voice / singing".to_string()), &["sing in"]);
    add(&mut rules, "musical_instruments", &format!(concat!(r"\bi{} (?:dj|produce (?:music|beats|edm|techno|house|hip[- ]hop|electronic music|tracks)|make (?:beats|electronic music|edm|techno|house music)|",
        r"make music (?:in|on|with|using) (?:ableton|fl studio|logic(?: pro)?|garageband|reaper|bitwig|cubase|pro tools))\b(?![\w'-])"), ADV), |_| Some("dj / production".to_string()), &["dj", "produce", "beats", "make music", "edm", "techno"]);

    let arts = pick(ARTS);
    let art_anchors = &["bjj", "jiu", "judo", "muay", "box", "mma", "wrestl", "karate", "taekwondo", "tkd", "tae kwon", "kendo", "fenc", "hema", "capoeira", "kung fu", "wing chun", "tai chi", "aikido", "jujutsu",
        "jujitsu", "krav", "escrima", "eskrima", "kali", "arnis", "filipino martial", "sambo"];
    let fighters = pick(FIGHTERS);
    let colors = r"(?:white|yellow|orange|green|blue|purple|brown|black|red)";
    add(&mut rules, "martial_arts", &format!(concat!(r"{} (?:train|training|trained|do|doing|done|practice|practicing|practiced|practise|practising|practised|compete in|competing in|teach|teaching|coach|coaching|",
        r"started|started training|started doing|took up) (?:in )?({})(?:{} ({}))?(?:{} ({}))?\b",
        r"(?![\w-]| (?:class|classes|gym|gyms|on tv|matches|fights|events|videos|tournaments|linux|yuga|kaisen)\b)"), perfect, arts, joint, arts, joint, arts), mapped(ARTS), art_anchors);
    let holder = format!(r"\b(?:{IM}|i have|i hold|i got|i earned|i've got|ive got|i received|i was promoted to|i achieved)(?: (?:now|currently|also|just|finally|recently|a|an|my))*");
    let rank = r"(?:\d+(?:st|nd|rd|th)[- ]dan |(?:\d|one|two|three|four)[- ]stripe(?:d)? )?";
    add(&mut rules, "martial_arts", &format!(r"{holder} {rank}{colors} belt (?:in|at) ({arts})\b"), mapped(ARTS), &["belt"]);
    add(&mut rules, "martial_arts", &format!(r"{holder} {rank}({arts}) {colors} belt\b"), mapped(ARTS), &["belt"]);
    add(&mut rules, "martial_arts", &format!(r"\b{IM}(?: (?:a|an))?(?: (?:amateur|pro|professional|competitive|competition|active|lifelong))* ({fighters})\b(?!s\b|'s| (?:dog|mix|puppy|shorts|briefs)\b)"), mapped(FIGHTERS), &["judoka", "karateka", "kickboxer", "fighter", "fencer", "practitioner", "boxer"]);

    let bjj = r"(?:bjj|brazilian jiu[- ]?jitsu|jiu[- ]?jitsu|jiujitsu)";
    let belt = r"(white|blue|purple|brown|black)";
    let belted = |m: &Match| m.first_s().map(|color| format!("{color} belt"));
    add(&mut rules, "bjj_belt", &format!(r"{holder} {rank}{bjj} {belt}(?: belt)?\b(?! belts)"), belted, &["bjj", "jiu"]);
    add(&mut rules, "bjj_belt", &format!(r"{holder} {rank}{belt} belt (?:in |at )?{bjj}\b"), belted, &["bjj", "jiu"]);
    add(&mut rules, "bjj_belt", &format!(r"{OPEN}{HERE}{rank}{bjj} {belt}(?: belt)? here\b"), belted, &["bjj", "jiu"]);
    add(&mut rules, "bjj_belt", &format!(r"\b{IM}(?: (?:now|currently|also|just|a|an|only|still))* {rank}{belt} belt\b(?! (?:in|at|judo|karate|taekwondo|tkd|tae kwon do|kung fu|aikido|jujutsu|krav|hapkido|shotokan)\b)"), belted, &["bjj", "jiu jitsu", "jiu-jitsu", "jiujitsu"]);

    let persons = pick(PERSONS);
    let certificates = pick(CERTIFICATES);
    let pilot_anchors = &["pilot", "flight", "flying", "faa", "aviation", "aircraft", "cessna", "ppl", "atpl", "cfi", "airline", "part 107", "checkride"];
    add(&mut rules, "pilot_certificates", &format!(r"\b{IM}(?: (?:now|currently|also|just|finally|officially|a|an|the))*(?: (?:low[- ]time|low[- ]hour|new|newly minted|very new|recent|boring|proud|faa|easa|caa|instrument[- ]rated|certified|licensed))* ({persons})(?: (?:holder|certificate holder|license holder|licence holder))?\b(?!['\w-]| (?:student|students|training|course|exam|checkride|written|lessons?|candidate)\b)"), mapped(PERSONS), pilot_anchors);
    add(&mut rules, "pilot_certificates", &format!(r"\bi(?: (?:just|recently|finally|also|now|already|currently|officially))* (?:have|hold|got|earned|obtained|received|passed|completed|added|'ve got|ve got|have got) (?:a |an |my |the )?(?:faa |easa |caa |tc |icao |us |uk )?({certificates})(?![\w'-]| (?:student|students|training|course|lessons?|ground school|written|exam|test|theory)\b)"), mapped(CERTIFICATES), pilot_anchors);
    add(&mut rules, "pilot_certificates", &format!(r"\b{IM}(?: (?:now|currently|also|just|finally|officially))* (?:an? )?instrument[- ]rated\b"), |_| Some("instrument rating".to_string()), pilot_anchors);
    add(&mut rules, "pilot_certificates", &format!(r"{OPEN}{HERE}(?:low[- ]time |low[- ]hour |new )?({persons})(?: holder)? here\b"), mapped(PERSONS), pilot_anchors);

    let radio_anchors = &["r/amateurradio", "r/hamradio", "ham", "amateur", "radio", "licen", "exam"];
    let class = r"(technician|tech|general|extra|amateur extra)(?:[- ]class)?";
    add(&mut rules, "amateur_radio_license", r"\Ar/(?:amateurradio|hamradio): [^\n]*?(?:[\[(]\s*(technician|tech|t|general|g|extra|amateur extra|e|ae)\s*[\])]|\b(technician|general|extra)\s*\Z)", mapped(CLASSES), radio_anchors);
    add(&mut rules, "amateur_radio_license", &format!(r"\b{IM}(?: (?:now|currently|also|just|finally|officially|a|an|proud))* (?:licensed |licenced )?{class} (?:ham|licensee|operator|license holder|licence holder|ham radio operator|amateur radio operator|amateur)\b"), radio(), radio_anchors);
    add(&mut rules, "amateur_radio_license", &format!(r"\bi(?: (?:just|recently|finally|also|now|already|currently|officially))* (?:have|hold|got|earned|obtained|upgraded to|'ve got|ve got|have got)(?: (?:my|a|an|the))? (?:us |fcc |ham |amateur |amateur radio |ham radio )?{class} (?:license|licence|ticket)\b"), radio(), radio_anchors);
    add(&mut rules, "amateur_radio_license", &format!(r"\bi(?: (?:just|recently|finally|also|now|already|officially))* (?:passed|upgraded to)(?: (?:my|the))? (?:ham |amateur |amateur radio |ham radio )?{class}(?: (?:exam|test|license exam|licence exam))?(?![\w'-]| (?:ed|education|admission|surgery|anesthesia|anaesthesia|election|elections|chemistry|biology|physics|math|maths)\b)"), radio(), radio_anchors);

    let scene_anchors = &["goth", "alt", "emo", "metalhead", "headbang", "punk", "nerd", "geek", "jock", "weeb", "weeab", "otaku", "cowboy", "cowgirl", "bimbo", "gym rat", "gymrat", "hipp", "grunge",
        "skate", "nudist", "naturist"];
    let nouns = r"(?:girl|guy|boy|kid|chick|dude|gal|woman|man|lady|person|type|gf|bf|babe|boi|bro|couple|mom|dad|mum|wife|husband|teen|grrl|lesbian|femboy|twink|bear|daddy|milf|slut|bitch|queen|princess|lad|fella|nerd)";
    let nouned: Vec<String> = NOUNED.iter().map(|word| format!(r"{}(?= {nouns}\b)", escape(word))).collect();
    let label = format!("{}|{}", longest_first(LABELS.iter().copied()), nouned.join("|"));
    let chain = format!(r"({label})(?:(?: ?(?:/|&|\+|,) ?| and (?:an? )?| )({label}))?(?:(?: ?(?:/|&|\+|,) ?| and (?:an? )?| )({label}))?(?: {nouns})?");
    let adjective = r"(?:big|huge|total|massive|complete|proper|full|real|true|giant|absolute|hardcore|diehard|die[- ]hard|casual|average|typical|resident|certified|self[- ]proclaimed|self[- ]confessed|lifelong|life[- ]long|longtime|long[- ]time|full[- ]time|part[- ]time|home|practicing|practising|proud|baby|old|elder|old[- ]school|trad|tattooed|little|lil|tall|short|chubby|thick|curvy|petite|skinny|fat|tiny|nerdy|geeky|lesbian|gay|queer|trans|bi|straight|millennial|aging|ageing|middle[- ]aged|older|young|hairy|bearded|hot|cute|shy|lonely|sad|weird|wannabe|closet|closeted|secret|horny|slutty|dumb|ditzy|alternative|fit|masc|femme|black|white|asian|latina|latino|filthy|dirty|bored|kinky|sexy|busty|hung|smooth|awkward|introverted|quiet|grumpy|happy|silly|goofy|loud|crazy|fellow|socially awkward|single|married|local)";
    let block = r"(?![\w'-]| (?:fan|fans|band|bands|music|song|songs|show|shows|phase|scene|style|look|aesthetic|account|squad|culture|movie|movies|fashion|stuff|vibes?|club|position|outfits?|costumes?|clothes|clothing|makeup|hair|haircut|bar|night|party|subreddit|sub|community|crowd|stereotype|meme|trope|joke|bimbofication|transformation|hypno|game|games|hat|boots|ride|riding|strap|rock|metal|rap|rapper|ass|adjacent|inspired|ish)\b)";
    let scenes = |m: &Match| value_of(SCENES, m);
    rules.push(needs(rule("subculture", &format!(concat!(r"\b{}(?: (?:also|still|now|just|basically|actually|really|totally|definitely|kinda|kind of|sort of|pretty much|literally|honestly|technically|always|lowkey|low key))*",
        r"(?: (?:a|an|such a|such an|bit of a|bit of an|a bit of a|a bit of an|kind of a|kind of an|sort of a|sort of an|kinda a|kinda an|something of a|somewhat of a|another|your|ur|the|total|full|complete|proper))?",
        r"(?: {})* {}{}"), IM, adjective, chain, block), scenes, hedge()), scene_anchors));
    rules.push(needs(rule("subculture", &format!(r"{OPEN}(?:a |an |just a |just an |fellow |another |proud |old |big |huge |total )?(?:{adjective} )*{chain} here\b"), scenes, hedge()), scene_anchors));
    rules.push(needs(rule("subculture", &format!(r"{TAG}[\s,/|-]+(?:a |an )?(?:{adjective} )*{chain}{block}"), scenes, hedge()), scene_anchors));
    rules.push(needs(rule("subculture", &format!(r"\bas an? (?:{adjective} )*{chain}(?: myself)?(?=,| myself\b| i\b| i'm\b| im\b)"), scenes, hedge()), scene_anchors));
    let styles = longest_first(STYLES.iter().copied());
    rules.push(needs(rule("subculture", &format!(r"\bi(?: (?:usually|mostly|often|always|still|also|generally|tend to|like to))* dress (?:in an? |in |very |pretty |kinda |kind of |mostly |quite |super |really |fairly )?({styles})(?: (?:style|clothes|clothing|fashion|aesthetic))?\b(?![\w'-])"), scenes, hedge()), scene_anchors));

    let golf_anchors = &["handicap", "hcp", "hdcp", "golf"];
    let stroke = r"(\+?\d{1,2}(?:\.\d)?)";
    let cap = r"(?:handicap|hcp|hdcp|handicapper|capper)";
    add(&mut rules, "golf_handicap", &format!(r"\b{IM}(?: (?:currently|now|only|just|still|about|around|roughly|like|basically))* (?:a |an )?(?:~|about |around |roughly )?{stroke}(?:ish)?[- ]?{cap}\b"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"\bmy (?:golf |current |official |ghin |whs )?(?:handicap|hcp|hdcp)(?: index)? (?:is|is now|is currently|sits at|of|:|has dropped to|dropped to|is down to|went down to|is at|is around|is about|hovers around)(?: (?:a|an|around|about|like|~|currently|now|only|roughly|at))* ~?{stroke}\b(?!\s*(?:-|to|and)\s*\d|%)"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"{OPEN}{HERE}{stroke} ?(?:handicap|hcp|hdcp)(?: golfer| player)? here\b"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"{OPEN}{stroke} ?(?:hcp|hdcp)\b(?=\s*(?:$|[.,!;:)\n]|\b(?:here|and|but|so|golfer|player)\b))"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"\bi{ADV} (?:have|carry|play to|play off) (?:a |an )?{stroke}[- ]?(?:handicap|hcp|hdcp)\b"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"{OPEN}(?:current )?(?:handicap|hcp|hdcp)(?: index)? (?:is|is at|is now|is currently|currently|sits at|of)(?: (?:a|an|around|about|~|now))* {stroke}\b(?!\s*(?:-|to|and)\s*\d|%)"), handicap, golf_anchors);
    add(&mut rules, "golf_handicap", &format!(r"\bi(?:'m| am)? (?:currently |now )?play(?:ing)? off (?:of )?(?:a |an )?{stroke}(?: handicap| hcp| hdcp)?\b(?!\s*(?:-|to)\s*\d)"), handicap, &["golf"]);
    add(&mut rules, "golf_handicap", &format!(r"\b{IM}(?: (?:a|an))? scratch (?:golfer|player)\b"), |_| Some("0".to_string()), golf_anchors);

    let chess_anchors = &["chess", "fide", "uscf"];
    let elo = r"(\d{3,4})";
    let level = r"(?: (?:currently|now|only|just|still|about|around|roughly|like))*";
    add(&mut rules, "chess_rating", &format!(r"\bmy (?:(?:current|chess|fide|uscf|lichess|chess\.com|chess com|online|otb|rapid|blitz|bullet|classical|official) )*(?:elo|rating)(?: on (?:lichess|chess\.com|chess com))?(?: (?:in )?(?:rapid|blitz|bullet|classical))? (?:is|is now|is currently|is around|is about|sits at|hovers around|is at|of|:)(?: (?:around|about|like|roughly|only|now|currently|just|a|an|~|at))* ~?{elo}\b(?!\s*(?:-|to)\s*\d|\s*(?:/|out of))"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\b{IM}{level} rated (?:at |around |about |roughly |~)?{elo}\b(?!\s*(?:-|to)\s*\d)"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\b{IM}{level} (?:a |an )?(?:~|around |about )?{elo}\+? ?(?:elo|rated|fide|uscf)\b"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\bi (?:have|got|hold|reached|achieved)(?: (?:a|an|my))? (?:(?:fide|uscf|lichess|chess\.com|rapid|blitz|bullet|classical) )*(?:rating|elo) of (?:around |about |~)?{elo}\b"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\b{IM}{level} (?:~|around |about )?{elo}\+? (?:on|in) (?:lichess|chess\.com|chess com)\b"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\bmy (?:rapid|blitz|bullet|classical)(?: (?:rating|elo))? (?:is|is now|is around|is about|sits at|:)(?: (?:only|around|about|like|~|now|currently))* {elo}\b(?!\s*(?:-|to)\s*\d)"), ranged(100.0, 3000.0), chess_anchors);
    add(&mut rules, "chess_rating", &format!(r"\bi (?:have|hold|got) (?:a |an )(?:~|around |about )?{elo} (?:fide|uscf|lichess|chess\.com|rapid|blitz|classical)(?: rating| elo)?\b"), ranged(100.0, 3000.0), chess_anchors);

    let typing_anchors = &["wpm", "words per minute", "words a minute"];
    let speed = r"(\d{2,3})(?:\s*(?:-|to)\s*(\d{2,3}))?";
    let wpm = r"\+? ?(?:wpm|words per minute|words a minute)";
    add(&mut rules, "typing_speed", &format!(r"\bi(?: (?:can|usually|normally|currently|typically|generally|easily|consistently))* (?:type|average|can do|type at)(?: (?:at|around|about|roughly|like|over|~|between))* ~?{speed}{wpm}"), ranged(20.0, 250.0), typing_anchors);
    add(&mut rules, "typing_speed", &format!(r"\bmy (?:typing speed|wpm|average typing speed|typing)(?: is| sits at| is around| is about| of| is like|:)(?: (?:around|about|like|roughly|~))* ~?{speed}\b"), ranged(20.0, 250.0), typing_anchors);
    add(&mut rules, "typing_speed", &format!(r"\bi (?:have|got) (?:a )?typing speed of (?:around |about |~)?{speed}\b"), ranged(20.0, 250.0), typing_anchors);

    let run_anchors = &["5k", "5 k", "parkrun"];
    let time = r"(\d{1,2}):([0-5]\d)(?![:\d]| ?/ ?(?:km|mi|mile|k)\b| ?(?:per|min ?/|/))";
    let five = r"(?:5 ?km?|parkrun)";
    add(&mut rules, "running_5k_time", &format!(r"\bmy (?:current |new |latest |best |recent |official )?{five} (?:pr|pb|time|personal best|personal record|best|record)(?: time)?(?: is| was|:| -| of| stands at| is now| is currently| sits at| =)?(?: (?:a|an|around|about|~|now|currently|just|right))* ~?{time}"), minutes, run_anchors);
    add(&mut rules, "running_5k_time", &format!(r"\bi(?: (?:just|finally|recently|also|actually))* (?:ran|run|did|finished|clocked|set|completed) (?:a |an |my |the )?(?:new |first |best )?(?:(?:pr|pb) (?:of |in )?)?~?{time}(?: min(?:ute)?s?)? (?:{five}|for (?:a |the |my )?{five})\b"), minutes, run_anchors);
    add(&mut rules, "running_5k_time", &format!(r"\bi(?: (?:just|finally|recently|also))* (?:ran|run|did|finished|completed|clocked) (?:a |an |my |the )?(?:first |fastest |best |new )?{five}(?: (?:pr|pb|race|time trial))? in (?:about |around |~)?{time}"), minutes, run_anchors);
    add(&mut rules, "running_5k_time", &format!(r"(?:^|\n)\s*(?:[-*]\s*)?{five}(?: (?:pr|pb))?\s*[:=-]\s*~?{time}"), minutes, run_anchors);
    add(&mut rules, "running_5k_time", &format!(r"{OPEN}(?:current |new )?{five} (?:pr|pb)(?: is|:| -| of| =)? ~?{time}"), minutes, run_anchors);

    let cube_anchors = &["ao5", "ao12", "ao50", "ao100", "3x3", "cfop", "cube", "cubing", "roux"];
    let solve = r"(\d{1,3}(?:\.\d{1,2})?)";
    add(&mut rules, "speedcubing_average", &format!(r"\bmy (?:3x3 |current |global |overall )*(?:average|avg|ao5|ao12|ao50|ao100|ao1000)(?: (?:on|for|in) (?:the )?3x3)? (?:is|:|of|is now|is around|is about|is currently|sits at|is like)(?: (?:around|about|like|roughly|~|now|currently|a))* ~?{solve}(?: ?(?:seconds|secs|sec|s))?\b(?!\s*(?:-|to)\s*\d| ?(?:%|mph|km|miles|min|minutes|hours|hrs|years|days|percent|wpm|fps|hz|ms\b|lbs?|kg|points|moves))"), ranged(3.0, 180.0), cube_anchors);
    add(&mut rules, "speedcubing_average", &format!(r"\bi(?: (?:currently|now|usually|generally|still|consistently))* average (?:around |about |roughly |like |~)?(?:{solve} ?(?:seconds|secs|sec|s)\b|(\d{{1,3}}(?:\.\d{{1,2}})?)(?= (?:on|with|for|in) (?:the |a )?(?:3x3|cfop|roux|zz)\b)|(\d{{1,3}}\.\d{{1,2}})\b)(?!\s*(?:-|to)\s*\d)"), ranged(3.0, 180.0), cube_anchors);

    let ram_anchors = &["ram", "memory"];
    let spec_anchors = &["my specs", "my pc", "my build", "my rig", "my setup", "my system", "my computer", "my laptop", "my config", "my current", "my desktop", "my machine"];
    let gb = r"(?:(\d) ?x ?)?(\d{1,3}) ?gb";
    let ram = r"(?: (?:of )?(?:ddr\d\w*|lpddr\d\w*|unified|system|\d{4} ?mhz|cl\d+))*(?: of)? (?:ram|memory)\b";
    let owner = format!(r"\b(?:i(?: (?:only|also|now|currently|just))* (?:have|run|use|got|installed|upgraded to|added|'ve got|ve got|have got)|{IM}(?: (?:currently|now|only))* (?:running|rocking|using|on|working with)|my (?:pc|computer|laptop|rig|build|system|machine|desktop|setup|mac|macbook|pc build|gaming pc|server) (?:has|only has|came with|is running|runs|uses))(?: (?:a|an|only|just|about|around|a whopping|like|~|over))*");
    add(&mut rules, "ram_gb", &format!(r"{owner} {gb}{ram}(?! (?:on|in) (?:my|the|a) (?:phone|tablet|ipad))"), memory, ram_anchors);
    add(&mut rules, "ram_gb", &format!(r"(?:^|[\n|•,;(]\s*)(?:[-*]\s*)?(?:ram|memory|system memory)\s*[:=-]\s*{gb}\b"), |m: &Match| if TENTATIVE.test(m.string) { None } else { memory(m) }, spec_anchors);
    add(&mut rules, "ram_gb", &format!(r"\bmy {gb}{ram}"), memory, ram_anchors);
    add(&mut rules, "ram_gb", &format!(r"{RIG_FLAIR}{gb}{ram}"), memory, ram_anchors);
    add(&mut rules, "ram_gb", &format!(r"\b(?:i{ADV} (?:have|own|use|got|bought|built)|my) (?:an? |the )?(?:[\w-]+ ){{1,4}}?with {gb}{ram}"), memory, ram_anchors);

    let gpu = r"((?:(?:nvidia|geforce|amd|radeon|intel) )*(?:(?:rtx|gtx) ?\d{3,4}(?: ?(?:ti super|ti|super))?|rx ?\d{3,4}(?: ?(?:xtx|xt|gre))?|rx ?vega ?\d{2}|radeon (?:vii|\d{3,4}m?)|arc ?[ab]\d{3}))\b";
    let cpu = r"((?:(?:intel|amd) )?(?:core )?(?:i[3579][- ]\d{4,5}[a-z]{0,2}|i[3579] \d{1,2}th gen)|(?:intel (?:core )?|core )i[3579]|(?:(?:intel|amd) )?(?:core )?(?:ryzen [3579](?: pro)? \d{4}[a-z0-9]{0,3}|ryzen [3579]|ryzen \d{4}x3d|core ultra [579] \d{3}[a-z]?|threadripper \d{4}\w*|[1-9]\d{3}x3d|[3-9]\d00x|[5-9]950x|1[0-4][4-9]00k[fs]?))\b";
    let gear = r"(?: (?:a|an|the|my|this|one|two|2|dual|new|used|brand new|second[- ]hand|refurbished|an old|old))*";
    let have = format!(r"\bi{ADV} (?:have|run|use|own|got|bought|built|installed|upgraded to|'ve got|ve got|have got|went with|picked up|snagged|game on|play on)");
    let using = format!(r"\b{IM}{ADV} (?:running|rocking|using|on|stuck with|stuck on|gaming on|playing on)");
    let mine = r"\bmy (?:(?:new|current|trusty|main|own|lowly|aging|ancient|humble|beloved|poor|little) )*(?:(?:gpu|graphics card|video card|card|pc|computer|laptop|rig|build|system|machine|desktop|setup|gaming pc|gaming laptop|cpu|processor|chip) (?:is|has|runs|uses|came with|is running)(?: (?:a|an|the|only|just))* )?";
    let gpu_anchors = &["rtx", "gtx", "rx", "radeon", "arc"];
    let cpu_anchors = &["ryzen", "i3", "i5", "i7", "i9", "core ultra", "x3d", "00x", "50x", "00k", "threadripper"];
    let keep = |m: &Match| m.first_s();
    let silent = |part: &str| part.replacen('(', "(?:", 1);
    for (attribute, part, other, label, anchors) in [("gpu", gpu, silent(cpu), r"(?:gpu|graphics|graphics card|video card|gfx)", gpu_anchors as &[&str]),
        ("cpu", cpu, silent(gpu), r"(?:cpu|processor|proc)", cpu_anchors as &[&str])] {
        let paired = format!(r"(?:{other}(?: \d{{1,2}} ?gb)?(?:,|,? and|,? with|,? \+|/)(?: an?| the| my)? )?");
        add(&mut rules, attribute, &format!(r"{have}{gear} {paired}{part}"), keep, anchors);
        add(&mut rules, attribute, &format!(r"{using}{gear} {paired}{part}"), keep, anchors);
        add(&mut rules, attribute, &format!(r"{mine}{part}"), keep, anchors);
        add(&mut rules, attribute, &format!(r"{RIG_FLAIR}{part}"), keep, anchors);
        add(&mut rules, attribute, &format!(r"(?:^|[\n|•,;(]\s*)(?:[-*]\s*)?{label}\s*[:=-]\s*{part}"), listed, spec_anchors);
    }

    let phone = concat!(r"((?:apple )?iphone(?: ?(?:\d{1,2}[sc]?|xs|xr|x|se))?(?: ?(?:pro max|pro|plus|mini|max|e))?|(?:google )?pixel ?\d{1,2}a?(?: (?:pro xl|pro fold|pro|xl|fold))?|",
        r"(?:samsung )?galaxy (?:s\d{1,2}(?: ?(?:ultra|plus|fe|\+|u))?|note ?\d{1,2}(?: ultra)?|z ?(?:fold|flip) ?\d|a\d{2})|samsung (?:s\d{1,2}(?: ?(?:ultra|plus|fe|\+))?|a\d{2}|z ?(?:fold|flip) ?\d)|",
        r"s(?:2\d|1\d) ?(?:ultra|plus|fe|u)|oneplus ?\d{1,2}[rt]?(?: pro)?|(?:xiaomi|redmi note|redmi|poco [xfm]) ?\d{1,2}[a-z]?(?: (?:pro\+?|ultra|lite))?|iqoo (?:neo )?\d{1,2}r?|nothing phone ?\(?\d\)?)",
        r"(?!['\w+-]| (?:case|cases|charger|cable|app|apps|game|games|emulator|version|screen protector)\b)");
    let phone_anchors = &["iphone", "pixel", "galaxy", "samsung", "oneplus", "xiaomi", "redmi", "poco", "iqoo", "nothing phone", "ultra", "s2", "s1"];
    add(&mut rules, "phone", &format!(r"\bi{ADV} (?:have|use|own|got|bought|switched to|upgraded to|'ve got|ve got|have got|went with|picked up|daily drive|daily)(?: (?:a|an|the|my|this|new|used|brand new|second[- ]hand|refurbished))* {phone}"), keep, phone_anchors);
    add(&mut rules, "phone", &format!(r"\b{IM}{ADV} (?:on|using|rocking|stuck with|stuck on|still on)(?: (?:a|an|the|my|this|new))* {phone}"), keep, phone_anchors);
    add(&mut rules, "phone", &format!(r"\bmy (?:(?:new|current|trusty|main|own|daily|personal) )*{phone}"), keep, phone_anchors);
    add(&mut rules, "phone", &format!(r"(?:{OPEN}{HERE}|\b{IM} (?:a |an )?(?:proud |happy |longtime |long[- ]time |lifelong )?){phone} (?:user|owner)\b"), keep, phone_anchors);

    let makes = longest_first(MAKES.iter().copied());
    let models = longest_first(MODELS.iter().copied());
    let branded = longest_first(BRANDED.iter().copied());
    let drive = r"\b(?:i(?: (?:also|now|currently|still|just|recently|finally|actually|only))* (?:drive|own|have|bought|got|daily|daily drive|'ve got|ve got|have got)|my)";
    let trim = r"(?: (?:a|an|the|new|used|brand new|little|trusty|beloved|current|lifted|stock|modded|manual|automatic|white|black|red|blue|silver|grey|gray|green|awd|4x4|limited|sport|base|'?\d{2}|(?:19|20)\d{2}|\d(?:st|nd|rd|th) gen))*";
    let car = format!(r"(?:(?:({makes}) )?({models})|({makes}) ({branded})|({makes}))\b(?![\w'-]| (?:dealership|dealer|parts|commercial|ad|ads|stock|shares|factory|plant|logo|duty|duties|center|centre|engagement|pride|responsibility|responsibilities|life|society|groups?|leaders?|space|education|rights|sense|virtue)\b)");
    add(&mut rules, "vehicles", &format!(r"{drive}{trim} {car}"), named, &[]);

    let enthusiasts = longest_first(ENTHUSIASTS.iter().copied());
    let amateurs = longest_first(AMATEURS.iter().copied());
    let keen = r"(?:avid|amateur|hobbyist|hobby|keen|passionate|casual|weekend|recreational|enthusiastic)";
    let big = r"(?: (?:big|huge|avid|total|massive|hardcore|casual|passionate|keen|lifelong|life[- ]long|proud|self[- ]proclaimed|bit of an?|real|true|serious|amateur|hobbyist|pc|console|retro|home|giant))*";
    let unpaid = r"\b(?!s\b|'s| (?:by trade|by profession|for a living)\b)";
    add(&mut rules, "hobbies", &format!(r"\b{IM}(?: (?:a|an))?{big} ({enthusiasts}){unpaid}"), keep, &[]);
    add(&mut rules, "hobbies", &format!(r"\b{IM}(?: (?:a|an))? (?:\w+ )?{keen} ({amateurs}){unpaid}"), keep, &[]);
    add(&mut rules, "hobbies", &format!(r"{OPEN}(?:a |an |just a |fellow |another |big |huge |avid )*({enthusiasts}) here\b"), keep, &[]);
    rules
}

fn hobbies(lowered: &[char], found: &mut Found) {
    for lead in HOBBY_LEAD.iter(lowered) {
        let start = lead.end();
        let lead_text = st(strip_space(lead.text()));
        let verbs = lead_text.ends_with(" to") || lead_text.ends_with(" i");
        let stop = next_mark(lowered, start, ".!?\n;():").min(start + 160);
        if hedged(lowered, lead.start(), stop, self_hedge()) {
            continue;
        }
        for (index, piece) in re_split(&PIECES, &lowered[start..stop]).into_iter().enumerate() {
            if ABOUT.test(piece) {
                continue;
            }
            let piece = QUALIFIER.sub(piece, "");
            let piece = FILLER.sub(&piece, "");
            let name = st(strip_space(&piece));
            match HOBBIES.get(&name).or_else(|| if verbs { DOINGS.get(&name) } else { None }) {
                Some(value) => found.set("hobbies", *value, start),
                None if index == 0 && OBJECT.test(&piece) => break,
                None => {}
            }
        }
    }
}

pub fn interests(lowered: &[char], found: &mut Found) {
    let bits = present(lowered);
    for (entry, mask) in RULES.iter().zip(&GATES.rules) {
        if mask.as_ref().is_some_and(|mask| !meets(&bits, mask)) {
            continue;
        }
        for m in entry.re.iter(lowered) {
            if let Some(stated) = (entry.value)(&m) {
                if !hedged(lowered, m.start(), m.end(), entry.hedge) {
                    for value in stated.split('|') {
                        found.set(entry.attribute, value, m.start());
                    }
                }
            }
        }
    }
    if meets(&bits, &GATES.hobbies) {
        hobbies(lowered, found);
    }
    let devices: Vec<(String, String, usize)> = found.items.iter().filter(|(attribute, _, _)| attribute == "phone" || attribute == "cpu").cloned().collect();
    for (attribute, value, position) in devices {
        if attribute == "cpu" {
            found.set("cpu", vendor(&value), position);
        } else {
            found.set("phone", handset(&value), position);
        }
    }
}

fn vendor(cpu: &str) -> &'static str {
    if cpu.contains("intel") || cpu.contains("core") || cpu.starts_with('i') || cpu.ends_with('k') || cpu.ends_with("kf") || cpu.ends_with("ks") {
        "intel"
    } else if cpu.contains("ryzen") || cpu.contains("threadripper") || cpu.ends_with('x') || cpu.ends_with("x3d") {
        "amd"
    } else {
        panic!("cpu {cpu:?} has no vendor")
    }
}

fn handset(phone: &str) -> &'static str {
    if phone.contains("iphone") {
        "iphone"
    } else if phone.contains("pixel") {
        "pixel"
    } else if phone.contains("galaxy") || phone.contains("samsung") || phone.starts_with('s') {
        "samsung"
    } else if phone.contains("oneplus") {
        "oneplus"
    } else if phone.contains("xiaomi") || phone.contains("redmi") || phone.contains("poco") {
        "xiaomi"
    } else if phone.contains("iqoo") {
        "iqoo"
    } else if phone.contains("nothing") {
        "nothing"
    } else {
        panic!("phone {phone:?} has no brand")
    }
}

pub fn init() {
    timed("fandom.interests.init", || {
        LazyLock::force(&RULES);
        LazyLock::force(&GATES);
        for re in [&HOBBY_LEAD, &ABOUT, &PIECES, &QUALIFIER, &FILLER, &OBJECT] {
            LazyLock::force(re);
        }
        LazyLock::force(&HOBBIES);
        LazyLock::force(&DOINGS);
        LazyLock::force(&TENTATIVE);
        LazyLock::force(&HAM);
    });
}
