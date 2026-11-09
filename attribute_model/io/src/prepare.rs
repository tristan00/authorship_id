use crate::database::{Database, Rows};
use crate::{log, option, timed};
use crossbeam_channel::unbounded;
use half::f16;
use half::slice::HalfFloatSliceExt;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Condvar, Mutex};
use std::thread;
use std::time::Instant;

const DIMENSIONS: usize = 512;
const VALUE_AUTHORS: usize = 10;
const CATEGORICAL_VALUES: usize = 256;
const SPLIT_LABELS: usize = 100;
const SPREAD_ROWS: usize = 1 << 20;
const SPLITS: [&str; 4] = ["train", "validation", "calibration", "test"];
const BUCKETS: [usize; 10] = [0, 0, 0, 0, 0, 0, 0, 1, 2, 3];
const CLAIM_PARTS: usize = 16;
const VECTOR_STREAMS: usize = 8;
const VECTOR_CHUNKS: usize = 128;
const WINDOW: usize = 16;
const WRITE_BYTES: usize = 64 << 20;
const LABEL_BLOCK: usize = 4096;
const FEATURE_BLOCK: usize = 32;
const NEWLINE: &str = if cfg!(windows) { "\r\n" } else { "\n" };
const VECTOR_LENGTH: [u8; 2] = [(DIMENSIONS & 0x7f | 0x80) as u8, (DIMENSIONS >> 7) as u8];

#[derive(Default)]
struct Attribute {
    rows: Vec<(u32, u32)>,
    values: Vec<String>,
}

struct Part {
    authors: Vec<String>,
    attributes: Vec<Attribute>,
}

struct Encoded {
    target: Option<&'static str>,
    names: Option<Vec<String>>,
    entries: Vec<(u32, f32)>,
    sets: Option<(Vec<i64>, Vec<i32>)>,
    excluded: usize,
    counts: [usize; 4],
    trainable: bool,
}

enum Json {
    Int(usize),
    Float(f64),
    Text(String),
    List(Vec<Json>),
    Map(Vec<(String, Json)>),
}

fn utf8(bytes: &[u8]) -> String {
    String::from_utf8(bytes.to_vec()).expect("clickhouse text is not UTF-8")
}

fn quoted(text: &str) -> String {
    format!("'{}'", text.replace('\\', "\\\\").replace('\'', "\\'"))
}

fn raw<T: Copy>(values: &[T]) -> &[u8] {
    unsafe { std::slice::from_raw_parts(values.as_ptr().cast(), std::mem::size_of_val(values)) }
}

fn header(descr: &str, shape: &[usize]) -> Vec<u8> {
    let dims = if shape.len() == 1 { format!("({},)", shape[0]) } else { format!("({})", shape.iter().map(usize::to_string).collect::<Vec<_>>().join(", ")) };
    let mut text = format!("{{'descr': '{descr}', 'fortran_order': False, 'shape': {dims}, }}");
    text.push_str(&" ".repeat(21usize.saturating_sub(shape[0].to_string().len())));
    let length = text.len() + 1;
    let padding = 64 - (10 + length) % 64;
    let mut out = b"\x93NUMPY\x01\x00".to_vec();
    out.extend_from_slice(&((length + padding) as u16).to_le_bytes());
    out.extend_from_slice(text.as_bytes());
    out.extend(std::iter::repeat(b' ').take(padding));
    out.push(b'\n');
    out
}

pub fn save<T: Copy>(path: &Path, descr: &str, shape: &[usize], values: &[T]) {
    let mut out = BufWriter::with_capacity(WRITE_BYTES, File::create(path).unwrap());
    out.write_all(&header(descr, shape)).unwrap();
    out.write_all(raw(values)).unwrap();
    out.flush().unwrap();
}

fn months(database: &Database) -> Vec<(String, Json)> {
    let mut rows = database.rows("SELECT month, toString(loaded_at) FROM months ORDER BY month FORMAT RowBinary");
    let mut found = Vec::new();
    while !rows.done() {
        let month = utf8(rows.bytes());
        found.push((month, Json::Text(utf8(rows.bytes()))));
    }
    found
}

fn kinds(database: &Database) -> Vec<(String, String)> {
    let mut rows = database.rows("SELECT attribute, kind FROM author_attributes ORDER BY attribute FORMAT RowBinary");
    let mut found = Vec::new();
    while !rows.done() {
        let attribute = utf8(rows.bytes());
        found.push((attribute, utf8(rows.bytes())));
    }
    assert!(!found.is_empty(), "author_attributes is empty; claim consolidation publishes it");
    for (name, _) in &found {
        assert!(!name.trim().is_empty() && name.trim() == name, "target names must be nonempty strings without surrounding whitespace");
    }
    log(&format!("consolidated attributes={}", found.len()));
    found
}

fn ranges(database: &Database, parts: usize) -> Vec<String> {
    let mut rows = database.rows("SELECT DISTINCT author FROM author_claims WHERE cityHash64(author) % 1000 = 0 ORDER BY author FORMAT RowBinary");
    let mut sample = Vec::new();
    while !rows.done() {
        sample.push(utf8(rows.bytes()));
    }
    let mut edges: Vec<String> = (1..parts).filter_map(|part| sample.get(sample.len() * part / parts).map(|edge| quoted(edge))).collect();
    edges.dedup();
    let lows = std::iter::once(None).chain(edges.iter().map(Some));
    let highs = edges.iter().map(Some).chain(std::iter::once(None));
    lows.zip(highs)
        .map(|bounds| match bounds {
            (None, None) => String::from("1"),
            (Some(low), None) => format!("author >= {low}"),
            (None, Some(high)) => format!("author < {high}"),
            (Some(low), Some(high)) => format!("author >= {low} AND author < {high}"),
        })
        .collect()
}

fn advance(rows: &mut Rows, current: &mut Vec<u8>) -> bool {
    if rows.done() {
        return false;
    }
    let next = rows.bytes();
    assert!(current.is_empty() || next > current.as_slice(), "author vectors are not unique and ordered");
    current.clear();
    current.extend_from_slice(next);
    true
}

fn read_part(database: &Database, filter: &str, names: &str, count: usize) -> Part {
    let started = Instant::now();
    let indexes = (1..=count).map(|index| index.to_string()).collect::<Vec<_>>().join(", ");
    let mut rows = database.rows(&format!(
        "SELECT author, toUInt16(transform(attribute, [{names}], [{indexes}], 0)), value FROM author_claims WHERE {filter} AND attribute IN ({names}) ORDER BY author FORMAT RowBinary"
    ));
    let mut vectors = database.rows(&format!("SELECT author FROM author_vectors WHERE {filter} ORDER BY author FORMAT RowBinary"));
    let mut part = Part { authors: Vec::new(), attributes: (0..count).map(|_| Attribute::default()).collect() };
    let mut ids: Vec<HashMap<Vec<u8>, u32>> = (0..count).map(|_| HashMap::new()).collect();
    let (mut author, mut vector) = (Vec::new(), Vec::new());
    let (mut first, mut more, mut labeled, mut claims) = (true, advance(&mut vectors, &mut vector), false, 0usize);
    while !rows.done() {
        let next = rows.bytes();
        if first || next != author.as_slice() {
            assert!(first || next > author.as_slice(), "claims are not ordered by author");
            first = false;
            author.clear();
            author.extend_from_slice(next);
            while more && vector < author {
                more = advance(&mut vectors, &mut vector);
            }
            labeled = more && vector == author;
            if labeled {
                part.authors.push(utf8(&author));
            }
        }
        let index = u16::from_le_bytes(rows.fixed()) as usize;
        assert!((1..=count).contains(&index), "claim attribute is not consolidated");
        let index = index - 1;
        let value = rows.bytes();
        if !labeled {
            continue;
        }
        let attribute = &mut part.attributes[index];
        let id = match ids[index].get(value) {
            Some(&id) => id,
            None => {
                attribute.values.push(utf8(value));
                ids[index].insert(value.to_vec(), attribute.values.len() as u32 - 1);
                attribute.values.len() as u32 - 1
            }
        };
        attribute.rows.push((part.authors.len() as u32 - 1, id));
        claims += 1;
    }
    log(&format!("claims part {filter} authors={} claims={claims} seconds={:.1}", part.authors.len(), started.elapsed().as_secs_f64()));
    part
}

fn claims(database: &Database, kinds: &[(String, String)], names: &str) -> (Vec<String>, Vec<Attribute>) {
    let filters = ranges(database, CLAIM_PARTS);
    let parts: Vec<Part> = thread::scope(|scope| {
        let handles: Vec<_> = filters.iter().map(|filter| scope.spawn(|| read_part(database, filter, names, kinds.len()))).collect();
        handles.into_iter().map(|handle| handle.join().unwrap()).collect()
    });
    let mut authors: Vec<String> = Vec::new();
    let mut attributes: Vec<Attribute> = kinds.iter().map(|_| Attribute::default()).collect();
    let mut ids: Vec<HashMap<String, u32>> = kinds.iter().map(|_| HashMap::new()).collect();
    for part in parts {
        assert!(authors.last().zip(part.authors.first()).map_or(true, |(last, first)| last < first), "claim parts overlap");
        let offset = authors.len() as u32;
        for ((merged, known), local) in attributes.iter_mut().zip(ids.iter_mut()).zip(part.attributes) {
            let remap: Vec<u32> = local
                .values
                .into_iter()
                .map(|value| {
                    *known.entry(value.clone()).or_insert_with(|| {
                        merged.values.push(value);
                        merged.values.len() as u32 - 1
                    })
                })
                .collect();
            merged.rows.extend(local.rows.iter().map(|&(row, value)| (row + offset, remap[value as usize])));
        }
        authors.extend(part.authors);
    }
    log(&format!("labeled authors={} claims={}", authors.len(), attributes.iter().map(|attribute| attribute.rows.len()).sum::<usize>()));
    (authors, attributes)
}

fn partition(author: &str) -> u8 {
    assert!(author.is_ascii(), "author {author:?} is not ASCII, so its casefold needs Unicode rules");
    let digest = Sha256::new().chain_update(b"attribute-model:").chain_update(author.to_ascii_lowercase().as_bytes()).finalize();
    (u32::from_be_bytes([digest[0], digest[1], digest[2], digest[3]]) % 10) as u8
}

fn splits(authors: &[String], threads: usize) -> Vec<u8> {
    let mut splits = vec![0u8; authors.len()];
    let size = authors.len().div_ceil(threads).max(1);
    thread::scope(|scope| {
        for (out, chunk) in splits.chunks_mut(size).zip(authors.chunks(size)) {
            scope.spawn(move || {
                for (slot, author) in out.iter_mut().zip(chunk) {
                    *slot = partition(author);
                }
            });
        }
    });
    splits
}

fn layout(splits: &[u8]) -> (Vec<u32>, Vec<u32>, [usize; 5]) {
    let mut bounds = [0usize; 5];
    for &split in splits {
        bounds[BUCKETS[split as usize] + 1] += 1;
    }
    for split in 0..4 {
        bounds[split + 1] += bounds[split];
    }
    let mut next = bounds;
    let mut order = vec![0u32; splits.len()];
    let mut position = vec![0u32; splits.len()];
    for (row, &split) in splits.iter().enumerate() {
        let slot = &mut next[BUCKETS[split as usize]];
        order[*slot] = row as u32;
        position[row] = *slot as u32;
        *slot += 1;
    }
    log(&format!("split rows train={} validation={} calibration={} test={}", bounds[1], bounds[2] - bounds[1], bounds[3] - bounds[2], bounds[4] - bounds[3]));
    (order, position, bounds)
}

fn read_chunk(database: &Database, authors: &[String], names: &str) -> Vec<f16> {
    let filter = format!("author >= {} AND author <= {}", quoted(&authors[0]), quoted(&authors[authors.len() - 1]));
    let mut rows = database.rows(&format!(
        "SELECT author, vector FROM author_vectors WHERE {filter} AND author IN (SELECT author FROM author_claims WHERE {filter} AND attribute IN ({names})) FORMAT RowBinary"
    ));
    let mut vectors = vec![f16::ZERO; authors.len() * DIMENSIONS];
    let mut seen = vec![false; authors.len()];
    let mut floats = [0f32; DIMENSIONS];
    let mut found = 0usize;
    while !rows.done() {
        let author = rows.bytes();
        let index = authors.binary_search_by(|probe| probe.as_bytes().cmp(author)).expect("author vectors changed while they were read");
        assert!(!seen[index], "author vectors are not unique");
        seen[index] = true;
        assert!(rows.fixed::<2>() == VECTOR_LENGTH, "author vector does not have {DIMENSIONS} dimensions");
        let bytes: [u8; DIMENSIONS * 4] = rows.fixed();
        for (float, word) in floats.iter_mut().zip(bytes.chunks_exact(4)) {
            *float = f32::from_le_bytes(word.try_into().unwrap());
        }
        vectors[index * DIMENSIONS..][..DIMENSIONS].convert_from_f32_slice(&floats);
        found += 1;
    }
    assert!(found == authors.len(), "author vectors changed while they were read");
    vectors
}

fn vectors(database: &Database, authors: &[String], names: &str, splits: &[u8], edges: &[usize; 5], path: &Path) -> (Vec<f16>, usize) {
    let training: Vec<usize> = (0..authors.len()).filter(|&author| BUCKETS[splits[author] as usize] == 0).collect();
    let step = (training.len() / SPREAD_ROWS).max(1);
    let mut slots = vec![u32::MAX; authors.len()];
    let mut picked = 0usize;
    for &author in training.iter().step_by(step) {
        slots[author] = picked as u32;
        picked += 1;
    }
    let mut sample = vec![f16::ZERO; picked * DIMENSIONS];
    let bounds = |chunk: usize| (chunk * authors.len() / VECTOR_CHUNKS, (chunk + 1) * authors.len() / VECTOR_CHUNKS);
    let chunks: Vec<usize> = (0..VECTOR_CHUNKS).filter(|&chunk| bounds(chunk).0 < bounds(chunk).1).collect();
    let total = authors.len();
    let mut file = BufWriter::with_capacity(WRITE_BYTES, File::create(path).unwrap());
    file.write_all(&header("<f2", &[total, DIMENSIONS])).unwrap();
    let mut held: Vec<Vec<f16>> = (1..4).map(|split| Vec::with_capacity((edges[split + 1] - edges[split]) * DIMENSIONS)).collect();
    let next = AtomicUsize::new(0);
    let written = (Mutex::new(0usize), Condvar::new());
    let (results, outbox) = unbounded::<(usize, Vec<f16>)>();
    let started = Instant::now();
    thread::scope(|scope| {
        for _ in 0..VECTOR_STREAMS {
            let results = results.clone();
            let (next, written, chunks, bounds) = (&next, &written, &chunks, &bounds);
            scope.spawn(move || loop {
                let index = next.fetch_add(1, Ordering::Relaxed);
                if index >= chunks.len() {
                    break;
                }
                let mut done = written.0.lock().unwrap();
                while index >= *done + WINDOW {
                    done = written.1.wait(done).unwrap();
                }
                drop(done);
                let (low, high) = bounds(chunks[index]);
                results.send((index, read_chunk(database, &authors[low..high], names))).unwrap();
            });
        }
        drop(results);
        let (mut pending, mut done, mut kept) = (BTreeMap::new(), 0usize, 0usize);
        for (index, vectors) in outbox {
            pending.insert(index, vectors);
            while let Some(vectors) = pending.remove(&done) {
                let (low, high) = bounds(chunks[done]);
                for (author, row) in (low..high).zip(vectors.chunks_exact(DIMENSIONS)) {
                    match BUCKETS[splits[author] as usize] {
                        0 => file.write_all(raw(row)).unwrap(),
                        split => held[split - 1].extend_from_slice(row),
                    }
                    if slots[author] != u32::MAX {
                        sample[slots[author] as usize * DIMENSIONS..][..DIMENSIONS].copy_from_slice(row);
                    }
                }
                kept += high - low;
                done += 1;
                *written.0.lock().unwrap() = done;
                written.1.notify_all();
                if done % 16 == 0 || done == chunks.len() {
                    log(&format!("labeled vectors kept={kept} of {total} seconds={:.1}", started.elapsed().as_secs_f64()));
                }
            }
        }
        assert!(done == chunks.len(), "vector chunks are missing");
    });
    timed("write held vectors", || {
        for rows in &held {
            file.write_all(raw(rows)).unwrap();
        }
        file.flush().unwrap();
    });
    (sample, picked)
}

fn catalog(claims: &Attribute, minimum: usize) -> Vec<String> {
    let mut counts = vec![0usize; claims.values.len()];
    for &(_, value) in &claims.rows {
        counts[value as usize] += 1;
    }
    let mut kept: Vec<usize> = (0..counts.len()).filter(|&value| counts[value] >= minimum).collect();
    kept.sort_unstable_by(|&left, &right| counts[right].cmp(&counts[left]).then_with(|| claims.values[left].cmp(&claims.values[right])));
    kept.into_iter().map(|value| claims.values[value].clone()).collect()
}

fn indexed(claims: &Attribute, names: &[String]) -> Vec<Option<u32>> {
    let positions: HashMap<&str, u32> = names.iter().enumerate().map(|(position, name)| (name.as_str(), position as u32)).collect();
    claims.values.iter().map(|value| positions.get(value.as_str()).copied()).collect()
}

fn latest(claims: &Attribute, value: impl Fn(u32) -> f32) -> (Vec<(u32, f32)>, usize) {
    let mut entries: Vec<(u32, f32)> = claims.rows.iter().map(|&(row, id)| (row, value(id))).collect();
    entries.sort_by_key(|&(row, _)| row);
    let mut excluded = 0;
    let entries = entries
        .chunk_by(|left, right| left.0 == right.0)
        .map(|group| {
            if !group[group.len() - 1].1.is_finite() {
                excluded += group.len();
            }
            group[group.len() - 1]
        })
        .collect();
    (entries, excluded)
}

fn encode(name: &str, kind: &str, claims: &Attribute, splits: &[u8]) -> Encoded {
    let (target, names, entries, sets, excluded) = if claims.rows.is_empty() {
        (None, Some(Vec::new()), Vec::new(), None, 0)
    } else {
        match kind {
            "number" => {
                let numbers: Vec<f32> = claims.values.iter().map(|value| value.parse::<f64>().unwrap_or_else(|_| panic!("{name}: number claim {value:?} is not a float")) as f32).collect();
                let (entries, excluded) = latest(claims, |id| numbers[id as usize]);
                (Some("numeric"), None, entries, None, excluded)
            }
            "one" => {
                let common = catalog(claims, VALUE_AUTHORS);
                let (names, target) = if common.len() > CATEGORICAL_VALUES { (common, "embedding") } else { (catalog(claims, 1), "categorical") };
                let index = indexed(claims, &names);
                let (entries, excluded) = latest(claims, |id| index[id as usize].map_or(f32::NAN, |position| position as f32));
                (Some(target), Some(names), entries, None, excluded)
            }
            "set" => {
                let names = catalog(claims, VALUE_AUTHORS);
                let index = indexed(claims, &names);
                let mut pairs: Vec<(u32, u32)> = claims.rows.iter().filter_map(|&(row, value)| index[value as usize].map(|position| (row, position))).collect();
                pairs.sort_unstable();
                let mut indptr = vec![0i64; splits.len() + 1];
                for &(row, _) in &pairs {
                    indptr[row as usize + 1] += 1;
                }
                let entries: Vec<(u32, f32)> = (0..splits.len()).filter(|&row| indptr[row + 1] > 0).map(|row| (row as u32, 1.)).collect();
                for row in 0..splits.len() {
                    indptr[row + 1] += indptr[row];
                }
                let excluded = claims.rows.len() - pairs.len();
                (Some("set"), Some(names), entries, Some((indptr, pairs.into_iter().map(|(_, position)| position as i32).collect::<Vec<_>>())), excluded)
            }
            other => panic!("{name}: consolidated kind {other:?} is not number, one or set"),
        }
    };
    let mut counts = [0usize; 4];
    for &(row, value) in &entries {
        if value.is_finite() {
            counts[BUCKETS[splits[row as usize] as usize]] += 1;
        }
    }
    let values = names.as_ref().map_or(0, Vec::len);
    let trainable = target.is_some() && counts.iter().all(|&count| count >= SPLIT_LABELS) && (target == Some("numeric") || values >= 2);
    if !trainable {
        log(&format!("attribute {name} not trainable labels={counts:?} values={values}"));
    }
    Encoded { target, names, entries: if trainable { entries } else { Vec::new() }, sets: sets.filter(|_| trainable), excluded, counts, trainable }
}

fn write_labels(path: &Path, columns: &[&[(u32, f32)]], authors: usize) {
    let mut out = BufWriter::with_capacity(WRITE_BYTES, File::create(path).unwrap());
    out.write_all(&header("<f4", &[authors, columns.len()])).unwrap();
    let width = columns.len();
    let mut cursors = vec![0usize; width];
    let mut block = vec![f32::NAN; LABEL_BLOCK * width];
    for start in (0..authors).step_by(LABEL_BLOCK) {
        let end = authors.min(start + LABEL_BLOCK);
        block.fill(f32::NAN);
        for ((target, entries), cursor) in columns.iter().enumerate().zip(cursors.iter_mut()) {
            while *cursor < entries.len() && (entries[*cursor].0 as usize) < end {
                let (row, value) = entries[*cursor];
                block[(row as usize - start) * width + target] = value;
                *cursor += 1;
            }
        }
        out.write_all(raw(&block[..(end - start) * width])).unwrap();
    }
    out.flush().unwrap();
}

fn write_authors(path: &Path, authors: &[String], order: &[u32]) {
    let mut out = BufWriter::with_capacity(WRITE_BYTES, File::create(path).unwrap());
    let mut text = String::new();
    for (index, author) in order.iter().map(|&row| &authors[row as usize]).enumerate() {
        text.clear();
        text.push_str(if index == 0 { "[" } else { "," });
        text.push_str(NEWLINE);
        text.push_str("  ");
        escape(author, &mut text);
        out.write_all(text.as_bytes()).unwrap();
    }
    out.write_all(if authors.is_empty() { format!("[]{NEWLINE}") } else { format!("{NEWLINE}]{NEWLINE}") }.as_bytes()).unwrap();
    out.flush().unwrap();
}

fn labels(staging: &Path, kinds: &[(String, String)], attributes: &[Attribute], authors: &[String], order: &[u32], splits: &[u8], threads: usize) -> Vec<Encoded> {
    let next = AtomicUsize::new(0);
    let results: Vec<Mutex<Option<Encoded>>> = kinds.iter().map(|_| Mutex::new(None)).collect();
    timed("encode labels", || {
        thread::scope(|scope| {
            for _ in 0..threads {
                scope.spawn(|| loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    if index >= kinds.len() {
                        break;
                    }
                    let (name, kind) = &kinds[index];
                    *results[index].lock().unwrap() = Some(encode(name, kind, &attributes[index], splits));
                });
            }
        })
    });
    let encoded: Vec<Encoded> = results.into_iter().map(|result| result.into_inner().unwrap().unwrap()).collect();
    assert!(encoded.iter().any(|encoded| encoded.trainable), "No consolidated attribute has enough labels to train");
    let columns: Vec<&[(u32, f32)]> = encoded.iter().filter(|encoded| encoded.trainable).map(|encoded| encoded.entries.as_slice()).collect();
    timed("write labels", || write_labels(&staging.join("labels.npy"), &columns, splits.len()));
    timed("write sets", || {
        for ((name, _), encoded) in kinds.iter().zip(&encoded) {
            if let Some((indptr, values)) = &encoded.sets {
                save(&staging.join("sets").join(format!("{name}.indptr.npy")), "<i8", &[indptr.len()], indptr);
                save(&staging.join("sets").join(format!("{name}.values.npy")), "<i4", &[values.len()], values);
            }
        }
    });
    save(&staging.join("splits.npy"), "|u1", &[splits.len()], splits);
    timed("write authors", || write_authors(&staging.join("authors.json"), authors, order));
    encoded
}

fn features(sample: &[f16], rows: usize) -> (Vec<f32>, Vec<f32>) {
    let mut center = vec![0f32; DIMENSIONS];
    let mut spread = vec![0f32; DIMENSIONS];
    thread::scope(|scope| {
        for (first, (center, spread)) in center.chunks_mut(FEATURE_BLOCK).zip(spread.chunks_mut(FEATURE_BLOCK)).enumerate() {
            scope.spawn(move || {
                let columns = first * FEATURE_BLOCK..first * FEATURE_BLOCK + center.len();
                let mut floats = vec![0f32; center.len()];
                let mut sums = vec![0f32; center.len()];
                for row in sample.chunks_exact(DIMENSIONS) {
                    row[columns.clone()].convert_to_f32_slice(&mut floats);
                    for (sum, float) in sums.iter_mut().zip(&floats) {
                        *sum += float;
                    }
                }
                for (mean, sum) in center.iter_mut().zip(&sums) {
                    *mean = (*sum as f64 / rows as f64) as f32;
                }
                sums.fill(0.);
                for row in sample.chunks_exact(DIMENSIONS) {
                    row[columns.clone()].convert_to_f32_slice(&mut floats);
                    for ((sum, float), mean) in sums.iter_mut().zip(&floats).zip(center.iter()) {
                        let offset = float - mean;
                        *sum += offset * offset;
                    }
                }
                for (deviation, sum) in spread.iter_mut().zip(&sums) {
                    *deviation = ((*sum as f64 / rows as f64) as f32).sqrt().max(1e-4);
                }
            });
        }
    });
    (center, spread)
}

fn float(value: f64) -> String {
    assert!(value.is_finite(), "manifest float {value} is not finite");
    let scientific = format!("{value:e}");
    let (mantissa, exponent) = scientific.split_once('e').unwrap();
    let exponent: i32 = exponent.parse().unwrap();
    let sign = if mantissa.starts_with('-') { "-" } else { "" };
    let digits: String = mantissa.chars().filter(char::is_ascii_digit).collect();
    if !(-4..16).contains(&exponent) {
        let fraction = if digits.len() > 1 { format!(".{}", &digits[1..]) } else { String::new() };
        format!("{sign}{}{fraction}e{}{:02}", &digits[..1], if exponent < 0 { '-' } else { '+' }, exponent.abs())
    } else if exponent < 0 {
        format!("{sign}0.{}{digits}", "0".repeat((-exponent - 1) as usize))
    } else if digits.len() <= exponent as usize + 1 {
        format!("{sign}{digits}{}.0", "0".repeat(exponent as usize + 1 - digits.len()))
    } else {
        format!("{sign}{}.{}", &digits[..exponent as usize + 1], &digits[exponent as usize + 1..])
    }
}

fn escape(text: &str, out: &mut String) {
    out.push('"');
    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            control if (control as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", control as u32)),
            other => out.push(other),
        }
    }
    out.push('"');
}

fn render(value: &Json, depth: usize, out: &mut String) {
    let open = |out: &mut String, index: usize| {
        if index > 0 {
            out.push(',');
        }
        out.push_str(NEWLINE);
        out.push_str(&"  ".repeat(depth + 1));
    };
    match value {
        Json::Int(number) => out.push_str(&number.to_string()),
        Json::Float(number) => out.push_str(&float(*number)),
        Json::Text(text) => escape(text, out),
        Json::List(items) if items.is_empty() => out.push_str("[]"),
        Json::Map(items) if items.is_empty() => out.push_str("{}"),
        Json::List(items) => {
            out.push('[');
            for (index, item) in items.iter().enumerate() {
                open(out, index);
                render(item, depth + 1, out);
            }
            out.push_str(NEWLINE);
            out.push_str(&"  ".repeat(depth));
            out.push(']');
        }
        Json::Map(items) => {
            out.push('{');
            for (index, (key, item)) in items.iter().enumerate() {
                open(out, index);
                escape(key, out);
                out.push_str(": ");
                render(item, depth + 1, out);
            }
            out.push_str(NEWLINE);
            out.push_str(&"  ".repeat(depth));
            out.push('}');
        }
    }
}

fn manifest(path: &Path, kinds: &[(String, String)], encoded: &[Encoded], bounds: &[usize; 5], months: Vec<(String, Json)>, center: Vec<f32>, spread: Vec<f32>) {
    let trainable: Vec<(&String, &Encoded)> = kinds.iter().map(|(name, _)| name).zip(encoded).filter(|(_, encoded)| encoded.trainable).collect();
    let floats = |values: Vec<f32>| Json::List(values.into_iter().map(|value| Json::Float(value as f64)).collect());
    let named = |value: fn(&Encoded) -> Json| Json::Map(trainable.iter().map(|(name, encoded)| (name.to_string(), value(encoded))).collect());
    let catalogs = trainable.iter().filter_map(|(name, encoded)| encoded.names.as_ref().map(|names| (name.to_string(), Json::List(names.iter().cloned().map(Json::Text).collect()))));
    let insufficient = kinds.iter().zip(encoded).filter(|(_, encoded)| !encoded.trainable).map(|((name, _), encoded)| {
        let labels = SPLITS.iter().zip(encoded.counts).map(|(split, count)| (split.to_string(), Json::Int(count))).collect::<Vec<_>>();
        (name.clone(), Json::Map(vec![(String::from("labels"), Json::Map(labels)), (String::from("values"), Json::Int(encoded.names.as_ref().map_or(0, Vec::len)))]))
    });
    let manifest = Json::Map(vec![
        (String::from("targets"), named(|encoded| Json::Text(encoded.target.unwrap().to_string()))),
        (String::from("catalogs"), Json::Map(catalogs.collect())),
        (String::from("authors"), Json::Int(bounds[4])),
        (String::from("splits"), Json::Map(SPLITS.iter().enumerate().map(|(split, name)| (name.to_string(), Json::List(vec![Json::Int(bounds[split]), Json::Int(bounds[split + 1])]))).collect())),
        (String::from("source"), Json::Map(vec![(String::from("months"), Json::Map(months))])),
        (String::from("features"), Json::Map(vec![(String::from("dimensions"), Json::Int(DIMENSIONS)), (String::from("center"), floats(center)), (String::from("spread"), floats(spread))])),
        (String::from("target_counts"), named(|encoded| Json::Int(encoded.counts.iter().sum()))),
        (String::from("split_labels"), named(|encoded| Json::List(encoded.counts.iter().map(|&count| Json::Int(count)).collect()))),
        (String::from("excluded_values"), named(|encoded| Json::Int(encoded.excluded))),
        (String::from("insufficient"), Json::Map(insufficient.collect())),
    ]);
    let mut text = String::new();
    render(&manifest, 0, &mut text);
    text.push_str(NEWLINE);
    fs::write(path, text).unwrap();
}

fn prepare(database: &Database, directory: &Path, threads: usize) {
    let staging = directory.with_file_name(format!("{}.staging", directory.file_name().unwrap().to_str().unwrap()));
    if staging.exists() {
        fs::remove_dir_all(&staging).unwrap();
    }
    let months = timed("months", || months(database));
    let kinds = timed("kinds", || kinds(database));
    let names = kinds.iter().map(|(name, _)| quoted(name)).collect::<Vec<_>>().join(", ");
    let (authors, mut attributes) = timed("claims", || claims(database, &kinds, &names));
    fs::create_dir_all(staging.join("sets")).unwrap();
    let splits = timed("splits", || splits(&authors, threads));
    let (order, position, bounds) = timed("layout", || layout(&splits));
    let ordered: Vec<u8> = timed("reorder", || {
        for attribute in &mut attributes {
            for row in &mut attribute.rows {
                row.0 = position[row.0 as usize];
            }
        }
        order.iter().map(|&row| splits[row as usize]).collect()
    });
    let (encoded, (sample, rows)) = thread::scope(|scope| {
        let labels = scope.spawn(|| timed("labels", || labels(&staging, &kinds, &attributes, &authors, &order, &ordered, threads)));
        let vectors = timed("vectors", || vectors(database, &authors, &names, &splits, &bounds, &staging.join("users.npy")));
        (labels.join().unwrap(), vectors)
    });
    let (center, spread) = timed("features", || features(&sample, rows));
    manifest(&staging.join("manifest.json"), &kinds, &encoded, &bounds, months, center, spread);
    if directory.exists() {
        fs::remove_dir_all(directory).unwrap();
    }
    fs::rename(&staging, directory).unwrap();
}

pub fn run(database: &Database, args: &[String]) {
    let directory = PathBuf::from(args.first().filter(|arg| !arg.starts_with("--")).expect("usage: attribute_io prepare DIRECTORY --host HOST"));
    let threads: usize = option(args, "--threads", "1").parse().unwrap();
    timed("prepare", || prepare(database, &directory, threads));
}
