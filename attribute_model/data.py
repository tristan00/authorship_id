import io
import json
import shutil
from pathlib import Path

import lance
import numpy as np
import psycopg
import pyarrow as pa
import pyarrow.compute as pc
from psycopg.rows import dict_row
from pyarrow import csv

from author_encoder.config import DIMENSIONS, VECTOR_STORE
from author_encoder.index import PROTOCOL
from author_encoder.lock import index_lock
from claim_extraction.config import NUMERIC
from database import DSN

from . import LOG, timed, write_json
from .config import check_targets, partition, validate

CLAIMS = "COPY (SELECT author, attribute, value FROM author_claims WHERE attribute = ANY(%s)) TO STDOUT (FORMAT CSV)"
ARRAYS = ("users", "labels", "splits")


def source(conn):
    months = {row["month"]: str(row["loaded_at"]) for row in conn.execute("SELECT month, loaded_at FROM months ORDER BY month")}
    run = conn.execute("SELECT run_id::text FROM consolidation").fetchone()
    if not run:
        raise ValueError("Consolidation must finish before preparing model targets")
    return {"months": months, "consolidation": run["run_id"], "protocol": json.loads(PROTOCOL)}


@timed
def read_claims(conn, targets):
    buffer = io.BytesIO()
    with conn.cursor().copy(CLAIMS, [list(targets)]) as copy:
        for chunk in copy:
            buffer.write(chunk)
    names = ["author", "attribute", "value"]
    table = csv.read_csv(pa.BufferReader(buffer.getvalue()), read_options=csv.ReadOptions(column_names=names),
                         convert_options=csv.ConvertOptions(column_types={name: pa.string() for name in names}, strings_can_be_null=False))
    LOG.info("attribute claims rows=%d", table.num_rows)
    return table


def encode(values, name, kind):
    if kind == "numeric":
        numbers = pc.cast(values, pa.float64()).to_numpy()
        if not np.isfinite(numbers).all():
            raise ValueError("Numeric claims must be finite")
        low, high = NUMERIC.get(name, (-np.inf, np.inf))
        return np.where((numbers >= low) & (numbers <= high), numbers, np.nan), None
    counts = pc.value_counts(values).to_pylist()
    catalog = [item["values"] for item in sorted(counts, key=lambda item: (-item["counts"], item["values"]))]
    return pc.index_in(values, value_set=pa.array(catalog)).to_numpy().astype(np.float64), catalog


@timed
def labeled_users(dataset, labeled):
    stored = dataset.to_table(columns=["author"], scan_in_order=True)["author"]
    found = pc.index_in(stored, value_set=labeled)
    mask = pc.is_valid(found).to_numpy(zero_copy_only=False)
    positions = np.flatnonzero(mask)
    rows = np.full(len(labeled), -1, dtype=np.int64)
    rows[found.take(positions).to_numpy().astype(np.int64)] = np.arange(len(positions))
    users, scanned = [], 0
    for batch in dataset.to_batches(columns=["vector"], batch_size=65536, scan_in_order=True):
        kept = np.flatnonzero(mask[scanned:scanned + batch.num_rows])
        if len(kept):
            vectors = batch["vector"].flatten().to_numpy().reshape(-1, DIMENSIONS)[kept]
            if not np.isfinite(vectors).all():
                raise ValueError("Saved user vectors must be finite")
            users.append(vectors.astype(np.float16))
        scanned += batch.num_rows
        if scanned % (64 * 65536) < batch.num_rows:
            LOG.info("attribute users scanned=%d of %d", scanned, len(stored))
    if scanned != len(stored):
        raise ValueError("User store rows changed between the author and vector scans")
    return rows, users, stored.take(positions).to_pylist(), scanned


@timed
def prepare(directory, targets):
    targets = validate(targets)
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    with index_lock(VECTOR_STORE), psycopg.connect(DSN, row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        expected = source(conn)
        dataset = lance.dataset(VECTOR_STORE)
        metadata = dataset.schema.metadata
        if metadata.get(b"protocol") != PROTOCOL.encode() or json.loads(metadata[b"source"])["months"] != expected["months"]:
            raise ValueError("User vectors do not match the completed source months")
        claims = read_claims(conn, targets)
        labeled = pc.unique(claims["author"])
        rows, users, authors, scanned = labeled_users(dataset, labeled)
        del dataset
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if source(conn) != expected:
            raise ValueError("Source changed during preparation; nothing was written")
    if len(authors) < 1000:
        raise ValueError("At least 1000 labeled authors with user vectors are required")
    owners = rows[pc.index_in(claims["author"], value_set=labeled).to_numpy()]
    present = owners >= 0
    labels = np.full((len(authors), len(targets)), np.nan)
    catalogs, excluded = {}, {}
    for column, (name, kind) in enumerate(targets.items()):
        chosen = np.flatnonzero(present & pc.equal(claims["attribute"], name).to_numpy(zero_copy_only=False))
        if not len(chosen):
            raise ValueError(f"No observed labels for configured field {name}")
        labels[owners[chosen], column], catalog = encode(claims["value"].take(chosen), name, kind)
        excluded[name] = int(len(chosen) - np.isfinite(labels[owners[chosen], column]).sum())
        if catalog is not None:
            catalogs[name] = catalog
    kept = np.flatnonzero(np.isfinite(labels).any(1))
    authors, labels = [authors[index] for index in kept], labels[kept]
    staging.mkdir(parents=True)
    np.save(staging / "users.npy", np.concatenate(users)[kept])
    del users
    np.save(staging / "labels.npy", labels)
    np.save(staging / "splits.npy", np.fromiter(map(partition, authors), dtype=np.uint8, count=len(authors)))
    write_json(staging / "authors.json", authors)
    counts = np.isfinite(labels).sum(0)
    manifest = {"targets": targets, "catalogs": catalogs, "authors": len(authors), "scanned_users": scanned, "source": expected,
                "target_counts": {name: int(count) for name, count in zip(targets, counts)}, "excluded_out_of_range": excluded,
                "numeric_ranges": {name: NUMERIC[name] for name, kind in targets.items() if kind == "numeric" and name in NUMERIC}}
    write_json(staging / "manifest.json", manifest)
    if directory.exists():
        shutil.rmtree(directory)
    staging.rename(directory)
    return {"authors": len(authors), "directory": str(directory), "target_counts": manifest["target_counts"], "excluded_out_of_range": excluded}


def load(directory, targets):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    check_targets(targets, manifest["targets"])
    arrays = {name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False) for name in ARRAYS}
    if arrays["users"].shape != (manifest["authors"], DIMENSIONS) or arrays["labels"].shape != (manifest["authors"], len(targets)) or len(arrays["splits"]) != manifest["authors"]:
        raise ValueError("Prepared arrays do not match the manifest")
    return manifest, arrays
