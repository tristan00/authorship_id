import hashlib
from pathlib import Path


ROOT = Path(r"C:\reddit_data\attribute_model")
DATA = ROOT / "data"
MODEL = ROOT / "model.pt"
KINDS = {"numeric", "categorical", "embedding", "set"}
SEED = 719
DIMENSIONS = 512
THREADS = 2
VECTOR_RANGES = 64
GPU_MEMORY = .9
PREDICTION_BATCH = 16384
INSERT_ROWS = 1 << 20
SPLITS = {"train": (0, 1, 2, 3, 4, 5, 6), "validation": (7,), "calibration": (8,), "test": (9,)}
VALUE_AUTHORS = 10
SPLIT_LABELS = 100
CATEGORICAL_VALUES = 256
TEMPERATURE_ROWS = 1 << 16
THRESHOLDS = (.02, .05, .1, .15, .2, .3, .4, .5)
PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .1, "rank": 256, "batch": 2048, "lr": .002, "weight_decay": .1, "epochs": 6}


def validate(targets):
    if not isinstance(targets, dict) or not targets:
        raise ValueError("Targets must be a nonempty mapping of attribute names to types")
    for name, kind in targets.items():
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError("Target names must be nonempty strings without surrounding whitespace")
        if kind not in KINDS:
            raise ValueError(f"{name}: target type {kind!r} is not one of {sorted(KINDS)}")
    return dict(targets)


def partition(author):
    return int(hashlib.sha256(f"attribute-model:{author.casefold()}".encode()).hexdigest()[:8], 16) % 10
