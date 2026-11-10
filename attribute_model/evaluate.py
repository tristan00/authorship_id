from typing import NamedTuple

import numpy as np
import torch

from . import timed

DEVICE = "cuda"
BINS = 15
CHUNK = 1 << 26
WINDOW = 8192
SET_WINDOW = 4096


class Labeled(NamedTuple):
    rows: torch.Tensor
    target: torch.Tensor
    indptr: torch.Tensor | None
    members: torch.Tensor | None


class Group(NamedTuple):
    columns: list
    rows: torch.Tensor
    target: torch.Tensor
    owner: torch.Tensor
    counts: torch.Tensor
    offsets: list
    lengths: torch.Tensor | None
    members: torch.Tensor | None
    starts: torch.Tensor | None


@timed
def trunk(model, inputs, batch=1 << 16):
    model.eval()
    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
        return torch.cat([model(*(part[start:start + batch].to(DEVICE) for part in inputs)) for start in range(0, len(inputs[0]), batch)])


def chosen(probabilities, threshold):
    return (probabilities >= threshold) | (probabilities == probabilities.max(1, keepdim=True).values)


def restrict(indptr, values, rows):
    starts, lengths = indptr[rows], indptr[rows + 1] - indptr[rows]
    offsets = torch.cumsum(lengths, 0) - lengths
    members = values[torch.repeat_interleave(starts - offsets, lengths) + torch.arange(int(lengths.sum()), device=lengths.device)]
    return torch.cat([lengths.new_zeros(1), torch.cumsum(lengths, 0)]).to(DEVICE), members.to(DEVICE)


@timed
def labeled(labels, sets):
    lists = {column: (indptr, values) for column, indptr, values in sets}
    columns, rows = torch.isfinite(labels).T.nonzero().T
    edges = torch.searchsorted(columns, torch.arange(labels.shape[1] + 1, device=columns.device)).tolist()
    result = []
    for column, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        picked = rows[low:high]
        result.append(Labeled(picked.to(DEVICE), labels[picked, column].to(DEVICE), *(restrict(*lists[column], picked) if column in lists else (None, None))))
    return result


def groups(specs, kinds):
    shapes = {}
    for column, spec in enumerate(specs):
        if spec["type"] in kinds:
            shapes.setdefault(len(spec.get("values", ())), []).append(column)
    return list(shapes.values())


def gather(data, columns):
    sizes = [len(data[column].rows) for column in columns]
    counts = torch.tensor(sizes, device=DEVICE)
    lists = (None, None, None)
    if data[columns[0]].indptr is not None:
        lengths = torch.cat([data[column].indptr.diff() for column in columns])
        lists = (lengths, torch.cat([data[column].members for column in columns]), torch.cat([lengths.new_zeros(1), torch.cumsum(lengths, 0)]))
    return Group(columns, torch.cat([data[column].rows for column in columns]), torch.cat([data[column].target for column in columns]),
                 torch.repeat_interleave(torch.arange(len(columns), device=DEVICE), counts), counts, np.cumsum([0] + sizes).tolist(), *lists)


def chunks(model, hidden, group, width, window):
    ids = group.rows // window
    bounds = [0, *(torch.nonzero((ids[1:] != ids[:-1]) | (group.owner[1:] != group.owner[:-1])).squeeze(1) + 1).tolist(), len(group.rows)]
    owners = group.owner[bounds[:-1]].tolist()
    first, budget = 0, max(1, CHUNK // width)
    while first < len(owners):
        last = first + 1
        while last < len(owners) and bounds[last + 1] - bounds[first] <= budget:
            last += 1
        start, end = bounds[first], bounds[last]
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            output = torch.cat([model.output(hidden[group.rows[bounds[segment]:bounds[segment + 1]]], group.columns[owners[segment]]).float() for segment in range(first, last)])
        truth = None
        if group.lengths is not None:
            truth = torch.zeros(output.shape, dtype=torch.bool, device=DEVICE)
            truth[torch.repeat_interleave(torch.arange(end - start, device=DEVICE), group.lengths[start:end]), group.members[int(group.starts[start]):int(group.starts[end])]] = True
        yield group.owner[start:end], output, truth
        first = last


def outputs(model, hidden, group, width, window):
    return torch.cat([output for _, output, _ in chunks(model, hidden, group, width, window)])


def per_head(values, owner, heads):
    return torch.zeros((heads, *values.shape[1:]), dtype=torch.long, device=DEVICE).index_add(0, owner, values.long())


def totals(values, owner, counts):
    starts = torch.cumsum(counts, 0) - counts
    width = int(counts.max())
    padded = values.new_zeros(len(counts) * width).index_put((owner * width + torch.arange(len(values), device=values.device) - starts[owner],), values)
    return padded.view(len(counts), width).sum(1)


def means(values, group):
    return totals(values, group.owner, group.counts) * (1 / group.counts.to(values.dtype))


def tallies(values, owner, heads, size, weights=None):
    return torch.bincount(owner * size + values, weights, minlength=heads * size).view(heads, size)


def micro(hits, predicted, actual):
    precision, recall = hits / max(predicted, 1), hits / max(actual, 1)
    return precision, recall, 2 * hits / max(predicted + actual, 1)


def priors(specs, group):
    return torch.tensor([specs[column]["prior"] for column in group.columns], dtype=torch.float32, device=DEVICE)


def set_reports(model, hidden, specs, group, fitted):
    heads, size = len(group.columns), len(specs[group.columns[0]]["values"])
    thresholds = torch.tensor([fitted[column]["threshold"] for column in group.columns], dtype=torch.float32, device=DEVICE)
    guesses = chosen(priors(specs, group), torch.tensor([fitted[column]["prior_threshold"] for column in group.columns], dtype=torch.float32, device=DEVICE)[:, None])
    hits = predicted_count = actual = 0
    stated = torch.zeros((heads, size), dtype=torch.long, device=DEVICE)
    for owner, output, truth in chunks(model, hidden, group, size, SET_WINDOW):
        predicted = chosen(output.sigmoid(), thresholds[owner, None])
        hits = hits + per_head((predicted & truth).sum(1), owner, heads)
        predicted_count = predicted_count + per_head(predicted.sum(1), owner, heads)
        actual = actual + per_head(truth.sum(1), owner, heads)
        stated += per_head(truth, owner, heads)
    counts = torch.stack([group.counts, hits, predicted_count, actual, (guesses * stated).sum(1), guesses.sum(1) * group.counts], 1).double().tolist()
    result = {}
    for column, (n, hit, chosen_count, stated_count, prior_hits, guessed) in zip(group.columns, counts):
        precision, recall, f1 = micro(hit, chosen_count, stated_count)
        prior_precision, prior_recall, prior_f1 = micro(prior_hits, guessed, stated_count)
        result[column] = {"n": int(n), "pairs": int(stated_count), "precision": precision, "recall": recall, "f1": f1, "prior_precision": prior_precision, "prior_recall": prior_recall,
                          "prior_f1": prior_f1, "threshold": fitted[column]["threshold"], "prior_threshold": fitted[column]["prior_threshold"], "mean_size": specs[column]["mean_size"]}
    return result


def categorical_reports(model, hidden, specs, group, fitted):
    classes = len(specs[group.columns[0]]["values"])
    inverse = 1 / torch.tensor([fitted[column]["temperature"] for column in group.columns], dtype=torch.float32, device=DEVICE)
    target = group.target.long()
    parts = []
    start = 0
    for owner, output, _ in chunks(model, hidden, group, classes, WINDOW):
        scored = (output * inverse[owner, None]).softmax(1)
        chunk = target[start:start + len(owner)]
        start += len(owner)
        picked = scored.argmax(1)
        parts.append((picked, scored.gather(1, picked[:, None]).squeeze(1), -scored.gather(1, chunk[:, None]).squeeze(1).clamp_min(1e-12).log(),
                      (scored.topk(min(5, classes), 1).indices == chunk[:, None]).any(1)))
    picked, confidence, losses, tops = (torch.cat(items) for items in zip(*parts))
    correct = picked == target
    majority = torch.tensor([int(np.argmax(specs[column]["counts"])) for column in group.columns], device=DEVICE)
    prior = priors(specs, group)
    heads = len(group.columns)
    hits = tallies(target[correct], group.owner[correct], heads, classes).float()
    predictions, actual = tallies(picked, group.owner, heads, classes), tallies(target, group.owner, heads, classes)
    sizes = (predictions + actual).float()
    used = sizes > 0
    common = predictions.argmax(1)
    bins = (confidence * BINS).long().clamp(0, BINS - 1)
    gaps = (tallies(bins, group.owner, heads, BINS, confidence.double()) - tallies(bins, group.owner, heads, BINS, correct.double())).abs()
    fields = {"n": group.counts, "accuracy": means(correct.float(), group), "majority_baseline_accuracy": means((target == majority[group.owner]).float(), group),
              "macro_f1": ((2 * hits / sizes.clamp_min(1)) * used).sum(1) * (1 / used.sum(1).float()),
              "macro_recall": ((hits / actual.float().clamp_min(1)) * (actual > 0)).sum(1) * (1 / (actual > 0).sum(1).float()), "top5_accuracy": means(tops.float(), group),
              "most_predicted_share": means((picked == common[group.owner]).float(), group), "log_loss": means(losses, group),
              "prior_log_loss": means(-prior[group.owner, target].log(), group), "calibration_error": gaps.sum(1) / tallies(bins, group.owner, heads, BINS).double().sum(1)}
    fields = {name: value.tolist() for name, value in fields.items()}
    common = common.tolist()
    result = {}
    for slot, column in enumerate(group.columns):
        values = {name: value[slot] for name, value in fields.items()}
        result[column] = {"n": values["n"], "accuracy": values["accuracy"], "majority_baseline_accuracy": values["majority_baseline_accuracy"], "macro_f1": values["macro_f1"],
                          "macro_recall": values["macro_recall"], "top5_accuracy": values["top5_accuracy"], "most_predicted": specs[column]["values"][common[slot]],
                          "most_predicted_share": values["most_predicted_share"], "log_loss": values["log_loss"], "prior_log_loss": values["prior_log_loss"],
                          "calibration_error": values["calibration_error"]}
    return result


def numeric_reports(model, hidden, specs, group):
    scale = torch.tensor([specs[column]["scale"] for column in group.columns], dtype=torch.float32, device=DEVICE)
    center = torch.tensor([specs[column]["center"] for column in group.columns], dtype=torch.float32, device=DEVICE)
    predicted = outputs(model, hidden, group, 1, WINDOW)[:, 0] * scale[group.owner] + center[group.owner]
    error = predicted - group.target
    shifted = [values - means(values, group)[group.owner] for values in (predicted, group.target)]
    spread = [means(values * values, group).sqrt() for values in shifted]
    fields = {"n": group.counts, "mae": means(error.abs(), group), "median_baseline_mae": means((group.target - center[group.owner]).abs(), group), "rmse": means(error.pow(2), group).sqrt(),
              "correlation": (means(shifted[0] * shifted[1], group) / spread[0] / spread[1]).clamp(-1, 1)}
    fields = {name: value.tolist() for name, value in fields.items()}
    return {column: {name: value[slot] for name, value in fields.items()} for slot, column in enumerate(group.columns)}


def improvement(fields):
    if "mae" in fields:
        return 1 - fields["mae"] / fields["median_baseline_mae"]
    if "accuracy" in fields:
        return (fields["accuracy"] - fields["majority_baseline_accuracy"]) / (1 - fields["majority_baseline_accuracy"])
    return (fields["f1"] - fields["prior_f1"]) / (1 - fields["prior_f1"])


@timed
def evaluated(model, hidden, data, specs, calibration):
    result = {}
    with torch.inference_mode():
        for columns in groups(specs, ("numeric",)):
            result |= numeric_reports(model, hidden, specs, gather(data, columns))
        for columns in groups(specs, ("categorical", "embedding")):
            result |= categorical_reports(model, hidden, specs, gather(data, columns), calibration)
        for columns in groups(specs, ("set",)):
            result |= set_reports(model, hidden, specs, gather(data, columns), calibration)
    report = {}
    for column, spec in enumerate(specs):
        report[spec["name"]] = result[column] | {"improvement": improvement(result[column])}
    return report


@timed
def report(model, inputs, labels, sets, specs, calibration):
    return evaluated(model, trunk(model, inputs), labeled(labels, sets), specs, calibration)
