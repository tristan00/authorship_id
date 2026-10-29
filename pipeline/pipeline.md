# Month pipeline

`python -m pipeline --month YYYY-MM` takes one month from the Reddit dumps to the explorer. Each step does only what is still missing, so a rerun after a crash continues where it stopped and a rerun after success only checks. Every step logs its entry and exit with timings to `pipeline.log`.

1. Download (`reddit_dumps.download.download`): the month's comment and submission dumps by torrent, skipped when the month is loaded. libtorrent resume data keeps finished pieces across runs.
2. Load (`database.load.add`), skipped when the month is in `months`. It drops the four b-tree indexes of `records` and deletes the month's records, which the BRIN index `records_created` finds without a full scan. It copies the dumps into `records` and `bodies_stage`, rebuilds `bodies`, builds the missing indexes and freezes both tables. The `months` row, with the number of records copied, is written last, so an interrupted load starts over.
3. Clean: while the month's dumps are on disk, it checks that `records` holds exactly the copied rows within the month's bounds, then deletes the two dumps. Once the torrent holds no dumps, it also deletes the torrent directory with its `.torrent` and `.resume` files.
4. Claim extraction (`claim_extraction.run.run`): every month with `months.extracted_at` empty; see `claim_extraction/annotation.md`.
5. Consolidation (`claim_consolidation.consolidate.consolidate`): rebuilds `claim_evidence` and `author_claims` over all loaded months, unless `consolidation` covers exactly the loaded months and started after the last extraction.
6. Vectors (`author_encoder.update.update`): text vectors for new bodies, then the user vector store; see `author_encoder/encoder.md`. It needs the GPU, and nothing may hold the user vector store open.
7. Explorer (`explorer.prepare.prepare`): rebuilt unless `explorer_totals.run_id` is the current consolidation run.

## State

- `bodies.month`: the month whose load first added a text. A rebuild keeps the stored month when a text reappears, so a text belongs to one month for good. Extraction and text vectors find new texts by month and `text_sha256` range, never by heap position, because each load rewrites `bodies`.
- `months`: `records` (rows copied), `loaded_at` and `extracted_at`.
- `consolidation`: the months covered and when the run started and finished.
- `explorer_totals.run_id`: the consolidation the explorer was built from.

Staging tables (`bodies_stage`, `bodies_next`, `text_claims_parts`, `explorer_counts`) exist only while their step runs. While a load runs, `records` has no b-tree indexes, so record lookups from the explorer are slow until it ends.
