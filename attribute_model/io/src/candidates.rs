use crate::database::Database;
use crate::prepare::{catalog, claims, indexed, latest, quoted, raw, utf8, Attribute, CATEGORICAL_VALUES, SPLIT_LABELS, VALUE_AUTHORS, WRITE_BYTES};
use crate::{log, option, timed};
use serde_json::{json, Map, Value};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::thread;

const FILES: [&str; 4] = ["rows.u32", "values.f32", "pair_rows.u32", "pair_values.u32"];

struct Encoded {
    target: Option<&'static str>,
    names: Option<Vec<String>>,
    rows: Vec<u32>,
    values: Vec<f32>,
    pairs: Option<(Vec<u32>, Vec<u32>)>,
    excluded: usize,
    unmatched: usize,
    counts: [usize; 4],
    trainable: bool,
    spread: bool,
}

struct Slot {
    name: String,
    rows: Vec<u32>,
    values: Vec<f32>,
    pairs: Option<(Vec<u32>, Vec<u32>)>,
    size: usize,
}

fn median(values: &mut [f32]) -> f32 {
    let middle = values.len() / 2;
    let upper = *values.select_nth_unstable_by(middle, f32::total_cmp).1;
    if values.len() % 2 == 1 {
        upper
    } else {
        (values[..middle].iter().copied().fold(f32::NEG_INFINITY, f32::max) + upper) / 2.
    }
}

fn spread(entries: &[(u32, f32)], end: usize) -> bool {
    let mut values: Vec<f32> = entries.iter().take_while(|entry| (entry.0 as usize) < end).map(|entry| entry.1).collect();
    let center = median(&mut values);
    let mut deviations: Vec<f32> = values.iter().map(|value| (value - center).abs()).collect();
    median(&mut deviations) > 0.
}

fn offsets<'a>(count: usize, parts: impl Iterator<Item = &'a [u32]>) -> Vec<i64> {
    let mut indptr = vec![0i64; count + 1];
    for rows in parts {
        for &row in rows {
            indptr[row as usize + 1] += 1;
        }
    }
    for slot in 1..=count {
        indptr[slot] += indptr[slot - 1];
    }
    indptr
}

fn ranges(indptr: &[i64], threads: usize) -> Vec<(usize, usize)> {
    let count = indptr.len() - 1;
    let total = indptr[count];
    let mut cuts: Vec<usize> = (0..=threads).map(|part| indptr.partition_point(|&at| at < total * part as i64 / threads as i64).min(count)).collect();
    cuts[threads] = count;
    cuts.dedup();
    cuts.windows(2).map(|pair| (pair[0], pair[1])).collect()
}

fn split<'a, T>(mut array: &'a mut [T], indptr: &[i64], ranges: &[(usize, usize)]) -> Vec<&'a mut [T]> {
    let mut parts = Vec::with_capacity(ranges.len());
    for &(start, end) in ranges {
        let (part, rest) = array.split_at_mut((indptr[end] - indptr[start]) as usize);
        parts.push(part);
        array = rest;
    }
    parts
}

fn bounds(rows: &[u32], start: usize, end: usize) -> (usize, usize) {
    (rows.partition_point(|&row| (row as usize) < start), rows.partition_point(|&row| (row as usize) < end))
}

fn labels(count: usize, slots: &[Slot], threads: usize) -> (Vec<i64>, Vec<i16>, Vec<f32>) {
    let indptr = offsets(count, slots.iter().map(|slot| &slot.rows[..]));
    let ranges = ranges(&indptr, threads);
    let total = indptr[count] as usize;
    let (mut columns, mut values) = (vec![0i16; total], vec![0f32; total]);
    thread::scope(|scope| {
        for ((&(start, end), columns), values) in ranges.iter().zip(split(&mut columns, &indptr, &ranges)).zip(split(&mut values, &indptr, &ranges)) {
            let indptr = &indptr;
            scope.spawn(move || {
                let mut cursor: Vec<usize> = indptr[start..end].iter().map(|&at| (at - indptr[start]) as usize).collect();
                for (column, slot) in slots.iter().enumerate() {
                    let (low, high) = bounds(&slot.rows, start, end);
                    for (&row, &value) in slot.rows[low..high].iter().zip(&slot.values[low..high]) {
                        let at = &mut cursor[row as usize - start];
                        columns[*at] = column as i16;
                        values[*at] = value;
                        *at += 1;
                    }
                }
            });
        }
    });
    (indptr, columns, values)
}

fn members(count: usize, sets: &[&(Vec<u32>, Vec<u32>)], threads: usize) -> (Vec<i64>, Vec<i16>, Vec<i16>, Vec<i16>) {
    let indptr = offsets(count, sets.iter().map(|pairs| &pairs.0[..]));
    let ranges = ranges(&indptr, threads);
    let total = indptr[count] as usize;
    let (mut slots, mut ranks, mut values) = (vec![0i16; total], vec![0i16; total], vec![0i16; total]);
    thread::scope(|scope| {
        let parts = split(&mut slots, &indptr, &ranges).into_iter().zip(split(&mut ranks, &indptr, &ranges)).zip(split(&mut values, &indptr, &ranges));
        for (&(start, end), ((slots, ranks), values)) in ranges.iter().zip(parts) {
            let indptr = &indptr;
            scope.spawn(move || {
                let mut cursor: Vec<usize> = indptr[start..end].iter().map(|&at| (at - indptr[start]) as usize).collect();
                for (order, pairs) in sets.iter().enumerate() {
                    let (low, high) = bounds(&pairs.0, start, end);
                    let (mut previous, mut rank) = (u32::MAX, 0i16);
                    for (&row, &value) in pairs.0[low..high].iter().zip(&pairs.1[low..high]) {
                        rank = if row == previous { rank + 1 } else { 0 };
                        previous = row;
                        let at = &mut cursor[row as usize - start];
                        slots[*at] = order as i16;
                        ranks[*at] = rank;
                        values[*at] = value as i16;
                        *at += 1;
                    }
                }
            });
        }
    });
    (indptr, slots, ranks, values)
}

fn write<T: Copy>(output: &Path, name: &str, values: &[T]) {
    fs::write(output.join(name), raw(values)).unwrap();
}

fn layout(output: &Path, count: usize, slots: &[Slot], threads: usize) -> Value {
    let sets: Vec<(usize, &(Vec<u32>, Vec<u32>), usize)> = slots.iter().enumerate().filter_map(|(column, slot)| slot.pairs.as_ref().map(|pairs| (column, pairs, slot.size))).collect();
    let longest: Vec<usize> = sets.iter().map(|(_, pairs, _)| pairs.0.chunk_by(|left, right| left == right).map(<[u32]>::len).max().unwrap()).collect();
    let limit = i16::MAX as usize;
    assert!(slots.len() <= limit && sets.iter().all(|set| set.2 <= limit) && longest.iter().all(|&size| size <= limit), "label indexes do not fit int16");
    let (indptr, columns, values) = timed("label layout", || labels(count, slots, threads));
    write(output, "label_indptr.i64", &indptr);
    write(output, "label_columns.i16", &columns);
    write(output, "label_values.f32", &values);
    let entries = columns.len();
    drop((indptr, columns, values));
    let pairs: Vec<&(Vec<u32>, Vec<u32>)> = sets.iter().map(|set| set.1).collect();
    let (indptr, set_slots, ranks, set_values) = timed("member layout", || members(count, &pairs, threads));
    write(output, "member_indptr.i64", &indptr);
    write(output, "member_slot.i16", &set_slots);
    write(output, "member_rank.i16", &ranks);
    write(output, "member_value.i16", &set_values);
    log(&format!("layout slots={} sets={} labels={entries} members={}", slots.len(), sets.len(), set_slots.len()));
    json!({"slots": slots.iter().map(|slot| &slot.name).collect::<Vec<_>>(), "sets": sets.iter().zip(&longest).map(|(set, &size)| [set.0, size, set.2]).collect::<Vec<_>>(),
           "labels": entries, "members": set_slots.len()})
}

fn kinds(database: &Database) -> Vec<(String, String)> {
    let mut rows = database.rows("SELECT attribute, kind FROM claim_attributes WHERE kind IN ('number', 'one', 'set') ORDER BY attribute FORMAT RowBinary");
    let mut found = Vec::new();
    while !rows.done() {
        let attribute = utf8(rows.bytes());
        found.push((attribute, utf8(rows.bytes())));
    }
    assert!(!found.is_empty(), "claim_attributes lists no number, one or set attribute");
    log(&format!("candidates={}", found.len()));
    found
}

fn index(directory: &Path) -> (Vec<String>, [usize; 3]) {
    let authors: Vec<String> = serde_json::from_slice(&fs::read(directory.join("authors.json")).unwrap()).unwrap();
    let manifest: Value = serde_json::from_slice(&fs::read(directory.join("manifest.json")).unwrap()).unwrap();
    assert!(manifest["authors"].as_u64() == Some(authors.len() as u64), "authors.json does not match the manifest in {}", directory.display());
    let edges = ["train", "validation", "calibration"].map(|split| manifest["splits"][split][1].as_u64().unwrap() as usize);
    log(&format!("index authors={} edges={edges:?}", authors.len()));
    (authors, edges)
}

fn mapping(index: &[String], authors: &[String], threads: usize) -> Vec<u32> {
    let size = index.len().div_ceil(threads).max(1);
    let found: Vec<Vec<(usize, u32)>> = thread::scope(|scope| {
        let handles: Vec<_> = index
            .chunks(size)
            .enumerate()
            .map(|(chunk, names)| scope.spawn(move || names.iter().enumerate().filter_map(|(offset, name)| authors.binary_search(name).ok().map(|slot| (slot, (chunk * size + offset) as u32))).collect()))
            .collect();
        handles.into_iter().map(|handle| handle.join().unwrap()).collect()
    });
    let mut mapped = vec![u32::MAX; authors.len()];
    for (slot, row) in found.into_iter().flatten() {
        mapped[slot] = row;
    }
    log(&format!("mapped claim authors={} of {}", mapped.iter().filter(|&&row| row != u32::MAX).count(), authors.len()));
    mapped
}

fn encode(name: &str, kind: &str, claims: &Attribute, mapped: &[u32], edges: &[usize; 3]) -> Encoded {
    let matched: Vec<(u32, u32)> = claims.rows.iter().filter_map(|&(author, value)| Some(mapped[author as usize]).filter(|&row| row != u32::MAX).map(|row| (row, value))).collect();
    let unmatched = claims.rows.len() - matched.len();
    let (target, names, entries, pairs, excluded) = if matched.is_empty() {
        (None, Some(Vec::new()), Vec::new(), None, 0)
    } else {
        match kind {
            "number" => {
                let numbers: Vec<f32> = claims.values.iter().map(|value| value.parse::<f64>().unwrap_or_else(|_| panic!("{name}: number claim {value:?} is not a float")) as f32).collect();
                let (entries, excluded) = latest(&matched, |id| numbers[id as usize]);
                (Some("numeric"), None, entries, None, excluded)
            }
            "one" => {
                let common = catalog(&matched, &claims.values, VALUE_AUTHORS);
                let (names, target) = if common.len() > CATEGORICAL_VALUES { (common, "embedding") } else { (catalog(&matched, &claims.values, 1), "categorical") };
                let index = indexed(&claims.values, &names);
                let (entries, excluded) = latest(&matched, |id| index[id as usize].map_or(f32::NAN, |position| position as f32));
                (Some(target), Some(names), entries, None, excluded)
            }
            "set" => {
                let names = catalog(&matched, &claims.values, VALUE_AUTHORS);
                let index = indexed(&claims.values, &names);
                let mut kept: Vec<(u32, u32)> = matched.iter().filter_map(|&(row, value)| index[value as usize].map(|position| (row, position))).collect();
                kept.sort_unstable();
                let mut entries: Vec<(u32, f32)> = kept.iter().map(|&(row, _)| (row, 1.)).collect();
                entries.dedup_by_key(|entry| entry.0);
                let excluded = matched.len() - kept.len();
                (Some("set"), Some(names), entries, Some(kept.into_iter().unzip()), excluded)
            }
            other => panic!("{name}: kind {other:?} is not number, one or set"),
        }
    };
    let entries: Vec<(u32, f32)> = entries.into_iter().filter(|entry| entry.1.is_finite()).collect();
    let mut counts = [0usize; 4];
    for &(row, _) in &entries {
        counts[edges.iter().filter(|&&edge| edge <= row as usize).count()] += 1;
    }
    let values = names.as_ref().map_or(0, Vec::len);
    let trainable = target.is_some() && counts.iter().all(|&count| count >= SPLIT_LABELS) && (target == Some("numeric") || values >= 2);
    let spread = !(trainable && target == Some("numeric")) || spread(&entries, edges[0]);
    let (rows, numbers) = if trainable { entries.into_iter().unzip() } else { (Vec::new(), Vec::new()) };
    Encoded { target, names, rows, values: numbers, pairs: pairs.filter(|_| trainable), excluded, unmatched, counts, trainable, spread }
}

fn build(database: &Database, output: &Path, directory: &Path, threads: usize) {
    let (index, edges) = timed("index", || index(directory));
    let kinds = timed("kinds", || kinds(database));
    let names = kinds.iter().map(|(name, _)| quoted(name)).collect::<Vec<_>>().join(", ");
    let (authors, attributes) = timed("claims", || claims(database, &kinds, &names, false));
    let mapped = timed("map authors", || mapping(&index, &authors, threads));
    let count = index.len();
    drop(index);
    fs::create_dir_all(output).unwrap();
    let mut files: Vec<BufWriter<File>> = FILES.iter().map(|name| BufWriter::with_capacity(WRITE_BYTES, File::create(output.join(name)).unwrap())).collect();
    let (mut targets, mut entries, mut pairs, mut slots) = (Map::new(), 0usize, 0usize, Vec::new());
    let order: Vec<usize> = (0..kinds.len()).collect();
    timed("encode", || {
        for chunk in order.chunks(threads) {
            let encoded: Vec<Encoded> = thread::scope(|scope| {
                let (kinds, attributes, mapped, edges) = (&kinds, &attributes, &mapped, &edges);
                let handles: Vec<_> = chunk.iter().map(|&slot| scope.spawn(move || encode(&kinds[slot].0, &kinds[slot].1, &attributes[slot], mapped, edges))).collect();
                handles.into_iter().map(|handle| handle.join().unwrap()).collect()
            });
            for (&slot, encoded) in chunk.iter().zip(encoded) {
                files[0].write_all(raw(&encoded.rows)).unwrap();
                files[1].write_all(raw(&encoded.values)).unwrap();
                let pair_range = encoded.pairs.as_ref().map(|(rows, values)| {
                    files[2].write_all(raw(rows)).unwrap();
                    files[3].write_all(raw(values)).unwrap();
                    pairs += rows.len();
                    [pairs - rows.len(), pairs]
                });
                entries += encoded.rows.len();
                targets.insert(
                    kinds[slot].0.clone(),
                    json!({"kind": kinds[slot].1, "target": encoded.target, "names": encoded.names, "excluded": encoded.excluded, "unmatched": encoded.unmatched,
                           "counts": encoded.counts, "trainable": encoded.trainable, "spread": encoded.spread, "entries": [entries - encoded.rows.len(), entries], "pairs": pair_range}),
                );
                if encoded.trainable && encoded.spread {
                    slots.push(Slot { name: kinds[slot].0.clone(), size: encoded.names.as_ref().map_or(0, Vec::len), rows: encoded.rows, values: encoded.values, pairs: encoded.pairs });
                }
            }
        }
    });
    for file in &mut files {
        file.flush().unwrap();
    }
    drop((files, authors, attributes, mapped));
    let layout = timed("layout", || layout(output, count, &slots, threads));
    let summary = json!({"index": directory.to_str().unwrap(), "authors": count, "edges": edges, "entries": entries, "pairs": pairs, "targets": targets, "layout": layout});
    fs::write(output.join("targets.json"), serde_json::to_string(&summary).unwrap()).unwrap();
    log(&format!("candidate labels entries={entries} pairs={pairs} trainable={}", summary["targets"].as_object().unwrap().values().filter(|target| target["trainable"] == true).count()));
}

pub fn run(database: &Database, args: &[String]) {
    let output = PathBuf::from(args.first().filter(|arg| !arg.starts_with("--")).expect("usage: attribute_io candidates OUTPUT --index DIRECTORY --host HOST --database DATABASE"));
    let directory = PathBuf::from(option(args, "--index", ""));
    assert!(directory.join("authors.json").exists(), "--index must name a prepared model directory");
    let threads: usize = option(args, "--threads", "1").parse().unwrap();
    timed("candidates", || build(database, &output, &directory, threads));
}
