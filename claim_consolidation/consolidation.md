# Claim consolidation

Consolidation turns an author's claim evidence into at most one value per attribute. `rules.consolidate` does this. Production (`consolidate.py`) and evaluation (`evaluate.py`) call the same function, and it does not depend on the order of the evidence.

## Evidence

An author's evidence is one `(source, subreddit, field, value)` per text claim (`text_claims` joined to `records` on the text hash) and one per distinct flair claim, matched on subreddit and flair text (`flair_claims`). Records whose author is exactly one of `database.NO_AUTHOR` ('', '[deleted]', '[removed]') give no evidence. `consolidate.EVIDENCE` builds `claim_evidence`, and the sampler reads its eligible authors and their evidence from that table, so `sample --month` requires the current consolidation to cover exactly that month. The sampler writes two files per dataset:

- `records.jsonl`, the annotator input: per author, lines `r/subreddit source field: value`, shuffled per author and capped at `CLAIM_LINES`;
- `claims.jsonl`, the same evidence uncapped and sorted: `{"id", "claims": [[source, subreddit, field, value], ...]}`.

Rule work reads `claims.jsonl` and the labels only, never `records.jsonl`, so nothing depends on the order the annotator saw.

## Commands

```
python -m claim_consolidation sample --month 2026-03 --dataset author_8plus --min-claims 8 --authors 500000
python -m claim_consolidation labels --month 2026-03 --dataset author_8plus
python -m claim_consolidation fit --month 2026-03 --dataset author_8plus
python -m claim_consolidation evaluate --month 2026-03 --dataset author_8plus --split validation
python -m claim_consolidation consolidate
```

`sample` draws at most `--authors` authors with at least `--min-claims` claims, excluding authors already in other datasets of the month. The records are annotated with `LABEL_MODEL` and the prompt `LABEL_PROMPT` from `prompts.py`, served through `local_annotator.serve.running`, into `runs/<model>/<prompt>.jsonl` next to the records. `labels` parses those answers into `labels.jsonl`, keeping each raw answer. It first strips an echoed leading `r/subreddit ` and `text ` or `flair ` from each answer line, then applies `claim_extraction.normalize.parse`. `evaluate` scores the rules against the labels on `train` or `validation`. Validation holds the authors that `claim_extraction.labels.split` puts in validation or test; consolidation has no test part. It skips authors with more than `CLAIM_LINES` claims, whose evidence the annotator saw only in part. `consolidate` rebuilds `claim_evidence` and `author_claims` for every loaded month.

## Evaluation

Scores are micro precision, recall and F1 over `(author, field, value)`. Misses split three ways:

- silent: the rules give nothing where the label has a value;
- extra: the rules give a value where the label has none;
- different: both have a value and the values differ.

`ceiling` is the share of label values that occur in the author's claims. `reachable`, on train only, is the ceiling minus label values in tied fields that gemma's majority answer for authors with the same value counts still gets wrong. It is optimistic and does not depend on the rules.

## Rules

The value with the most claims wins. Ties are broken only as follows; otherwise the field is left empty.

- age: adults (18 or more) over minors. Of two remaining ages, the lower one when it is at least `OLDER` and the gap is at least `GAP`, otherwise the higher one. Of an odd number of three or more, the median. An even number of four or more leaves age empty.
- birth year: the tied year consistent with the resolved age, within one year.
- country and state: a tied country containing the resolved state, or a tied state inside the resolved country (`normalize.REGIONS`), for residence and for origin.
- nationality and origin country: the tied value equal to the other field's resolved value.
- gender: female when the resolved orientation is lesbian.
- height, weight, income: the higher of two tied values. Of an odd number of three or more, the median for height and weight; income is left empty, as are even numbers of four or more.
- any other field: fitted tie strengths, below.

## Tie strengths

`fit` reads the train labels and claims and writes `STRENGTHS`, which `rules` and production load. For each non-numeric field, a value's strength is how often gemma chose it when it was tied: wins plus `STRENGTH_PRIOR` over ties plus twice `STRENGTH_PRIOR`. A subreddit-specific strength exists for each subreddit and value seen in at least `SUBREDDIT_SUPPORT` train ties. It is that subreddit's win rate, smoothed toward the value's strength with weight `SUBREDDIT_WEIGHT`. A tied value scores the mean strength over the distinct subreddits of its claims. A value never seen tied scores 0.5. The highest score wins only if it is strictly higher than the next.

## Choosing rules

Rules and their constants are fit on train and kept only if they raise validation micro F1. Rules use preferences over values, cross-field consistency and subreddit evidence. They use no tables keyed by author or by an author's exact value counts, and never the order of lines in the annotator input.
