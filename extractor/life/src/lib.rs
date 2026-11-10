mod flair;
mod lifestyle;
mod relationship;
mod shared;
mod together;
mod traits;

use claimcore::*;
use std::sync::LazyLock;

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    let mut rules = relationship::build();
    rules.extend(together::build());
    rules.extend(traits::build());
    rules
});
static LIFESTYLE: LazyLock<Vec<Rule>> = LazyLock::new(lifestyle::build);

pub fn rules() -> &'static [Rule] {
    &RULES
}

pub fn lifestyle_rules() -> &'static [Rule] {
    &LIFESTYLE
}

const DIETS: [(&str, &str, &str); 19] = [
    ("vegan", "diet_type", "vegan"),
    ("vegetarian", "diet_type", "vegetarian"),
    ("pescatarian", "diet_type", "pescatarian"),
    ("flexitarian", "diet_type", "flexitarian"),
    ("omnivore / meat eater", "diet_type", "omnivore"),
    ("carnivore", "diet_type", "carnivore"),
    ("gluten-free", "dietary_restrictions", "gluten-free"),
    ("dairy free", "dietary_restrictions", "dairy-free"),
    ("low fodmap", "dietary_restrictions", "low-fodmap"),
    ("sugar free", "dietary_restrictions", "sugar-free"),
    ("halal", "dietary_restrictions", "halal"),
    ("kosher", "dietary_restrictions", "kosher"),
    ("keto", "diet_plan", "keto"),
    ("low carb", "diet_plan", "low carb"),
    ("paleo", "diet_plan", "paleo"),
    ("intermittent fasting", "diet_plan", "intermittent fasting"),
    ("calorie counting", "diet_plan", "calorie counting"),
    ("high protein", "diet_plan", "high protein"),
    ("mediterranean diet", "diet_plan", "mediterranean"),
];
const UNLISTED_DIETS: [&str; 1] = ["plant-based"];
const AXES: [(&str, char, &str, char, &str); 4] = [
    ("mbti_ei", 'e', "extraverted", 'i', "introverted"),
    ("mbti_ns", 'n', "intuitive", 's', "sensing"),
    ("mbti_tf", 't', "thinking", 'f', "feeling"),
    ("mbti_jp", 'j', "judging", 'p', "perceiving"),
];

fn diet(value: &str) -> Option<(&'static str, &'static str)> {
    if UNLISTED_DIETS.contains(&value) {
        return None;
    }
    let (_, attribute, split) = DIETS.iter().find(|(stated, _, _)| *stated == value).unwrap_or_else(|| panic!("diet value {value:?} has no split attribute"));
    Some((attribute, split))
}

pub fn axes(value: &str) -> Vec<(&'static str, &'static str)> {
    assert!(value.len() == 4, "mbti type {value:?} is not four letters");
    if value.matches('x').count() > 2 {
        return Vec::new();
    }
    value
        .chars()
        .zip(AXES)
        .filter(|(letter, _)| *letter != 'x')
        .map(|(letter, (attribute, first, first_value, second, second_value))| {
            assert!(letter == first || letter == second, "mbti type {value:?} has {letter:?} where {first} or {second} belongs");
            (attribute, if letter == first { first_value } else { second_value })
        })
        .collect()
}

pub fn settle(found: &mut Found) {
    let mut split = Vec::new();
    for (attribute, value, position, origin) in std::mem::take(&mut found.items) {
        match attribute.as_str() {
            "diet" => split.extend(diet(&value).map(|(attribute, value)| (attribute.to_string(), value.to_string(), position, origin))),
            "mbti_type" => split.extend(axes(&value).into_iter().map(|(attribute, value)| (attribute.to_string(), value.to_string(), position, origin))),
            _ => found.items.push((attribute, value, position, origin)),
        }
    }
    for (attribute, value, position, origin) in split {
        found.put(&attribute, value, position, origin);
    }
}

pub fn init() {
    timed("life.init", || {
        let gated = LIFESTYLE.iter().filter(|entry| entry.gate.is_some()).count();
        log(&format!("life rules={} lifestyle rules={} lifestyle gated={gated}", RULES.len(), LIFESTYLE.len()));
    });
}
