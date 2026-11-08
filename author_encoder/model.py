import json
import math
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download, snapshot_download
from safetensors.torch import load_file
from torch import nn
from torch.nn import functional as F
from transformers import AutoConfig, AutoModel

from . import timed
from .config import AGGREGATE_USERS, CPU_THREADS, CUDA_MEMORY, DIMENSIONS, LUAR, MODEL_FILES


@timed
def download():
    return snapshot_download(LUAR[0], revision=LUAR[1], allow_patterns=list(MODEL_FILES))


@timed
def load_model(device="cuda"):
    torch.set_num_threads(CPU_THREADS)
    model = AuthorEncoder().to(device).eval().requires_grad_(False)
    if device == "cuda":
        torch.cuda.set_per_process_memory_fraction(CUDA_MEMORY / torch.cuda.get_device_properties(device).total_memory)
        torch.backends.cuda.matmul.allow_fp16_accumulation = True
        model.transformer.half()
    return model


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
        for layer in self.transformer.encoder.layer:
            attention = layer.attention.self
            attention.register_buffer("qkv_weight", torch.cat([attention.query.weight, attention.key.weight, attention.value.weight]).detach(), persistent=False)
            attention.register_buffer("qkv_bias", torch.cat([attention.query.bias, attention.key.bias, attention.value.bias]).detach(), persistent=False)

    def pooled(self, tokens):
        size, length = tokens.shape
        hidden = self.transformer.embeddings(input_ids=tokens).view(size * length, -1)
        for layer in self.transformer.encoder.layer:
            attention = layer.attention.self
            qkv = F.linear(hidden, attention.qkv_weight, attention.qkv_bias).view(size, length, 3, attention.num_attention_heads, -1)
            context = F.scaled_dot_product_attention(*qkv.permute(2, 0, 3, 1, 4))
            hidden = layer.attention.output.LayerNorm(layer.attention.output.dense(context.transpose(1, 2).reshape(size * length, -1)) + hidden)
            hidden = layer.output.LayerNorm(layer.output.dense(layer.intermediate(hidden)) + hidden)
        return hidden.view(size, length, -1).mean(1, dtype=torch.float32)

    @timed
    def features(self, batches, count):
        rows, tokens, shapes = batches
        device = self.linear.weight.device
        rows, tokens = (torch.from_numpy(array).pin_memory().to(device, non_blocking=True).long() for array in (rows, tokens))
        features = torch.empty((count, self.transformer.config.hidden_size), dtype=torch.float16, device=device)
        done = used = 0
        with torch.inference_mode():
            for size, length in shapes:
                features[rows[done:done + size]] = self.pooled(tokens[used:used + size * length].view(size, length)).half()
                done, used = done + size, used + size * length
        return features

    def aggregate(self, texts, lengths):
        present = torch.arange(texts.shape[1], device=texts.device) < lengths[:, None]
        scores = (texts @ texts.transpose(1, 2) / math.sqrt(texts.shape[-1])).masked_fill(~present[:, None, :], -math.inf)
        attended = (scores.softmax(-1) @ texts).masked_fill(~present[:, :, None], -math.inf)
        return F.normalize(self.linear(attended.amax(1)), dim=-1)

    @timed
    def users(self, features, lengths):
        if not len(lengths) or lengths.min() < 1 or lengths.sum() != len(features):
            raise ValueError("Each user needs at least one text and the features must cover every text")
        starts = np.cumsum(lengths) - lengths
        found = []
        with torch.inference_mode():
            for start in range(0, len(lengths), AGGREGATE_USERS):
                counts = lengths[start:start + AGGREGATE_USERS]
                width = np.arange(counts.max())
                rows = torch.as_tensor(np.where(width < counts[:, None], starts[start:start + AGGREGATE_USERS, None] + width, 0), device=features.device)
                found.append(self.aggregate(features[rows].float(), torch.as_tensor(counts, device=features.device)))
            vectors = torch.cat(found).cpu().numpy()
        if vectors.shape != (len(lengths), DIMENSIONS) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1., atol=0.002):
            raise ValueError("Invalid author embeddings")
        return vectors
