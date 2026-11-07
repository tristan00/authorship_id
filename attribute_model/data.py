import json
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from claim_consolidation.config import NUMERIC
from claim_extraction.schema import FLAIR_ATTRIBUTES
from database import client

from . import LOG, timed, write_json
from .config import DEFAULTS, DIMENSIONS, SPLITS, STRICT_SHARE, STRICT_SUPPORT, VALUE_AUTHORS, check_targets, partition, validate

CLAIMS = "SELECT author, attribute, value, support, share FROM author_claims WHERE attribute IN {attributes:Array(String)}"
VECTORS = "SELECT author, vector FROM author_vectors WHERE author IN labeled ORDER BY author"
ARRAYS = ("users", "labels", "splits")
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
    db.command("CREATE TEMPORARY TABLE labeled (author String)")
    db.insert_arrow("labeled", pa.table({"author": labeled}))
    total = db.command("SELECT count() FROM author_vectors WHERE author IN labeled")
    vectors = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(total, DIMENSIONS))
    authors, kept, started = [], 0, time.perf_counter()
    with db.query_arrow_stream(VECTORS) as stream:
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
    buckets = np.fromiter(map(partition, names.to_pylist()), dtype=np.uint8, count=len(names))
    owner = pc.index_in(claims["author"], value_set=names).to_numpy()
    evaluated = np.isin(buckets[owner], [bucket for name in ("validation", "calibration", "test") for bucket in SPLITS[name]])
    judged = pc.and_(pc.greater_equal(claims["support"], STRICT_SUPPORT), pc.greater_equal(claims["share"], STRICT_SHARE))
    strict = pc.or_(judged, pc.is_in(claims["attribute"], value_set=pa.array(list(FLAIR_ATTRIBUTES)))).to_numpy(zero_copy_only=False)
    keep = ~evaluated | strict
    stated = {name: owner[pc.equal(claims["attribute"], name).to_numpy(zero_copy_only=False)] for name in targets if name in DEFAULTS}
    claims = claims.filter(pa.array(keep))
    owner = owner[keep]
    chosen = np.flatnonzero(np.bincount(owner, minlength=len(names)) > 0)
    labeled = names.take(pa.array(chosen))
    del names
    remap = np.full(len(buckets), -1, dtype=np.int64)
    remap[chosen] = np.arange(len(chosen))
    owner = remap[owner]
    stated = {name: remap[found][remap[found] >= 0] for name, found in stated.items()}
    LOG.info("labeled authors=%d rows=%d", len(labeled), claims.num_rows)
    staging.mkdir(parents=True)
    vectors, authors = read_vectors(db, labeled, staging / "users.npy")
    position = pc.fill_null(pc.index_in(labeled, value_set=pa.array(authors, pa.string())), -1).to_numpy()
    placed = position[owner]
    present = placed >= 0
    labels = np.full((len(authors), len(targets)), np.nan, dtype=np.float32)
    catalogs, excluded = {}, {}
    attributes = claims["attribute"]
    for column, (name, kind) in enumerate(targets.items()):
        selected = np.flatnonzero(present & pc.equal(attributes, name).to_numpy(zero_copy_only=False))
        if not len(selected):
            raise ValueError(f"No observed labels for configured field {name}")
        labels[placed[selected], column], catalog = encode(claims["value"].take(pa.array(selected)), name, kind)
        excluded[name] = int(len(selected) - np.isfinite(labels[placed[selected], column]).sum())
        if catalog is not None:
            catalogs[name] = catalog
        if name in DEFAULTS:
            silent = np.ones(len(authors), dtype=bool)
            spoken = position[stated[name]]
            silent[spoken[spoken >= 0]] = False
            labels[silent, column] = catalog.index(DEFAULTS[name])
    splits = np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors))
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(vectors[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": DIMENSIONS, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    np.save(staging / "labels.npy", labels)
    np.save(staging / "splits.npy", splits)
    write_json(staging / "authors.json", authors)
    counts = np.isfinite(labels).sum(0)
    manifest = {"targets": targets, "catalogs": catalogs, "authors": len(authors), "source": source, "features": features, "target_counts": {name: int(count) for name, count in zip(targets, counts)},
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
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or arrays["labels"].shape != (manifest["authors"], len(targets)) or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    return manifest, arrays
