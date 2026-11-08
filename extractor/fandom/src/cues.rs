use aho_corasick::{AhoCorasick, AhoCorasickKind};
use std::sync::LazyLock;

pub const POSITIVE: &[&str] = &[
    " love", " adore", " enjoy", " like", " dig", " recommend", " second", " rewatched", " replayed", " obsessed", " addicted", " into", " fan of", " hooked", " enough of",
    " fav", " good", " great", " amazing", " awesome", " excellent", " fantastic", " underrated", " underappreciated", " goat", " incredible", " perfect", " beautiful", " fun",
    " peak", " fire", " best", " jam", " banger", " masterpiece", " classic", " brilliant", " phenomenal", " gorgeous", " wonderful", " playing", " watching", " listening",
    " reading", " bingeing", " binging", " replaying", " rewatching", "for me", "mine is", "hands down",
];
pub const PRAISED: &[&str] = &[" peak", " goat", " amazing", " incredible", " underrated", " phenomenal", " masterpiece", " banger", " fire", " elite", "tier", " best"];
pub const LIKED_PERSON: &[&str] = &[" like ", " liked "];
pub const CHOICE: &[&str] = &["^("];
pub const CREATED: &[&str] = &[" vid", " stream", " vod", " channel", " podcast", " content", " vlog"];
pub const WATCHED: &[&str] = &[" youtube", " twitch", " tiktok", " kick"];
pub const LISTENED: &[&str] = &[" listen", " jamming to ", " bumping "];
pub const ALBUM: &[&str] = &["'s ", "s' "];
pub const ALBUM_WORDS: &[&str] = &[" album", " song", " single", " discography", " tour", " concert", " record", " ep", " lp", " music", " vocals", " lyrics"];
pub const SEEN: &[&str] = &[" saw ", " seen ", " see ", " seeing "];
pub const SEEN_WORDS: &[&str] = &[" live", " in concert", " perform", " play live", " open for"];
pub const WROTE: &[&str] = &[" book", " novel", " series", " trilogy", " saga", " writing"];
pub const WRITTEN_BY: &[&str] = &["by "];
pub const FAVOURED: &[&str] = &["fav", "^(like"];
pub const FAV: &[&str] = &["fav"];
pub const LOVED: &[&str] = &["love ", "loved ", "adore ", "adored ", "enjoy ", "enjoyed ", "obsessed with "];
pub const GOAT: &[&str] = &["goat ", "goat:"];
pub const CRUSH: &[&str] = &["crush on ", "crushes on "];
pub const STAN: &[&str] = &[" stan "];
pub const FAN_OF: &[&str] = &[" fan of ", " supporter of ", " admirer of "];

const LISTS: &[&[&str]] = &[POSITIVE, PRAISED, LIKED_PERSON, CHOICE, CREATED, WATCHED, LISTENED, ALBUM, ALBUM_WORDS, SEEN, SEEN_WORDS, WROTE, WRITTEN_BY, FAVOURED, FAV, LOVED, GOAT, CRUSH, STAN, FAN_OF];

static WORDS: LazyLock<Vec<&'static str>> = LazyLock::new(|| {
    let mut words: Vec<&'static str> = Vec::new();
    for list in LISTS {
        for word in *list {
            if !words.contains(word) {
                words.push(word);
            }
        }
    }
    assert!(words.len() <= 256);
    words
});

static MATCHER: LazyLock<AhoCorasick> = LazyLock::new(|| AhoCorasick::builder().kind(Some(AhoCorasickKind::DFA)).build(WORDS.iter()).unwrap());

#[derive(Clone, Copy)]
pub struct Mask([u64; 4]);

pub fn mask(words: &[&str]) -> Mask {
    let mut bits = [0u64; 4];
    for word in words {
        let index = WORDS.iter().position(|w| w == word).unwrap_or_else(|| panic!("unknown cue {word}"));
        bits[index / 64] |= 1 << (index % 64);
    }
    Mask(bits)
}

macro_rules! masks {
    ($($name:ident),*) => {
        #[allow(non_snake_case)]
        pub struct Masks { $(pub $name: Mask),* }
        pub static MASKS: LazyLock<Masks> = LazyLock::new(|| Masks { $($name: mask($name)),* });
    };
}

masks!(POSITIVE, PRAISED, LIKED_PERSON, CHOICE, CREATED, WATCHED, LISTENED, ALBUM, ALBUM_WORDS, SEEN, SEEN_WORDS, WROTE, WRITTEN_BY, FAVOURED, FAV, LOVED, GOAT, CRUSH, STAN, FAN_OF);

pub struct Cues([u64; 4]);

fn cue_byte(c: char) -> u8 {
    if c.is_ascii() {
        return c.to_ascii_lowercase() as u8;
    }
    if c == '\u{2019}' {
        return b'\'';
    }
    let mut lowered = c.to_lowercase();
    if let (Some(l), None) = (lowered.next(), lowered.next()) {
        if l.is_ascii() {
            return l as u8;
        }
    }
    let mut raised = c.to_uppercase();
    if let (Some(u), None) = (raised.next(), raised.next()) {
        if u.is_ascii() {
            return u.to_ascii_lowercase() as u8;
        }
    }
    0x80
}

impl Cues {
    pub fn of(text: &[char]) -> Cues {
        let buffer: Vec<u8> = text.iter().map(|&c| cue_byte(c)).collect();
        let mut bits = [0u64; 4];
        for found in MATCHER.find_overlapping_iter(&buffer) {
            let index = found.pattern().as_usize();
            bits[index / 64] |= 1 << (index % 64);
        }
        Cues(bits)
    }

    pub fn any(&self, mask: Mask) -> bool {
        (0..4).any(|i| self.0[i] & mask.0[i] != 0)
    }
}

pub fn init() {
    LazyLock::force(&MATCHER);
    LazyLock::force(&MASKS);
}

thread_local! {
    static LAST: std::cell::RefCell<(Vec<char>, [u64; 4])> = const { std::cell::RefCell::new((Vec::new(), [0; 4])) };
}

pub fn cues_of(text: &[char]) -> Cues {
    LAST.with(|last| {
        let mut last = last.borrow_mut();
        if last.0.as_slice() != text {
            let found = Cues::of(text);
            *last = (text.to_vec(), found.0);
        }
        Cues(last.1)
    })
}
