import json
import random
import zlib
from collections import Counter, defaultdict

import psycopg

from database import DSN

from . import LOG, timed
from .annotate import generate, next_round, rounds, rows, texts, votes
from .config import ANNOTATIONS, EXTRACTOR, GOLD_AUTHORS, GOLD_BUCKET, GOLD_PER_ATTRIBUTE, GOLD_TEXTS, HELD_FOLDS, NEEDS, PLACE_CHAINS, TEACHER, THRESHOLDS, VERIFIERS
from .extractor import load_extractor, predict, splitter, windows
from .rules import CHAINED, agree, chain, decide, flair_strength, needs, place_paths, strength
from .sample import MINOR, safety
from .schema import ALL_FIELDS, BOT, canonical, renamed

CUTS = (.2, .5, .8, .9, .95)
LETTERS = "ABCDEFGH"
BEFORE, AFTER = 170, 120
DESCRIPTIONS = {"age": "their age now", "height": "their height in centimeters", "weight": "their body weight now in kilograms", "income": "their yearly income in US dollars", "nationality": "the country they are a citizen or national of",
                "residence_country": "the country they live in now", "residence_region": "the state or region they live in now", "residence_city": "the city or town they live in now", "origin_country": "the country they were born or raised in",
                "origin_region": "the state or region they were born or raised in", "origin_city": "the city or town they were born or raised in", "native_language": "their first language", "gender": "their gender", "sexual_orientation": "their sexual orientation",
                "ethnicity": "their race or ethnicity", "religion": "their religion or belief", "political_identity": "their political identity", "relationship_status": "their relationship status now", "parental_status": "whether they have children",
                "education": "their education, highest reached or current level", "field_of_study": "the subject they study or studied", "employment_status": "their main activity now", "occupation": "the field of their current job", "body_type": "their body type",
                "hair_color": "their hair color", "physical_condition": "a physical condition they have now", "mental_condition": "a mental condition they have now", "neurotype": "a neurodevelopmental condition they have", "diet": "their diet", "smoking": "whether they smoke",
                "living_with": "who they live with", "housing": "their housing", "pets": "their pets", "military_status": "their military status", "political_compass": "their position on the political compass",
                "personality_type": "their personality type", "generation": "the generation they belong to", "fan_sports_team": "the sports team they support", "fan_athlete": "the athlete they are most a fan of", "fan_artist": "the musician, band or artist they are most a fan of",
                "fan_author": "the book author they are most a fan of", "fan_character": "the fictional character they are most a fan of", "fan_franchise": "the show, film series, anime, comic or book series they are most a fan of",
                "fan_video_game": "the video game they are most a fan of", "fan_creator": "the streamer or online creator they are most a fan of", "fan_celebrity": "the famous person they are most a fan of"}
AUTHOR_PROMPT = """Below are excerpts written by one Reddit author in different posts and comments. An automatic system read them and found possible values for one thing about this author. Words between [[ and ]] are what the system used, and the system is often wrong. A flair is a label the author chose to show next to their name.

Decide which option is true of the author now, using only these excerpts. Tags such as 28F or [M4F] at the start of the author's own post describe the author. Something said about another person, a question, a hypothetical, a joke, role-play, a quotation, or a past fact that no longer holds does not count. If the author's situation changed, use the most recent sincere statement. If an excerpt looks like the author but gives a value that conflicts with most of the others, weigh how clear each statement is.

About the author: {description}

{options}
Z: None of these is shown to be true of the author.

Answer with exactly one letter."""
EVIDENCE = """SELECT author, source, source_key, subreddit, field, value, probability, text_sha256 FROM claim_evidence
              WHERE abs(hashtext(author)) %% %(parts)s = %(part)s AND field <> %(bot)s"""


def first_letter(answer, allowed):
    return next((char for char in (answer or "").strip().upper() if char in allowed), None)


def text_truth(dataset):
    ballots_of = {model: votes(f"{dataset}.gold", model) for model in VERIFIERS}
    truth, teacher = defaultdict(set), defaultdict(set)
    for item in rows(ANNOTATIONS / f"{dataset}.gold.jsonl"):
        pair = canonical(item["attribute"], item["value"])
        if pair is None:
            continue
        attribute, value = pair
        value = renamed(attribute, value)
        if value is None:
            continue
        ballots = [first_letter(ballots_of[model].get(item["id"]), "YN") for model in VERIFIERS]
        if TEACHER in item["models"]:
            teacher[item["text_id"], attribute].add(str(value))
        if ballots[0] == "Y" and "Y" in ballots[1:]:
            truth[item["text_id"], attribute].add(value)
    return truth, teacher


def equal(attribute, left, right):
    try:
        return agree(attribute, left, right)
    except ValueError:
        return False


@timed
def extractor(dataset="uniform", path=EXTRACTOR):
    truth, teacher = text_truth(dataset)
    wanted = Counter(attribute for (_, attribute), values in truth.items() for _ in values)
    corpus = texts(dataset)
    held = [identifier for identifier in json.loads(GOLD_TEXTS.read_text(encoding="utf-8")) if identifier in corpus]
    body = [corpus[identifier]["text"] for identifier in held]
    model, pad = load_extractor(path)
    found = predict(model, pad, *windows(splitter(model.encoder.config.name_or_path), body), body)
    results = {}
    for cut in CUTS:
        hits, picked = Counter(), Counter()
        for owner, facts in found.items():
            for (attribute, value), (score, _, _) in facts.items():
                if score >= cut:
                    picked[attribute] += 1
                    hits[attribute] += any(equal(attribute, value, known) for known in truth.get((held[owner], attribute), ()))
        total_hit, total_picked, total_wanted = sum(hits.values()), sum(picked.values()), sum(wanted.values())
        per = {name: 2 * hits[name] / max(picked[name] + wanted[name], 1) for name in wanted}
        results[cut] = {"precision": round(total_hit / max(total_picked, 1), 4), "recall": round(total_hit / max(total_wanted, 1), 4), "f1": round(2 * total_hit / max(total_picked + total_wanted, 1), 4), "macro_f1": round(sum(per.values()) / len(per), 4),
                        "fields": {name: round(value, 3) for name, value in sorted(per.items(), key=lambda item: -wanted[item[0]])}}
        LOG.info("extractor vs annotators cut=%s %s", cut, json.dumps(results[cut]))
    hits, picked = Counter(), Counter()
    for key, values in teacher.items():
        for value in values:
            picked[key[1]] += 1
            hits[key[1]] += any(equal(key[1], value, known) for known in truth.get(key, ()))
    mine, hit = sum(picked.values()), sum(hits.values())
    per = {name: 2 * hits[name] / max(picked[name] + wanted[name], 1) for name in wanted}
    results["teacher"] = {"precision": round(hit / max(mine, 1), 4), "recall": round(hit / max(sum(wanted.values()), 1), 4), "f1": round(2 * hit / max(mine + sum(wanted.values()), 1), 4), "macro_f1": round(sum(per.values()) / len(per), 4),
                          "fields": {name: round(value, 3) for name, value in sorted(per.items(), key=lambda item: -wanted[item[0]])}}
    LOG.info("teacher vs annotators %s", json.dumps(results["teacher"]))
    return results


def excerpt(text, low, high):
    begin, end = max(0, low - BEFORE), min(len(text), high + AFTER)
    return " ".join((("..." if begin else "") + text[begin:low] + "[[" + text[low:high] + "]]" + text[high:end] + ("..." if end < len(text) else "")).split())


def cohort_evidence():
    table = defaultdict(lambda: defaultdict(list))
    with psycopg.connect(DSN) as conn:
        for author, source, key, subreddit, field, value, probability, digest in conn.execute(EVIDENCE, {"parts": GOLD_AUTHORS, "part": GOLD_BUCKET, "bot": BOT}):
            table[author][field].append({"source": source, "key": key, "subreddit": subreddit, "value": value, "probability": probability, "digest": digest and bytes(digest)})
    return table


def expanded(fields):
    found = defaultdict(list)
    for field, entries in fields.items():
        if field not in CHAINED:
            found[field] += [{**entry, "field": field, "origin": entry["value"], "weight": 1.} for entry in entries]
    for places in PLACE_CHAINS:
        for depth, field in enumerate(places):
            for entry in fields.get(field, ()):
                for weight, path in place_paths(depth, entry["value"]):
                    for upper, target in enumerate(places):
                        if path[upper] is not None:
                            found[target].append({**entry, "field": field, "origin": entry["value"], "value": path[upper], "weight": weight})
    return found


@timed
def author_gold():
    table = {author: expanded(fields) for author, fields in cohort_evidence().items()}
    judged = {f"{row['author']}|{row['attribute']}" for row in rows(ANNOTATIONS / "author_gold.jsonl")}
    pools = defaultdict(lambda: ([], []))
    for author in sorted(table):
        for field, entries in table[author].items():
            if f"{author}|{field}" not in judged:
                pools[field][len({entry["value"] for entry in entries}) > 1].append(author)
    rng, picked = random.Random(5 + len(rounds("author_gold"))), []
    for field, (plain, conflicted) in sorted(pools.items()):
        rng.shuffle(plain)
        rng.shuffle(conflicted)
        taken = conflicted[:GOLD_PER_ATTRIBUTE // 2]
        picked += [(author, field) for author in taken + plain[:GOLD_PER_ATTRIBUTE - len(taken)]]
    shown, digests = {}, set()
    for author, field in picked:
        grouped = defaultdict(list)
        for entry in table[author][field]:
            grouped[entry["value"]].append(entry)
        ranked = sorted(grouped, key=lambda value: -sum(entry["weight"] * entry["probability"] for entry in grouped[value]))[:6]
        shown[author, field] = {value: sorted(grouped[value], key=lambda entry: -entry["weight"] * entry["probability"])[:3] for value in ranked}
        digests |= {entry["digest"] for value in ranked for entry in shown[author, field][value] if entry["digest"]}
    with psycopg.connect(DSN) as conn:
        bodies = dict(conn.execute("SELECT text_sha256, text FROM bodies WHERE text_sha256 = ANY(%s)", [list(digests)]).fetchall())
        spans = {(bytes(digest), field, value): (low, high) for digest, field, value, low, high in conn.execute("SELECT text_sha256, field, value, start_char, end_char FROM text_claims WHERE text_sha256 = ANY(%s)", [list(digests)])}
    bodies = {bytes(digest): text for digest, text in bodies.items()}
    adult, minors = safety()
    written = blocked = 0
    records = ANNOTATIONS / "author_gold.prompts.jsonl"
    with open(records, "w", encoding="utf-8") as prompts, open(ANNOTATIONS / "author_gold.jsonl", "a", encoding="utf-8") as items:
        for author, field in picked:
            options, risky, values = [], False, list(shown[author, field])
            for letter, value in zip(LETTERS, values):
                lines = []
                for entry in shown[author, field][value]:
                    if entry["source"] == "flair":
                        lines.append(f"  - flair in r/{entry['subreddit']}: {entry['key'].partition('/')[2]}")
                        continue
                    text = bodies[entry["digest"]]
                    if entry["subreddit"] in adult and (author in minors or MINOR.search(text) or (field == "age" and float(value) < 18)):
                        risky = True
                    low, high = spans[entry["digest"], entry["field"], entry["origin"]]
                    lines.append(f"  - r/{entry['subreddit']}: {excerpt(text, low, high)}")
                options.append(f"{letter}: {value}\n" + "\n".join(lines))
            if risky:
                blocked += 1
                continue
            key = f"{author}|{field}"
            prompts.write(json.dumps({"id": key, "text": AUTHOR_PROMPT.format(description=DESCRIPTIONS[field], options="\n".join(options))}, ensure_ascii=False) + "\n")
            items.write(json.dumps({"id": key, "author": author, "attribute": field, "values": values}, ensure_ascii=False) + "\n")
            written += 1
    LOG.info("author gold items=%d blocked=%d", written, blocked)
    run = next_round("author_gold", TEACHER)
    for model in VERIFIERS:
        generate(model, records, run, 4)


def gold_choice(answer, values):
    letter = first_letter(answer, LETTERS + "Z")
    if letter is None:
        return None
    if letter == "Z":
        return "none"
    return values[LETTERS.index(letter)] if LETTERS.index(letter) < len(values) else None


def author_truth():
    ballots = {model: votes("author_gold", model) for model in VERIFIERS}
    truth = {}
    for item in rows(ANNOTATIONS / "author_gold.jsonl"):
        picks = [gold_choice(ballots[model].get(item["id"]), item["values"]) for model in VERIFIERS]
        if picks[0] is not None and picks[0] in picks[1:]:
            truth[item["author"], item["attribute"]] = picks[0]
    return truth


def score_add(count, chosen, label, attribute, amount):
    if chosen is None:
        if label != "none":
            count["silent"] += amount
    elif label != "none" and agree(attribute, chosen, label):
        count["hit"] += amount
    else:
        count["wrong"] += amount


def f1(count):
    return 2 * count["hit"] / max(2 * count["hit"] + count["wrong"] + count["silent"], 1e-9)


def fitted(count):
    return 1.25 * count["hit"] / max(1.25 * count["hit"] + count["wrong"] + .25 * count["silent"], 1e-9)


def summary(count):
    return {"precision": round(count["hit"] / max(count["hit"] + count["wrong"], 1e-9), 3), "recall": round(count["hit"] / max(count["hit"] + count["silent"], 1e-9), 3), "f1": round(f1(count), 3)}


def mention_amounts(entries, need):
    return [(entry["value"], flair_strength(need) if entry["source"] == "flair" else strength(entry["probability"])) for entry in entries]


def outcome(fields, attribute, required):
    if attribute not in CHAINED:
        return decide(attribute, mention_amounts(fields.get(attribute, ()), required[attribute]), required[attribute])
    places = next(places for places in PLACE_CHAINS if attribute in places)
    return chain(places, {field: mention_amounts(fields.get(field, ()), required[field]) for field in places}, required).get(attribute)


def score_need(members, attribute, need, base):
    count = Counter()
    required = {**base, attribute: need}
    for label, amount, fields in members:
        found = outcome(fields, attribute, required)
        score_add(count, found[0] if found else None, label, attribute, amount)
    return count


@timed
def thresholds():
    truth = author_truth()
    table = cohort_evidence()
    shown = {author: expanded(fields) for author, fields in table.items()}
    population = Counter((field, len({entry["value"] for entry in entries}) > 1) for fields in shown.values() for field, entries in fields.items())
    sampled = Counter((attribute, len({entry["value"] for entry in shown[author][attribute]}) > 1) for author, attribute in truth)
    members = defaultdict(list)
    folds = defaultdict(list)
    for (author, attribute), label in truth.items():
        stratum = attribute, len({entry["value"] for entry in shown[author][attribute]}) > 1
        members[attribute].append((label, population[stratum] / sampled[stratum], table[author]))
        folds[attribute].append(zlib.crc32(author.encode()) % HELD_FOLDS)
    chosen, held, report = {}, Counter(), {}
    macro = []
    base = needs()
    for attribute in (name for name in ALL_FIELDS if name in members):
        entries = members[attribute]
        total = Counter()
        for fold in range(HELD_FOLDS):
            train = [entry for entry, place in zip(entries, folds[attribute]) if place != fold]
            test = [entry for entry, place in zip(entries, folds[attribute]) if place == fold]
            total += score_need(test, attribute, max(NEEDS, key=lambda need: fitted(score_need(train, attribute, need, base))), base)
        held += total
        macro.append(f1(total))
        chosen[attribute] = max(NEEDS, key=lambda need: fitted(score_need(entries, attribute, need, base)))
        base[attribute] = chosen[attribute]
        report[attribute] = {"need": chosen[attribute], **summary(score_need(entries, attribute, chosen[attribute], base))}
    missing = sorted(set(ALL_FIELDS) - set(chosen))
    if missing:
        raise ValueError(f"No gold for {missing}")
    THRESHOLDS.write_text(json.dumps({name: chosen[name] for name in ALL_FIELDS}, indent=0) + "\n", encoding="utf-8")
    LOG.info("consolidation vs annotators held_out=%s macro_f1=%.3f gold=%d", summary(held), sum(macro) / len(macro), len(truth))
    for attribute, entry in report.items():
        LOG.info("consolidation %s %s", attribute, json.dumps(entry))
    return {"held_out": summary(held), "macro_f1": round(sum(macro) / len(macro), 3), "fields": report}
