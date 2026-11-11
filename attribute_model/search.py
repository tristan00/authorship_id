import json
import math
import time

import optuna
import torch
from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.transforms import Standardize
from botorch.optim import optimize_acqf
from ConfigSpace import Configuration, ConfigurationSpace, Float, Integer
from gpytorch.mlls import ExactMarginalLogLikelihood
from smac import HyperparameterOptimizationFacade, Scenario
from smac.runhistory.dataclasses import TrialInfo, TrialValue
from smac.runhistory.encoder import RunHistoryLogScaledEncoder
from smac.runhistory.enumerations import StatusType

from pipeline.lock import Hold

from . import LOG, timed, write_json
from .config import GPU_MEMORY, MIN_IMPROVEMENT, SEARCH_PATIENCE, SEARCH_PHASES, SEARCH_SPACE, SEED
from .model import AttributeModel
from .train import DEVICE, architecture, fit, load_data, train

DISTRIBUTIONS = {name: optuna.distributions.IntDistribution(low, high, log=log) if isinstance(low, int) else optuna.distributions.FloatDistribution(low, high, log=log)
                 for name, (low, high, log) in SEARCH_SPACE.items()}


def typed(values):
    return {name: int(round(float(values[name]))) if isinstance(low, int) else float(values[name]) for name, (low, high, log) in SEARCH_SPACE.items()}


def unit(values):
    return [(math.log(values[name] / low) / math.log(high / low)) if log else (values[name] - low) / (high - low) for name, (low, high, log) in SEARCH_SPACE.items()]


def decoded(point):
    return typed({name: low * (high / low) ** x if log else low + x * (high - low) for x, (name, (low, high, log)) in zip(point, SEARCH_SPACE.items())})


def stale(history, phase):
    best, count = math.inf, 0
    for entry in history:
        improved = entry["score"] is not None and best - entry["score"] >= MIN_IMPROVEMENT
        best = best if entry["score"] is None else min(best, entry["score"])
        if entry["phase"] == phase:
            count = 0 if improved else count + 1
    return count


def finished(history):
    return [entry for entry in history if entry["score"] is not None]


@timed
def tpe(history, evaluate):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=SEED + len(history), multivariate=True))
    for entry in history:
        study.add_trial(optuna.trial.create_trial(params=typed(entry["parameters"]), distributions=DISTRIBUTIONS, value=entry["score"],
                                                  state=optuna.trial.TrialState.FAIL if entry["score"] is None else optuna.trial.TrialState.COMPLETE))
    while stale(history, "tpe") < SEARCH_PATIENCE:
        trial = study.ask(DISTRIBUTIONS)
        score = evaluate("tpe", trial.params)
        study.tell(trial, score, state=optuna.trial.TrialState.FAIL if score is None else optuna.trial.TrialState.COMPLETE)


def unused(config, seed=0):
    raise RuntimeError("SMAC runs through ask and tell")


@timed
def smac(history, evaluate, directory):
    space = ConfigurationSpace(seed=SEED)
    space.add([Integer(name, (low, high), log=log) if isinstance(low, int) else Float(name, (low, high), log=log) for name, (low, high, log) in SEARCH_SPACE.items()])
    scenario = Scenario(space, deterministic=True, n_trials=1 << 30, seed=SEED + len(history), output_directory=directory)
    optimizer = HyperparameterOptimizationFacade(scenario, unused, initial_design=HyperparameterOptimizationFacade.get_initial_design(scenario, n_configs=0),
                                                 runhistory_encoder=RunHistoryLogScaledEncoder(scenario, considered_states=[StatusType.SUCCESS]), overwrite=True, logging_level=40)
    for entry in history:
        optimizer.tell(TrialInfo(Configuration(space, values=typed(entry["parameters"])), seed=0), outcome(entry["score"]))
    while stale(history, "smac") < SEARCH_PATIENCE:
        info = optimizer.ask()
        optimizer.tell(info, outcome(evaluate("smac", dict(info.config))))


def outcome(score):
    return TrialValue(cost=math.inf, status=StatusType.CRASHED) if score is None else TrialValue(cost=score)


@timed
def proposal(history):
    inputs = torch.tensor([unit(typed(entry["parameters"])) for entry in finished(history)], dtype=torch.double)
    scores = -torch.tensor([[entry["score"]] for entry in finished(history)], dtype=torch.double)
    model = SingleTaskGP(inputs, scores, outcome_transform=Standardize(m=1))
    fit_gpytorch_mll(ExactMarginalLogLikelihood(model.likelihood, model))
    bounds = torch.stack([torch.zeros(len(SEARCH_SPACE)), torch.ones(len(SEARCH_SPACE))]).double()
    candidate, _ = optimize_acqf(qLogNoisyExpectedImprovement(model, inputs), bounds=bounds, q=1, num_restarts=8, raw_samples=512)
    return decoded(candidate[0].tolist())


@timed
def botorch(history, evaluate):
    while stale(history, "botorch") < SEARCH_PATIENCE:
        evaluate("botorch", proposal(history))


@timed
def candidate(manifest, specs, data, parameters):
    torch.manual_seed(SEED)
    model = AttributeModel(manifest["targets"], specs, **architecture(parameters, manifest)).to(DEVICE)
    try:
        score, history = fit(model, specs, data, parameters)
    except FloatingPointError as error:
        LOG.warning("search candidate diverged: %s", error)
        return None, 0
    finally:
        del model
        torch.cuda.empty_cache()
    return score, len(history)


@timed
def search(directory, stem, base):
    stem.parent.mkdir(parents=True, exist_ok=True)
    record, output = stem.with_suffix(".json"), stem.with_suffix(".pt")
    with Hold(f"search {stem.name}"):
        torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
        manifest, specs, data = load_data(directory)
        history = json.loads(record.read_text(encoding="utf-8")) if record.exists() else []
        started = time.perf_counter()

        def evaluate(phase, values):
            parameters = base | typed(values)
            tick = time.perf_counter()
            score, epochs = candidate(manifest, specs, data, parameters)
            history.append({"phase": phase, "score": score, "epochs": epochs, "seconds": time.perf_counter() - tick, "parameters": parameters})
            write_json(record, history)
            LOG.info("search %s phase=%s trial=%d score=%s best=%.5f epochs=%d seconds=%.0f elapsed=%.0f parameters=%s", stem.name, phase, len(history), "diverged" if score is None else f"{score:.5f}",
                     min(entry["score"] for entry in finished(history)), epochs, history[-1]["seconds"], time.perf_counter() - started, json.dumps(parameters))
            return score

        if not history:
            evaluate("baseline", base)
        phases = {"tpe": lambda: tpe(history, evaluate), "smac": lambda: smac(history, evaluate, stem.with_name(stem.name + "_smac")), "botorch": lambda: botorch(history, evaluate)}
        for phase in SEARCH_PHASES:
            phases[phase]()
        data = None
        torch.cuda.empty_cache()
        best = min(finished(history), key=lambda entry: entry["score"])
        phases = {phase: min((entry["score"] for entry in finished(history) if entry["phase"] == phase), default=None) for phase in ("baseline", *SEARCH_PHASES)}
        LOG.info("search %s trials=%d best=%.5f phase=%s phases=%s parameters=%s", stem.name, len(history), best["score"], best["phase"], json.dumps(phases), json.dumps(best["parameters"]))
        return train(directory, output, best["parameters"]) | {"trials": len(history), "phases": phases, "best_phase": best["phase"]}
