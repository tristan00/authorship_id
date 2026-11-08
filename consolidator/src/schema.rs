pub const BOT: &str = "automated_account";
pub const FLAIR: &str = "flair";
const YES: &str = "yes";
const NO: &str = "no";
const FANDOM: [&str; 9] = ["sports_team", "athlete", "artist", "author", "character", "franchise", "video_game", "creator", "celebrity"];
const PHYSICAL: [&str; 13] = [
    "diabetes", "autoimmune disease", "chronic pain or fibromyalgia", "cancer", "heart or blood condition", "digestive condition", "hormonal or reproductive condition",
    "neurological condition", "skin condition", "respiratory condition or allergy", "vision or hearing impairment", "physical disability", "other physical condition",
];
const MENTAL: [&str; 14] = [
    "adhd", "autism", "both adhd and autism", "depression", "anxiety", "bipolar disorder", "ptsd", "ocd", "eating disorder", "personality disorder",
    "schizophrenia or psychosis", "addiction", "neurodivergent, unspecified", "other mental health condition",
];
const CONDITIONS: [(&str, &str); 22] = [
    ("anxiety", "anxiety"), ("depression", "depression"), ("addiction", "addiction"), ("ocd", "ocd"), ("ptsd", "ptsd"), ("eating disorder", "eating_disorder"),
    ("bipolar disorder", "bipolar_disorder"), ("schizophrenia or psychosis", "psychosis"), ("personality disorder", "personality_disorder"), ("adhd", "adhd"),
    ("autism", "autism"), ("diabetes", "diabetes"), ("autoimmune disease", "autoimmune_disease"), ("chronic pain or fibromyalgia", "chronic_pain"), ("cancer", "cancer"),
    ("heart or blood condition", "heart_condition"), ("digestive condition", "digestive_condition"), ("hormonal or reproductive condition", "hormonal_condition"),
    ("skin condition", "skin_condition"), ("respiratory condition or allergy", "respiratory_condition"), ("vision or hearing impairment", "sensory_impairment"),
    ("physical disability", "physical_disability"),
];
const PERSONALITY: [&str; 16] = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"];
const GENERATION: [&str; 6] = ["silent generation", "baby boomer", "gen x", "millennial", "gen z", "gen alpha"];
const MBTI: [(&str, [(char, &str); 2]); 4] = [
    ("mbti_ie", [('I', "introvert"), ('E', "extravert")]),
    ("mbti_ns", [('N', "intuitive"), ('S', "sensing")]),
    ("mbti_tf", [('T', "thinking"), ('F', "feeling")]),
    ("mbti_jp", [('J', "judging"), ('P', "perceiving")]),
];

pub fn stored_field(attribute: &str) -> String {
    if FANDOM.contains(&attribute) {
        format!("fan_{attribute}")
    } else {
        attribute.to_string()
    }
}

fn pairs(found: &[(&str, &str)]) -> Vec<(String, String)> {
    found.iter().map(|(name, stated)| (name.to_string(), stated.to_string())).collect()
}

pub fn decomposed(field: &str, value: &str) -> Vec<(String, String)> {
    match (field, value) {
        ("gender", "trans woman") => pairs(&[("gender", "female"), ("transgender", YES)]),
        ("gender", "trans man") => pairs(&[("gender", "male"), ("transgender", YES)]),
        ("gender", "transgender, unspecified") => pairs(&[("transgender", YES)]),
        ("sexual_orientation", "gay" | "lesbian") => pairs(&[("sexual_orientation", "gay or lesbian")]),
        ("sexual_orientation", "queer, unspecified") => pairs(&[("sexual_orientation", "queer")]),
        ("education", "high school student") => pairs(&[("education", "no high school diploma")]),
        ("education", "college student") => pairs(&[("education", "some college, no degree")]),
        ("education", "graduate student") => pairs(&[("education", "bachelor's degree")]),
        ("education", "professional degree such as law or medicine") => pairs(&[("education", "professional degree")]),
        ("hair_color", "bald") => pairs(&[("bald", YES)]),
        ("diet", "eats everything") => pairs(&[("diet", "eats meat")]),
        ("diet", "keto or low carb" | "halal or kosher" | "gluten free") => vec![],
        ("pets", "dog") => pairs(&[("pet_dog", YES)]),
        ("pets", "cat") => pairs(&[("pet_cat", YES)]),
        ("pets", "dog and cat") => pairs(&[("pet_dog", YES), ("pet_cat", YES)]),
        ("pets", "no pets") => pairs(&[("pet_dog", NO), ("pet_cat", NO)]),
        ("pets", "other pet") => vec![],
        ("physical_condition" | "mental_condition" | "neurotype", _) if PHYSICAL.contains(&value) || MENTAL.contains(&value) => {
            match CONDITIONS.iter().find(|(condition, _)| *condition == value) {
                Some((_, name)) => pairs(&[(name, YES)]),
                None if value == "both adhd and autism" => pairs(&[("adhd", YES), ("autism", YES)]),
                None => vec![],
            }
        }
        ("personality_type", _) if PERSONALITY.contains(&value) => MBTI
            .iter()
            .zip(value.chars())
            .map(|((name, letters), letter)| (name.to_string(), letters.iter().find(|(code, _)| *code == letter).unwrap().1.to_string()))
            .collect(),
        ("generation", _) if GENERATION.contains(&value) => vec![],
        _ => vec![(field.to_string(), value.to_string())],
    }
}
