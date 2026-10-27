import json
import math
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download, snapshot_download
from safetensors.torch import load_file
from torch import nn
from torch.nn import functional as F
from transformers import AutoConfig, AutoModel, AutoTokenizer

from . import timed
from .config import CPU_THREADS, DIMENSIONS, ENCODE_BATCH, LUAR, MODEL_FILES, TEXTS_PER_USER


@timed
def download():
    return snapshot_download(LUAR[0], revision=LUAR[1], allow_patterns=list(MODEL_FILES))


@timed
def load_tokenizer():
    return AutoTokenizer.from_pretrained(LUAR[0], revision=LUAR[1], local_files_only=True)


@timed
def load_model(device="cuda"):
    torch.set_num_threads(CPU_THREADS)
    torch.set_float32_matmul_precision("highest")
    return AuthorEncoder().to(device).eval().requires_grad_(False)


class AuthorEncoder(nn.Module):
    @timed
    def __init__(self):
        super().__init__()
        path = hf_hub_download(LUAR[0], "config.json", revision=LUAR[1], local_files_only=True)
        config = AutoConfig.for_model(**json.loads(Path(path).read_text())["backbone_config"])
        config.output_hidden_states = False
        self.transformer = AutoModel.from_config(config, attn_implementation="sdpa")
        self.linear = nn.Linear(config.hidden_size, DIMENSIONS)
        state = load_file(hf_hub_download(LUAR[0], "model.safetensors", revision=LUAR[1], local_files_only=True))
        self.load_state_dict(state, strict=True)

    def encode_texts(self, ids, mask):
        hidden = self.transformer(input_ids=ids, attention_mask=mask, output_hidden_states=False).last_hidden_state.float()
        return (hidden * mask.unsqueeze(-1)).sum(1) / mask.sum(1).clamp_min(1).unsqueeze(1)

    def aggregate(self, texts, valid):
        scores = texts @ texts.transpose(1, 2) / math.sqrt(texts.shape[-1])
        weights = scores.masked_fill(~valid[:, None, :], float("-inf")).softmax(-1)
        values = (weights @ texts).masked_fill(~valid[:, :, None], float("-inf")).amax(1)
        return F.normalize(self.linear(values).float(), dim=-1)

    @timed
    def forward(self, tokens):
        lengths = tokens["attention_mask"].sum(1)
        if not len(lengths) or len(lengths) % TEXTS_PER_USER:
            raise ValueError(f"Each user must have exactly {TEXTS_PER_USER} tokenized texts")
        users = len(lengths) // TEXTS_PER_USER
        device = self.linear.weight.device
        order = torch.argsort(lengths)
        features = torch.empty((len(order), self.transformer.config.hidden_size), device=device, dtype=torch.float32)
        with torch.inference_mode(), torch.autocast(device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
            for start in range(0, len(order), ENCODE_BATCH):
                selected = order[start:start + ENCODE_BATCH]
                width = ((int(lengths[selected[-1]]) + 7) // 8) * 8
                ids = tokens["input_ids"][selected, :width].to(device)
                mask = tokens["attention_mask"][selected, :width].to(device)
                features[selected.to(device)] = self.encode_texts(ids, mask)
            features = features.reshape(users, TEXTS_PER_USER, -1)
            vectors = self.aggregate(features, torch.ones((users, TEXTS_PER_USER), device=device, dtype=torch.bool)).cpu().numpy()
        if vectors.shape != (users, DIMENSIONS) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1., atol=0.002):
            raise ValueError("Invalid author embeddings")
        return vectors
