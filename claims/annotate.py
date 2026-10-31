import json
import subprocess
import sys
from collections import Counter

from . import LOG, timed
from .config import ANNOTATIONS, ANNOTATOR, GOLD_TEXTS, TEACHER, TRAINING, VERIFIERS
from .schema import CLOSED, VERIFY, claim_text, parse

BEFORE, AFTER = 500, 300
STOP = {"after": 2000, "max_error": .01, "max_shared_mib": 512}


def rows(path):
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def texts(dataset):
    return {row["id"]: row for row in rows(ANNOTATIONS / f"{dataset}.jsonl")}


def answers(dataset, model):
    found = {}
    for path in sorted((ANNOTATIONS / "runs" / dataset / model).glob("[0-9]*.jsonl")):
        for row in rows(path):
            if row["error"] is None:
                found[row["id"]] = row["answer"]
    return found


@timed
def generate(model, records, dataset, tokens, retries=8):
    out = ANNOTATIONS / "runs" / dataset / model
    out.mkdir(parents=True, exist_ok=True)
    prompt, stop = out.parent / f"{model}.prompt.json", out.parent / f"{model}.stop.json"
    prompt.write_text(json.dumps({"name": dataset, "template": "{text}", "max_tokens": tokens}), encoding="utf-8")
    stop.write_text(json.dumps(STOP), encoding="utf-8")
    for attempt in range(retries):
        code = subprocess.run([sys.executable, "-m", "local_annotator.generate", model, str(prompt), str(records), str(out), "--stop", str(stop), "--max-model-len", "8192", "--workers", "128", "--seqs", "256"], cwd=ANNOTATOR).returncode
        LOG.info("generate model=%s dataset=%s attempt=%d code=%d", model, dataset, attempt, code)
        if code == 0:
            return
    raise RuntimeError(f"generate {model} {dataset} failed after {retries} attempts")


@timed
def extract(dataset, model=TEACHER):
    records = ANNOTATIONS / f"{dataset}.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as out:
        for row in rows(ANNOTATIONS / f"{dataset}.jsonl"):
            out.write(json.dumps({"id": row["id"], "text": CLOSED.format(text=row["text"])}, ensure_ascii=False) + "\n")
    generate(model, records, dataset, 200)


def proposals(datasets, model=TEACHER):
    held = set(json.loads(GOLD_TEXTS.read_text(encoding="utf-8")))
    seen = set()
    for dataset in datasets:
        found = answers(dataset, model)
        for row in rows(ANNOTATIONS / f"{dataset}.jsonl"):
            identifier = row["id"]
            if identifier in found and identifier not in seen and identifier not in held:
                seen.add(identifier)
                yield identifier, row["text"], parse(found[identifier], row["text"])


def fact_key(identifier, attribute, value):
    return f"{identifier}|{attribute}|{value}"


@timed
def verify(datasets=TRAINING, model=TEACHER):
    records = ANNOTATIONS / "verify.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as out:
        for identifier, text, found in proposals(datasets, model):
            for (attribute, value), quote in found.items():
                out.write(json.dumps({"id": fact_key(identifier, attribute, value), "text": VERIFY.format(claim=claim_text(attribute, value), quote=quote, text=excerpt(text, quote))}, ensure_ascii=False) + "\n")
    generate(model, records, "verify", 4)


def facts(datasets=TRAINING, model=TEACHER):
    checked = answers("verify", model)
    total = kept = 0
    for identifier, text, found in proposals(datasets, model):
        confirmed = {pair: quote for pair, quote in found.items() if (checked.get(fact_key(identifier, *pair)) or "").strip().upper().startswith("Y")}
        total, kept = total + len(found), kept + len(confirmed)
        yield identifier, text, confirmed
    LOG.info("teacher facts proposed=%d confirmed=%d", total, kept)


def excerpt(text, quote):
    if len(text) <= BEFORE + AFTER + 200:
        return text
    start = max(text.lower().find(quote.lower()), 0)
    low, high = max(0, start - BEFORE), min(len(text), start + len(quote) + AFTER)
    return ("..." if low else "") + text[low:high] + ("..." if high < len(text) else "")


@timed
def gold(dataset, limit):
    corpus = texts(dataset)
    runs = {model: answers(dataset, model) for model in VERIFIERS}
    shared = sorted(set.intersection(*map(set, runs.values())))[:limit]
    proposals = {}
    for model, found in runs.items():
        for identifier in shared:
            for (attribute, value), quote in parse(found[identifier], corpus[identifier]["text"]).items():
                entry = proposals.setdefault(f"{identifier}|{attribute}|{value}", {"text_id": identifier, "attribute": attribute, "value": value, "quote": quote, "models": []})
                entry["models"].append(model)
    records = ANNOTATIONS / f"{dataset}.gold.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as prompts, open(ANNOTATIONS / f"{dataset}.gold.jsonl", "w", encoding="utf-8") as items:
        for key, entry in proposals.items():
            prompt = VERIFY.format(claim=claim_text(entry["attribute"], entry["value"]), quote=entry["quote"], text=excerpt(corpus[entry["text_id"]]["text"], entry["quote"]))
            prompts.write(json.dumps({"id": key, "text": prompt}, ensure_ascii=False) + "\n")
            items.write(json.dumps({"id": key, **entry}, ensure_ascii=False) + "\n")
    GOLD_TEXTS.write_text(json.dumps(shared), encoding="utf-8")
    LOG.info("gold texts=%d proposals=%d by_models=%s", len(shared), len(proposals), Counter(len(entry["models"]) for entry in proposals.values()).most_common())
    for model in VERIFIERS:
        generate(model, records, f"{dataset}.gold", 4)
