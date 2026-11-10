#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod month;
mod native;
mod rows;

use std::path::Path;
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

fn option<'a>(args: &'a [String], name: &str) -> Option<&'a str> {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str)
}

fn required<'a>(args: &'a [String], name: &str) -> &'a str {
    option(args, name).unwrap_or_else(|| panic!("missing {name}"))
}

fn main() {
    let report = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        report(info);
        std::process::exit(101);
    }));
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("month") => {
            let url = format!(
                "http://{}:{}/?database={}&max_execution_time=0",
                required(&args, "--host"),
                option(&args, "--port").unwrap_or("8123"),
                option(&args, "--database").unwrap_or("reddit")
            );
            let threads = required(&args, "--threads").parse().unwrap();
            let count = month::run(&url, Path::new(required(&args, "--comments")), Path::new(required(&args, "--posts")), threads);
            println!("{count}");
        }
        _ => {
            eprintln!("usage: loader month --comments PATH --posts PATH --host HOST --threads N [--port 8123] [--database reddit]");
            std::process::exit(2);
        }
    }
}
