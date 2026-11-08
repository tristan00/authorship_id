import json
import math
import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import torch
from torch.nn import functional as F

from claim_extraction.schema import FLAIR_ATTRIBUTES

from . import LOG, timed
from .config import DEFAULTS, GPU_MEMORY, PARAMETERS, SEED, SPLITS, STRICT_SHARE, STRICT_SUPPORT, TEMPERATURE_ROWS, CALIBRATION_ROWS, TRAIN_SUPPORT, validate
from .data import load
from .evaluate import DEVICE, collect, report
from .model import AttributeModel, specifications

INPUTS = ("users", "subreddits", "weights")


def score(model, inputs, labels, specs, batch=2048):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(labels), batch):
            batch_sums, batch_counts, _ = model.terms(model(*(part[start:start + batch].to(DEVICE) for part in inputs)), labels[start:start + batch].to(DEVICE))
            sums, counts = sums + batch_sums, counts + batch_counts
    ratios = (sums / counts / model.baseline).tolist()
    return float(np.mean(ratios)), dict(zip((spec["name"] for spec in specs), ratios))


def fit_calibration(logits, target, biased, batch=16384):
    log_t = torch.zeros(1, device=logits.device, requires_grad=True)
    bias = torch.zeros(logits.shape[1], device=logits.device, requires_grad=biased)
    optimizer = torch.optim.LBFGS([log_t, bias] if biased else [log_t], lr=.1, max_iter=200)

    def closure():
        optimizer.zero_grad()
        total = torch.zeros((), device=logits.device)
        for start in range(0, len(logits), batch):
            loss = F.cross_entropy(logits[start:start + batch].clone() / log_t.exp() + bias, target[start:start + batch], reduction="sum") / len(logits)
            loss.backward()
            total += loss.detach()
        return total
    optimizer.step(closure)
    return {"temperature": float(log_t.detach().exp()), "bias": bias.detach().cpu().tolist()}


@timed
def categorical(model, inputs, labels, column, spec):
    biased = spec["type"] == "categorical"
    sample, target = collect(model, inputs, labels, column, CALIBRATION_ROWS if biased else TEMPERATURE_ROWS)
    return fit_calibration(sample, target.long(), biased)


@timed
def calibrate(model, inputs, labels, specs):
    result = []
    for column, spec in enumerate(specs):
        result.append({} if spec["type"] == "numeric" else categorical(model, inputs, labels, column, spec))
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


def effective(manifest, targets, arrays, selected, training):
    labels = np.asarray(arrays["labels"][selected])
    support, share = (np.asarray(arrays[name][selected], dtype=np.float32) for name in ("support", "share"))
    claimed = np.isfinite(support)
    flair = np.isin(list(targets), list(FLAIR_ATTRIBUTES))
    keep = support >= TRAIN_SUPPORT if training else ((support >= STRICT_SUPPORT) & (share >= STRICT_SHARE)) | flair
    labels[claimed & ~keep] = np.nan
    stated = labels.copy()
    for column, name in enumerate(targets):
        if name in DEFAULTS:
            labels[~claimed[:, column], column] = manifest["catalogs"][name].index(DEFAULTS[name])
    return labels, stated


def load_splits(manifest, targets, arrays):
    splits = np.asarray(arrays["splits"])
    selected = {name: np.flatnonzero(np.isin(splits, buckets)) for name, buckets in SPLITS.items()}
    labeled = {name: effective(manifest, targets, arrays, indices, name == "train") for name, indices in selected.items()}
    specs = specifications(targets, manifest["catalogs"], labeled["train"][0], slice(None))
    for name in ("validation", "calibration", "test"):
        counts = np.isfinite(labeled[name][0]).sum(0)
        if (counts < 100).any():
            raise ValueError(f"Fewer than 100 {name} labels for {', '.join(spec['name'] for spec, count in zip(specs, counts) if count < 100)}")
    LOG.info("attribute model rows=%s", {name: len(indices) for name, indices in selected.items()})
    data = {}
    for name, indices in selected.items():
        device = DEVICE if name in ("train", "validation") else "cpu"
        data[name] = (placed(arrays, indices, device), *(torch.as_tensor(array, dtype=torch.float32, device=device) for array in labeled[name][:1 if name == "train" else 2]))
    return specs, data


@timed
def load_data(directory, targets):
    manifest, arrays = load(directory, targets)
    return (manifest, *load_splits(manifest, targets, arrays))


def capacities(model, specs, rows, batch):
    rates = [specs[index]["training_labels"] / rows for index in model.embedding]
    return [min(batch, 64 * math.ceil((rate * batch + 8 * math.sqrt(rate * (1 - rate) * batch)) / 64)) for rate in rates]


@timed
def fit(model, specs, data, parameters):
    inputs, labels = data["train"]
    capacity = capacities(model, specs, len(labels), parameters["batch"])
    return run_epochs(model, len(labels), parameters, lambda index: model.loss(model(*(part[index] for part in inputs)), labels[index], capacity), lambda: score(model, *data["validation"][:2], specs))


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


@timed
def train(directory, output, targets, parameters=PARAMETERS):
    targets = validate(targets)
    output = Path(output)
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    torch.manual_seed(SEED)
    manifest, specs, data = load_data(directory, targets)
    architecture = {**{key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}, "features": manifest["features"], "subreddits": len(manifest["subreddits"]) + 1}
    model = AttributeModel(targets, specs, **architecture).to(DEVICE)
    best, history = fit(model, specs, data, parameters)
    authors = {name: len(split[1]) for name, split in data.items()}
    del data["train"]
    calibration = calibrate(model, *data["calibration"][:2], specs)
    evaluation = report(model, *data["test"], specs, calibration)
    for name, fields in evaluation.items():
        LOG.info("attribute model test %s %s", name, json.dumps(fields))
    model_id = str(uuid.uuid4())
    artifact = {"model_id": model_id, "targets": targets, "specifications": specs, "architecture": architecture, "subreddits": manifest["subreddits"], "parameters": parameters, "model": {name: value.cpu() for name, value in model.state_dict().items()},
                "calibration": calibration, "evaluation": evaluation, "history": history, "validation_score": best, "source": manifest["source"],
                "authors": authors, "splits": SPLITS}
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
