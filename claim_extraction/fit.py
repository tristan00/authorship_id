import json
import math
from array import array
from collections import Counter, defaultdict
from itertools import product

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression

from . import LOG, timed
from .config import ANNOTATIONS, FIELDS, FIT_C, FIT_FOLDS, FIT_MIN_COUNT, FIT_THRESHOLDS, WEIGHTS
from .rules import features

FIELD_INDEX = {field: index for index, field in enumerate(FIELDS)}


def records(month, datasets):
    for dataset in datasets:
        root = ANNOTATIONS / month / dataset
        labels = {}
        for line in open(root / "labels.jsonl", encoding="utf-8"):
            row = json.loads(line)
            if row["split"] == "train":
                labels[row["id"]] = row["values"]
        for line in open(root / "records.jsonl", encoding="utf-8"):
            row = json.loads(line)
            if row["id"] in labels:
                yield row["text"], labels[row["id"]]


@timed
def collect(month, datasets):
    ids, indices, indptr = {}, array("i"), array("q", [0])
    texts, fields, targets, values, labels = array("i"), array("b"), array("b"), [], Counter()
    for index, (text, truth) in enumerate(records(month, datasets)):
        labels.update(truth.keys())
        for field, result, found in features(text):
            indices.extend(ids.setdefault(name, len(ids)) for name in sorted(found))
            indptr.append(len(indices))
            texts.append(index)
            fields.append(FIELD_INDEX[field])
            targets.append(truth.get(field) == result)
            values.append(result)
    matrix = csr_matrix((np.ones(len(indices), dtype=np.float32), np.frombuffer(indices, dtype=np.int32), np.frombuffer(indptr, dtype=np.int64)),
                        shape=(len(texts), len(ids)))
    keep = np.flatnonzero(np.bincount(matrix.indices, minlength=len(ids)) >= FIT_MIN_COUNT)
    names = np.array(sorted(ids, key=ids.get), dtype=object)[keep]
    matrix = matrix[:, keep].tocsr()
    LOG.info("collect texts=%d labels=%d candidates=%d features=%d nonzeros=%d", index + 1, sum(labels.values()), matrix.shape[0], len(names), matrix.nnz)
    return matrix, names, np.frombuffer(texts, dtype=np.int32), np.frombuffer(fields, dtype=np.int8), np.frombuffer(targets, dtype=np.int8), values, labels


def train(matrix, targets, c):
    return LogisticRegression(C=c, max_iter=5000).fit(matrix, targets)


def best(probabilities, texts, fields, targets):
    chosen = {}
    for key, probability, target in zip(zip(texts.tolist(), fields.tolist()), probabilities.tolist(), targets.tolist()):
        if probability > chosen.get(key, (-1.0,))[0]:
            chosen[key] = (probability, target)
    return [(FIELDS[key[1]], probability, target) for key, (probability, target) in chosen.items()]


def f1(count, total):
    return 2 * count["tp"] / (count["tp"] + count["fp"] + total) if total else 0.0


@timed
def validate(matrix, texts, fields, targets, labels):
    counts = defaultdict(Counter)
    for c, fold in product(FIT_C, range(FIT_FOLDS)):
        held = texts % FIT_FOLDS == fold
        model = train(matrix[~held], targets[~held], c)
        for field, probability, target in best(model.predict_proba(matrix[held])[:, 1], texts[held], fields[held], targets[held]):
            for threshold in FIT_THRESHOLDS:
                if probability >= threshold:
                    counts[c, threshold, field]["tp" if target else "fp"] += 1
        LOG.info("validate c=%s fold=%d", c, fold)
    micro = defaultdict(Counter)
    for (c, threshold, _), count in counts.items():
        micro[c, threshold].update(count)
    scores = {key: f1(count, sum(labels.values())) for key, count in micro.items()}
    LOG.info("validate %s", {f"{c}/{threshold}": round(score, 4) for (c, threshold), score in sorted(scores.items())})
    c, threshold = max(scores, key=scores.get)
    cutoffs = {field: max((t for t in FIT_THRESHOLDS if t <= threshold), key=lambda t: f1(counts[c, t, field], labels[field])) for field in FIELDS}
    LOG.info("validate c=%s threshold=%s cutoffs=%s", c, threshold, cutoffs)
    return c, cutoffs


@timed
def fit(month, datasets):
    matrix, names, texts, fields, targets, _, labels = collect(month, datasets)
    c, cutoffs = validate(matrix, texts, fields, targets, labels)
    model = train(matrix, targets, c)
    weights = {name: round(float(weight), 4) for name, weight in zip(names, model.coef_[0]) if abs(weight) >= 1e-3}
    result = {"c": c, "bias": round(float(model.intercept_[0]), 4), "cutoffs": {field: round(math.log(t / (1 - t)), 4) for field, t in cutoffs.items()},
              "weights": weights}
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    LOG.info("fit datasets=%s c=%s weights=%d path=%s", datasets, c, len(weights), WEIGHTS)
