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
from .config import GPU_MEMORY, PARAMETERS, PUBLISH_MARGIN, SEED, SPLIT_LABELS, SPLITS, TEMPERATURE_ROWS, THRESHOLDS
from .data import load
from .evaluate import DEVICE, chosen, collect, memberships, report, trunk
from .model import AttributeModel, specifications

INPUTS = ("users",)


def gathered(padded, rows):
    return {column: table[slots[rows]] for column, (slots, table) in padded.items()}


def padded_sets(sets, specs, rows, device):
    result = {}
    for column, indptr, values in sets:
        size = len(specs[column]["values"])
        indptr, values = np.asarray(indptr.cpu()), np.asarray(values.cpu())
        lengths = np.diff(indptr)
        stated = np.flatnonzero(lengths)
        slots = np.full(rows, len(stated), dtype=np.int64)
        slots[stated] = np.arange(len(stated))
        width = int(lengths.max())
        table = np.full((len(stated) + 1, width), size, dtype=np.int16 if size < np.iinfo(np.int16).max else np.int32)
        owners = np.repeat(np.arange(len(stated)), lengths[stated])
        table[owners, np.arange(len(values)) - np.repeat(indptr[stated], lengths[stated])] = values
        result[column] = (torch.as_tensor(slots, device=device), torch.as_tensor(table, device=device))
    return result


def score(model, inputs, labels, sets, specs, padded, batch=2048):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(labels), batch):
            rows = torch.arange(start, min(start + batch, len(labels)), device=labels.device)
            target = labels[start:start + batch].to(DEVICE)
            batch_sums, batch_counts, _ = model.terms(model(*(part[start:start + batch].to(DEVICE) for part in inputs)), target, gathered(padded, rows))
            sums, counts = sums + batch_sums, counts + batch_counts
    ratios = (sums / counts / model.baseline).tolist()
    return float(np.mean(ratios)), dict(zip((spec["name"] for spec in specs), ratios))


def temperature(logits, target, batch=16384):
    log_t = torch.zeros(1, device=logits.device, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        total = torch.zeros((), device=logits.device)
        for start in range(0, len(logits), batch):
            loss = F.cross_entropy(logits[start:start + batch].clone() / log_t.exp(), target[start:start + batch], reduction="sum") / len(logits)
            loss.backward()
            total += loss.detach()
        return total
    optimizer.step(closure)
    return float(log_t.detach().exp())


@timed
def categorical(model, hidden, labels, column, spec):
    sample, target = collect(model, hidden, labels, column, TEMPERATURE_ROWS)
    return {"temperature": temperature(sample, target.long())}


@timed
def membership(model, hidden, labels, column, indptr, values):
    pairs = torch.zeros(len(THRESHOLDS), 2, device=DEVICE)
    actual = 0
    for probabilities, truth in memberships(model, hidden, labels, column, indptr, values):
        for slot, threshold in enumerate(THRESHOLDS):
            predicted = chosen(probabilities, threshold)
            pairs[slot] += torch.stack([(predicted & truth).sum(), predicted.sum()])
        actual += int(truth.sum())
    scores = 2 * pairs[:, 0] / (pairs[:, 1] + actual)
    best = int(scores.argmax())
    return {"threshold": THRESHOLDS[best], "f1": float(scores[best])}


@timed
def calibrate(model, inputs, labels, sets, specs):
    lists = {column: (indptr, values) for column, indptr, values in sets}
    hidden = trunk(model, inputs)
    result = []
    for column, spec in enumerate(specs):
        if spec["type"] == "numeric":
            result.append({})
        elif spec["type"] == "set":
            result.append(membership(model, hidden, labels, column, *lists[column]))
        else:
            result.append(categorical(model, hidden, labels, column, spec))
        LOG.info("attribute model calibrated %s %s", spec["name"], json.dumps(result[-1]))
    return result


def placed(arrays, selected, device):
    result = []
    for name in INPUTS:
        source = arrays[name]
        target = torch.empty((len(selected), source.shape[1]), dtype=torch.from_numpy(source[:1].copy()).dtype, device=device)
        for start in range(0, len(selected), 1 << 20):
            target[start:start + (1 << 20)] = torch.from_numpy(np.asarray(source[selected[start:start + (1 << 20)]]))
        result.append(target)
    return tuple(result)


def subset(indptr, values, rows):
    starts, ends = np.asarray(indptr[rows]), np.asarray(indptr[rows + 1])
    lengths = ends - starts
    offsets = np.concatenate([[0], np.cumsum(lengths)])
    return offsets, np.asarray(values[np.repeat(starts - offsets[:-1], lengths) + np.arange(offsets[-1])])


def load_splits(manifest, arrays, sets):
    targets = manifest["targets"]
    splits = np.asarray(arrays["splits"])
    selected = {name: np.flatnonzero(np.isin(splits, buckets)) for name, buckets in SPLITS.items()}
    labeled = {name: np.asarray(arrays["labels"][indices]) for name, indices in selected.items()}
    lists = {split: {name: subset(*sets[name], indices) for name in sets} for split, indices in selected.items()}
    specs = specifications(targets, manifest["catalogs"], labeled["train"], lists["train"])
    for name in ("validation", "calibration", "test"):
        counts = np.isfinite(labeled[name]).sum(0)
        if (counts < SPLIT_LABELS).any():
            raise ValueError(f"Fewer than {SPLIT_LABELS} {name} labels for {', '.join(spec['name'] for spec, count in zip(specs, counts) if count < SPLIT_LABELS)}")
    LOG.info("attribute model rows=%s", {name: len(indices) for name, indices in selected.items()})
    columns = {name: column for column, name in enumerate(targets)}
    data = {}
    for name, indices in selected.items():
        device = DEVICE if name in ("train", "validation") else "cpu"
        members = [(columns[target], torch.as_tensor(indptr, device=device), torch.as_tensor(values, dtype=torch.long, device=device)) for target, (indptr, values) in lists[name].items()]
        data[name] = (placed(arrays, indices, device), torch.as_tensor(labeled[name], dtype=torch.float32, device=device), members)
    return specs, data


@timed
def load_data(directory):
    manifest, arrays, sets = load(directory)
    return (manifest, *load_splits(manifest, arrays, sets))


def capacities(model, specs, rows, batch):
    rates = [specs[index]["training_labels"] / rows for index in model.embedding]
    return [min(batch, 64 * math.ceil((rate * batch + 8 * math.sqrt(rate * (1 - rate) * batch)) / 64)) for rate in rates]


@timed
def fit(model, specs, data, parameters):
    inputs, labels, sets = data["train"]
    padded = {name: padded_sets(data[name][2], specs, len(data[name][1]), DEVICE) for name in ("train", "validation")}
    capacity = capacities(model, specs, len(labels), parameters["batch"])
    return run_epochs(model, len(labels), parameters, lambda index: model.loss(model(*(part[index] for part in inputs)), labels[index], gathered(padded["train"], index), capacity),
                      lambda: score(model, *data["validation"], specs, padded["validation"]))


def run_epochs(model, rows, parameters, loss_of, validate):
    batch = parameters["batch"]
    batches = rows // batch
    steps = batches * parameters["epochs"]
    warmup = max(1, round(.03 * steps))
    rate = torch.tensor(parameters["lr"], device=DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=rate, weight_decay=parameters["weight_decay"], fused=True, capturable=True)
    index = torch.zeros(batch, dtype=torch.long, device=DEVICE)
    generator = torch.Generator(device=DEVICE).manual_seed(SEED)

    def schedule(number):
        return parameters["lr"] * min(1, (number + 1) / warmup) * .5 * (1 + math.cos(math.pi * min(1, number / steps)))

    def step():
        with torch.autocast(DEVICE, dtype=torch.bfloat16, cache_enabled=False):
            loss, overflow = loss_of(index)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1., foreach=True)
        optimizer.step()
        return loss.detach(), overflow

    order = torch.randperm(rows, device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
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
            order = torch.randperm(rows, device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
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
            raise FloatingPointError(f"Nonfinite attribute-model loss or {int(dropped)} labeled rows beyond the head capacity")
        trained = time.perf_counter() - started
        validation, fields = validate()
        history.append({"epoch": epoch + 1, "training_loss": float(total) / (batches - (3 if epoch == 0 else 0)), "validation_score": validation, "fields": fields})
        LOG.info("attribute model epoch=%d loss=%.5f validation=%.5f train_seconds=%.1f seconds=%.1f", epoch + 1, history[-1]["training_loss"], validation, trained, time.perf_counter() - started)
        if validation < best:
            best, saved = validation, {name: value.detach().clone() for name, value in model.state_dict().items()}
    del graph
    model.load_state_dict(saved)
    return best, history


def architecture(parameters, manifest):
    return {**{key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}, "features": manifest["features"]}


@timed
def finish(model, manifest, specs, data, parameters, best, history, output):
    output = Path(output)
    authors = {name: len(split[1]) for name, split in data.items()}
    del data["train"]
    calibration = calibrate(model, *data["calibration"], specs)
    evaluation = report(model, *data["test"], specs, calibration)
    for name, fields in evaluation.items():
        LOG.info("attribute model test %s %s", name, json.dumps(fields))
    published = [name for name, fields in evaluation.items() if fields["improvement"] >= PUBLISH_MARGIN]
    not_predictive = {name: round(fields["improvement"], 4) for name, fields in evaluation.items() if name not in published}
    LOG.info("attribute model published=%d margin=%s not_predictive=%s", len(published), PUBLISH_MARGIN, json.dumps(not_predictive))
    model_id = str(uuid.uuid4())
    artifact = {"model_id": model_id, "targets": manifest["targets"], "specifications": specs, "architecture": architecture(parameters, manifest), "parameters": parameters,
                "model": {name: value.cpu() for name, value in model.state_dict().items()}, "calibration": calibration, "evaluation": evaluation, "published": published, "not_predictive": sorted(not_predictive), "history": history, "validation_score": best,
                "source": manifest["source"], "authors": authors, "splits": SPLITS}
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
    return {"model": str(output), "model_id": model_id, "parameters": parameters, "validation_score": best, "published": published, "not_predictive": not_predictive, "evaluation": evaluation}


@timed
def train(directory, output, parameters=PARAMETERS):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    torch.manual_seed(SEED)
    manifest, specs, data = load_data(directory)
    model = AttributeModel(manifest["targets"], specs, **architecture(parameters, manifest)).to(DEVICE)
    best, history = fit(model, specs, data, parameters)
    return finish(model, manifest, specs, data, parameters, best, history, output)
