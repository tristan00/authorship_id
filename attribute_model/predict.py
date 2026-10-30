import json
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

import lance
import numpy as np
import psycopg
import pyarrow as pa
import torch
from psycopg import sql
from psycopg.copy import QueuedLibpqWriter
from psycopg.types.json import Jsonb
from pyarrow import csv

from author_encoder.config import DIMENSIONS, VECTOR_STORE
from author_encoder.index import PROTOCOL, vector
from author_encoder.lock import index_lock
from database import DSN

from . import LOG, timed
from .config import THREADS, check_targets, columns, validate
from .model import AttributeModel, numeric

COPY = "COPY author_predictions_next FROM STDIN (FORMAT CSV, FREEZE)"
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


def table_rows(model, artifact, catalogs, names, authors, vectors):
    arrays = [authors]
    for spec, _, scored in calibrated(artifact, model.outputs(model(vectors))):
        if spec["type"] == "numeric":
            arrays += [pa.array(column.cpu().numpy()) for column in scored]
        else:
            probability, index = scored.max(1)
            arrays += [catalogs[spec["name"]].take(index.cpu().numpy()), pa.array(probability.cpu().numpy())]
    sink = pa.BufferOutputStream()
    csv.write_csv(pa.table(arrays, names=names), sink, csv.WriteOptions(include_header=False))
    return sink.getvalue().to_pybytes()


@timed
def predict_table(model_path, targets, device="cuda", batch=32768):
    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    check_targets(validate(targets), artifact["targets"])
    model = build(artifact).to(device)
    catalogs = {spec["name"]: pa.array(spec["values"]) for spec in artifact["specifications"] if spec["type"] != "numeric"}
    fields = schema(artifact["targets"])
    names = [name for name, _ in fields]
    users = 0
    with psycopg.connect(DSN) as conn:
        conn.execute(sql.SQL("CREATE TABLE author_predictions_next ({})").format(
            sql.SQL(", ").join(sql.SQL("{} {} NOT NULL").format(sql.Identifier(name), sql.SQL(kind)) for name, kind in fields)))
        with index_lock(VECTOR_STORE):
            dataset = lance.dataset(VECTOR_STORE)
            metadata = dataset.schema.metadata
            if metadata.get(b"protocol") != PROTOCOL.encode() or json.loads(metadata[b"source"])["months"] != artifact["source"]["months"]:
                raise ValueError("User vectors do not match the months the model was trained on")
            with conn.cursor() as cursor, cursor.copy(COPY, writer=QueuedLibpqWriter(cursor)) as copy, torch.inference_mode():
                for number, chunk in enumerate(dataset.to_batches(columns=["author", "vector"], batch_size=batch), 1):
                    vectors = torch.from_numpy(chunk["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS).copy()).to(device)
                    copy.write(table_rows(model, artifact, catalogs, names, chunk["author"], vectors))
                    users += chunk.num_rows
                    if number % 128 == 0:
                        LOG.info("attribute predictions users=%d", users)
            del dataset
        LOG.info("attribute predictions copied users=%d columns=%d", users, len(names))
        conn.execute(PUBLISH)
        conn.execute("INSERT INTO prediction (model_id, source, targets, interval_mass, users) VALUES (%s, %s, %s, %s, %s)",
                     [artifact["model_id"], Jsonb(artifact["source"]), Jsonb(artifact["targets"]), artifact["parameters"]["interval_mass"], users])
    return {"model_id": artifact["model_id"], "users": users, "columns": len(names)}


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
