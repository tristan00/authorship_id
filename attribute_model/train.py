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
from .data import load, read, reader
from .evaluate import DEVICE, SET_WINDOW, WINDOW, Labeled, chosen, chunks, gather, groups, labeled, outputs, per_head, priors, report, totals, trunk
from .model import AttributeModel, specifications

INPUTS = ("users",)


def member_columns(sets, specs):
    return [(column, indptr, values, torch.arange(int((indptr[1:] - indptr[:-1]).max()), device=indptr.device), len(specs[column]["values"])) for column, indptr, values in sets]


def gathered(columns, rows):
    result = {}
    for column, indptr, values, offsets, size in columns:
        start = indptr[rows]
        positions = start[:, None] + offsets
        stated = offsets < (indptr[rows + 1] - start)[:, None]
        result[column] = torch.where(stated, values[positions.clamp(max=len(values) - 1)], size)
    return result


def score(model, inputs, labels, sets, specs, columns, batch=2048):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(labels), batch):
            rows = torch.arange(start, min(start + batch, len(labels)), device=labels.device)
            target = labels[start:start + batch].to(DEVICE)
            batch_sums, batch_counts, _ = model.terms(model(*(part[start:start + batch].to(DEVICE) for part in inputs)), target, gathered(columns, rows))
            sums, counts = sums + batch_sums, counts + batch_counts
    ratios = (sums / counts / model.baseline).tolist()
    return float(np.mean(ratios)), dict(zip((spec["name"] for spec in specs), ratios))


def sampled(data, limit, batch=WINDOW):
    rows = data.rows
    if len(rows) < limit:
        return data
    kept = int(torch.searchsorted(rows, (rows[limit - 1] // batch + 1) * batch))
    return Labeled(rows[:kept], data.target[:kept], None, None)


def temperatures(group, output, lr=.1, iterations=100, tolerance_grad=1e-7, tolerance_change=1e-9):
    target = group.target.long()

    def evaluate(position):
        position = position.detach().requires_grad_()
        loss = totals(F.cross_entropy(output / position.exp()[group.owner, None], target, reduction="none"), group.owner, group.counts) / group.counts
        grad, = torch.autograd.grad(loss.sum(), position)
        return loss.detach(), grad

    position = torch.zeros(len(group.columns), device=DEVICE)
    loss, grad = evaluate(position)
    active = grad.abs() > tolerance_grad
    scale = torch.ones_like(position)
    for iteration in range(1, iterations + 1):
        if iteration == 1:
            direction = -grad
            step = (1 / grad.abs()).clamp(max=1.) * lr
        else:
            change, moved = grad - previous, direction * step
            curvature = change * moved
            scale = torch.where(curvature > 1e-10, curvature / (change * change), scale)
            direction = -grad * scale
            step = torch.full_like(position, lr)
        previous, last = grad, loss
        active = active & (grad * direction <= -tolerance_change)
        position = torch.where(active, position + step * direction, position)
        if iteration == iterations or not bool(active.any()):
            break
        loss, grad = evaluate(position)
        active = active & (grad.abs() > tolerance_grad) & ((direction * step).abs() > tolerance_change) & ((loss - last).abs() >= tolerance_change)
    return position.exp().tolist()


@timed
def categorical(model, hidden, data, specs, columns):
    group = gather([sampled(data[column], TEMPERATURE_ROWS) if column in columns else data[column] for column in range(len(data))], columns)
    output = outputs(model, hidden, group, len(specs[columns[0]]["values"]), WINDOW)
    with torch.inference_mode(False):
        return {column: {"temperature": value} for column, value in zip(columns, temperatures(group, output.clone()))}


@timed
def membership(model, hidden, data, specs, columns):
    group = gather(data, columns)
    heads, size = len(columns), len(specs[columns[0]]["values"])
    prior = priors(specs, group)
    guessed = torch.stack([chosen(prior, threshold) for threshold in THRESHOLDS])
    model_pairs = torch.zeros(len(THRESHOLDS), 2, heads, dtype=torch.long, device=DEVICE)
    actual = 0
    stated = torch.zeros((heads, size), dtype=torch.long, device=DEVICE)
    for owner, output, truth in chunks(model, hidden, group, size, SET_WINDOW):
        probabilities = output.sigmoid()
        for slot, threshold in enumerate(THRESHOLDS):
            predicted = chosen(probabilities, threshold)
            model_pairs[slot, 0] += per_head((predicted & truth).sum(1), owner, heads)
            model_pairs[slot, 1] += per_head(predicted.sum(1), owner, heads)
        actual = actual + per_head(truth.sum(1), owner, heads)
        stated += per_head(truth, owner, heads)
    pairs = torch.stack([model_pairs, torch.stack([(guessed * stated).sum(2), guessed.sum(2) * group.counts], 1)]).float()
    scores = 2 * pairs[:, :, 0] / (pairs[:, :, 1] + actual.float())
    best = scores.argmax(1).tolist()
    values = scores.tolist()
    return {column: {"threshold": THRESHOLDS[best[0][slot]], "f1": values[0][best[0][slot]][slot], "prior_threshold": THRESHOLDS[best[1][slot]], "prior_f1": values[1][best[1][slot]][slot]}
            for slot, column in enumerate(columns)}


@timed
def calibrated(model, hidden, data, specs):
    result = {column: {} for column, spec in enumerate(specs) if spec["type"] == "numeric"}
    for columns in groups(specs, ("categorical", "embedding")):
        result |= categorical(model, hidden, data, specs, columns)
    for columns in groups(specs, ("set",)):
        result |= membership(model, hidden, data, specs, columns)
    for column, spec in enumerate(specs):
        LOG.info("attribute model calibrated %s %s", spec["name"], json.dumps(result[column]))
    return [result[column] for column in range(len(specs))]


@timed
def calibrate(model, inputs, labels, sets, specs):
    return calibrated(model, trunk(model, inputs), labeled(labels, sets), specs)


@timed
def place_split(arrays, sets, columns, readers, name, start, end):
    device = DEVICE if name in ("train", "validation") else "cpu"
    members = []
    for target, (indptr, values) in sets.items():
        offsets = read(indptr, start, end + 1, device, readers)
        low, high = int(offsets[0]), int(offsets[-1])
        offsets -= low
        members.append((columns[target], offsets, read(values, low, high, device, readers).long()))
    return tuple(read(arrays[array], start, end, device, readers) for array in INPUTS), read(arrays["labels"], start, end, device, readers), members


@timed
def observed(manifest, train):
    _, labels, members = train
    names = list(manifest["targets"])
    sets = {}
    for column, indptr, values in members:
        lengths = indptr.diff()
        sets[names[column]] = (int((lengths > 0).sum()), int(lengths.max()), int(indptr[-1]), torch.bincount(values, minlength=len(manifest["catalogs"][names[column]])).cpu().numpy())
    return [column[torch.isfinite(column)].cpu().numpy() for column in labels.T], sets


def load_splits(manifest, arrays, sets):
    targets = manifest["targets"]
    columns = {name: column for column, name in enumerate(targets)}
    readers = reader()
    data = {name: place_split(arrays, sets, columns, readers, name, start, end) for name, (start, end) in manifest["splits"].items()}
    specs = specifications(targets, manifest["catalogs"], *observed(manifest, data["train"]))
    for slot, name in enumerate(SPLITS):
        short = [target for target, counts in manifest["split_labels"].items() if counts[slot] < SPLIT_LABELS]
        if slot and short:
            raise ValueError(f"Fewer than {SPLIT_LABELS} {name} labels for {', '.join(short)}")
    LOG.info("attribute model rows=%s", {name: len(split[1]) for name, split in data.items()})
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
    columns = {name: member_columns(data[name][2], specs) for name in ("train", "validation")}
    capacity = capacities(model, specs, len(labels), parameters["batch"])
    return run_epochs(model, len(labels), parameters, lambda index: model.loss(model(*(part[index] for part in inputs)), labels[index], gathered(columns["train"], index), capacity),
                      lambda: score(model, *data["validation"], specs, columns["validation"]))


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
