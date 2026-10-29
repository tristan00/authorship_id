# Author encoder

The encoder is the pinned LUAR model `config.LUAR`. Its transformer turns a text into a 768-dimensional feature: the mean of the last hidden states over the text's tokens, at most `MAX_LENGTH` tokens after `clean`. Its head turns 64 such features into a 512-dimensional unit user vector: scaled dot-product attention over the 64 features, a maximum over texts, a linear layer and normalization. Text features are computed once and stored; user vectors apply only the head to stored features and never rerun the transformer.

## Stores

Both stores are Lance datasets on C:, which holds no Postgres data.

- `TEXT_STORE` (`C:\reddit_data\text_vectors\bodies.lance`): one row per body whose `clean` text is nonempty. Columns: `text_sha256` (32 bytes, the `bodies` key), `part` (first heap page of the part it came from) and `vector` (768 × float16). It has no indexes: text vectors are read only by `text_sha256`, through the user build's hash map. A row takes about 1.6 KB.
- `VECTOR_STORE` (`C:\reddit_data\user_vectors.lance`): one row per eligible author. Columns: `author`, `usable_texts`, `sample_ids` (the 64 record ids) and `vector` (512 × float32). The schema metadata key `protocol` records the model, sampling and source query. Indexes: IVF_RQ with cosine distance on `vector`, a B-tree on `author`.

A body is usable exactly when its hash is in the text store. Records reach their feature through `records.text_sha256`.

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

`texts` reads the source table in parts of `PART_PAGES` heap pages by ctid range. `PREPARE_WORKERS` processes copy `text_sha256, text`, apply `clean`, drop empty texts and tokenize. Tokenizing uses `tokens.load_tokenizer`, the `tokenizers` library on the pinned `tokenizer.json` with the same ids as the transformers tokenizer, in chunks into flat int32 arrays. `tokens.token_batches` groups texts of exactly equal token length into batches of at most `TOKEN_BUDGET` tokens. The main process runs the transformer in bfloat16 on the GPU without an attention mask, which gives the same features as padded batches up to float16 rounding. A writer thread appends each part as one Lance fragment. Appends are atomic, and a rerun skips every part already in the `part` column. The GPU is the limit: about 38k texts per second on an idle RTX 5090. `torch.compile` is unavailable because Windows has no Triton.

## User vectors

`index` samples like the earlier encoder. It considers records whose author is not in `database.NO_AUTHOR` and whose `text_status` is `available` or `title_only`, ordered by `md5('luar-user-vector-64-v1:' || record_id), record_id`. An author with at least 64 usable records gets the first 64. One query (`index.SOURCE`) returns each author's ordered record ids and hashes. Rows are located through a map of 8-byte hash prefixes to row positions, read from the text store's hash column. Each fetched row's full hash is checked against the request, so a prefix collision fails instead of returning a wrong vector. `FETCH_THREADS` threads take `FETCH_ROWS` rows each. The head runs on CPU, `HEAD_USERS` users at a time, and each batch is appended to `user_vectors.building.lance`. A rerun checks the protocol and continues after the last appended author. When the query ends the store is compacted and indexed, then renamed to `VECTOR_STORE`; a store exists under that name only when complete.

`index.similar` is an approximate nearest-neighbour search with `USER_SEARCH`, excluding the author. `index.vector` returns an author's row. The explorer and `demographic_model.data.export` read the store through these functions and the dataset.

## Commands

```
python -m author_encoder download
python -m author_encoder texts --source bodies
python -m author_encoder index
python -m author_encoder similar AUTHOR --limit 50
python -m author_encoder vector AUTHOR
python -m author_encoder encode --input users.jsonl --output vectors.jsonl
```

`texts --source` takes any table with `text_sha256` and `text`, optionally schema-qualified, and `--limit` encodes at most that many remaining parts. `encode` reads JSONL authors with their texts, samples 64 usable texts per author and runs the full model; it does not use the stores.

## Memory

The writer's process tree must stay under 20 GB of private memory. On 9.86 million bodies it peaked at 12.6 GB private and 4.5 GB resident. These causes were found and removed:

- On Windows, GPU allocations count as committed host memory, though not as resident RAM. Exact-length batches have about 190 shapes per part, and the CUDA caching allocator kept a block of each, so it reserved 5 to 9 GB while allocating at most 1.4 GB. `load_model` caps it at `CUDA_MEMORY`, which costs no speed.
- `transformers.AutoTokenizer` imports torch, about 2.5 GB per worker. Workers use `tokens.py` and import no torch; `texts.write` imports the model only in the main process.
- A whole part's tokenizer output as Python objects costs several GB per worker for large parts, because every token becomes a Python integer and a Rust encoding. Parts stay at 8000 pages, and tokenizing in chunks into int32 arrays keeps a part's tokens near its int32 size.

The user build holds the hash map, 12 bytes per text row (about 3.7 GB for 307 million rows, about twice that while sorting), plus one batch of features. pylance 14.0.2 also panics when writing fixed-size lists of strings, so `sample_ids` is a variable list whose length the build checks.
