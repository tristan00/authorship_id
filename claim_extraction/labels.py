import json
import zlib
from collections import Counter

from . import LOG, timed
from .config import ANNOTATIONS, SPLITS
from .normalize import parse


def split(record_id):
    bucket = zlib.crc32(str(record_id).encode()) % 100
    return next(name for name, upper in SPLITS if bucket < upper)


def vote(ballots):
    resolved = {}
    for field in {field for ballot in ballots for field in ballot}:
        ranked = Counter(ballot.get(field) for ballot in ballots).most_common(2)
        winner, support = ranked[0]
        if winner is not None and support >= 2 and support > (ranked[1][1] if len(ranked) > 1 else 0):
            resolved[field] = winner
    return resolved


def examples(month, dataset, split):
    root = ANNOTATIONS / month / dataset
    labels = {row["id"]: row["values"] for row in map(json.loads, open(root / "labels.jsonl", encoding="utf-8")) if row["split"] == split}
    for row in map(json.loads, open(root / "records.jsonl", encoding="utf-8")):
        if row["id"] in labels:
            yield row["id"], row["text"], labels[row["id"]]


def read_voter(directory):
    answers = {}
    for path in sorted(directory.glob("[0-9][0-9].jsonl")):
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            answers[row["id"]] = parse(row["answer"])
    LOG.info("voter %s answers=%d", directory.name, len(answers))
    return answers


@timed
def labels(month, dataset):
    root = ANNOTATIONS / month / dataset
    voters = {directory.name: read_voter(directory) for directory in sorted((root / "voters").iterdir())}
    ids = [json.loads(line)["id"] for line in open(root / "records.jsonl", encoding="utf-8")]
    missing = [name for name, answers in voters.items() if len(answers) != len(ids)]
    if missing:
        raise ValueError(f"voters without every record: {missing}")
    fields, splits = Counter(), Counter()
    with open(root / "labels.jsonl", "w", encoding="utf-8") as out:
        for record_id in ids:
            values = vote([answers[record_id] for answers in voters.values()])
            fields.update(values.keys())
            splits[split(record_id), bool(values)] += 1
            out.write(json.dumps({"id": record_id, "split": split(record_id), "values": values}, ensure_ascii=False) + "\n")
    report = {"voters": {name: sum(map(len, answers.values())) for name, answers in voters.items()}, "fields": dict(fields.most_common()),
              "splits": {f"{name} {'with' if positive else 'without'} values": count for (name, positive), count in sorted(splits.items())}}
    (root / "labels_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    LOG.info("labels %s", report)
