#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod database;
mod rules;
mod run;

use crossbeam_channel::bounded;
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

pub fn parallel<T: Send, R: Send>(threads: usize, produce: impl FnOnce(crossbeam_channel::Sender<T>) + Send, work: impl Fn(T) -> R + Sync, mut consume: impl FnMut(R)) {
    let (tasks, inbox) = bounded::<T>(threads * 4);
    let (results, outbox) = bounded::<R>(threads * 4);
    std::thread::scope(|scope| {
        scope.spawn(move || produce(tasks));
        for _ in 0..threads {
            let inbox = inbox.clone();
            let results = results.clone();
            let work = &work;
            scope.spawn(move || {
                for task in inbox {
                    results.send(work(task)).unwrap();
                }
            });
        }
        drop(results);
        for result in outbox {
            consume(result);
        }
    });
}

fn option<'a>(args: &'a [String], name: &str, default: &'a str) -> &'a str {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str).unwrap_or(default)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("run") => {
            let database = database::Database::new(option(&args, "--host", "localhost"), option(&args, "--port", "8123").parse().unwrap(), option(&args, "--database", "reddit"));
            run::run(&database, option(&args, "--threads", "1").parse().unwrap());
        }
        _ => {
            eprintln!("usage: consolidate run --host HOST [--port 8123] [--database reddit] [--threads N]");
            std::process::exit(2);
        }
    }
}
