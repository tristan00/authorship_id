import json
import random
import time

import torch

from . import LOG, timed, write_json
from .config import GPU_MEMORY, PARAMETERS, SEED, TUNE_ROUNDS, TUNE_SPACE, TUNE_TRIALS
from .model import AttributeModel
from .train import DEVICE, fit


def architecture(parameters, manifest):
    return {**{key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}, "features": manifest["features"]}


def attempt(targets, manifest, specs, data, parameters, epochs):
    torch.manual_seed(SEED)
    model = AttributeModel(targets, specs, **architecture(parameters, manifest)).to(DEVICE)
    try:
        return fit(model, specs, data, {**parameters, "epochs": epochs})[0]
    finally:
        del model
        torch.cuda.empty_cache()


@timed
def tune(targets, load, directory, out):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    rng = random.Random(SEED)
    manifest, specs, data = load(directory, targets)
    trials = [PARAMETERS] + [{**PARAMETERS, **{key: rng.choice(values) for key, values in TUNE_SPACE.items()}} for _ in range(TUNE_TRIALS - 1)]
    started, history = time.perf_counter(), []
    for round_number, epochs in enumerate(TUNE_ROUNDS):
        scored = []
        for parameters in trials:
            tick = time.perf_counter()
            score = attempt(targets, manifest, specs, data, parameters, epochs)
            scored.append((score, parameters))
            history.append({"round": round_number, "epochs": epochs, "score": score, "parameters": parameters, "seconds": time.perf_counter() - tick})
            LOG.info("tune round=%d epochs=%d score=%.5f seconds=%.1f elapsed=%.0f parameters=%s", round_number, epochs, score, history[-1]["seconds"], time.perf_counter() - started, json.dumps(parameters))
            write_json(out, history)
        scored.sort(key=lambda item: item[0])
        trials = [parameters for _, parameters in scored[:max(1, len(scored) // 3)]]
    best = {**trials[0], "epochs": TUNE_ROUNDS[-1]}
    LOG.info("tune best score=%.5f parameters=%s", scored[0][0], json.dumps(best))
    return {"score": scored[0][0], "parameters": best}
