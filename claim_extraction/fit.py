import json
import math
import time
from array import array
from collections import Counter, defaultdict
from itertools import islice, product
from multiprocessing import Pool

import numpy as np
from joblib import Parallel, delayed
from scipy.sparse import csr_matrix, hstack
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from . import LOG, timed
from .config import FIELDS, FIT_C, FIT_FOLDS, FIT_MIN_COUNT, FIT_THRESHOLDS, FIT_TOL, WEIGHTS, WORKERS
from .labels import examples
from .rules import cross, features

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
    with threadpool_limits(1):
        model = LogisticRegression(C=c, max_iter=5000, tol=FIT_TOL).fit(matrix[~held], targets[~held])
        result = model.predict_proba(matrix[held])[:, 1] if held.any() else model
    return result, time.time() - start


def best(probabilities, texts, fields, targets):
    chosen = {}
    for key, probability, target in zip(zip(texts.tolist(), fields.tolist()), probabilities.tolist(), targets.tolist()):
        if probability > chosen.get(key, (-1.0,))[0]:
            chosen[key] = (probability, target)
    return [(FIELDS[key[1]], probability, target) for key, (probability, target) in chosen.items()]


def f1(count, total):
    return 2 * count["tp"] / (count["tp"] + count["fp"] + total) if total else 0.0


@timed
def search(matrix, texts, fields, targets, labels, start):
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
    tuned = {c: tune(counts, c, labels, start) for c in FIT_C}
    LOG.info("search %s", {c: round(score, 4) for c, (_, score) in tuned.items()})
    c = max(tuned, key=lambda key: tuned[key][1])
    cutoffs = tuned[c][0]
    per_field = {field: round(f1(counts[c, cutoffs[field], field], labels[field]), 4) for field in FIELDS if labels[field]}
    LOG.info("search c=%s oof=%.4f macro=%.4f cutoffs=%s", c, tuned[c][1], sum(per_field.values()) / len(per_field), cutoffs)
    LOG.info("search fields=%s", per_field)
    oof = np.zeros(len(texts))
    for fold in range(FIT_FOLDS):
        oof[texts % FIT_FOLDS == fold] = results[c, fold][0]
    return results[c, FIT_FOLDS][0], c, cutoffs, oof


def tune(counts, c, labels, start):
    present = [field for field in FIELDS if labels[field]]
    total = sum(labels.values())
    score = lambda chosen: (f1(sum((counts[c, chosen[field], field] for field in FIELDS), Counter()), total) +
                            sum(f1(counts[c, chosen[field], field], labels[field]) for field in present) / len(present))
    cutoffs = dict(start)
    for _ in range(3):
        for field in FIELDS:
            cutoffs[field] = max(FIT_THRESHOLDS, key=lambda t: score({**cutoffs, field: t}))
    return cutoffs, f1(sum((counts[c, cutoffs[field], field] for field in FIELDS), Counter()), total)


@timed
def crossing(probabilities, texts, fields):
    tops = defaultdict(dict)
    for text, field, probability in zip(texts.tolist(), fields.tolist(), probabilities.tolist()):
        if probability > tops[text].get(FIELDS[field], -1.0):
            tops[text][FIELDS[field]] = probability
    ids, indices, indptr = {}, array("i"), array("q", [0])
    for text, field in zip(texts.tolist(), fields.tolist()):
        indices.extend(ids.setdefault(name, len(ids)) for name in sorted(cross(FIELDS[field], tops[text])))
        indptr.append(len(indices))
    matrix = csr_matrix((np.ones(len(indices), dtype=np.float32), np.frombuffer(indices, dtype=np.int32), np.frombuffer(indptr, dtype=np.int64)),
                        shape=(len(texts), len(ids)))
    keep = np.flatnonzero(np.bincount(matrix.indices, minlength=len(ids)) >= FIT_MIN_COUNT)
    LOG.info("crossing features=%d nonzeros=%d", len(keep), matrix.nnz)
    return matrix[:, keep], np.array(sorted(ids, key=ids.get), dtype=object)[keep]


def coefficients(names, model):
    return {name: round(float(weight), 4) for name, weight in zip(names, model.coef_[0]) if abs(weight) >= 1e-3}


@timed
def starting(path):
    logits = json.loads(path.read_text(encoding="utf-8"))["cutoffs"]
    cutoffs = {field: min(FIT_THRESHOLDS, key=lambda t: abs(t - 1 / (1 + math.exp(-logits[field])))) for field in FIELDS}
    LOG.info("start path=%s cutoffs=%s", path, cutoffs)
    return cutoffs


@timed
def fit(month, datasets, start):
    matrix, names, texts, fields, targets, labels = collect(month, datasets)
    begin = starting(start)
    first, _, _, oof = search(matrix, texts, fields, targets, labels, begin)
    extra, extra_names = crossing(oof, texts, fields)
    model, c, cutoffs, _ = search(hstack([matrix, extra]).tocsr(), texts, fields, targets, labels, begin)
    weights = coefficients(np.concatenate([names, extra_names]), model)
    result = {"c": c, "bias": round(float(model.intercept_[0]), 4), "cutoffs": {field: round(math.log(t / (1 - t)), 4) for field, t in cutoffs.items()},
              "weights": weights, "first": {"bias": round(float(first.intercept_[0]), 4), "weights": coefficients(names, first)}}
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    LOG.info("fit datasets=%s c=%s weights=%d path=%s", datasets, c, len(weights), WEIGHTS)
