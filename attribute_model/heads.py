import math

import torch
from torch import nn
from torch.nn import functional as F

from .structure import Graph

RANKED = 256
QUANTILES = (.1, .2, .3, .4, .5, .6, .7, .8, .9)
TINY = 1e-30


def leaves_of(parents, size):
    used = {parent for parent in parents if parent >= 0}
    return [node for node in range(size) if node not in used and parents[node] >= -1]


def options(structure, structures):
    kind = structure["kind"]
    if kind == "number":
        return ["point", "laplace", "quantile", "bins"]
    if kind == "scale":
        return ["flat", "ordinal"] + (["born"] if structure.get("born") and structure["born"]["from"] in structures else [])
    if kind == "grid":
        return ["flat", "axes"]
    if structure.get("axes"):
        return ["separate", "joint"]
    found, size = ["flat"], len(structure["nodes"])
    for key, parents in structure["groupings"].items():
        suffix = "" if len(structure["groupings"]) == 1 else f":{key}"
        if not structure["single"] or not set(structure["values"]) <= set(leaves_of(parents, size)):
            found.append("tree" + suffix)
        if any(parent >= 0 for parent in parents):
            found.append("levels" + suffix)
    return found


def prior(counts):
    return (counts + .5) / (counts.sum() + .5 * len(counts))


def depths(parents):
    depth = torch.ones_like(parents)
    current = parents.clone()
    while bool((current >= 0).any()):
        depth += (current >= 0).long()
        current = torch.where(current >= 0, parents[current.clamp_min(0)], current)
    return depth


def layers(parents):
    depth = depths(parents)
    return [(depth == level).nonzero().squeeze(1) for level in range(2, int(depth.max()) + 1)]


def upward(values, parents, levels):
    for nodes in reversed(levels):
        values.index_add_(1, parents[nodes], values[:, nodes])
    return values


class Output(nn.Module):
    def __init__(self, width, size, rank):
        super().__init__()
        self.ranked = size > RANKED
        if self.ranked:
            self.projection = nn.Linear(width, rank, bias=False)
            self.labels = nn.Parameter(torch.randn(size, rank) * .02)
            self.bias = nn.Parameter(torch.zeros(size))
        else:
            self.linear = nn.Linear(width, size)
            with torch.no_grad():
                self.linear.weight.normal_(std=.01)
                self.linear.bias.zero_()

    def offset(self):
        return self.bias if self.ranked else self.linear.bias

    def forward(self, hidden):
        if self.ranked:
            return self.projection(hidden) @ self.labels.T / math.sqrt(self.labels.shape[1]) + self.bias
        return self.linear(hidden)


class Head(nn.Module):
    capacity = None

    def __init__(self, targets, columns, size, width, rank):
        super().__init__()
        self.targets, self.columns, self.size = targets, columns, size
        self.output = Output(width, size, rank)
        self.register_buffer("column_index", torch.tensor(columns), persistent=False)

    def forward(self, hidden):
        return self.output(hidden)

    def present(self, batch):
        return torch.isfinite(batch.labels[:, self.column_index]).any(1)

    def loss(self, hidden, batch, temperature=1., limited=True):
        present = self.present(batch)
        rows = torch.arange(len(present), device=present.device)
        overflow = present.new_zeros((), dtype=torch.long)
        if self.capacity is not None and limited:
            rows = torch.argsort((~present).byte(), stable=True)[:self.capacity]
            overflow = (present.sum() - self.capacity).clamp_min(0)
            present = present[rows]
        terms = self.terms(self.forward(hidden[rows]).float(), batch, rows, temperature)
        return torch.where(present, terms, 0.).sum(), present.sum(), overflow

    def initialize(self, counts):
        pass


class Tree(Head):
    def __init__(self, name, column, structure, representation, width, rank, device, group=None):
        self.mode, _, key = representation.partition(":")
        graph = Graph(structure, device)
        key = key or next(iter(structure["groupings"]))
        parents = structure["groupings"][key]
        leaves = leaves_of(parents, graph.size)
        size = {"flat": len(structure["values"]), "tree": len(leaves), "levels": graph.size}[self.mode]
        super().__init__([name], [column] + ([group] if group is not None and self.mode != "flat" else []), size, width, rank)
        self.name, self.single, self.graph, self.key = name, structure["single"], graph, key
        self.register_buffer("parents", torch.tensor(parents, device=device), persistent=False)
        self.register_buffer("leaves", torch.tensor(leaves, device=device), persistent=False)
        self.register_buffer("outside", self.parents < -1, persistent=False)
        values = graph.values
        found = graph.ancestors[values]
        keep = found < graph.size
        membership = torch.zeros((len(values), graph.size), device=device)
        membership[torch.arange(len(values), device=device)[:, None].expand_as(found)[keep], found[keep]] = 1
        self.register_buffer("membership", membership, persistent=False)
        self.register_buffer("named", torch.zeros(graph.size, dtype=torch.bool, device=device).index_fill(0, values, True), persistent=False)
        self.chain = layers(self.parents)
        self.others = []
        for other, found in graph.groupings.items():
            if other != key:
                internal = torch.zeros(graph.size, dtype=torch.bool, device=device)
                internal[found[found >= 0]] = True
                self.others.append((internal, found, layers(found)))

    def log_nodes(self, logits):
        if self.mode == "tree":
            full = logits.new_zeros((len(logits), self.graph.size))
            full[:, self.leaves] = logits.softmax(1)
            return upward(full, self.parents, self.chain).clamp_min(TINY).log()
        logits = logits.masked_fill(self.outside, -torch.inf)
        slots = torch.where(self.parents >= 0, self.parents, self.graph.size)
        peak = logits.new_full((len(logits), self.graph.size + 1), -torch.inf).scatter_reduce(1, slots.expand_as(logits), logits, "amax")
        shifted = logits - peak[:, slots]
        total = logits.new_zeros((len(logits), self.graph.size + 1)).index_add_(1, slots, shifted.exp())
        log = shifted - total[:, slots].clamp_min(TINY).log()
        for nodes in self.chain:
            log[:, nodes] = log[:, nodes] + log[:, self.parents[nodes]]
        return log

    def terms(self, logits, batch, rows, temperature):
        logits = logits / temperature
        if self.mode == "flat" and self.single:
            return F.cross_entropy(logits, batch.labels[rows, self.columns[0]].nan_to_num(0).long(), reduction="none")
        if self.mode == "flat":
            return F.softplus(logits).sum(1) - F.pad(logits, (0, 1)).gather(1, batch.raw[self.name][rows]).sum(1)
        truth = batch.truth[self.name][rows]
        valid = truth < self.graph.size
        picked = F.pad(self.log_nodes(logits), (0, 1)).gather(1, truth)
        return -torch.where(valid, picked, 0.).sum(1) / valid.sum(1).clamp_min(1)

    def nodes(self, logits, temperature=1.):
        logits = logits.float() / temperature
        if self.mode == "flat" and self.single:
            return logits.softmax(1) @ self.membership
        if self.mode == "flat":
            probability = logits.new_zeros((len(logits), self.graph.size))
            probability[:, self.graph.values] = logits.sigmoid()
            for nodes in reversed(self.chain):
                nodes = nodes[~self.named[self.parents[nodes]]]
                probability.scatter_reduce_(1, self.parents[nodes].expand(len(logits), -1), probability[:, nodes], "amax")
            return probability
        probability = self.log_nodes(logits).exp()
        for internal, parents, levels in self.others:
            probability = upward(probability.masked_fill(internal, 0.), parents, levels)
        return probability

    def initialize(self, counts):
        with torch.no_grad():
            if self.mode == "flat":
                self.output.offset().copy_(prior(counts).log() if self.single else prior(counts).logit())
            elif self.mode == "tree":
                self.output.offset().copy_(prior(counts[self.leaves]).log())


class Scale(Head):
    def __init__(self, name, column, structure, representation, width, rank, device, born=None):
        self.mode, count = representation, len(structure["names"])
        if self.mode == "born":
            born_column, low, high = born
            super().__init__([name], [column, born_column], high - low + 1, width, rank)
            self.low = low
            years = torch.arange(low, high + 1, device=device, dtype=torch.float32)
            self.register_buffer("position", torch.bucketize(years, torch.tensor(structure["born"]["starts"], device=device, dtype=torch.float32), right=True), persistent=False)
        else:
            super().__init__([name], [column], 1 if self.mode == "ordinal" else count, width, rank)
        if self.mode == "ordinal":
            self.cuts = nn.Parameter(torch.zeros(count - 1))
        self.name, self.count = name, count

    def nodes(self, logits, temperature=1.):
        logits = logits.float()
        if self.mode == "ordinal":
            cuts = self.cuts[:1] + torch.cat([self.cuts.new_zeros(1), F.softplus(self.cuts[1:]).cumsum(0)])
            below = torch.sigmoid((cuts[None, :] - logits) / temperature)
            below = torch.cat([below.new_zeros((len(below), 1)), below, below.new_ones((len(below), 1))], 1)
            return below.diff(dim=1).clamp_min(TINY)
        probability = (logits / temperature).softmax(1)
        if self.mode == "born":
            return probability.new_zeros((len(probability), self.count)).index_add_(1, self.position, probability).clamp_min(TINY)
        return probability.clamp_min(TINY)

    def terms(self, logits, batch, rows, temperature):
        truth = batch.truth[self.name][rows]
        valid = truth < self.count
        log = F.pad(self.nodes(logits, temperature).log(), (0, 1)).gather(1, truth)
        own = -torch.where(valid, log, 0.).sum(1) / valid.sum(1).clamp_min(1)
        if self.mode != "born":
            return own
        year = batch.labels[rows, self.columns[1]]
        index = (year.nan_to_num(self.low) - self.low).round().long().clamp(0, self.size - 1)
        exact = -(logits / temperature).log_softmax(1).gather(1, index[:, None]).squeeze(1)
        return own + torch.where(torch.isfinite(year), exact, 0.)

    def initialize(self, counts):
        with torch.no_grad():
            if self.mode == "flat":
                self.output.offset().copy_(prior(counts).log())
            elif self.mode == "ordinal":
                cumulative = prior(counts).cumsum(0)[:-1].clamp(1e-4, 1 - 1e-4).logit()
                self.cuts.copy_(torch.cat([cumulative[:1], torch.log(torch.expm1(cumulative.diff().clamp_min(1e-3)))]))


class Grid(Head):
    def __init__(self, name, column, structure, representation, width, rank, device):
        rows, columns = structure["shape"]
        super().__init__([name], [column], rows * columns if representation == "flat" else rows + columns, width, rank)
        self.name, self.mode, self.shape = name, representation, structure["shape"]
        self.register_buffer("cells", torch.tensor(structure["values"], device=device), persistent=False)

    def nodes(self, logits, temperature=1.):
        logits = logits.float() / temperature
        if self.mode == "flat":
            return logits.softmax(1)
        rows = self.shape[0]
        return (logits[:, :rows].softmax(1)[:, :, None] * logits[:, rows:].softmax(1)[:, None, :]).flatten(1)

    def terms(self, logits, batch, rows, temperature):
        cell = self.cells[batch.labels[rows, self.columns[0]].nan_to_num(0).long()]
        return -self.nodes(logits, temperature).clamp_min(TINY).log().gather(1, cell[:, None]).squeeze(1)

    def initialize(self, counts):
        rows, columns = self.shape
        with torch.no_grad():
            if self.mode == "flat":
                self.output.offset().copy_(prior(counts).log())
            else:
                grid = prior(counts).view(rows, columns)
                self.output.offset().copy_(torch.cat([grid.sum(1).log(), grid.sum(0).log()]))


class Joint(Head):
    def __init__(self, names, columns, width, rank, device):
        super().__init__(names, columns, 1 << len(names), width, rank)
        self.register_buffer("bits", ((torch.arange(self.size, device=device)[:, None] >> torch.arange(len(names), device=device)) & 1).float(), persistent=False)

    def terms(self, logits, batch, rows, temperature):
        stated = batch.labels[rows][:, self.column_index]
        consistent = ((self.bits[None] == stated[:, None, :]) | ~torch.isfinite(stated)[:, None, :]).all(2)
        return -torch.where(consistent, (logits / temperature).log_softmax(1), -torch.inf).logsumexp(1)

    def marginals(self, logits, temperature=1.):
        ones = (logits.float() / temperature).softmax(1) @ self.bits
        return [torch.stack([1 - ones[:, axis], ones[:, axis]], 1) for axis in range(len(self.targets))]


class Number(Head):
    def __init__(self, name, column, spec, representation, width, rank, device):
        self.mode = representation
        self.center, self.scale, self.low, self.high = spec["center"], spec["scale"], math.floor(spec["low"]), math.ceil(spec["high"])
        super().__init__([name], [column], {"point": 1, "laplace": 2, "quantile": len(QUANTILES), "bins": self.high - self.low + 1}[self.mode], width, rank)
        self.name = name
        self.register_buffer("levels", torch.tensor(QUANTILES, device=device), persistent=False)

    def quantiles(self, logits):
        half = len(QUANTILES) // 2
        steps = F.softplus(logits)
        middle = logits[:, half:half + 1]
        upper = middle + F.pad(steps[:, half + 1:], (1, 0)).cumsum(1)
        lower = middle - F.pad(steps[:, :half].flip(1), (1, 0)).cumsum(1)
        return torch.cat([lower[:, 1:].flip(1), upper], 1)

    def terms(self, logits, batch, rows, temperature):
        value = batch.labels[rows, self.columns[0]].nan_to_num(self.center)
        normal = (value - self.center) / self.scale
        if self.mode == "point":
            return (normal - logits[:, 0]).abs()
        if self.mode == "laplace":
            width = F.softplus(logits[:, 1]) + 1e-3
            return (normal - logits[:, 0]).abs() / width + width.log()
        if self.mode == "quantile":
            gap = normal[:, None] - self.quantiles(logits)
            return torch.maximum(self.levels * gap, (self.levels - 1) * gap).mean(1)
        index = (value - self.low).round().long().clamp(0, self.size - 1)
        return -(logits / temperature).log_softmax(1).gather(1, index[:, None]).squeeze(1)

    def initialize(self, counts):
        if self.mode == "bins":
            with torch.no_grad():
                self.output.offset().copy_(prior(counts).log())
