import json
import re
from collections import Counter

from claim_extraction.config import ANNOTATIONS
from claim_extraction.normalize import parse

from . import LOG, timed
from .config import LABEL_MODEL, LABEL_PROMPT

ECHO = re.compile(r"^(?:r/\S+ )?(?:text |flair )?", re.M)


@timed
def labels(month, dataset):
    root = ANNOTATIONS / month / dataset
    with open(root / "runs" / LABEL_MODEL / f"{LABEL_PROMPT}.jsonl", encoding="utf-8") as stream:
        answers = {row["id"]: row for row in map(json.loads, stream)}
    with open(root / "claims.jsonl", encoding="utf-8") as stream:
        authors = [json.loads(line)["id"] for line in stream]
    rows, lines, parsed, fields = [], 0, 0, Counter()
    for author in filter(answers.__contains__, authors):
        answer = answers[author]
        text = ECHO.sub("", answer["answer"]) if answer["error"] is None else ""
        for line in filter(str.strip, text.splitlines()):
            lines += 1
            parsed += bool(parse(line))
        values = parse(text)
        fields.update(values.keys())
        rows.append({"id": author, "values": values, "error": answer["error"], "answer": answer["answer"]})
    (root / "labels.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    LOG.info("labels dataset=%s authors=%s unanswered=%s errors=%s with_values=%.4f line_parse_rate=%.4f values=%s fields=%s", dataset, len(rows),
             len(authors) - len(rows), sum(row["error"] is not None for row in rows), sum(bool(row["values"]) for row in rows) / len(rows), parsed / lines,
             sum(fields.values()), dict(fields.most_common()))
