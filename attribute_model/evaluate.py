import numpy as np
import torch

from . import timed
from .model import calibrated, numeric

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
        yield calibrated(output, fitted), target


def macro_f1(predicted, target, classes):
    hits = torch.bincount(target[predicted == target], minlength=classes).float()
    sizes = (torch.bincount(predicted, minlength=classes) + torch.bincount(target, minlength=classes)).float()
    return float((2 * hits / sizes.clamp_min(1))[sizes > 0].mean())


def macro_recall(predicted, target, classes):
    sizes = torch.bincount(target, minlength=classes).float()
    return float((torch.bincount(target[predicted == target], minlength=classes).float() / sizes.clamp_min(1))[sizes > 0].mean())


def area(score, positive):
    ranks = torch.argsort(torch.argsort(score)).double() + 1
    count = positive.sum().double()
    return float(((ranks * positive).sum() - count * (count + 1) / 2) / (count * (len(score) - count)))


def precision_area(score, positive):
    ordered = positive[torch.argsort(score, descending=True)].double()
    hits = ordered.cumsum(0)
    return float((hits / torch.arange(1, len(ordered) + 1, device=ordered.device) * ordered).sum() / ordered.sum().clamp_min(1))


def calibration_error(confidence, correct):
    bins = (confidence * BINS).long().clamp(0, BINS - 1)
    counts = torch.bincount(bins, minlength=BINS).double()
    gaps = (torch.bincount(bins, confidence.double(), minlength=BINS) - torch.bincount(bins, correct.double(), minlength=BINS)).abs()
    return float(gaps.sum() / counts.sum())


def categorical_report(model, inputs, labels, stated, column, spec, fitted):
    chosen, targets, said, losses, tops, confidences, spreads = [], [], [], [], [], [], []
    prior = torch.as_tensor(spec["prior"], device=DEVICE)
    for (scored, target), spoken in zip(probabilities(model, inputs, labels, column, fitted), spoken_batches(labels, stated, column), strict=True):
        target = target.long()
        chosen.append(scored.argmax(1))
        targets.append(target)
        said.append(spoken)
        losses.append(-scored.gather(1, target[:, None]).squeeze(1).clamp_min(1e-12).log())
        tops.append((scored.topk(min(5, scored.shape[1]), 1).indices == target[:, None]).any(1))
        confidences.append(scored.gather(1, chosen[-1][:, None]).squeeze(1))
        if spec["default"] is not None:
            spreads.append(1 - scored[:, spec["default"]])
    chosen, target, said, losses, tops, confidence = (torch.cat(items) for items in (chosen, targets, said, losses, tops, confidences))
    classes = len(spec["values"])
    common = int(torch.bincount(chosen, minlength=classes).argmax())
    majority = int(np.argmax(spec["counts"]))
    result = {"n": len(target), "accuracy": float((chosen == target).float().mean()), "majority_baseline_accuracy": float((target == majority).float().mean()),
              "macro_f1": macro_f1(chosen, target, classes), "macro_recall": macro_recall(chosen, target, classes), "top5_accuracy": float(tops.float().mean()),
              "most_predicted": spec["values"][common], "most_predicted_share": float((chosen == common).float().mean()),
              "log_loss": float(losses.mean()), "prior_log_loss": float(-prior[target].log().mean()), "calibration_error": calibration_error(confidence, chosen == target)}
    if spec["default"] is not None:
        spread = torch.cat(spreads)
        positive, called = target != spec["default"], chosen != spec["default"]
        result |= {"stated_n": int(said.sum()), "stated_accuracy": float((chosen[said] == target[said]).float().mean()) if said.any() else 0.,
                   "stated_majority_accuracy": float((target[said] == int(torch.bincount(target[said], minlength=classes).argmax())).float().mean()) if said.any() else 0.,
                   "stated_share": float(positive.float().mean()), "called_share": float(called.float().mean()), "stated_recall": float(called[positive].float().mean()),
                   "stated_precision": float(positive[called].float().mean()) if called.any() else 0., "auc": area(spread, positive),
                   "average_precision": precision_area(spread, positive), "detection_calibration_error": calibration_error(spread, positive),
                   "positive_value_accuracy": float((chosen[positive & called] == target[positive & called]).float().mean()) if (positive & called).any() else 0.}
    return result


def spoken_batches(labels, stated, column, batch=8192):
    for start in range(0, len(labels), batch):
        yield torch.isfinite(stated[start:start + batch, column].to(DEVICE))[torch.isfinite(labels[start:start + batch, column].to(DEVICE))]


def numeric_report(model, inputs, labels, column, spec):
    output, target = collect(model, inputs, labels, column)
    low, predicted, high = numeric(output, spec).unbind(1)
    error = predicted - target
    return {"n": len(error), "mae": float(error.abs().mean()), "median_baseline_mae": float((target - spec["center"]).abs().mean()), "rmse": float(error.pow(2).mean().sqrt()),
            "correlation": float(torch.corrcoef(torch.stack([predicted, target]))[0, 1]), "interval_coverage": float(((target >= low) & (target <= high)).float().mean()),
            "interval_width": float((high - low).median())}


@timed
def report(model, inputs, labels, stated, specs, calibration):
    result = {}
    with torch.inference_mode():
        for column, (spec, fitted) in enumerate(zip(specs, calibration)):
            result[spec["name"]] = numeric_report(model, inputs, labels, column, spec) if spec["type"] == "numeric" else categorical_report(model, inputs, labels, stated, column, spec, fitted)
    return result
