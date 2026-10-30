# Month pipeline

`python -m pipeline --month YYYY-MM` takes one month from the Reddit dumps to the explorer. Each step does only what is still missing, so a rerun after a crash continues where it stopped and a rerun after success only checks. Every step logs its entry and exit with timings to `pipeline.log`.

1. Download (`reddit_dumps.download.download`): the month's comment and submission dumps by torrent, skipped when the month is loaded. libtorrent resume data keeps finished pieces across runs. Once it finishes, the following month downloads in a background process (logged to `download.log`) while the month is processed, when the catalog lists it and it is not loaded; the run waits for it at the end.
2. Load (`database.load.add`), skipped when the month is in `months`. `records` is range partitioned on `created_utc` and `bodies` is list partitioned on `month`, one partition of each per month. The load drops the month's partitions, copies the dumps into a detached `records_YYYY_MM` and the unlogged `bodies_stage`, then builds `bodies_YYYY_MM` from the staged texts whose hash is in no other partition, frozen as it is copied. In parallel it freezes `records_YYYY_MM` and builds its four b-tree indexes. Both partitions are then attached, so older months are never rewritten, reindexed or vacuumed. The `months` row, with the number of records copied, is written last, so an interrupted load starts over.
3. Clean: while the month's dumps are on disk, it checks that `records` holds exactly the copied rows within the month's bounds, then deletes the two dumps. Once the torrent holds no dumps, it also deletes the torrent directory with its `.torrent` and `.resume` files.
4. Claim extraction (`claim_extraction.run.run`): every month with `months.extracted_at` empty; see `claim_extraction/annotation.md`.
5. Consolidation (`claim_consolidation.consolidate.consolidate`), unless `consolidation` covers exactly the loaded months and started after the last extraction. When the previous run covered a subset of the loaded months and none of them was loaded or extracted after it started, it appends the evidence of the added months to `claim_evidence` and reconsolidates only the authors with new evidence. The distinct authors of the added evidence are collected with hash aggregation off: under the step's parallel settings the planner estimated 188k distinct authors among 2026-05's 25M evidence rows (there are 4.0M) and chose a two-level parallel hash aggregate whose final stage produced about 100 authors per second for an hour; the sort takes 5 s. Otherwise it rebuilds `claim_evidence` and `author_claims` over all months.
6. Vectors (`author_encoder.update.update`, then `author_encoder.update.users`): text vectors for new bodies, then the months the user vector store lacks, recomputing only the users whose sample the new records change; see `author_encoder/encoder.md`. It runs in its own process from the end of the clean step, alongside steps 4, 5 and 7, and the run waits for it at the end. It needs the GPU, and nothing may hold the user vector store open.
7. Explorer (`explorer.prepare.prepare`): rebuilt unless `explorer_totals.run_id` is the current consolidation run. When the consolidation extended the run the explorer was built from, it merges the added months' activity into `explorer_activity` and recomputes `explorer_texts` only for the authors active in those months. It runs in one transaction.

## State

- `bodies.month`: the month whose load first added a text. A text belongs to one month for good. Extraction and text vectors find new texts by month and `text_sha256` range, which reads only that month's partition.
- `months`: `records` (rows copied), `loaded_at` and `extracted_at`.
- `empty_bodies`: the bodies whose clean text is empty, by month, written by the text vector step when it finishes a month. User vectors skip their records.
- `consolidation`: the months covered, when the run started and finished, and for an appending run the run it extended (`base`) and the months it added (`added`).
- `explorer_totals.run_id`: the consolidation the explorer was built from.

`records_2026_03_2026_04` and `bodies_2026_03_2026_04` hold the two months loaded before partitioning; the load refuses to reload either of those months.

Staging tables (`bodies_stage`, `text_claims_parts`, `claim_evidence_added`, `claim_authors`, `explorer_added`, `explorer_touched`, `explorer_counts`) exist only while their step runs.
