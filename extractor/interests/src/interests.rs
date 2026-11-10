use aho_corasick::AhoCorasick;
use claimcore::*;
use std::sync::LazyLock;

const IM: &str = r"(?:i'm|im|i am)";
const OPEN: &str = concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,(]\s*)");

const SCENES: &[(&str, &str)] = &[("goth", "goth"), ("gothic", "goth"), ("alt", "alt"), ("alternative", "alt"), ("emo", "emo"), ("metalhead", "metalhead"), ("headbanger", "metalhead"),
    ("punk", "punk"), ("punk rocker", "punk"), ("punk rock", "punk"), ("nerd", "nerd / geek"), ("geek", "nerd / geek"), ("nerdy", "nerd / geek"), ("geeky", "nerd / geek"), ("jock", "jock"),
    ("weeb", "otaku / weeb"), ("weeaboo", "otaku / weeb"), ("otaku", "otaku / weeb"), ("cowboy", "cowboy / western"), ("cowgirl", "cowboy / western"), ("western", "cowboy / western"),
    ("bimbo", "bimbo"), ("bimboi", "bimbo"), ("gym rat", "gym rat"), ("gymrat", "gym rat"), ("hippie", "hippie"), ("hippy", "hippie"), ("grunge", "grunge"), ("skater", "skater"),
    ("skateboarder", "skater"), ("nudist", "nudist / naturist"), ("naturist", "nudist / naturist")];
const LABELS: &[&str] = &["goth", "emo", "metalhead", "headbanger", "punk", "punk rocker", "nerd", "geek", "jock", "weeb", "weeaboo", "otaku", "cowboy", "cowgirl", "bimbo", "bimboi", "gym rat",
    "gymrat", "hippie", "skater", "skateboarder", "nudist", "naturist"];
const NOUNED: &[&str] = &["alt", "alternative", "gothic", "nerdy", "geeky", "hippy", "grunge", "punk rock"];
const STYLES: &[&str] = &["goth", "gothic", "alt", "alternative", "emo", "punk", "grunge", "hippie", "hippy", "skater", "western"];
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
    concat!(r"(?:^", claimcore::flair!(), r"|\n)\s*(?:hobbies(?: and interests)?|interests)\s*[:-]|(?:i'm|im|i am)(?: (?:really|very|also|super|heavily|big|huge|mostly|mainly|kinda|pretty|quite))* into|"),
    r"i (?:really |also |absolutely |truly |just |genuinely |especially |do )?(?:love|like|enjoy|adore)(?: to)?|(?:i'm|im|i am) (?:also |really |very )?interested in|",
    concat!(r"(?:(?<=^|[.!?\n]|[.!?\n] |[.!?\n]  )|\A", claimcore::flair!(), r")(?:also |really )?(?:love|enjoy|into)|"),
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
const HOBBY_GROUPS: [(&str, &str); 12] = [
    ("gaming", r"\b(?:gaming|gamer|video ?games?|play (?:video )?games)\b"),
    ("reading", r"\b(?:reading|reader|i read|books?)\b"),
    ("music", r"\b(?:music|guitar|piano|singing|play (?:the )?\w+ instrument)\b"),
    ("art and drawing", r"\b(?:art|drawing|painting|sketching|illustration|digital art)\b"),
    ("crafts", r"\b(?:knitting|crochet(?:ing)?|sewing|woodworking|crafts?|crafting|embroidery|pottery)\b"),
    ("cooking and baking", r"\b(?:cooking|baking|cook|bake)\b"),
    ("outdoors", r"\b(?:hiking|camping|fishing|hunting|backpacking|kayaking|outdoors)\b"),
    ("sports and fitness", r"\b(?:gym|lifting|running|cycling|climbing|swimming|yoga|martial arts|golf|tennis|soccer|football|basketball)\b"),
    ("collecting", r"\b(?:collecting|collector|collection)\b"),
    ("photography", r"\b(?:photography|photographer)\b"),
    ("gardening", r"\b(?:gardening|gardener|garden)\b"),
    ("anime and tv", r"\b(?:anime|manga|watching (?:tv|movies|shows))\b"),
];
static GROUPS: LazyLock<Vec<(&str, Re)>> = LazyLock::new(|| HOBBY_GROUPS.iter().map(|(group, pattern)| (*group, Re::new(pattern))).collect());
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

fn add(rules: &mut Vec<Rule>, attribute: &'static str, pattern: &str, value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static, anchors: &[&str]) {
    let entry = rule(attribute, pattern, value, self_hedge());
    rules.push(if anchors.is_empty() { entry } else { needs(entry, anchors) });
}

fn build() -> Vec<Rule> {
    let mut rules = Vec::new();
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

    let keep = |m: &Match| m.first_s();
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
}

pub fn settle(found: &mut Found) {
    let mut grouped: Vec<(&'static str, usize, Origin)> = Vec::new();
    for (_, value, position, origin) in found.items.iter().filter(|(attribute, ..)| attribute == "hobbies") {
        let value = chars(value);
        grouped.extend(GROUPS.iter().filter(|(_, pattern)| pattern.test(&value)).map(|(group, _)| (*group, *position, *origin)));
    }
    for (group, position, origin) in grouped {
        found.put("hobby_group", group, position, origin);
    }
}

pub fn init() {
    timed("interests.init", || {
        LazyLock::force(&RULES);
        LazyLock::force(&GROUPS);
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

fn re_split<'a>(re: &Re, s: &'a [char]) -> Vec<&'a [char]> {
    let mut pieces = Vec::new();
    let mut last = 0;
    for m in re.iter(s) {
        pieces.push(&s[last..m.start()]);
        last = m.end();
    }
    pieces.push(&s[last..]);
    pieces
}
