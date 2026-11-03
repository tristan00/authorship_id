import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import numpy as np

from . import LOG, timed, write_json
from .config import DIMENSIONS, EXACT_CHUNK, EXACT_STORE, EXACT_THREADS, VECTOR_STORE
from .index import users, vector

ROUNDING = 2 * (DIMENSIONS + 3) * 2.0 ** -24
ARRAYS = ("codes", "scales", "slack")


def normalised(vectors):
    values = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(values).all() or not (norms > 0).all():
        raise ValueError("User vectors must be finite and nonzero")
    return values / norms


def manifest(path=VECTOR_STORE):
    dataset = users(path)
    return {"store": str(path), "version": dataset.version, "rows": dataset.count_rows()}


def current(target=EXACT_STORE, path=VECTOR_STORE):
    stamp = target / "manifest.json"
    return stamp.exists() and json.loads(stamp.read_text(encoding="utf-8")) == manifest(path)


@timed
def quantize(path=VECTOR_STORE, target=EXACT_STORE):
    if current(target, path):
        LOG.info("exact search data current path=%s", target)
        return {"skipped": True}
    expected = manifest(path)
    rows = expected["rows"]
    staging, prior = (target.with_name(target.name + suffix) for suffix in (".building", ".previous"))
    for leftover in (staging, prior):
        shutil.rmtree(leftover, ignore_errors=True)
    staging.mkdir(parents=True)
    arrays = {"codes": np.lib.format.open_memmap(staging / "codes.npy", mode="w+", dtype=np.int8, shape=(rows, DIMENSIONS)),
              "scales": np.lib.format.open_memmap(staging / "scales.npy", mode="w+", dtype=np.float64, shape=(rows,)),
              "slack": np.lib.format.open_memmap(staging / "slack.npy", mode="w+", dtype=np.float64, shape=(rows,))}

    def encode(start, values):
        unit = normalised(values)
        scale = np.abs(unit).max(axis=1) / 127
        code = np.rint(unit / scale[:, None]).astype(np.int8)
        residual = np.linalg.norm(unit - code * scale[:, None], axis=1)
        stop = start + len(unit)
        arrays["codes"][start:stop], arrays["scales"][start:stop] = code, scale
        arrays["slack"][start:stop] = (residual + ROUNDING * scale * np.linalg.norm(code.astype(np.float64), axis=1)) * (1 + 1e-9) + 1e-12

    start = 0
    with ThreadPoolExecutor(EXACT_THREADS) as pool:
        for batch in users(path).to_batches(columns=["vector"], batch_size=EXACT_CHUNK):
            values = batch.column("vector").flatten().to_numpy(zero_copy_only=False).reshape(-1, DIMENSIONS)
            step = -(-len(values) // EXACT_THREADS)
            list(pool.map(lambda offset: encode(start + offset, values[offset:offset + step]), range(0, len(values), step)))
            start += len(values)
    if start != rows:
        raise ValueError(f"Read {start} user vectors, the store has {rows}")
    for name in ARRAYS:
        arrays[name].flush()
    arrays.clear()
    write_json(staging / "manifest.json", expected)
    if target.exists():
        target.rename(prior)
    staging.rename(target)
    shutil.rmtree(prior, ignore_errors=True)
    LOG.info("exact search data rows=%d path=%s", rows, target)
    return {"rows": rows, "path": str(target)}


@lru_cache(maxsize=1)
def loaded(target, signature):
    return {name: np.load(target / f"{name}.npy", mmap_mode="r") for name in ARRAYS} | {"manifest": json.loads((target / "manifest.json").read_text(encoding="utf-8"))}


@timed
def nearest(author, limit, path=VECTOR_STORE, target=EXACT_STORE):
    stamp = target / "manifest.json"
    if not stamp.exists():
        raise RuntimeError(f"Exact search data {target} is missing; run python -m author_encoder exact")
    stored = loaded(target, stamp.stat().st_mtime_ns)
    if stored["manifest"] != manifest(path):
        raise RuntimeError(f"Exact search data {target} was built for another version of {path}; run python -m author_encoder exact")
    found = vector(author, path)
    if found is None:
        return None
    query = normalised([found["vector"]])[0]
    single = query.astype(np.float32)
    rows = stored["manifest"]["rows"]
    approximate = np.empty(rows, dtype=np.float64)

    def score(start):
        stop = min(start + EXACT_CHUNK, rows)
        approximate[start:stop] = (stored["codes"][start:stop].astype(np.float32) @ single).astype(np.float64) * stored["scales"][start:stop]

    with ThreadPoolExecutor(EXACT_THREADS) as pool:
        list(pool.map(score, range(0, rows, EXACT_CHUNK)))
    kept = min(limit + 1, rows)
    lower = approximate - stored["slack"]
    floor = np.partition(lower, rows - kept)[rows - kept]
    candidates = np.flatnonzero(approximate + stored["slack"] >= floor)
    table = users(path).take(candidates.tolist(), columns=["author", "usable_texts", "vector"])
    scores = normalised(table.column("vector").combine_chunks().flatten().to_numpy(zero_copy_only=False).reshape(-1, DIMENSIONS)) @ query
    ranked = sorted(zip(table.column("author").to_pylist(), table.column("usable_texts").to_pylist(), scores.tolist()), key=lambda row: (-row[2], row[0]))
    LOG.info("exact neighbours author=%s candidates=%d", author, len(candidates))
    return [{"author": name, "similarity": similarity, "usable_texts": usable} for name, usable, similarity in ranked if name != author][:limit]
