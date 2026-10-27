# Claims annotation

Labels for measuring text self-claim extraction come from local LLM annotators run by the separate `D:\local_annotator` repository. The annotation task, its prompt and its models are defined in `claim_extraction/annotation.json` and are **frozen as of commit `6d25841`** (the file moved from `claims/` unchanged). Any change to that file requires relabeling every dataset, because labels made under different prompts or models are not comparable.

## Pipeline

1. Load a month into the database (`python -m database add --months YYYY-MM`).
2. Sample datasets of texts:
   `python -m claim_extraction sample --month 2026-03 --datasets train0 validation train1 train2 train3 test`
3. Label each dataset with one call to the annotator, which runs every voter, the tiebreaker and the vote:
   ```
   cd D:\local_annotator
   python -m local_annotator D:/authorship_id/claim_extraction/annotation.json D:/reddit_data/annotations/2026-03/<dataset>/records.jsonl D:/reddit_data/annotations/2026-03/<dataset>/labels
   ```
4. Score the extractor against one dataset or a pool of datasets, written to `<month>/evaluations/`:
   `python -m claim_extraction evaluate --month 2026-03 --datasets train0 train1 train2 train3`

Nothing on the authorship_id side loops over annotators or votes; all of that happens inside the one annotator call.

## Datasets

Each dataset lives in `D:\reddit_data\annotations\<month>\<dataset>\`:

| file | content |
|---|---|
| `records.jsonl` | `{"id", "text"}` per text |
| `labels/labels.jsonl` | `{"id", "values": {field: value}, "unresolved": [fields], "ballots": [...]}` per text |
| `labels/voters/<model>.jsonl` | each voter's raw answer per text |
| `labels/report.json` | timings, rates, invalid answers, pairwise agreement, unresolved and resolved counts |
| `annotate.log` | the annotator run log |

Sampling draws texts, not authors: one run takes random readable texts of the month (body or title only) of at most 10,000 UTF-8 bytes, so every prompt fits the annotators' 16,384-token context (a token never covers less than a byte), from a random sample of the table's pages, and splits them into disjoint datasets of 100,000. Datasets from separate runs can share a few texts. Extraction never sees authors; author-level consolidation lives in `claim_consolidation` and is not evaluated here.

| dataset | use |
|---|---|
| `train0` to `train3` | extractor development; error examples may be read |
| `validation` | metrics only during development, never examples |
| `test` | held out; scored at the end only |

`D:\reddit_data\annotations\<month>\evaluations\` holds one score report per evaluated pool, and for training pools only, sampled errors and the most common wrong values.

## Task

The annotators read one Reddit text at a time and list facts the author states about themselves that are true at the time of writing, either stated outright or following necessarily from what they say (for example "my husband" means married, "28F" means age 28 and female). They leave out facts about other people, quoted lines, questions, hypotheticals, jokes, role-play, plans, past states, guesses from topic or style, and values worked out from another fact.

Each answer is `none` or up to 12 lines of `field: value`, lowercase, at most one value per field. Decoding is constrained by a regular expression built from the field definitions, so every answer is well formed and every closed-set value is one of the listed values. Six worked examples follow the instructions as separate chat turns.

The value sets come from external standards, not from the extractor:

| field | values |
|---|---|
| age | whole years, 13 to 100 |
| birth_year | 1920 to 2013 |
| generation | Pew Research Center generations |
| gender | female, male, non-binary |
| sexual_orientation | straight, gay, lesbian, bisexual, pansexual, asexual, queer |
| race_ethnicity | US OMB SPD 15 (2024) categories plus multiracial |
| nationality, residence_country, origin_country | 199 sovereign states and territories (UN members and observers, Taiwan, Kosovo, Hong Kong, Puerto Rico) |
| language | native language, ISO 639-1 living languages; the language a text is written in does not count |
| religion | christian, muslim, jewish, hindu, buddhist, sikh, other religion, atheist, agnostic, no religion |
| residence_state, origin_state | first-level region, full English name; England, Scotland, Wales and Northern Ireland for the UK |
| residence_city, origin_city | English city or town name |
| height | whole centimeters, 120 to 230 |
| weight | whole kilograms, 30 to 300 |
| income | own yearly income in whole US dollars, only when stated in US dollars; hourly times 2080, monthly times 12 |
| education | highest level completed, US Census ACS attainment categories |
| education_subject | US CIP 2020 two-digit families |
| occupation | US SOC 2018 major groups |
| employment_status | employed, self-employed, unemployed, student, retired, homemaker, unable to work |
| marital_status | US Census ACS marital status |
| relationship_status | single, in a relationship, engaged, married |
| parental_status | parent, expecting, no children |
| mental_health | common DSM-5 diagnoses; the first named if several |
| political_compass | Political Compass quadrants plus centrist |
| political_ideology | anarchist, communist, socialist, progressive, liberal, centrist, conservative, libertarian, nationalist |

## Annotators

| role | model | family | why |
|---|---|---|---|
| voter | `gemma4-26b-a4b-nvfp4` | Google | strongest instruction following published (IFEval 96.4, MMLU-Pro 84.8); conservative answers; fast |
| voter | `gpt-oss-20b` (low reasoning) | OpenAI | highest agreement with gemma among fast models (0.54 to 0.58); conservative answers |
| voter | `ministral3-14b` | Mistral | best agreement with gemma among the remaining models fast enough for the budget (0.425, level with qwen3-14b at 0.427), faster than qwen3-14b and a fourth family |
| tiebreaker | `qwen3.6-35b-a3b-nvfp4` | Alibaba | strongest published model available (MMLU-Pro 85.0, GPQA 84.8) and best agreement with gemma (0.595), but only 35 texts/s here, so it only sees records the voters split on |

Agreement is positive agreement: twice the shared values over all values the two models gave. It measures consistency, not accuracy; there is no hand-labeled gold set.

Models considered and dropped, all measured on the same 3,000-text pilot:

| model | reason |
|---|---|
| `qwen3.8-27b-nvfp4` | server hung for 20 minutes at the first CUDA graph capture |
| `qwen3.6-35b-a3b-nvfp4` as a voter | 35 texts/s; vLLM's Mamba "align" prefix caching path, unresolved |
| `qwen3-30b-a3b-2507-awq` | 1,221 values against about 250 from gemma; agreement 0.27 with gemma |
| `mistral-small3.2-24b-nvfp4` | 928 values; agreement 0.38 with gemma; 98 texts/s |
| `glm4.7-flash-awq` | 2,176 values; agreement 0.18 with gemma; 4.6 texts/s |
| `qwen3-14b-fp8` | agreement 0.427 with gemma, like ministral, but slower and the same family as the tiebreaker |

## Voting

Every voter labels every text. A field is resolved when one answer (a value, or none) has at least two votes and more votes than any other answer. Records with any unresolved field go to the tiebreaker, whose vote is added; fields already resolved stay as they were. An invalid answer abstains for that field. Fields still unresolved after the tiebreaker are listed in `unresolved` and are excluded from scoring. Transport failures stop the run; no record is dropped.

## 2026-03 runs

Each run labels 100,000 texts with four server starts and stops, not resumed, and must finish within the annotator's 40-minute limit:

| dataset | minutes | gemma4-26b-a4b-nvfp4 | ministral3-14b | gpt-oss-20b | qwen3.6-35b-a3b-nvfp4 tiebreak |
|---|---|---|---|---|---|
| train0 | 29.2 | 309 s, 413 texts/s | 667 s, 163 texts/s | 521 s, 232 texts/s | 242 s, 451 calls |
| validation | 32.9 | 399 s, 375 texts/s | 746 s, 159 texts/s | 550 s, 231 texts/s | 268 s, 510 calls |

| | gemma | ministral | gpt-oss |
|---|---|---|---|
| values given, train0 | 9,184 | 19,605 | 8,590 |
| invalid fields, train0 | 42 | 156 | 10 |
| failed answers, train0 | 0 | 1 | 1 |

Positive agreement on train0: gemma and gpt-oss 0.533, gemma and ministral 0.463, ministral and gpt-oss 0.355. 77 texts kept an unresolved field; 4,554 texts have at least one resolved value (5,039 in validation).

## Limitations

- Labels are majority votes of three models, not ground truth.
- ministral3-14b gives about 2.3 times as many values as the other voters; voting limits its effect but it is the weakest voter.
- income, language and political_compass have very low voter agreement, so few values resolve for them.
- vLLM runs at 0.80 GPU memory utilization. At 0.88 its total use reached the 32.6 GB of VRAM and Windows spilled into shared memory, dropping gemma from about 300 to 54 texts/s mid-run. Enabling WSL pinned memory was tried and reverted: fast for 15,000 requests, then slower than without it.
