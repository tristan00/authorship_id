import json
import math
from collections import Counter, defaultdict
from itertools import product
from multiprocessing import Pool

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

from . import LOG, timed
from .config import ANNOTATIONS, FIELDS, FIT_C, FIT_FOLDS, FIT_MIN_COUNT, FIT_THRESHOLDS, WEIGHTS, WORKERS
from .rules import features


def records(month, dataset):
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


def examples(item):
    text, truth = item
    return list(truth), [(field, sorted(found), int(truth.get(field) == result)) for field, result, found in features(text)]


@timed
def collect(month, dataset):
    items, labels = [], Counter()
    with Pool(WORKERS) as pool:
        for index, (fields, found) in enumerate(pool.imap(examples, records(month, dataset), chunksize=1000)):
            labels.update(fields)
            items.extend(((index, field), names, target) for field, names, target in found)
    LOG.info("collect texts=%d labels=%d candidates=%d", index + 1, sum(labels.values()), len(items))
    return items, labels


def train(items, c):
    counts = Counter(name for _, names, _ in items for name in names)
    vectorizer = DictVectorizer()
    matrix = vectorizer.fit_transform([{name: 1 for name in names if counts[name] >= FIT_MIN_COUNT} for _, names, _ in items])
    return vectorizer, LogisticRegression(C=c, max_iter=5000).fit(matrix, [target for *_, target in items])


def best(items, fitted):
    vectorizer, model = fitted
    chosen = {}
    for (key, _, target), probability in zip(items, model.predict_proba(vectorizer.transform([{name: 1 for name in names} for _, names, _ in items]))[:, 1]):
        if probability > chosen.get(key, (-1.0,))[0]:
            chosen[key] = (probability, target)
    return [(key[1], probability, target) for key, (probability, target) in chosen.items()]


def f1(count, total):
    return 2 * count["tp"] / (count["tp"] + count["fp"] + total) if total else 0.0


@timed
def validate(items, labels):
    counts = defaultdict(Counter)
    for c, fold in product(FIT_C, range(FIT_FOLDS)):
        fitted = train([item for item in items if item[0][0] % FIT_FOLDS != fold], c)
        for field, probability, target in best([item for item in items if item[0][0] % FIT_FOLDS == fold], fitted):
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
def fit(month, dataset):
    items, labels = collect(month, dataset)
    c, cutoffs = validate(items, labels)
    vectorizer, model = train(items, c)
    weights = {name: round(float(weight), 4) for name, weight in zip(vectorizer.get_feature_names_out(), model.coef_[0]) if abs(weight) >= 1e-3}
    result = {"c": c, "bias": round(float(model.intercept_[0]), 4), "cutoffs": {field: round(math.log(t / (1 - t)), 4) for field, t in cutoffs.items()},
              "weights": weights}
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    LOG.info("fit c=%s weights=%d path=%s", c, len(weights), WEIGHTS)
