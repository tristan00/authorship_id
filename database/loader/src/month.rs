use crate::native::{Bodies, Records};
use crate::{log, rows, timed};
use crossbeam_channel::{bounded, Receiver, Sender};
use std::fs::File;
use std::io::{Read, Seek};
use std::path::Path;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering::Relaxed};
use std::time::Instant;

const CHUNK: usize = 4 << 20;
const SPARE: usize = 1 << 16;
const PART_ROWS: usize = 65_536;
const ENCODERS: usize = 2;
const INSERTERS: usize = 2;
const INSERT_ROWS: usize = 2_000_000;

type Chunk = (bool, Vec<u8>);
type Part = (Records, Bodies);
type Block = (Vec<u8>, usize);

#[derive(Default)]
struct Stage {
    busy: AtomicU64,
    wait_in: AtomicU64,
    wait_out: AtomicU64,
    ended: AtomicU64,
    items: AtomicUsize,
    rows: AtomicUsize,
    bytes: AtomicUsize,
}

fn since(started: Instant) -> u64 {
    started.elapsed().as_nanos() as u64
}

fn seconds(counter: &AtomicU64) -> f64 {
    counter.load(Relaxed) as f64 / 1e9
}

impl Stage {
    fn end(&self, run: Instant) {
        self.ended.fetch_max(since(run), Relaxed);
    }

    fn report(&self, name: &str, threads: usize) {
        let ended = seconds(&self.ended);
        log(&format!(
            "stage {name} threads={threads} ended={ended:.3}s busy={:.3}s busy_per_thread={:.3}s utilization={:.2} wait_in={:.3}s wait_out={:.3}s items={} rows={} bytes={}",
            seconds(&self.busy),
            seconds(&self.busy) / threads as f64,
            seconds(&self.busy) / threads as f64 / ended.max(1e-9),
            seconds(&self.wait_in),
            seconds(&self.wait_out),
            self.items.load(Relaxed),
            self.rows.load(Relaxed),
            self.bytes.load(Relaxed),
        ));
    }
}

fn fill(reader: &mut impl Read, buffer: &mut [u8]) -> usize {
    let mut filled = 0;
    while filled < buffer.len() {
        match reader.read(&mut buffer[filled..]).unwrap_or_else(|error| panic!("zstd decode failed: {error}")) {
            0 => break,
            read => filled += read,
        }
    }
    filled
}

fn decode(path: &Path, comment: bool, chunks: &Sender<Chunk>, free: &Receiver<Vec<u8>>, stage: &Stage, run: Instant) {
    timed(&format!("decode {}", path.display()), || {
        let mut file = File::open(path).unwrap_or_else(|error| panic!("cannot open {}: {error}", path.display()));
        let mut header = Vec::new();
        (&mut file).take(18).read_to_end(&mut header).unwrap();
        let expected = zstd::zstd_safe::get_frame_content_size(&header).unwrap_or_else(|error| panic!("{} has no valid zstd frame header: {error:?}", path.display()));
        log(&format!("decode {} frame_content_size={}", path.display(), expected.map_or("absent".to_string(), |size| size.to_string())));
        file.rewind().unwrap();
        let mut decoder = zstd::stream::read::Decoder::new(file).unwrap();
        decoder.window_log_max(31).unwrap();
        let (mut buffer, mut decompressed) = (Vec::with_capacity(CHUNK + SPARE), 0u64);
        loop {
            let started = Instant::now();
            let start = buffer.len();
            buffer.resize(start + CHUNK, 0);
            let read = fill(&mut decoder, &mut buffer[start..]);
            buffer.truncate(start + read);
            decompressed += read as u64;
            let cut = if read == 0 {
                if !buffer.is_empty() {
                    buffer.push(b'\n');
                }
                buffer.len()
            } else {
                memchr::memrchr(b'\n', &buffer[start..]).map_or(0, |end| start + end + 1)
            };
            if cut > 0 {
                let mut rest = free.try_recv().unwrap_or_else(|_| Vec::with_capacity(CHUNK + SPARE));
                rest.clear();
                rest.extend_from_slice(&buffer[cut..]);
                buffer.truncate(cut);
                let chunk = std::mem::replace(&mut buffer, rest);
                stage.busy.fetch_add(since(started), Relaxed);
                stage.items.fetch_add(1, Relaxed);
                stage.bytes.fetch_add(chunk.len(), Relaxed);
                let waiting = Instant::now();
                chunks.send((comment, chunk)).unwrap();
                stage.wait_out.fetch_add(since(waiting), Relaxed);
            } else {
                stage.busy.fetch_add(since(started), Relaxed);
            }
            if read == 0 {
                break;
            }
        }
        if let Some(expected) = expected {
            assert_eq!(decompressed, expected, "{} decompressed to {decompressed} bytes, frame header says {expected}", path.display());
        }
        log(&format!("decode {} decompressed={decompressed}", path.display()));
        stage.end(run);
    })
}

fn parse(chunks: &Receiver<Chunk>, free: &Sender<Vec<u8>>, parts: &Sender<Part>, stage: &Stage, run: Instant) -> usize {
    let (mut records, mut bodies, mut count) = (Records::default(), Bodies::default(), 0);
    loop {
        let waiting = Instant::now();
        let Ok((comment, chunk)) = chunks.recv() else { break };
        stage.wait_in.fetch_add(since(waiting), Relaxed);
        let started = Instant::now();
        let mut start = 0;
        for end in memchr::memchr_iter(b'\n', &chunk) {
            if end > start {
                rows::add(&chunk[start..end], comment, &mut records, &mut bodies);
            }
            start = end + 1;
        }
        stage.busy.fetch_add(since(started), Relaxed);
        stage.items.fetch_add(1, Relaxed);
        stage.bytes.fetch_add(chunk.len(), Relaxed);
        free.try_send(chunk).ok();
        if records.rows >= PART_ROWS {
            count += records.rows;
            stage.rows.fetch_add(records.rows, Relaxed);
            let waiting = Instant::now();
            parts.send((std::mem::take(&mut records), std::mem::take(&mut bodies))).unwrap();
            stage.wait_out.fetch_add(since(waiting), Relaxed);
        }
    }
    if records.rows > 0 {
        count += records.rows;
        stage.rows.fetch_add(records.rows, Relaxed);
        let waiting = Instant::now();
        parts.send((records, bodies)).unwrap();
        stage.wait_out.fetch_add(since(waiting), Relaxed);
    }
    stage.end(run);
    count
}

fn encode(parts: &Receiver<Part>, records_out: &Sender<Block>, bodies_out: &Sender<Block>, stage: &Stage, run: Instant) {
    loop {
        let waiting = Instant::now();
        let Ok((records, bodies)) = parts.recv() else { break };
        stage.wait_in.fetch_add(since(waiting), Relaxed);
        let started = Instant::now();
        let record_block = (records.encode(), records.rows);
        let body_block = (bodies.rows > 0).then(|| (bodies.encode(), bodies.rows));
        drop((records, bodies));
        stage.busy.fetch_add(since(started), Relaxed);
        stage.items.fetch_add(1, Relaxed);
        stage.rows.fetch_add(record_block.1, Relaxed);
        stage.bytes.fetch_add(record_block.0.len() + body_block.as_ref().map_or(0, |block| block.0.len()), Relaxed);
        let waiting = Instant::now();
        records_out.send(record_block).unwrap();
        if let Some(block) = body_block {
            bodies_out.send(block).unwrap();
        }
        stage.wait_out.fetch_add(since(waiting), Relaxed);
    }
    stage.end(run);
}

struct Body<'a> {
    blocks: &'a Receiver<Block>,
    current: Vec<u8>,
    position: usize,
    rows: usize,
    bytes: usize,
    waited: u64,
}

impl Read for Body<'_> {
    fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
        while self.position == self.current.len() {
            if self.rows >= INSERT_ROWS {
                return Ok(0);
            }
            let waiting = Instant::now();
            let next = self.blocks.recv();
            self.waited += since(waiting);
            match next {
                Ok((block, rows)) => {
                    self.bytes += block.len();
                    (self.current, self.position, self.rows) = (block, 0, self.rows + rows);
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

fn insert(url: &str, table: &str, blocks: &Receiver<Block>, stage: &Stage, run: Instant) {
    let sql = format!("INSERT INTO {table} FORMAT Native");
    loop {
        let waiting = Instant::now();
        let Ok((block, rows)) = blocks.recv() else { break };
        stage.wait_in.fetch_add(since(waiting), Relaxed);
        let started = Instant::now();
        let mut body = Body { blocks, bytes: block.len(), current: block, position: 0, rows, waited: 0 };
        match ureq::post(url).query("query", &sql).send(&mut body) {
            Ok(_) => {}
            Err(ureq::Error::Status(code, response)) => panic!("clickhouse {code} for {sql}: {}", response.into_string().unwrap_or_default()),
            Err(other) => panic!("clickhouse insert failed for {sql}: {other}"),
        }
        let spent = since(started);
        stage.busy.fetch_add(spent - body.waited, Relaxed);
        stage.wait_in.fetch_add(body.waited, Relaxed);
        stage.items.fetch_add(1, Relaxed);
        stage.rows.fetch_add(body.rows, Relaxed);
        stage.bytes.fetch_add(body.bytes, Relaxed);
        log(&format!("insert {table} rows={} bytes={} seconds={:.3} waited={:.3}", body.rows, body.bytes, spent as f64 / 1e9, body.waited as f64 / 1e9));
    }
    stage.end(run);
}

pub fn run(url: &str, comments: &Path, posts: &Path, threads: usize) -> usize {
    timed("month", || {
        let run = Instant::now();
        let [decoding, parsing, encoding, inserting_records, inserting_bodies] = std::array::from_fn::<Stage, 5, _>(|_| Stage::default());
        let (chunk_sender, chunks) = bounded::<Chunk>(threads * 2);
        let (free_sender, free) = bounded::<Vec<u8>>(threads * 2);
        let (part_sender, parts) = bounded::<Part>(ENCODERS * 2);
        let (record_sender, record_blocks) = bounded::<Block>(INSERTERS * 2);
        let (body_sender, body_blocks) = bounded::<Block>(INSERTERS * 2);
        let count = AtomicUsize::new(0);
        log(&format!("month comments={} posts={} parsers={threads} encoders={ENCODERS} inserters={INSERTERS} chunk={CHUNK} part_rows={PART_ROWS} insert_rows={INSERT_ROWS}", comments.display(), posts.display()));
        std::thread::scope(|scope| {
            for (path, comment) in [(comments, true), (posts, false)] {
                let (sender, free, stage) = (chunk_sender.clone(), free.clone(), &decoding);
                scope.spawn(move || decode(path, comment, &sender, &free, stage, run));
            }
            for _ in 0..threads {
                let (chunks, free, sender, stage, count) = (chunks.clone(), free_sender.clone(), part_sender.clone(), &parsing, &count);
                scope.spawn(move || count.fetch_add(parse(&chunks, &free, &sender, stage, run), Relaxed));
            }
            for _ in 0..ENCODERS {
                let (parts, records_out, bodies_out, stage) = (parts.clone(), record_sender.clone(), body_sender.clone(), &encoding);
                scope.spawn(move || encode(&parts, &records_out, &bodies_out, stage, run));
            }
            for _ in 0..INSERTERS {
                let (blocks, stage) = (record_blocks.clone(), &inserting_records);
                scope.spawn(move || insert(url, "records", &blocks, stage, run));
                let (blocks, stage) = (body_blocks.clone(), &inserting_bodies);
                scope.spawn(move || insert(url, "bodies_stage", &blocks, stage, run));
            }
            drop((chunk_sender, chunks, free_sender, free, part_sender, parts, record_sender, record_blocks, body_sender, body_blocks));
        });
        decoding.report("decode", 2);
        parsing.report("parse", threads);
        encoding.report("encode", ENCODERS);
        inserting_records.report("insert_records", INSERTERS);
        inserting_bodies.report("insert_bodies", INSERTERS);
        let (count, inserted) = (count.load(Relaxed), inserting_records.rows.load(Relaxed));
        assert_eq!(count, inserted, "parsed {count} records but inserted {inserted}");
        log(&format!("month records={count} bodies={} seconds={:.3}", inserting_bodies.rows.load(Relaxed), run.elapsed().as_secs_f64()));
        count
    })
}
