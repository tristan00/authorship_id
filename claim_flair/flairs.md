# Flair claims

`flairs.json` maps a (subreddit, author flair) pair to self-claims, one entry `{subreddit, flair, field, value}` per field. Fields and values are claim_extraction's, each a single number or category. `python -m claim_flair load` replaces `flair_claims` with these entries in one transaction.

## How the mapping was built

The mapping is built once, from the 2026-03 month. The scripts and intermediate files are kept outside the repository; only the result is here.

Flairs: every (subreddit, flair, author) of a text with a non-empty author flair, without the `NOT_PEOPLE` authors. That is 6.1M triples, 1.8M (subreddit, flair) pairs, 1.68M distinct flairs and 3.04M authors.

Text evidence: each author's `text_claims` counted by field and value. The author's text value for a field is the value claimed in the most of the author's texts, when no other value is claimed as often: 7.6M (author, field) values over 3.81M authors.

Proposals come from two sources.

- **Segment parser.** The flair is split at `|`, `•`, `·`, commas, semicolons, `" - "`, dashes, brackets and `" / "`. Flag emoji become country names and `:emoji_codes:` become words. Each segment is classified as one of:
  - an age and gender tag (`28M`, `M 31`)
  - pronouns
  - a bare number
  - a country, demonym, state, city, language or job title
  - a value of gender, orientation, religion, generation, race, ideology or political compass

  A segment with spaces that matches none of these is split into spans of up to three words, kept only when every span classifies ("M 31 Texas", "Indian Man"). Otherwise it is `other`. A country proposes residence country and nationality, a demonym proposes nationality and residence country, and a bare number proposes age.
- **Rules extractor.** The candidates `rules.groups` finds in the flair text itself.

Proposals are checked at two levels:

- **Exact pairs.** A (subreddit, flair) pair with at least 10 authors: 64,189 pairs covering 2.38M authors. Each proposal is checked against the authors of the pair. This covers flairs whose meaning is the whole string, such as "Indian Man" in askindianmen or "Canada" in asktheworld.
- **Shapes.** A shape is the ordered list of a flair's segment kinds, such as `tag|state`. In a (subreddit, shape) group with at least 10 authors, every author's own flair value is compared with that author's text value, pooled over all flairs of the shape. A passing group contributes every flair of that shape, each with its own values. This keeps personal flairs like "24 | F | Ohio", which are unique to one author.

An author agrees when the flair value equals the author's text value. For age, a value within one year agrees, because flairs lag birthdays; other numeric fields stay exact. Agreement is measured where at least 10 authors have a text value for the field. An entry is kept when agreement is at least 0.8 and its Wilson 95% lower bound is at least 0.6, so 8 of 10 (lower bound 0.49) is not enough. When the two levels give different values for one (subreddit, flair, field), the key is dropped; this did not happen.

Agreement is bimodal. Exact-equality agreement where at least 10 authors have a text value:

| agreement | exact pairs | shape groups |
|---|---|---|
| < 0.2 | 1,542 | 316 |
| 0.2-0.4 | 409 | 113 |
| 0.4-0.5 | 257 | 103 |
| 0.5-0.6 | 367 | 137 |
| 0.6-0.7 | 419 | 182 |
| 0.7-0.8 | 442 | 210 |
| 0.8-0.9 | 652 | 253 |
| 0.9-0.95 | 464 | 167 |
| >= 0.95 | 579 | 157 |

Proposals supported by both sources agree best: a median of 0.78 at the exact level, against 0.30 for rules-only and 0.00 for parser-only. Rules-only and parser-only proposals are mostly ranges and point counts ("Woman 30 to 40" as age 30, "Partassipant [1]" as age 1).

At agreement 0.8 alone, the mapping had 16,982 entries. The Wilson bound removes 1,666 of them, taking 16,948 author-fields from 10,587 authors. Age within one year adds 2,101 entries and 12,722 author-fields. The new groups include uncut_cock (bare numbers, 0.83 over 2,469 authors with a text age), twentyagers (0.81 over 1,852), uncut (0.88), teenagersbutworse (0.85) and onlyteenagersallowed (0.83).

## Result

17,417 entries for 14,341 (subreddit, flair) pairs in 627 subreddits: 1,571 from exact pairs and 15,846 from shapes. They give 307,271 authors a flair claim. In 263,720 author-fields the author had no text value for that field.

| field | entries | authors | authors without a text value |
|---|---|---|---|
| gender | 4,298 | 150,381 | 91,676 |
| nationality | 3,674 | 96,264 | 81,921 |
| residence_country | 2,369 | 30,129 | 24,963 |
| age | 3,164 | 29,177 | 6,944 |
| residence_state | 1,382 | 18,147 | 14,485 |
| origin_country | 35 | 16,778 | 15,682 |
| occupation | 1,173 | 15,041 | 10,563 |
| religion | 301 | 7,522 | 4,949 |
| residence_city | 502 | 4,759 | 2,533 |
| sexual_orientation | 289 | 3,001 | 1,899 |
| generation | 118 | 2,592 | 2,141 |
| parental_status | 27 | 2,359 | 1,137 |
| marital_status | 27 | 2,346 | 1,220 |
| race_ethnicity | 34 | 2,151 | 1,529 |
| relationship_status | 5 | 746 | 622 |
| mental_health | 5 | 592 | 405 |
| height | 6 | 484 | 315 |
| political_ideology | 3 | 376 | 317 |
| employment_status | 4 | 263 | 199 |
| birth_year | 1 | 256 | 220 |

The largest mappings:

- askmenadvice "man" is gender male: 30,377 authors, 0.91.
- asktheworld flag-and-name flairs give nationality: 242 flairs, 52,117 authors, 0.86.
- goonedmeetup tags give age (0.86) and gender (0.98): 270 flairs, 14,202 authors.
- askindianmen "Indian Man" is gender male: 0.90.
- fragtmaenner "M | 26-35" is gender male, and the range is ignored: 0.89.
- askanamerican `state|state` flairs give residence state: 0.83.

## Limitations

- Agreement is measured against extracted text claims, not against ground truth.
- Bare-number age flairs in the large teen subreddits fail even within one year. r/teenagers has 0.60 over 5,724 authors with a text age: 45% exact, 15% one year apart and 30% five or more years apart, mostly with the text age higher. indianteenagers has 0.60, askteenboys 0.67, thirtiesindia 0.66, teenindia 0.70 and twentiesindia 0.74.
- Country flairs in sports and travel subreddits pass as nationality just above the line (2westerneurope4u, cricket, olympics, rugbyunion and travel, 0.80 to 0.82).
- The mapping is static. Flairs and subreddits that first appear after 2026-03, or that had fewer than 10 authors then, have no entries until it is rebuilt.
