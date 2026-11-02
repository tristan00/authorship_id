import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import lance
import numpy as np
import torch

from author_encoder import clean
from author_encoder.config import MAX_LENGTH, TEXT_STORE
from author_encoder.index import FEATURES, vectors_at
from author_encoder.lock import index_lock
from author_encoder.model import load_model as load_encoder
from author_encoder.texts import MONTHS, quantize, scales
from author_encoder.tokens import load_tokenizer

from . import LOG, timed, write_json
from .config import DATA, ENCODERS, SPLITS, check_targets, validate
from .data import load
from .predict import load_model, predict
from .train import load_splits

ARRAYS = ("codes", "labels", "buckets")
SPREAD_ROWS = 1 << 20


@timed
def fetch(dataset, rows, path):
    codes = np.lib.format.open_memmap(path, mode="w+", dtype=np.int8, shape=(len(rows), FEATURES))
    fragments, starts = np.unique(rows >> np.uint64(32), return_index=True)
    ends, started = np.append(starts[1:], len(rows)), time.perf_counter()

    def read(index):
        codes[starts[index]:ends[index]] = vectors_at(dataset, fragments[index], (rows[starts[index]:ends[index]] & np.uint64(0xFFFFFFFF)).astype(np.int64))

    with ThreadPoolExecutor(ENCODERS) as pool:
        for index, _ in enumerate(pool.map(read, range(len(fragments))), 1):
            if index % 256 == 0:
                elapsed = time.perf_counter() - started
                LOG.info("text features fragments=%d/%d rate=%.0f/s eta=%.0fs", index, len(fragments), ends[index - 1] / elapsed, (len(rows) - ends[index - 1]) * elapsed / ends[index - 1])
    codes.flush()
    return codes


@timed
def prepare(directory, targets):
    targets = validate(targets)
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    manifest, arrays = load(DATA, targets)
    author_buckets = np.asarray(arrays["splits"])
    staging.mkdir(parents=True)
    rows = np.load(DATA / "clean_rows.npy")[np.searchsorted(np.load(DATA / "clean_owners.npy"), np.arange(manifest["authors"]))]
    owners = np.argsort(rows)
    rows = rows[owners]
    with index_lock(TEXT_STORE):
        texts = lance.dataset(TEXT_STORE)
        if json.loads(texts.schema.metadata[MONTHS]) != manifest["source"]["months"]:
            raise ValueError("The prepared labels and text vectors cover different months")
        codes = fetch(texts, rows, staging / "codes.npy")
        scale = scales(texts)
    buckets = author_buckets[owners]
    np.save(staging / "labels.npy", np.asarray(arrays["labels"]).astype(np.float32)[owners])
    np.save(staging / "buckets.npy", buckets)
    training = np.flatnonzero(np.isin(buckets, SPLITS["train"]))
    sample = np.asarray(codes[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    features = {"dimensions": FEATURES, "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist(), "scale": scale.tolist()}
    del codes
    write_json(staging / "manifest.json", {"targets": targets, "catalogs": manifest["catalogs"], "source": manifest["source"], "texts": len(rows), "authors": manifest["authors"], "features": features})
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"texts": len(rows), "authors": manifest["authors"], "directory": str(directory)}


@timed
def load_text(directory, targets):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    check_targets(targets, manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["codes"].shape != (manifest["texts"], FEATURES) or arrays["labels"].shape != (manifest["texts"], len(targets)) or len(arrays["buckets"]) != manifest["texts"]:
        raise ValueError("Prepared text arrays do not match the manifest")
    return (manifest, *load_splits(manifest, targets, arrays["codes"], arrays["labels"], np.asarray(arrays["buckets"])))


@lru_cache(maxsize=1)
def encoder():
    return load_encoder("cpu"), load_tokenizer()


@timed
def predict_text(model_path, targets, text):
    cleaned = clean(text)
    if not cleaned:
        return {"status": "empty"}
    loaded = load_model(model_path, targets)
    model, tokenizer = encoder()
    ids = tokenizer.encode(cleaned).ids
    with torch.inference_mode():
        features = model.pooled(torch.tensor([ids])).numpy()
    artifact = loaded[1]
    codes, _ = quantize(features, np.array(artifact["architecture"]["features"]["scale"], dtype=np.float32))
    return {"status": "ready", "attributes": predict(loaded, codes)[0], "tokens": len(ids), "truncated": len(ids) >= MAX_LENGTH, "months": list(artifact["source"]["months"])}
