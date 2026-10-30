import json
import math
import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import torch
from torch.nn import functional as F

from . import LOG, timed
from .config import PARAMETERS, SEED, SPLITS, validate
from .data import load
from .model import AttributeModel, numeric, specifications

DEVICE = "cuda"


def collect(model, vectors, labels, batch=32768):
    model.eval()
    parts = []
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(vectors), batch):
            target = labels[start:start + batch]
            present = torch.isfinite(target)
            parts.append([(output[present[:, column]].float(), target[present[:, column], column]) for column, output in enumerate(model.outputs(model(vectors[start:start + batch].float())))])
    return [(torch.cat([output for output, _ in column]), torch.cat([target for _, target in column])) for column in zip(*parts)]


def score(model, vectors, labels, specs, batch=32768):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(vectors), batch):
            batch_sums, batch_counts, _ = model.terms(model(vectors[start:start + batch].float()), labels[start:start + batch])
            sums, counts = sums + batch_sums, counts + batch_counts
    ratios = (sums / counts / model.baseline).tolist()
    return float(np.mean(ratios)), dict(zip((spec["name"] for spec in specs), ratios))


def temperature(logits, target):
    logits = logits.clone()
    log_t = torch.zeros(1, device=logits.device, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), target)
        loss.backward()
        return loss
    optimizer.step(closure)
    return float(log_t.detach().exp())


@timed
def calibrate(model, vectors, labels, specs, mass):
    result = []
    for (output, target), spec in zip(collect(model, vectors, labels), specs):
        if spec["type"] == "numeric":
            _, lower, upper = numeric(output, spec)
            residuals = torch.sort(torch.maximum(lower - target, target - upper)).values.cpu().numpy()
            rank = math.ceil((len(residuals) + 1) * mass)
            if rank > len(residuals):
                raise ValueError(f"{spec['name']}: too few calibration labels for a {mass:.0%} interval")
            result.append({"n": len(residuals), "mass": mass, "radius": float(residuals[rank - 1])})
        else:
            result.append({"n": len(target), "temperature": temperature(output, target.long())})
    return result


def expected_calibration(confidence, correct, bins=15):
    edges = np.linspace(0, 1, bins + 1)[1:-1]
    which = np.digitize(confidence, edges)
    return float(sum(abs(confidence[which == b].mean() - correct[which == b].mean()) * np.mean(which == b) for b in np.unique(which)))


@timed
def report(model, vectors, labels, specs, calibration):
    result = {}
    for (output, target), spec, fitted in zip(collect(model, vectors, labels), specs, calibration):
        if spec["type"] == "numeric":
            predicted, lower, upper = numeric(output, spec)
            lower, upper = lower - fitted["radius"], upper + fitted["radius"]
            error = (predicted - target).cpu().numpy()
            base = (target - spec["center"]).abs().mean()
            result[spec["name"]] = {"n": len(error), "mae": float(np.abs(error).mean()), "median_baseline_mae": float(base), "rmse": float(np.sqrt(np.mean(error ** 2))),
                                    "interval_coverage": float(((target >= lower) & (target <= upper)).float().mean()), "interval_width": float((upper - lower).mean()),
                                    "interval_width_median": float((upper - lower).median())}
        else:
            target = target.long()
            probabilities = (output / fitted["temperature"]).softmax(1)
            confidence, predicted = probabilities.max(1)
            correct = (predicted == target).cpu().numpy()
            counts = np.bincount(target.cpu().numpy(), minlength=len(spec["values"]))
            wins = np.bincount(target.cpu().numpy(), weights=correct, minlength=len(spec["values"]))
            prior = torch.as_tensor(spec["prior"], device=DEVICE)
            result[spec["name"]] = {"n": len(correct), "accuracy": float(correct.mean()), "majority_baseline_accuracy": float((target == int(np.argmax(spec["counts"]))).float().mean()),
                                    "top5_accuracy": float((probabilities.topk(min(5, probabilities.shape[1]), 1).indices == target[:, None]).any(1).float().mean()),
                                    "macro_recall": float(np.mean(wins[counts > 0] / counts[counts > 0])),
                                    "log_loss": float(F.nll_loss(probabilities.clamp_min(1e-12).log(), target)), "prior_log_loss": float(-prior[target].log().mean()),
                                    "calibration_error": expected_calibration(confidence.cpu().numpy(), correct)}
    return result


def gpu(arrays, selected):
    vectors = torch.empty((len(selected), arrays["users"].shape[1]), dtype=torch.float16, device=DEVICE)
    for start in range(0, len(selected), 1 << 20):
        vectors[start:start + (1 << 20)] = torch.from_numpy(np.asarray(arrays["users"][selected[start:start + (1 << 20)]]))
    return vectors, torch.as_tensor(np.asarray(arrays["labels"][selected]), dtype=torch.float32, device=DEVICE)


@timed
def load_data(directory, targets):
    manifest, arrays = load(directory, targets)
    splits = np.asarray(arrays["splits"])
    selected = {name: np.flatnonzero(np.isin(splits, buckets)) for name, buckets in SPLITS.items()}
    specs = specifications(targets, manifest["catalogs"], arrays["labels"], selected["train"])
    for name in ("validation", "calibration", "test"):
        counts = np.isfinite(np.asarray(arrays["labels"][selected[name]])).sum(0)
        if (counts < 100).any():
            raise ValueError(f"Fewer than 100 {name} labels for {', '.join(spec['name'] for spec, count in zip(specs, counts) if count < 100)}")
    LOG.info("attribute model authors=%s", {name: len(indices) for name, indices in selected.items()})
    return manifest, specs, {name: gpu(arrays, indices) for name, indices in selected.items()}


def capacities(model, specs, rows, batch):
    rates = [specs[index]["training_labels"] / rows for index in model.embedding]
    return [min(batch, 64 * math.ceil((rate * batch + 8 * math.sqrt(rate * (1 - rate) * batch)) / 64)) for rate in rates]


@timed
def fit(model, specs, data, parameters):
    vectors, labels = data["train"]
    batch = parameters["batch"]
    batches = len(labels) // batch
    steps = batches * parameters["epochs"]
    warmup = max(1, round(.03 * steps))
    capacity = capacities(model, specs, len(labels), batch)
    rate = torch.tensor(parameters["lr"], device=DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=rate, weight_decay=parameters["weight_decay"], fused=True, capturable=True)
    index = torch.zeros(batch, dtype=torch.long, device=DEVICE)
    generator = torch.Generator(device=DEVICE).manual_seed(SEED)

    def schedule(number):
        return parameters["lr"] * min(1, (number + 1) / warmup) * .5 * (1 + math.cos(math.pi * min(1, number / steps)))

    def step():
        with torch.autocast(DEVICE, dtype=torch.bfloat16, cache_enabled=False):
            loss, overflow = model.loss(model(vectors[index].float()), labels[index], capacity)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1., foreach=True)
        optimizer.step()
        return loss.detach(), overflow

    order = torch.randperm(len(labels), device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
    model.train()
    side = torch.cuda.Stream()
    side.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(side):
        for number in range(3):
            index.copy_(order[number])
            rate.fill_(schedule(number))
            optimizer.zero_grad(set_to_none=True)
            step()
    torch.cuda.current_stream().wait_stream(side)
    graph = torch.cuda.CUDAGraph()
    optimizer.zero_grad(set_to_none=True)
    with torch.cuda.graph(graph):
        loss, overflow = step()
    best, saved, history, number, started = math.inf, None, [], 3, time.perf_counter()
    for epoch in range(parameters["epochs"]):
        if epoch:
            order = torch.randperm(len(labels), device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
        model.train()
        total = torch.zeros((), device=DEVICE)
        dropped = torch.zeros((), dtype=torch.long, device=DEVICE)
        for selected in order[3 if epoch == 0 else 0:]:
            index.copy_(selected)
            rate.fill_(schedule(number))
            graph.replay()
            total += loss
            dropped += overflow
            number += 1
        if not torch.isfinite(total) or dropped:
            raise FloatingPointError(f"Nonfinite attribute-model loss or {int(dropped)} labeled rows beyond the embedding-head capacity {capacity}")
        trained = time.perf_counter() - started
        validation, fields = score(model, *data["validation"], specs)
        history.append({"epoch": epoch + 1, "training_loss": float(total) / (batches - (3 if epoch == 0 else 0)), "validation_score": validation, "fields": fields})
        LOG.info("attribute model epoch=%d loss=%.5f validation=%.5f train_seconds=%.1f seconds=%.1f", epoch + 1, history[-1]["training_loss"], validation, trained, time.perf_counter() - started)
        if validation < best:
            best, saved = validation, {name: value.detach().clone() for name, value in model.state_dict().items()}
    del graph
    model.load_state_dict(saved)
    return best, history


@timed
def train(directory, output, targets, parameters=PARAMETERS):
    targets = validate(targets)
    output = Path(output)
    torch.manual_seed(SEED)
    manifest, specs, data = load_data(directory, targets)
    architecture = {key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}
    model = AttributeModel(targets, specs, **architecture).to(DEVICE)
    best, history = fit(model, specs, data, parameters)
    calibration = calibrate(model, *data["calibration"], specs, parameters["interval_mass"])
    evaluation = report(model, *data["test"], specs, calibration)
    for name, fields in evaluation.items():
        LOG.info("attribute model test %s %s", name, json.dumps(fields))
    model_id = str(uuid.uuid4())
    artifact = {"model_id": model_id, "targets": targets, "specifications": specs, "architecture": architecture, "parameters": parameters, "model": {name: value.cpu() for name, value in model.state_dict().items()},
                "calibration": calibration, "evaluation": evaluation, "history": history, "validation_score": best, "source": manifest["source"],
                "authors": {name: len(labels) for name, (_, labels) in data.items()}, "splits": SPLITS}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, prefix=output.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(artifact, stream)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"model": str(output), "model_id": model_id, "validation_score": best, "evaluation": evaluation}
