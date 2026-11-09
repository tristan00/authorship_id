mod characters;
mod cues;
mod fandom;
mod interests;
mod lexicon;

use claimcore::*;
use std::sync::LazyLock;

pub use characters::characters;
pub use fandom::{adjacent, fandom, favorites};

pub fn rules() -> &'static [Rule] {
    &[]
}

pub fn init() {
    LazyLock::force(&lexicon::LEXICON);
    LazyLock::force(&lexicon::INDEX);
    fandom::init();
    characters::init();
    cues::init();
    interests::init();
}
