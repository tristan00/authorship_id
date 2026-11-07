import json
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pyarrow as pa
import torch
from clickhouse_connect.driver.binding import format_str, quote_identifier

from database import client

from . import LOG, timed
from .config import DIMENSIONS, GPU_MEMORY, INSERT_ROWS, PREDICTION_BATCH, THREADS, check_targets, validate
from .model import AttributeModel, decide, numeric

KIND = {"numeric": "Float32", "categorical": "LowCardinality(String)", "embedding": "LowCardinality(String)"}
VECTORS = "SELECT author, vector FROM author_vectors"


def schema(artifact):
    columns = "".join(f", {quote_identifier(name)} {KIND[kind]}" for name, kind in artifact["targets"].items())
    comment = json.dumps({key: artifact[key] for key in ("model_id", "source", "targets")})
    return f"CREATE TABLE author_predictions_next (author String{columns}) ENGINE = MergeTree ORDER BY author COMMENT {format_str(comment)}"


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


def decided(artifact, outputs):
    for spec, fitted, output in zip(artifact["specifications"], artifact["calibration"], outputs):
        yield spec, numeric(output, spec) if spec["type"] == "numeric" else decide((output / fitted["temperature"]).softmax(1), spec, fitted)


@timed
def predict(loaded, vectors):
    model, artifact = loaded
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != model.input.in_features or not np.isfinite(values).all():
        raise ValueError(f"Expected finite {model.input.in_features}-dimensional inputs")
    result = [{} for _ in values]
    with torch.inference_mode():
        for start in range(0, len(values), 1024):
            for spec, chosen in decided(artifact, model.outputs(model(torch.from_numpy(values[start:start + 1024])))):
                for row, value in enumerate(chosen.tolist(), start):
                    result[row][spec["name"]] = {"value": value if spec["type"] == "numeric" else spec["values"][value]}
    return result


@torch.inference_mode()
def infer(model, artifact, catalogs, batch, device):
    vectors = torch.from_numpy(batch["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS).copy()).to(device)
    columns = {"author": batch["author"]}
    for spec, chosen in decided(artifact, model.outputs(model(vectors))):
        chosen = chosen.cpu().numpy()
        columns[spec["name"]] = pa.array(chosen.astype(np.float32)) if spec["type"] == "numeric" else catalogs[spec["name"]].take(chosen)
    return pa.table(columns)


@timed
def predict_table(model_path, targets, device="cuda"):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    check_targets(validate(targets), artifact["targets"])
    model = build(artifact).to(device)
    catalogs = {spec["name"]: pa.array(spec["values"]) for spec in artifact["specifications"] if spec["type"] != "numeric"}
    reader, writer = client(), client()
    writer.command("DROP TABLE IF EXISTS author_predictions_next")
    writer.command(schema(artifact))
    total = reader.command("SELECT count() FROM author_vectors")
    if not total:
        raise ValueError("No author vectors to predict")
    users, buffered, pending, started = 0, [], None, time.perf_counter()

    def flush():
        nonlocal buffered, pending
        if pending is not None:
            pending.result()
        pending = pool.submit(writer.insert_arrow, "author_predictions_next", pa.concat_tables(buffered))
        buffered = []

    with ThreadPoolExecutor(1) as pool, reader.query_arrow_stream(VECTORS, settings={"max_block_size": PREDICTION_BATCH}) as stream:
        for batch in stream:
            buffered.append(infer(model, artifact, catalogs, batch, device))
            users += batch.num_rows
            if sum(table.num_rows for table in buffered) >= INSERT_ROWS:
                flush()
                elapsed = time.perf_counter() - started
                LOG.info("attribute predictions users=%d of %d rate=%.0f/s eta=%.0fs", users, total, users / elapsed, (total - users) * elapsed / users)
        if buffered:
            flush()
        pending.result()
    if users != total:
        raise ValueError("Author vectors changed while predictions were written")
    writer.command("CREATE TABLE IF NOT EXISTS author_predictions AS author_predictions_next")
    writer.command("EXCHANGE TABLES author_predictions_next AND author_predictions")
    writer.command("DROP TABLE author_predictions_next")
    return {"model_id": artifact["model_id"], "users": users, "columns": len(artifact["targets"]) + 1}


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
                records.append((number, record))
    if not records:
        raise ValueError("Input contains no vectors")
    predictions = predict(loaded, [record["vector"] for _, record in records])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, prefix=output_path.name + ".", suffix=".tmp", delete=False) as destination:
            temporary = Path(destination.name)
            for (number, record), attributes in zip(records, predictions):
                destination.write(json.dumps({"id": record.get("id", record.get("author", number)), "attributes": attributes}, ensure_ascii=False) + "\n")
        temporary.rename(output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"predictions": len(records), "output": str(output_path)}


@timed
def predict_user(model_path, targets, author):
    found = client().query("SELECT texts, vector FROM author_vectors WHERE author = {author:String}", parameters={"author": author}).result_rows
    if not found:
        raise ValueError(f"No author vector for {author}")
    texts, vector = found[0]
    return {"author": author, "texts": texts, "attributes": predict(load_model(model_path, targets), [vector])[0]}
