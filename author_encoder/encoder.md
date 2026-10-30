# Author encoder

The encoder is the pinned LUAR model `config.LUAR`. Its transformer turns a text into a 768-dimensional feature: the mean of the last hidden states over the text's tokens, at most `MAX_LENGTH` tokens after `clean`. Its head turns 64 such features into a 512-dimensional unit user vector: scaled dot-product attention over the 64 features, a maximum over texts, a linear layer and normalization. Text features are computed once and stored; user vectors apply only the head to stored features and never rerun the transformer.

## Stores

Both stores are Lance datasets on C:, which holds no Postgres data.

- `TEXT_STORE` (`C:\reddit_data\text_vectors\bodies.lance`): one row per body whose `clean` text is nonempty. Columns: `text_sha256` (32 bytes, the `bodies` key) and `vector` (768 × int8). Every fragment is sorted by `text_sha256`. Schema metadata: `int8_scales`, the 768 dequantization scales, and `months`, each fully encoded month with the `loaded_at` it was encoded from. The user update reads text vectors by row address, finding the address of a newly sampled record once from the hash columns. A row takes about 0.8 KB; 2026-03 is 307,272,845 rows in 229 GiB.
- `VECTOR_STORE` (`C:\reddit_data\user_vectors.lance`): one row per author with at least one usable record, sorted by `author_hash`. Columns: `author`, `author_hash`, `usable_texts`, `sample_ids` (up to 256 record ids, by priority), `sample_priorities`, `sample_rows` (each sampled text's text store row address, fragment id × 2^32 + offset) and `vector` (512 × float32). Schema metadata: `protocol` records the model, sampling and source query, and `source` the months with their `loaded_at`, the bucket count and the text store fragments the row addresses point into. Indexes: IVF_RQ with cosine distance on `vector`, a B-tree on `author`. 2026-03 and 2026-04 are 27,999,464 users in 77 GiB.

A body is usable exactly when its hash is in the text store; `empty_bodies` (`month`, `text_sha256`) lists the others, whose clean text is empty. Records reach their feature through `records.text_sha256`.

## Store choice

Lance with an IVF_RQ index was chosen by measuring stores on the text features, when the plan still included searching them. Text search has since been dropped; Lance holds both stores, and IVF_RQ indexes the user vectors. Every candidate stored the same real 768-dimensional features. Recall is against exact cosine top-50 from a GPU brute-force scan, for 1000 held-out queries; latency is the single-query median. Each candidate has three query settings, from fast to accurate, shown as recall@10 at milliseconds. Peak memory is the process working set, or the whole WSL VM for the WSL servers.

| candidate | rows | ingest rows/s | build | peak memory | disk GiB | recall@10 at ms |
|---|---|---|---|---|---|---|
| Lance IVF_RQ | 10M | 337k | 188 s | 7.9 GB | 19.7 | 0.959 at 9.9, 0.982 at 19.8, 0.997 at 45 |
| Lance IVF_PQ | 10M | 299k | 196 s on GPU | not recorded | about 16 | 0.829 at 20.5, 0.935 at 69, 0.968 at 239 |
| FAISS IVF-PQ, fp16 rerank | 10M | 29k | 543 s | 10.0 GB | 15.3 | 0.884 at 4.1, 0.897 at 8.5, 0.933 at 21.5 |
| flat fp16, GPU brute force | 10M | – | – | 18.2 GB and 15 GB VRAM | 14.3 | 0.998 at 10 |
| Lance IVF_RQ | 1M | 364k | 53 s | 3.2 GB | 2.0 | 0.971 at 5.8, 0.987 at 16.5, 0.996 at 37 |
| Lance IVF_SQ | 1M | 300k | 55 s | 3.4 GB | 2.2 | 0.971 at 8.7, 0.990 at 21, 0.999 at 51 |
| Lance IVF_PQ | 1M | 332k | 109 s on GPU | 4.7 GB | 1.6 | 0.880 at 15, 0.971 at 34, 0.990 at 90 |
| Lance IVF_HNSW_SQ | 1M | 364k | 35 s | 3.5 GB | 2.4 | 0.864 at 2.1, 0.936 at 3.1, 0.954 at 5.6 |
| FAISS IVF-PQ, fp16 rerank | 1M | 60k | 87 s | 4.5 GB | 1.5 | 0.904 at 1.2, 0.915 at 5.2, 0.954 at 13 |
| USearch HNSW f16 | 1M | 4.5k | 221 s | 4.4 GB | 1.6 | 0.882 at 1.4, 0.917 at 2.5, 0.934 at 4.3 |
| USearch HNSW i8 | 1M | 8.1k | 124 s | 3.6 GB | 0.85 | 0.809 at 0.9, 0.828 at 1.6, 0.839 at 2.6 |
| Qdrant on-disk HNSW, int8 | 1M | 35k | 25 s | 7.9 GB private | 2.75 | 0.939 at 1.6, 0.944 at 1.8 |
| Qdrant on-disk HNSW, binary | 1M | 34k | 15 s | 6.7 GB private | 2.4 | 0.929 at 1.6, 0.932 at 1.6 |
| DuckDB VSS HNSW, fp32 | 1M | 58k | 148 s | 13.5 GB | 5.8 | 0.886 at 4.5, 0.919 at 5.2, 0.936 at 6.6 |
| Chroma (hnswlib) | 1M | 3.1k | 323 s | 5.0 GB | 3.2 | 0.918 at 1.1 |
| pgvector halfvec HNSW (WSL) | 1M | 9.1k | 72 s | 17.5 GB | 3.85 | 0.897 at 3.1, 0.928 at 6.1, 0.942 at 11.2 |
| pgvectorscale DiskANN (WSL) | 1M | 17k | about 25 min | 22.7 GB | – | 0.863 at 7.7, 0.926 at 13, 0.938 at 22.5 |
| Milvus DiskANN (WSL) | 1M | about 42k | stopped at the RAM floor after 13 min | 22.9 GB | – | – |

A month holds about 300 million distinct bodies, far more than RAM. HNSW stores need their graph or quantized vectors in memory and mostly stay below 0.95 recall. pgvectorscale and Milvus build too slowly or use too much memory. FAISS keeps no keys or raw vectors, and the Windows build cannot keep inverted lists on disk. Lance IVF_RQ has the best recall for its latency of the stores that keep everything on disk. It ingests nearly nine times faster than the encoder produces features, needs no server, and keeps keys, vectors and indexes in one store. Its recall barely drops from 1M to 10M rows. IVF_SQ reaches the same recall but is slower and has a larger index.

## Text vectors

`texts.write` encodes every loaded month that the text store's `months` metadata does not list with the same `loaded_at`. A month's texts are `bodies WHERE month = M`, read in `HASH_PARTS` parts of equal `text_sha256` range; `bodies` stays sorted by hash, so each part is one index range scan of about 300,000 rows. `PREPARE_WORKERS` processes copy `text_sha256, text` and drop every body whose full hash is already in a store fragment overlapping the part's range; each fragment's first and last hash bound it, so a part reads one to three fragments. They apply `clean` to the rest, drop empty texts, sort by hash and tokenize. Tokenizing uses `tokens.load_tokenizer`, the `tokenizers` library on the pinned `tokenizer.json` with the same ids as the transformers tokenizer, in chunks into flat int32 arrays. `tokens.token_batches` sorts a part's texts by token length and returns that order, the tokens in that order as one flat int32 array, and the batch shapes: texts of exactly equal length, at most `TOKEN_BUDGET` tokens per batch. The main process copies the order and the tokens to the GPU once per part through pinned memory and runs the transformer in bfloat16 without an attention mask, which gives the same features as padded batches up to float16 rounding. `AuthorEncoder.pooled` runs the transformer's layers itself, with the query, key and value projections fused into one matrix product, and nothing in the batch loop waits for the GPU, so kernels queue ahead of Python. `AuthorEncoder.host` starts copying a part's features into pinned host memory and hands the writer a function that waits for the copy, so the next part starts while it runs. A writer thread quantizes each part to int8 and appends it as one sorted Lance fragment. Appends are atomic and the membership check is exact, so a rerun after a failure encodes only what is still missing, and a month is recorded in `months` only after all its parts. Rewriting the existing 2026-03 store this way would add nothing: three sample parts found every body already stored. The GPU is the limit. On a fixed sample of 1,000,000 April bodies, run three times through `texts.encode` with four workers, the writer encodes about 43k texts per second with the GPU busy 97% of the time, against 35k and 81% (three runs, 34.5k to 36.4k) when the forward pass synchronized with the host three times per batch; the features are bit-identical. The 2026-04 write ran at 37k texts per second before this change. Flash attention is not in the Windows build of PyTorch, so SDPA uses the memory-efficient kernel. cuDNN attention was four times slower; the GELU fused into cuBLASLt (46.8k) and float16 accumulation (52k) moved int8 codes by up to 2 and 6 steps; token budgets from 16k to 64k and cuBLASLt changed speed by less than run-to-run noise, and 128k does not fit `CUDA_MEMORY`. `torch.compile` is unavailable because Windows has no Triton. Workers also return the hashes of the bodies they clean to empty; once every month is written, `texts.record_empty` replaces those months' rows of `empty_bodies` with them, before the months are stamped. In 2026-03 and 2026-04, 95,304 and 95,356 bodies clean to empty and are not stored; they were listed in `empty_bodies` once, as the bodies absent from the store.

## Int8 text vectors

Features are stored as int8 with one symmetric scale per dimension: `q = clip(round(x / s), -127, 127)` and `x ≈ q × s`. Each `s` is the largest absolute value of its dimension over the 307,272,845 features of 2026-03, divided by 127; those largest values run from 1.13 to 7.49, median 2.13. `texts.quantize` quantizes, `texts.write` reads the scales from `TEXT_STORE` so every month uses one quantizer, and `index.TextStore` dequantizes. A value beyond its scale saturates at ±127. `texts.write` logs clipped values per part and returns their total, so a shift in the features shows before the scales need refitting; 2026-03 has none by construction.

int8 was measured against the float16 features before the store was converted:

| measure | result |
|---|---|
| text feature cosine, the 3.2M sampled features of 50,000 users | min 0.999764, mean 0.999909 |
| user vector cosine, all 1,182,315 users | min 0.999841, mean 0.999993 |
| top-10 neighbours, int8 query against the float16-based store, 2,000 users | overlap 0.9925, identical for 92.5% |
| top-10 neighbours, int8 on both sides among 50,000 users, 2,000 users | overlap 0.9921, identical for 92.0% |
| bytes per row | 804 instead of 1,572 |
| 2026-03 text store | 230 GiB instead of 449 GiB |

The conversion kept every hash. On a million random rows the dequantized features had cosine at least 0.999794 to the float16 ones, and no value was off by more than half a step.

## User vectors

`index.build` keeps one row per author with at least one usable record: a record whose author is not in `database.NO_AUTHOR`, whose `text_status` is `available` or `title_only` and whose body is not in `empty_bodies`. A record's priority is `index.digest(record_id, SAMPLE_SEED)`, 64-bit FNV-1a over the UTF-8 bytes finished with splitmix64. A user's sample is the up to 256 usable records with the smallest priorities, and `usable_texts` counts all of them. The 256 smallest of a union are the 256 smallest of the old sample and the new records, so adding a month needs only the store's rows and the month's records, never older records. The store records the months it covers, and `build` adds the loaded months it lacks. It rebuilds from an empty store when the protocol, the bucket count or a covered month's `loaded_at` changed, or when a text store fragment the row addresses point into changed; a full build is the same code adding every month to an empty store.

Facts are computed once, where their data is already read: `texts.write` lists the bodies that clean to empty in `empty_bodies` when it finishes a month, the priority is computed once when a record is first read, and a sampled text's row address is found once and kept in `sample_rows`. An update runs four passes, each over one part of the data at a time, spilling to `VECTOR_WORK`:

1. `collect` reads the added months' records in `RECORD_BLOCKS` block ranges of the `records` partitions, one autocommit `COPY` of `author, record_id, text_sha256` per range of a few seconds, so it holds no transaction and no lock beyond one short statement. It drops records whose hash is in `empty_bodies`, hashes authors and record ids, and appends each record to one of `BUCKETS` spills by the top byte of `author_hash`.
2. `sample` streams the old store in `author_hash` order, so a bucket's rows arrive together, and merges each bucket with its new records: new users, updated `usable_texts` and the new sample. A user whose sample did not change keeps its vector. Only users with a newly sampled record are recomputed; their sampled texts become requests, by stored row address for old samples and by hash for new ones, spilled by the first hash byte.
3. `fetch` resolves each part's hashes against the hash columns of the store fragments covering the part and reads every requested row once with sorted `take`s, which at the density of a full build is as fast as a scan; random single-row reads ran at 66k rows per second against 1.45M for a fragment scan. Features are spilled by bucket.
4. `encode` dequantizes a bucket's features and runs the head on CPU for its recomputed users, sorted by length and padded to the longest in batches of at most `HEAD_TEXTS` texts. Padded texts are masked out of the attention and the maximum. Each bucket is appended to `user_vectors.building.lance`.

The new store is then indexed and stamped with `source`, the current store is renamed to `user_vectors.previous.lance`, the new one takes its place and the previous one is deleted. A failure or kill at any point leaves the current store as it was; the next run deletes the partial build and spills and starts the update over. A store whose `source` matches the loaded months is not rebuilt. The swap renames directories, which Windows refuses while another process holds files inside, so readers of the user store must be stopped while it runs.

For 2026-03 and 2026-04, 27,999,464 authors have a usable record, 739,999,788 records are usable, 550,516,171 texts are sampled and 510,193 users have 256; an independent SQL count over `records` and `empty_bodies` gave the same four numbers. The full build took 100 minutes: 19 for `collect` (740,235,584 records in 252 statements of about 4.5 seconds), 9 for `sample`, 21 for `fetch`, 49 for `encode` and 3 for the indexes. `encode` is limited by the single-threaded numpy dequantization and padding of each head batch. The full build of 2026-03 under the earlier protocol (64 texts, 1,182,315 users) took 32 minutes. On the 109,464 users of bucket 0, adding 2026-04 to the store built from 2026-03 took 891 seconds, 584 of them in `collect`, the scan of the new month, and 283 in `fetch`, of which reading every fragment's hash column takes most; it ran alongside the end of the full build. It recomputed 77,259 users and refetched 2,016,320 texts, 94% of the bucket's sampled texts, because the users active in the new month hold most of them; its rows matched the full build's in authors, `usable_texts`, samples, priorities and row addresses, with vectors within 2e-7 (1.8e-7). On a schema of a non-superuser role with 1,907 users of both months, the incremental and the full build also matched, as did a pure-Python sample of each user and the head run on each user alone, and a build killed during `encode` left the store as it was and completed on the rerun.

`index.similar` is an approximate nearest-neighbour search with `USER_SEARCH`, excluding the author. On 500 random users against exact search, `USER_SEARCH` (200 probes, refine factor 40) returned the exact top 10 for all of them at 9.5 ms median; 100 probes with refine factor 20 gave recall 0.997 at 5.9 ms. `index.vector` returns an author's row. The explorer and `demographic_model.data.export` read the store through these functions and the dataset.

## Commands

```
python -m author_encoder download
python -m author_encoder update
python -m author_encoder users
python -m author_encoder similar AUTHOR --limit 50
python -m author_encoder vector AUTHOR
python -m author_encoder encode --input users.jsonl --output vectors.jsonl
```

`update` runs `update.update`, the pipeline's vector step: it encodes the missing bodies, then deletes old Lance versions and unreferenced files in the text store. `users` runs `update.users`, the pipeline step after it: it refuses to start unless the text store's `months` match the loaded months, adds the months the user store lacks, then deletes old versions in the user store. Both hold a lock on the text store and point `TMP` and `TEMP` at `VECTOR_WORK`, which they empty before and after, so no spill outlives them even after a crash. `encode` reads JSONL authors with their texts, samples up to 256 usable texts per author and runs the full model; it does not use the stores.

## Memory

The writer's process tree must stay under 20 GB of private memory. On 9.86 million bodies it peaked at 12.6 GB private and 4.5 GB resident, and on the 2026-03 write at 12.9 GB private and 4.8 GB resident. Pinned buffers for features waiting for the writer add about 1.4 GB: on the 1,000,000-body April sample the tree peaked at 15.5 GB private and 7.0 GB resident, against 14.1 GB and 6.4 GB before them. These causes were found and removed:

- On Windows, GPU allocations count as committed host memory, though not as resident RAM. Exact-length batches have about 190 shapes per part, and the CUDA caching allocator kept a block of each, so it reserved 5 to 9 GB while allocating at most 1.4 GB. `load_model` caps it at `CUDA_MEMORY`, which costs no speed.
- `transformers.AutoTokenizer` imports torch, about 2.5 GB per worker. Workers use `tokens.py` and import no torch; `texts.write` imports the model only in the main process.
- A whole part's tokenizer output as Python objects costs several GB per worker for large parts, because every token becomes a Python integer and a Rust encoding. Parts stay near 300,000 bodies, and tokenizing in chunks into int32 arrays keeps a part's tokens near its int32 size.

The update and the user build must each stay under 16 GB. The user update holds one bucket or one hash part at a time: the empty-body hashes, one block range of records, a bucket's records, users and features, or a part's requests, hash columns and features. The full 2026-03 and 2026-04 build peaked at 8.6 GB private and 8.5 GB resident, in `encode`, and its spills and staging store at 485 GB on C:; the bucket-0 update peaked at 6.8 GB, in `encode`. pylance 14.0.2 also panics when writing fixed-size lists of strings, so `sample_ids` is a variable list.
