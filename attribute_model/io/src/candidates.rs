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
    let (rows, numbers) = if trainable { entries.into_iter().unzip() } else { (Vec::new(), Vec::new()) };
    Encoded { target, names, rows, values: numbers, pairs: pairs.filter(|_| trainable), excluded, unmatched, counts, trainable }
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
    let (mut targets, mut entries, mut pairs) = (Map::new(), 0usize, 0usize);
    let slots: Vec<usize> = (0..kinds.len()).collect();
    timed("encode", || {
        for chunk in slots.chunks(threads) {
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
                           "counts": encoded.counts, "trainable": encoded.trainable, "entries": [entries - encoded.rows.len(), entries], "pairs": pair_range}),
                );
            }
        }
    });
    for file in &mut files {
        file.flush().unwrap();
    }
    let summary = json!({"index": directory.to_str().unwrap(), "authors": count, "edges": edges, "entries": entries, "pairs": pairs, "targets": targets});
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
