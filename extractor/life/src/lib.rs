mod home;
mod lifestyle;
mod parental;
mod relationship;
mod shared;

use claimcore::*;
use std::sync::LazyLock;

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    let mut rules = relationship::build();
    rules.extend(parental::build());
    rules.extend(shared::scoped_rules(home::pets()));
    rules.extend(shared::scoped_rules(home::living()));
    rules.extend(home::housing());
    rules
});
static LIFESTYLE: LazyLock<Vec<Rule>> = LazyLock::new(lifestyle::build);

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn lifestyle_rules() -> &'static [Rule] {
    &LIFESTYLE
}

pub fn init() {
    timed("life.init", || {
        let gated = LIFESTYLE.iter().filter(|entry| entry.gate.is_some()).count();
        log(&format!("life rules={} lifestyle rules={} lifestyle gated={gated}", RULES.len(), LIFESTYLE.len()));
    });
}
