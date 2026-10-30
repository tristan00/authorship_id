import json
import queue
import shutil
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

import lance
import numpy as np
import psycopg
import pyarrow as pa
import torch
from psycopg import sql
from psycopg.types.json import Jsonb

from author_encoder.config import DIMENSIONS, VECTOR_STORE
from author_encoder.index import PROTOCOL, vector
from author_encoder.lock import index_lock
from database import DSN

from . import LOG, timed
from .config import ENCODERS, GPU_MEMORY, PREDICTIONS, SEGMENT_BYTES, THREADS, check_targets, columns, validate
from .model import AttributeModel, numeric

SIGNATURE = b"PGCOPY\n\xff\r\n\x00" + bytes(8)
TRAILER = b"\xff\xff"
PUBLISH = """
ALTER TABLE author_predictions_next ADD PRIMARY KEY (author);
DROP TABLE IF EXISTS author_predictions;
ALTER TABLE author_predictions_next RENAME TO author_predictions;
ALTER INDEX author_predictions_next_pkey RENAME TO author_predictions_pkey;
ANALYZE author_predictions;
DROP TABLE IF EXISTS prediction;
CREATE TABLE prediction (model_id uuid PRIMARY KEY, source jsonb NOT NULL, targets jsonb NOT NULL, interval_mass real NOT NULL, users bigint NOT NULL, finished_at timestamptz NOT NULL DEFAULT clock_timestamp());
"""


def schema(targets):
    result = [("author", "text")]
    for name, kind in targets.items():
        result += zip(columns(name, kind), ("real",) * 3 if kind == "numeric" else ("text", "real"))
    return result


def build(artifact):
    model = AttributeModel(artifact["targets"], artifact["specifications"], **artifact["architecture"])
    model.load_state_dict(artifact["model"], strict=True)
    return model.eval().requires_grad_(False)


@lru_cache(maxsize=1)
def cached(path, modified, configured):
    torch.set_num_threads(THREADS)
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    check_targets(dict(configured), artifact["targets"])
    return build(artifact), artifact


def load_model(path, targets):
    path = Path(path).resolve()
    return cached(str(path), path.stat().st_mtime_ns, tuple(validate(targets).items()))


def calibrated(artifact, outputs):
    for spec, fitted, output in zip(artifact["specifications"], artifact["calibration"], outputs):
        if spec["type"] == "numeric":
            value, lower, upper = numeric(output, spec)
            yield spec, fitted, (value, lower - fitted["radius"], upper + fitted["radius"])
        else:
            yield spec, fitted, (output / fitted["temperature"]).softmax(1)


@timed
def predict(loaded, vectors, candidates=5):
    model, artifact = loaded
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != DIMENSIONS or not np.isfinite(values).all():
        raise ValueError(f"Expected finite {DIMENSIONS}-dimensional user vectors")
    result = [{} for _ in values]
    with torch.inference_mode():
        for start in range(0, len(values), 1024):
            for spec, fitted, scored in calibrated(artifact, model.outputs(model(torch.from_numpy(values[start:start + 1024])))):
                name = spec["name"]
                if spec["type"] == "numeric":
                    for row, (value, lower, upper) in enumerate(zip(*(column.tolist() for column in scored)), start):
                        result[row][name] = {"type": "numeric", "value": value, "lower": lower, "upper": upper, "interval_mass": fitted["mass"]}
                else:
                    probabilities, indices = scored.topk(min(candidates, scored.shape[1]), 1)
                    for row, (labels, scores) in enumerate(zip(indices.tolist(), probabilities.tolist()), start):
                        options = [{"value": spec["values"][label], "probability": probability} for label, probability in zip(labels, scores)]
                        result[row][name] = {"type": spec["type"], "value": options[0]["value"], "probability": options[0]["probability"], "candidates": options}
    return result


@torch.inference_mode()
def infer(model, artifact, catalogs, chunk, device):
    vectors = torch.from_numpy(chunk["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS).copy()).to(device)
    numbers, indices = [], []
    for spec, _, scored in calibrated(artifact, model.outputs(model(vectors))):
        if spec["type"] == "numeric":
            numbers += scored
        else:
            probability, index = scored.max(1)
            numbers.append(probability)
            indices.append(index)
    numbers, indices = torch.stack(numbers, 1).cpu().numpy(), torch.stack(indices, 1).cpu().numpy()
    result, number, category = [chunk["author"]], 0, 0
    for spec in artifact["specifications"]:
        if spec["type"] == "numeric":
            result += [numbers[:, number + offset] for offset in range(3)]
            number += 3
        else:
            result += [catalogs[spec["name"]].take(indices[:, category]), numbers[:, number]]
            number, category = number + 1, category + 1
    return result


def binary(columns):
    rows = len(columns[0])
    lengths = np.full((rows, len(columns)), 4, dtype=np.int64)
    texts = {}
    for index, column in enumerate(columns):
        if not isinstance(column, np.ndarray):
            offsets = np.frombuffer(column.buffers()[1], dtype=np.int64 if pa.types.is_large_string(column.type) else np.int32)[column.offset:column.offset + rows + 1].astype(np.int64)
            texts[index] = offsets, np.frombuffer(column.buffers()[2], dtype=np.uint8)
            lengths[:, index] = np.diff(offsets)
    sizes = lengths + 4
    ends = np.cumsum(sizes.sum(1) + 2)
    starts = ends - sizes.sum(1) - 2
    fields = starts[:, None] + 2 + np.cumsum(sizes, 1) - sizes
    out = np.empty(int(ends[-1]), dtype=np.uint8)
    out[starts[:, None] + np.arange(2)] = np.full(rows, len(columns), dtype=">u2").view(np.uint8).reshape(rows, 2)
    out[fields[..., None] + np.arange(4)] = lengths.astype(">u4").view(np.uint8).reshape(rows, len(columns), 4)
    numbers = [index for index, column in enumerate(columns) if isinstance(column, np.ndarray)]
    out[fields[:, numbers, None] + 4 + np.arange(4)] = np.stack([columns[index] for index in numbers], 1).astype(">f4").view(np.uint8).reshape(rows, len(numbers), 4)
    for index, (offsets, data) in texts.items():
        out[np.arange(offsets[0], offsets[-1]) + np.repeat(fields[:, index] + 4 - offsets[:-1], lengths[:, index])] = data[offsets[0]:offsets[-1]]
    return out


def encoded(dataset, model, artifact, device, batch):
    catalogs = {spec["name"]: pa.array(spec["values"]) for spec in artifact["specifications"] if spec["type"] != "numeric"}
    with ThreadPoolExecutor(ENCODERS) as pool:
        pending = deque()
        for chunk in dataset.to_batches(columns=["author", "vector"], batch_size=batch):
            pending.append((chunk.num_rows, pool.submit(binary, infer(model, artifact, catalogs, chunk, device))))
            if len(pending) > 2 * ENCODERS:
                rows, future = pending.popleft()
                yield rows, future.result()
        for rows, future in pending:
            yield rows, future.result()


def finish(stream, segments):
    stream.write(TRAILER)
    stream.close()
    segments.put(Path(stream.name))


def write_segments(rows, total, segments, loader):
    users, number, stream, started = 0, 0, None, time.perf_counter()
    for count, data in rows:
        if loader.done():
            loader.result()
        if stream is None:
            stream = (PREDICTIONS / f"{number:04d}.bin").open("wb")
            stream.write(SIGNATURE)
        stream.write(data)
        users += count
        if stream.tell() >= SEGMENT_BYTES:
            finish(stream, segments)
            stream, number = None, number + 1
            elapsed = time.perf_counter() - started
            LOG.info("attribute predictions written users=%d of %d rate=%.0f/s eta=%.0fs", users, total, users / elapsed, (total - users) * elapsed / users)
    if stream is not None:
        finish(stream, segments)
    return users


def load_segments(fields, artifact, segments):
    with psycopg.connect(DSN) as conn:
        conn.execute(sql.SQL("CREATE TABLE author_predictions_next ({})").format(
            sql.SQL(", ").join(sql.SQL("{} {} NOT NULL").format(sql.Identifier(name), sql.SQL(kind)) for name, kind in fields)))
        while isinstance(item := segments.get(), Path):
            started = time.perf_counter()
            conn.execute(sql.SQL("COPY author_predictions_next FROM {} (FORMAT BINARY, FREEZE)").format(sql.Literal(str(item))))
            item.unlink()
            LOG.info("attribute predictions loaded %s seconds=%.1f", item.name, time.perf_counter() - started)
        if item is None:
            raise RuntimeError("Prediction segments are incomplete; nothing was published")
        started = time.perf_counter()
        conn.execute(PUBLISH)
        conn.execute("INSERT INTO prediction (model_id, source, targets, interval_mass, users) VALUES (%s, %s, %s, %s, %s)",
                     [artifact["model_id"], Jsonb(artifact["source"]), Jsonb(artifact["targets"]), artifact["parameters"]["interval_mass"], item])
        LOG.info("attribute predictions keyed and published users=%d seconds=%.1f", item, time.perf_counter() - started)
    return item


@timed
def predict_table(model_path, targets, device="cuda", batch=32768):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    check_targets(validate(targets), artifact["targets"])
    model = build(artifact).to(device)
    fields = schema(artifact["targets"])
    if PREDICTIONS.exists():
        shutil.rmtree(PREDICTIONS)
    PREDICTIONS.mkdir(parents=True)
    segments = queue.Queue()
    try:
        with ThreadPoolExecutor(1) as pool:
            loader = pool.submit(load_segments, fields, artifact, segments)
            users = None
            try:
                with index_lock(VECTOR_STORE):
                    dataset = lance.dataset(VECTOR_STORE)
                    metadata = dataset.schema.metadata
                    if metadata.get(b"protocol") != PROTOCOL.encode() or json.loads(metadata[b"source"])["months"] != artifact["source"]["months"]:
                        raise ValueError("User vectors do not match the months the model was trained on")
                    users = write_segments(encoded(dataset, model, artifact, device, batch), dataset.count_rows(), segments, loader)
                    del dataset
            finally:
                segments.put(users)
            loader.result()
    finally:
        shutil.rmtree(PREDICTIONS)
    return {"model_id": artifact["model_id"], "users": users, "columns": len(fields)}


@timed
def predict_file(model_path, targets, input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    if output_path.exists():
        raise FileExistsError(output_path)
    loaded = load_model(model_path, targets)
    records = []
    with input_path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                record = json.loads(line)
                if not isinstance(record, dict) or not isinstance(record.get("vector"), list):
                    raise ValueError(f"Line {number} needs a vector array")
                records.append(record)
    if not records:
        raise ValueError("Input contains no vectors")
    predictions = predict(loaded, [record["vector"] for record in records])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, prefix=output_path.name + ".", suffix=".tmp", delete=False) as destination:
            temporary = Path(destination.name)
            for number, (record, attributes) in enumerate(zip(records, predictions), 1):
                destination.write(json.dumps({"id": record.get("id", record.get("author", number)), "attributes": attributes}, ensure_ascii=False) + "\n")
        temporary.rename(output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"predictions": len(records), "output": str(output_path)}


@timed
def predict_user(model_path, targets, author):
    found = vector(author)
    if found is None:
        raise ValueError(f"No user vector for {author}")
    return {"author": author, "sampled_texts": found["sampled_texts"], "attributes": predict(load_model(model_path, targets), [found["vector"]])[0]}
