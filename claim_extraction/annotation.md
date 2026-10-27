# Claims annotation

Labels for measuring text self-claim extraction come from three local LLM voters served by vLLM through the separate `D:\local_annotator` package, driven by `label1m.py`. `claim_extraction/annotation.json` defines the fields and their value sets; `normalize.py` maps every voter answer onto them. The voters do not use the prompt in `annotation.json`.

## Pipeline

1. Load a month into the database (`python -m database add --months YYYY-MM`).
2. Sample texts into a dataset: `python -m claim_extraction sample --month 2026-03 --datasets panel1m`
3. Label it with `label1m.py` (see below), which writes one answer file per voter and shard.
4. Vote the answers into labels: `python -m claim_extraction labels --month 2026-03 --datasets panel1m`
5. Score the rules extractor on one split, written to `<month>/evaluations/<dataset>_<split>.json`:
   `python -m claim_extraction evaluate --month 2026-03 --datasets panel1m --split validation`

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
| `panel40k` | 40,000 | earlier pilot; its `labels.jsonl` predates `normalize.py` |

`panel1m` has 33,186 train, 1,899 validation and 1,981 test texts with at least one resolved value.

## Labeling

`label1m.py` runs each voter over the dataset in shards of 50,000 records, one vLLM server start per voter, and skips shards that already have a timing file, so a stopped run resumes at the first missing shard. It currently lives in the benchmark scratch directory next to `bench.py`, `clean.py` and `prompts.py`, outside this repository.

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

## Normalization and voting

`normalize.parse` reads one answer: it maps the prompt-specific keys (`age_years`, `job_title`, `height_imperial`, `hourly_wage_usd`, ...) to the fields, then each value onto the field's value set: numbers within `config.NUMERIC` with unit conversion (feet and inches, pounds, stone, hourly times 2080, monthly times 12), closed sets through synonym tables, countries through aliases and demonyms, first-level regions through abbreviations and a region list, occupation and study subject through keyword patterns onto the SOC and CIP groups. Values with notes, guesses ("implied", "inferred"), past states, plans or ranges are dropped, as are answers with more than 12 values.

`labels.vote` resolves a field when one answer (a value, or none) has at least two of the three votes and more votes than any other answer. There is no tiebreaker; unresolved fields are left out of `values` and count as negatives.

## Rules extractor

`rules.extract` lowercases the text, removes quoted lines, quoted strings and links, and maps curly primes to `'` and `"`. It then applies, in order: age and gender tags (`28F`, `m24`, `[M4F]`, `[m4r]`, `32 straight man`, `male, 23`, `[F] 19`), a two-digit age at the start of the text or in brackets, standalone heights in feet and inches, centimetres or metres, weights when a height or age is present, then first-person phrase patterns per field. Places are matched against countries, first-level regions and `cities.json`; occupations against `jobs.json` and a list of job nouns. Vocabularies for religion, mental health, generation, ideology, orientation, race and languages come from the value tables in `normalize.py`; country names and demonyms from its country tables. Income reads hourly, weekly and monthly amounts and scales them to a year (2080, 52, 12). Bare weights without a unit are read as pounds from 100 and as kilograms below. Two-digit birth years (`born in 96`) become 19xx, and a text that is only a year from 1930 to 2013 (or a date in those years) is read as a birth year, which matches how the voters label such replies. Spanish, Portuguese, French, German and Italian forms are covered for age, gender, orientation and atheism. Names that are both a city and a first-level region resolve to the city when the labels mostly use the city (Delhi, New York, Berlin, Auckland and a few others).

`jobs.json` is built from panel1m train labels and voter answers. `cities.json` is the GeoNames `cities15000` names plus city labels seen at least twice in panel1m train, without names of three letters or less, names that appear lowercase in panel1m train text at least half as often as capitalized, and names whose train precision is below 0.34 over at least two false positives.

Candidate patterns come from mining 1-3 token contexts around each train label's surface form and ranking them by train precision and support. A pattern is added when its precision on panel1m train is above about half the micro F1 (about 0.34).

| split | texts | precision | recall | micro F1 |
|---|---|---|---|---|
| panel1m train | 899,826 | 0.680 | 0.688 | 0.684 |
| panel1m validation | 49,738 | 0.675 | 0.685 | 0.680 |

F1 by field before this round (commit ce75191) and now, ordered by train label count:

| field | train labels | train before | train now | validation labels | validation before | validation now |
|---|---|---|---|---|---|---|
| age | 20800 | 0.83 | 0.84 | 1188 | 0.83 | 0.84 |
| gender | 13133 | 0.68 | 0.68 | 768 | 0.67 | 0.68 |
| residence_city | 2497 | 0.46 | 0.48 | 137 | 0.37 | 0.37 |
| marital_status | 1836 | 0.47 | 0.51 | 92 | 0.48 | 0.50 |
| residence_country | 1678 | 0.35 | 0.39 | 110 | 0.42 | 0.44 |
| occupation | 1455 | 0.44 | 0.45 | 94 | 0.45 | 0.49 |
| residence_state | 1325 | 0.43 | 0.45 | 72 | 0.41 | 0.43 |
| parental_status | 1284 | 0.33 | 0.39 | 59 | 0.31 | 0.40 |
| height | 1198 | 0.78 | 0.80 | 58 | 0.77 | 0.86 |
| race_ethnicity | 1167 | 0.47 | 0.50 | 82 | 0.53 | 0.60 |
| nationality | 1117 | 0.45 | 0.51 | 66 | 0.42 | 0.52 |
| sexual_orientation | 1071 | 0.50 | 0.54 | 71 | 0.44 | 0.46 |
| relationship_status | 612 | 0.13 | 0.20 | 30 | 0.28 | 0.35 |
| employment_status | 594 | 0.18 | 0.26 | 28 | 0.00 | 0.00 |
| weight | 533 | 0.70 | 0.71 | 41 | 0.72 | 0.78 |
| origin_country | 456 | 0.28 | 0.40 | 39 | 0.28 | 0.33 |
| mental_health | 390 | 0.36 | 0.42 | 22 | 0.45 | 0.50 |
| religion | 349 | 0.43 | 0.52 | 32 | 0.36 | 0.40 |
| education_subject | 281 | 0.04 | 0.42 | 13 | 0.25 | 0.48 |
| income | 274 | 0.07 | 0.25 | 15 | 0.00 | 0.10 |
| birth_year | 240 | 0.12 | 0.61 | 11 | 0.00 | 0.70 |
| generation | 197 | 0.43 | 0.52 | 8 | 0.00 | 0.17 |
| education | 150 | 0.24 | 0.35 | 6 | 0.29 | 0.22 |
| origin_city | 141 | 0.26 | 0.33 | 10 | 0.14 | 0.14 |
| language | 128 | 0.09 | 0.32 | 4 | 0.00 | 0.50 |
| origin_state | 115 | 0.28 | 0.33 | 7 | 0.55 | 0.67 |
| political_ideology | 63 | 0.37 | 0.44 | 2 | 0.00 | 0.00 |

political_compass has no resolved labels. Across panel1m the voters mostly answer it with values outside its value set ("left", "center-left", "not stated"); the in-set forms ("centrist", "center", "lib-right") already map in `normalize.py`, occur 14 times over all three voters, and never twice on the same text.

## Limitations

- Labels are majority votes of three models, not ground truth.
- The voters often leave gender out of bare tags such as "M32" (gemma4-12b and qwen3-4b give only the age), so about 40% of correct tag genders count as false positives and rules gender precision is capped near 0.6. This is accepted for now; no relabeling.
- "my wife", "my boyfriend" and "my son" are rarely labeled as marital, relationship or parental status, so those patterns are mostly excluded ("my husband" and "my wife and I" stay); relationship status stays near 0.1 recall.
- Residence is often unlabeled in personal ads ("m 43 wellington", "#losangeles") and when stated as "here in X", so tag-and-place and "here in" patterns stay below the precision bar.
- Countries are rarely labeled when only a state or city is stated, so the extractor does not derive one from the other.
- Employment status, income, birth year, generation, education, language and the political fields have fewer than 30 panel1m validation labels each.
