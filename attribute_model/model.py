import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import timed
from .config import validate
from .heads import Grid, Joint, Number, Scale, Tree, options


class Block(nn.Module):
    def __init__(self, width, expand, dropout):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.up = nn.Linear(width, width * expand)
        self.down = nn.Linear(width * expand, width)
        self.dropout = nn.Dropout(dropout)

    def forward(self, hidden):
        return hidden + self.dropout(self.down(F.gelu(self.up(self.norm(hidden)))))


def choices_for(structures):
    found = {}
    for name, structure in structures.items():
        key = "mbti" if structure.get("axes") else name
        found[key] = options(structure, structures)
    return found


def heads(specs, structures, choices, width, rank, device):
    columns = {spec["name"]: column for column, spec in enumerate(specs)}
    built = {}
    for spec in specs:
        name, structure = spec["name"], structures[spec["name"]]
        kind = structure["kind"]
        if structure.get("axes"):
            if choices["mbti"] == "joint":
                built.setdefault("mbti", Joint(structure["axes"], [columns[axis] for axis in structure["axes"]], width, rank, device))
                continue
            built[name] = Tree(name, columns[name], structure, "flat", width, rank, device)
        elif kind == "number":
            built[name] = Number(name, columns[name], spec, choices[name], width, rank, device)
        elif kind == "scale":
            born = None
            if choices[name] == "born":
                source, starts = specs[columns[structure["born"]["from"]]], structure["born"]["starts"]
                born = (columns[source["name"]], int(np.floor(min(source["low"], starts[0] - 1))), int(np.ceil(max(source["high"], 2 * starts[-1] - starts[-2]))))
            built[name] = Scale(name, columns[name], structure, choices[name], width, rank, device, born)
        elif kind == "grid":
            built[name] = Grid(name, columns[name], structure, choices[name], width, rank, device)
        else:
            built[name] = Tree(name, columns[name], structure, choices[name], width, rank, device, columns.get(structure.get("groups")))
    return built


class AttributeModel(nn.Module):
    def __init__(self, targets, specifications, structures, choices, width, depth, expand, dropout, rank, features, device="cuda"):
        super().__init__()
        targets = validate(targets)
        if [spec["name"] for spec in specifications] != list(targets):
            raise ValueError("Target specifications do not match the configured fields")
        self.specifications, self.structures, self.choices = specifications, structures, choices
        self.input = nn.Linear(features["dimensions"], width)
        self.blocks = nn.Sequential(*(Block(width, expand, dropout) for _ in range(depth)))
        self.norm = nn.LayerNorm(width)
        self.heads = nn.ModuleDict(heads(specifications, structures, choices, width, rank, device))
        self.register_buffer("shift", torch.tensor(features["center"], dtype=torch.float32), persistent=False)
        self.register_buffer("factor", 1 / torch.tensor(features["spread"], dtype=torch.float32), persistent=False)
        self.register_buffer("baseline", torch.ones(len(self.heads)), persistent=False)
        self.register_buffer("weight", torch.ones(len(self.heads)), persistent=False)

    def forward(self, vectors):
        return self.norm(self.blocks(self.input((vectors.float() - self.shift) * self.factor)))

    def terms(self, hidden, batch, limited=True):
        found = [head.loss(hidden, batch, limited=limited) for head in self.heads.values()]
        sums, counts, overflow = (torch.stack(items) for items in zip(*found))
        return sums, counts, overflow.sum()

    def loss(self, hidden, batch):
        sums, counts, overflow = self.terms(hidden, batch)
        return (sums / counts.clamp_min(1) / self.baseline * self.weight).mean(), overflow


@timed
def specifications(targets, catalogs, columns):
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
            spec |= {"center": center, "scale": scale, "low": float(np.min(observed)), "high": float(np.max(observed))}
        else:
            spec |= {"values": catalogs[name]}
            if len(catalogs[name]) < 2:
                raise ValueError(f"{name}: at least two values are required")
        result.append(spec)
    return result
