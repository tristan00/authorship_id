import json
import mmap
import os
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
import torch
import torch.nn.functional as F
from clickhouse_connect.driver.binding import format_str, quote_identifier

from database import author_ranges, client, host, selected

from . import LOG, timed
from .config import DIMENSIONS, GPU_MEMORY, INSERT_ROWS, PREDICTION_BATCH, SPLITS, THREADS, VECTOR_RANGES, data
from .evaluate import chosen
from .model import AttributeModel, numeric

KIND = {"numeric": "Float32", "categorical": "LowCardinality(String)", "embedding": "LowCardinality(String)", "set": "Array(LowCardinality(String))"}
BINARY = Path(__file__).resolve().parent / "io" / "target" / "release" / "attribute_io.exe"
SLOTS = 6
FETCHERS = 2
ENCODERS = 4
INSERTERS = 2


def schema(artifact):
    targets = {name: artifact["targets"][name] for name in artifact["published"]}
    columns = "".join(f", {quote_identifier(name)} {KIND[kind]}" for name, kind in targets.items())
    comment = json.dumps({"model_id": artifact["model_id"], "source": artifact["source"], "targets": targets, "not_predictive": artifact["not_predictive"]})
    return f"CREATE TABLE author_predictions_next (author String{columns}) ENGINE = MergeTree ORDER BY author COMMENT {format_str(comment)}"


def build(artifact):
    model = AttributeModel(artifact["targets"], artifact["specifications"], **artifact["architecture"])
    model.load_state_dict(artifact["model"], strict=True)
    return model.eval().requires_grad_(False)


@lru_cache(maxsize=1)
def cached(path, modified):
    torch.set_num_threads(THREADS)
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    return build(artifact), artifact


def load_model(path):
    path = Path(path).resolve()
    return cached(str(path), path.stat().st_mtime_ns)


def decided(artifact, outputs):
    for spec, fitted, output in zip(artifact["specifications"], artifact["calibration"], outputs):
        if spec["name"] not in artifact["published"]:
            continue
        if spec["type"] == "numeric":
            yield spec, numeric(output, spec)
        elif spec["type"] == "set":
            yield spec, chosen(output.float().sigmoid(), fitted["threshold"])
        else:
            yield spec, output.argmax(1)


def named(spec, decision):
    if spec["type"] == "set":
        return [[spec["values"][index] for index in row.nonzero().flatten().tolist()] for row in decision.cpu()]
    return [spec["values"][index] for index in decision.tolist()]


@timed
def predict(loaded, vectors):
    model, artifact = loaded
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != model.input.in_features or not np.isfinite(values).all():
        raise ValueError(f"Expected finite {model.input.in_features}-dimensional inputs")
    result = [{} for _ in values]
    with torch.inference_mode():
        for start in range(0, len(values), 1024):
            for spec, decision in decided(artifact, model.outputs(model(torch.from_numpy(values[start:start + 1024])))):
                for row, value in enumerate(decision.tolist() if spec["type"] == "numeric" else named(spec, decision), start):
                    result[row][spec["name"]] = {"value": value}
    return result


def kind(spec):
    return spec["type"] if spec["type"] in ("numeric", "set") else "categorical"


def stacked(items, rows, device):
    return torch.stack(items, 1) if items else torch.empty(rows, 0, device=device)


@torch.inference_mode()
def decide(model, artifact, columns, vectors, device):
    decisions = {spec["name"]: decision for spec, decision in decided(artifact, model.outputs(model(vectors.to(device))))}
    numeric = stacked([decisions[spec["name"]] for spec in columns if kind(spec) == "numeric"], len(vectors), device)
    categorical = stacked([decisions[spec["name"]] for spec in columns if kind(spec) == "categorical"], len(vectors), device).int()
    sets = torch.cat([F.pad(decisions[spec["name"]], (0, -len(spec["values"]) % 64)) for spec in columns if kind(spec) == "set"] or [torch.empty(len(vectors), 0, dtype=torch.bool, device=device)], 1)
    packed = (sets.view(len(vectors), -1, 8).to(torch.uint8) << torch.arange(8, dtype=torch.uint8, device=device)).sum(2, dtype=torch.uint8)
    return numeric, categorical, packed


def slot_views(shared, sizes):
    memory = torch.frombuffer(shared, dtype=torch.uint8)
    slot_bytes, offsets = sum(sizes), np.cumsum([0, *sizes])
    return [[memory[slot * slot_bytes + offsets[index]:slot * slot_bytes + offsets[index + 1]].view(dtype).view(PREDICTION_BATCH, -1) for index, dtype in enumerate((torch.float32, torch.float32, torch.int32, torch.uint8))] for slot in range(SLOTS)]


@timed
def stream(model, artifact, ranges, table, total, device):
    columns = [next(spec for spec in artifact["specifications"] if spec["name"] == name) for name in artifact["published"]]
    kinds = [kind(spec) for spec in columns]
    words = sum(-(-len(spec["values"]) // 64) for spec in columns if kind(spec) == "set")
    sizes = [PREDICTION_BATCH * width for width in (DIMENSIONS * 4, kinds.count("numeric") * 4, kinds.count("categorical") * 4, words * 8)]
    name = f"attribute_predict_{os.getpid()}"
    shared = mmap.mmap(-1, SLOTS * sum(sizes), tagname=name)
    views = slot_views(shared, sizes)
    layout = {"shared": name, "table": table, "batch": PREDICTION_BATCH, "slots": SLOTS, "fetchers": FETCHERS, "encoders": ENCODERS, "inserters": INSERTERS, "insert_rows": INSERT_ROWS,
              "dimensions": DIMENSIONS, "slot_bytes": sum(sizes), "ranges": ranges, "columns": [{"name": spec["name"], "type": kind(spec), "values": spec.get("values", [])} for spec in columns]}
    users, logged, started = 0, 0, time.perf_counter()
    with TemporaryDirectory() as directory:
        path = Path(directory) / "layout.json"
        path.write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")
        process = subprocess.Popen([str(BINARY), "predict", str(path), "--host", host(), "--database", selected()], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for line in process.stdout:
                if line == b"end\n":
                    break
                slot, rows = map(int, line.split())
                for target, source in zip(views[slot][1:], decide(model, artifact, columns, views[slot][0][:rows], device)):
                    target[:rows].copy_(source)
                process.stdin.write(b"%d\n" % slot)
                process.stdin.flush()
                users += rows
                if users - logged >= INSERT_ROWS:
                    logged, elapsed = users, time.perf_counter() - started
                    LOG.info("attribute predictions users=%d of %d rate=%.0f/s eta=%.0fs", users, total, users / elapsed, (total - users) * elapsed / users)
            process.stdin.close()
            code = process.wait()
        except BaseException:
            process.kill()
            raise
    del views
    shared.close()
    if code:
        raise RuntimeError(f"attribute_io predict exited with {code}")
    return users


@timed
def predict_table(model_path, device="cuda"):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    splits = np.load(data() / "splits.npy", mmap_mode="r")
    prepared = {name: int(np.isin(splits, buckets).sum()) for name, buckets in SPLITS.items()}
    if artifact["authors"] != prepared:
        raise ValueError(f"{model_path} was trained on other prepared data ({artifact['authors']}) than {data()} ({prepared})")
    model = build(artifact).to(device)
    db = client()
    db.command("DROP TABLE IF EXISTS author_predictions_next")
    db.command(schema(artifact))
    total = db.command("SELECT count() FROM author_vectors")
    if not total:
        raise ValueError("No author vectors to predict")
    users = stream(model, artifact, author_ranges(db, "author_vectors", VECTOR_RANGES), "author_predictions_next", total, device)
    if users != total:
        raise ValueError("Author vectors changed while predictions were written")
    db.command("CREATE TABLE IF NOT EXISTS author_predictions AS author_predictions_next")
    db.command("EXCHANGE TABLES author_predictions_next AND author_predictions")
    db.command("DROP TABLE author_predictions_next")
    return {"model_id": artifact["model_id"], "users": users, "columns": len(artifact["published"]) + 1}


@timed
def predict_file(model_path, input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    if output_path.exists():
        raise FileExistsError(output_path)
    loaded = load_model(model_path)
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
def predict_user(model_path, author):
    found = client().query("SELECT texts, vector FROM author_vectors WHERE author = {author:String}", parameters={"author": author}).result_rows
    if not found:
        raise ValueError(f"No author vector for {author}")
    texts, vector = found[0]
    return {"author": author, "texts": texts, "attributes": predict(load_model(model_path), [vector])[0]}
