import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import numpy as np
import torch

from . import timed
from .config import SPLITS, validate

ARRAYS = ("users", "labels")
BLOCK = 32 << 20
READERS = 4


@timed
def prepare(directory):
    from pipeline.run import rust
    directory = Path(directory)
    rust("attribute_model/io", "attribute_io", "prepare", "attribute_prepare.log", str(directory))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return {"authors": manifest["authors"], "directory": str(directory), "targets": manifest["targets"], "target_counts": manifest["target_counts"],
            "excluded_values": manifest["excluded_values"], "insufficient": manifest["insufficient"]}


class Stored(NamedTuple):
    path: Path
    offset: int
    dtype: np.dtype
    shape: tuple


def stored(path):
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    return Stored(path, array.offset, array.dtype, array.shape)


def fill(stream, view):
    done = 0
    while done < len(view):
        read = stream.readinto(view[done:done + BLOCK])
        if not read:
            raise EOFError(f"{stream.name} ended early")
        done += read


def read(source, start, end, device, readers):
    pool, staging = readers
    width = int(np.prod(source.shape[1:], dtype=np.int64)) * source.dtype.itemsize
    target = torch.empty((end - start, *source.shape[1:]), dtype=torch.from_numpy(np.empty(0, source.dtype)).dtype, device=device)
    flat = target.view(-1).view(torch.uint8)
    offset = source.offset + start * width

    def part(slot):
        buffer, done = staging[slot]
        with open(source.path, "rb", buffering=0) as stream:
            for low in range(slot * BLOCK, len(flat), len(staging) * BLOCK):
                size = min(BLOCK, len(flat) - low)
                stream.seek(offset + low)
                if device == "cpu":
                    fill(stream, memoryview(flat[low:low + size].numpy()))
                    continue
                done.synchronize()
                fill(stream, memoryview(buffer.numpy())[:size])
                flat[low:low + size].copy_(buffer[:size], non_blocking=True)
                done.record()
    list(pool.map(part, range(len(staging))))
    if device != "cpu":
        torch.cuda.current_stream().synchronize()
    return target


def reader():
    return ThreadPoolExecutor(READERS), [(torch.empty(BLOCK, dtype=torch.uint8, pin_memory=True), torch.cuda.Event()) for _ in range(READERS)]


def load(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    targets = validate(manifest["targets"])
    arrays = {name: stored(directory / f"{name}.npy") for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], manifest["features"]["dimensions"]) or arrays["labels"].shape != (manifest["authors"], len(targets)):
        raise ValueError("Prepared arrays do not match the manifest")
    splits = np.load(directory / "splits.npy", allow_pickle=False)
    bounds = [manifest["splits"][name] for name in SPLITS]
    if len(splits) != manifest["authors"] or [start for start, _ in bounds] + [manifest["authors"]] != [0] + [end for _, end in bounds] or not all(np.isin(splits[start:end], buckets).all() for (start, end), buckets in zip(bounds, SPLITS.values())):
        raise ValueError("Prepared splits do not match the manifest")
    sets = {name: tuple(stored(directory / "sets" / f"{name}.{part}.npy") for part in ("indptr", "values")) for name, kind in targets.items() if kind == "set"}
    if any(indptr.shape != (manifest["authors"] + 1,) for indptr, _ in sets.values()):
        raise ValueError("Prepared value lists do not match the manifest")
    return manifest, arrays, sets
