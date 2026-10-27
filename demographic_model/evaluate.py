import hashlib
import logging
from collections import defaultdict
from functools import lru_cache

import numpy as np
import orjson
import torch
from scipy.special import expit

from database import timed

from claim_extraction.config import NUMERIC

from .config import COMPLETE_HEADS, FOLDS, PARAMETERS
from .data import compile_targets, split_users, write_json
from .model import DemographicModel
from .store import initialize, load_fold, publish
from .train import checkpoint_hash, evaluate

LOG = logging.getLogger(__name__)


def numeric_summaries(weights, locations, scales, attribute):
    low = np.repeat((locations - 30 * scales).min(1)[:, None], 3, axis=1)
    high = np.repeat((locations + 30 * scales).max(1)[:, None], 3, axis=1)
    quantiles = np.array([.1, .5, .9])
    for _ in range(64):
        middle = (low + high) / 2
        mass = (weights[:, None, :] * expit((middle[:, :, None] - locations[:, None, :]) / scales[:, None, :])).sum(2)
        low = np.where(mass < quantiles, middle, low)
        high = np.where(mass < quantiles, high, middle)
    lower, upper = NUMERIC[attribute]
    values = lower + (upper - lower) * expit((low + high) / 2)
    if not np.isfinite(values).all():
        raise FloatingPointError("Numeric prediction is not finite")
    return [{"lower": float(low), "median": float(median), "upper": float(high), "interval_mass": .8} for low, median, high in values]


@timed
def hierarchies(root, heads):
    children, parents = defaultdict(set), defaultdict(set)
    for parent, child in orjson.loads((root / "taxonomy.json").read_bytes())["edges"]:
        children[parent].add(child)
        parents[child].add(parent)

    @lru_cache(None)
    def subtree(node):
        return frozenset({node}.union(*(subtree(child) for child in children[node])))

    @lru_cache(None)
    def depth(node):
        return 1 + max((depth(parent) for parent in parents[node]), default=-1)

    result = []
    for head in heads:
        positions = {node: index for index, node in enumerate(head["catalog"])}
        pairs = [(positions[node], positions[member]) for node in head["catalog"] for member in subtree(node) if member in positions]
        ancestors = defaultdict(set)
        for ancestor, member in pairs:
            if ancestor != member:
                ancestors[member].add(ancestor)
        matrix = torch.sparse_coo_tensor(torch.tensor(pairs).T, torch.ones(len(pairs)), (len(positions), len(positions))).coalesce().cuda()
        depths = torch.tensor([depth(node) for node in head["catalog"]], dtype=torch.float32, device="cuda")
        typical = torch.sparse.mm(matrix, torch.tensor(head["prior"], dtype=torch.float32, device="cuda")[:, None]).squeeze(1).cpu()
        result.append((matrix, depths, ancestors, typical))
    return result


@timed
def predictions(model, embeddings, indices, authors, fold, structures):
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(indices), 64):
            selected = indices[start:start + 64]
            vectors = model.projection(embeddings[torch.as_tensor(selected, device="cuda")])
            records = [{field: {"facets": [], "numeric": []} for field in model.compiled["fields"]} for _ in selected]
            for index, head in enumerate(model.compiled["heads"]):
                matrix, depths, ancestors, typical = structures[index]
                exact = model.heads[index](vectors).softmax(-1)
                mass = torch.sparse.mm(matrix, exact.T).T
                specific_scores, specific_nodes = (scores.cpu().tolist() for scores in exact[:, :-1].max(1))
                confident = mass >= .5
                headline = torch.where(confident.any(1), torch.where(confident, depths * 2 + mass, -torch.inf).argmax(1), mass.argmax(1)).cpu().tolist()
                complete = mass.shape[1] <= COMPLETE_HEADS
                scores, nodes = mass.topk(mass.shape[1] if complete else min(16, mass.shape[1]), dim=-1)
                mass, scores, nodes = mass.cpu(), scores.cpu().tolist(), nodes.cpu().tolist()
                for row, (best, row_scores, row_nodes, specific_node, specific_score) in enumerate(zip(headline, scores, nodes, specific_nodes, specific_scores, strict=True)):
                    others = [(node, score) for score, node in zip(row_scores, row_nodes, strict=True) if node != best and (complete or node not in ancestors[best])]
                    chosen = [(best, float(mass[row, best]))] + (others if complete else others[:4])
                    candidates = [{"node": head["catalog"][node], "label": head["labels"][node], "kind": head["kinds"][node], "probability": score, "typical": float(typical[node])} for node, score in chosen]
                    specific = {"node": head["catalog"][specific_node], "label": head["labels"][specific_node], "kind": head["kinds"][specific_node], "probability": specific_score}
                    records[row][head["attribute"]]["facets"].append({"facet": head["facet"], "candidates": candidates, "specific": specific})
            for index, number in enumerate(model.compiled["numbers"]):
                if not number["train"]:
                    continue
                weights, locations, scales = model.distribution(vectors, index)
                weights = weights.exp().cpu().numpy()
                weights /= weights.sum(1, keepdims=True)
                locations = locations.cpu().numpy() * number["scale"] + number["center"]
                scales = scales.cpu().numpy() * number["scale"]
                summaries = numeric_summaries(weights, locations, scales, number["key"][0])
                for row, summary in enumerate(summaries):
                    records[row][number["key"][0]]["numeric"].append({"context": number["key"][1:], "summary": summary, "training_targets": number["train"]})
            for user, record in zip(selected, records, strict=True):
                yield authors[user], record
            if start % 4096 == 0:
                LOG.info("write predictions fold=%s users=%s/%s", fold + 1, min(start + 64, len(indices)), len(indices))


@timed
def test(root):
    torch.set_num_threads(8)
    torch.set_float32_matmul_precision("high")
    manifest = orjson.loads((root / "manifest.json").read_bytes())
    if manifest["folds"] != FOLDS or manifest["parameters"] != PARAMETERS:
        raise ValueError("The trained run has different settings")
    training = [orjson.loads((root / f"fold_{fold}" / "complete.json").read_bytes()) for fold in range(FOLDS)]
    authors = orjson.loads((root / "authors.json").read_bytes())
    folds = np.load(root / "folds.npy")
    embeddings = torch.from_numpy(np.load(root / "embeddings.npy")).cuda()
    initialize(manifest, authors, folds)
    totals = {field: {"n": 0, "loss_sum": 0., "prior_loss_sum": 0.} for field in manifest["fields"]}
    for fold, summary in enumerate(training):
        directory = root / f"fold_{fold}"
        digest = checkpoint_hash(directory / "model.pt")
        held_out = np.flatnonzero(folds == fold)
        if digest != summary["checkpoint_sha256"] or summary["excluded_fold"] != fold or summary["run_id"] != manifest["run_id"] or summary["held_out_indices_sha256"] != hashlib.sha256(held_out.tobytes()).hexdigest():
            raise ValueError("Checkpoint or excluded-user assignment changed")
        reference = torch.load(directory / "targets.pt", map_location="cpu", weights_only=False)
        splits = split_users(authors, folds, fold)
        compiled = compile_targets(root, authors, splits, reference)
        labeled = np.array([bool(targets) for targets in compiled["users"]])
        if np.any(labeled[folds != fold]):
            raise ValueError("Evaluation includes users outside the held-out fold")
        selected = np.flatnonzero(labeled)
        checkpoint = torch.load(directory / "model.pt", map_location="cpu", weights_only=True)
        if checkpoint["excluded_fold"] != fold or checkpoint["run_id"] != manifest["run_id"]:
            raise ValueError("Checkpoint belongs to a different fold or run")
        model = DemographicModel(compiled, checkpoint["config"]).cuda()
        baseline = evaluate(model, embeddings, selected, prior=True)
        model.load_state_dict(checkpoint["model"])
        measured = evaluate(model, embeddings, selected)
        report = {"fold": fold, "users": len(held_out), "labeled_users": len(selected), "attributes": {}}
        for field, values in measured.items():
            if values["n"] != baseline[field]["n"]:
                raise ValueError("Model and baseline evaluated different targets")
            report["attributes"][field] = values | {"prior_loss": baseline[field]["loss"]}
            if values["n"]:
                totals[field]["n"] += values["n"]
                totals[field]["loss_sum"] += values["n"] * values["loss"]
                totals[field]["prior_loss_sum"] += values["n"] * baseline[field]["loss"]
        write_json(directory / "evaluation.json", report)
        load_fold(manifest, fold, digest, summary, report, predictions(model, embeddings, held_out, authors, fold, hierarchies(root, compiled["heads"])))
        del model, compiled, checkpoint, reference
        torch.cuda.empty_cache()
    attributes = {}
    for field, values in totals.items():
        if values["n"] != manifest["target_counts"][field]:
            raise ValueError(f"Out-of-fold evaluation did not cover every target for {field}")
        if not values["n"]:
            continue
        loss = values["loss_sum"] / values["n"]
        prior = values["prior_loss_sum"] / values["n"]
        attributes[field] = {"n": values["n"], "loss": loss, "prior_loss": prior, "loss_reduction": 1 - loss / max(prior, .01)}
    write_json(root / "evaluation.json", {"run_id": manifest["run_id"], "users": len(authors), "folds": FOLDS, "attributes": attributes, "macro_loss_reduction": float(np.mean([value["loss_reduction"] for value in attributes.values()]))})
    publish(manifest)
    LOG.info("published out-of-fold predictions users=%s folds=%s attributes=%s", len(authors), FOLDS, len(attributes))
