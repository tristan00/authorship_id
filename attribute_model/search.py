import json
import time

import optuna
import torch

from pipeline.lock import Hold

from . import LOG, timed
from .config import GPU_MEMORY, MIN_IMPROVEMENT, SEARCH_PATIENCE, SEARCH_SPACE, SEARCH_STARTUP, SEED
from .model import AttributeModel
from .train import DEVICE, architecture, fit, load_data, train


def suggested(trial):
    return {name: trial.suggest_int(name, low, high, log=log) if isinstance(low, int) else trial.suggest_float(name, low, high, log=log) for name, (low, high, log) in SEARCH_SPACE.items()}


def stale(study):
    best, count = float("inf"), 0
    for trial in study.trials:
        improved = trial.state == optuna.trial.TrialState.COMPLETE and best - trial.value >= MIN_IMPROVEMENT
        best = min(best, trial.value) if trial.state == optuna.trial.TrialState.COMPLETE else best
        if trial.number >= SEARCH_STARTUP:
            count = 0 if improved else count + 1
    return count


@timed
def search(directory, stem, base):
    stem.parent.mkdir(parents=True, exist_ok=True)
    with Hold(f"search {stem.name}"):
        torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
        manifest, specs, data = load_data(directory)
        study = optuna.create_study(study_name=stem.name, storage=f"sqlite:///{stem.with_suffix('.db').as_posix()}", load_if_exists=True)
        for interrupted in study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.RUNNING,)):
            study.tell(interrupted.number, state=optuna.trial.TrialState.FAIL)
            LOG.warning("search %s trial=%d was interrupted and is marked failed", stem.name, interrupted.number)
        study.sampler = optuna.samplers.TPESampler(n_startup_trials=SEARCH_STARTUP, multivariate=True, seed=SEED + len(study.trials))
        if not study.trials:
            study.enqueue_trial({name: base[name] for name in SEARCH_SPACE})
        started = time.perf_counter()

        @timed
        def objective(trial):
            parameters = base | suggested(trial)
            torch.manual_seed(SEED)
            model = AttributeModel(manifest["targets"], specs, **architecture(parameters, manifest)).to(DEVICE)
            try:
                score, history = fit(model, specs, data, parameters)
            finally:
                del model
                torch.cuda.empty_cache()
            trial.set_user_attr("epochs", len(history))
            return score

        def report(study, trial):
            LOG.info("search %s trial=%d state=%s score=%s best=%.5f stale=%d seconds=%.0f elapsed=%.0f parameters=%s", stem.name, trial.number, trial.state.name, trial.value,
                     study.best_value, stale(study), trial.duration.total_seconds(), time.perf_counter() - started, json.dumps(trial.params))
            if stale(study) >= SEARCH_PATIENCE:
                study.stop()

        if stale(study) < SEARCH_PATIENCE:
            study.optimize(objective, callbacks=[report], catch=(FloatingPointError,))
        data = None
        torch.cuda.empty_cache()
        best = base | study.best_params
        LOG.info("search %s trials=%d best=%.5f trial=%d parameters=%s", stem.name, len(study.trials), study.best_value, study.best_trial.number, json.dumps(best))
        return train(directory, stem.with_suffix(".pt"), best) | {"trials": len(study.trials), "best_trial": study.best_trial.number, "baseline": study.trials[0].value}
