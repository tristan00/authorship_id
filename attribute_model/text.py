import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download

from author_encoder import clean
from author_encoder.config import LUAR, MAX_LENGTH, TOKEN_BUDGET
from author_encoder.model import load_model as load_encoder
from author_encoder.tokens import load_tokenizer
from database import LOGS, host, selected
from . import LOG, timed, write_json
from .config import TEXT_ENCODE
from .predict import BINARY, load_model, predict

SHARED = ("labels.npy", "splits.npy", "authors.json", "parents.json")
SPREAD_ROWS = 1 << 20


@timed
def encoded(staging, source, authors, train, path):
    model = load_encoder("cuda")
    features = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(authors, model.transformer.config.hidden_size))
    start, end = train
    step = max(1, (end - start) // SPREAD_ROWS)
    sample = np.empty((len(range(start, end, step)), features.shape[1]), dtype=np.float16)

    def keep(rows, found):
        features[rows] = found
        picked = (rows >= start) & (rows < end) & ((rows - start) % step == 0)
        sample[(rows[picked] - start) // step] = found[picked]
    tokenizer = hf_hub_download(LUAR[0], "tokenizer.json", revision=LUAR[1], local_files_only=True)
    command = [str(BINARY), "texts", "--source", str(source), "--out", str(staging), "--tokenizer", tokenizer, "--max-length", str(MAX_LENGTH), "--chunk", str(TEXT_ENCODE), "--budget", str(TOKEN_BUDGET), "--host", host(), "--database", selected()]
    texts = tokens = truncated = 0
    with open(LOGS / "attribute_texts.log", "a", encoding="utf-8") as log, ThreadPoolExecutor(1) as writer:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=log)
        written = writer.submit(int)
        try:
            for line in process.stdout:
                parts = [staging / f"{line.split()[0].decode()}.{part}.npy" for part in ("rows", "order", "tokens", "shapes")]
                rows, order, flat, shapes = (np.load(part) for part in parts)
                for part in parts:
                    part.unlink()
                started = time.perf_counter()
                found = model.features((order, flat, shapes.tolist()), len(rows)).cpu().numpy()
                encoding = time.perf_counter() - started
                written.result()
                written = writer.submit(keep, rows, found)
                texts, tokens, truncated = texts + len(rows), tokens + len(flat), truncated + int(shapes[shapes[:, 1] >= MAX_LENGTH, 0].sum())
                LOG.info("text features encoded=%d of %d encode_seconds=%.1f write_wait_seconds=%.1f", texts, authors, encoding, time.perf_counter() - started - encoding)
            written.result()
        except BaseException:
            process.kill()
            raise
        if process.wait():
            raise RuntimeError(f"attribute_io texts exited with {process.returncode}")
    if texts != authors:
        raise ValueError(f"Encoded {texts} texts for {authors} labeled authors")
    features.flush()
    return sample, {"tokens": tokens, "truncated": truncated}


@timed
def spread(sample):
    sample = sample.astype(np.float32)
    return {"dimensions": sample.shape[1], "center": sample.mean(0).tolist(), "spread": np.maximum(sample.std(0), 1e-4).tolist()}


@timed
def prepare_text(directory, source):
    directory, source = Path(directory), Path(source)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    sample, texts = encoded(staging, source, manifest["authors"], manifest["splits"]["train"], staging / "users.npy")
    for name in SHARED:
        os.link(source / name, staging / name)
    shutil.copytree(source / "sets", staging / "sets", copy_function=os.link)
    manifest["features"] = spread(sample)
    manifest["texts"] = texts
    write_json(staging / "manifest.json", manifest)
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"texts": manifest["authors"], "directory": str(directory), "tokens": texts}


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
