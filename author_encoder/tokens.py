from itertools import chain

import numpy as np
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from . import timed
from .config import LUAR, MAX_LENGTH, TOKEN_BUDGET


@timed
def load_tokenizer():
    tokenizer = Tokenizer.from_file(hf_hub_download(LUAR[0], "tokenizer.json", revision=LUAR[1], local_files_only=True))
    tokenizer.enable_truncation(MAX_LENGTH)
    tokenizer.no_padding()
    return tokenizer


def token_batches(tokenizer, texts, chunk=16384):
    lengths, flat = [], []
    for start in range(0, len(texts), chunk):
        ids = [encoding.ids for encoding in tokenizer.encode_batch(texts[start:start + chunk])]
        lengths.append(np.fromiter(map(len, ids), dtype=np.int64, count=len(ids)))
        flat.append(np.fromiter(chain.from_iterable(ids), dtype=np.int32, count=int(lengths[-1].sum())))
    lengths, flat = np.concatenate(lengths), np.concatenate(flat)
    offsets = np.cumsum(lengths) - lengths
    order = np.argsort(lengths, kind="stable")
    batches = []
    for rows in np.split(order, np.flatnonzero(np.diff(lengths[order])) + 1):
        length = int(lengths[rows[0]])
        step = max(1, TOKEN_BUDGET // length)
        for start in range(0, len(rows), step):
            selected = rows[start:start + step]
            batches.append((selected.astype(np.int32), flat[offsets[selected, None] + np.arange(length)]))
    return batches
