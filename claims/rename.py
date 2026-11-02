import json
import time
from pathlib import Path

import psycopg
import torch
from psycopg import sql
from psycopg.types.json import Jsonb

from attribute_model.config import DATA, MODEL, TARGETS, TEXT_DATA, TEXT_MODEL, columns
from database import DSN

from . import LOG, timed
from .config import ANNOTATIONS, THRESHOLDS

MANIFEST_MAPS = ("targets", "catalogs", "target_counts", "excluded_out_of_range")


def renamed_keys(mapping, old, new):
    return {new if key == old else key: value for key, value in mapping.items()}


def rewrite_json(path, old, new):
    text = path.read_bytes().decode("utf-8")
    if text.count(f'"{old}":') != 1:
        raise ValueError(f"{path} does not hold {old} exactly once")
    path.write_bytes(text.replace(f'"{old}":', f'"{new}":').encode("utf-8"))


def rename_database(old, new):
    with psycopg.connect(DSN) as conn:
        conn.execute(sql.SQL("ALTER TYPE claim_field RENAME VALUE {} TO {}").format(sql.Literal(old), sql.Literal(new)))
        targets, evaluation = conn.execute("SELECT targets, evaluation FROM prediction").fetchone()
        if old in targets:
            for suffix in [name.removeprefix(old) for name in columns(old, targets[old])] + ["_stated"]:
                conn.execute(sql.SQL("ALTER TABLE author_predictions RENAME COLUMN {} TO {}").format(sql.Identifier(old + suffix), sql.Identifier(new + suffix)))
            conn.execute("UPDATE prediction SET targets = %s, evaluation = %s", [Jsonb(renamed_keys(targets, old, new)), Jsonb(renamed_keys(evaluation, old, new))])


def rename_model(path, old, new):
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    artifact["targets"] = renamed_keys(artifact["targets"], old, new)
    artifact["evaluation"] = renamed_keys(artifact["evaluation"], old, new)
    for spec in artifact["specifications"]:
        spec["name"] = new if spec["name"] == old else spec["name"]
    for entry in artifact["history"]:
        entry["fields"] = renamed_keys(entry["fields"], old, new)
    temporary = path.with_suffix(".renaming")
    torch.save(artifact, temporary)
    temporary.replace(path)


def rename_manifest(path, old, new):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name in MANIFEST_MAPS:
        if name in manifest:
            manifest[name] = renamed_keys(manifest[name], old, new)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding="utf-8")


def rename_gold(path, old, new):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    with open(path, "w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row | {"attribute": new if row["attribute"] == old else row["attribute"]}, ensure_ascii=False) + "\n")


@timed
def rename(old, new):
    started = time.perf_counter()
    rename_database(old, new)
    LOG.info("renamed database %s to %s seconds=%.2f", old, new, time.perf_counter() - started)
    for path in (THRESHOLDS, TARGETS):
        rewrite_json(Path(path), old, new)
    for path in (MODEL, TEXT_MODEL):
        rename_model(path, old, new)
    for directory in (DATA, TEXT_DATA):
        rename_manifest(directory / "manifest.json", old, new)
    rename_gold(ANNOTATIONS / "author_gold.jsonl", old, new)
    LOG.info("renamed %s to %s seconds=%.2f", old, new, time.perf_counter() - started)
    return {"old": old, "new": new, "seconds": round(time.perf_counter() - started, 2)}
