import json
import time

import optuna
import torch

from pipeline.lock import Hold

from . import LOG, timed
from .config import GPU_MEMORY, MIN_IMPROVEMENT, SEARCH_PATIENCE, SEARCH_SPACE, SEARCH_STARTUP, SEED
from .evaluate import objective
from .model import choices_for
from .train import assess, built, fit, load_data, train

PREFIX = "choice_"


def suggested(trial, options):
    numbers = {name: trial.suggest_int(name, low, high, log=log) if isinstance(low, int) else trial.suggest_float(name, low, high, log=log) for name, (low, high, log) in SEARCH_SPACE.items()}
    return numbers, {key: trial.suggest_categorical(PREFIX + key, found) for key, found in options.items() if len(found) > 1}


def stale(study):
    best, count, complete = -float("inf"), 0, 0
    for trial in study.trials:
        done = trial.state == optuna.trial.TrialState.COMPLETE
        if complete >= SEARCH_STARTUP:
            count = 0 if done and trial.value - best >= MIN_IMPROVEMENT else count + 1
        if done:
            best, complete = max(best, trial.value), complete + 1
    return count


def separated(params):
    return {key: value for key, value in params.items() if not key.startswith(PREFIX)}, {key[len(PREFIX):]: value for key, value in params.items() if key.startswith(PREFIX)}


@timed
def search(directory, stem, base, chosen):
    stem.parent.mkdir(parents=True, exist_ok=True)
    with Hold(f"search {stem.name}"):
        torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
        manifest, specs, structures, splits, stats = load_data(directory)
        options = choices_for(structures)
        study = optuna.create_study(study_name=stem.name, storage=f"sqlite:///{stem.with_suffix('.db').as_posix()}", load_if_exists=True, direction="maximize")
        for interrupted in study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.RUNNING,)):
            study.tell(interrupted.number, state=optuna.trial.TrialState.FAIL)
            LOG.warning("search %s trial=%d was interrupted and is marked failed", stem.name, interrupted.number)
        study.sampler = optuna.samplers.TPESampler(n_startup_trials=SEARCH_STARTUP, multivariate=True, seed=SEED + len(study.trials))
        if not study.trials:
            study.enqueue_trial({name: base[name] for name in SEARCH_SPACE} | {PREFIX + key: chosen.get(key, found[0]) for key, found in options.items() if len(found) > 1})
        started = time.perf_counter()

        @timed
        def evaluate(trial):
            numbers, picked = suggested(trial, options)
            parameters = base | numbers
            model = built(manifest, specs, structures, picked, parameters, stats[1], splits["train"])
            try:
                score, history = fit(model, splits, parameters)
                _, _, reports = assess(model, splits, stats)
            finally:
                del model
                torch.cuda.empty_cache()
            trial.set_user_attr("epochs", len(history))
            trial.set_user_attr("skills", {name: round(fields["skill"], 4) for name, fields in reports["validation"].items()})
            return objective(reports["validation"])

        def report(study, trial):
            LOG.info("search %s trial=%d state=%s objective=%s best=%.5f stale=%d seconds=%.0f elapsed=%.0f parameters=%s", stem.name, trial.number, trial.state.name, trial.value,
                     study.best_value, stale(study), trial.duration.total_seconds(), time.perf_counter() - started, json.dumps(trial.params))
            if stale(study) >= SEARCH_PATIENCE:
                study.stop()

        if stale(study) < SEARCH_PATIENCE:
            study.optimize(evaluate, callbacks=[report], catch=(FloatingPointError, torch.OutOfMemoryError))
        splits = None
        torch.cuda.empty_cache()
        numbers, picked = separated(study.best_params)
        best = base | numbers
        LOG.info("search %s trials=%d best=%.5f trial=%d parameters=%s choices=%s", stem.name, len(study.trials), study.best_value, study.best_trial.number, json.dumps(best), json.dumps(picked))
        return train(directory, stem.with_suffix(".pt"), best, picked) | {"trials": len(study.trials), "best_trial": study.best_trial.number, "baseline": study.trials[0].value}
