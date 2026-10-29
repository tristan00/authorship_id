# Claim consolidation

Consolidation turns an author's claim evidence into at most one value per attribute. `rules.consolidate` does this. Production (`consolidate.py`) and evaluation (`evaluate.py`) call the same function, and it does not depend on the order of the evidence.

## Evidence

An author's evidence is one `(source, field, value)` per text claim (`text_claims` joined to `texts`) and one per distinct flair claim, matched on subreddit and flair text (`flair_claims`). The sampler writes the same evidence as lines `source field: value`, shuffled per author and capped at `CLAIM_LINES`. Production uses all of an author's evidence; evaluation uses the lines the labeler saw.

## Commands

```
python -m claim_consolidation sample --month 2026-03 --dataset author_200k --authors 200000
python -m claim_consolidation labels --month 2026-03 --dataset author_200k
python -m claim_consolidation evaluate --month 2026-03 --dataset author_200k --split validation
python -m claim_consolidation consolidate
```

`sample` draws authors with at least `MIN_CLAIMS` claims, excluding authors already in other datasets of the month, and writes `records.jsonl`. The records are annotated with `LABEL_MODEL` and the prompt `LABEL_PROMPT` from `prompts.py`, served through `local_annotator.serve.running`, into `runs/<model>/<prompt>.jsonl` next to the records. `labels` parses those answers into `labels.jsonl`, keeping each raw answer. It first strips one echoed leading `text ` or `flair ` from each answer line, then applies `claim_extraction.normalize.parse`. `evaluate` scores the rules against the labels on `train` or `validation`; it refuses `test`. `consolidate` rebuilds `claim_evidence` and `author_claims` for every loaded month.

## Evaluation

Scores are micro precision, recall and F1 over `(author, field, value)`. Misses split three ways:

- silent: the rules give nothing where the label has a value;
- extra: the rules give a value where the label has none;
- different: both have a value and the values differ.

`ceiling` is the share of label values that occur in the author's input. `reachable`, on train only, is the ceiling minus label values in tied fields that gemma's majority answer for authors with the same value counts still gets wrong. It is optimistic and does not depend on the rules.

## Rules

The value with the most claims wins. Ties are broken only as follows; otherwise the field is left empty.

- age:
  1. the tied age consistent with the resolved birth year, within one year;
  2. the tied ages consistent with the resolved generation;
  3. adults (18 or more) over minors;
  4. of two remaining ages, the lower one when it is at least `OLDER` and the gap is at least `GAP`, otherwise the higher one. Three or more remaining ages leave age empty.
- birth year: the tied year consistent with the resolved age. generation: the tied generation consistent with the resolved birth year or age.
- country and state: a tied country containing the resolved state, or a tied state inside the resolved country (`normalize.REGIONS`), for residence and for origin.
- nationality and origin country: the tied value equal to the other field's resolved value.
- gender: female when the resolved orientation is lesbian.
- height, weight, income: the higher value.
- `PREFER` pairs: a tied value wins only if it beats every other tied value.

## Tie policy

Each `PREFER` pair needs gemma to agree with it in at least 60% of at least 30 two-way train ties. Pairs in sensitive fields (race_ethnicity, religion, sexual_orientation, gender, nationality, origin fields) also need a reason about the author. Pairs without one leave the tie unbroken. Base rates are not a reason, and neither is the position of a line in the shuffled input.

| field | pair | reason |
|---|---|---|
| education | higher degree over lower | accumulation |
| gender | non-binary over male, female | markedness |
| sexual_orientation | bisexual over gay, lesbian, straight | specificity |
| sexual_orientation | queer over gay, lesbian | markedness |
| religion | atheist, agnostic over a religion | change over time |
| religion | atheist, agnostic over no religion | specificity |
| race_ethnicity | multiracial over a single race | specificity |
| occupation | any listed category over management | specificity |
| employment_status | self-employed over employed; employed over unemployed, retired | gemma preference |
| relationship_status | married over single; in a relationship over single; married, engaged over in a relationship | gemma preference |
| marital_status | married over divorced | gemma preference |
| parental_status | parent over no children | gemma preference |
