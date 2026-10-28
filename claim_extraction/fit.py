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
from .config import FIELDS, FIT_C, FIT_FOLDS, FIT_MIN_COUNT, FIT_THRESHOLDS, WEIGHTS, WORKERS
from .labels import examples
from .rules import features

FIELD_INDEX = {field: index for index, field in enumerate(FIELDS)}
CHUNK = 2000


def records(month, datasets):
    for dataset in datasets:
        for _, text, values in examples(month, dataset, "train"):
            yield text, values


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
    scored = defaultdict(list)
    for c, fold in product(FIT_C, range(FIT_FOLDS)):
        held = texts % FIT_FOLDS == fold
        for field, probability, target in best(results[c, fold][0], texts[held], fields[held], targets[held]):
            scored[c, field].append((probability, target))
    counts = defaultdict(Counter)
    for (c, field), pairs in scored.items():
        probabilities, hits = np.array(pairs).T
        for threshold in FIT_THRESHOLDS:
            chosen = probabilities >= threshold
            tp = int(hits[chosen].sum())
            counts[c, threshold, field].update({"tp": tp, "fp": int(chosen.sum()) - tp})
    total = sum(labels.values())
    tuned = {c: tune(counts, c, total) for c in FIT_C}
    LOG.info("search %s", {c: round(score, 4) for c, (_, score) in tuned.items()})
    c = max(tuned, key=lambda key: tuned[key][1])
    cutoffs = tuned[c][0]
    LOG.info("search c=%s oof=%.4f cutoffs=%s", c, tuned[c][1], cutoffs)
    LOG.info("search fields=%s", {field: round(f1(counts[c, cutoffs[field], field], labels[field]), 4) for field in FIELDS if labels[field]})
    return results[c, FIT_FOLDS][0], c, cutoffs


def tune(counts, c, total):
    micro = lambda chosen: f1(sum((counts[c, chosen[field], field] for field in FIELDS), Counter()), total)
    cutoffs = dict.fromkeys(FIELDS, max(FIT_THRESHOLDS, key=lambda t: micro(dict.fromkeys(FIELDS, t))))
    for _ in range(3):
        for field in FIELDS:
            cutoffs[field] = max(FIT_THRESHOLDS, key=lambda t: micro({**cutoffs, field: t}))
    return cutoffs, micro(cutoffs)


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
