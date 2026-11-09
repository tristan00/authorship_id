#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod database;
mod predict;
mod prepare;
mod texts;

use std::time::{Instant, SystemTime, UNIX_EPOCH};

pub fn log(message: &str) {
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64();
    eprintln!("{now:.3} {message}");
}

pub fn timed<T>(name: &str, work: impl FnOnce() -> T) -> T {
    let started = Instant::now();
    log(&format!("{name} start"));
    let result = work();
    log(&format!("{name} done seconds={:.3}", started.elapsed().as_secs_f64()));
    result
}

fn option<'a>(args: &'a [String], name: &str, default: &'a str) -> &'a str {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str).unwrap_or(default)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let database = || database::Database::new(option(&args, "--host", "localhost"), option(&args, "--port", "8123").parse().unwrap(), option(&args, "--database", "reddit"));
    match args.get(1).map(String::as_str) {
        Some("prepare") => prepare::run(&database(), &args[2..]),
        Some("predict") => predict::run(&database(), &args[2..]),
        Some("texts") => texts::run(&database(), &args[2..]),
        _ => {
            eprintln!("usage: attribute_io prepare|predict|texts ... --host HOST [--port 8123] [--database reddit]");
            std::process::exit(2);
        }
    }
}
