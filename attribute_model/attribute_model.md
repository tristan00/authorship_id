# Attribute model

The attribute model predicts an author's consolidated self claims (`author_claims`) from the author's LUAR user vector (`author_encoder`, 512 dimensions). `targets.json` lists the attributes it trains on and predicts, each as `numeric`, `categorical` or `embedding`; `prepare`, `train` and `predict` all read it, and a model or prepared dataset built from another list is refused. `embedding` is a categorical attribute with too many values for a full output layer (cities): its head scores values as dot products with learned value embeddings of rank `rank`.

## Commands

```
python -m attribute_model prepare
python -m attribute_model train
python -m attribute_model user AUTHOR
python -m attribute_model predict --input vectors.jsonl --output predictions.jsonl
```

`prepare` writes `C:\reddit_data\attribute_model\data`, `train` writes `C:\reddit_data\attribute_model\model.pt`, and every command takes `--targets` for another target list. `user` predicts from an author's stored user vector; `predict` reads JSONL lines with a `vector` (and an `id` or `author`), such as the output of `python -m author_encoder encode`, and writes one line of predictions per input.

## Data

`prepare` copies the claims of the configured attributes out of `author_claims` in one `COPY`, then scans the user vector store once (`author`, `vector`) and keeps every author with a claim, holding the store's lock and one repeatable-read snapshot of the database; it refuses to publish if the user store does not match the loaded months or the consolidation changed meanwhile. Values are encoded per attribute: numbers as floats, categories as indices into a catalog ordered by frequency. Authors are split by `sha256("attribute-model:" + casefold(author))` into ten buckets: 0 to 6 train, 7 validation, 8 calibration, 9 test, so an author keeps its split across rebuilds. Every claim and every sampled text stays in the input, including the texts the claims were extracted from.

With the 2026-03 and 2026-04 consolidation, 9,455,893 claims of the 18 configured attributes give 5,480,202 authors with a user vector and at least one label; `prepare` takes 10 minutes, most of it the scan of the 27,999,464-row store. Numeric claims outside `claim_extraction.config.NUMERIC` are not labels, and the manifest counts them per attribute: 176,616 ages, mostly 1 to 12 (26,696 claim 1 and 29,666 claim 2, largely children's ages extracted as the author's), and up to 777. With them, the 5% quantile of age followed the extraction error and adult authors got predicted ages under 10; without them the test MAE of age fell from 6.19 to 5.55 and its interval from 27.1 to 24.4 years.

## Model

The vector, scaled by √512, passes through a linear layer to `width`, `depth` pre-norm residual MLP blocks (`expand` × `width` hidden, GELU, dropout) and a final layer norm. One linear layer produces every numeric and categorical output; each `embedding` attribute has its own low-rank head. Categorical biases start at the log prior of the training values, numeric outputs at the training median.

Numeric attributes are standardized by the training median and 1.4826 × the median absolute deviation. Each has three outputs, the 5%, 50% and 95% quantiles, trained with the pinball loss and sorted at prediction; the value is the median. Conformalized quantile regression widens or narrows the 5% to 95% band by one calibrated amount per attribute, so an author's interval depends on the author. Against one point output with a smooth L1 loss and a fixed conformal radius, on validation, the MAE was the same (age 6.20 against 6.21, height 8.17 against 8.15, weight 18.27 against 18.29, birth year 10.12 against 10.24), coverage stayed at 90%, and the mean age interval fell from 31.7 to 27.1 years (median 21.4); height, weight and birth year intervals changed by under 2%.

The loss of each attribute is its mean over the batch rows that have a label, divided by the loss of the training prior (the prior's cross entropy, or the loss of always predicting the median), and the attributes are averaged with equal weight. Validation selects the epoch with the lowest mean of these ratios: 1 is no better than the prior.

## Training

Training keeps every split on the GPU (5.5M × 512 float16 vectors and their labels, about 6 GB) and draws batches by index, so no data crosses the bus during an epoch. The step runs in bfloat16 autocast and is captured once as a CUDA graph (forward, backward, gradient clipping and fused AdamW with a device-side learning rate), then replayed per batch; the learning rate warms up over 3% of the steps and follows a cosine to zero. Categorical attributes share one padded log-softmax. The `embedding` heads, whose catalogs hold 9,531 and 5,573 values, score only the rows with a label: the rows are moved to the front and a fixed number are scored, 8 standard deviations above the expected labelled rows per batch, and an epoch fails if any batch held more. On the full data (width 1024, depth 2, batch 4096) these steps took an epoch from 67 s to 3.0 s at 92% GPU use:

| step | ms per 4,096-row step | epoch |
|---|---|---|
| one head and loss per attribute, rows selected by boolean masks | 70 | 67 s |
| the same with multiplied masks, no host syncs | 15.6 | 15 s |
| one fused head and padded log-softmax | 8.5 | 8.2 s |
| `index_copy` padding instead of an indexed gather, whose backward serialized on atomics into the pad column | 5.7 | 5.5 s |
| CUDA graph | 5.1 | 4.9 s |
| labelled rows only in the `embedding` heads | | 3.0 s |

float32 with TF32 matrix products took 6.7 ms per step against 5.1 in bfloat16. The tuned model (batch 2048) takes 4.9 s per epoch and 41 s for `train` including loading, calibration and the test report.

## Calibration and test

The calibration split fits one softmax temperature per categorical attribute and a split-conformal correction per numeric attribute for 90% intervals. Predictions report the top five values with calibrated probabilities, or a value with its interval. The test split is used once, for the report saved in the model.

On the 547,931 test authors (the model trained on 3,836,176):

| attribute | labels | accuracy or MAE | log loss or 90% interval |
|---|---|---|---|
| age | 361,588 | MAE 5.55 (median 8.74) | 0.902 coverage, width 24.4 (median 20.1) |
| birth_year | 8,639 | MAE 10.27 (median 13.52) | 0.890 coverage, width 47.0 (median 47.3) |
| generation | 15,374 | 0.551 (majority 0.378), top 5 0.946 | log loss 1.334 (prior 1.711), ECE 0.013 |
| nationality | 48,830 | 0.783 (majority 0.245), top 5 0.926 | log loss 0.936 (prior 3.144), ECE 0.008 |
| language | 7,250 | 0.606 (majority 0.542), top 5 0.916 | log loss 1.324 (prior 2.133), ECE 0.029 |
| residence_country | 67,598 | 0.794 (majority 0.277), top 5 0.935 | log loss 0.860 (prior 2.835), ECE 0.010 |
| residence_state | 58,129 | 0.653 (majority 0.123), top 5 0.863 | log loss 1.331 (prior 3.674), ECE 0.015 |
| residence_city | 75,928 | 0.401 (majority 0.040), top 5 0.627 | log loss 3.312 (prior 6.418), ECE 0.026 |
| origin_country | 20,302 | 0.687 (majority 0.168), top 5 0.867 | log loss 1.351 (prior 3.751), ECE 0.012 |
| origin_state | 7,474 | 0.489 (majority 0.126), top 5 0.794 | log loss 1.910 (prior 3.913), ECE 0.015 |
| origin_city | 7,246 | 0.291 (majority 0.045), top 5 0.529 | log loss 4.307 (prior 6.386), ECE 0.031 |
| height | 39,096 | MAE 8.23 (median 10.57) | 0.902 coverage, width 33.7 (median 33.5) |
| weight | 20,955 | MAE 18.39 (median 20.72) | 0.901 coverage, width 79.8 (median 74.8) |
| education | 18,410 | 0.418 (majority 0.263), top 5 0.870 | log loss 1.803 (prior 2.463), ECE 0.019 |
| education_subject | 13,925 | 0.499 (majority 0.183), top 5 0.842 | log loss 1.668 (prior 2.754), ECE 0.008 |
| occupation | 64,169 | 0.506 (majority 0.141), top 5 0.808 | log loss 1.831 (prior 3.066), ECE 0.007 |
| marital_status | 67,276 | 0.905 (majority 0.888), top 5 0.997 | log loss 0.315 (prior 0.485), ECE 0.004 |
| relationship_status | 26,355 | 0.726 (majority 0.341), top 5 0.983 | log loss 0.809 (prior 1.461), ECE 0.009 |

## Tuning

The stored user vector is the input. On 87,882 labelled users of four store fragments, the mean of the user's sampled 768-dimensional text features scored 0.816 against 0.776 for the user vector and 0.781 for both; a single text feature scored 0.944, so the model predicts from user vectors only. With all 5.6M authors instead of a 2M sample the same configuration went from 0.631 to 0.589: data size dominates.

Validation curves pick one epoch for all attributes: choosing each attribute's best epoch separately gained 0.003 (0.5949 to 0.5920), because nearly all peak within two epochs of each other. Optuna (TPE, 136 trials of 12 to 60 s, about an hour) searched width 256 to 4096, depth 1 to 4, expansion 1 to 4, dropout, input dropout, embedding rank 16 to 256, batch 1024 to 16384, learning rate, weight decay and 3 to 16 epochs on the full data with the smooth L1 numeric loss. The best eight trials lay within 0.001 of each other (0.5775 to 0.5785) at width 1024, depth 3, expansion 1, rank 128, batch 2048, six epochs, dropout 0.27 to 0.30, weight decay 0.2 to 0.35 and learning rate 1.3 to 1.7e-3, against 0.5880 for the starting configuration (width 1024, depth 2, dropout 0.1, weight decay 0.01) and 0.618 at 2M authors for the configuration the package was first written with (width 128, depth 1, rank 32). Input dropout went to zero and was removed. `config.PARAMETERS` holds the chosen values. Validation scores of runs with quantile outputs are higher (0.591) because the numeric ratios use the pinball loss of the prior.
