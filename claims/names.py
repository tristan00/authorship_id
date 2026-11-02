import json
import unicodedata
from collections import Counter, defaultdict

import psycopg

from database import DSN, vacuum

from . import LOG, timed
from .annotate import answers, generate, next_round, votes
from .config import ANNOTATIONS, NAME_CHECKED, NAME_MENTIONS, NAMES_FILE, TEACHER, TRAINING, VERIFIERS
from .schema import CLUB, KINDS, LETTERS, NAME_CHECK, NAME_GENERIC, NAME_PROMPT, NAME_SAME, SQUEEZE, STORED_KINDS, spelled

RUN = "names"
SAME = "names.same"
CHECK = "names.check"
GENERIC = "names.generic"
SINGLE_NAMED = "fictional character"
CLOSED = frozenset({"country", "state or region", "city"})
LONGEST = 60
SHORTEST = 2
READ = "SELECT field, value, count(*) FROM text_claims WHERE field = ANY(%s::claim_field[]) GROUP BY 1, 2 HAVING count(*) >= %s"
CHANGES = "CREATE TEMP TABLE name_changes (field claim_field NOT NULL, raw text NOT NULL, target text) ON COMMIT DROP"
RENAME = "UPDATE {table} c SET value = n.target FROM name_changes n WHERE n.target IS NOT NULL AND c.field = n.field AND c.value = n.raw"
REMOVE = "DELETE FROM {table} c USING name_changes n WHERE n.target IS NULL AND c.field = n.field AND c.value = n.raw"
STORED = ("text_claims", "flair_claims")


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
def collected(extra):
    counts = defaultdict(Counter)
    for found in (votes("fandom", TEACHER), *(answers(dataset, TEACHER) for dataset in TRAINING), *(answers(dataset, model) for model in VERIFIERS for dataset in ("uniform", "fandom.gold", "flairs"))):
        for answer in found.values():
            for kind, value in mentions(answer):
                counts[kind][value] += 1
    for kind, values in extra.items():
        counts[kind].update(values)
    LOG.info("names distinct=%s", {kind: len(values) for kind, values in counts.items()})
    return counts


@timed
def extracted():
    counts = defaultdict(Counter)
    with psycopg.connect(DSN) as conn:
        for field, value, amount in conn.execute(READ, [list(STORED_KINDS), NAME_MENTIONS]):
            counts[STORED_KINDS[field]][value] += amount
    return counts


def reading(kind, answer):
    text = (answer or "").strip().splitlines()[0] if (answer or "").strip() else ""
    text = text.rpartition("=")[2].strip().strip("*_`\"'.").lower().removeprefix("the ")
    if kind == "sports team":
        text = CLUB.sub("", text)
    if text == "none":
        return text
    return text if text and not text.endswith(": none") and LETTERS.search(text) and len(text) <= LONGEST else None


def agreed(key, tables, wanted):
    lead, *rest = ((table.get(key) or "").strip()[:1].upper() for table in tables)
    return lead in wanted and any(item in wanted for item in rest)


def proposal(name, ballot):
    lead, one, two = ballot
    if one and two and one != "none" and folded(one) == folded(two) and folded(one) != folded(name):
        return one
    return lead if lead and lead != "none" and folded(lead) != folded(name) else None


def settled(ballot):
    lead, *rest = ballot
    return bool(lead) and any(item and folded(item) == folded(lead) for item in rest)


def ballot_of(kind, name, tables):
    return [reading(kind, table.get(f"{kind}|{name}")) for table in tables]


def judged(kind, name, ballot, same):
    lead, *rest = ballot
    if lead == "none" and sum(item == "none" for item in rest) >= (1 if kind in CLOSED else len(rest)):
        return None
    target = proposal(name, ballot)
    if target is None:
        return name
    if target == lead and settled(ballot):
        return target
    return target if agreed(f"{kind}|{name}|{target}", same, ("Y",)) else name


def resolved(kind, values, tables, same):
    picked = {name: judged(kind, name, ballot_of(kind, name, tables), same) for name in values}
    final = {}
    for name in values:
        current, steps = picked[name], 0
        while current is not None and current != picked.get(current, current) and steps < 5:
            current, steps = picked[current], steps + 1
        final[name] = current if current is not None and len(folded(current)) >= SHORTEST else None
    mass = Counter()
    for name, target in final.items():
        if target is not None:
            mass[target] += values[name] + 1
    spelling = {}
    for target, _ in mass.most_common():
        spelling.setdefault(folded(target), target)
    total = Counter()
    for target, amount in mass.items():
        total[spelling[folded(target)]] += amount
    return {name: target and spelling[folded(target)] for name, target in final.items()}, total


def asked(run, items, tokens):
    known = votes(run, TEACHER)
    fresh = [(key, text) for key, text in items if key not in known]
    LOG.info("names run=%s new=%d", run, len(fresh))
    if fresh:
        name = next_round(run, TEACHER)
        records = ANNOTATIONS / f"{name}.prompts.jsonl"
        with open(records, "w", encoding="utf-8") as out:
            for key, text in fresh:
                out.write(json.dumps({"id": key, "text": text}, ensure_ascii=False) + "\n")
        for model in VERIFIERS:
            generate(model, records, name, tokens)
    return [votes(run, model) for model in VERIFIERS]


def questions(counts, tables):
    for kind, values in counts.items():
        for name in values:
            ballot = ballot_of(kind, name, tables)
            target = proposal(name, ballot)
            if target is not None and not (target == ballot[0] and settled(ballot)):
                yield f"{kind}|{name}|{target}", NAME_SAME.format(kind=kind, name=name, target=target)


def checked(final):
    for kind, (_, total) in final.items():
        if kind not in CLOSED:
            for target, amount in total.items():
                if amount >= NAME_CHECKED:
                    yield f"{kind}|{target}", NAME_CHECK.format(kind=kind, name=target)


def generic(final, checks):
    for target in set(final[SINGLE_NAMED][0].values()) - {None}:
        key = f"{SINGLE_NAMED}|{target}"
        if agreed(key, checks, ("B", "C")):
            yield key, NAME_GENERIC.format(name=target)


def rejected(kind, target, checks, generics):
    key = f"{kind}|{target}"
    if kind == SINGLE_NAMED:
        return agreed(key, checks, ("C",)) or agreed(key, generics, ("B",))
    return agreed(key, checks, ("B", "C"))


@timed
def annotate(extra):
    counts = collected(extra)
    tables = asked(RUN, ((f"{kind}|{value}", NAME_PROMPT.format(kind=kind, name=value)) for kind, values in counts.items() for value in values), 24)
    kinds = set(KINDS.values())
    for key in tables[0]:
        kind, _, value = key.partition("|")
        if kind in kinds:
            counts[kind][value] += 0
    same = asked(SAME, questions(counts, tables), 4)
    final = {kind: resolved(kind, values, tables, same) for kind, values in counts.items()}
    checks = asked(CHECK, checked(final), 4)
    generics = asked(GENERIC, generic(final, checks), 4)
    table = {}
    for kind, (chosen, _) in final.items():
        dropped = {target for target in set(chosen.values()) - {None} if rejected(kind, target, checks, generics)}
        table[kind] = {name: None if target is None or target in dropped else target for name, target in chosen.items() if target is None or target in dropped or target != name}
        LOG.info("names kind=%s names=%d rejected=%d", kind, len(chosen), len(dropped))
    NAMES_FILE.write_text(json.dumps(table, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    LOG.info("names table=%s", {kind: len(entries) for kind, entries in table.items()})


@timed
def apply():
    table = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    with psycopg.connect(DSN) as conn:
        conn.execute("SET LOCAL work_mem = '2GB'")
        conn.execute(CHANGES)
        with conn.cursor().copy("COPY name_changes FROM STDIN") as copy:
            for field, kind in STORED_KINDS.items():
                for raw, target in table.get(kind, {}).items():
                    copy.write_row((field, raw, target))
        conn.execute("ANALYZE name_changes")
        for name in STORED:
            renamed = conn.execute(RENAME.format(table=name)).rowcount
            removed = conn.execute(REMOVE.format(table=name)).rowcount
            LOG.info("names applied table=%s renamed=%d removed=%d", name, renamed, removed)
    vacuum(*STORED)
