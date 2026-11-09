import numpy as np
import torch

from . import timed
from .model import numeric

DEVICE = "cuda"
BINS = 15


def streamed(model, inputs, labels, column, limit=None, batch=8192):
    model.eval()
    taken = 0
    for start in range(0, len(labels), batch):
        if limit is not None and taken >= limit:
            return
        target = labels[start:start + batch, column].to(DEVICE)
        present = torch.isfinite(target)
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = model.output(model(*(part[start:start + batch].to(DEVICE)[present] for part in inputs)), column).float()
        taken += len(output)
        yield output, target[present]


def collect(model, inputs, labels, column, limit=None):
    outputs, targets = zip(*streamed(model, inputs, labels, column, limit))
    return torch.cat(outputs), torch.cat(targets)


def probabilities(model, inputs, labels, column, fitted):
    for output, target in streamed(model, inputs, labels, column):
        yield (output / fitted["temperature"]).softmax(1), target


def chosen(probabilities, threshold):
    return (probabilities >= threshold) | (probabilities == probabilities.max(1, keepdim=True).values)


def memberships(model, inputs, labels, column, indptr, values, batch=4096):
    model.eval()
    for start in range(0, len(labels), batch):
        rows = torch.arange(start, min(start + batch, len(labels)), device=labels.device)[torch.isfinite(labels[start:start + batch, column])]
        if not len(rows):
            continue
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = model.output(model(*(part[rows].to(DEVICE) for part in inputs)), column).float()
        starts, lengths = indptr[rows], indptr[rows + 1] - indptr[rows]
        offsets = torch.cumsum(lengths, 0) - lengths
        members = values[torch.repeat_interleave(starts - offsets, lengths) + torch.arange(int(lengths.sum()), device=lengths.device)]
        truth = torch.zeros(output.shape, dtype=torch.bool, device=DEVICE)
        truth[torch.repeat_interleave(torch.arange(len(rows), device=lengths.device), lengths).to(DEVICE), members.to(DEVICE)] = True
        yield output.softmax(1), truth


def set_report(model, inputs, labels, column, spec, fitted, indptr, values):
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    sums = torch.zeros(6, device=DEVICE)
    for probabilities, truth in memberships(model, inputs, labels, column, indptr, values):
        predicted = chosen(probabilities, fitted["threshold"])
        guessed = chosen(prior.expand_as(probabilities), fitted["threshold"])
        hits, sizes, members = (predicted & truth).sum(1).float(), predicted.sum(1).float(), truth.sum(1).float()
        top = truth.gather(1, probabilities.topk(min(5, probabilities.shape[1]), 1).indices).sum(1).float()
        sums += torch.stack([torch.ones_like(hits).sum(), (2 * hits / (sizes + members)).sum(), (hits / sizes).sum(), (hits / members).sum(), (top / members.clamp(max=5)).sum(),
                             (2 * (guessed & truth).sum(1) / (guessed.sum(1) + members)).sum()])
    n = float(sums[0])
    return {"n": int(n), "f1": float(sums[1]) / n, "precision": float(sums[2]) / n, "recall": float(sums[3]) / n, "recall_at_5": float(sums[4]) / n, "prior_f1": float(sums[5]) / n,
            "threshold": fitted["threshold"], "mean_size": spec["mean_size"]}


def macro_f1(predicted, target, classes):
    hits = torch.bincount(target[predicted == target], minlength=classes).float()
    sizes = (torch.bincount(predicted, minlength=classes) + torch.bincount(target, minlength=classes)).float()
    return float((2 * hits / sizes.clamp_min(1))[sizes > 0].mean())


def macro_recall(predicted, target, classes):
    sizes = torch.bincount(target, minlength=classes).float()
    return float((torch.bincount(target[predicted == target], minlength=classes).float() / sizes.clamp_min(1))[sizes > 0].mean())


def calibration_error(confidence, correct):
    bins = (confidence * BINS).long().clamp(0, BINS - 1)
    counts = torch.bincount(bins, minlength=BINS).double()
    gaps = (torch.bincount(bins, confidence.double(), minlength=BINS) - torch.bincount(bins, correct.double(), minlength=BINS)).abs()
    return float(gaps.sum() / counts.sum())


def categorical_report(model, inputs, labels, column, spec, fitted):
    chosen, targets, losses, tops, confidences = [], [], [], [], []
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    for scored, target in probabilities(model, inputs, labels, column, fitted):
        target = target.long()
        chosen.append(scored.argmax(1))
        targets.append(target)
        losses.append(-scored.gather(1, target[:, None]).squeeze(1).clamp_min(1e-12).log())
        tops.append((scored.topk(min(5, scored.shape[1]), 1).indices == target[:, None]).any(1))
        confidences.append(scored.gather(1, chosen[-1][:, None]).squeeze(1))
    chosen, target, losses, tops, confidence = (torch.cat(items) for items in (chosen, targets, losses, tops, confidences))
    classes = len(spec["values"])
    common = int(torch.bincount(chosen, minlength=classes).argmax())
    majority = int(np.argmax(spec["counts"]))
    result = {"n": len(target), "accuracy": float((chosen == target).float().mean()), "majority_baseline_accuracy": float((target == majority).float().mean()),
              "macro_f1": macro_f1(chosen, target, classes), "macro_recall": macro_recall(chosen, target, classes), "top5_accuracy": float(tops.float().mean()),
              "most_predicted": spec["values"][common], "most_predicted_share": float((chosen == common).float().mean()),
              "log_loss": float(losses.mean()), "prior_log_loss": float(-prior[target].log().mean()), "calibration_error": calibration_error(confidence, chosen == target)}
    return result


def numeric_report(model, inputs, labels, column, spec):
    output, target = collect(model, inputs, labels, column)
    predicted = numeric(output, spec)
    error = predicted - target
    return {"n": len(error), "mae": float(error.abs().mean()), "median_baseline_mae": float((target - spec["center"]).abs().mean()), "rmse": float(error.pow(2).mean().sqrt()),
            "correlation": float(torch.corrcoef(torch.stack([predicted, target]))[0, 1])}


@timed
def report(model, inputs, labels, sets, specs, calibration):
    lists = {column: (indptr, values) for column, indptr, values in sets}
    result = {}
    with torch.inference_mode():
        for column, (spec, fitted) in enumerate(zip(specs, calibration)):
            if spec["type"] == "numeric":
                result[spec["name"]] = numeric_report(model, inputs, labels, column, spec)
            elif spec["type"] == "set":
                result[spec["name"]] = set_report(model, inputs, labels, column, spec, fitted, *lists[column])
            else:
                result[spec["name"]] = categorical_report(model, inputs, labels, column, spec, fitted)
    return result
