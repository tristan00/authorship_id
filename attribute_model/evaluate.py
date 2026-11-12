import math
from typing import NamedTuple

import torch
from torch.nn import functional as F

from . import LOG, timed
from .heads import Joint, Number, prior

DEVICE = "cuda"
CHUNK = 1 << 13
SAMPLE = 1 << 16
PIECE = 1 << 12
CUTOFFS = (.02, .05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .6, .7, .8, .9)
LEAVES = 4
BINS = 15
CURVE = 200
CLIMATE = 4096
INTERVAL = .8


def padded(indptr, values, rows, width, empty):
    start = indptr[rows]
    offsets = torch.arange(width, device=rows.device)
    stated = offsets < (indptr[rows + 1] - start)[:, None]
    return torch.where(stated, values[(start[:, None] + offsets).clamp(max=max(len(values) - 1, 0))], empty)


class Batch(NamedTuple):
    labels: torch.Tensor
    truth: dict
    raw: dict

    def to(self, device):
        return Batch(self.labels.to(device), {name: value.to(device) for name, value in self.truth.items()}, {name: value.to(device) for name, value in self.raw.items()})

    def take(self, rows, names):
        return Batch(self.labels[rows], {name: value[rows] for name, value in self.truth.items() if name in names}, {name: value[rows] for name, value in self.raw.items() if name in names})


class Split:
    def __init__(self, inputs, labels, truths, raw):
        self.inputs, self.labels, self.truths, self.raw = inputs, labels, truths, raw
        self.widths = {name: max(int(indptr.diff().max()), 1) for name, (indptr, _, _) in {**truths, **raw}.items()}

    def __len__(self):
        return len(self.labels)

    def batch(self, rows):
        pad = lambda found: {name: padded(indptr, values, rows, self.widths[name], empty) for name, (indptr, values, empty) in found.items()}
        return Batch(self.labels[rows], pad(self.truths), pad(self.raw))


def chunks(model, split, size=CHUNK):
    model.eval()
    for start in range(0, len(split), size):
        rows = torch.arange(start, min(start + size, len(split)), device=split.labels.device)
        batch = split.batch(rows).to(DEVICE)
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
            hidden = model(split.inputs[rows].to(DEVICE))
        yield hidden, batch


def owners(model):
    return {name: (key, head) for key, head in model.heads.items() for name in head.targets}


def sentinel(structure):
    kind = structure["kind"]
    return len(structure["nodes"]) if kind == "tree" else len(structure["names"]) if kind == "scale" else structure["shape"][0] * structure["shape"][1]


def scored(structure, name, column, batch):
    if structure["kind"] == "number":
        return torch.isfinite(batch.labels[:, column])
    return (batch.truth[name] != sentinel(structure)).any(1)


def golden(loss, low=-1.5, high=1.5, steps=24):
    ratio = (math.sqrt(5) - 1) / 2
    a, b = low, high
    c, d = b - ratio * (b - a), a + ratio * (b - a)
    fc, fd = loss(c), loss(d)
    for _ in range(steps):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - ratio * (b - a)
            fc = loss(c)
        else:
            a, c, fc = c, d, fd
            d = a + ratio * (b - a)
            fd = loss(d)
    return (a + b) / 2


@timed
def samples(model, split):
    kept = {key: ([], [], 0) for key in model.heads}
    for hidden, batch in chunks(model, split):
        for key, head in model.heads.items():
            hiddens, batches, count = kept[key]
            if count >= SAMPLE:
                continue
            present = head.present(batch).nonzero().squeeze(1)[:SAMPLE - count]
            if len(present):
                hiddens.append(hidden[present].cpu())
                batches.append(batch.take(present, head.targets))
                kept[key] = (hiddens, batches, count + len(present))
    return {key: (torch.cat(hiddens), Batch(torch.cat([part.labels for part in batches]), *({name: torch.cat([getattr(part, field)[name] for part in batches])
                                                                                               for name in getattr(batches[0], field)} for field in ("truth", "raw"))))
            for key, (hiddens, batches, _) in kept.items() if hiddens}


def number_spread(head, logits, value):
    normal = (value - head.center) / head.scale
    if head.mode == "point":
        return float((normal - logits[:, 0]).abs().mean())
    if head.mode == "laplace":
        return float(((normal - logits[:, 0]).abs() / (F.softplus(logits[:, 1]) + 1e-3)).mean())
    if head.mode == "quantile":
        grid = torch.logspace(math.log10(.5), math.log10(2), 15).tolist()
        return min(grid, key=lambda spread: float(number_scores(head, logits, value, {"spread": spread})[0].mean()))
    return 1.


@timed
def calibrate(model, split):
    fitted = {}
    with torch.inference_mode():
        for key, (hidden, batch) in samples(model, split).items():
            head = model.heads[key]
            pieces = [torch.arange(start, min(start + PIECE, len(hidden)), device=DEVICE) for start in range(0, len(hidden), PIECE)]

            def logits_of(rows):
                with torch.autocast(DEVICE, dtype=torch.bfloat16):
                    return head(hidden[rows.cpu()].to(DEVICE)).float()

            if isinstance(head, Number) and head.mode != "bins":
                fitted[key] = {"spread": number_spread(head, logits_of(torch.arange(len(hidden), device=DEVICE)), batch.labels[:, head.columns[0]])}
            else:
                loss = lambda log: sum(float(head.terms(logits_of(rows), batch, rows, math.exp(log)).sum()) for rows in pieces) / len(hidden)
                fitted[key] = {"temperature": math.exp(golden(loss))}
            if isinstance(head, Number):
                logits = logits_of(torch.arange(len(hidden), device=DEVICE))
                value = batch.labels[:, head.columns[0]].float()
                _, middle, low, high = number_scores(head, logits, value, fitted[key])
                ratio = torch.maximum((middle - value) / (middle - low).clamp_min(1e-3), (value - middle) / (high - middle).clamp_min(1e-3))
                fitted[key]["reach"] = float(ratio.quantile(INTERVAL))
            LOG.info("calibrated %s %s", key, fitted[key])
    return fitted


def node_probabilities(head, logits, fitted, target=None):
    temperature = fitted.get("temperature", 1.)
    if isinstance(head, Joint):
        return head.marginals(logits, temperature)[head.targets.index(target)]
    return head.nodes(logits, temperature)


class Space:
    def __init__(self, structure, information, device=DEVICE):
        from .structure import Graph
        self.graph = Graph(structure, device)
        size = self.graph.size
        self.size, self.device = size, device
        information = torch.as_tensor(information)
        self.information = torch.cat([information.float().clamp_min(1e-3).to(device), torch.zeros(2, device=device)])
        self.ancestors = torch.cat([self.graph.ancestors, torch.full((2, self.graph.ancestors.shape[1]), size, device=device)])
        self.depths = torch.cat([(self.graph.ancestors < size).sum(1), torch.zeros(2, dtype=torch.long, device=device)])
        children = [[] for _ in range(size + 1)]
        for parents in structure["groupings"].values():
            for child, parent in enumerate(parents):
                if parent >= 0:
                    children[parent].append(child)
        children[size] = self.graph.ancestors.new_tensor([node for node in range(size) if all(parents[node] < 0 for parents in structure["groupings"].values())]).tolist()
        width = max(len(found) for found in children)
        self.children = torch.tensor([sorted(set(found)) + [size + 1] * (width - len(set(found))) for found in children] + [[size + 1] * width], device=device)
        self.depth = int((self.graph.ancestors < size).sum(1).max())
        self.single = structure["single"]
        self.prior = (2 ** -information.float()).to(device)
        self.slots = self.ancestors.shape[1] * (1 if self.single else LEAVES)

    def ordered(self, leaves):
        nodes = self.ancestors[leaves]
        key = (torch.arange(leaves.shape[1], device=self.device)[None, :, None] * 64 + self.depths[nodes]).flatten(1)
        nodes = nodes.flatten(1)
        valid = nodes < self.size
        earlier = (nodes[:, :, None] == nodes[:, None, :]) & torch.ones(nodes.shape[1], nodes.shape[1], dtype=torch.bool, device=self.device).tril(-1)
        valid &= ~earlier.any(2)
        order = torch.where(valid, key, 1 << 30).argsort(dim=1, stable=True)[:, :self.slots]
        nodes = nodes.gather(1, order)
        return torch.where(valid.gather(1, order), nodes, -1)

    def decode(self, probability, cutoff):
        rows = len(probability)
        extended = torch.cat([probability, probability.new_ones((rows, 1)), probability.new_full((rows, 1), -1.)], 1)
        if self.single:
            current = torch.full((rows,), self.size, device=self.device)
            for step in range(self.depth + 1):
                candidates = self.children[current]
                scores = extended.gather(1, candidates)
                best, picked = scores.max(1)
                following = candidates.gather(1, picked[:, None]).squeeze(1)
                accept = (following <= self.size) & ((best >= cutoff) | (current == self.size))
                current = torch.where(accept, following, current)
            return current[:, None]
        reported = probability >= cutoff
        found = reported.nonzero()
        above = self.ancestors[found[:, 1]]
        proper = (above < self.size) & (above != found[:, 1:2])
        covered = torch.zeros_like(reported)
        covered[found[:, 0:1].expand_as(above)[proper], above[proper]] = True
        score = torch.where(reported & ~covered, probability, -1.)
        top, leaves = score.topk(min(LEAVES, self.size), 1)
        leaves = torch.where(top >= 0, leaves, self.size + 1)
        tops = self.children[self.size]
        tops = tops[tops <= self.size]
        likeliest = tops[probability[:, tops].argmax(1)]
        leaves[:, 0] = torch.where(top[:, 0] < 0, likeliest, leaves[:, 0])
        return leaves

    def credit(self, leaves, truth):
        sentinel = self.size + 1
        truth = torch.where(truth < self.size, truth, sentinel)
        ap, at = self.ancestors[leaves], self.ancestors[truth]
        p_valid, t_valid = leaves < self.size, truth < self.size
        p_in_t = (at[:, None, :, :] == leaves[:, :, None, None]).any(-1)
        t_in_p = (ap[:, :, None, :] == truth[:, None, :, None]).any(-1)
        shared = ((ap[:, :, None, :, None] == at[:, None, :, None, :]) & (ap[:, :, None, :, None] < self.size)).any(-1)
        common = (self.information[ap][:, :, None, :] * shared).amax(-1)
        icp, ict = self.information[leaves][:, :, None], self.information[truth][:, None, :]
        precision = torch.where(p_in_t | t_in_p, 1., common / icp)
        recall = torch.where(t_in_p, 1., torch.where(p_in_t, icp / ict, common / ict))
        pairs = p_valid[:, :, None] & t_valid[:, None, :]
        precision = torch.where(pairs, precision, -1.).amax(2)
        recall = torch.where(pairs, recall, -1.).amax(1)
        precision = torch.where(p_valid, precision, 0.).sum(1) / p_valid.sum(1).clamp_min(1)
        recall = torch.where(t_valid, recall, 0.).sum(1) / t_valid.sum(1).clamp_min(1)
        score = 2 * precision * recall / (precision + recall).clamp_min(1e-9)
        return score, precision, recall

    def reported(self, leaves, truth, probability):
        truth = torch.where(truth < self.size, truth, self.size + 1)
        nodes = self.ordered(leaves)
        valid = nodes >= 0
        nodes = torch.where(valid, nodes, self.size + 1)
        closure = self.ancestors[torch.where(truth < self.size, truth, self.size + 1)].flatten(1)
        correct = (nodes[:, :, None] == closure[:, None, :]).any(2)
        below = (self.ancestors[nodes][:, :, None, :] == truth[:, None, :, None]).any(3).any(2) & ~correct
        valid &= ~below
        chance = F.pad(probability, (0, 2)).gather(1, nodes)
        return chance[valid], correct[valid]


class Tally:
    def __init__(self):
        self.sums = {}

    def add(self, name, value):
        value = value.double().sum() if torch.is_tensor(value) else value
        self.sums[name] = self.sums.get(name, 0) + value

    def confidence(self, chance, correct):
        chance, correct = chance.float().clamp(0, 1), correct.float()
        bins = (chance * BINS).long().clamp(0, BINS - 1)
        self.add("items", len(chance))
        self.add("brier", (chance - correct) ** 2)
        for name, values in (("bin_count", torch.ones_like(chance)), ("bin_chance", chance), ("bin_correct", correct)):
            self.sums[name] = self.sums.get(name, torch.zeros(BINS, dtype=torch.float64, device=DEVICE)) + torch.bincount(bins, values.double(), minlength=BINS)
        curve = (chance * CURVE).long().clamp(0, CURVE - 1)
        for name, mask in (("positive", correct > 0), ("negative", correct == 0)):
            self.sums[name] = self.sums.get(name, torch.zeros(CURVE, dtype=torch.float64, device=DEVICE)) + torch.bincount(curve[mask], minlength=CURVE).double()

    def report(self):
        found = {name: (value.tolist() if torch.is_tensor(value) and value.dim() else float(value)) for name, value in self.sums.items()}
        result = {}
        if "items" in found and found["items"]:
            count = torch.tensor(found["bin_count"])
            result["calibration_error"] = float((torch.tensor(found["bin_chance"]) - torch.tensor(found["bin_correct"])).abs().sum() / count.sum())
            result["brier"] = found["brier"] / found["items"]
            positive, negative = torch.tensor(found["positive"]), torch.tensor(found["negative"])
            below = torch.cumsum(negative, 0) - negative
            pairs = positive.sum() * negative.sum()
            result["auroc"] = float(((positive * below).sum() + .5 * (positive * negative).sum()) / pairs) if pairs > 0 else None
            result["reported_items"] = int(found["items"])
        return result, found


def climate(spec, labels):
    observed = labels[torch.isfinite(labels)]
    picked = observed[torch.randperm(len(observed), generator=torch.Generator().manual_seed(0))[:CLIMATE]].to(DEVICE).float()
    return picked, float((picked[:, None] - picked[None, :]).abs().mean() / 2)


def number_scores(head, logits, value, fitted, climate_sample=None):
    value = value.float()
    spread = fitted.get("spread", 1.)
    if head.mode in ("point", "laplace"):
        middle = logits[:, 0] * head.scale + head.center
        width = (spread if head.mode == "point" else (F.softplus(logits[:, 1]) + 1e-3) * spread) * head.scale
        width = torch.as_tensor(width, device=logits.device).expand_as(middle)
        gap = (value - middle).abs() / width
        crps = width * (gap + torch.exp(-gap) - .75)
        reach = width * math.log(1 / (1 - INTERVAL))
        low, high = middle - reach, middle + reach
    elif head.mode == "quantile":
        quantiles = head.quantiles(logits) * head.scale + head.center
        half = quantiles.shape[1] // 2
        middle = quantiles[:, half]
        quantiles = middle[:, None] + (quantiles - middle[:, None]) * spread
        gap = value[:, None] - quantiles
        crps = 2 * torch.maximum(head.levels * gap, (head.levels - 1) * gap).mean(1)
        low, high = quantiles[:, 0], quantiles[:, -1]
    else:
        probability = (logits / fitted.get("temperature", 1.)).softmax(1)
        cumulative = probability.cumsum(1)
        years = torch.arange(head.low, head.high + 1, device=logits.device, dtype=torch.float32)
        crps = ((cumulative - (years[None, :] >= value[:, None]).float()) ** 2).sum(1)
        middle = years[(cumulative < .5).sum(1).clamp(max=len(years) - 1)]
        low = years[(cumulative < (1 - INTERVAL) / 2).sum(1).clamp(max=len(years) - 1)]
        high = years[(cumulative < (1 + INTERVAL) / 2).sum(1).clamp(max=len(years) - 1)]
    reach = fitted.get("reach", 1.)
    low, high = middle - (middle - low) * reach, middle + (high - middle) * reach
    result = [crps, middle, low, high]
    if climate_sample is not None:
        sample, half_mean = climate_sample
        result.append((sample[None, :] - value[:, None]).abs().mean(1) - half_mean)
    return result


def scale_choice(distribution):
    return (distribution.cumsum(1) < .5).sum(1).clamp(max=distribution.shape[1] - 1)


def grid_choice(probability, shape):
    rows, columns = shape
    grid = probability.view(-1, rows, columns)
    row, column = scale_choice(grid.sum(2)), scale_choice(grid.sum(1))
    return row * columns + column


def platt(chance, correct, steps=30):
    x = chance.double().clamp(1e-6, 1 - 1e-6).logit()
    y = correct.double()
    a, b = torch.ones((), dtype=torch.float64, device=x.device), torch.zeros((), dtype=torch.float64, device=x.device)
    for _ in range(steps):
        p = torch.sigmoid(a * x + b)
        weight = (p * (1 - p)).clamp_min(1e-9)
        gradient = torch.stack([((p - y) * x).sum(), (p - y).sum()])
        hessian = torch.stack([torch.stack([(weight * x * x).sum(), (weight * x).sum()]), torch.stack([(weight * x).sum(), weight.sum()])])
        a, b = torch.stack([a, b]) - torch.linalg.solve(hessian + 1e-6 * torch.eye(2, dtype=torch.float64, device=x.device), gradient)
    return [float(a), float(b)]


def calibrated(chance, fitted):
    a, b = fitted
    return torch.sigmoid(a * chance.float().clamp(1e-6, 1 - 1e-6).logit() + b)


def item_credit(kind, chosen, truth, structure):
    valid = truth < (len(structure["names"]) if kind == "scale" else structure["shape"][0] * structure["shape"][1])
    if kind == "scale":
        distance = (chosen[:, None] - truth).abs().float() / (len(structure["names"]) - 1)
    else:
        columns = structure["shape"][1]
        distance = ((chosen[:, None] // columns - truth // columns).abs() + (chosen[:, None] % columns - truth % columns).abs()).float() / (sum(structure["shape"]) - 2)
    return torch.where(valid, 1 - distance, -1.).amax(1), (valid & (chosen[:, None] == truth)).any(1)


class Evaluation:
    def __init__(self, model, information, counts, climates):
        self.model = model
        self.spaces = {name: Space(model.structures[name], information[name]) for name, structure in model.structures.items() if structure["kind"] == "tree"}
        self.priors = {name: prior(torch.as_tensor(counts[name], dtype=torch.float32)).to(DEVICE) for name, structure in model.structures.items() if structure["kind"] in ("scale", "grid")}
        self.climates = climates

    def items(self, split, fitted):
        found = owners(self.model)
        for hidden, batch in chunks(self.model, split):
            for column, (name, structure) in enumerate(self.model.structures.items()):
                key, head = found[name]
                rows = scored(structure, name, column, batch).nonzero().squeeze(1)
                if len(rows):
                    with torch.inference_mode(), torch.autocast(DEVICE, dtype=torch.bfloat16):
                        logits = head(hidden[rows]).float()
                    yield name, structure, head, logits, batch.take(rows, (name,)), fitted[key]

    @timed
    def cutoffs(self, split, fitted):
        sums = {name: torch.zeros((2, len(CUTOFFS)), dtype=torch.float64, device=DEVICE) for name in self.spaces}
        with torch.inference_mode():
            for name, structure, head, logits, batch, fit in self.items(split, fitted):
                if name not in self.spaces:
                    continue
                space, truth = self.spaces[name], batch.truth[name]
                probability = node_probabilities(head, logits, fit, name)
                constant = space.prior.expand(len(probability), -1)
                for slot, cutoff in enumerate(CUTOFFS):
                    sums[name][0, slot] += space.credit(space.decode(probability, cutoff), truth)[0].double().sum()
                    sums[name][1, slot] += space.credit(space.decode(constant, cutoff), truth)[0].double().sum()
        cutoffs = {name: {"cutoff": CUTOFFS[int(found[0].argmax())], "prior_cutoff": CUTOFFS[int(found[1].argmax())]} for name, found in sums.items()}
        items = {}
        with torch.inference_mode():
            for name, structure, head, logits, batch, fit in self.items(split, fitted):
                if structure["kind"] != "number":
                    chance, correct = self.decided(name, structure, head, logits, batch, fit, cutoffs)[-2:]
                    items.setdefault(name, []).append((chance, correct))
        for name, found in items.items():
            cutoffs.setdefault(name, {})["platt"] = platt(torch.cat([chance for chance, _ in found]), torch.cat([correct for _, correct in found]))
        return cutoffs

    def decided(self, name, structure, head, logits, batch, fit, cutoffs):
        truth, kind = batch.truth[name], structure["kind"]
        probability = node_probabilities(head, logits, fit, name)
        if kind == "tree":
            space = self.spaces[name]
            leaves = space.decode(probability, cutoffs[name]["cutoff"])
            return (space, probability, leaves, *space.reported(leaves, truth, probability))
        chosen = scale_choice(probability) if kind == "scale" else grid_choice(probability, structure["shape"])
        exact = (chosen[:, None] == truth).any(1)
        return probability, chosen, probability.gather(1, chosen[:, None]).squeeze(1), exact

    @timed
    def score(self, split, fitted, cutoffs):
        tallies = {name: Tally() for name in self.model.structures}
        with torch.inference_mode():
            for name, structure, head, logits, batch, fit in self.items(split, fitted):
                tally, kind = tallies[name], structure["kind"]
                tally.add("n", len(logits))
                if kind == "number":
                    value = batch.labels[:, head.columns[0]]
                    crps, middle, low, high, base = number_scores(head, logits, value, fit, self.climates[name])
                    tally.add("crps", crps)
                    tally.add("baseline_crps", base)
                    tally.add("mae", (middle - value).abs())
                    tally.add("covered", (value >= low) & (value <= high))
                    tally.add("width", high - low)
                    continue
                truth = batch.truth[name]
                if kind == "tree":
                    space, probability, leaves, chance, correct = self.decided(name, structure, head, logits, batch, fit, cutoffs)
                    score, precision, recall = space.credit(leaves, truth)
                    tally.add("credit", score)
                    tally.add("precision", precision)
                    tally.add("recall", recall)
                    tally.add("baseline", space.credit(space.decode(space.prior.expand(len(probability), -1), cutoffs[name]["prior_cutoff"]), truth)[0])
                    tally.add("bits_predicted", torch.where(leaves < space.size, space.information[leaves], 0.).sum(1) / (leaves < space.size).sum(1).clamp_min(1))
                    tally.add("bits_stated", torch.where(truth < space.size, space.information[truth.clamp(max=space.size + 1)], 0.).sum(1) / (truth < space.size).sum(1).clamp_min(1))
                    tally.confidence(calibrated(chance, cutoffs[name]["platt"]), correct)
                    continue
                distribution, chosen, chance, exact = self.decided(name, structure, head, logits, batch, fit, cutoffs)
                score, _ = item_credit(kind, chosen, truth, structure)
                constant = self.priors[name].expand(len(distribution), -1)
                base_choice = scale_choice(constant) if kind == "scale" else grid_choice(constant, structure["shape"])
                tally.add("credit", score)
                tally.add("accuracy", exact)
                tally.add("baseline", item_credit(kind, base_choice, truth, structure)[0])
                tally.confidence(calibrated(chance, cutoffs[name]["platt"]), exact)
        return {name: summarize(name, tally, self.model.structures[name]) for name, tally in tallies.items()}


def summarize(name, tally, structure):
    confidence, found = tally.report()
    n = max(found.get("n", 0), 1)
    if structure["kind"] == "number":
        crps, base = found["crps"] / n, found["baseline_crps"] / n
        return {"n": int(found["n"]), "crps": crps, "baseline_crps": base, "skill": 1 - crps / base, "mae": found["mae"] / n, "coverage": found["covered"] / n,
                "interval_width": found["width"] / n}
    credit, base = found["credit"] / n, found["baseline"] / n
    result = {"n": int(found["n"]), "credit": credit, "baseline_credit": base, "skill": (credit - base) / max(1 - base, 1e-9)}
    for key in ("precision", "recall", "bits_predicted", "bits_stated", "accuracy"):
        if key in found:
            result[key] = found[key] / n
    return result | confidence


def objective(report):
    return sum(fields["skill"] for fields in report.values()) / len(report)
