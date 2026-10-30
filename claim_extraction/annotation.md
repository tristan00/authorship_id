# Claims annotation

Labels for measuring text self-claim extraction come from three local LLM voters served by vLLM through the separate `D:\local_annotator` package, driven by `label1m.py`. `claim_extraction/annotation.json` defines the fields and their value sets; `normalize.py` maps voter answers onto them where an answer is a known form of a value and otherwise keeps the voter's value. The voters do not use the prompt in `annotation.json`.

## Pipeline

1. Load a month into the database (`python -m database add --months YYYY-MM`).
2. Sample texts into a dataset: `python -m claim_extraction sample --month 2026-03 --datasets panel1m`
3. Label it with `label1m.py` (see below), which writes one answer file per voter and shard.
4. Vote the answers into labels: `python -m claim_extraction labels --month 2026-03 --datasets panel1m`
5. Fit the candidate scorer on the train splits of one or more datasets, written to `C:\reddit_data\models\claim_extraction.json`, starting the cutoff search from the cutoffs of the weights file given as `--start` (normally the installed model):
   `python -m claim_extraction fit --month 2026-03 --datasets panel1m panel1m_b --start C:\reddit_data\models\claim_extraction.json`
6. Score the extractor on one split of each dataset, written to `<month>/evaluations/<dataset>_<split>.json`:
   `python -m claim_extraction evaluate --month 2026-03 --datasets panel1m panel1m_b --split validation`
7. Extract claims from the readable texts of every loaded month not yet extracted into `text_claims` (`text_sha256`, `field`, `value`, `start_char`, `end_char`), which consolidation and the explorer read through `records.text_sha256`:
   `python -m claim_extraction extract`
   A stopped run resumes. `--reset` empties `text_claims` and extracts every month again. The month pipeline (`python -m pipeline`) runs this step.

### Extraction

`extract` reads each distinct non-empty text of `bodies` once. A record is readable (`text_status` available or title_only) exactly when its text is non-empty, so the read needs no join with `records` and no status filter; a text shared by several records is extracted once and its claims apply to all of them. Texts over 10,000 bytes, which sampling leaves out, are kept. They are about 5 per million texts and take under 0.03% of extraction time. `bodies.month` is the month whose load first added a text, so each text belongs to exactly one month. The months to extract are those with `months.extracted_at` empty. Each is split into `EXTRACT_PARTS` = 4,096 equal `text_sha256` ranges (about 75,000 texts at 300 million per month). A worker reads its range through `bodies_pkey`, `COPY (SELECT ... WHERE month = %s AND text_sha256 BETWEEN %s AND %s AND text <> '') TO STDOUT`. `bodies` is sorted by hash, so a range is one stretch of the heap, which also holds the other months' texts of that range. Parts are hash ranges, not heap pages, because every load rebuilds `bodies` and moves its rows. The parent never sees texts, only part numbers and counts.

Each part is one transaction: delete the claims of the part's texts, read, extract with `rules.claims`, COPY the claims into `text_claims`, and mark the part finished in `text_claims_parts` (keyed by month and part) with its texts, claims, CPU seconds and read, extract and write seconds. A worker that dies loses only its open part, so a rerun continues with the unfinished parts. The delete makes a part safe to repeat, as when a month is loaded again. When every part is finished, the months get `extracted_at`, the parts table is dropped, and `text_claims` is vacuumed and analyzed. On two 250,000-record test months, killing a run after 1,587 of 8,192 parts and rerunning gave the same rows as single-process `rules.claims` on every text. Each worker loads the model once and keeps one connection, so 24 workers take about 260 MB each. The shared feature-id table with per-field weight lists (see Speed) adds about 43 MB: a process holds 183 MB after loading the model and vocabulary against 140 MB with per-field tables.

Claim spans are code-point offsets into the stored text, as the explorer slices it. `rules.claims` maps the winning candidate's span back through the rewrites: `US` to `USA`, lowercasing that changes length, blanked quotes and links, and removed zero-width characters. On validation, all 9,178 spans in untouched texts match the stored text exactly. Of 3,593 spans in rewritten texts, 3,591 match after the same rewrite; the other two end on a blanked link and cover the link.

On a 1.92M-text slice, the staged claims equal single-process `rules.claims` on a 10% subsample, and parts write no duplicate rows. Reading takes 3.5% of a worker's time and writing 0.05%, and Postgres used 0.2 cores at most. Workers are CPU-bound, so throughput is set by the CPU. The Ultra 9 285K has 8 performance cores (logical CPUs 0, 1, 10-13, 22, 23) at about 10,900 texts/s for one pinned process and 16 efficiency cores at about 8,200. Pinned processes running together lose 9-13% to shared caches: about 184,000 texts/s across all 24 cores.

| workers | texts/s (wall) | texts/s per worker while busy |
|---|---|---|
| 1 | 11,200 | 11,400 |
| 4 | 40,900 | 11,100 |
| 8 | 70,400 | 10,500 |
| 16 | 106,400 | 8,800 |
| 20 | 155,800 | 8,500 |
| 22 | 156,700 | 7,900 |
| 23 | 159,800 | 7,700 |
| 24 | 165,600 | 7,700 |

Up to 16 workers the rows come from the 1.92M-text slice, where the 3 s worker start is part of the wall time. From 20 workers they come from separate 9.6M-text slices read cold from disk.

The 2026-03 run read 371,780,434 texts, the same count as a direct query of the population, of which 64,507 were over 10,000 bytes. It wrote 23,532,072 claims on 14,329,043 texts, 6.33 per 100 texts against 6.40 predicted on panel200k validation. Extraction took about 43 minutes over 24 workers, plus 14 s for the finish step.

After the split into `records` and `bodies`, the 2026-03 run read 307,368,148 distinct non-empty texts and wrote 16,550,491 claims on 10,018,217 texts. Joined to `records` on the text hash, they are exactly the 23,532,072 claims of the per-record run (EXCEPT ALL is empty both ways). It used 156 µs of CPU per text against 144 µs before, since deduplication removes mostly short texts, and 48,068 CPU seconds in total. The run took 56 minutes because other jobs shared the machine and each worker got 0.61 of a core; alone it would take about 35.

The heap's first ~8M pages interleave posts with comments, because the loader read both dumps in parallel; the rest is comments only. The mixed region yields about 11.7 claims per 100 texts and ran at about 105,000 texts/s. The comment-only region yields about 2.3 and ran at about 150,000. Over the whole month, posts are 12.2% of texts with 35.21 claims per 100, against 35.55 predicted on panel200k validation, where posts are also 12.2%. Comments have 2.32 against 2.33. Every field with at least 0.1 claims per 100 texts is within 9% of its validation rate. The larger ratios (origin state 1.72, language 1.49, employment 1.36, origin country 0.76) are on fields with 7 to 51 validation predictions per 100,000 texts.

On a fresh random sample of 100,000 texts from the month, the stored claims equal single-process `rules.claims` and `rules.extract` exactly. The table has no duplicate (record_id, field) and no span outside its text.

Two texts stopped earlier attempts; each was fixed with identical output on the validation and fit-feature checks, and the run resumed from its finished parts.

- An income amount with hundreds of digits parsed to infinity, which `round()` cannot convert. `earnings` and `normalize.bounded` now treat a non-finite amount like any out-of-range number.
- A post with 17,550 consecutive newlines kept `TAG_FOR` backtracking cubically through `\s*[\[\(]?\s*`, so its part never finished. Both such runs are now written as `\s*(?:[\[\(]\s*)?` and `\s*(?:[\]\)]\s*)?(?:[-–|:]\s*)?`. The rewrite gives the same matches on 2M random strings and the post now takes 12 s.

Of all patterns, only `TAG_SELF`, `TAG_ANY` and `TAG_FOR` grow faster than linearly on long whitespace runs. They grow quadratically: about 2 s for 16,000 newlines.

## Datasets

Each dataset lives in `C:\reddit_data\annotations\<month>\<dataset>\`:

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

Over panel1m, panel1m_b and panel200k this gives 141,609 resolved labels, against 129,324 from the earlier parser that dropped unknown values, values with notes and numbers outside `config.NUMERIC`. 8,143 labels are outside the value sets (marital status "single", orientation "m4m", mental health "depressed", ...) and 1,878 numbers are outside `config.NUMERIC`, the range outside which `attribute_model` does not train on numeric claims; extractor candidates use `config.CANDIDATE_BOUNDS` instead. 10,098 of 183,249 numeric answers are not a single number.

`labels.vote` resolves a field when one answer (a value, or none) has at least two of the three votes and more votes than any other answer. There is no tiebreaker; unresolved fields are left out of `values` and count as negatives.

## Rules extractor

`rules.extract` turns an uppercase `US` into `USA`, lowercases the text, drops zero-width characters, removes quoted lines, quoted strings of six characters or more (not starting at an inch mark such as `6'4"`) and links, and maps curly apostrophes and primes to `'` and `"`, so patterns are written with `'` only. It then collects candidates, scores each with one linear model, and keeps per field the best candidate whose score clears that field's cutoff.

Candidates come from three kinds of sources, up to three matches per pattern:

- patterns: age and gender tags (`28F`, `m24`, `[M4F]`, `m4f27`, `[m4r]`, `32 straight man`, `male, 23`, `[F] 19`), tags with a dash or underscore (`m-45`, `21-f`, `20y-m`), a two-digit age at the start of the text (also `20y` and `22/oklahoma`) or in brackets, a text that is only a number, ages written as words ("nineteen", "sixty-six"), heights in feet and inches (also `5"3`, `6'00`, "a 6'3 guy", and `6ft` or `6 foot` before any word), centimetres or metres (`1,80`, also at the end of a sentence), weights, a unit-less weight right after a height (`5'9 150`, read as pounds from 100 up and as kilograms below), and flag emoji for countries;
- phrases: first-person patterns per field (`PHRASES`), including Spanish, Portuguese, French, German, Italian and Dutch forms for marital status ("estoy casado", "mi marido"), relationship status ("je suis célibataire") and children ("tenemos dos hijos", "no tengo hijos"), birth years from "born ... 1996" anywhere, "dob" or "date of birth" with a date and "born in Tulsa in 1970", with two-digit years from 00 to 13 read as 2000s, "X resident", "I've lived in X", "we live on the westside of X", "I'm London based", "my state X" and "vivo en" / "je vis à" / "ich wohne in X" for residence ("I'm from X" and a country right after a tag were tried and lowered residence country F1), income from "i bring home 45k" and "income: $72k", employment from "i have a job", "we work full time", "i'm salaried", "at work", "my boss", "i freelance", "... for a living" and "i don't have a job" / "lost my job" / "got laid off" (also with a curly apostrophe), a job title after an age/gender tag ("27m, iit grad, software engineer", "34m phd scientist") or after "i'm NAME, a", "and work in X", orientation words not before a hyphen ("bi-weekly") or after "be" ("gonna be straight"), relationship and children from "in a healthy relationship", "i'm a 22-year-old mom", "30 latino dad", "married with kids", "with 2 young kids", "we had a baby", "had my first child" and "my first kiddo", "I (21f) am" as a first-person form in every pattern, and for gender "mid 30s fit female", "19 german guy", "i'm married and a man", gender as a list item (", Male, Canadian"), "(I'm M)", "29 single m here", "as an aging male", "this is a man", "bi guy(32)" and "agender"/"genderfluid", pronoun tags ("she/her" female, "he/him" male, "they/them" non-binary), a text that is only "F" or "M", "56 WM", and request tags such as `[M4F]` right after a `#` or an emoji, with places matched against countries, first-level regions and `cities.json` and occupations against `jobs.json` and a list of job nouns;
- broad mentions: any vocabulary word of a field anywhere in the text (gender words, countries, demonyms, regions, cities, languages, race, orientation, religion, marital, relationship, employment, mental health, ideology, generation, `jobs.json` titles, degrees, study subjects, "my son", "my son's", "no kids", "mom", "my gf", "pregnant", ...), the voters' own values in `values.json`, any money amount for income, any year from 1920 to 2013 for birth year (135 train birth years had no other candidate), and any standalone two-digit number for age, also before a comma or full stop and with a `yo`/`yrs`/`y` suffix or a hyphenated `-year-old`. Words are split so that a hyphen stays inside a word only before another letter or digit, so the r4r title "24 [M4F] Michigan- looking" mentions `michigan`. Vocabulary is read in sorted order so the per-field cap of four mentions, and with it the fit, does not depend on string hashing. Numeric candidates are bounded by `config.CANDIDATE_BOUNDS`, which allows ages from 1 to 120 because the voters label ages below 13 (mostly texts that are only a number).

Every candidate also gets context cues from its own sentence: another person as the subject before it ("he", "her", "my wife", "you") or right after it ("at 33, she"), negation, "we"/"us", past-tense context ("used to", "when i was", "turned"), hypothetical context, generic subjects ("people", "everyone"), comparisons ("than", "over", "in their"), a question sentence, and for numbers a unit or range right after ("15 matches", "10 years of", "20-25"). Conditions that used to discard a match are flags instead: hypothetical context before a phrase ("if", "would", "used to be", ...), another person mentioned before a height or weight, and a text that is only a tag (`M35`, whose gender the voters rarely label). The first unflagged pattern or phrase candidate of a field, which is what first-match rules would return, is marked `pick`.

Features per candidate: source, kind, `pick`, rank, position, how many candidates share the value, how many values compete, text length and line count, the number of first-person words in the text (0, 1-2, 3-7, 8 or more), how much of the text is capitalized (none, some, most), whether the matched span has a capital letter (uppercase "M32" tags are gender-labeled 55% of the time against 14% for lowercase "m32"), the value range for numeric fields (age 13, 16, 18, ... 100; height, weight, income and birth year likewise), a form token that crosses the source with the span's case (capital, lowercase, digits only), its position (text start or not) and whether it sits in brackets, so "M32" at the start and "m32" mid-text are separate cases, the bare-tag flag, the fields that have candidates, the value for categorical fields, the two tokens before and one after the match, the four tokens on each side as a bag, for phrases whether the match starts at an age/gender tag, a bare number, a first-person word or anything else (the tag-anchored marital, race, orientation and nationality phrases also fire on bare numbers, as in "40% of married", and are right 37-80% of the time from a number against 58-95% from a tag), for tag, number and amount candidates the span with digits masked (`00 m`, `00-year old`, `$00k a year`), whether a first-person word ("i", "my", "me", ...) is among the four before, for residence candidates whether a state or country follows the mention ("phoenix, az", "budapest, hungary"), for vocabulary mentions the matched text when it differs from the value it resolves to ("wife" and "woman" both resolve to female but predict a gender label at 24% and 63%), except in fields whose surface forms are near-synonyms of one value (language, generation, education subject), where the text only splits the evidence for that value, and the number of tokens on the candidate's own line (below 3, 6, 12, 30 or more), so a bare "ottawa, on" or "27m" line inside a longer post differs from a mention in running prose. Every feature appears both on its own and crossed with the field, so small fields share the general weights; source-specific features are also crossed with the source.

The fit log reports out-of-fold F1 per field. `fit` trains one logistic regression over all candidates of the train splits of the given datasets (features seen at least 3 times), solved to `config.FIT_TOL` = 1e-6 with one BLAS/OpenMP thread per fit. Without the thread limit each joblib worker took a share of the cores, so the same fit gave different probabilities with 4 parallel jobs than with 12 (one C value against three) and a single-C screening run could not reproduce the full fit; pinned, the C = 0.3 probabilities are byte-identical either way and the fit takes no longer. At sklearn's default tolerance of 1e-4 the solver stopped early: tightening it raised out-of-fold micro F1 by 0.0007 and macro F1 by 0.0034 on the first pass, and it cut how far fields that a rule change does not touch move between two fits from 0.0024 to 0.0005 (mean absolute out-of-fold F1 change, first pass), so single rule batches became measurable. The regularization C and per-field probability cutoffs (0.05 to 0.95 in steps of 0.025) are chosen on 3-fold out-of-fold predictions on train: starting from the cutoffs of the `--start` weights file, three passes of coordinate ascent set each field's cutoff to maximize pooled micro F1 plus macro F1 (the mean over fields). Started from one global threshold instead, a rule change that left the summed objective unchanged could still trade 0.001 of micro F1 for macro F1 through a different set of cutoffs, and fields the change never touched moved by up to 0.01; refitting the current rules from their own installed cutoffs reproduces them exactly. Cutoffs that instead maximized each field's own F1, capped at the global threshold, cost about 0.007 out-of-fold micro F1, mostly in false positives on small fields; tuning on micro F1 alone raised small fields' cutoffs until they went nearly silent (mental health 0.30 to 0.45). The fit is two-pass: the first model's out-of-fold probabilities give each text's top score per field, and every candidate of a field gets the other fields' top scores, bucketed at 0.1, 0.25, 0.4, 0.6 and 0.8, as features for a second model fitted the same way (gender is labeled on 53% of tag texts with an age label and 4% without). The weights file holds both models; `extract` scores the first, then the second. The weights are stored outside the repository as a model artifact. Candidates are collected in `config.WORKERS` processes, each with its own feature table that the main process remaps, and the nine cross-validation fits run in parallel with the three full fits, one per C; on panel1m and panel1m_b train the whole fit takes about 30 minutes and `evaluate` about 5 seconds per validation split.

`jobs.json` is built from panel1m train labels and voter answers. `cities.json` is the GeoNames `cities15000` names plus city labels seen at least twice in panel1m train, without names of three letters or less, names that appear lowercase in panel1m train text at least half as often as capitalized, and names whose train precision is below 0.34 over at least two false positives, plus the 48 city labels seen at least twice in panel1m and panel1m_b train that this left out (Philadelphia, Pittsburgh, Calgary, Perth, Madrid, Tokyo, ...) unless they are written lowercase more than twice as often as capitalized, with a country or state when most of their labels name one, plus 115 city names that any single voter gave at least three times on panel1m and panel1m_b train (Nagpur, Fresno, Ankara, Bologna, Johannesburg, ...) under the same case rule. City aliases from `normalize.py` ("nyc", "philly", "la") are mentions too, and a place that is exactly an alias is read as that city first, so "I live in LA" is Los Angeles while "Lafayette, LA" stays Louisiana.

`values.json` holds the label values outside the value sets (and, for occupation and study subject, outside the SOC and CIP groups) that occur at least twice among panel1m and panel1m_b train labels, have at least three characters, and match their field's train label in at least 1% of the train texts that mention them; the mention is a candidate with the voters' wording as its value (marital status "single", orientation "m4m", mental health "depressed", ...).

The weights are fitted on panel1m and panel1m_b train (1,799,903 texts, 115,285 labels). Cross-validation chose C = 0.3 for both passes; with the tuned cutoffs the out-of-fold micro F1 is 0.732 and the macro F1 (mean over fields) 0.501. Tuning cutoffs on micro F1 alone gave the same micro F1 and a macro F1 of 0.461 when it was last compared. Pooled scores count the three validation splits together (13,211 labels); "before round 1" is the model fitted on the corrected labels before the candidate, feature and cutoff changes since. Round 1 sorted validation misses into categories, so all three validation splits saw some rule work; from round 2 on, development reads train errors and out-of-fold scores only, and validation is used for scoring.

| validation micro F1 | panel1m | panel1m_b | panel200k | pooled |
|---|---|---|---|---|
| before round 1 | 0.713 | 0.708 | 0.701 | 0.706 |
| current | 0.739 | 0.737 | 0.722 | 0.730 |

Validation F1 by field on each split and pooled over all three (pooled precision 0.743, recall 0.718), with the pooled F1 before round 1. Fields are ordered by pooled validation label count.

| field | pooled labels | panel1m | panel1m_b | panel200k | pooled | before round 1 |
|---|---|---|---|---|---|---|
| age | 4853 | 0.88 | 0.89 | 0.87 | 0.88 | 0.86 |
| gender | 3090 | 0.76 | 0.76 | 0.75 | 0.76 | 0.74 |
| residence_city | 599 | 0.55 | 0.58 | 0.61 | 0.59 | 0.56 |
| occupation | 521 | 0.53 | 0.43 | 0.45 | 0.46 | 0.44 |
| marital_status | 457 | 0.59 | 0.58 | 0.62 | 0.60 | 0.58 |
| residence_country | 456 | 0.54 | 0.52 | 0.50 | 0.51 | 0.49 |
| sexual_orientation | 355 | 0.54 | 0.62 | 0.60 | 0.59 | 0.56 |
| race_ethnicity | 354 | 0.78 | 0.73 | 0.64 | 0.70 | 0.64 |
| residence_state | 350 | 0.59 | 0.53 | 0.58 | 0.57 | 0.55 |
| parental_status | 302 | 0.49 | 0.52 | 0.49 | 0.50 | 0.41 |
| nationality | 296 | 0.61 | 0.59 | 0.60 | 0.60 | 0.57 |
| height | 283 | 0.92 | 0.85 | 0.83 | 0.85 | 0.81 |
| mental_health | 151 | 0.52 | 0.51 | 0.51 | 0.51 | 0.43 |
| relationship_status | 133 | 0.36 | 0.35 | 0.23 | 0.29 | 0.28 |
| employment_status | 132 | 0.32 | 0.26 | 0.38 | 0.34 | 0.32 |
| origin_country | 128 | 0.42 | 0.59 | 0.34 | 0.42 | 0.43 |
| weight | 122 | 0.82 | 0.70 | 0.77 | 0.77 | 0.76 |
| religion | 109 | 0.61 | 0.75 | 0.53 | 0.60 | 0.51 |
| education | 107 | 0.22 | 0.42 | 0.36 | 0.35 | 0.24 |
| education_subject | 88 | 0.38 | 0.43 | 0.45 | 0.43 | 0.42 |
| income | 71 | 0.48 | 0.45 | 0.52 | 0.49 | 0.27 |
| generation | 55 | 0.46 | 0.57 | 0.38 | 0.45 | 0.49 |
| birth_year | 51 | 0.70 | 0.67 | 0.68 | 0.68 | 0.55 |
| language | 47 | 0.29 | 0.39 | 0.13 | 0.27 | 0.26 |
| origin_city | 37 | 0.13 | 0.36 | 0.24 | 0.23 | 0.18 |
| origin_state | 31 | 0.53 | 0.50 | 0.36 | 0.45 | 0.46 |
| political_ideology | 27 | 0.47 | 0.00 | 0.23 | 0.26 | 0.24 |
| political_compass | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

panel1m_b labels relationship status 24% less often per train text than panel1m (5.1 against 6.8 per 10,000) and parental status 16% less, from per-server voter variance. The combined model learns the lower rate, which is why relationship status drops on both validation splits.

political_compass has 35 resolved labels over the three datasets, 34 of them outside its value set ("left-leaning", "right leaning", "leftist").

### Speed

`extract` runs at about 10,400 texts/s in one process on the first 20,000 panel200k records (171 characters on average), against 1,414 before the speed work. Every speed change was checked for identical output: `extract` on all validation texts of panel1m, panel1m_b and panel200k, and the fit features of 300,000 panel1m train texts. 69% of texts have no candidate and cost about 55 µs. Texts with candidates average 305 characters and take about three quarters of the time.

A regex runs only when the text can match it. At import, every phrase, tag and stat pattern is parsed with `re._parser` into requirement options: sets of literals of which at least one must occur. Character classes of up to eight characters, optional parts and alternations are spelled out up to 64 strings. Known prefixes and suffixes are carried through groups that can't be spelled whole, so `(?:i'm|im|i am|i \(..\) am) ([mf])` needs "i'm f", "im m", ... instead of " m". Anchors and lookarounds count as zero width. Literals are looked up in a copy of the text with every whitespace run collapsed to one space and every digit turned into 0. In that copy `\s+` spells as a space and any digit as "0", so a tag pattern needs "0 f" or "0m" rather than any "f", and a pattern that needs a digit needs "0". Options whose shortest literal is under three characters are dropped (`SHORTEST`), except the strongest one. They rarely rejected a text but quadrupled the literal hits. The 3,084 remaining literals are found in one pass by an Aho-Corasick automaton (`pyahocorasick`). Each literal carries a bitmask of the options it satisfies, and a pattern runs when its options are all covered. Phrase patterns are reached only through the literals of their strongest option. A regex whose first consumed item, after zero-width `\b` and lookarounds, is a literal or a character class, alone or opening a group, is rewritten at import to consume that character first and check the assertions in a one-character lookbehind after it: `\b(?<!my )i'm` matches as `i(?<=\b(?<!my )i)'m`. `re` then finds start positions with its C prefix or character-set scan instead of entering the matcher at every position. This applies to 101 of the 233 phrase, tag and stat patterns and halves the time of those that run; moving `\b` into each branch of an alternation gave nothing on phrases and slowed the context cues, so alternations are left alone. Any other regex whose possible first characters are known starts with a lookahead on them. The quote and link removal and the `US` rewrite are skipped when their own required literals are absent. Those literals come from the same analysis but are checked on the raw text, which holds only while they contain no space or digit.

Text-level features (capitals, line count, first-person count) are computed only when a candidate exists. Vocabulary mentions walk a token trie. At load, every feature name gets one id shared by all fields, and each field gets two weight lists indexed by id, holding w[x] + w[field|x] for the bare feature x, or 0 when the field has no weight for it. A candidate's features are looked up once in that one table, which is a third the size of the 28 per-field tables it replaced and stays warmer in cache (7.3 against 10.6 µs per candidate), and both passes index the lists. Adding the zero weights leaves every sum bit-identical. The folding changes the order of the float additions against the unfolded model; on the validation splits no extracted value changed. The other fields' top-score features are looked up once per field, and the first pass runs only when a text has candidates for more than one field, since the second pass of a single field reads no top scores. Features that depend only on the span (the four context tokens on each side, cues, line length, case form) are computed once per span and text: 37% of candidates share their span with an earlier one, as a city and the state and country derived from it do. ASCII texts count letters and capitals with `bytes.translate`. `rules.groups` yields each candidate's general and own feature sets for `extract`, and `rules.features` builds the field-crossed set from them for the fit.

Per text, about 93 µs go to candidate features (20), scoring (18), phrase regexes (15), vocabulary mentions (10), tag and stat patterns (7.5), literal finding (7), lowercasing and removals (5.5), tokens (5) and the gating copy (3). Tag and stat patterns run from one ordered table of regex, requirement mask and handler (`SCANS`), so a pattern that can't match costs one integer test.

On a fixed sample of 1,000,000 new April 2026 texts (one contiguous `text_sha256` range of `bodies`, 180 characters on average, 54,563 claims), the shared feature-id table, the per-span features, the rewritten regex starts and smaller fixes (a plain loop in `bucket`, skipping the quote straightening and the candidate derivation when there is nothing to do, one regex for the next sentence end) cut CPU per text in one process from 107 to 91 µs, the mean of two side-by-side runs of both versions on two performance cores, swapped. 20 processes went from about 112,000 to 136,000 texts/s and from 154 to 127 µs of CPU per text, on a machine shared with other jobs. Before, the third of texts that have candidates (2.9 each) cost 266 µs and the rest 19 µs; of an average text's 108 µs, about 48 went to candidate features (28) and scoring (20, half of it feature lookups), 14 to phrase regexes, 11 to tokens, the gating copy and literal finding, 6 to vocabulary mentions and 5 to tag and stat patterns. The new code's claims equal the old code's on all 1M texts, both single-process and over 20 processes, and its claims, `extract` results and fit features equal them on all panel1m and panel200k texts (fit features on the first 300,000). Tried and dropped for no measurable gain: an unrolled token regex, an ASCII fast path for the gating copy, filtering phrase positions in one comprehension, per-span line token counts, and `array('d')` weight lists, which saved 26 MB per worker but summed slower. A cache of runnable phrases per literal mask would hit rarely (40,589 distinct masks per 100,000 texts).

## Limitations

- Labels are majority votes of three models, not ground truth.
- The voters often leave gender out of bare tags such as "M32" (gemma4-12b and qwen3-4b give only the age): gender is labeled on 14% of texts that are only a tag. Against the majority labels, gemma4-12b and gemma4-26b each score about 0.83 micro F1 on train and qwen3-4b 0.64.
- Countries are rarely labeled when only a state or city is stated (the United States in 56 of 743 such train texts), so the extractor does not derive one from the other.
- Income, birth year, generation, language, origin city, origin state and the political fields have fewer than 75 pooled validation labels each (political_compass 6), so their validation F1 moves by a few texts per change.
