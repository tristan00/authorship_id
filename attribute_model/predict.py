import json
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import torch

from author_encoder.config import DIMENSIONS

from . import timed
from .config import THREADS, check_targets, validate
from .model import AttributeModel, numeric


@lru_cache(maxsize=1)
def cached(path, modified, configured):
    torch.set_num_threads(THREADS)
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    check_targets(dict(configured), artifact["targets"])
    model = AttributeModel(artifact["targets"], artifact["specifications"], **artifact["architecture"])
    model.load_state_dict(artifact["model"], strict=True)
    return model.eval().requires_grad_(False), artifact


def load_model(path, targets):
    path = Path(path).resolve()
    return cached(str(path), path.stat().st_mtime_ns, tuple(validate(targets).items()))


@timed
def predict(loaded, vectors, candidates=5):
    model, artifact = loaded
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != DIMENSIONS or not np.isfinite(values).all():
        raise ValueError(f"Expected finite {DIMENSIONS}-dimensional user vectors")
    result = [{} for _ in values]
    with torch.inference_mode():
        for start in range(0, len(values), 1024):
            outputs = model.outputs(model(torch.from_numpy(values[start:start + 1024])))
            for spec, fitted, output in zip(artifact["specifications"], artifact["calibration"], outputs):
                name = spec["name"]
                if spec["type"] == "numeric":
                    points, lower, upper = (column.tolist() for column in numeric(output, spec))
                    for row, (value, low, high) in enumerate(zip(points, lower, upper), start):
                        result[row][name] = {"type": "numeric", "value": value, "lower": low - fitted["radius"], "upper": high + fitted["radius"], "interval_mass": fitted["mass"]}
                else:
                    scores, indices = (output / fitted["temperature"]).softmax(1).topk(min(candidates, output.shape[1]), 1)
                    for row, (labels, probabilities) in enumerate(zip(indices.tolist(), scores.tolist()), start):
                        options = [{"value": spec["values"][label], "probability": probability} for label, probability in zip(labels, probabilities)]
                        result[row][name] = {"type": spec["type"], "value": options[0]["value"], "probability": options[0]["probability"], "candidates": options}
    return result


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
    from author_encoder.index import vector
    found = vector(author)
    if found is None:
        raise ValueError(f"No user vector for {author}")
    return {"author": author, "sampled_texts": found["sampled_texts"], "attributes": predict(load_model(model_path, targets), [found["vector"]])[0]}
