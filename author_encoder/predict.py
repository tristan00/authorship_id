import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from database import client

from . import LOG, clean, timed
from .config import BATCH_USERS, DIMENSIONS, TEXTS_PER_USER
from .model import load_model
from .store import TABLES, parts, span
from .tokens import load_tokenizer, token_batches


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
    return model.users(model.features(batches, int(lengths.sum())), lengths)


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


@timed
def load_part(reader, tokenizer, low, high):
    where, parameters = span(low, high)
    table = reader.query_arrow(f"SELECT author, text FROM author_texts WHERE {where} ORDER BY author", parameters=parameters)
    authors = table["author"].combine_chunks()
    if not len(authors):
        return authors, np.zeros(0, dtype=np.int64), None
    starts = np.flatnonzero(np.r_[True, pc.not_equal(authors[1:], authors[:-1]).to_numpy(zero_copy_only=False)])
    lengths = np.diff(np.r_[starts, len(authors)])
    return authors.take(pa.array(starts)), lengths, token_batches(tokenizer, table["text"].to_pylist())


@timed
def store_part(writer, part, low, high, authors, lengths, found, seconds):
    where, parameters = span(low, high)
    if writer.command(f"SELECT count() FROM author_vectors WHERE {where}", parameters=parameters):
        writer.command(f"DELETE FROM author_vectors WHERE {where}", parameters=parameters)
    if len(authors):
        values = pa.array(found.astype(np.float32).ravel())
        offsets = pa.array(np.arange(0, len(values) + 1, DIMENSIONS, dtype=np.int32))
        writer.insert_arrow("author_vectors", pa.table({"author": authors.cast(pa.string()), "texts": pa.array(lengths.astype(np.uint16)), "vector": pa.ListArray.from_arrays(offsets, values)}))
    writer.insert("encoded_parts", [(part, low, high, len(authors), int(lengths.sum()), seconds)], column_names=("part", "low", "high", "authors", "texts", "seconds"))


@timed
def encode_store(device="cuda", reset=False):
    db, reader, writer = client(), client(), client()
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
    LOG.info("encode parts=%d done=%d todo=%d", len(ranges), len(done), len(todo))
    model = load_model(device)
    tokenizer = load_tokenizer()
    started, texts, stored = time.perf_counter(), 0, None
    with ThreadPoolExecutor(1) as loader, ThreadPoolExecutor(1) as saver:
        pending = loader.submit(load_part, reader, tokenizer, *ranges[todo[0]]) if todo else None
        for index, part in enumerate(todo, 1):
            tick = time.perf_counter()
            authors, lengths, batches = pending.result()
            if index < len(todo):
                pending = loader.submit(load_part, reader, tokenizer, *ranges[todo[index]])
            found = vectors(model, batches, lengths) if len(authors) else None
            if stored is not None:
                stored.result()
            stored = saver.submit(store_part, writer, part, *ranges[part], authors, lengths, found, time.perf_counter() - tick)
            texts += int(lengths.sum())
            elapsed = time.perf_counter() - started
            LOG.info("progress parts=%d/%d part=%d authors=%d texts=%d texts_per_s=%.0f eta_hours=%.2f", index, len(todo), part, len(authors), texts, texts / elapsed, elapsed / index * (len(todo) - index) / 3600)
        if stored is not None:
            stored.result()
    return {"parts": len(ranges), "encoded": len(todo), "texts": texts}
