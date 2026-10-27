from collections import defaultdict

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from database import timed


class DemographicModel(nn.Module):
    @timed
    def __init__(self, compiled, config):
        super().__init__()
        self.compiled = compiled
        self.config = config
        width = config["width"]
        self.projection = nn.Sequential(nn.Linear(512, width), nn.GELU(), nn.LayerNorm(width), nn.Dropout(config["dropout"]))
        self.heads = nn.ModuleList(nn.Linear(width, len(head["catalog"])) for head in compiled["heads"])
        self.numeric = nn.ModuleList(nn.Linear(width, 3 * config["mixtures"]) for _ in compiled["numbers"])
        with torch.no_grad():
            for layer, head in zip(self.heads, compiled["heads"]):
                nn.init.normal_(layer.weight, std=.005)
                layer.bias.copy_(torch.tensor(np.log(head["prior"]), dtype=torch.float32))
            for layer in self.numeric:
                layer.weight.zero_()
                layer.bias.zero_()
                layer.bias[config["mixtures"]:2 * config["mixtures"]] = torch.linspace(-.75, .75, config["mixtures"])
        for index, head in enumerate(compiled["heads"]):
            coordinates = torch.as_tensor(head["matrix"])
            matrix = torch.sparse_coo_tensor(coordinates, torch.ones(coordinates.shape[1]), (head["query_count"], len(head["catalog"]))).coalesce()
            self.register_buffer(f"events_{index}", matrix, persistent=False)

    def distribution(self, vectors, number):
        weights, locations, scales = self.numeric[number](vectors).chunk(3, dim=-1)
        return weights.log_softmax(-1), locations, F.softplus(scales) + .025


def interval_mass(weights, locations, scales, low, high):
    finite_a, finite_b = torch.isfinite(low[:, None]), torch.isfinite(high[:, None])
    a = (torch.where(finite_a, low[:, None], 0.) - locations) / scales
    b = (torch.where(finite_b, high[:, None], 0.) - locations) / scales
    difference = (a - b).clamp(max=-torch.finfo(a.dtype).tiny)
    middle = F.logsigmoid(b) + F.logsigmoid(-a) + torch.log(-torch.expm1(difference))
    mass = torch.where(~finite_a, F.logsigmoid(b), torch.where(~finite_b, F.logsigmoid(-a), middle))
    mass = torch.where(~finite_a & ~finite_b, 0., mass)
    return torch.logsumexp(weights + mass, dim=-1)


def objective(model, vectors, indices):
    category, numeric = defaultdict(list), defaultdict(list)
    unknown = []
    atom_branch, branch_group, group_target, attributes = [], [], [], []
    for local, index in enumerate(indices):
        for target in model.compiled["users"][index]:
            target_id = len(attributes)
            attributes.append(target["attribute"])
            for group in target["groups"]:
                group_id = len(group_target)
                group_target.append(target_id)
                for branch in group:
                    branch_id = len(branch_group)
                    branch_group.append(group_id)
                    for atom in branch:
                        atom_id = len(atom_branch)
                        atom_branch.append(branch_id)
                        if atom["kind"] == "node":
                            query = model.compiled["queries"][atom["query"]]
                            category[query["head"]].append((atom_id, local, query["local"], atom["negative"]))
                        elif atom["kind"] == "numeric":
                            numeric[atom["number"]].append((atom_id, local, atom["bounds"]))
                        else:
                            unknown.append(atom_id)
    device = vectors.device
    losses = torch.zeros(len(atom_branch), device=device)
    if unknown:
        losses[torch.tensor(unknown, device=device)] = -np.log(1e-12)
    for head, requests in category.items():
        values = np.asarray(requests, dtype=np.int64)
        users, inverse = np.unique(values[:, 1], return_inverse=True)
        probabilities = model.heads[head](vectors[torch.as_tensor(users, device=device)]).softmax(-1)
        events = torch.sparse.mm(getattr(model, f"events_{head}"), probabilities.T).T
        mass = events[torch.as_tensor(inverse, device=device), torch.as_tensor(values[:, 2], device=device)]
        mass = torch.where(torch.as_tensor(values[:, 3], device=device).bool(), 1 - mass, mass)
        losses[torch.as_tensor(values[:, 0], device=device)] = -mass.clamp(min=1e-12, max=1).log()
    for index, requests in numeric.items():
        number = model.compiled["numbers"][index]
        rows, limits, owners = [], [], []
        for request_index, (_, local, bounds) in enumerate(requests):
            for low, high in bounds:
                rows.append(local)
                limits.append(((low - number["center"]) / number["scale"], (high - number["center"]) / number["scale"]))
                owners.append(request_index)
        params = model.distribution(vectors[torch.tensor(rows, device=device)], index)
        limits = torch.tensor(limits, dtype=torch.float64, device=device)
        log_mass = interval_mass(*params, limits[:, 0], limits[:, 1])
        groups = torch.tensor(owners, device=device)
        maxima = torch.full((len(requests),), -torch.inf, device=device, dtype=log_mass.dtype).scatter_reduce(0, groups, log_mass, reduce="amax", include_self=True)
        sums = torch.zeros_like(maxima).scatter_add(0, groups, (log_mass - maxima[groups]).exp())
        nll = -(maxima + sums.clamp_min(1e-30).log()).clamp(max=0)
        losses[torch.tensor([request[0] for request in requests], device=device)] = nll.float()
    atom_branch = torch.tensor(atom_branch, device=device)
    branch_group = torch.tensor(branch_group, device=device)
    group_target = torch.tensor(group_target, device=device)
    branch_loss = torch.zeros(len(branch_group), device=device).scatter_add(0, atom_branch, losses)
    branch_loss /= torch.bincount(atom_branch, minlength=len(branch_group)).clamp_min(1)
    group_loss = torch.full((len(group_target),), torch.inf, device=device).scatter_reduce(0, branch_group, branch_loss, reduce="amin", include_self=True)
    target_loss = torch.zeros(len(attributes), device=device).scatter_add(0, group_target, group_loss)
    target_loss /= torch.bincount(group_target, minlength=len(attributes)).clamp_min(1)
    return target_loss, torch.tensor(attributes, device=device)
