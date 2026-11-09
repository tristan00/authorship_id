import json
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from database import author_ranges, author_span, client

from . import LOG, timed, write_json
from .config import CATEGORICAL_VALUES, DIMENSIONS, SPLITS, VALUE_AUTHORS, VECTOR_RANGES, partition, validate

ATTRIBUTES = "SELECT attribute, kind FROM author_attributes ORDER BY attribute"
CLAIMS = "SELECT author, attribute, value FROM author_claims WHERE attribute IN {attributes:Array(String)}"
VECTORS = "SELECT author, vector FROM author_vectors WHERE {where} AND author IN (SELECT author FROM labeled WHERE {where}) ORDER BY author"
ARRAYS = ("users", "labels", "splits")
SPREAD_ROWS = 1 << 20


def months(db):
    return {month: str(loaded) for month, loaded in db.query("SELECT month, loaded_at FROM months ORDER BY month").result_rows}


@timed
def read_kinds(db):
    kinds = dict(db.query(ATTRIBUTES).result_rows)
    if not kinds:
        raise ValueError("author_attributes is empty; claim consolidation publishes it")
    LOG.info("consolidated attributes=%d kinds=%s", len(kinds), sorted(set(kinds.values())))
    return kinds


@timed
def read_claims(db, attributes):
    table = db.query_arrow(CLAIMS, parameters={"attributes": attributes})
    LOG.info("attribute claims rows=%d", table.num_rows)
    return table


def catalog(values, minimum):
    counts = pc.value_counts(values).to_pylist()
    return [item["values"] for item in sorted(counts, key=lambda item: (-item["counts"], item["values"])) if item["counts"] >= minimum]


def indexed(values, names):
    return pc.index_in(values, value_set=pa.array(names, pa.string())).to_numpy(zero_copy_only=False).astype(np.float64)


def grouped(rows, values, authors):
    order = np.lexsort((values, rows))
    rows, values = rows[order], values[order]
    indptr = np.concatenate([[0], np.cumsum(np.bincount(rows, minlength=authors))]).astype(np.int64)
    return indptr, values.astype(np.int32)


@timed
def read_vectors(db, labeled, path):
    db.command("CREATE TEMPORARY TABLE labeled (author String) ENGINE = MergeTree ORDER BY author")
    db.insert_arrow("labeled", pa.table({"author": labeled}))
    total = db.command("SELECT count() FROM author_vectors WHERE author IN labeled")
    vectors = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(total, DIMENSIONS))
    authors, kept, started = [], 0, time.perf_counter()
    for low, high in author_ranges(db, "author_vectors", VECTOR_RANGES):
        where, parameters = author_span(low, high)
        with db.query_arrow_stream(VECTORS.format(where=where), parameters=parameters) as stream:
            for batch in stream:
                vectors[kept:kept + batch.num_rows] = batch["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS)
                authors += batch["author"].to_pylist()
                kept += batch.num_rows
                if kept // (1 << 20) != (kept - batch.num_rows) // (1 << 20):
                    LOG.info("labeled vectors kept=%d of %d seconds=%.1f", kept, total, time.perf_counter() - started)
    db.command("DROP TEMPORARY TABLE labeled")
    if kept != total:
        raise ValueError("Author vectors changed while they were read")
    vectors.flush()
    return vectors, authors


def encoded(name, kind, values, rows, authors):
    if kind == "number":
        return "numeric", pc.cast(values, pa.float64()).to_numpy(), None, None
    if kind == "one":
        common = catalog(values, VALUE_AUTHORS)
        names, target = (common, "embedding") if len(common) > CATEGORICAL_VALUES else (catalog(values, 1), "categorical")
        return target, indexed(values, names), names, None
    if kind == "set":
        names = catalog(values, VALUE_AUTHORS)
        index = indexed(values, names)
        kept = np.isfinite(index)
        return "set", np.where(kept, 1., np.nan), names, grouped(rows[kept], index[kept].astype(np.int64), authors)
    raise ValueError(f"{name}: consolidated kind {kind!r} is not number, one or set")


@timed
def prepare(directory):
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    db = client()
    source = {"months": months(db)}
    kinds = read_kinds(db)
    claims = read_claims(db, list(kinds))
    names = pc.unique(claims["author"])
    LOG.info("labeled authors=%d rows=%d", len(names), claims.num_rows)
    staging.mkdir(parents=True)
    (staging / "sets").mkdir()
    vectors, authors = read_vectors(db, names, staging / "users.npy")
    position = pc.fill_null(pc.index_in(claims["author"], value_set=pa.array(authors, pa.string())), -1).to_numpy()
    labels = np.full((len(authors), len(kinds)), np.nan, dtype=np.float32)
    targets, catalogs, excluded = {}, {}, {}
    attributes = claims["attribute"]
    for column, (name, kind) in enumerate(kinds.items()):
        selected = np.flatnonzero((position >= 0) & pc.equal(attributes, name).to_numpy(zero_copy_only=False))
        if not len(selected):
            raise ValueError(f"No observed labels for consolidated attribute {name}")
        rows = position[selected]
        target, column_values, names, sets = encoded(name, kind, claims["value"].take(pa.array(selected)), rows, len(authors))
        targets[name] = target
        if target == "set":
            np.save(staging / "sets" / f"{name}.indptr.npy", sets[0])
            np.save(staging / "sets" / f"{name}.values.npy", sets[1])
            present = np.flatnonzero(np.diff(sets[0]))
            labels[present, column] = 1.
            excluded[name] = int(len(selected) - len(sets[1]))
        else:
            labels[rows, column] = column_values
            excluded[name] = int(len(selected) - np.isfinite(labels[rows, column]).sum())
        if names is not None:
            catalogs[name] = names
    splits = np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors))
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(vectors[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": DIMENSIONS, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    for name, array in (("labels", labels), ("splits", splits)):
        np.save(staging / f"{name}.npy", array)
    write_json(staging / "authors.json", authors)
    counts = np.isfinite(labels).sum(0)
    manifest = {"targets": validate(targets), "catalogs": catalogs, "authors": len(authors), "source": source, "features": features,
                "target_counts": {name: int(count) for name, count in zip(targets, counts)}, "excluded_values": excluded}
    write_json(staging / "manifest.json", manifest)
    del vectors
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"authors": len(authors), "directory": str(directory), "targets": targets, "target_counts": manifest["target_counts"], "excluded_values": excluded}


def load(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    targets = validate(manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or arrays["labels"].shape != (manifest["authors"], len(targets)) or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    sets = {name: tuple(np.load(directory / "sets" / f"{name}.{part}.npy", mmap_mode="r", allow_pickle=False) for part in ("indptr", "values"))
            for name, kind in targets.items() if kind == "set"}
    if any(len(indptr) != manifest["authors"] + 1 for indptr, _ in sets.values()):
        raise ValueError("Prepared value lists do not match the manifest")
    return manifest, arrays, sets
