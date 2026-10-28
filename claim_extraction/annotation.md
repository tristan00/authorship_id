# Claims annotation

Labels for measuring text self-claim extraction come from three local LLM voters served by vLLM through the separate `D:\local_annotator` package, driven by `label1m.py`. `claim_extraction/annotation.json` defines the fields and their value sets; `normalize.py` maps every voter answer onto them. The voters do not use the prompt in `annotation.json`.

## Pipeline

1. Load a month into the database (`python -m database add --months YYYY-MM`).
2. Sample texts into a dataset: `python -m claim_extraction sample --month 2026-03 --datasets panel1m`
3. Label it with `label1m.py` (see below), which writes one answer file per voter and shard.
4. Vote the answers into labels: `python -m claim_extraction labels --month 2026-03 --datasets panel1m`
5. Fit the candidate scorer on the train splits of one or more datasets, written to `D:\reddit_data\models\claim_extraction.json`:
   `python -m claim_extraction fit --month 2026-03 --datasets panel1m panel1m_b`
6. Score the extractor on one split of each dataset, written to `<month>/evaluations/<dataset>_<split>.json`:
   `python -m claim_extraction evaluate --month 2026-03 --datasets panel1m panel1m_b --split validation`

## Datasets

Each dataset lives in `D:\reddit_data\annotations\<month>\<dataset>\`:

| file | content |
|---|---|
| `records.jsonl` | `{"id", "text"}` per text |
| `voters/<model>.<prompt>/NN.jsonl` | one shard of a voter's raw answers, `{"id", "answer", "error", "retried", "seconds"}` |
| `voters/<model>.<prompt>/NN.timing.json` | the shard's record count, rate and errors; its presence marks the shard done |
| `labels.jsonl` | `{"id", "split", "values": {field: value}}` per text |
| `labels_report.json` | values per voter, resolved values per field, texts with and without values per split |

Sampling draws random readable texts of the month (body or title only) of at most 10,000 UTF-8 bytes. Splits are fixed per record id (`crc32(id) % 100`): train below 90, validation below 95, test the rest.

| dataset | texts | use |
|---|---|---|
| `panel1m` | 999,865 | train for rule development, validation for metrics only, test held out to the end |
| `panel1m_b` | 1,000,000 | second sample of the same month, disjoint from `panel1m`, same voters and splits |
| `panel40k` | 40,000 | earlier pilot; its `labels.jsonl` predates `normalize.py` |

`panel1m` has 33,186 train, 1,899 validation and 1,981 test texts with at least one resolved value; `panel1m_b` has 32,507, 1,841 and 1,763. Resolved counts per field in `panel1m_b` are within 8% of `panel1m` for every field with more than 1,000 labels, except parental status (−15%). Smaller fields differ by up to 25% (relationship status −24%, origin state −25%, generation −20%, income +13%), mostly because gemma4-12b recall on them changes between servers (see below).

## Labeling

`label1m.py <dataset>` runs each voter over the dataset in shards of 50,000 records, one accepted vLLM server start per voter, and skips shards that already have a timing file, so a stopped run resumes at the first missing shard. It currently lives in the benchmark scratch directory next to `bench.py`, `clean.py` and `prompts.py`, outside this repository.

| voter | prompt | rate on panel1m |
|---|---|---|
| `gemma4-26b-a4b-nvfp4` | `tail`: named fields, metric and imperial height, no prose | about 460 texts/s per shard |
| `qwen3-4b-2507-fp8` | `only_set`: named fields, only fields with a value | about 620 texts/s per shard |
| `gemma4-12b-nvfp4` | `units`: plain field names, age in years, height in cm, weight in kg, income in yearly USD | about 128 texts/s per shard |

Prompts ask for "the author's explicitly stated current facts about themselves, as field: value lines, or none", followed by the field list. Answers are free text, not constrained decoding.

Hard failures, never partial output:

- vLLM runs at 0.80 GPU memory utilization. At 0.85 the WSL VM filled the 32 GB card, spilled 0.77 GB into Windows shared memory and dropped gemma4-12b from 128 to about 9 texts/s while the GPU still reported 100% use.
- Every 2,000 records and between shards, the run stops if shared GPU memory exceeds 256 MiB (about 40 MiB at idle).
- A shard that exceeds its time limit raises instead of writing a truncated shard with a timing file.

### Per-start variance of gemma4-12b

gemma4-12b answers a text without claims either with a bare `none` or with every field listed as `none`. Which one it prefers is fixed for the life of one vLLM server and changes between starts. On the same first 2,000 panel1m records, with identical prompt, sampling, weights and vLLM install, nineteen starts gave a mean answer length from 88 to 433 characters (panel1m: 161) and from 51 to 150 texts/s. The spread is the same at 0.80 and 0.85 GPU memory, with and without FlashInfer autotuning, with a fresh autotune cache and without prefix caching, so no single setting pins it. Small per-start numeric differences likely flip a near-tie on the first output tokens.

The style does not change the labels. A list of `none` lines parses to `none`, and every start agrees with the panel1m answers on 1,947 to 1,962 of the 2,000 parsed labels, long or short style alike. On the 88 of those texts where the panel1m answer has values, every start agrees on only 46 to 62, so gemma4-12b labels vary that much between any two servers. Over whole shards the per-field rate moves too: panel1m's own two gemma4-12b servers (shards 00-13 and 14-19) found 1,737 and 1,404 relationship status values per million texts, 464 and 263 generation and 621 and 267 birth year, while gemma4-26b stays within a few percent across servers.

`label1m.py` therefore gates each server start for speed and sanity. It replays the first 2,000 panel1m records and accepts the server only at 97% parsed label agreement with the voter's panel1m answers and at least 100 texts/s; otherwise it restarts, up to 20 times, then raises. Each attempt logs answer length, rate and agreement, and all remaining shards of the voter run on the accepted server. panel1m_b gemma4-12b shards 00-09 come from a long-style server at about 68 texts/s, and 10-19 from a gated one. The gemma4-26b and qwen3-4b answers did not drift between panel1m and panel1m_b (bare `none` share 0.95 and 0.97 on every shard of both).

## Normalization and voting

`normalize.parse` reads one answer: it maps the prompt-specific keys (`age_years`, `job_title`, `height_imperial`, `hourly_wage_usd`, ...) to the fields, then each value onto the field's value set: numbers within `config.NUMERIC` with unit conversion (feet and inches, pounds, stone, hourly times 2080, monthly times 12), closed sets through synonym tables, countries through aliases and demonyms, first-level regions through abbreviations and a region list, occupation and study subject through keyword patterns onto the SOC and CIP groups. Values with notes, guesses ("implied", "inferred"), past states, plans or ranges are dropped, as are answers with more than 12 values.

`labels.vote` resolves a field when one answer (a value, or none) has at least two of the three votes and more votes than any other answer. There is no tiebreaker; unresolved fields are left out of `values` and count as negatives.

## Rules extractor

`rules.extract` lowercases the text, removes quoted lines, quoted strings of six characters or more and links, and maps curly primes to `'` and `"`. It then collects candidates, scores each with one linear model, and keeps per field the best candidate whose score clears that field's cutoff.

Candidates come from three kinds of sources, up to three matches per pattern:

- patterns: age and gender tags (`28F`, `m24`, `[M4F]`, `[m4r]`, `32 straight man`, `male, 23`, `[F] 19`), a two-digit age at the start of the text or in brackets, heights in feet and inches, centimetres or metres, and weights;
- phrases: first-person patterns per field (`PHRASES`), with places matched against countries, first-level regions and `cities.json` and occupations against `jobs.json` and a list of job nouns;
- broad mentions: any vocabulary word of a field anywhere in the text (gender words, countries, demonyms, regions, cities, languages, race, orientation, religion, marital, relationship, employment, mental health, ideology, generation, `jobs.json` titles, degrees, study subjects, "my son", "pregnant", ...), and any standalone two-digit number for age. Vocabulary is read in sorted order so the per-field cap of four mentions, and with it the fit, does not depend on string hashing.

Conditions that used to discard a match are flags instead: hypothetical context before a phrase ("if", "would", "used to be", ...), another person mentioned before a height or weight, and a text that is only a tag (`M35`, whose gender the voters rarely label). The first unflagged pattern or phrase candidate of a field, which is what first-match rules would return, is marked `pick`.

Features per candidate: source, kind, `pick`, rank, position, how many candidates share the value, how many values compete, text length and line count, the bare-tag flag, the fields that have candidates, the value for categorical fields, the two tokens before and one after the match, the four tokens on each side as a bag, and whether a first-person word ("i", "my", "me", ...) is among the four before. Every feature appears both on its own and crossed with the field, so small fields share the general weights; source-specific features are also crossed with the source.

`fit` trains one logistic regression over all candidates of the train splits of the given datasets (features seen at least 3 times). The regularization C and a global probability threshold are chosen by 3-fold cross-validation on train for micro F1. Each field then gets the cutoff at or below that threshold that maximizes its own out-of-fold F1, so low-F1 fields keep candidates that help them. The weights are stored outside the repository as a model artifact.

`jobs.json` is built from panel1m train labels and voter answers. `cities.json` is the GeoNames `cities15000` names plus city labels seen at least twice in panel1m train, without names of three letters or less, names that appear lowercase in panel1m train text at least half as often as capitalized, and names whose train precision is below 0.34 over at least two false positives.

The current weights are fitted on panel1m and panel1m_b train (1,799,903 texts, 105,245 labels). Cross-validation chose C = 0.3 and a threshold of 0.4 (out-of-fold micro F1 0.743); on panel1m train alone it chose the same (0.735).

| validation split | texts with values | panel1m model | combined model |
|---|---|---|---|
| panel1m | 1,899 | 0.740 | 0.743 |
| panel1m_b | 1,841 | 0.734 | 0.741 |

Validation F1 by field: first-match rules (commit 88718f3), the model fitted on panel1m train, and the model fitted on both train splits. Fields are ordered by panel1m train label count.

| field | panel1m train labels | panel1m validation labels | rules | panel1m model | combined model | panel1m_b validation labels | panel1m model | combined model |
|---|---|---|---|---|---|---|---|---|
| age | 20800 | 1188 | 0.84 | 0.88 | 0.88 | 1165 | 0.89 | 0.89 |
| gender | 13133 | 768 | 0.68 | 0.75 | 0.75 | 731 | 0.74 | 0.74 |
| residence_city | 2497 | 137 | 0.37 | 0.54 | 0.54 | 146 | 0.56 | 0.55 |
| marital_status | 1836 | 92 | 0.50 | 0.62 | 0.58 | 108 | 0.56 | 0.59 |
| residence_country | 1678 | 110 | 0.44 | 0.49 | 0.53 | 98 | 0.50 | 0.53 |
| occupation | 1455 | 94 | 0.49 | 0.60 | 0.58 | 75 | 0.47 | 0.51 |
| residence_state | 1325 | 72 | 0.42 | 0.52 | 0.57 | 66 | 0.55 | 0.57 |
| parental_status | 1284 | 59 | 0.40 | 0.42 | 0.39 | 56 | 0.46 | 0.46 |
| height | 1198 | 58 | 0.86 | 0.91 | 0.91 | 64 | 0.81 | 0.83 |
| race_ethnicity | 1167 | 82 | 0.60 | 0.74 | 0.79 | 65 | 0.73 | 0.73 |
| nationality | 1117 | 66 | 0.52 | 0.56 | 0.58 | 78 | 0.54 | 0.55 |
| sexual_orientation | 1071 | 71 | 0.46 | 0.63 | 0.66 | 53 | 0.67 | 0.70 |
| relationship_status | 612 | 30 | 0.38 | 0.39 | 0.41 | 28 | 0.37 | 0.26 |
| employment_status | 594 | 28 | 0.00 | 0.26 | 0.36 | 23 | 0.30 | 0.31 |
| weight | 533 | 41 | 0.78 | 0.85 | 0.85 | 24 | 0.73 | 0.73 |
| origin_country | 456 | 39 | 0.33 | 0.43 | 0.43 | 30 | 0.63 | 0.63 |
| mental_health | 390 | 22 | 0.50 | 0.48 | 0.51 | 24 | 0.51 | 0.50 |
| religion | 349 | 32 | 0.40 | 0.52 | 0.56 | 22 | 0.61 | 0.67 |
| education_subject | 281 | 13 | 0.48 | 0.58 | 0.41 | 19 | 0.41 | 0.51 |
| income | 274 | 15 | 0.19 | 0.19 | 0.19 | 14 | 0.35 | 0.35 |
| birth_year | 240 | 11 | 0.70 | 0.70 | 0.70 | 15 | 0.48 | 0.48 |
| generation | 197 | 8 | 0.17 | 0.53 | 0.50 | 10 | 0.57 | 0.70 |
| education | 150 | 6 | 0.22 | 0.29 | 0.25 | 16 | 0.36 | 0.40 |
| origin_city | 141 | 10 | 0.14 | 0.14 | 0.14 | 5 | 0.44 | 0.40 |
| language | 128 | 4 | 0.50 | 0.40 | 0.44 | 11 | 0.57 | 0.57 |
| origin_state | 115 | 7 | 0.67 | 0.67 | 0.67 | 7 | 0.60 | 0.60 |
| political_ideology | 63 | 2 | 0.00 | 0.00 | 0.00 | 3 | 0.00 | 0.00 |

panel1m_b labels relationship status 24% less often per train text than panel1m (5.1 against 6.8 per 10,000) and parental status 16% less, from per-server voter variance. The combined model learns the lower rate, which is why relationship status drops on both validation splits.

political_compass has no resolved labels. Across panel1m the voters mostly answer it with values outside its value set ("left", "center-left", "not stated"); the in-set forms ("centrist", "center", "lib-right") already map in `normalize.py`, occur 14 times over all three voters, and never twice on the same text.

## Limitations

- Labels are majority votes of three models, not ground truth.
- The voters often leave gender out of bare tags such as "M32" (gemma4-12b and qwen3-4b give only the age): gender is labeled on 14% of texts that are only a tag. Against the majority labels, gemma4-12b and gemma4-26b each score about 0.83 micro F1 on train and qwen3-4b 0.64.
- Countries are rarely labeled when only a state or city is stated (the United States in 56 of 743 such train texts), so the extractor does not derive one from the other.
- Employment status, income, birth year, generation, education, language and the political fields have fewer than 30 panel1m validation labels each, so their validation F1 moves by whole texts: language's 0.50 to 0.44 is one false positive.
