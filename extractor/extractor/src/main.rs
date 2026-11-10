#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod database;
mod run;
mod score;

use claimcore::*;
use serde::Deserialize;
use serde_json::value::RawValue;
use std::collections::BTreeMap;
use std::io::{BufWriter, Write};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{LazyLock, Mutex};
use std::time::Instant;

#[derive(Deserialize)]
struct Row<'a> {
    #[serde(borrow)]
    id: &'a RawValue,
    text: String,
}

static BOT_SAFE: LazyLock<Vec<&'static str>> = LazyLock::new(|| {
    let mut safe: Vec<&'static str> = demographics::rules().iter().chain(work::rules()).map(|rule| rule.attribute).collect();
    safe.extend(["automated_account", "relationship_status", "parent_role"]);
    safe.sort();
    safe.dedup();
    safe
});

static RULES: LazyLock<(Vec<&'static Rule>, prefilter::Literals)> = LazyLock::new(|| {
    let rules: Vec<&'static Rule> = [demographics::rules(), location::rules(), life::rules(), life::lifestyle_rules(), work::rules(), health::rules()].into_iter().flatten().collect();
    let patterns: Vec<(&str, u32, Option<&[Vec<char>]>)> = rules.iter().map(|rule| (rule.re.pattern.as_str(), rule.re.flags, rule.gate.as_deref())).collect();
    let literals = prefilter::Literals::new(&patterns);
    (rules, literals)
});

const INVALID_EXAMPLES: usize = 5;

const ID_CHARS: usize = 16;

static INVALID: Mutex<BTreeMap<String, (u64, Vec<(String, String)>)>> = Mutex::new(BTreeMap::new());

fn contracted(attribute: &str, value: &str, origin: Origin, id: impl FnOnce() -> String) -> Option<String> {
    let known = contract::SCHEMA.attribute(attribute).unwrap_or_else(|| panic!("a rule emitted {attribute:?}, which claim_extraction/schema.json does not define"));
    let normal = known.normal(value);
    if normal.is_none() {
        let mut invalid = INVALID.lock().unwrap();
        let (count, examples) = invalid.entry(attribute.to_string()).or_default();
        *count += 1;
        if examples.len() < INVALID_EXAMPLES && !examples.iter().any(|(example, _)| example == value) {
            examples.push((value.to_string(), format!("{value} {} {}:{}", id(), origin.file().replace('\\', "/"), origin.line())));
        }
    }
    normal
}

fn short(id: &str) -> String {
    id.trim_matches('"').chars().take(ID_CHARS).collect()
}

fn invalid() -> String {
    let invalid = INVALID.lock().unwrap();
    let total: u64 = invalid.values().map(|(count, _)| count).sum();
    let detail: Vec<String> = invalid.iter().map(|(attribute, (count, examples))| format!("{attribute}:{count}{:?}", examples.iter().map(|(_, shown)| shown).collect::<Vec<_>>())).collect();
    format!("{total} {}", detail.join(" "))
}

fn bot_safe(attribute: &str) -> bool {
    BOT_SAFE.binary_search(&attribute).is_ok()
}

fn init() {
    std::thread::scope(|scope| {
        scope.spawn(fandom::init);
        scope.spawn(location::init);
        scope.spawn(work::init);
        scope.spawn(|| {
            demographics::init();
            life::init();
            health::init();
            LazyLock::force(&BOT_SAFE);
            LazyLock::force(&RULES);
            LazyLock::force(&MASKED);
            LazyLock::force(&BOT_TEXT);
        });
    });
}

fn positioned(raw: &str) -> Vec<(String, String, usize, Origin)> {
    let text = prepared(raw);
    let lowered = lower(&text);
    set_current(&text, &lowered);
    let automatic = BOT_TEXT.test(&lowered);
    let mut found = Found::default();
    demographics::tags(&text, &lowered, &mut found);
    let (rules, literals) = &*RULES;
    run_possible(rules, &literals.possible(&lowered), &lowered, automatic, &bot_safe, &mut found);
    fandom::favorites(&text, &mut found);
    fandom::fandom(&text, &mut found);
    fandom::adjacent(&text, &mut found);
    fandom::characters(&text, &mut found);
    if !automatic {
        health::ailments(&lowered, &mut found);
    }
    location::places(&text, &lowered, &mut found);
    demographics::settle(&lowered, &mut found);
    life::settle(&mut found);
    set_current(&[], &[]);
    finish(found)
}

fn encoded(id: &str, picks: &[(String, String, usize)]) -> String {
    let mut out = String::with_capacity(64 + picks.len() * 48);
    out.push_str("{\"id\": ");
    out.push_str(id);
    out.push_str(", \"picks\": [");
    for (index, (attribute, value, position)) in picks.iter().enumerate() {
        if index > 0 {
            out.push_str(", ");
        }
        out.push('[');
        out.push_str(&serde_json::to_string(attribute).unwrap());
        out.push_str(", ");
        out.push_str(&serde_json::to_string(value).unwrap());
        out.push_str(", ");
        out.push_str(&position.to_string());
        out.push(']');
    }
    out.push_str("]}");
    out
}

fn read_lines(path: &str) -> Vec<String> {
    let content = std::fs::read_to_string(path).unwrap_or_else(|error| panic!("cannot read {path}: {error}"));
    content.lines().filter(|line| !line.trim().is_empty()).map(str::to_string).collect()
}

fn process(line: &str) -> String {
    let row: Row = serde_json::from_str(line).unwrap_or_else(|error| panic!("bad input line: {error}"));
    let claims: Vec<(String, String, usize)> = positioned(&row.text)
        .into_iter()
        .filter_map(|(attribute, value, position, origin)| contracted(&attribute, &value, origin, || short(row.id.get())).map(|value| (attribute, value, position)))
        .collect();
    encoded(row.id.get(), &claims)
}

fn extract(input: &str, output: &str, threads: usize) {
    timed("extract", || {
        let lines = timed("read", || read_lines(input));
        timed("init", init);
        let started = Instant::now();
        let next = AtomicUsize::new(0);
        let chunk = 256;
        let mut results: Vec<String> = vec![String::new(); lines.len()];
        let slots: Vec<std::sync::Mutex<&mut [String]>> = results.chunks_mut(chunk).map(std::sync::Mutex::new).collect();
        std::thread::scope(|scope| {
            for _ in 0..threads.max(1) {
                scope.spawn(|| loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    if index >= slots.len() {
                        break;
                    }
                    let mut slot = slots[index].lock().unwrap();
                    for (offset, out) in slot.iter_mut().enumerate() {
                        *out = process(&lines[index * chunk + offset]);
                    }
                });
            }
        });
        drop(slots);
        let seconds = started.elapsed().as_secs_f64();
        log(&format!("texts={} threads={threads} seconds={seconds:.2} rate={:.0} failures={} invalid={}", lines.len(), lines.len() as f64 / seconds, re::FAILURES.load(Ordering::Relaxed), invalid()));
        timed("write", || {
            let mut writer = BufWriter::new(std::fs::File::create(output).unwrap());
            for line in &results {
                writer.write_all(line.as_bytes()).unwrap();
                writer.write_all(b"\n").unwrap();
            }
            writer.flush().unwrap();
        });
    });
}

fn bench(input: &str) {
    let lines = read_lines(input);
    let texts: Vec<String> = lines.iter().map(|line| serde_json::from_str::<Row>(line).unwrap().text).collect();
    let started = Instant::now();
    init();
    println!("startup seconds {:.3}", started.elapsed().as_secs_f64());
    let mut total = 0usize;
    for text in texts.iter().take(5000) {
        total += positioned(text).len();
    }
    for pass in 1..=3 {
        let started = Instant::now();
        for text in &texts {
            total += positioned(text).len();
        }
        println!("pass {pass} us/text {:.2}", started.elapsed().as_secs_f64() * 1e6 / texts.len() as f64);
    }
    println!("picks {total} failures {} jit_failures {}", re::FAILURES.load(Ordering::Relaxed), re::JIT_FAILURES.load(Ordering::Relaxed));
}

fn prompts(prompt: &str, input: &str, output: &str) {
    timed("prompts", || {
        let template = contract::SCHEMA.template(prompt);
        let mut writer = BufWriter::new(std::fs::File::create(output).unwrap());
        let mut count = 0usize;
        for line in read_lines(input) {
            let row: Row = serde_json::from_str(&line).unwrap_or_else(|error| panic!("bad input line: {error}"));
            let text = template.replace("{text}", &row.text);
            writeln!(writer, "{{\"id\": {}, \"text\": {}}}", row.id.get(), serde_json::to_string(&text).unwrap()).unwrap();
            count += 1;
        }
        writer.flush().unwrap();
        log(&format!("prompts prompt={prompt} records={count}"));
    });
}

fn option<'a>(args: &'a [String], name: &str, default: &'a str) -> &'a str {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str).unwrap_or(default)
}

fn required<'a>(args: &'a [String], name: &str) -> &'a str {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str).unwrap_or_else(|| panic!("missing {name}"))
}

fn positional(args: &[String]) -> Vec<&str> {
    let mut found = Vec::new();
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        if arg.starts_with("--") {
            iter.next();
        } else {
            found.push(arg.as_str());
        }
    }
    found
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let threads: usize = option(&args, "--threads", "1").parse().unwrap();
    match args.get(1).map(String::as_str) {
        Some("extract") if args.len() >= 4 => extract(&args[2], &args[3], threads),
        Some("bench") if args.len() >= 3 => bench(&args[2]),
        Some("prompts") if args.len() >= 5 => prompts(&args[2], &args[3], &args[4]),
        Some("template") if args.len() >= 3 => print!("{}", contract::SCHEMA.template(&args[2])),
        Some("score") if args.len() > 5 => score::score(&args[2], &args[3], &args[4], option(&args, "--agree", "2").parse().unwrap(), threads, &positional(&args[5..]), args.iter().position(|arg| arg == "--contested").map(|index| args[index + 1].as_str())),
        Some("conditions") => {
            for (attribute, name, value) in health::english_conditions() {
                println!("{attribute}	{name}	{value}");
            }
        }
        Some(command @ ("run" | "flairs")) => {
            let database = database::Database::new(option(&args, "--host", "localhost"), option(&args, "--port", "8123").parse().unwrap(), required(&args, "--database"));
            run::attributes(&database);
            if command == "run" {
                run::extract(&database, threads);
            } else {
                run::flairs(&database, threads);
            }
        }
        _ => {
            eprintln!("usage: claims extract <input.jsonl> <output.jsonl> --threads N | claims bench <input.jsonl> | claims prompts <prompt> <input.jsonl> <output.jsonl> | claims template <prompt> | claims score <prompt> <texts.jsonl> <report.json> <answers_dir>... [--agree N] [--contested <out.jsonl>] --threads N | claims conditions | claims run|flairs --host H --database D [--port P] --threads N");
            std::process::exit(2);
        }
    }
}
