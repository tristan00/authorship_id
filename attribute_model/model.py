import math

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from author_encoder.config import DIMENSIONS

from .config import QUANTILES, validate


class Block(nn.Module):
    def __init__(self, width, expand, dropout):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.up = nn.Linear(width, width * expand)
        self.down = nn.Linear(width * expand, width)
        self.dropout = nn.Dropout(dropout)

    def forward(self, hidden):
        return hidden + self.dropout(self.down(F.gelu(self.up(self.norm(hidden)))))


class LabelEmbedding(nn.Module):
    def __init__(self, width, labels, rank):
        super().__init__()
        self.projection = nn.Linear(width, rank, bias=False)
        self.labels = nn.Parameter(torch.randn(labels, rank) * .02)
        self.bias = nn.Parameter(torch.zeros(labels))

    def forward(self, hidden):
        return self.projection(hidden) @ self.labels.T / math.sqrt(self.labels.shape[1]) + self.bias


class AttributeModel(nn.Module):
    def __init__(self, targets, specifications, width, depth, expand, dropout, rank):
        super().__init__()
        targets = validate(targets)
        if [spec["name"] for spec in specifications] != list(targets) or any(spec["type"] != targets[spec["name"]] for spec in specifications):
            raise ValueError("Target specifications do not match the configured fields")
        self.specifications = specifications
        self.input = nn.Linear(DIMENSIONS, width)
        self.blocks = nn.Sequential(*(Block(width, expand, dropout) for _ in range(depth)))
        self.norm = nn.LayerNorm(width)
        self.numeric, self.categorical, self.embedding = ([index for index, spec in enumerate(specifications) if spec["type"] == kind] for kind in ("numeric", "categorical", "embedding"))
        sizes = [len(QUANTILES)] * len(self.numeric) + [len(specifications[index]["values"]) for index in self.categorical]
        offsets = np.cumsum([0] + sizes)
        self.slices = dict(zip(self.numeric + self.categorical, zip(offsets[:-1].tolist(), offsets[1:].tolist())))
        self.head = nn.Linear(width, int(offsets[-1]))
        self.embeddings = nn.ModuleList(LabelEmbedding(width, len(specifications[index]["values"]), rank) for index in self.embedding)
        with torch.no_grad():
            self.head.weight.normal_(std=.01)
            self.head.bias.zero_()
            for index in self.numeric:
                start, end = self.slices[index]
                self.head.weight[start:end].zero_()
                self.head.bias[start:end] = torch.tensor(specifications[index]["quantiles"])
            for index in self.categorical:
                self.head.bias[slice(*self.slices[index])] = torch.tensor(specifications[index]["prior"]).log()
            for slot, index in enumerate(self.embedding):
                self.embeddings[slot].bias.copy_(torch.tensor(specifications[index]["prior"]).log())
        widest = max((len(specifications[index]["values"]) for index in self.categorical), default=1)
        positions = [row * widest + offset for row, index in enumerate(self.categorical) for offset in range(len(specifications[index]["values"]))]
        buffers = {"numeric_targets": torch.tensor(self.numeric, dtype=torch.long), "categorical_targets": torch.tensor(self.categorical, dtype=torch.long),
                   "numeric_columns": torch.tensor([self.slices[index][0] for index in self.numeric], dtype=torch.long), "positions": torch.tensor(positions, dtype=torch.long),
                   "center": torch.tensor([specifications[index]["center"] for index in self.numeric], dtype=torch.float32),
                   "scale": torch.tensor([specifications[index]["scale"] for index in self.numeric], dtype=torch.float32),
                   "quantiles": torch.tensor(QUANTILES, dtype=torch.float32),
                   "baseline": torch.tensor([spec["baseline"] for spec in specifications], dtype=torch.float32)}
        for name, value in buffers.items():
            self.register_buffer(name, value, persistent=False)
        self.widest = widest
        self.first_categorical = int(offsets[len(self.numeric)])

    def forward(self, vectors):
        return self.norm(self.blocks(self.input(vectors * math.sqrt(DIMENSIONS))))

    def outputs(self, hidden):
        flat = self.head(hidden)
        result = [None] * len(self.specifications)
        for index, (start, end) in self.slices.items():
            result[index] = flat[:, start:end]
        for slot, index in enumerate(self.embedding):
            result[index] = self.embeddings[slot](hidden)
        return result

    def terms(self, hidden, labels, capacity=None):
        flat = self.head(hidden).float()
        sums = torch.zeros(len(self.specifications), device=flat.device)
        present = torch.isfinite(labels)
        counts = present.sum(0)
        filled = torch.where(present, labels, 0.)
        overflow = torch.zeros((), dtype=torch.long, device=flat.device)
        if self.numeric:
            normalized = (filled[:, self.numeric_targets] - self.center) / self.scale
            error = normalized[..., None] - flat[:, self.numeric_columns[:, None] + torch.arange(len(QUANTILES), device=flat.device)]
            loss = torch.maximum(self.quantiles * error, (self.quantiles - 1) * error).mean(-1)
            sums[self.numeric_targets] = (loss * present[:, self.numeric_targets]).sum(0)
        if self.categorical:
            padded = torch.full((len(flat), len(self.categorical) * self.widest), -math.inf, device=flat.device)
            padded = padded.index_copy(1, self.positions, flat[:, self.first_categorical:]).view(len(flat), len(self.categorical), self.widest)
            nll = -padded.log_softmax(-1).gather(2, filled[:, self.categorical_targets].long()[..., None]).squeeze(2)
            sums[self.categorical_targets] = (nll * present[:, self.categorical_targets]).sum(0)
        for slot, index in enumerate(self.embedding):
            rows = torch.arange(len(flat), device=flat.device) if capacity is None else torch.argsort((~present[:, index]).byte(), stable=True)[:capacity[slot]]
            nll = F.cross_entropy(self.embeddings[slot](hidden[rows]).float(), filled[rows, index].long(), reduction="none")
            sums[index] = (nll * present[rows, index]).sum()
            if capacity is not None:
                overflow += (counts[index] - capacity[slot]).clamp_min(0)
        return sums, counts, overflow

    def loss(self, hidden, labels, capacity=None):
        sums, counts, overflow = self.terms(hidden, labels, capacity)
        return (sums / counts.clamp_min(1) / self.baseline).mean(), overflow


def numeric(output, spec):
    values = (output.float() * spec["scale"] + spec["center"]).sort(1).values
    return values[:, 1], values[:, 0], values[:, 2]


def specifications(targets, catalogs, labels, training):
    result = []
    for column, (name, kind) in enumerate(validate(targets).items()):
        observed = np.asarray(labels[training, column])
        observed = observed[np.isfinite(observed)]
        if len(observed) < 2:
            raise ValueError(f"{name}: fewer than two training labels")
        spec = {"name": name, "type": kind, "training_labels": len(observed)}
        if kind == "numeric":
            center = float(np.median(observed))
            scale = float(np.median(np.abs(observed - center)) * 1.4826)
            if scale <= 0:
                raise ValueError(f"{name}: numeric training labels have no spread")
            normalized = (observed - center) / scale
            quantiles = np.quantile(normalized, QUANTILES)
            baseline = np.mean([np.maximum(q * (normalized - v), (q - 1) * (normalized - v)).mean() for q, v in zip(QUANTILES, quantiles)])
            spec |= {"center": center, "scale": scale, "quantiles": quantiles.tolist(), "baseline": float(baseline)}
        else:
            values = catalogs[name]
            if len(values) < 2:
                raise ValueError(f"{name}: at least two categorical values are required")
            counts = np.bincount(observed.astype(np.int64), minlength=len(values))
            prior = (counts + .5) / (counts.sum() + .5 * len(values))
            spec |= {"values": values, "counts": counts.tolist(), "prior": prior.tolist(), "baseline": float(-np.log(prior[observed.astype(np.int64)]).mean())}
        result.append(spec)
    return result
