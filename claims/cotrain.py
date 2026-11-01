import json

from . import LOG, timed
from .annotate import excerpt, fact_key, generate, next_round, proposals, votes
from .config import ANNOTATIONS, FLOOR, TEACHER, TRAINING
from .extractor import load_extractor, predict, splitter, windows
from .rules import agree
from .schema import BOT, NUMBERS, VERIFY, claim_text, renamed

CHUNK = 100_000


def written(digest_rows, found, known, prompts, items):
    count = 0
    for owner, entries in found.items():
        identifier, text, teacher = digest_rows[owner]
        for (attribute, value), (score, low, high) in entries.items():
            value = float(value) if attribute in NUMBERS else renamed(attribute, value)
            key = fact_key(identifier, attribute, value)
            if attribute == BOT or value is None or key in known or any(other == attribute and agree(attribute, held, value) for other, held in teacher):
                continue
            quote = text[low:high]
            prompts.write(json.dumps({"id": key, "text": VERIFY.format(claim=claim_text(attribute, value), quote=quote, text=excerpt(text, quote))}, ensure_ascii=False) + "\n")
            items.write(json.dumps({"key": key, "id": identifier, "attribute": attribute, "value": value, "quote": quote, "score": score}, ensure_ascii=False) + "\n")
            count += 1
    return count


@timed
def propose(datasets=TRAINING, minimum=FLOOR):
    model, pad = load_extractor()
    tokenizer = splitter(model.encoder.config.name_or_path)
    known = votes("cotrain", TEACHER)
    name = next_round("cotrain", TEACHER)
    records = ANNOTATIONS / f"{name}.prompts.jsonl"
    total = seen = 0
    with open(records, "w", encoding="utf-8") as prompts, open(ANNOTATIONS / "cotrain.jsonl", "a", encoding="utf-8") as items:
        chunk = []
        for row in proposals(datasets):
            chunk.append(row)
            if len(chunk) == CHUNK:
                body = [item[1] for item in chunk]
                total += written(chunk, predict(model, pad, *windows(tokenizer, body), body), known, prompts, items)
                seen += len(chunk)
                LOG.info("cotrain texts=%d new facts=%d", seen, total)
                chunk = []
        if chunk:
            body = [item[1] for item in chunk]
            total += written(chunk, predict(model, pad, *windows(tokenizer, body), body), known, prompts, items)
    LOG.info("cotrain round=%s facts=%d", name, total)
    del model
    generate(TEACHER, records, name, 4)
