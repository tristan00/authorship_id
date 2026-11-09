import math

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .config import validate


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
    def __init__(self, targets, specifications, width, depth, expand, dropout, rank, features):
        super().__init__()
        targets = validate(targets)
        if [spec["name"] for spec in specifications] != list(targets) or any(spec["type"] != targets[spec["name"]] for spec in specifications):
            raise ValueError("Target specifications do not match the configured fields")
        self.specifications = specifications
        self.input = nn.Linear(features["dimensions"], width)
        self.blocks = nn.Sequential(*(Block(width, expand, dropout) for _ in range(depth)))
        self.norm = nn.LayerNorm(width)
        self.numeric, self.categorical = ([index for index, spec in enumerate(specifications) if spec["type"] == kind] for kind in ("numeric", "categorical"))
        self.embedding = [index for index, spec in enumerate(specifications) if spec["type"] in ("embedding", "set")]
        self.multiple = [specifications[index]["type"] == "set" for index in self.embedding]
        sizes = [1] * len(self.numeric) + [len(specifications[index]["values"]) for index in self.categorical]
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
                self.head.bias[start:end] = 0
            for index in self.categorical:
                self.head.bias[slice(*self.slices[index])] = torch.tensor(specifications[index]["prior"]).log()
            for slot, index in enumerate(self.embedding):
                prior = torch.tensor(specifications[index]["prior"])
                self.embeddings[slot].bias.copy_(prior.logit() if self.multiple[slot] else prior.log())
        buffers = {"numeric_targets": torch.tensor(self.numeric, dtype=torch.long), "categorical_targets": torch.tensor(self.categorical, dtype=torch.long),
                   "numeric_columns": torch.tensor([self.slices[index][0] for index in self.numeric], dtype=torch.long),
                   "center": torch.tensor([specifications[index]["center"] for index in self.numeric], dtype=torch.float32),
                   "scale": torch.tensor([specifications[index]["scale"] for index in self.numeric], dtype=torch.float32),
                   "baseline": torch.tensor([spec["baseline"] for spec in specifications], dtype=torch.float32),
                   "weight": (counted := torch.tensor([float(spec["training_labels"]) for spec in specifications])) / counted.mean(),
                   "shift": torch.tensor(features["center"], dtype=torch.float32),
                   "factor": 1 / torch.tensor(features["spread"], dtype=torch.float32)}
        for name, value in buffers.items():
            self.register_buffer(name, value, persistent=False)

    def forward(self, vectors):
        return self.norm(self.blocks(self.input((vectors.float() - self.shift) * self.factor)))

    def outputs(self, hidden):
        flat = self.head(hidden)
        result = [None] * len(self.specifications)
        for index, (start, end) in self.slices.items():
            result[index] = flat[:, start:end]
        for slot, index in enumerate(self.embedding):
            result[index] = self.embeddings[slot](hidden)
        return result

    def output(self, hidden, index):
        if index in self.slices:
            start, end = self.slices[index]
            return F.linear(hidden, self.head.weight[start:end], self.head.bias[start:end])
        return self.embeddings[self.embedding.index(index)](hidden)

    def terms(self, hidden, labels, members, capacity=None):
        flat = self.head(hidden).float()
        sums = torch.zeros(len(self.specifications), device=flat.device)
        present = torch.isfinite(labels)
        counts = present.sum(0)
        filled = torch.where(present, labels, 0.)
        overflow = torch.zeros((), dtype=torch.long, device=flat.device)
        if self.numeric:
            normalized = (filled[:, self.numeric_targets] - self.center) / self.scale
            loss = (normalized - flat[:, self.numeric_columns]).abs()
            sums[self.numeric_targets] = (loss * present[:, self.numeric_targets]).sum(0)
        if self.categorical:
            nll = [(F.cross_entropy(flat[:, slice(*self.slices[index])], filled[:, index].long(), reduction="none") * present[:, index]).sum() for index in self.categorical]
            sums = sums.index_copy(0, self.categorical_targets, torch.stack(nll))
        for slot, index in enumerate(self.embedding):
            rows = torch.arange(len(flat), device=flat.device) if capacity is None else torch.argsort((~present[:, index]).byte(), stable=True)[:capacity[slot]]
            logits = self.embeddings[slot](hidden[rows]).float()
            if self.multiple[slot]:
                stated = members[index][rows].long()
                nll = F.softplus(logits).sum(1) - F.pad(logits, (0, 1)).gather(1, stated).sum(1)
            else:
                nll = F.cross_entropy(logits, filled[rows, index].long(), reduction="none")
            sums[index] = (nll * present[rows, index]).sum()
            if capacity is not None:
                overflow += (counts[index] - capacity[slot]).clamp_min(0)
        return sums, counts, overflow

    def loss(self, hidden, labels, members, capacity=None):
        sums, counts, overflow = self.terms(hidden, labels, members, capacity)
        return (sums / counts.clamp_min(1) / self.baseline * self.weight).mean(), overflow


def numeric(output, spec):
    return output[:, 0].float() * spec["scale"] + spec["center"]


def specifications(targets, catalogs, labels, sets):
    result = []
    for column, (name, kind) in enumerate(validate(targets).items()):
        observed = np.asarray(labels[:, column])
        observed = observed[np.isfinite(observed)]
        if len(observed) < 2:
            raise ValueError(f"{name}: fewer than two training labels")
        spec = {"name": name, "type": kind, "training_labels": len(observed)}
        if kind == "numeric":
            center = float(np.median(observed))
            scale = float(np.median(np.abs(observed - center)) * 1.4826)
            if scale <= 0:
                raise ValueError(f"{name}: numeric training labels have no spread")
            spec |= {"center": center, "scale": scale, "baseline": float(np.abs((observed - center) / scale).mean())}
            result.append(spec)
            continue
        values = catalogs[name]
        if len(values) < 2:
            raise ValueError(f"{name}: at least two values are required")
        if kind == "set":
            indptr, members = sets[name]
            lengths = np.diff(indptr)
            stated = int((lengths > 0).sum())
            counts = np.bincount(members, minlength=len(values))
            prior = (counts + .5) / (stated + 1)
            spec |= {"values": values, "counts": counts.tolist(), "prior": prior.tolist(), "mean_size": float(lengths[lengths > 0].mean()), "longest": int(lengths.max()),
                     "baseline": float((counts * -np.log(prior) + (stated - counts) * -np.log1p(-prior)).sum() / stated)}
        else:
            counts = np.bincount(observed.astype(np.int64), minlength=len(values))
            prior = (counts + .5) / (counts.sum() + .5 * len(values))
            spec |= {"values": values, "counts": counts.tolist(), "prior": prior.tolist(), "baseline": float(-np.log(prior[observed.astype(np.int64)]).mean())}
        result.append(spec)
    return result
