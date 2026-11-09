import hashlib
import json
from pathlib import Path

from claim_extraction.schema import BINARY, NO

TARGETS = Path(__file__).with_name("targets.json")
ROOT = Path(r"C:\reddit_data\attribute_model")
DATA = ROOT / "data"
MODEL = ROOT / "model.pt"
TUNE = ROOT / "tune"
KINDS = {"numeric", "categorical", "embedding"}
NUMERIC = {"age": (13, 100), "height": (120, 230), "weight": (30, 300), "income": (1000, 10_000_000)}
SEED = 719
DIMENSIONS = 512
THREADS = 2
GPU_MEMORY = .9
PREDICTION_BATCH = 16384
INSERT_ROWS = 1 << 20
SPLITS = {"train": (0, 1, 2, 3, 4, 5, 6), "validation": (7,), "calibration": (8,), "test": (9,)}
STRICT_SUPPORT = 2.
TRAIN_SUPPORT = 1.
STRICT_SHARE = .7
VALUE_AUTHORS = 10
SUBREDDITS_PER_AUTHOR = 32
SUBREDDIT_AUTHORS = 100
DEFAULTS = {"native_language": "english", "sexual_orientation": "straight", "parental_status": "no children", "military_status": "never served", "smoking": "non-smoker", "diet": "eats meat",
            **dict.fromkeys(BINARY, NO)}
TEMPERATURE_ROWS = 1 << 16
PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .1, "rank": 256, "batch": 2048, "lr": .002, "weight_decay": .1, "epochs": 6, "activity": True}
TUNE_TRIALS = 18
TUNE_SPACE = {"width": (512, 1024, 2048), "depth": (1, 2, 3), "expand": (1, 2), "dropout": (.1, .2, .3, .5), "rank": (64, 128, 256), "batch": (1024, 2048, 4096), "lr": (3e-4, 5e-4, 1e-3, 2e-3), "weight_decay": (.01, .1, .3), "activity": (True, False)}


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


def check_targets(expected, actual):
    if list(expected.items()) != list(actual.items()):
        raise ValueError("Target configuration differs from the saved data or model; prepare and train with the current JSON")
