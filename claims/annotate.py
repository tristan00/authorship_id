import json
import subprocess
import sys
from collections import Counter

from . import LOG, timed
from .config import ANNOTATIONS, ANNOTATOR, FAN_WHOLE, GOLD_TEXTS, TEACHER, TRAINING, VERIFIERS
from .schema import CLOSED, FAN_WORDS, FANDOM_PROMPT, VERIFY, claim_text, parse

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


def rounds(name):
    return sorted(path.name for path in (ANNOTATIONS / "runs").glob(f"{name}*") if path.name == name or path.name.removeprefix(f"{name}.").isdigit())


def votes(name, model):
    found = {}
    for run in rounds(name):
        found.update(answers(run, model))
    return found


def next_round(name, model):
    used = [run for run in rounds(name) if (ANNOTATIONS / "runs" / run / model / "manifest.json").exists()]
    return f"{name}.{len(used)}" if used else name


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


@timed
def fandom(datasets=TRAINING, model=TEACHER):
    seen = set(votes("fandom", model))
    known = len(seen)
    name = next_round("fandom", model)
    records = ANNOTATIONS / f"{name}.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as out:
        for dataset in datasets:
            for row in rows(ANNOTATIONS / f"{dataset}.jsonl"):
                if row["id"] not in seen and (dataset in FAN_WHOLE or FAN_WORDS.search(row["text"])):
                    seen.add(row["id"])
                    out.write(json.dumps({"id": row["id"], "text": FANDOM_PROMPT.format(text=row["text"])}, ensure_ascii=False) + "\n")
    LOG.info("fandom round=%s new texts=%d", name, len(seen) - known)
    generate(model, records, name, 120)


def fandom_checked(model=TEACHER):
    return frozenset(votes("fandom", model))


def proposals(datasets, model=TEACHER):
    held = set(json.loads(GOLD_TEXTS.read_text(encoding="utf-8")))
    fans = votes("fandom", model)
    seen = set()
    for dataset in datasets:
        found = answers(dataset, model)
        for row in rows(ANNOTATIONS / f"{dataset}.jsonl"):
            identifier = row["id"]
            if identifier in found and identifier not in seen and identifier not in held:
                seen.add(identifier)
                yield identifier, row["text"], {**parse(found[identifier], row["text"]), **parse(fans.get(identifier), row["text"])}


def fact_key(identifier, attribute, value):
    return f"{identifier}|{attribute}|{value}"


@timed
def verify(datasets=TRAINING, model=TEACHER):
    known = votes("verify", model)
    name = next_round("verify", model)
    records = ANNOTATIONS / f"{name}.prompts.jsonl"
    written = 0
    with open(records, "w", encoding="utf-8") as out:
        for identifier, text, found in proposals(datasets, model):
            for (attribute, value), quote in found.items():
                key = fact_key(identifier, attribute, value)
                if key not in known:
                    out.write(json.dumps({"id": key, "text": VERIFY.format(claim=claim_text(attribute, value), quote=quote, text=excerpt(text, quote))}, ensure_ascii=False) + "\n")
                    written += 1
    LOG.info("verify round=%s new facts=%d", name, written)
    generate(model, records, name, 4)


def facts(datasets=TRAINING, model=TEACHER):
    checked = votes("verify", model)
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
    records = ANNOTATIONS / "fandom.gold.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as out:
        for identifier in shared:
            out.write(json.dumps({"id": identifier, "text": FANDOM_PROMPT.format(text=corpus[identifier]["text"])}, ensure_ascii=False) + "\n")
    for model in VERIFIERS:
        generate(model, records, "fandom.gold", 120)
    fans = {model: answers("fandom.gold", model) for model in VERIFIERS}
    proposals = {}
    for model, found in runs.items():
        for identifier in shared:
            for (attribute, value), quote in {**parse(found[identifier], corpus[identifier]["text"]), **parse(fans[model].get(identifier), corpus[identifier]["text"])}.items():
                entry = proposals.setdefault(f"{identifier}|{attribute}|{value}", {"text_id": identifier, "attribute": attribute, "value": value, "quote": quote, "models": []})
                entry["models"].append(model)
    name = next_round(f"{dataset}.gold", VERIFIERS[0])
    known = votes(f"{dataset}.gold", VERIFIERS[0])
    records = ANNOTATIONS / f"{name}.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as prompts, open(ANNOTATIONS / f"{dataset}.gold.jsonl", "w", encoding="utf-8") as items:
        for key, entry in proposals.items():
            if key not in known:
                prompt = VERIFY.format(claim=claim_text(entry["attribute"], entry["value"]), quote=entry["quote"], text=excerpt(corpus[entry["text_id"]]["text"], entry["quote"]))
                prompts.write(json.dumps({"id": key, "text": prompt}, ensure_ascii=False) + "\n")
            items.write(json.dumps({"id": key, **entry}, ensure_ascii=False) + "\n")
    GOLD_TEXTS.write_text(json.dumps(shared), encoding="utf-8")
    LOG.info("gold round=%s texts=%d proposals=%d new=%d by_models=%s", name, len(shared), len(proposals), len(proposals) - sum(key in known for key in proposals), Counter(len(entry["models"]) for entry in proposals.values()).most_common())
    for model in VERIFIERS:
        generate(model, records, name, 4)
