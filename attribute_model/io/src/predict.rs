use crate::database::Database;
use crate::{log, timed};
use crossbeam_channel::{bounded, unbounded, Receiver};
use serde_json::Value;
use std::ffi::c_void;
use std::io::{BufRead, Read, Write};
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering::Relaxed};
use std::sync::Mutex;
use std::time::Instant;

const DIMENSIONS: usize = 512;
const VECTOR_PREFIX: [u8; 2] = [0x80, 0x04];
const FILE_MAP_ALL_ACCESS: u32 = 0xF001F;

#[link(name = "kernel32")]
extern "system" {
    fn OpenFileMappingW(access: u32, inherit: i32, name: *const u16) -> *mut c_void;
    fn MapViewOfFile(mapping: *mut c_void, access: u32, high: u32, low: u32, bytes: usize) -> *mut c_void;
}

#[derive(Clone, Copy)]
struct Shared(*mut u8);
unsafe impl Send for Shared {}
unsafe impl Sync for Shared {}

impl Shared {
    fn open(name: &str) -> Shared {
        let wide: Vec<u16> = name.encode_utf16().chain([0]).collect();
        let mapping = unsafe { OpenFileMappingW(FILE_MAP_ALL_ACCESS, 0, wide.as_ptr()) };
        assert!(!mapping.is_null(), "cannot open shared memory {name}");
        let view = unsafe { MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, 0) };
        assert!(!view.is_null(), "cannot map shared memory {name}");
        Shared(view as *mut u8)
    }

    fn slice(&self, offset: usize, length: usize) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.add(offset), length) }
    }

    fn write(&self, offset: usize, bytes: &[u8]) {
        unsafe { std::ptr::copy_nonoverlapping(bytes.as_ptr(), self.0.add(offset), bytes.len()) }
    }
}

enum Kind {
    Numeric,
    Ranked(usize, usize, Keys),
}

struct Keys {
    count: usize,
    width: usize,
    bytes: Vec<u8>,
}

impl Keys {
    fn new(values: &[Value]) -> Keys {
        let mut bytes = Vec::new();
        values.iter().for_each(|value| put_bytes(&mut bytes, value.as_str().unwrap().as_bytes()));
        Keys { count: values.len(), width: if values.len() <= 1 << 8 { 1 } else if values.len() <= 1 << 16 { 2 } else { 4 }, bytes }
    }

    fn write(&self, out: &mut Vec<u8>, indexes: &[u32]) {
        out.extend_from_slice(&(self.width.trailing_zeros() as u64 | 1 << 9).to_le_bytes());
        out.extend_from_slice(&(self.count as u64).to_le_bytes());
        out.extend_from_slice(&self.bytes);
        out.extend_from_slice(&(indexes.len() as u64).to_le_bytes());
        for &index in indexes {
            assert!((index as usize) < self.count, "decision index {index} outside {} values", self.count);
            out.extend_from_slice(&index.to_le_bytes()[..self.width]);
        }
    }
}

struct Column {
    header: Vec<u8>,
    confidence: Vec<u8>,
    kind: Kind,
}

struct Layout {
    shared: String,
    table: String,
    batch: usize,
    slots: usize,
    fetchers: usize,
    encoders: usize,
    inserters: usize,
    insert_rows: usize,
    ranges: Vec<(String, String)>,
    columns: Vec<Column>,
    numeric: usize,
    pairs: usize,
}

fn header(name: &str, type_name: &str) -> Vec<u8> {
    let mut out = Vec::new();
    put_bytes(&mut out, name.as_bytes());
    put_bytes(&mut out, type_name.as_bytes());
    out
}

impl Layout {
    fn read(path: &str) -> Layout {
        let value: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let number = |key: &str| value[key].as_u64().unwrap_or_else(|| panic!("layout needs {key}")) as usize;
        let mut pairs = 0;
        let columns: Vec<Column> = value["columns"].as_array().unwrap().iter().map(|column| {
            let name = column["name"].as_str().unwrap();
            match column["type"].as_str().unwrap() {
                "numeric" => Column { header: header(name, "Float32"), confidence: Vec::new(), kind: Kind::Numeric },
                "ranked" => {
                    let slots = column["slots"].as_u64().unwrap() as usize;
                    pairs += slots;
                    Column {
                        header: header(name, "Array(LowCardinality(String))"),
                        confidence: header(&format!("{name}_confidence"), "Array(Float32)"),
                        kind: Kind::Ranked(pairs - slots, slots, Keys::new(column["values"].as_array().unwrap())),
                    }
                }
                other => panic!("unknown column type {other}"),
            }
        }).collect();
        let layout = Layout {
            shared: value["shared"].as_str().unwrap().to_string(),
            table: value["table"].as_str().unwrap().to_string(),
            batch: number("batch"),
            slots: number("slots"),
            fetchers: number("fetchers"),
            encoders: number("encoders"),
            inserters: number("inserters"),
            insert_rows: number("insert_rows"),
            ranges: value["ranges"].as_array().unwrap().iter().map(|pair| (pair[0].as_str().unwrap().to_string(), pair[1].as_str().unwrap().to_string())).collect(),
            numeric: columns.iter().filter(|column| matches!(column.kind, Kind::Numeric)).count(),
            columns,
            pairs,
        };
        assert_eq!(number("dimensions"), DIMENSIONS);
        assert_eq!(number("slot_bytes"), layout.slot_bytes(), "slot layout differs from python");
        layout
    }

    fn regions(&self) -> [usize; 4] {
        [self.batch * DIMENSIONS * 4, self.batch * self.numeric * 4, self.batch * self.pairs * 4, self.batch * self.pairs * 4]
    }

    fn written(&self) -> usize {
        1 + self.columns.iter().map(|column| if matches!(column.kind, Kind::Ranked(..)) { 2 } else { 1 }).sum::<usize>()
    }

    fn slot_bytes(&self) -> usize {
        self.regions().iter().sum()
    }

    fn region(&self, slot: usize, index: usize) -> usize {
        slot * self.slot_bytes() + self.regions()[..index].iter().sum::<usize>()
    }
}

#[derive(Default)]
struct Stats {
    fetch: AtomicU64,
    wait: AtomicU64,
    encode: AtomicU64,
    insert: AtomicU64,
    fetched: AtomicUsize,
    inserted: AtomicUsize,
    finished: AtomicUsize,
}

fn nanos(started: Instant) -> u64 {
    started.elapsed().as_nanos() as u64
}

fn seconds(counter: &AtomicU64) -> f64 {
    counter.load(Relaxed) as f64 / 1e9
}

struct Batch {
    slot: usize,
    rows: usize,
    authors: Vec<u8>,
}

fn put_length(out: &mut Vec<u8>, mut length: usize) {
    while length >= 0x80 {
        out.push(length as u8 | 0x80);
        length >>= 7;
    }
    out.push(length as u8);
}

fn put_bytes(out: &mut Vec<u8>, bytes: &[u8]) {
    put_length(out, bytes.len());
    out.extend_from_slice(bytes);
}

fn quote(value: &str) -> String {
    format!("'{}'", value.replace('\\', "\\\\").replace('\'', "\\'"))
}

fn dispatch(batch: Batch, pending: &Mutex<Vec<Option<Batch>>>, stats: &Stats) {
    let line = format!("{} {}\n", batch.slot, batch.rows);
    stats.fetched.fetch_add(batch.rows, Relaxed);
    let slot = batch.slot;
    pending.lock().unwrap()[slot] = Some(batch);
    let mut out = std::io::stdout().lock();
    out.write_all(line.as_bytes()).unwrap();
    out.flush().unwrap();
}

fn fetch(database: &Database, layout: &Layout, shared: Shared, ranges: &Receiver<(String, String)>, free: &Receiver<usize>, pending: &Mutex<Vec<Option<Batch>>>, stats: &Stats) {
    while let Ok((low, high)) = ranges.recv() {
        let started = Instant::now();
        let mut waited = 0;
        let upper = if high.is_empty() { String::new() } else { format!(" AND author < {}", quote(&high)) };
        let mut rows = database.rows(&format!("SELECT author, vector FROM author_vectors WHERE author >= {}{upper} ORDER BY author FORMAT RowBinary", quote(&low)));
        let mut batch: Option<Batch> = None;
        while !rows.done() {
            let current = batch.get_or_insert_with(|| {
                let waiting = Instant::now();
                let slot = free.recv().unwrap();
                waited += nanos(waiting);
                Batch { slot, rows: 0, authors: Vec::with_capacity(layout.batch * 24) }
            });
            put_bytes(&mut current.authors, rows.bytes());
            assert_eq!(rows.fixed::<2>(), VECTOR_PREFIX, "vectors must have {DIMENSIONS} dimensions");
            shared.write(layout.region(current.slot, 0) + current.rows * DIMENSIONS * 4, &rows.fixed::<{ DIMENSIONS * 4 }>());
            current.rows += 1;
            if current.rows == layout.batch {
                dispatch(batch.take().unwrap(), pending, stats);
            }
        }
        if let Some(current) = batch.take() {
            dispatch(current, pending, stats);
        }
        stats.wait.fetch_add(waited, Relaxed);
        stats.fetch.fetch_add(nanos(started) - waited, Relaxed);
    }
    if stats.finished.fetch_add(1, Relaxed) + 1 == layout.fetchers {
        let mut out = std::io::stdout().lock();
        out.write_all(b"end\n").unwrap();
        out.flush().unwrap();
    }
}

fn encode(layout: &Layout, shared: Shared, batch: &Batch) -> Vec<u8> {
    let rows = batch.rows;
    let numeric = shared.slice(layout.region(batch.slot, 1), rows * layout.numeric * 4);
    let picked = shared.slice(layout.region(batch.slot, 2), rows * layout.pairs * 4);
    let chances = shared.slice(layout.region(batch.slot, 3), rows * layout.pairs * 4);
    let mut out = Vec::with_capacity(batch.authors.len() + rows * 1024);
    put_length(&mut out, layout.written());
    put_length(&mut out, rows);
    put_bytes(&mut out, b"author");
    put_bytes(&mut out, b"String");
    out.extend_from_slice(&batch.authors);
    let (mut number, mut indexes, mut offsets, mut values) = (0, Vec::with_capacity(rows * 4), Vec::with_capacity(rows), Vec::with_capacity(rows * 16));
    for column in &layout.columns {
        out.extend_from_slice(&column.header);
        match &column.kind {
            Kind::Numeric => {
                (0..rows).for_each(|row| out.extend_from_slice(&numeric[(row * layout.numeric + number) * 4..][..4]));
                number += 1;
            }
            Kind::Ranked(offset, slots, keys) => {
                (indexes.clear(), offsets.clear(), values.clear());
                for row in 0..rows {
                    for slot in 0..*slots {
                        let at = (row * layout.pairs + offset + slot) * 4;
                        let index = i32::from_le_bytes(picked[at..at + 4].try_into().unwrap());
                        if index >= 0 {
                            indexes.push(index as u32);
                            values.extend_from_slice(&chances[at..at + 4]);
                        }
                    }
                    offsets.push(indexes.len() as u64);
                }
                out.extend_from_slice(&1u64.to_le_bytes());
                offsets.iter().for_each(|end| out.extend_from_slice(&end.to_le_bytes()));
                if !indexes.is_empty() {
                    keys.write(&mut out, &indexes);
                }
                out.extend_from_slice(&column.confidence);
                offsets.iter().for_each(|end| out.extend_from_slice(&end.to_le_bytes()));
                out.extend_from_slice(&values);
            }
        }
    }
    out
}

struct Body<'a> {
    parts: &'a Receiver<(Vec<u8>, usize)>,
    current: Vec<u8>,
    position: usize,
    rows: usize,
    bytes: usize,
    limit: usize,
}

impl Read for Body<'_> {
    fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
        while self.position == self.current.len() {
            if self.rows >= self.limit {
                return Ok(0);
            }
            match self.parts.recv() {
                Ok((part, rows)) => {
                    self.bytes += self.current.len();
                    (self.current, self.position, self.rows) = (part, 0, self.rows + rows);
                }
                Err(_) => return Ok(0),
            }
        }
        let length = buffer.len().min(self.current.len() - self.position);
        buffer[..length].copy_from_slice(&self.current[self.position..self.position + length]);
        self.position += length;
        Ok(length)
    }
}

fn insert(url: &str, layout: &Layout, parts: &Receiver<(Vec<u8>, usize)>, stats: &Stats) {
    let sql = format!("INSERT INTO {} FORMAT Native", layout.table);
    while let Ok((current, rows)) = parts.recv() {
        let started = Instant::now();
        let mut body = Body { parts, current, position: 0, rows, bytes: 0, limit: layout.insert_rows };
        match ureq::post(url).query("query", &sql).send(&mut body) {
            Ok(_) => {}
            Err(ureq::Error::Status(code, response)) => panic!("clickhouse {code} for {sql}: {}", response.into_string().unwrap_or_default()),
            Err(other) => panic!("clickhouse insert failed: {other}"),
        }
        let spent = nanos(started);
        stats.insert.fetch_add(spent, Relaxed);
        let total = stats.inserted.fetch_add(body.rows, Relaxed) + body.rows;
        log(&format!("predict insert rows={} bytes={} seconds={:.3} inserted={total}", body.rows, body.bytes + body.current.len(), spent as f64 / 1e9));
    }
}

pub fn run(database: &Database, args: &[String]) {
    timed("predict", || {
        let layout = Layout::read(&args[0]);
        let shared = Shared::open(&layout.shared);
        let stats = Stats::default();
        let started = Instant::now();
        let (free_sender, free) = bounded(layout.slots);
        (0..layout.slots).for_each(|slot| free_sender.send(slot).unwrap());
        let (range_sender, ranges) = unbounded();
        layout.ranges.iter().for_each(|range| range_sender.send(range.clone()).unwrap());
        drop(range_sender);
        let pending = Mutex::new((0..layout.slots).map(|_| None).collect::<Vec<Option<Batch>>>());
        let (completed, finished) = bounded::<Batch>(layout.slots);
        let (part_sender, parts) = bounded(layout.slots);
        std::thread::scope(|scope| {
            for _ in 0..layout.fetchers {
                scope.spawn(|| fetch(database, &layout, shared, &ranges, &free, &pending, &stats));
            }
            for _ in 0..layout.encoders {
                let (finished, part_sender, free_sender, layout, stats) = (finished.clone(), part_sender.clone(), free_sender.clone(), &layout, &stats);
                scope.spawn(move || {
                    for batch in finished {
                        let begun = Instant::now();
                        let body = encode(layout, shared, &batch);
                        free_sender.send(batch.slot).unwrap();
                        stats.encode.fetch_add(nanos(begun), Relaxed);
                        part_sender.send((body, batch.rows)).unwrap();
                    }
                });
            }
            drop((part_sender, finished));
            for _ in 0..layout.inserters {
                scope.spawn(|| insert(database.url(), &layout, &parts, &stats));
            }
            for line in std::io::stdin().lock().lines() {
                let slot: usize = line.unwrap().trim().parse().unwrap();
                completed.send(pending.lock().unwrap()[slot].take().expect("completed slot was not pending")).unwrap();
            }
            drop(completed);
        });
        let (fetched, inserted, elapsed) = (stats.fetched.load(Relaxed), stats.inserted.load(Relaxed), started.elapsed().as_secs_f64());
        assert_eq!(fetched, inserted, "fetched rows were not all inserted");
        log(&format!(
            "predict rows={inserted} seconds={elapsed:.3} rate={:.0}/s fetch={:.3}s fetch_thread_rate={:.0}/s slot_wait={:.3}s encode={:.3}s encode_thread_rate={:.0}/s insert={:.3}s insert_thread_rate={:.0}/s fetchers={} encoders={} inserters={}",
            inserted as f64 / elapsed,
            seconds(&stats.fetch),
            inserted as f64 / seconds(&stats.fetch),
            seconds(&stats.wait),
            seconds(&stats.encode),
            inserted as f64 / seconds(&stats.encode),
            seconds(&stats.insert),
            inserted as f64 / seconds(&stats.insert),
            layout.fetchers,
            layout.encoders,
            layout.inserters,
        ));
    });
}
