import hashlib
import json
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from itertools import islice
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pyarrow as pa
import torch

from database import client

from . import LOG, clean, timed
from .config import BATCH_TEXTS, BATCH_USERS, DIMENSIONS, TEXTS_PER_USER, WORKERS
from .model import load_model
from .store import TABLES, parts, span
from .tokens import load_tokenizer, prepare, start_worker, token_batches


def records(stream):
    authors = set()
    for line_number, line in enumerate(stream, 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict) or not isinstance(record.get("author"), str) or not record["author"].strip():
            raise ValueError(f"Line {line_number}: author must be a nonempty string")
        author = record["author"]
        if author in authors:
            raise ValueError(f"Line {line_number}: duplicate author {author}")
        authors.add(author)
        texts = record.get("texts")
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise ValueError(f"Line {line_number}: texts must be a list of strings")
        usable = [(index, cleaned) for index, text in enumerate(texts) if (cleaned := clean(text))]
        if not usable:
            raise ValueError(f"Line {line_number}: {author} needs at least one usable text")
        selected = sorted(usable, key=lambda item: hashlib.sha256(f"luar-user-vector-256-v1:{author}:{item[0]}:{item[1]}".encode()).digest())[:TEXTS_PER_USER]
        yield {"author": author, "usable_texts": len(usable), "sampled_texts": len(selected), "sample_indices": [index for index, _ in selected], "dimensions": DIMENSIONS}, [text for _, text in selected]


def vectors(model, batches, lengths):
    features = model.features(batches, int(lengths.sum())).float()
    present = np.arange(lengths.max()) < lengths[:, None]
    starts = np.cumsum(lengths) - lengths
    rows = torch.as_tensor(np.where(present, starts[:, None] + np.arange(lengths.max()), 0), device=features.device)
    return model.users(features[rows] * torch.as_tensor(present[:, :, None], device=features.device), lengths)


@timed
def encode_file(source, output, device="cuda"):
    if output.exists():
        raise FileExistsError(output)
    model = load_model(device)
    tokenizer = load_tokenizer()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    count = 0
    try:
        with source.open(encoding="utf-8") as stream, NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, prefix=output.name + ".", suffix=".tmp", delete=False) as target:
            temporary = Path(target.name)
            incoming = records(stream)
            while batch := list(islice(incoming, BATCH_USERS)):
                texts = [text for _, texts in batch for text in texts]
                found = vectors(model, token_batches(tokenizer, texts), np.array([len(texts) for _, texts in batch]))
                for (metadata, _), vector in zip(batch, found, strict=True):
                    target.write(json.dumps(metadata | {"vector": vector.tolist()}) + "\n")
                count += len(batch)
                LOG.info("encoded users=%d output=%s", count, output)
            if not count:
                raise ValueError("Input contains no users")
        temporary.rename(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"users": count, "dimensions": DIMENSIONS, "output": str(output)}


def author_batches(reader, where, parameters):
    batch, count, current = [], 0, None
    with reader.query_row_block_stream(f"SELECT author, text FROM author_texts WHERE {where} ORDER BY author", parameters=parameters) as stream:
        for block in stream:
            for author, text in block:
                if author != current:
                    if count >= BATCH_TEXTS:
                        yield batch
                        batch, count = [], 0
                    current = author
                    batch.append((author, []))
                batch[-1][1].append(text)
                count += 1
    if batch:
        yield batch


@timed
def encode_part(db, reader, pool, model, part, low, high):
    started = time.perf_counter()
    where, parameters = span(low, high)
    if db.command(f"SELECT count() FROM author_vectors WHERE {where}", parameters=parameters):
        db.command(f"DELETE FROM author_vectors WHERE {where}", parameters=parameters)
    authors, lengths, found, pending = [], [], [], deque()

    def finish(future):
        names, counts, batches = future.result()
        if names:
            found.append(vectors(model, batches, counts))
            authors.extend(names)
            lengths.append(counts)

    for batch in author_batches(reader, where, parameters):
        pending.append(pool.submit(prepare, batch))
        if len(pending) > 2 * WORKERS:
            finish(pending.popleft())
    while pending:
        finish(pending.popleft())
    texts = int(sum(counts.sum() for counts in lengths))
    if authors:
        values = np.concatenate(found).astype(np.float32).ravel()
        offsets = pa.array(np.arange(0, len(values) + 1, DIMENSIONS, dtype=np.int32))
        db.insert_arrow("author_vectors", pa.table({"author": pa.array(authors, pa.string()), "texts": pa.array(np.concatenate(lengths).astype(np.uint16)),
                                                    "vector": pa.ListArray.from_arrays(offsets, pa.array(values))}))
    seconds = time.perf_counter() - started
    db.insert("encoded_parts", [(part, low, high, len(authors), texts, seconds)], column_names=("part", "low", "high", "authors", "texts", "seconds"))
    LOG.info("part=%d authors=%d texts=%d seconds=%.1f texts_per_s=%.0f", part, len(authors), texts, seconds, texts / max(seconds, 1e-9))
    return texts


@timed
def encode_store(device="cuda", reset=False):
    db, reader = client(), client()
    if reset:
        db.command("DROP TABLE IF EXISTS author_vectors")
        db.command("DROP TABLE IF EXISTS encoded_parts")
    for statement in TABLES:
        db.command(statement)
    ranges = parts(db)
    done = {part: (low, high) for part, low, high in db.query("SELECT part, low, high FROM encoded_parts").result_rows}
    if any(part >= len(ranges) or ranges[part] != bounds for part, bounds in done.items()):
        raise ValueError("encoded_parts were written with other author ranges; rerun with --reset")
    todo = [part for part in range(len(ranges)) if part not in done]
    LOG.info("encode parts=%d done=%d todo=%d workers=%d", len(ranges), len(done), len(todo), WORKERS)
    model = load_model(device)
    started, texts = time.perf_counter(), 0
    with ProcessPoolExecutor(WORKERS, initializer=start_worker) as pool:
        for index, part in enumerate(todo, 1):
            texts += encode_part(db, reader, pool, model, part, *ranges[part])
            elapsed = time.perf_counter() - started
            LOG.info("progress parts=%d/%d texts=%d texts_per_s=%.0f eta_hours=%.1f", index, len(todo), texts, texts / elapsed, elapsed / index * (len(todo) - index) / 3600)
    return {"parts": len(ranges), "encoded": len(todo), "texts": texts}
