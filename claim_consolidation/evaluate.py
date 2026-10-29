import json
import time
from collections import Counter, defaultdict

from claim_extraction.config import ANNOTATIONS
from claim_extraction.labels import split

from . import LOG, timed
from .config import CLAIM_LINES
from .rules import consolidate

PARTS = ("train", "validation")


def rows(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def f1(hit, given, wanted):
    precision, recall = hit / given if given else 0.0, hit / wanted if wanted else 0.0
    return precision, recall, 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def tied(tally):
    top = max(tally.values())
    return sum(count == top for count in tally.values()) > 1


@timed
def evaluate(month, dataset, part):
    if part not in PARTS:
        raise ValueError(f"evaluate runs on {PARTS}, not {part}")
    root = ANNOTATIONS / month / dataset
    labels = {row["id"]: row for row in rows(root / "labels.jsonl") if split(row["id"]) == part}
    claimed = [(row["id"], [tuple(claim) for claim in row["claims"]]) for row in rows(root / "claims.jsonl") if row["id"] in labels]
    capped = sum(len(evidence) > CLAIM_LINES for _, evidence in claimed)
    failed = sum(labels[author]["error"] is not None for author, _ in claimed)
    records = [(author, evidence) for author, evidence in claimed if len(evidence) <= CLAIM_LINES and labels[author]["error"] is None]
    started = time.perf_counter()
    predicted = [consolidate(evidence) for _, evidence in records]
    seconds = time.perf_counter() - started
    counts = {kind: Counter() for kind in ("hit", "silent", "extra", "different", "wanted", "given", "present")}
    groups = defaultdict(Counter)
    for (author, evidence), mine in zip(records, predicted):
        truth, seen, tallies = labels[author]["values"], {(field, value) for _, _, field, value in evidence}, {}
        for _, _, field, value in evidence:
            tallies.setdefault(field, Counter())[value] += 1
        for field in mine.keys() | truth.keys():
            ours, theirs = mine.get(field), truth.get(field)
            counts["given"][field] += ours is not None
            counts["wanted"][field] += theirs is not None
            counts["present"][field] += theirs is not None and (field, theirs) in seen
            kind = "hit" if ours == theirs else "silent" if ours is None else "extra" if theirs is None else "different"
            counts[kind][field] += 1
        for field, tally in tallies.items():
            if tied(tally):
                groups[field, tuple(sorted(tally.items()))][truth.get(field), (field, truth.get(field)) in seen] += 1
    unreachable = Counter()
    for (field, _), answers in groups.items():
        majority = Counter({answer: count for (answer, _), count in answers.items()}).most_common(1)[0][0]
        unreachable[field] += sum(count for (answer, present), count in answers.items() if present and answer != majority)
    total = {kind: sum(counter.values()) for kind, counter in counts.items()}
    precision, recall, score = f1(total["hit"], total["given"], total["wanted"])
    report = {"authors": len(records), "skipped_over_cap": capped, "failed_labels": failed, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(score, 4),
              "ceiling": round(total["present"] / total["wanted"], 4),
              "reachable": round((total["present"] - sum(unreachable.values())) / total["wanted"], 4) if part == "train" else None,
              "authors_per_second": round(len(records) / seconds),
              **{kind: total[kind] for kind in ("hit", "silent", "extra", "different", "wanted", "given")},
              "fields": {field: {"f1": round(f1(counts["hit"][field], counts["given"][field], counts["wanted"][field])[2], 4),
                                 "wanted": counts["wanted"][field], "silent": counts["silent"][field], "extra": counts["extra"][field],
                                 "different": counts["different"][field],
                                 "ceiling": round(counts["present"][field] / counts["wanted"][field], 4) if counts["wanted"][field] else None,
                                 "reachable": round((counts["present"][field] - unreachable[field]) / counts["wanted"][field], 4)
                                 if counts["wanted"][field] and part == "train" else None}
                         for field in sorted(counts["wanted"], key=counts["wanted"].get, reverse=True)}}
    LOG.info("evaluate %s %s %s", dataset, part, json.dumps({key: value for key, value in report.items() if key != "fields"}))
    for field, values in report["fields"].items():
        LOG.info("field %s %s", field, json.dumps(values))
    return report
