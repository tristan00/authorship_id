import hashlib
import json
from pathlib import Path

TARGETS = Path(__file__).with_name("targets.json")
ROOT = Path(r"C:\reddit_data\attribute_model")
DATA = ROOT / "data"
MODEL = ROOT / "model.pt"
KINDS = {"numeric", "categorical", "embedding"}
SEED = 719
THREADS = 2
SPLITS = {"train": (0, 1, 2, 3, 4, 5, 6), "validation": (7,), "calibration": (8,), "test": (9,)}
QUANTILES = (.05, .5, .95)
PARAMETERS = {"width": 1024, "depth": 3, "expand": 1, "dropout": .27, "rank": 128, "batch": 2048, "lr": .0015, "weight_decay": .27, "epochs": 6, "interval_mass": .9}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate target: {key}")
        result[key] = value
    return result


def validate(targets):
    if not isinstance(targets, dict) or not targets:
        raise ValueError("Targets must be a nonempty JSON object mapping attribute names to types")
    for name, kind in targets.items():
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError("Target names must be nonempty strings without surrounding whitespace")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError(f"{name}: target type must be numeric, categorical, or embedding")
    return dict(targets)


def read_targets(path=TARGETS):
    return validate(json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique))


def partition(author):
    return int(hashlib.sha256(f"attribute-model:{author.casefold()}".encode()).hexdigest()[:8], 16) % 10


def columns(name, kind):
    return (name, f"{name}_lower", f"{name}_upper") if kind == "numeric" else (name, f"{name}_probability")


def check_targets(expected, actual):
    if list(expected.items()) != list(actual.items()):
        raise ValueError("Target configuration differs from the saved data or model; prepare and train with the current JSON")
