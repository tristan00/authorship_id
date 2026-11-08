import json
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from author_encoder.store import parts, span
from database import client

from . import LOG, timed, write_json
from .config import DEFAULTS, DIMENSIONS, NUMERIC, SPLITS, VALUE_AUTHORS, check_targets, partition, validate
from .features import bags, vocabulary

CLAIMS = "SELECT author, attribute, value, support, share FROM author_claims WHERE attribute IN {attributes:Array(String)}"
VECTORS = ("WITH picked AS (SELECT author FROM labeled WHERE {where}) SELECT author, vector, subreddits, counts FROM author_vectors "
           "INNER JOIN (SELECT author, subreddits, counts FROM author_subreddits WHERE {where} AND author IN picked) AS s USING author WHERE {where} AND author IN picked ORDER BY author")
ARRAYS = ("users", "subreddits", "weights", "labels", "support", "share", "splits")
SPREAD_ROWS = 1 << 20


def months(db):
    return {month: str(loaded) for month, loaded in db.query("SELECT month, loaded_at FROM months ORDER BY month").result_rows}


@timed
def read_claims(db, targets):
    table = db.query_arrow(CLAIMS, parameters={"attributes": list(targets)})
    LOG.info("attribute claims rows=%d", table.num_rows)
    return table


def encode(values, name, kind):
    if kind == "numeric":
        numbers = pc.cast(values, pa.float64()).to_numpy()
        low, high = NUMERIC[name]
        return np.where((numbers >= low) & (numbers <= high), numbers, np.nan), None
    counts = pc.value_counts(values).to_pylist()
    catalog = [item["values"] for item in sorted(counts, key=lambda item: (-item["counts"], item["values"])) if kind != "embedding" or item["counts"] >= VALUE_AUTHORS]
    if name in DEFAULTS and DEFAULTS[name] not in catalog:
        catalog.append(DEFAULTS[name])
    return pc.index_in(values, value_set=pa.array(catalog)).to_numpy().astype(np.float64), catalog


@timed
def read_vectors(db, labeled, path):
    db.command("CREATE TEMPORARY TABLE labeled (author String) ENGINE = MergeTree ORDER BY author")
    db.insert_arrow("labeled", pa.table({"author": labeled}))
    total = db.command("SELECT count() FROM author_vectors WHERE author IN labeled")
    vectors = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(total, DIMENSIONS))
    authors, names, counts, kept, started = [], [], [], 0, time.perf_counter()
    for low, high in parts(db):
        where, parameters = span(low, high)
        with db.query_arrow_stream(VECTORS.format(where=where), parameters=parameters) as stream:
            for batch in stream:
                vectors[kept:kept + batch.num_rows] = batch["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS)
                authors += batch["author"].to_pylist()
                names.append(batch["subreddits"])
                counts.append(batch["counts"])
                kept += batch.num_rows
                if kept // (1 << 20) != (kept - batch.num_rows) // (1 << 20):
                    LOG.info("labeled vectors kept=%d of %d seconds=%.1f", kept, total, time.perf_counter() - started)
    db.command("DROP TEMPORARY TABLE labeled")
    if kept != total:
        raise ValueError("Author vectors changed while they were read")
    vectors.flush()
    return vectors, authors, pa.concat_arrays(names), pa.concat_arrays(counts)


@timed
def prepare(directory, targets):
    targets = validate(targets)
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    db = client()
    source = {"months": months(db)}
    claims = read_claims(db, targets)
    names = pc.unique(claims["author"])
    LOG.info("labeled authors=%d rows=%d", len(names), claims.num_rows)
    staging.mkdir(parents=True)
    vectors, authors, subreddits, counts = read_vectors(db, names, staging / "users.npy")
    position = pc.fill_null(pc.index_in(claims["author"], value_set=pa.array(authors, pa.string())), -1).to_numpy()
    shape = (len(authors), len(targets))
    labels = np.full(shape, np.nan, dtype=np.float32)
    support, share = np.full(shape, np.nan, dtype=np.float16), np.full(shape, np.nan, dtype=np.float16)
    catalogs, excluded = {}, {}
    attributes = claims["attribute"]
    for column, (name, kind) in enumerate(targets.items()):
        selected = np.flatnonzero((position >= 0) & pc.equal(attributes, name).to_numpy(zero_copy_only=False))
        if not len(selected):
            raise ValueError(f"No observed labels for configured field {name}")
        rows = position[selected]
        labels[rows, column], catalog = encode(claims["value"].take(pa.array(selected)), name, kind)
        support[rows, column] = claims["support"].take(pa.array(selected)).to_numpy()
        share[rows, column] = claims["share"].take(pa.array(selected)).to_numpy()
        excluded[name] = int(len(selected) - np.isfinite(labels[rows, column]).sum())
        if catalog is not None:
            catalogs[name] = catalog
    splits = np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors))
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(vectors[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": DIMENSIONS, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    known = vocabulary(subreddits.take(pa.array(training)))
    ids, weights = bags(subreddits, counts, pa.array(known, pa.string()))
    for name, array in (("subreddits", ids), ("weights", weights), ("labels", labels), ("support", support), ("share", share), ("splits", splits)):
        np.save(staging / f"{name}.npy", array)
    write_json(staging / "authors.json", authors)
    counts = np.isfinite(labels).sum(0)
    manifest = {"targets": targets, "catalogs": catalogs, "subreddits": known, "authors": len(authors), "source": source, "features": features, "target_counts": {name: int(count) for name, count in zip(targets, counts)},
                "excluded_out_of_range": excluded, "numeric_ranges": {name: NUMERIC[name] for name, kind in targets.items() if kind == "numeric"}}
    write_json(staging / "manifest.json", manifest)
    del vectors
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"authors": len(authors), "directory": str(directory), "target_counts": manifest["target_counts"], "excluded_out_of_range": excluded}


def load(directory, targets):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    check_targets(targets, manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or any(arrays[name].shape != (manifest["authors"], len(targets)) for name in ("labels", "support", "share")) or arrays["subreddits"].shape != arrays["weights"].shape or len(arrays["subreddits"]) != manifest["authors"] or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    return manifest, arrays
