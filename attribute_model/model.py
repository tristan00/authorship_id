import math

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import timed
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
        classes, shapes = {}, {}
        for index in self.categorical:
            classes.setdefault(len(specifications[index]["values"]), []).append(index)
        for slot, index in enumerate(self.embedding):
            shapes.setdefault((self.multiple[slot], len(specifications[index]["values"])), []).append(slot)
        self.categorical_groups = [(size, len(heads)) for size, heads in classes.items()]
        self.shapes = list(shapes.items())
        self.layouts = {}
        grouped = [index for heads in classes.values() for index in heads]
        buffers = {"numeric_targets": torch.tensor(self.numeric, dtype=torch.long), "categorical_targets": torch.tensor(self.categorical, dtype=torch.long),
                   "categorical_order": torch.tensor(grouped, dtype=torch.long), "categorical_columns": torch.tensor([column for index in grouped for column in range(*self.slices[index])], dtype=torch.long),
                   "embedding_targets": torch.tensor(self.embedding, dtype=torch.long),
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

    def layout(self, capacity):
        key = None if capacity is None else tuple(capacity)
        if key not in self.layouts:
            groups = {}
            for (multiple, size), slots in self.shapes:
                for slot in slots:
                    groups.setdefault((multiple, size, None if capacity is None else capacity[slot]), []).append(slot)
            device = self.embedding_targets.device
            with torch.inference_mode(False):
                self.layouts[key] = ([(multiple, size, rows, slots, torch.tensor(slots, device=device), torch.tensor([self.embedding[slot] for slot in slots], device=device))
                                      for (multiple, size, rows), slots in groups.items()], None if capacity is None else torch.tensor(capacity, device=device))
        return self.layouts[key]

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
            nll, first, column = [], 0, 0
            for size, heads in self.categorical_groups:
                targets = self.categorical_order[first:first + heads]
                logits = flat.index_select(1, self.categorical_columns[column:column + heads * size]).view(-1, size)
                nll.append((F.cross_entropy(logits, filled[:, targets].long().view(-1), reduction="none").view(len(flat), heads) * present[:, targets]).sum(0))
                first, column = first + heads, column + heads * size
            sums = sums.index_copy(0, self.categorical_order, torch.cat(nll))
        if self.embedding:
            groups, limits = self.layout(capacity)
            order = None if capacity is None else torch.argsort((~present[:, self.embedding_targets]).byte(), dim=0, stable=True)
            rows = [None if capacity is None else order[:capacity[slot], slot] for slot in range(len(self.embedding))]
            logits = [self.embeddings[slot](hidden if capacity is None else hidden[rows[slot]]).float() for slot in range(len(self.embedding))]
            parts = []
            for multiple, size, count, slots, positions, columns in groups:
                stacked = torch.stack([logits[slot] for slot in slots])
                selected = None if capacity is None else order[:count].index_select(1, positions)
                chosen = (present[:, columns] if capacity is None else present[selected, columns]).T
                if multiple:
                    stated = [members[self.embedding[slot]] if capacity is None else members[self.embedding[slot]][rows[slot]] for slot in slots]
                    longest = max(part.shape[1] for part in stated)
                    stated = torch.stack([F.pad(part.long(), (0, longest - part.shape[1]), value=size) for part in stated])
                    nll = F.softplus(stacked).sum(2) - F.pad(stacked, (0, 1)).gather(2, stated).sum(2)
                else:
                    target = (filled[:, columns] if capacity is None else filled[selected, columns]).T.long()
                    nll = F.cross_entropy(stacked.view(-1, size), target.reshape(-1), reduction="none").view(len(slots), -1)
                parts.append((nll * chosen).sum(1))
            sums = sums.index_copy(0, torch.cat([columns for *_, columns in groups]), torch.cat(parts))
            if capacity is not None:
                overflow = (counts[self.embedding_targets] - limits).clamp_min(0).sum()
        return sums, counts, overflow

    def loss(self, hidden, labels, members, capacity=None):
        sums, counts, overflow = self.terms(hidden, labels, members, capacity)
        return (sums / counts.clamp_min(1) / self.baseline * self.weight).mean(), overflow


def numeric(output, spec):
    return output[:, 0].float() * spec["scale"] + spec["center"]


@timed
def specifications(targets, catalogs, columns, sets):
    result = []
    for observed, (name, kind) in zip(columns, validate(targets).items()):
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
            stated, longest, size, counts = sets[name]
            prior = (counts + .5) / (stated + 1)
            spec |= {"values": values, "counts": counts.tolist(), "prior": prior.tolist(), "mean_size": size / stated, "longest": longest,
                     "baseline": float((counts * -np.log(prior) + (stated - counts) * -np.log1p(-prior)).sum() / stated)}
        else:
            counts = np.bincount(observed.astype(np.int64), minlength=len(values))
            prior = (counts + .5) / (counts.sum() + .5 * len(values))
            spec |= {"values": values, "counts": counts.tolist(), "prior": prior.tolist(), "baseline": float(-np.log(prior[observed.astype(np.int64)]).mean())}
        result.append(spec)
    return result
