import json
import random
from collections import Counter, defaultdict
from multiprocessing import Pool

from . import LOG, timed
from .config import ANNOTATIONS, FIELDS, WORKERS
from .labels import examples
from .rules import extract

ERROR_SAMPLES = 20


def score(rows):
    counts = {field: Counter() for field in FIELDS}
    errors = defaultdict(list)
    wrong = {field: Counter() for field in FIELDS}
    with Pool(WORKERS) as pool:
        predictions = pool.map(extract, [text for _, text, _ in rows], chunksize=500)
    for (record_id, text, expected), predicted in zip(rows, predictions):
        for field in FIELDS:
            guess, truth = predicted.get(field), expected.get(field)
            if guess is not None and guess == truth:
                counts[field]["tp"] += 1
                continue
            if guess is not None:
                counts[field]["fp"] += 1
                wrong[field][guess, truth] += 1
            if truth is not None:
                counts[field]["fn"] += 1
            if guess is not None or truth is not None:
                errors[field].append({"id": record_id, "predicted": guess, "label": truth, "text": text})
    return counts, errors, wrong


def metrics(count):
    tp, fp, fn = count["tp"], count["fp"], count["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def report(counts):
    total = sum(counts.values(), Counter())
    return {"micro": metrics(total), "fields": {field: metrics(count) for field, count in counts.items() if sum(count.values())}}


@timed
def evaluate(month, dataset, split):
    rows = list(examples(month, dataset, split))
    counts, errors, wrong = score(rows)
    result = {"dataset": dataset, "split": split, "texts": len(rows), **report(counts)}
    if split == "train":
        rng = random.Random(0)
        result["wrong"] = {field: [[guess, truth, n] for (guess, truth), n in common.most_common(20)] for field, common in wrong.items() if common}
        result["errors"] = {field: rng.sample(rows, min(ERROR_SAMPLES, len(rows))) for field, rows in errors.items()}
    out = ANNOTATIONS / month / "evaluations"
    out.mkdir(exist_ok=True)
    (out / f"{dataset}_{split}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    LOG.info("evaluate %s %s texts=%d micro=%s", dataset, split, len(rows), result["micro"])
    return result
