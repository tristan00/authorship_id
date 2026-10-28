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

- patterns: age and gender tags (`28F`, `m24`, `[M4F]`, `m4f27`, `[m4r]`, `32 straight man`, `male, 23`, `[F] 19`), tags with a dash or underscore (`m-45`, `21-f`, `20y-m`), a two-digit age at the start of the text (also `20y` and `22/oklahoma`) or in brackets, a text that is only a number, ages written as words ("nineteen", "sixty-six"), heights in feet and inches (also `5"3`, and `6ft` or `6 foot` before any word), centimetres or metres (`1,80`), weights, a unit-less weight right after a height (`5'9 150`, read as pounds from 100 up and as kilograms below), and flag emoji for countries;
- phrases: first-person patterns per field (`PHRASES`), including Spanish, Portuguese, French, German, Italian and Dutch forms for marital status ("estoy casado", "mi marido"), relationship status ("je suis célibataire") and children ("tenemos dos hijos", "no tengo hijos"), birth years from "born ... 1996" anywhere, "dob" or "date of birth" with a date and "born in Tulsa in 1970", with two-digit years from 00 to 13 read as 2000s, "X resident", "I've lived in X", "we live on the westside of X", "I'm London based", "my state X" and "vivo en" / "je vis à" / "ich wohne in X" for residence ("I'm from X" and a country right after a tag were tried and lowered residence country F1), income from "i bring home 45k" and "income: $72k", employment from "i have a job", "we work full time", "i'm salaried", "at work", "my boss", "i freelance", "... for a living" and "i don't have a job" / "lost my job" / "got laid off" (also with a curly apostrophe), a job title after an age/gender tag ("27m, iit grad, software engineer", "34m phd scientist") or after "i'm NAME, a", "and work in X", orientation words not before a hyphen ("bi-weekly") or after "be" ("gonna be straight"), relationship and children from "in a healthy relationship", "i'm a 22-year-old mom", "30 latino dad", "married with kids", "with 2 young kids", "we had a baby", "had my first child" and "my first kiddo", "I (21f) am" as a first-person form in every pattern, and for gender "mid 30s fit female", "19 german guy", "i'm married and a man", gender as a list item (", Male, Canadian"), "(I'm M)", "29 single m here", "as an aging male", "this is a man", "bi guy(32)" and "agender"/"genderfluid", with places matched against countries, first-level regions and `cities.json` and occupations against `jobs.json` and a list of job nouns;
- broad mentions: any vocabulary word of a field anywhere in the text (gender words, countries, demonyms, regions, cities, languages, race, orientation, religion, marital, relationship, employment, mental health, ideology, generation, `jobs.json` titles, degrees, study subjects, "my son", "my son's", "no kids", "mom", "my gf", "pregnant", ...), the voters' own values in `values.json`, any money amount for income, and any standalone two-digit number for age, also before a comma or full stop and with a `yo`/`yrs`/`y` suffix or a hyphenated `-year-old`. Vocabulary is read in sorted order so the per-field cap of four mentions, and with it the fit, does not depend on string hashing. Numeric candidates are bounded by `config.CANDIDATE_BOUNDS`, which allows ages from 1 to 120 because the voters label ages below 13 (mostly texts that are only a number).

Every candidate also gets context cues from its own sentence: another person as the subject before it ("he", "her", "my wife", "you") or right after it ("at 33, she"), negation, "we"/"us", past-tense context ("used to", "when i was", "turned"), hypothetical context, generic subjects ("people", "everyone"), comparisons ("than", "over", "in their"), a question sentence, and for numbers a unit or range right after ("15 matches", "10 years of", "20-25"). Conditions that used to discard a match are flags instead: hypothetical context before a phrase ("if", "would", "used to be", ...), another person mentioned before a height or weight, and a text that is only a tag (`M35`, whose gender the voters rarely label). The first unflagged pattern or phrase candidate of a field, which is what first-match rules would return, is marked `pick`.

Features per candidate: source, kind, `pick`, rank, position, how many candidates share the value, how many values compete, text length and line count, the number of first-person words in the text (0, 1-2, 3-7, 8 or more), how much of the text is capitalized (none, some, most), whether the matched span has a capital letter (uppercase "M32" tags are gender-labeled 55% of the time against 14% for lowercase "m32"), the value range for numeric fields (age 13, 16, 18, ... 100; height, weight, income and birth year likewise), a form token that crosses the source with the span's case (capital, lowercase, digits only), its position (text start or not) and whether it sits in brackets, so "M32" at the start and "m32" mid-text are separate cases, the bare-tag flag, the fields that have candidates, the value for categorical fields, the two tokens before and one after the match, the four tokens on each side as a bag, for phrases whether the match starts at an age/gender tag, a bare number, a first-person word or anything else (the tag-anchored marital, race, orientation and nationality phrases also fire on bare numbers, as in "40% of married", and are right 37-80% of the time from a number against 58-95% from a tag), for tag, number and amount candidates the span with digits masked (`00 m`, `00-year old`, `$00k a year`), and whether a first-person word ("i", "my", "me", ...) is among the four before. Every feature appears both on its own and crossed with the field, so small fields share the general weights; source-specific features are also crossed with the source.

The fit log reports out-of-fold F1 per field. `fit` trains one logistic regression over all candidates of the train splits of the given datasets (features seen at least 3 times). The regularization C and per-field probability cutoffs (0.05 to 0.95 in steps of 0.025) are chosen on 3-fold out-of-fold predictions on train: starting from the best single threshold, three passes of coordinate ascent set each field's cutoff to maximize pooled micro F1 plus macro F1 (the mean over fields). Cutoffs that instead maximized each field's own F1, capped at the global threshold, cost about 0.007 out-of-fold micro F1, mostly in false positives on small fields; tuning on micro F1 alone raised small fields' cutoffs until they went nearly silent (mental health 0.30 to 0.45). The fit is two-pass: the first model's out-of-fold probabilities give each text's top score per field, and every candidate of a field gets the other fields' top scores, bucketed at 0.1, 0.25, 0.4, 0.6 and 0.8, as features for a second model fitted the same way (gender is labeled on 53% of tag texts with an age label and 4% without). The weights file holds both models; `extract` scores the first, then the second. The weights are stored outside the repository as a model artifact. Candidates are collected in `config.WORKERS` processes, each with its own feature table that the main process remaps, and the nine cross-validation fits run in parallel with the three full fits, one per C; on panel1m and panel1m_b train the whole fit takes about 3 minutes and `evaluate` about 5 seconds per validation split.

`jobs.json` is built from panel1m train labels and voter answers. `cities.json` is the GeoNames `cities15000` names plus city labels seen at least twice in panel1m train, without names of three letters or less, names that appear lowercase in panel1m train text at least half as often as capitalized, and names whose train precision is below 0.34 over at least two false positives, plus the 48 city labels seen at least twice in panel1m and panel1m_b train that this left out (Philadelphia, Pittsburgh, Calgary, Perth, Madrid, Tokyo, ...) unless they are written lowercase more than twice as often as capitalized, with a country or state when most of their labels name one, plus 115 city names that any single voter gave at least three times on panel1m and panel1m_b train (Nagpur, Fresno, Ankara, Bologna, Johannesburg, ...) under the same case rule. City aliases from `normalize.py` ("nyc", "philly", "la") are mentions too, and a place that is exactly an alias is read as that city first, so "I live in LA" is Los Angeles while "Lafayette, LA" stays Louisiana.

`values.json` holds the label values outside the value sets (and, for occupation and study subject, outside the SOC and CIP groups) that occur at least twice among panel1m and panel1m_b train labels, have at least three characters, and match their field's train label in at least 1% of the train texts that mention them; the mention is a candidate with the voters' wording as its value (marital status "single", orientation "m4m", mental health "depressed", ...).

The weights are fitted on panel1m and panel1m_b train (1,799,903 texts, 115,285 labels). Cross-validation chose C = 0.3 for both passes; with the tuned cutoffs the out-of-fold micro F1 is 0.729 and the macro F1 (mean over fields) 0.493. Tuning cutoffs on micro F1 alone gave the same micro F1 and a macro F1 of 0.461 when it was last compared. Pooled scores count the three validation splits together (13,211 labels); "before round 1" is the model fitted on the corrected labels before the candidate, feature and cutoff changes since. Round 1 sorted validation misses into categories, so all three validation splits saw some rule work; from round 2 on, development reads train errors and out-of-fold scores only, and validation is used for scoring.

| validation micro F1 | panel1m | panel1m_b | panel200k | pooled |
|---|---|---|---|---|
| before round 1 | 0.713 | 0.708 | 0.701 | 0.706 |
| current | 0.737 | 0.732 | 0.719 | 0.726 |

Validation F1 by field on each split and pooled over all three (pooled precision 0.743, recall 0.711), with the pooled F1 before round 1. Fields are ordered by pooled validation label count.

| field | pooled labels | panel1m | panel1m_b | panel200k | pooled | before round 1 |
|---|---|---|---|---|---|---|
| age | 4853 | 0.88 | 0.89 | 0.87 | 0.88 | 0.86 |
| gender | 3090 | 0.76 | 0.75 | 0.75 | 0.75 | 0.74 |
| residence_city | 599 | 0.58 | 0.59 | 0.60 | 0.59 | 0.56 |
| occupation | 521 | 0.52 | 0.42 | 0.44 | 0.45 | 0.44 |
| marital_status | 457 | 0.58 | 0.60 | 0.64 | 0.62 | 0.58 |
| residence_country | 456 | 0.55 | 0.47 | 0.50 | 0.51 | 0.49 |
| sexual_orientation | 355 | 0.52 | 0.59 | 0.59 | 0.57 | 0.56 |
| race_ethnicity | 354 | 0.75 | 0.69 | 0.61 | 0.67 | 0.64 |
| residence_state | 350 | 0.59 | 0.52 | 0.58 | 0.57 | 0.55 |
| parental_status | 302 | 0.46 | 0.53 | 0.43 | 0.46 | 0.41 |
| nationality | 296 | 0.58 | 0.57 | 0.60 | 0.59 | 0.57 |
| height | 283 | 0.90 | 0.84 | 0.84 | 0.85 | 0.81 |
| mental_health | 151 | 0.54 | 0.50 | 0.48 | 0.50 | 0.43 |
| relationship_status | 133 | 0.41 | 0.31 | 0.17 | 0.27 | 0.28 |
| employment_status | 132 | 0.25 | 0.27 | 0.29 | 0.28 | 0.32 |
| origin_country | 128 | 0.49 | 0.66 | 0.34 | 0.46 | 0.43 |
| weight | 122 | 0.82 | 0.70 | 0.75 | 0.76 | 0.76 |
| religion | 109 | 0.56 | 0.73 | 0.47 | 0.55 | 0.51 |
| education | 107 | 0.21 | 0.37 | 0.32 | 0.31 | 0.24 |
| education_subject | 88 | 0.31 | 0.38 | 0.46 | 0.40 | 0.42 |
| income | 71 | 0.47 | 0.45 | 0.51 | 0.49 | 0.27 |
| generation | 55 | 0.50 | 0.59 | 0.43 | 0.49 | 0.49 |
| birth_year | 51 | 0.73 | 0.61 | 0.67 | 0.67 | 0.55 |
| language | 47 | 0.29 | 0.38 | 0.24 | 0.30 | 0.26 |
| origin_city | 37 | 0.13 | 0.36 | 0.19 | 0.21 | 0.18 |
| origin_state | 31 | 0.53 | 0.55 | 0.35 | 0.45 | 0.46 |
| political_ideology | 27 | 0.40 | 0.00 | 0.25 | 0.24 | 0.24 |
| political_compass | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

panel1m_b labels relationship status 24% less often per train text than panel1m (5.1 against 6.8 per 10,000) and parental status 16% less, from per-server voter variance. The combined model learns the lower rate, which is why relationship status drops on both validation splits.

political_compass has 35 resolved labels over the three datasets, 34 of them outside its value set ("left-leaning", "right leaning", "leftist").

## Limitations

- Labels are majority votes of three models, not ground truth.
- The voters often leave gender out of bare tags such as "M32" (gemma4-12b and qwen3-4b give only the age): gender is labeled on 14% of texts that are only a tag. Against the majority labels, gemma4-12b and gemma4-26b each score about 0.83 micro F1 on train and qwen3-4b 0.64.
- Countries are rarely labeled when only a state or city is stated (the United States in 56 of 743 such train texts), so the extractor does not derive one from the other.
- Income, birth year, generation, language, origin city, origin state and the political fields have fewer than 75 pooled validation labels each (political_compass 6), so their validation F1 moves by a few texts per change.
