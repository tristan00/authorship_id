import math
import re
import time
from collections import Counter, defaultdict

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from transformers import AutoModel, AutoTokenizer

from . import LOG, timed
from .annotate import facts
from .config import BATCH_TEXTS, BATCH_TOKENS, ENCODER, EPOCHS, EXTRACTOR, FLOOR, LEARNING_RATE, MAX_TOKENS, OVERLAP, SEED, SPAN_CUT, YEAR
from .schema import CITY_FIELDS, COUNTRY_FIELDS, FREE, REGION_FIELDS

DEVICE = "cuda"
ENCODE_CHUNK = 50_000
OTHER = "<other>"
LIMITS = {**dict.fromkeys(CITY_FIELDS, 4000), **dict.fromkeys(REGION_FIELDS, 400), **dict.fromkeys(COUNTRY_FIELDS, 200), "native_language": 200}
DIGIT = re.compile(r"\d[\d,.]*")
WHOLE = re.compile(r"(?<![\d.,])(\d{1,4})(?![\d,]|\.\d)")
IMPERIAL = re.compile(r"(\d)\s*(?:'|’|ft|feet|foot)\s*(\d{1,2})?")
METERS = re.compile(r"(?<!\d)([12])[.,](\d{2})(?!\d)")
CENTIMETERS = re.compile(r"(?<!\d)(1\d{2}|2[0-2]\d)\s*cm")
POUNDS = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:lbs?|pounds?)")
KILOS = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:kgs?|kilos?|kilograms?)")
STONE = re.compile(r"(\d{1,2})\s*(?:st\b|stone)")
AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(k\b|thousand|m\b|mil|million)?", re.I)
SCALES = {"k": 1000, "t": 1000, "m": 1_000_000}
TIGHT = {"height", "weight", "income"}


def bucket(attribute, value):
    if attribute in ("age", "height"):
        return str(round(value))
    if attribute == "weight":
        return str(round(value / 2) * 2)
    if attribute == "income":
        return str(round(math.log10(max(value, 1000)) * 20) / 20)
    return value


def shown(attribute, value):
    return str(round(10 ** float(value))) if attribute == "income" else value


def read_age(text):
    for match in WHOLE.finditer(text):
        amount = int(match.group(1))
        if 1900 <= amount <= YEAR:
            return str(YEAR - amount)
        if 1 <= amount <= 120:
            return str(amount)
    return None


def read_height(text):
    if match := IMPERIAL.search(text):
        return str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54))
    if match := METERS.search(text):
        return str(int(match.group(1)) * 100 + int(match.group(2)))
    return match.group(1) if (match := CENTIMETERS.search(text)) else None


def read_weight(text):
    if match := POUNDS.search(text):
        return str(round(float(match.group(1)) * .4536))
    if match := KILOS.search(text):
        return str(round(float(match.group(1))))
    return str(round(int(match.group(1)) * 6.35)) if (match := STONE.search(text)) else None


def read_income(text):
    if not (match := AMOUNT.search(text)):
        return None
    amount = float(match.group(1).replace(",", "")) * SCALES.get((match.group(2) or "").lower()[:1], 1)
    return str(math.log10(amount)) if 1000 <= amount <= 100_000_000 else None


READERS = {"age": read_age, "height": read_height, "weight": read_weight, "income": read_income}


class Extractor(nn.Module):
    def __init__(self, catalog, encoder):
        super().__init__()
        self.catalog = catalog
        self.attributes = list(catalog)
        self.encoder = AutoModel.from_pretrained(encoder)
        width = self.encoder.config.hidden_size
        self.scorer = nn.Linear(width, len(self.attributes))
        self.values = nn.ModuleList(nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, len(catalog[name]))) for name in self.attributes)
        self.scorer.bias.data.fill_(-4.)

    def forward(self, ids, pad):
        mask = ids != pad
        hidden = self.encoder(input_ids=ids, attention_mask=mask).last_hidden_state
        return hidden, self.scorer(hidden).masked_fill(~mask[..., None], -30.)


def padded(rows, pad):
    width = max(map(len, rows))
    ids = np.full((len(rows), width), pad, dtype=np.int64)
    for row, values in enumerate(rows):
        ids[row, :len(values)] = values
    return torch.from_numpy(ids)


def splitter(name):
    tokenizer = AutoTokenizer.from_pretrained(name).backend_tokenizer
    tokenizer.enable_truncation(max_length=MAX_TOKENS, stride=OVERLAP)
    tokenizer.no_padding()
    return tokenizer


def windows(tokenizer, texts):
    ids, offsets, lengths, owners = [], [], [], []
    for owner, encoding in enumerate(tokenizer.encode_batch(texts)):
        for piece in (encoding, *encoding.overflowing):
            found = piece.ids
            ids += found
            offsets += piece.offsets
            lengths.append(len(found))
            owners.append(owner)
    return np.array(ids, dtype=np.int32), np.array(offsets, dtype=np.int32).reshape(-1, 2), np.array(lengths, dtype=np.int32), np.array(owners, dtype=np.int32)


def batches(lengths):
    order = np.argsort(lengths, kind="stable")
    start = 0
    while start < len(order):
        peak = np.maximum.accumulate(lengths[order[start:start + BATCH_TOKENS]])
        size = int(np.searchsorted(peak * np.arange(1, len(peak) + 1) > BATCH_TOKENS, True))
        size = max(size, 1)
        yield order[start:start + size]
        start += size


@torch.inference_mode()
def predict(model, pad, ids, offsets, lengths, owners, texts):
    begins = np.cumsum(lengths) - lengths
    found = defaultdict(dict)
    for chosen in batches(lengths):
        width = int(lengths[chosen].max())
        mask = np.arange(width) < lengths[chosen, None]
        places = begins[chosen, None] + np.arange(width)
        hidden, scores = model(torch.from_numpy(np.where(mask, ids[np.where(mask, places, 0)], pad).astype(np.int64)).to(DEVICE, non_blocking=True), pad)
        probabilities = scores.sigmoid()
        top = probabilities.max(1).values
        rows, columns = torch.nonzero(top > FLOOR, as_tuple=True)
        for column in columns.unique().tolist():
            here = rows[columns == column]
            part = probabilities[here, :, column]
            weight = ((part > SPAN_CUT) | (part >= top[here, column][:, None])).to(hidden.dtype)
            sure, picks = model.values[column]((hidden[here] * weight[..., None]).sum(1) / weight.sum(1, keepdim=True)).softmax(-1).max(-1)
            flags = weight.float().cpu().numpy()
            attribute = model.attributes[column]
            for line, (row, pick, score, belief) in enumerate(zip(here.tolist(), picks.tolist(), top[here, column].float().tolist(), sure.float().tolist())):
                window = chosen[row]
                positions = np.flatnonzero(flags[line])
                low, high = int(offsets[begins[window] + positions[0], 0]), int(offsets[begins[window] + positions[-1], 1])
                owner = int(owners[window])
                value = model.catalog[attribute][pick]
                if value == OTHER:
                    continue
                if attribute in READERS and (read := READERS[attribute](texts[owner][low:high])) is not None:
                    value = read
                else:
                    score *= belief
                    if score < FLOOR:
                        continue
                value = shown(attribute, value)
                if score > found[owner].get((attribute, value), (0.,))[0]:
                    found[owner][attribute, value] = (score, low, high)
    return found


def load_extractor(path=EXTRACTOR):
    saved = torch.load(path, map_location="cpu", weights_only=False)
    model = Extractor(saved["catalog"], saved["encoder"])
    model.load_state_dict(saved["state"])
    return model.to(DEVICE).half().eval(), AutoTokenizer.from_pretrained(saved["encoder"]).pad_token_id


def build_catalog(rows):
    counts = defaultdict(Counter)
    for _, _, found in rows:
        for (attribute, value) in found:
            counts[attribute][bucket(attribute, value)] += 1
    catalog = {attribute: [value for value, count in counted.most_common(LIMITS.get(attribute, 300)) if count >= (2 if attribute in FREE else 1)] for attribute, counted in counts.items()}
    return {attribute: values + [OTHER] if attribute in LIMITS else values for attribute, values in catalog.items() if values}


def label_spans(text, found, position, index, offsets):
    lowered, entries = text.lower(), []
    for (attribute, value), quote in found.items():
        name = bucket(attribute, value)
        if attribute not in position:
            continue
        if name not in index[attribute]:
            if OTHER not in index[attribute]:
                continue
            name = OTHER
        start = lowered.find(quote.lower())
        if start < 0:
            continue
        end = start + len(quote)
        if attribute == "age":
            inner = re.search(rf"(?<!\d){re.escape(name)}(?!\d)", lowered[start:end])
            if inner:
                start, end = start + inner.start(), start + inner.end()
        elif attribute in TIGHT:
            inner = DIGIT.search(lowered[start:end])
            if inner:
                start += inner.start()
        marks = [number for number, (low, high) in enumerate(offsets) if high > low and low < end and high > start]
        if marks:
            entries.append((position[attribute], index[attribute][name], marks))
    return entries


def value_loss(model, hidden, y, pairs):
    if not pairs:
        return hidden.sum() * 0
    groups = defaultdict(list)
    for row, column, value in pairs:
        groups[column].append((row, value))
    total = 0
    for column, items in groups.items():
        rows = torch.as_tensor([row for row, _ in items], device=DEVICE)
        targets = torch.as_tensor([value for _, value in items], device=DEVICE)
        weight = y[rows, :, column]
        pooled = (hidden[rows] * weight[..., None]).sum(1) / weight.sum(1, keepdim=True).clamp_min(1)
        total = total + F.cross_entropy(model.values[column](pooled), targets, reduction="sum")
    return total / len(pairs)


@timed
def fit(encoder=ENCODER, out=EXTRACTOR, epochs=EPOCHS):
    torch.manual_seed(SEED)
    rows = list(facts())
    catalog = build_catalog(rows)
    attributes = list(catalog)
    position = {attribute: column for column, attribute in enumerate(attributes)}
    index = {attribute: {value: item for item, value in enumerate(values)} for attribute, values in catalog.items()}
    pad = AutoTokenizer.from_pretrained(encoder).pad_token_id
    tokenizer = splitter(encoder)
    tokens, spans = [], []
    for start in range(0, len(rows), ENCODE_CHUNK):
        chunk = rows[start:start + ENCODE_CHUNK]
        for row, encoding in zip(chunk, tokenizer.encode_batch([row[1] for row in chunk])):
            tokens.append(np.array(encoding.ids, dtype=np.int32))
            spans.append(label_spans(row[1], row[2], position, index, encoding.offsets))
    lengths = np.fromiter(map(len, tokens), dtype=np.int32, count=len(tokens))
    LOG.info("extractor texts=%d positive=%d attributes=%d mean_tokens=%.1f", len(rows), sum(map(bool, spans)), len(attributes), lengths.mean())
    del rows
    model = Extractor(catalog, encoder).to(DEVICE)

    def batch_of(chosen):
        x = padded([tokens[item] for item in chosen], pad)
        y = torch.zeros((*x.shape, len(attributes)), dtype=torch.float32)
        pairs = []
        for row, item in enumerate(chosen):
            for column, value, marks in spans[item]:
                y[row, marks, column] = 1
                pairs.append((row, column, value))
        return x.to(DEVICE), y.to(DEVICE), pairs

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=.01)
    steps = epochs * (len(tokens) // BATCH_TEXTS)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=LEARNING_RATE, total_steps=steps, pct_start=.1)
    rng = np.random.default_rng(SEED)
    positive = torch.tensor(8., device=DEVICE)
    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(tokens))
        begun, running, step = time.perf_counter(), 0., 0
        for block in range(0, len(order), BATCH_TEXTS * 50):
            chunk = order[block:block + BATCH_TEXTS * 50]
            chunk = chunk[np.argsort(lengths[chunk])]
            batches = [chunk[start:start + BATCH_TEXTS] for start in range(0, len(chunk) - BATCH_TEXTS + 1, BATCH_TEXTS)]
            rng.shuffle(batches)
            for chosen in batches:
                x, y, pairs = batch_of(chosen)
                with torch.autocast(DEVICE, dtype=torch.bfloat16):
                    hidden, scores = model(x, pad)
                    mask = (x != pad)[..., None]
                    tag = (F.binary_cross_entropy_with_logits(scores, y, reduction="none", pos_weight=positive) * mask).sum() / mask.sum()
                    loss = tag * 2 + value_loss(model, hidden, y, pairs)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                optimizer.step()
                if schedule.last_epoch < steps - 1:
                    schedule.step()
                optimizer.zero_grad(set_to_none=True)
                running, step = running + loss.item(), step + 1
                if step % 500 == 0:
                    LOG.info("extractor epoch=%d step=%d loss=%.4f texts_per_second=%.0f", epoch, step, running / 500, step * BATCH_TEXTS / (time.perf_counter() - begun))
                    running = 0.
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state": model.state_dict(), "catalog": catalog, "encoder": encoder}, out)
    LOG.info("extractor saved path=%s", out)
