import numpy as np
import torch

from . import timed
from .model import numeric

DEVICE = "cuda"
BINS = 15


@timed
def trunk(model, inputs, batch=1 << 16):
    model.eval()
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        return torch.cat([model(*(part[start:start + batch].to(DEVICE) for part in inputs)) for start in range(0, len(inputs[0]), batch)])


def streamed(model, hidden, labels, column, limit=None, batch=8192):
    taken = 0
    for start in range(0, len(labels), batch):
        if limit is not None and taken >= limit:
            return
        target = labels[start:start + batch, column].to(DEVICE)
        present = torch.isfinite(target)
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = model.output(hidden[start:start + batch][present], column).float()
        taken += len(output)
        yield output, target[present]


def collect(model, hidden, labels, column, limit=None):
    outputs, targets = zip(*streamed(model, hidden, labels, column, limit))
    return torch.cat(outputs), torch.cat(targets)


def probabilities(model, hidden, labels, column, fitted):
    for output, target in streamed(model, hidden, labels, column):
        yield (output / fitted["temperature"]).softmax(1), target


def chosen(probabilities, threshold):
    return (probabilities >= threshold) | (probabilities == probabilities.max(1, keepdim=True).values)


def memberships(model, hidden, labels, column, indptr, values, batch=4096):
    for start in range(0, len(labels), batch):
        rows = torch.arange(start, min(start + batch, len(labels)), device=labels.device)[torch.isfinite(labels[start:start + batch, column])]
        if not len(rows):
            continue
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = model.output(hidden[rows.to(DEVICE)], column).float()
        starts, lengths = indptr[rows], indptr[rows + 1] - indptr[rows]
        offsets = torch.cumsum(lengths, 0) - lengths
        members = values[torch.repeat_interleave(starts - offsets, lengths) + torch.arange(int(lengths.sum()), device=lengths.device)]
        truth = torch.zeros(output.shape, dtype=torch.bool, device=DEVICE)
        truth[torch.repeat_interleave(torch.arange(len(rows), device=lengths.device), lengths).to(DEVICE), members.to(DEVICE)] = True
        yield output.sigmoid(), truth


def micro(hits, predicted, actual):
    precision, recall = hits / max(predicted, 1), hits / max(actual, 1)
    return precision, recall, 2 * hits / max(predicted + actual, 1)


def set_report(model, hidden, labels, column, spec, fitted, indptr, values):
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    sums = torch.zeros(6, dtype=torch.float64, device=DEVICE)
    for probabilities, truth in memberships(model, hidden, labels, column, indptr, values):
        predicted = chosen(probabilities, fitted["threshold"])
        guessed = chosen(prior.expand_as(probabilities), fitted["threshold"])
        sums += torch.stack([torch.tensor(float(len(truth)), device=DEVICE), (predicted & truth).sum(), predicted.sum(), truth.sum(), (guessed & truth).sum(), guessed.sum()]).double()
    n, hits, predicted, actual, prior_hits, guessed = sums.tolist()
    precision, recall, f1 = micro(hits, predicted, actual)
    prior_precision, prior_recall, prior_f1 = micro(prior_hits, guessed, actual)
    return {"n": int(n), "pairs": int(actual), "precision": precision, "recall": recall, "f1": f1, "prior_precision": prior_precision, "prior_recall": prior_recall,
            "prior_f1": prior_f1, "threshold": fitted["threshold"], "mean_size": spec["mean_size"]}


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


def categorical_report(model, hidden, labels, column, spec, fitted):
    chosen, targets, losses, tops, confidences = [], [], [], [], []
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    for scored, target in probabilities(model, hidden, labels, column, fitted):
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


def numeric_report(model, hidden, labels, column, spec):
    output, target = collect(model, hidden, labels, column)
    predicted = numeric(output, spec)
    error = predicted - target
    return {"n": len(error), "mae": float(error.abs().mean()), "median_baseline_mae": float((target - spec["center"]).abs().mean()), "rmse": float(error.pow(2).mean().sqrt()),
            "correlation": float(torch.corrcoef(torch.stack([predicted, target]))[0, 1])}


def improvement(fields):
    if "mae" in fields:
        return 1 - fields["mae"] / fields["median_baseline_mae"]
    if "accuracy" in fields:
        return (fields["accuracy"] - fields["majority_baseline_accuracy"]) / (1 - fields["majority_baseline_accuracy"])
    return (fields["f1"] - fields["prior_f1"]) / (1 - fields["prior_f1"])


@timed
def report(model, inputs, labels, sets, specs, calibration):
    lists = {column: (indptr, values) for column, indptr, values in sets}
    hidden = trunk(model, inputs)
    result = {}
    with torch.inference_mode():
        for column, (spec, fitted) in enumerate(zip(specs, calibration)):
            if spec["type"] == "numeric":
                result[spec["name"]] = numeric_report(model, hidden, labels, column, spec)
            elif spec["type"] == "set":
                result[spec["name"]] = set_report(model, hidden, labels, column, spec, fitted, *lists[column])
            else:
                result[spec["name"]] = categorical_report(model, hidden, labels, column, spec, fitted)
            result[spec["name"]]["improvement"] = improvement(result[spec["name"]])
    return result
