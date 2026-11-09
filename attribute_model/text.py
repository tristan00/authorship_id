import json
import os
import shutil
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download

from author_encoder import clean
from author_encoder.config import LUAR, MAX_LENGTH, TOKEN_BUDGET
from author_encoder.model import load_model as load_encoder
from author_encoder.tokens import load_tokenizer
from . import LOG, timed, write_json
from .config import DATA, SPLITS, TEXT_DATA, TEXT_ENCODE
from .predict import load_model, predict

SHARED = ("labels.npy", "splits.npy", "authors.json")
SPREAD_ROWS = 1 << 20


def batched(lengths, flat):
    order = np.argsort(lengths, kind="stable")
    ordered = lengths[order]
    starts = np.cumsum(lengths) - lengths
    tokens = flat[np.arange(int(ordered.sum())) + np.repeat(starts[order] - (np.cumsum(ordered) - ordered), ordered)]
    shapes = []
    for length, size in zip(*np.unique(ordered, return_counts=True)):
        step = max(1, TOKEN_BUDGET // int(length))
        shapes.extend((min(step, int(size) - start), int(length)) for start in range(0, int(size), step))
    return order.astype(np.int32), tokens, shapes


@timed
def tokenized(staging, source):
    from pipeline.run import rust
    tokenizer = hf_hub_download(LUAR[0], "tokenizer.json", revision=LUAR[1], local_files_only=True)
    rust("attribute_model/io", "attribute_io", "texts", "attribute_texts.log", "--authors", str(source / "authors.json"), "--out", str(staging), "--tokenizer", tokenizer, "--max-length", str(MAX_LENGTH))
    lengths = np.load(staging / "lengths.npy").astype(np.int64)
    flat = np.fromfile(staging / "tokens.bin", dtype=np.int32)
    if lengths.sum() != len(flat):
        raise ValueError("Text token lengths do not cover the token file")
    return lengths, flat


@timed
def encoded(lengths, flat, path):
    model = load_encoder("cuda")
    features = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(len(lengths), model.transformer.config.hidden_size))
    starts = np.cumsum(lengths) - lengths
    for start in range(0, len(lengths), TEXT_ENCODE):
        counts = lengths[start:start + TEXT_ENCODE]
        found = model.features(batched(counts, flat[starts[start]:starts[start] + counts.sum()]), len(counts))
        features[start:start + len(counts)] = found.cpu().numpy()
        LOG.info("text features encoded=%d of %d", start + len(counts), len(lengths))
    features.flush()
    return features


@timed
def prepare_text(directory=TEXT_DATA, source=DATA):
    directory, source = Path(directory), Path(source)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    lengths, flat = tokenized(staging, source)
    features = encoded(lengths, flat, staging / "users.npy")
    (staging / "lengths.npy").unlink()
    (staging / "tokens.bin").unlink()
    for name in SHARED:
        os.link(source / name, staging / name)
    shutil.copytree(source / "sets", staging / "sets", copy_function=os.link)
    splits = np.load(source / "splits.npy")
    training = np.flatnonzero(np.isin(splits, SPLITS["train"]))
    sample = np.asarray(features[training[::max(1, len(training) // SPREAD_ROWS)]], dtype=np.float32)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    manifest["features"] = {"dimensions": features.shape[1], "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}
    manifest["texts"] = {"tokens": int(lengths.sum()), "truncated": int((lengths >= MAX_LENGTH).sum())}
    write_json(staging / "manifest.json", manifest)
    del features
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"texts": len(lengths), "directory": str(directory), "tokens": manifest["texts"]}


@lru_cache(maxsize=1)
def encoder():
    return load_encoder("cpu"), load_tokenizer()


@timed
def predict_text(model_path, text):
    cleaned = clean(text)
    if not cleaned:
        raise ValueError("The text is empty after cleaning")
    model, tokenizer = encoder()
    ids = tokenizer.encode(cleaned).ids
    with torch.inference_mode():
        features = model.pooled(torch.tensor([ids])).half().numpy()
    return {"attributes": predict(load_model(model_path), features)[0], "tokens": len(ids), "truncated": len(ids) >= MAX_LENGTH}
