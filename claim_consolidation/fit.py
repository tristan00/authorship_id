import json
from collections import Counter, defaultdict

from claim_extraction.config import ANNOTATIONS

from . import LOG, timed
from .config import CLAIM_LINES, STRENGTH_PRIOR, STRENGTHS, SUBREDDIT_SUPPORT, SUBREDDIT_WEIGHT
from .evaluate import part, rows
from .rules import NUMERIC, leaders


@timed
def fit(month, dataset):
    root = ANNOTATIONS / month / dataset
    labels = {row["id"]: row["values"] for row in rows(root / "labels.jsonl") if part(row["id"]) == "train" and row["error"] is None}
    wins, seen, local_wins, local_seen, authors = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), 0
    with open(root / "claims.jsonl", encoding="utf-8") as stream:
        for row in map(json.loads, stream):
            if row["id"] not in labels or len(row["claims"]) > CLAIM_LINES:
                continue
            authors += 1
            truth, counts, sources = labels[row["id"]], defaultdict(Counter), defaultdict(set)
            for _, subreddit, field, value in row["claims"]:
                counts[field][value] += 1
                sources[field, value].add(subreddit)
            for field, found in counts.items():
                if field in NUMERIC or len(tied := leaders(found)) < 2:
                    continue
                for value in tied:
                    seen[field][value] += 1
                    wins[field][value] += truth.get(field) == value
                    for subreddit in sources[field, value]:
                        local_seen[field][subreddit, value] += 1
                        local_wins[field][subreddit, value] += truth.get(field) == value
    values = {field: {value: (wins[field][value] + STRENGTH_PRIOR) / (count + 2 * STRENGTH_PRIOR) for value, count in counted.items()}
              for field, counted in seen.items()}
    subreddits = defaultdict(lambda: defaultdict(dict))
    for field, counted in local_seen.items():
        for (subreddit, value), count in counted.items():
            if count >= SUBREDDIT_SUPPORT:
                subreddits[field][subreddit][value] = (local_wins[field][subreddit, value] + SUBREDDIT_WEIGHT * values[field][value]) / (count + SUBREDDIT_WEIGHT)
    STRENGTHS.write_text(json.dumps({"month": month, "dataset": dataset, "values": values, "subreddits": subreddits}, ensure_ascii=False), encoding="utf-8")
    LOG.info("fit dataset=%s authors=%s values=%s subreddit_values=%s path=%s", dataset, authors, sum(map(len, values.values())),
             sum(len(found) for fields in subreddits.values() for found in fields.values()), STRENGTHS)
