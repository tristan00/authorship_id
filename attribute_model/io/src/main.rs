#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod candidates;
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

fn required<'a>(args: &'a [String], name: &str) -> &'a str {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str).unwrap_or_else(|| panic!("missing {name}"))
}

fn main() {
    let report = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        report(info);
        std::process::exit(101);
    }));
    let args: Vec<String> = std::env::args().collect();
    let database = || database::Database::new(option(&args, "--host", "localhost"), option(&args, "--port", "8123").parse().unwrap(), required(&args, "--database"));
    match args.get(1).map(String::as_str) {
        Some("candidates") => candidates::run(&database(), &args[2..]),
        Some("prepare") => prepare::run(&database(), &args[2..]),
        Some("predict") => predict::run(&database(), &args[2..]),
        Some("texts") => texts::run(&database(), &args[2..]),
        _ => {
            eprintln!("usage: attribute_io candidates|prepare|predict|texts ... --host HOST --database DB [--port 8123]");
            std::process::exit(2);
        }
    }
}
