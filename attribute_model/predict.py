import json
import mmap
import os
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
import torch
from clickhouse_connect.driver.binding import format_str, quote_identifier

from database import author_ranges, client, host, selected

from . import LOG, timed
from .config import DIMENSIONS, GPU_MEMORY, INSERT_ROWS, PREDICTION_BATCH, SPLITS, THREADS, VECTOR_RANGES, data
from torch.nn import functional as F

from .evaluate import INTERVAL, Space, calibrated, grid_choice, node_probabilities, number_scores, owners, scale_choice
from .model import AttributeModel

BINARY = Path(__file__).resolve().parent / "io" / "target" / "release" / "attribute_io.exe"
SLOTS = 6
FETCHERS = 2
ENCODERS = 4
INSERTERS = 2
ARROW = " › "
SPAN = 8


def window(head, logits, fit):
    probability = (logits / fit.get("temperature", 1.)).softmax(1)
    cumulative = F.pad(probability.cumsum(1), (1, 0))
    found = [(cumulative[:, width:] - cumulative[:, :-width]).max(1) for width in range(1, min(SPAN + 1, probability.shape[1]) + 1)]
    shares, starts = torch.stack([share for share, _ in found], 1), torch.stack([start for _, start in found], 1)
    steps = torch.arange(shares.shape[1], device=logits.device)
    extra = torch.where(shares >= INTERVAL, steps, shares.shape[1] - 1).min(1).values
    start, share = starts.gather(1, extra[:, None]).squeeze(1), shares.gather(1, extra[:, None]).squeeze(1)
    years = torch.arange(probability.shape[1], device=logits.device)
    inside = (years >= start[:, None]) & (years <= (start + extra)[:, None])
    middle = (probability * inside).argmax(1)
    return torch.stack([middle, start, start + extra], 1).float() + head.low, share


def build(artifact, device):
    model = AttributeModel(artifact["targets"], artifact["specifications"], artifact["structures"], artifact["choices"], **artifact["architecture"], device=device)
    model.load_state_dict(artifact["model"], strict=True)
    return model.to(device).eval().requires_grad_(False)


def paths(structure):
    names, parents = structure["nodes"], next(iter(structure["groupings"].values()))

    def path(node):
        chain = [names[node]]
        while parents[node] >= 0:
            node = parents[node]
            chain.append(names[node])
        return ARROW.join(reversed(chain))
    return [path(node) for node in range(len(names))]


class Decoder:
    def __init__(self, artifact, device):
        self.model = build(artifact, device)
        self.owners = owners(self.model)
        self.fitted, self.cutoffs = artifact["calibration"], artifact["cutoffs"]
        self.spaces, self.labels, self.slots, self.numbers, self.groups, self.fields = {}, {}, {}, [], {}, {}
        for name, structure in artifact["structures"].items():
            kind = structure["kind"]
            if kind == "number":
                self.numbers.append(name)
                self.fields[name] = ("", "_low", "_high", "_confidence") if self.owners[name][1].mode == "bins" else ("", "_low", "_high")
            elif kind == "tree":
                self.spaces[name] = Space(structure, artifact["information"][name], device)
                crossed = len(structure["groupings"]) > 1
                self.labels[name], self.slots[name] = list(structure["nodes"]) if crossed else paths(structure), self.spaces[name].slots
                if crossed:
                    self.groups[name] = torch.ones(len(structure["nodes"]), dtype=torch.bool, device=device).index_fill_(0, torch.tensor(structure["values"], device=device), False)
            else:
                cells = {cell: value for value, cell in zip(structure["names"], structure["values"])} if kind == "grid" else dict(enumerate(structure["names"]))
                self.labels[name], self.slots[name] = [cells[index] for index in range(len(cells))], 1
        self.ranked = [name for name in artifact["structures"] if name not in self.numbers]

    def decide(self, vectors, uncut=False):
        hidden = self.model(vectors)
        numbers, picked, chances = [], [], []
        for name in self.model.structures:
            key, head = self.owners[name]
            fit = self.fitted[key]
            logits = head(hidden).float()
            if name in self.numbers:
                if head.mode == "bins":
                    found, share = window(head, logits, fit)
                    numbers.append(torch.cat([found, share[:, None]], 1))
                    continue
                _, middle, low, high = number_scores(head, logits, torch.zeros(len(logits), device=logits.device), fit)
                numbers.append(torch.stack([middle, low, high], 1))
                continue
            structure = self.model.structures[name]
            probability = node_probabilities(head, logits, fit, name)
            if structure["kind"] == "tree":
                space = self.spaces[name]
                nodes = space.ordered(space.decode(probability, 0. if uncut else self.cutoffs[name]["cutoff"]))
                if name in self.groups:
                    nodes = torch.where((nodes >= 0) & ~self.groups[name][nodes.clamp_min(0)], nodes, -1)
                chance = probability.gather(1, nodes.clamp_min(0))
            else:
                nodes = (scale_choice(probability) if structure["kind"] == "scale" else grid_choice(probability, structure["shape"]))[:, None]
                chance = probability.gather(1, nodes)
            picked.append(nodes)
            chances.append(torch.where(nodes >= 0, calibrated(chance, self.cutoffs[name]["platt"]), 0.))
        return torch.cat(numbers, 1), torch.cat(picked, 1).int(), torch.cat(chances, 1)

    def readable(self, decided):
        numbers, picked, chances = (part.cpu() for part in decided)
        result = [{} for _ in range(len(picked))]
        start = 0
        for name in self.numbers:
            width = len(self.fields[name])
            for row, found in enumerate(numbers[:, start:start + width].tolist()):
                result[row][name] = {"value": round(found[0], 1), "low": round(found[1], 1), "high": round(found[2], 1)} | ({"confidence": round(found[3], 3)} if width == 4 else {})
            start += width
        start = 0
        for name in self.ranked:
            width = self.slots[name]
            for row, (nodes, scores) in enumerate(zip(picked[:, start:start + width].tolist(), chances[:, start:start + width].tolist())):
                result[row][name] = [{"value": self.labels[name][node], "confidence": round(score, 3)} for node, score in zip(nodes, scores) if node >= 0]
            start += width
        return result


def schema(decoder, artifact):
    columns = "".join(f", {quote_identifier(name + field)} Float32" for name in decoder.numbers for field in decoder.fields[name])
    columns += "".join(f", {quote_identifier(name)} Array(LowCardinality(String)), {quote_identifier(name + '_confidence')} Array(Float32)" for name in decoder.ranked)
    comment = json.dumps({"model_id": artifact["model_id"], "source": artifact["source"], "targets": {name: ("window" if len(decoder.fields[name]) == 4 else "number") if name in decoder.numbers else "ranked" for name in artifact["targets"]}})
    return f"CREATE TABLE author_predictions_next (author String{columns}) ENGINE = MergeTree ORDER BY author COMMENT {format_str(comment)}"


@lru_cache(maxsize=1)
def cached(path, modified):
    torch.set_num_threads(THREADS)
    return Decoder(torch.load(path, map_location="cpu", weights_only=True), "cpu")


def load_model(path):
    path = Path(path).resolve()
    return cached(str(path), path.stat().st_mtime_ns)


@timed
def predict(decoder, vectors, uncut=False):
    values = np.asarray(vectors, dtype=np.float32)
    inputs = decoder.model.input.in_features
    if values.ndim != 2 or values.shape[1] != inputs or not np.isfinite(values).all():
        raise ValueError(f"Expected finite {inputs}-dimensional inputs")
    result = []
    with torch.inference_mode():
        for start in range(0, len(values), 1024):
            result += decoder.readable(decoder.decide(torch.from_numpy(values[start:start + 1024]), uncut))
    return result


def slot_views(shared, sizes, widths):
    memory = torch.frombuffer(shared, dtype=torch.uint8)
    slot_bytes, offsets = sum(sizes), np.cumsum([0, *sizes])
    return [[memory[slot * slot_bytes + offsets[index]:slot * slot_bytes + offsets[index + 1]].view(dtype).view(PREDICTION_BATCH, width)
             for index, (dtype, width) in enumerate(zip((torch.float32, torch.float32, torch.int32, torch.float32), widths))] for slot in range(SLOTS)]


@timed
def stream(decoder, ranges, table, total):
    pairs = sum(decoder.slots[name] for name in decoder.ranked)
    widths = (DIMENSIONS, sum(len(decoder.fields[name]) for name in decoder.numbers), pairs, pairs)
    sizes = [PREDICTION_BATCH * width * 4 for width in widths]
    name = f"attribute_predict_{os.getpid()}"
    shared = mmap.mmap(-1, SLOTS * sum(sizes), tagname=name)
    views = slot_views(shared, sizes, widths)
    columns = [{"name": target + field, "type": "numeric"} for target in decoder.numbers for field in decoder.fields[target]]
    columns += [{"name": target, "type": "ranked", "values": decoder.labels[target], "slots": decoder.slots[target]} for target in decoder.ranked]
    layout = {"shared": name, "table": table, "batch": PREDICTION_BATCH, "slots": SLOTS, "fetchers": FETCHERS, "encoders": ENCODERS, "inserters": INSERTERS, "insert_rows": INSERT_ROWS,
              "dimensions": DIMENSIONS, "slot_bytes": sum(sizes), "ranges": ranges, "columns": columns}
    users, logged, started = 0, 0, time.perf_counter()
    with TemporaryDirectory() as directory:
        path = Path(directory) / "layout.json"
        path.write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")
        process = subprocess.Popen([str(BINARY), "predict", str(path), "--host", host(), "--database", selected()], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for line in process.stdout:
                if line == b"end\n":
                    break
                slot, rows = map(int, line.split())
                with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                    decided = decoder.decide(views[slot][0][:rows].to("cuda"))
                for target, source in zip(views[slot][1:], decided):
                    target[:rows].copy_(source)
                process.stdin.write(b"%d\n" % slot)
                process.stdin.flush()
                users += rows
                if users - logged >= INSERT_ROWS:
                    logged, elapsed = users, time.perf_counter() - started
                    LOG.info("attribute predictions users=%d of %d rate=%.0f/s eta=%.0fs", users, total, users / elapsed, (total - users) * elapsed / users)
            process.stdin.close()
            code = process.wait()
        except BaseException:
            process.kill()
            raise
    del views
    shared.close()
    if code:
        raise RuntimeError(f"attribute_io predict exited with {code}")
    return users


@timed
def predict_table(model_path):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    artifact = torch.load(model_path, map_location="cpu", weights_only=True)
    splits = np.load(data() / "splits.npy", mmap_mode="r")
    prepared = {name: int(np.isin(splits, buckets).sum()) for name, buckets in SPLITS.items()}
    if artifact["authors"] != prepared:
        raise ValueError(f"{model_path} was trained on other prepared data ({artifact['authors']}) than {data()} ({prepared})")
    decoder = Decoder(artifact, "cuda")
    db = client()
    db.command("DROP TABLE IF EXISTS author_predictions_next")
    db.command(schema(decoder, artifact))
    total = db.command("SELECT count() FROM author_vectors")
    if not total:
        raise ValueError("No author vectors to predict")
    users = stream(decoder, author_ranges(db, "author_vectors", VECTOR_RANGES), "author_predictions_next", total)
    if users != total:
        raise ValueError("Author vectors changed while predictions were written")
    db.command("CREATE TABLE IF NOT EXISTS author_predictions AS author_predictions_next")
    db.command("EXCHANGE TABLES author_predictions_next AND author_predictions")
    db.command("DROP TABLE author_predictions_next")
    return {"model_id": artifact["model_id"], "users": users, "targets": len(artifact["targets"])}


@timed
def predict_file(model_path, input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    if output_path.exists():
        raise FileExistsError(output_path)
    decoder = load_model(model_path)
    records = []
    with input_path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                record = json.loads(line)
                if not isinstance(record, dict) or not isinstance(record.get("vector"), list):
                    raise ValueError(f"Line {number} needs a vector array")
                records.append((number, record))
    if not records:
        raise ValueError("Input contains no vectors")
    predictions = predict(decoder, [record["vector"] for _, record in records])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, prefix=output_path.name + ".", suffix=".tmp", delete=False) as destination:
            temporary = Path(destination.name)
            for (number, record), attributes in zip(records, predictions):
                destination.write(json.dumps({"id": record.get("id", record.get("author", number)), "attributes": attributes}, ensure_ascii=False) + "\n")
        temporary.rename(output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"predictions": len(records), "output": str(output_path)}


@timed
def predict_user(model_path, author):
    found = client().query("SELECT texts, vector FROM author_vectors WHERE author = {author:String}", parameters={"author": author}).result_rows
    if not found:
        raise ValueError(f"No author vector for {author}")
    texts, vector = found[0]
    return {"author": author, "texts": texts, "attributes": predict(load_model(model_path), [vector])[0]}
