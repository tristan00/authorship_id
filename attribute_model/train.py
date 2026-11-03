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
from .config import GPU_MEMORY, PARAMETERS, SEED, SPLITS, TAUS, TEMPERATURE_ROWS, validate
from .data import load
from .model import AttributeModel, adjusted, decide, numeric, specifications

DEVICE = "cuda"


def streamed(model, vectors, labels, column, limit=None, batch=8192, everyone=False):
    model.eval()
    taken = 0
    for start in range(0, len(vectors), batch):
        if limit is not None and taken >= limit:
            return
        target = labels[start:start + batch, column].to(DEVICE)
        present = torch.ones_like(target, dtype=torch.bool) if everyone else torch.isfinite(target)
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = model.output(model(vectors[start:start + batch].to(DEVICE)[present].float()), column).float()
        taken += len(output)
        yield output, target[present]


def collect(model, vectors, labels, column, limit=None):
    outputs, targets = zip(*streamed(model, vectors, labels, column, limit))
    return torch.cat(outputs), torch.cat(targets)


def score(model, vectors, labels, specs, batch=8192):
    model.eval()
    sums = counts = 0
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        for start in range(0, len(vectors), batch):
            batch_sums, batch_counts, _ = model.terms(model(vectors[start:start + batch].to(DEVICE).float()), labels[start:start + batch].to(DEVICE))
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


def macro_f1(predicted, target, classes):
    hits = torch.bincount(target[predicted == target], minlength=classes).float()
    sizes = (torch.bincount(predicted, minlength=classes) + torch.bincount(target, minlength=classes)).float()
    return float((2 * hits / sizes.clamp_min(1))[sizes > 0].mean())


def macro_recall(predicted, target, classes):
    sizes = torch.bincount(target, minlength=classes).float()
    return float((torch.bincount(target[predicted == target], minlength=classes).float() / sizes.clamp_min(1))[sizes > 0].mean())


def area(spread, positive):
    ranks = torch.argsort(torch.argsort(spread)).double() + 1
    count = positive.sum().double()
    return float(((ranks * positive).sum() - count * (count + 1) / 2) / (count * (len(spread) - count)))


def probabilities(model, vectors, labels, column, fitted, everyone=False):
    for output, target in streamed(model, vectors, labels, column, everyone=everyone):
        yield (output / fitted["temperature"]).softmax(1), target


def categorical(model, vectors, labels, column, spec):
    sample, target = collect(model, vectors, labels, column, TEMPERATURE_ROWS)
    fitted = {"temperature": temperature(sample, target.long())}
    del sample
    classes = len(spec["values"])
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    if spec["default"] is not None:
        prior[spec["default"]] = 0
    stated = float(prior.sum())
    prior /= stated
    shares, spreads = torch.zeros((len(TAUS), classes), device=DEVICE), []
    for scored, _ in probabilities(model, vectors, labels, column, fitted, everyone=True):
        for place, tau in enumerate(TAUS):
            shares[place] += torch.bincount(adjusted(scored, spec, tau), minlength=classes)
        if spec["default"] is not None:
            spreads.append(1 - scored[:, spec["default"]])
    distances = (shares / shares.sum(1, keepdim=True) - prior).abs().sum(1) / 2
    fitted |= {"n": int(shares[0].sum()), "tau": TAUS[int(distances.argmin())], "distance": float(distances.min())}
    if spec["default"] is not None:
        spreads = torch.cat(spreads)
        fitted["threshold"] = float(spreads.kthvalue(max(1, round(len(spreads) * (1 - stated)))).values)
    return fitted


@timed
def calibrate(model, vectors, labels, specs, mass):
    result = []
    for column, spec in enumerate(specs):
        if spec["type"] == "numeric":
            output, target = collect(model, vectors, labels, column)
            _, lower, upper = numeric(output, spec)
            residuals = torch.sort(torch.maximum(lower - target, target - upper)).values.cpu().numpy()
            rank = math.ceil((len(residuals) + 1) * mass)
            if rank > len(residuals):
                raise ValueError(f"{spec['name']}: too few calibration labels for a {mass:.0%} interval")
            result.append({"n": len(residuals), "mass": mass, "radius": float(residuals[rank - 1])})
        else:
            result.append(categorical(model, vectors, labels, column, spec))
        LOG.info("attribute model calibrated %s %s", spec["name"], json.dumps(result[-1]))
    return result


def categorical_report(model, vectors, labels, column, spec, fitted):
    chosen, targets, losses, tops, spreads = [], [], [], [], []
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    for scored, target in probabilities(model, vectors, labels, column, fitted):
        target = target.long()
        chosen.append(decide(scored, spec, fitted))
        targets.append(target)
        losses.append(-scored.gather(1, target[:, None]).squeeze(1).clamp_min(1e-12).log())
        tops.append((scored.topk(min(5, scored.shape[1]), 1).indices == target[:, None]).any(1))
        if spec["default"] is not None:
            spreads.append(1 - scored[:, spec["default"]])
    chosen, target, losses, tops = torch.cat(chosen), torch.cat(targets), torch.cat(losses), torch.cat(tops)
    classes = len(spec["values"])
    common = int(torch.bincount(chosen, minlength=classes).argmax())
    result = {"n": len(target), "accuracy": float((chosen == target).float().mean()), "majority_baseline_accuracy": float((target == int(np.argmax(spec["counts"]))).float().mean()),
              "macro_f1": macro_f1(chosen, target, classes), "macro_recall": macro_recall(chosen, target, classes), "top5_accuracy": float(tops.float().mean()),
              "most_predicted": spec["values"][common], "most_predicted_share": float((chosen == common).float().mean()),
              "log_loss": float(losses.mean()), "prior_log_loss": float(-prior[target].log().mean())}
    if spec["default"] is not None:
        positive, called = target != spec["default"], chosen != spec["default"]
        result |= {"stated_share": float(positive.float().mean()), "called_share": float(called.float().mean()), "stated_recall": float(called[positive].float().mean()),
                   "stated_precision": float(positive[called].float().mean()) if called.any() else 0., "auc": area(torch.cat(spreads), positive),
                   "positive_value_accuracy": float((chosen[positive & called] == target[positive & called]).float().mean()) if (positive & called).any() else 0.}
    return result


@timed
def report(model, vectors, labels, specs, calibration):
    result = {}
    for column, (spec, fitted) in enumerate(zip(specs, calibration)):
        if spec["type"] == "numeric":
            with torch.inference_mode():
                output, target = collect(model, vectors, labels, column)
                predicted, lower, upper = numeric(output, spec)
                lower, upper = lower - fitted["radius"], upper + fitted["radius"]
                error = (predicted - target).cpu().numpy()
                base = (target - spec["center"]).abs().mean()
                result[spec["name"]] = {"n": len(error), "mae": float(np.abs(error).mean()), "median_baseline_mae": float(base), "rmse": float(np.sqrt(np.mean(error ** 2))),
                                        "interval_coverage": float(((target >= lower) & (target <= upper)).float().mean()), "interval_width": float((upper - lower).mean()),
                                        "interval_width_median": float((upper - lower).median())}
        else:
            with torch.inference_mode():
                result[spec["name"]] = categorical_report(model, vectors, labels, column, spec, fitted)
    return result


def placed(inputs, labels, selected, device):
    vectors = torch.empty((len(selected), inputs.shape[1]), dtype=torch.from_numpy(inputs[:1].copy()).dtype, device=device)
    for start in range(0, len(selected), 1 << 20):
        vectors[start:start + (1 << 20)] = torch.from_numpy(np.asarray(inputs[selected[start:start + (1 << 20)]]))
    return vectors, torch.as_tensor(np.asarray(labels[selected]), dtype=torch.float32, device=device)


def load_splits(manifest, targets, inputs, labels, splits):
    selected = {name: np.flatnonzero(np.isin(splits, buckets)) for name, buckets in SPLITS.items()}
    specs = specifications(targets, manifest["catalogs"], labels, selected["train"])
    for name in ("validation", "calibration", "test"):
        counts = np.isfinite(np.asarray(labels[selected[name]])).sum(0)
        if (counts < 100).any():
            raise ValueError(f"Fewer than 100 {name} labels for {', '.join(spec['name'] for spec, count in zip(specs, counts) if count < 100)}")
    LOG.info("attribute model rows=%s", {name: len(indices) for name, indices in selected.items()})
    return specs, {name: placed(inputs, labels, indices, DEVICE if name in ("train", "validation") else "cpu") for name, indices in selected.items()}


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
