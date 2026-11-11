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
PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .1, "rank": 256, "batch": 2048, "lr": .002, "weight_decay": .1, "warmup": .2, "decay": .5, "patience": 2}
TEXT_PARAMETERS = {"width": 1024, "depth": 2, "expand": 1, "dropout": .3, "rank": 128, "batch": 2048, "lr": .001, "weight_decay": .1, "warmup": .2, "decay": .5, "patience": 2}
MIN_IMPROVEMENT = 1e-4
SEARCH_SPACE = {"width": (256, 2048, True), "depth": (0, 4, False), "expand": (1, 4, False), "dropout": (0., .5, False), "rank": (32, 512, True), "batch": (512, 16384, True),
                "lr": (1e-4, 1e-2, True), "weight_decay": (1e-3, 1., True), "warmup": (.01, 1., True), "decay": (.1, .8, False)}
SEARCH_PHASES = ("tpe", "smac", "botorch")
SEARCH_PATIENCE = 10


def data():
    return ROOT / selected() / "data"


def model():
    return ROOT / selected() / "model.pt"


def text_data():
    return ROOT / selected() / "text_data"


def text_model():
    return ROOT / selected() / "text_model.pt"


def searched():
    return ROOT / selected() / "search"


def validate(targets):
    if not isinstance(targets, dict) or not targets:
        raise ValueError("Targets must be a nonempty mapping of attribute names to types")
    for name, kind in targets.items():
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError("Target names must be nonempty strings without surrounding whitespace")
        if kind not in KINDS:
            raise ValueError(f"{name}: target type {kind!r} is not one of {sorted(KINDS)}")
    return dict(targets)

