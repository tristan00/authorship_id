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

fn option<'a>(args: &'a [String], name: &str) -> Option<&'a str> {
    args.iter().position(|arg| arg == name).and_then(|index| args.get(index + 1)).map(String::as_str)
}

fn usage() -> ! {
    eprintln!("usage: consolidate run --host HOST --threads N [--port 8123] [--database reddit] [--candidates]");
    std::process::exit(2);
}

fn required<'a>(args: &'a [String], name: &str) -> &'a str {
    option(args, name).unwrap_or_else(|| usage())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("run") => {
            let database = database::Database::new(required(&args, "--host"), option(&args, "--port").unwrap_or("8123").parse().unwrap(), option(&args, "--database").unwrap_or("reddit"));
            run::run(&database, required(&args, "--threads").parse().unwrap(), args.iter().any(|arg| arg == "--candidates"));
        }
        _ => usage(),
    }
}
