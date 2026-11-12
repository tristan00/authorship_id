import json
import math
import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

import torch

from . import LOG, timed
from .config import CHOICES, GPU_MEMORY, MIN_IMPROVEMENT, PARAMETERS, SEED, SPLIT_LABELS, SPLITS
from .data import load, read, reader
from .evaluate import CHUNK, DEVICE, Evaluation, Split, calibrate, chunks, climate, objective, sentinel
from .heads import RANKED, Grid, Number, Scale, Tree
from .model import AttributeModel, choices_for, specifications
from .structure import Graph, build, truth

BASELINE_ROWS = 1 << 17


@timed
def place_split(arrays, sets, columns, readers, name, start, end):
    device = DEVICE if name in ("train", "validation") else "cpu"
    members = {}
    for target, (indptr, values) in sets.items():
        offsets = read(indptr, start, end + 1, device, readers)
        low, high = int(offsets[0]), int(offsets[-1])
        members[columns[target]] = (offsets - low, read(values, low, high, device, readers).long())
    return read(arrays["users"], start, end, device, readers), read(arrays["labels"], start, end, device, readers), members


def splits_of(manifest, data, structures):
    columns = {name: column for column, name in enumerate(manifest["targets"])}
    graphs, found = {}, {}
    for split, (inputs, labels, members) in data.items():
        truths, raw = {}, {}
        for name, structure in structures.items():
            if structure["kind"] == "number":
                continue
            graph = None
            if structure["kind"] == "tree":
                graph = graphs.setdefault((name, labels.device.type), Graph(structure, labels.device))
            truths[name] = (*truth(structure, columns[name], columns, labels, members, graph), sentinel(structure))
            if manifest["targets"][name] == "set":
                raw[name] = (*members[columns[name]], len(manifest["catalogs"][name]))
        found[split] = Split(inputs, labels, truths, raw)
    return found


@timed
def statistics(manifest, specs, structures, train):
    columns = {name: column for column, name in enumerate(manifest["targets"])}
    information, counts, climates = {}, {}, {}
    for spec in specs:
        name, structure = spec["name"], structures[spec["name"]]
        column = train.labels[:, columns[name]]
        if structure["kind"] == "number":
            observed = column[torch.isfinite(column)]
            low = math.floor(spec["low"])
            counts[name] = {"bins": torch.bincount((observed - low).round().long(), minlength=math.ceil(spec["high"]) - low + 1).float()}
            climates[name] = climate(spec, column.cpu())
            continue
        indptr, values, _ = train.truths[name]
        found = {"authors": int((indptr.diff() > 0).sum())}
        if structure["kind"] == "tree":
            graph = Graph(structure, DEVICE)
            information[name] = graph.information(indptr.to(DEVICE), values.to(DEVICE)).cpu()
            found["nodes"] = torch.bincount(values, minlength=graph.size).float()
            if name in train.raw:
                found["values"] = torch.bincount(train.raw[name][1], minlength=len(spec["values"])).float()
            else:
                observed = column[torch.isfinite(column)].long()
                found["values"] = torch.bincount(observed, minlength=len(spec["values"])).float()
        else:
            found["positions"] = torch.bincount(values, minlength=sentinel(structure)).float()
        counts[name] = found
    return information, counts, climates


def load_splits(manifest, arrays, sets, directory):
    columns = {name: column for column, name in enumerate(manifest["targets"])}
    readers = reader()
    data = {name: place_split(arrays, sets, columns, readers, name, start, end) for name, (start, end) in manifest["splits"].items()}
    labels = data["train"][1]
    specs = specifications(manifest["targets"], manifest["catalogs"], [column[torch.isfinite(column)].cpu().numpy() for column in labels.T])
    for slot, name in enumerate(SPLITS):
        short = [target for target, counts in manifest["split_labels"].items() if counts[slot] < SPLIT_LABELS]
        if short:
            raise ValueError(f"Fewer than {SPLIT_LABELS} {name} labels for {', '.join(short)}")
    structures = build(manifest, directory)
    splits = splits_of(manifest, data, structures)
    LOG.info("attribute model rows=%s", {name: len(split) for name, split in splits.items()})
    return specs, structures, splits, statistics(manifest, specs, structures, splits["train"])


@timed
def load_data(directory):
    manifest, arrays, sets = load(directory)
    if manifest["insufficient"]:
        raise ValueError(f"Targets without enough labels: {sorted(manifest['insufficient'])}")
    return (manifest, *load_splits(manifest, arrays, sets, directory))


def initialize(model, counts):
    for head in model.heads.values():
        if isinstance(head, Number):
            head.initialize(counts[head.targets[0]]["bins"])
        elif isinstance(head, Tree):
            found = counts[head.targets[0]]
            with torch.no_grad():
                if head.mode == "flat" and head.single:
                    head.output.offset().copy_(((found["values"] + .5) / (found["values"].sum() + .5 * len(found["values"]))).log().to(DEVICE))
                elif head.mode == "flat":
                    head.output.offset().copy_(((found["values"] + .5) / (found["authors"] + 1)).clamp(max=1 - 1e-4).logit().to(DEVICE))
                elif head.mode == "tree":
                    head.initialize(found["nodes"].to(DEVICE))
        elif isinstance(head, (Scale, Grid)) and head.mode != "born":
            head.initialize(counts[head.targets[0]]["positions"].to(DEVICE))


@timed
def prepare_heads(model, specs, train, batch):
    labeled = {spec["name"]: spec["training_labels"] for spec in specs}
    sums = counts = present = 0
    with torch.no_grad():
        for start in range(0, min(BASELINE_ROWS, len(train)), CHUNK):
            sample = train.batch(torch.arange(start, min(start + CHUNK, len(train)), device=train.labels.device))
            found = model.terms(torch.zeros((len(sample.labels), model.input.out_features), device=DEVICE), sample, limited=False)
            sums, counts = sums + found[0], counts + found[1]
            present = present + torch.stack([head.present(sample).sum() for head in model.heads.values()])
    present = (present.float() / min(BASELINE_ROWS, len(train))).tolist()
    for head, rate in zip(model.heads.values(), present):
        if head.size > RANKED:
            head.capacity = min(batch, 64 * math.ceil((rate * batch + 8 * math.sqrt(rate * (1 - rate) * batch)) / 64))
    weight = torch.tensor([sum(labeled[name] for name in head.targets) for head in model.heads.values()], dtype=torch.float32, device=DEVICE)
    model.baseline.copy_(sums / counts.clamp_min(1))
    model.weight.copy_(weight / weight.mean())


@timed
def validate(model, split):
    sums = counts = 0
    with torch.inference_mode():
        for hidden, batch in chunks(model, split):
            found = model.terms(hidden.float(), batch, limited=False)
            sums, counts = sums + found[0], counts + found[1]
    ratios = (sums / counts.clamp_min(1) / model.baseline).tolist()
    fields = {}
    for (key, head), ratio in zip(model.heads.items(), ratios):
        fields |= {name: ratio for name in head.targets}
    return sum(fields.values()) / len(fields), fields


@timed
def fit(model, splits, parameters):
    train = splits["train"]
    return run_epochs(model, len(train), parameters, lambda index: model.loss(model(train.inputs[index]), train.batch(index)), lambda: validate(model, splits["validation"]))


def run_epochs(model, rows, parameters, loss_of, validate):
    batch = parameters["batch"]
    batches = rows // batch
    warmup = max(1, round(parameters["warmup"] * batches))
    lr = parameters["lr"]
    rate = torch.tensor(lr, device=DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=rate, weight_decay=parameters["weight_decay"], fused=True, capturable=True)
    index = torch.zeros(batch, dtype=torch.long, device=DEVICE)
    generator = torch.Generator(device=DEVICE).manual_seed(SEED)

    def schedule(number):
        return lr * min(1, (number + 1) / warmup)

    def step():
        with torch.autocast(DEVICE, dtype=torch.bfloat16, cache_enabled=False):
            loss, overflow = loss_of(index)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1., foreach=True)
        optimizer.step()
        return loss.detach(), overflow

    order = torch.randperm(rows, device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
    model.train()
    side = torch.cuda.Stream()
    side.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(side):
        for number in range(3):
            index.copy_(order[number])
            rate.fill_(schedule(number))
            optimizer.zero_grad(set_to_none=True)
            step()
    torch.cuda.current_stream().wait_stream(side)
    graph = torch.cuda.CUDAGraph()
    optimizer.zero_grad(set_to_none=True)
    with torch.cuda.graph(graph):
        loss, overflow = step()
    best, saved, history, number, stale, started = math.inf, None, [], 3, 0, time.perf_counter()
    while stale < parameters["patience"]:
        epoch = len(history)
        if epoch:
            order = torch.randperm(rows, device=DEVICE, generator=generator)[:batches * batch].view(batches, batch)
        model.train()
        total = torch.zeros((), device=DEVICE)
        dropped = torch.zeros((), dtype=torch.long, device=DEVICE)
        for selected in order[3 if epoch == 0 else 0:]:
            index.copy_(selected)
            rate.fill_(schedule(number))
            graph.replay()
            total += loss
            dropped += overflow
            number += 1
        if not torch.isfinite(total) or dropped:
            raise FloatingPointError(f"Nonfinite attribute-model loss or {int(dropped)} labeled rows beyond the head capacity")
        trained = time.perf_counter() - started
        validation, fields = validate()
        history.append({"epoch": epoch + 1, "lr": lr, "training_loss": float(total) / (batches - (3 if epoch == 0 else 0)), "validation_score": validation, "fields": fields})
        LOG.info("attribute model epoch=%d lr=%.2e loss=%.5f validation=%.5f train_seconds=%.1f seconds=%.1f", epoch + 1, lr, history[-1]["training_loss"], validation, trained, time.perf_counter() - started)
        improved = best - validation >= MIN_IMPROVEMENT
        if validation < best:
            best, saved = validation, {name: value.detach().clone() for name, value in model.state_dict().items()}
        stale = 0 if improved else stale + 1
        lr = lr if improved else lr * parameters["decay"]
    del graph
    model.load_state_dict(saved)
    return best, history


def architecture(parameters, manifest):
    return {**{key: parameters[key] for key in ("width", "depth", "expand", "dropout", "rank")}, "features": manifest["features"]}


def built(manifest, specs, structures, choices, parameters, counts, train):
    choices = {key: choices.get(key, found[0]) for key, found in choices_for(structures).items()}
    LOG.info("attribute model choices=%s", json.dumps(choices))
    torch.manual_seed(SEED)
    model = AttributeModel(manifest["targets"], specs, structures, choices, **architecture(parameters, manifest)).to(DEVICE)
    initialize(model, counts)
    prepare_heads(model, specs, train, parameters["batch"])
    return model


@timed
def assess(model, splits, stats, names=("validation",)):
    information, counts, climates = stats
    fitted = calibrate(model, splits["calibration"])
    evaluation = Evaluation(model, information, {name: found.get("positions") for name, found in counts.items()}, climates)
    cutoffs = evaluation.cutoffs(splits["calibration"], fitted)
    reports = {name: evaluation.score(splits[name], fitted, cutoffs) for name in names}
    return fitted, cutoffs, reports


@timed
def finish(model, manifest, specs, structures, splits, stats, parameters, best, history, output):
    output = Path(output)
    fitted, cutoffs, reports = assess(model, splits, stats, ("validation", "test"))
    for name, fields in reports["test"].items():
        LOG.info("attribute model test %s %s", name, json.dumps(fields))
    LOG.info("attribute model objective validation=%.5f test=%.5f", objective(reports["validation"]), objective(reports["test"]))
    information, counts, _ = stats
    artifact = {"model_id": str(uuid.uuid4()), "targets": manifest["targets"], "specifications": specs, "structures": structures, "choices": model.choices,
                "architecture": architecture(parameters, manifest), "parameters": parameters, "model": {name: value.cpu() for name, value in model.state_dict().items()},
                "calibration": fitted, "cutoffs": cutoffs, "information": {name: value.tolist() for name, value in information.items()},
                "priors": {name: found["positions"].tolist() for name, found in counts.items() if "positions" in found},
                "evaluation": reports["test"], "validation": reports["validation"], "objective": objective(reports["validation"]), "history": history, "validation_score": best,
                "source": manifest["source"], "authors": {name: len(split) for name, split in splits.items()}, "splits": SPLITS}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, prefix=output.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(artifact, stream)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"model": str(output), "model_id": artifact["model_id"], "parameters": parameters, "choices": model.choices, "validation_score": best, "objective": artifact["objective"],
            "test_objective": objective(reports["test"]), "evaluation": reports["test"]}


@timed
def train(directory, output, parameters=PARAMETERS, choices=CHOICES):
    torch.cuda.set_per_process_memory_fraction(GPU_MEMORY)
    manifest, specs, structures, splits, stats = load_data(directory)
    model = built(manifest, specs, structures, choices, parameters, stats[1], splits["train"])
    best, history = fit(model, splits, parameters)
    return finish(model, manifest, specs, structures, splits, stats, parameters, best, history, output)
