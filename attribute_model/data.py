import json
from pathlib import Path

import numpy as np

from . import timed
from .config import validate

ARRAYS = ("users", "labels", "splits")


@timed
def prepare(directory):
    from pipeline.run import rust
    directory = Path(directory)
    rust("attribute_model/io", "attribute_io", "prepare", "attribute_prepare.log", str(directory))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return {"authors": manifest["authors"], "directory": str(directory), "targets": manifest["targets"], "target_counts": manifest["target_counts"],
            "excluded_values": manifest["excluded_values"], "insufficient": manifest["insufficient"]}


def load(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    targets = validate(manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or arrays["labels"].shape != (manifest["authors"], len(targets)) or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    sets = {name: tuple(np.load(directory / "sets" / f"{name}.{part}.npy", mmap_mode="r", allow_pickle=False) for part in ("indptr", "values"))
            for name, kind in targets.items() if kind == "set"}
    if any(len(indptr) != manifest["authors"] + 1 for indptr, _ in sets.values()):
        raise ValueError("Prepared value lists do not match the manifest")
    return manifest, arrays, sets
