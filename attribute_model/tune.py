import json
import random
import time

import torch

from . import LOG, timed, write_json
from .config import GPU_MEMORY, PARAMETERS, SEED, TUNE_SPACE, TUNE_TRIALS, validate
from .model import AttributeModel
from .train import DEVICE, architecture, finish, fit, load_data


@timed
def tune(targets, directory, account, output):
    targets = validate(targets)
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    account.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    manifest, specs, data = load_data(directory, targets)
    trials = [PARAMETERS] + [{**PARAMETERS, **{key: rng.choice(values) for key, values in TUNE_SPACE.items()}} for _ in range(TUNE_TRIALS - 1)]
    started, history, leader = time.perf_counter(), [], None
    for number, parameters in enumerate(trials):
        tick = time.perf_counter()
        torch.manual_seed(SEED)
        model = AttributeModel(targets, specs, **architecture(parameters, manifest)).to(DEVICE)
        score, curve = fit(model, specs, data, parameters)
        history.append({"trial": number, "score": score, "parameters": parameters, "curve": curve, "seconds": time.perf_counter() - tick})
        LOG.info("tune trial=%d score=%.5f seconds=%.1f elapsed=%.0f parameters=%s", number, score, history[-1]["seconds"], time.perf_counter() - started, json.dumps(parameters))
        write_json(account, history)
        if leader is None or score < leader[0]:
            leader = (score, parameters, curve, {name: value.cpu() for name, value in model.state_dict().items()})
        del model
        torch.cuda.empty_cache()
    score, parameters, curve, state = leader
    LOG.info("tune best score=%.5f parameters=%s", score, json.dumps(parameters))
    model = AttributeModel(targets, specs, **architecture(parameters, manifest))
    model.load_state_dict(state)
    return finish(model.to(DEVICE), manifest, specs, data, parameters, score, curve, output)
