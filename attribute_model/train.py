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
from .config import GPU_MEMORY, PARAMETERS, SEED, SPLITS, validate
from .data import load
from .model import AttributeModel, numeric, specifications

DEVICE = "cuda"


def collect(model, vectors, labels, column, batch=8192):
    model.eval()
    outputs, targets = [], []
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(vectors), batch):
            target = labels[start:start + batch, column]
            present = torch.isfinite(target)
            outputs.append(model.outputs(model(vectors[start:start + batch][present].float()))[column].float())
            targets.append(target[present])
    return torch.cat(outputs), torch.cat(targets)


def score(model, vectors, labels, specs, batch=8192):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(vectors), batch):
            batch_sums, batch_counts, _ = model.terms(model(vectors[start:start + batch].float()), labels[start:start + batch])
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
def calibrate(model, vectors, labels, specs, mass):
    result = []
    for column, spec in enumerate(specs):
        output, target = collect(model, vectors, labels, column)
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


def stated_auc(model, vectors, labels, batch=8192):
    scores = torch.cat([model.stated(model(vectors[start:start + batch].float())).float() for start in range(0, len(vectors), batch)])
    present = torch.isfinite(labels)
    ranks = scores.argsort(0).argsort(0).double() + 1
    positives = present.sum(0).double()
    return (((ranks * present).sum(0) - positives * (positives + 1) / 2) / (positives * (len(labels) - positives))).tolist()


def expected_calibration(confidence, correct, bins=15):
    edges = np.linspace(0, 1, bins + 1)[1:-1]
    which = np.digitize(confidence, edges)
    return float(sum(abs(confidence[which == b].mean() - correct[which == b].mean()) * np.mean(which == b) for b in np.unique(which)))


@timed
@torch.inference_mode()
def report(model, vectors, labels, specs, calibration):
    result = {}
    for column, (spec, fitted) in enumerate(zip(specs, calibration)):
        output, target = collect(model, vectors, labels, column)
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
            logged = output.div_(fitted["temperature"]).log_softmax(1)
            del output
            confidence, predicted = logged.max(1)
            confidence = confidence.exp()
            correct = (predicted == target).cpu().numpy()
            counts = np.bincount(target.cpu().numpy(), minlength=len(spec["values"]))
            wins = np.bincount(target.cpu().numpy(), weights=correct, minlength=len(spec["values"]))
            prior = torch.as_tensor(spec["prior"], device=DEVICE)
            top5 = float((logged.topk(min(5, logged.shape[1]), 1).indices == target[:, None]).any(1).float().mean())
            result[spec["name"]] = {"n": len(correct), "accuracy": float(correct.mean()), "majority_baseline_accuracy": float((target == int(np.argmax(spec["counts"]))).float().mean()),
                                    "top5_accuracy": top5, "macro_recall": float(np.mean(wins[counts > 0] / counts[counts > 0])),
                                    "log_loss": float(F.nll_loss(logged.clamp_min_(math.log(1e-12)), target)), "prior_log_loss": float(-prior[target].log().mean()),
                                    "calibration_error": expected_calibration(confidence.cpu().numpy(), correct)}
    with torch.autocast(DEVICE, dtype=torch.bfloat16):
        model.eval()
        for spec, auc in zip(specs, stated_auc(model, vectors, labels)):
            result[spec["name"]] |= {"stated_share": spec["stated"], "stated_auc": auc}
    return result


def gpu(inputs, labels, selected):
    vectors = torch.empty((len(selected), inputs.shape[1]), dtype=torch.from_numpy(inputs[:1].copy()).dtype, device=DEVICE)
    for start in range(0, len(selected), 1 << 20):
        vectors[start:start + (1 << 20)] = torch.from_numpy(np.asarray(inputs[selected[start:start + (1 << 20)]]))
    return vectors, torch.as_tensor(np.asarray(labels[selected]), dtype=torch.float32, device=DEVICE)


def load_splits(manifest, targets, inputs, labels, splits):
    selected = {name: np.flatnonzero(np.isin(splits, buckets)) for name, buckets in SPLITS.items()}
    specs = specifications(targets, manifest["catalogs"], labels, selected["train"])
    for name in ("validation", "calibration", "test"):
        counts = np.isfinite(np.asarray(labels[selected[name]])).sum(0)
        if (counts < 100).any():
            raise ValueError(f"Fewer than 100 {name} labels for {', '.join(spec['name'] for spec, count in zip(specs, counts) if count < 100)}")
    LOG.info("attribute model rows=%s", {name: len(indices) for name, indices in selected.items()})
    return specs, {name: gpu(inputs, labels, indices) for name, indices in selected.items()}


@timed
def load_data(directory, targets):
    manifest, arrays = load(directory, targets)
    return (manifest, *load_splits(manifest, targets, arrays["users"], arrays["labels"], np.asarray(arrays["splits"])))


def capacities(model, specs, rows, batch):
    rates = [specs[index]["training_labels"] / rows for index in model.embedding]
    return [min(batch, 64 * math.ceil((rate * batch + 8 * math.sqrt(rate * (1 - rate) * batch)) / 64)) for rate in rates]


@timed
def fit(model, specs, data, parameters):
    vectors, labels = data["train"]
    capacity = capacities(model, specs, len(labels), parameters["batch"])
    return run_epochs(model, len(labels), parameters, lambda index: model.loss(model(vectors[index].float()), labels[index], capacity), lambda: score(model, *data["validation"], specs))


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
def train(directory, output, targets, parameters=PARAMETERS, loader=load_data):
    targets = validate(targets)
    output = Path(output)
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    torch.manual_seed(SEED)
    manifest, specs, data = loader(directory, targets)
    architecture = {**{key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}, "features": manifest["features"]}
    model = AttributeModel(targets, specs, **architecture).to(DEVICE)
    best, history = fit(model, specs, data, parameters)
    authors = {name: len(labels) for name, (_, labels) in data.items()}
    del data["train"]
    calibration = calibrate(model, *data["calibration"], specs, parameters["interval_mass"])
    evaluation = report(model, *data["test"], specs, calibration)
    for name, fields in evaluation.items():
        LOG.info("attribute model test %s %s", name, json.dumps(fields))
    model_id = str(uuid.uuid4())
    artifact = {"model_id": model_id, "targets": targets, "specifications": specs, "architecture": architecture, "parameters": parameters, "model": {name: value.cpu() for name, value in model.state_dict().items()},
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
