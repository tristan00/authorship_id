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
from .config import CPU_THREADS, CUDA_MEMORY, DIMENSIONS, LUAR, MODEL_FILES


@timed
def download():
    return snapshot_download(LUAR[0], revision=LUAR[1], allow_patterns=list(MODEL_FILES))


@timed
def load_model(device="cuda"):
    torch.set_num_threads(CPU_THREADS)
    model = AuthorEncoder().to(device).eval().requires_grad_(False)
    if device == "cuda":
        torch.cuda.set_per_process_memory_fraction(CUDA_MEMORY / torch.cuda.get_device_properties(device).total_memory)
        model.transformer.to(torch.bfloat16)
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

    def host(self, features):
        copy = torch.empty(features.shape, dtype=features.dtype, pin_memory=True).copy_(features, non_blocking=True)
        done = torch.cuda.Event()
        done.record()

        def wait():
            done.synchronize()
            return copy.numpy()
        return wait

    def aggregate(self, texts):
        scores = texts @ texts.transpose(1, 2) / math.sqrt(texts.shape[-1])
        return F.normalize(self.linear((scores.softmax(-1) @ texts).amax(1)), dim=-1)

    @timed
    def users(self, features):
        with torch.inference_mode():
            vectors = self.aggregate(torch.as_tensor(features, device=self.linear.weight.device).float()).cpu().numpy()
        if vectors.shape != (len(features), DIMENSIONS) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1., atol=0.002):
            raise ValueError("Invalid author embeddings")
        return vectors

    def project(self, features):
        with torch.inference_mode():
            return F.normalize(self.linear(features.float()), dim=-1)
