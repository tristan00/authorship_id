import json
import math
import time
from collections import Counter, defaultdict
from itertools import islice, product
from multiprocessing import Pool

import numpy as np
from joblib import Parallel, delayed
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression

from . import LOG, timed
from .config import ANNOTATIONS, FIELDS, FIT_C, FIT_FOLDS, FIT_MIN_COUNT, FIT_THRESHOLDS, WEIGHTS, WORKERS
from .rules import features

FIELD_INDEX = {field: index for index, field in enumerate(FIELDS)}
CHUNK = 2000


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


def batches(month, datasets):
    items = records(month, datasets)
    while batch := list(islice(items, CHUNK)):
        yield batch


def candidates(batch):
    names, indices, indptr, rows, fields, targets, labels = {}, [], [0], [], [], [], Counter()
    for row, (text, truth) in enumerate(batch):
        labels.update(truth.keys())
        for field, result, found in features(text):
            indices.extend(names.setdefault(name, len(names)) for name in sorted(found))
            indptr.append(len(indices))
            rows.append(row)
            fields.append(FIELD_INDEX[field])
            targets.append(truth.get(field) == result)
    return (len(batch), list(names), np.array(indices, dtype=np.int32), np.array(indptr, dtype=np.int64), np.array(rows, dtype=np.int32),
            np.array(fields, dtype=np.int8), np.array(targets, dtype=np.int8), labels)


@timed
def collect(month, datasets):
    ids, labels, parts, texts, nonzeros = {}, Counter(), [], 0, 0
    with Pool(WORKERS) as pool:
        for size, names, indices, indptr, rows, fields, targets, counts in pool.imap(candidates, batches(month, datasets)):
            remap = np.fromiter((ids.setdefault(name, len(ids)) for name in names), dtype=np.int32, count=len(names))
            parts.append((remap[indices], indptr[1:] + nonzeros, rows + texts, fields, targets))
            labels.update(counts)
            texts += size
            nonzeros += len(indices)
    indices, indptr, rows, fields, targets = (np.concatenate(column) for column in zip(*parts))
    matrix = csr_matrix((np.ones(len(indices), dtype=np.float32), indices, np.concatenate(([0], indptr))), shape=(len(rows), len(ids)))
    keep = np.flatnonzero(np.bincount(matrix.indices, minlength=len(ids)) >= FIT_MIN_COUNT)
    names = np.array(sorted(ids, key=ids.get), dtype=object)[keep]
    matrix = matrix[:, keep].tocsr()
    matrix.sort_indices()
    LOG.info("collect texts=%d labels=%d candidates=%d features=%d nonzeros=%d", texts, sum(labels.values()), matrix.shape[0], len(names), matrix.nnz)
    return matrix, names, rows, fields, targets, labels


def train(matrix, targets, texts, c, fold):
    start = time.time()
    held = texts % FIT_FOLDS == fold
    model = LogisticRegression(C=c, max_iter=5000).fit(matrix[~held], targets[~held])
    return (model.predict_proba(matrix[held])[:, 1] if held.any() else model), time.time() - start


def best(probabilities, texts, fields, targets):
    chosen = {}
    for key, probability, target in zip(zip(texts.tolist(), fields.tolist()), probabilities.tolist(), targets.tolist()):
        if probability > chosen.get(key, (-1.0,))[0]:
            chosen[key] = (probability, target)
    return [(FIELDS[key[1]], probability, target) for key, (probability, target) in chosen.items()]


def f1(count, total):
    return 2 * count["tp"] / (count["tp"] + count["fp"] + total) if total else 0.0


@timed
def search(matrix, texts, fields, targets, labels):
    jobs = [*product(FIT_C, range(FIT_FOLDS)), *product(FIT_C, (FIT_FOLDS,))]
    results = dict(zip(jobs, Parallel(n_jobs=len(jobs))(delayed(train)(matrix, targets, texts, c, fold) for c, fold in jobs)))
    LOG.info("search seconds=%s", {f"{c}/{fold}": round(seconds) for (c, fold), (_, seconds) in results.items()})
    counts = defaultdict(Counter)
    for c, fold in product(FIT_C, range(FIT_FOLDS)):
        held = texts % FIT_FOLDS == fold
        for field, probability, target in best(results[c, fold][0], texts[held], fields[held], targets[held]):
            for threshold in FIT_THRESHOLDS:
                if probability >= threshold:
                    counts[c, threshold, field]["tp" if target else "fp"] += 1
    micro = defaultdict(Counter)
    for (c, threshold, _), count in counts.items():
        micro[c, threshold].update(count)
    scores = {key: f1(count, sum(labels.values())) for key, count in micro.items()}
    LOG.info("search %s", {f"{c}/{threshold}": round(score, 4) for (c, threshold), score in sorted(scores.items())})
    c, threshold = max(scores, key=scores.get)
    cutoffs = {field: max((t for t in FIT_THRESHOLDS if t <= threshold), key=lambda t: f1(counts[c, t, field], labels[field])) for field in FIELDS}
    LOG.info("search c=%s threshold=%s cutoffs=%s", c, threshold, cutoffs)
    return results[c, FIT_FOLDS][0], c, cutoffs


@timed
def fit(month, datasets):
    matrix, names, texts, fields, targets, labels = collect(month, datasets)
    model, c, cutoffs = search(matrix, texts, fields, targets, labels)
    weights = {name: round(float(weight), 4) for name, weight in zip(names, model.coef_[0]) if abs(weight) >= 1e-3}
    result = {"c": c, "bias": round(float(model.intercept_[0]), 4), "cutoffs": {field: round(math.log(t / (1 - t)), 4) for field, t in cutoffs.items()},
              "weights": weights}
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    LOG.info("fit datasets=%s c=%s weights=%d path=%s", datasets, c, len(weights), WEIGHTS)
