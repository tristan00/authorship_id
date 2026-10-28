# Claims annotation

Labels for measuring text self-claim extraction come from three local LLM voters served by vLLM through the separate `D:\local_annotator` package, driven by `label1m.py`. `claim_extraction/annotation.json` defines the fields and their value sets; `normalize.py` maps voter answers onto them where an answer is a known form of a value and otherwise keeps the voter's value. The voters do not use the prompt in `annotation.json`.

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

Sampling draws random readable texts of the month (body or title only) of at most 10,000 UTF-8 bytes, leaving out every id already in a dataset of that month, and raises if the table sample holds fewer than it needs. Splits are fixed per record id (`crc32(id) % 100`): train below 90, validation below 95, test the rest. `--splits validation test` keeps only ids whose split is listed and draws 100,000 texts per listed split, scaling the table sample to the narrowest split: `python -m claim_extraction sample --month 2026-03 --datasets panel200k --splits validation test`

| dataset | texts | use |
|---|---|---|
| `panel1m` | 999,865 | train for rule development, validation for metrics only, test held out to the end |
| `panel1m_b` | 1,000,000 | second sample of the same month, disjoint from `panel1m`, same voters and splits |
| `panel200k` | 200,000 | 100,000 validation and 100,000 test texts of the same month, disjoint from every other dataset, same voters |
| `panel40k` | 40,000 | earlier pilot; its `labels.jsonl` predates `normalize.py` |

`panel1m` has 33,186 train, 1,899 validation and 1,981 test texts with at least one resolved value; `panel1m_b` has 32,507, 1,841 and 1,763. Resolved counts per field in `panel1m_b` are within 8% of `panel1m` for every field with more than 1,000 labels, except parental status (−15%). Smaller fields differ by up to 25% (relationship status −24%, origin state −25%, generation −20%, income +13%), mostly because gemma4-12b recall on them changes between servers (see below).

`panel200k` has 3,780 validation and 3,739 test texts with at least one resolved value, 376 per 10,000 texts against 388 and 361 on the validation and test splits of `panel1m` and `panel1m_b`. Per 10,000 texts, its resolved counts are within 5% of those two splits pooled for age, gender, residence city, residence country, occupation, race and ethnicity, sexual orientation, nationality and height. They are higher for residence state (+26%), relationship status (+23%), parental status (+17%) and marital status (+11%) and lower for origin country (−26%) and religion (−20%). gemma4-26b, whose rates hold across servers, also finds residence state 21% more often than on those splits, so at least that difference comes from the texts, not from voter drift.

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

`label1m.py` therefore gates each server start for speed and sanity. It replays the first 2,000 panel1m records and accepts the server only at 97% parsed label agreement with the voter's panel1m answers and at least 100 texts/s; otherwise it restarts, up to 20 times, then raises. Each attempt logs answer length, rate and agreement, and all remaining shards of the voter run on the accepted server. panel1m_b gemma4-12b shards 00-09 come from a long-style server at about 68 texts/s, and 10-19 from a gated one. All panel200k gemma4-12b shards come from one gated server, accepted on its second start (1,960/2,000 agreement, 145 texts/s, after a first start at 98 texts/s); gemma4-26b and qwen3-4b passed on their first start. The gemma4-26b and qwen3-4b answers did not drift between panel1m and panel1m_b (bare `none` share 0.95 and 0.97 on every shard of both).

## Normalization and voting

`normalize.parse` reads one answer. The voters are the reference: parsing only unifies formats and never drops a categorical value a voter gave. It splits lines that hold several `field: value` pairs, maps the prompt-specific keys (`age_years`, `job_title`, `height_imperial`, `hourly_wage_usd`, ...) and misspelled race keys to the fields, and keeps the first answer per field. A value is lowercased and stripped of markdown, quotes, surrounding brackets, parenthetical notes and trailing punctuation. Blanks (`none`, `n/a`, `unknown`, "not stated", "not explicitly stated", template echoes such as `[value]`) give no value. Numbers are converted to one unit (feet and inches, inches, pounds, stone, hourly times 2080, monthly times 12) without plausibility bounds; a numeric answer that is not a single number ("30s", "18+", "tall", "25, 27") gives no value. A categorical value that is a known form of a value-set entry maps onto it (synonym tables, country aliases and demonyms, region abbreviations, keyword patterns onto the SOC and CIP groups for occupation and study subject); any other value is kept as the voter wrote it. Mental health keeps the first condition named.

Over panel1m, panel1m_b and panel200k this gives 141,609 resolved labels, against 129,324 from the earlier parser that dropped unknown values, values with notes and numbers outside `config.NUMERIC`. 8,143 labels are outside the value sets (marital status "single", orientation "m4m", mental health "depressed", ...) and 1,878 numbers are outside `config.NUMERIC`, the range in which `demographic_model` encodes numeric targets; extractor candidates use `config.CANDIDATE_BOUNDS` instead. 10,098 of 183,249 numeric answers are not a single number.

`labels.vote` resolves a field when one answer (a value, or none) has at least two of the three votes and more votes than any other answer. There is no tiebreaker; unresolved fields are left out of `values` and count as negatives.

## Rules extractor

`rules.extract` turns an uppercase `US` into `USA`, lowercases the text, drops zero-width characters, removes quoted lines, quoted strings of six characters or more (not starting at an inch mark such as `6'4"`) and links, and maps curly primes to `'` and `"`. It then collects candidates, scores each with one linear model, and keeps per field the best candidate whose score clears that field's cutoff.

Candidates come from three kinds of sources, up to three matches per pattern:

- patterns: age and gender tags (`28F`, `m24`, `[M4F]`, `m4f27`, `[m4r]`, `32 straight man`, `male, 23`, `[F] 19`), a two-digit age at the start of the text or in brackets, a text that is only a number, ages written as words ("nineteen", "sixty-six"), heights in feet and inches (also `5"3`, and `6ft` or `6 foot` before any word), centimetres or metres (`1,80`), weights, a unit-less weight right after a height (`5'9 150`, read as pounds from 100 up and as kilograms below), and flag emoji for countries;
- phrases: first-person patterns per field (`PHRASES`), with places matched against countries, first-level regions and `cities.json` and occupations against `jobs.json` and a list of job nouns;
- broad mentions: any vocabulary word of a field anywhere in the text (gender words, countries, demonyms, regions, cities, languages, race, orientation, religion, marital, relationship, employment, mental health, ideology, generation, `jobs.json` titles, degrees, study subjects, "my son", "my son's", "no kids", "mom", "my gf", "pregnant", ...), the voters' own values in `values.json`, any money amount for income, and any standalone two-digit number for age, also before a comma or full stop and with a `yo`/`yrs` suffix. Vocabulary is read in sorted order so the per-field cap of four mentions, and with it the fit, does not depend on string hashing. Numeric candidates are bounded by `config.CANDIDATE_BOUNDS`, which allows ages from 1 to 120 because the voters label ages below 13 (mostly texts that are only a number).

Conditions that used to discard a match are flags instead: hypothetical context before a phrase ("if", "would", "used to be", ...), another person mentioned before a height or weight, and a text that is only a tag (`M35`, whose gender the voters rarely label). The first unflagged pattern or phrase candidate of a field, which is what first-match rules would return, is marked `pick`.

Features per candidate: source, kind, `pick`, rank, position, how many candidates share the value, how many values compete, text length and line count, the number of first-person words in the text (0, 1-2, 3-7, 8 or more), the bare-tag flag, the fields that have candidates, the value for categorical fields, the two tokens before and one after the match, the four tokens on each side as a bag, and whether a first-person word ("i", "my", "me", ...) is among the four before. Every feature appears both on its own and crossed with the field, so small fields share the general weights; source-specific features are also crossed with the source.

`fit` trains one logistic regression over all candidates of the train splits of the given datasets (features seen at least 3 times). The regularization C and a global probability threshold are chosen by 3-fold cross-validation on train for micro F1. Each field then gets the cutoff at or below that threshold that maximizes its own out-of-fold F1, so low-F1 fields keep candidates that help them. The weights are stored outside the repository as a model artifact. Candidates are collected in `config.WORKERS` processes, each with its own feature table that the main process remaps, and the nine cross-validation fits run in parallel with the three full fits, one per C; on panel1m and panel1m_b train the whole fit takes about 3 minutes and `evaluate` about 5 seconds per validation split.

`jobs.json` is built from panel1m train labels and voter answers. `cities.json` is the GeoNames `cities15000` names plus city labels seen at least twice in panel1m train, without names of three letters or less, names that appear lowercase in panel1m train text at least half as often as capitalized, and names whose train precision is below 0.34 over at least two false positives, plus the 48 city labels seen at least twice in panel1m and panel1m_b train that this left out (Philadelphia, Pittsburgh, Calgary, Perth, Madrid, Tokyo, ...) unless they are written lowercase more than twice as often as capitalized, with a country or state when most of their labels name one.

`values.json` holds the label values outside the value sets (and, for occupation and study subject, outside the SOC and CIP groups) that occur at least twice among panel1m and panel1m_b train labels, have at least three characters, and match their field's train label in at least 1% of the train texts that mention them; the mention is a candidate with the voters' wording as its value (marital status "single", orientation "m4m", mental health "depressed", ...).

The weights are fitted on panel1m and panel1m_b train (1,799,903 texts, 115,285 labels, 1,579,150 candidates). Cross-validation chose C = 0.3 and a threshold of 0.35 (out-of-fold micro F1 0.720, against 0.713 before round 1). Pooled scores count the three validation splits together (13,211 labels); "before round 1" is the model fitted on the corrected labels before the candidate changes of rounds 1 and 2. Round 1 sorted validation misses into categories, so all three validation splits saw some rule work; from round 2 on, development reads train errors and out-of-fold scores only, and validation is used for scoring.

| validation micro F1 | panel1m | panel1m_b | panel200k | pooled |
|---|---|---|---|---|
| before round 1 | 0.713 | 0.708 | 0.701 | 0.706 |
| current | 0.721 | 0.712 | 0.709 | 0.713 |

Validation F1 by field on each split and pooled over all three (pooled precision 0.718, recall 0.708), with the pooled F1 before round 1. Fields are ordered by pooled validation label count.

| field | pooled labels | panel1m | panel1m_b | panel200k | pooled | before round 1 |
|---|---|---|---|---|---|---|
| age | 4853 | 0.87 | 0.87 | 0.87 | 0.87 | 0.86 |
| gender | 3090 | 0.75 | 0.74 | 0.75 | 0.74 | 0.74 |
| residence_city | 599 | 0.55 | 0.56 | 0.58 | 0.57 | 0.56 |
| occupation | 521 | 0.51 | 0.39 | 0.44 | 0.45 | 0.44 |
| marital_status | 457 | 0.59 | 0.57 | 0.64 | 0.61 | 0.58 |
| residence_country | 456 | 0.54 | 0.52 | 0.48 | 0.50 | 0.49 |
| sexual_orientation | 355 | 0.48 | 0.58 | 0.58 | 0.55 | 0.56 |
| race_ethnicity | 354 | 0.72 | 0.69 | 0.62 | 0.67 | 0.64 |
| residence_state | 350 | 0.60 | 0.52 | 0.57 | 0.57 | 0.55 |
| parental_status | 302 | 0.41 | 0.47 | 0.45 | 0.45 | 0.41 |
| nationality | 296 | 0.54 | 0.57 | 0.58 | 0.57 | 0.57 |
| height | 283 | 0.91 | 0.82 | 0.82 | 0.84 | 0.81 |
| mental_health | 151 | 0.52 | 0.50 | 0.49 | 0.50 | 0.43 |
| relationship_status | 133 | 0.41 | 0.33 | 0.19 | 0.28 | 0.28 |
| employment_status | 132 | 0.34 | 0.27 | 0.28 | 0.29 | 0.32 |
| origin_country | 128 | 0.46 | 0.57 | 0.35 | 0.44 | 0.43 |
| weight | 122 | 0.83 | 0.71 | 0.73 | 0.76 | 0.76 |
| religion | 109 | 0.52 | 0.65 | 0.46 | 0.52 | 0.51 |
| education | 107 | 0.21 | 0.44 | 0.30 | 0.31 | 0.24 |
| education_subject | 88 | 0.33 | 0.38 | 0.41 | 0.38 | 0.42 |
| income | 71 | 0.38 | 0.38 | 0.46 | 0.43 | 0.27 |
| generation | 55 | 0.44 | 0.67 | 0.44 | 0.51 | 0.49 |
| birth_year | 51 | 0.70 | 0.48 | 0.51 | 0.55 | 0.55 |
| language | 47 | 0.29 | 0.44 | 0.14 | 0.29 | 0.26 |
| origin_city | 37 | 0.12 | 0.40 | 0.25 | 0.24 | 0.18 |
| origin_state | 31 | 0.53 | 0.55 | 0.35 | 0.45 | 0.46 |
| political_ideology | 27 | 0.43 | 0.00 | 0.26 | 0.26 | 0.24 |
| political_compass | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

panel1m_b labels relationship status 24% less often per train text than panel1m (5.1 against 6.8 per 10,000) and parental status 16% less, from per-server voter variance. The combined model learns the lower rate, which is why relationship status drops on both validation splits.

political_compass has 35 resolved labels over the three datasets, 34 of them outside its value set ("left-leaning", "right leaning", "leftist").

## Limitations

- Labels are majority votes of three models, not ground truth.
- The voters often leave gender out of bare tags such as "M32" (gemma4-12b and qwen3-4b give only the age): gender is labeled on 14% of texts that are only a tag. Against the majority labels, gemma4-12b and gemma4-26b each score about 0.83 micro F1 on train and qwen3-4b 0.64.
- Countries are rarely labeled when only a state or city is stated (the United States in 56 of 743 such train texts), so the extractor does not derive one from the other.
- Income, birth year, generation, language, origin city, origin state and the political fields have fewer than 75 pooled validation labels each (political_compass 6), so their validation F1 moves by a few texts per change.
