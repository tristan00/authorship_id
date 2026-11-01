import json
import unicodedata
from collections import Counter, defaultdict

from . import LOG, timed
from .annotate import answers, generate, next_round, votes
from .config import ANNOTATIONS, NAMES_FILE, TEACHER, TRAINING, VERIFIERS
from .schema import CLUB, KINDS, LETTERS, NAME_PROMPT, SQUEEZE, spelled

RUN = "names"
CLOSED = frozenset({"country", "state or region", "city"})
LONGEST = 60


def folded(text):
    return SQUEEZE.sub("", "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)).lower())


def mentions(answer):
    for line in (answer or "").splitlines():
        parts = [part.strip() for part in (line.split("|") if "|" in line else line.split(":", 1))]
        if len(parts) >= 2:
            attribute = parts[0].strip("-*• ").lower()
            if attribute in KINDS and (value := spelled(attribute, parts[1])):
                yield KINDS[attribute], value


@timed
def collected():
    counts = defaultdict(Counter)
    sources = [(dataset, TEACHER) for dataset in (*TRAINING, "fandom")] + [(dataset, model) for model in VERIFIERS for dataset in ("uniform", "fandom.gold", "flairs")]
    for dataset, model in dict.fromkeys(sources):
        for answer in answers(dataset, model).values():
            for kind, value in mentions(answer):
                counts[kind][value] += 1
    LOG.info("names distinct=%s", {kind: len(values) for kind, values in counts.items()})
    return counts


def reading(kind, answer):
    text = (answer or "").strip().splitlines()[0] if (answer or "").strip() else ""
    text = text.rpartition("=")[2].strip().strip("*_`\"'.").lower().removeprefix("the ")
    if kind == "sports team":
        text = CLUB.sub("", text)
    if text == "none":
        return text
    return text if text and LETTERS.search(text) and len(text) <= LONGEST else None


def judged(kind, name, tables):
    lead, *rest = (reading(kind, table.get(f"{kind}|{name}")) for table in tables)
    if lead is None or folded(lead) == folded(name):
        return name
    same = sum(1 for ballot in rest if ballot and folded(ballot) == folded(lead))
    if lead == "none":
        return None if same >= (1 if kind in CLOSED else len(rest)) else name
    return lead if same else name


def built(kind, values, tables):
    picked = {name: judged(kind, name, tables) for name in values}
    final = {}
    for name in values:
        current, steps = picked[name], 0
        while current is not None and current != picked.get(current, current) and steps < 5:
            current, steps = picked[current], steps + 1
        final[name] = current
    mass = Counter()
    for name, target in final.items():
        if target is not None:
            mass[target] += values[name] + 1
    spelling = {}
    for target, _ in mass.most_common():
        spelling.setdefault(folded(target), target)
    return {name: target and spelling[folded(target)] for name, target in final.items() if target is None or spelling[folded(target)] != name}


@timed
def annotate():
    counts = collected()
    known = votes(RUN, TEACHER)
    name = next_round(RUN, TEACHER)
    records = ANNOTATIONS / f"{name}.prompts.jsonl"
    written = 0
    with open(records, "w", encoding="utf-8") as out:
        for kind, values in counts.items():
            for value in values:
                if f"{kind}|{value}" not in known:
                    out.write(json.dumps({"id": f"{kind}|{value}", "text": NAME_PROMPT.format(kind=kind, name=value)}, ensure_ascii=False) + "\n")
                    written += 1
    LOG.info("names round=%s new=%d", name, written)
    if written:
        for model in VERIFIERS:
            generate(model, records, name, 24)
    tables = [votes(RUN, model) for model in VERIFIERS]
    table = {kind: built(kind, values, tables) for kind, values in counts.items()}
    NAMES_FILE.write_text(json.dumps(table, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    LOG.info("names table=%s", {kind: len(entries) for kind, entries in table.items()})
