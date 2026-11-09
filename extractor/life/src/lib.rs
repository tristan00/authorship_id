mod beliefs;
mod experience;
mod flair;
mod home;
mod lifestyle;
mod parental;
mod relationship;
mod shared;
mod siblings;
mod together;
mod traits;

use claimcore::*;
use std::sync::LazyLock;

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    let mut rules = relationship::build();
    rules.extend(parental::build());
    rules.extend(relationship::kink());
    rules.extend(together::build());
    rules.extend(experience::build());
    rules.extend(siblings::build());
    rules.extend(shared::scoped_rules(home::pets()));
    rules.extend(shared::scoped_rules(home::living()));
    rules.extend(home::housing());
    rules.extend(home::residency());
    rules.extend(traits::build());
    rules.extend(beliefs::build());
    rules
});
static LIFESTYLE: LazyLock<Vec<Rule>> = LazyLock::new(lifestyle::build);

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn lifestyle_rules() -> &'static [Rule] {
    &LIFESTYLE
}

const SPECIFIC_PARENTS: [&str; 6] = ["single parent", "stepparent", "foster / adoptive parent", "grandparent", "boy mom / girl dad", "empty nester"];

pub fn settle(found: &mut Found) {
    if found.items.iter().any(|(attribute, value, _)| attribute == "parent_role" && SPECIFIC_PARENTS.contains(&value.as_str())) {
        found.items.retain(|(attribute, value, _)| !(attribute == "parent_role" && value == "parent"));
    }
}

pub fn init() {
    timed("life.init", || {
        let gated = LIFESTYLE.iter().filter(|entry| entry.gate.is_some()).count();
        log(&format!("life rules={} lifestyle rules={} lifestyle gated={gated}", RULES.len(), LIFESTYLE.len()));
    });
}
