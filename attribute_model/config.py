from pathlib import Path

from database import selected

ROOT = Path(r"C:\reddit_data\attribute_model")
TEXT_ENCODE = 1 << 20
KINDS = {"numeric", "categorical", "embedding", "set"}
SEED = 719
DIMENSIONS = 512
THREADS = 2
VECTOR_RANGES = 64
GPU_MEMORY = .9
PREDICTION_BATCH = 16384
INSERT_ROWS = 1 << 20
SPLITS = {"train": (0, 1, 2, 3, 4, 5, 6), "validation": (7,), "calibration": (8,), "test": (9,)}
SPLIT_LABELS = 100
TEMPERATURE_ROWS = 1 << 16
THRESHOLDS = (.02, .05, .1, .15, .2, .3, .4, .5)
PUBLISH_MARGIN = .05
PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .1, "rank": 256, "batch": 2048, "lr": .002, "weight_decay": .1}
TEXT_PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .3, "rank": 128, "batch": 2048, "lr": .001, "weight_decay": .1}
WARMUP = .2
DECAY = .5
PATIENCE = 2
MIN_IMPROVEMENT = 1e-4


def data():
    return ROOT / selected() / "data"


def model():
    return ROOT / selected() / "model.pt"


def text_data():
    return ROOT / selected() / "text_data"


def text_model():
    return ROOT / selected() / "text_model.pt"


def validate(targets):
    if not isinstance(targets, dict) or not targets:
        raise ValueError("Targets must be a nonempty mapping of attribute names to types")
    for name, kind in targets.items():
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError("Target names must be nonempty strings without surrounding whitespace")
        if kind not in KINDS:
            raise ValueError(f"{name}: target type {kind!r} is not one of {sorted(KINDS)}")
    return dict(targets)

