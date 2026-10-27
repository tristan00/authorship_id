import hashlib
import logging
import random
import time

import numpy as np
import orjson
import torch

from database import timed

from .config import FOLDS, PARAMETERS

from .data import compile_targets, cover_validation, export, split_users, write_json
from .model import DemographicModel, objective

LOG = logging.getLogger(__name__)


def checkpoint_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@timed
def evaluate(model, embeddings, indices, prior=False):
    model.eval()
    sums = torch.zeros(len(model.compiled["fields"]), dtype=torch.float64, device="cuda")
    counts = torch.zeros_like(sums)
    with torch.inference_mode():
        for start in range(0, len(indices), model.config["batch"]):
            selected = indices[start:start + model.config["batch"]]
            vectors = torch.zeros((len(selected), model.config["width"]), device="cuda") if prior else model.projection(embeddings[torch.as_tensor(selected, device="cuda")])
            losses, attributes = objective(model, vectors, selected)
            sums.scatter_add_(0, attributes, losses.double())
            counts += torch.bincount(attributes, minlength=len(counts))
    return {field: {"n": int(n), "loss": float(total / n) if n else None} for field, total, n in zip(model.compiled["fields"], sums.cpu().tolist(), counts.cpu().tolist(), strict=True)}


@timed
def train(root):
    torch.set_num_threads(8)
    torch.set_float32_matmul_precision("high")
    manifest = orjson.loads((root / "manifest.json").read_bytes()) if (root / "manifest.json").exists() else export(root)
    if manifest["folds"] != FOLDS or manifest["parameters"] != PARAMETERS:
        raise ValueError("Existing run settings differ; choose a new output directory")
    authors = orjson.loads((root / "authors.json").read_bytes())
    folds = np.load(root / "folds.npy")
    embeddings = torch.from_numpy(np.load(root / "embeddings.npy")).cuda()
    if len(authors) != len(folds) or len(authors) != len(embeddings):
        raise ValueError("Dataset rows do not align")
    for fold in range(FOLDS):
        destination = root / f"fold_{fold}"
        if (destination / "complete.json").exists():
            LOG.info("fold already trained fold=%s", fold + 1)
            continue
        started = time.perf_counter()
        destination.mkdir(exist_ok=True)
        splits = cover_validation(root, authors, split_users(authors, folds, fold))
        compiled = compile_targets(root, authors, splits)
        labeled = np.array([bool(targets) for targets in compiled["users"]])
        training = np.flatnonzero((splits == 0) & labeled)
        validation = np.flatnonzero((splits == 1) & labeled)
        held_out = np.flatnonzero(folds == fold)
        if not len(training) or not len(validation) or not len(held_out) or np.any(labeled[held_out]):
            raise ValueError("Invalid fold separation")
        config = PARAMETERS | {"seed": PARAMETERS["seed"] + fold}
        random.seed(config["seed"])
        np.random.seed(config["seed"])
        torch.manual_seed(config["seed"])
        model = DemographicModel(compiled, config).cuda()
        baseline = evaluate(model, embeddings, validation, prior=True)
        scored = [field for field, item in baseline.items() if item["n"]]
        LOG.info("fold=%s attributes without validation targets: %s", fold + 1, [field for field in baseline if field not in scored])
        optimizer = torch.optim.AdamW(model.parameters(), lr=config["lr"], weight_decay=config["weight_decay"])
        best, best_epoch, history = float("inf"), 0, []
        for epoch in range(1, config["epochs"] + 1):
            model.train()
            order = np.random.default_rng(config["seed"] + epoch).permutation(training)
            total, steps = 0., 0
            epoch_started = time.perf_counter()
            for start in range(0, len(order), config["batch"]):
                selected = order[start:start + config["batch"]]
                vectors = model.projection(embeddings[torch.as_tensor(selected, device="cuda")])
                losses, attributes = objective(model, vectors, selected)
                sums = torch.zeros(len(compiled["fields"]), device="cuda").scatter_add(0, attributes, losses)
                counts = torch.bincount(attributes, minlength=len(sums))
                loss = (sums[counts > 0] / counts[counts > 0]).mean()
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"Nonfinite loss in fold {fold + 1}, epoch {epoch}")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
                optimizer.step()
                total += float(loss.detach())
                steps += 1
                if steps % 100 == 0:
                    LOG.info("fold=%s epoch=%s step=%s/%s loss=%.5f seconds=%.1f", fold + 1, epoch, steps, (len(order) + config["batch"] - 1) // config["batch"], total / steps, time.perf_counter() - epoch_started)
            measured = evaluate(model, embeddings, validation)
            score = float(np.mean([measured[field]["loss"] / max(baseline[field]["loss"], .01) for field in scored]))
            history.append({"epoch": epoch, "training_loss": total / steps, "validation_score": score, "validation": measured, "seconds": time.perf_counter() - epoch_started})
            if score < best:
                best, best_epoch = score, epoch
                torch.save({"model": model.state_dict(), "config": config, "epoch": epoch, "excluded_fold": fold, "run_id": manifest["run_id"]}, destination / "model.pt")
            write_json(destination / "history.json", history)
            LOG.info("fold=%s epoch=%s validation=%.6f best_epoch=%s", fold + 1, epoch, score, best_epoch)
            if epoch - best_epoch >= config["patience"]:
                break
        torch.save({key: value for key, value in compiled.items() if key != "users"}, destination / "targets.pt")
        write_json(destination / "complete.json", {"excluded_fold": fold, "run_id": manifest["run_id"], "training_users": len(training), "validation_users": len(validation), "held_out_users": len(held_out), "training_indices_sha256": hashlib.sha256(training.tobytes()).hexdigest(), "validation_indices_sha256": hashlib.sha256(validation.tobytes()).hexdigest(), "held_out_indices_sha256": hashlib.sha256(held_out.tobytes()).hexdigest(), "checkpoint_sha256": checkpoint_hash(destination / "model.pt"), "selected_epoch": best_epoch, "score": best, "baseline": baseline, "seconds": time.perf_counter() - started})
        del model, optimizer, compiled
        torch.cuda.empty_cache()
