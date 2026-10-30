import json
import queue
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import ProcessPoolExecutor
from itertools import islice

import lance
import numpy as np
import psycopg
import pyarrow as pa
from psycopg import sql

from database import DSN
from reddit_dumps import setup_logging

from . import LOG, clean, timed
from .config import HASH_PARTS, PREPARE_WORKERS, TEXT_STORE
from .tokens import load_tokenizer, token_batches

SCALES = b"int8_scales"
MONTHS = b"months"
DIGEST = 32
TOKENIZER = STORE = FRAGMENTS = None
CACHE = OrderedDict()


def relation(source):
    return sql.Identifier(*source.split("."))


def span(index):
    return index * 65536 // HASH_PARTS, (index + 1) * 65536 // HASH_PARTS


def bounds(index):
    low, high = span(index)
    return low.to_bytes(2, "big"), high.to_bytes(2, "big") if high < 65536 else None


def raw(column, width=DIGEST):
    return np.frombuffer(column.buffers()[1], dtype=np.uint8)[column.offset * width:(column.offset + len(column)) * width]


@timed
def fragments(path):
    if not path.exists():
        return []
    ranges = []
    for fragment in lance.dataset(path).get_fragments():
        ends = fragment.take([0, fragment.count_rows() - 1], columns=["text_sha256"]).column(0).to_pylist()
        ranges.append((fragment.fragment_id, ends[0], ends[1]))
    return ranges


def start_worker(log, path, ranges):
    global TOKENIZER, STORE, FRAGMENTS
    setup_logging(log)
    TOKENIZER, STORE, FRAGMENTS = load_tokenizer(), lance.dataset(path) if ranges else None, ranges
    CACHE.clear()


def stored(low, high):
    found = []
    for fragment, first, last in FRAGMENTS:
        if first <= high and last >= low:
            if fragment not in CACHE:
                digests = raw(STORE.get_fragment(fragment).to_table(columns=["text_sha256"]).column(0).combine_chunks()).tobytes()
                CACHE[fragment] = {digests[start:start + DIGEST] for start in range(0, len(digests), DIGEST)}
                if len(CACHE) > 8:
                    CACHE.popitem(last=False)
            CACHE.move_to_end(fragment)
            found.append(CACHE[fragment])
    return found


def prepare(job):
    source, month, index = job
    started = time.perf_counter()
    low, high = bounds(index)
    query = sql.SQL("COPY (SELECT text_sha256, text FROM {} WHERE month = {} AND text_sha256 >= {}{}) TO STDOUT").format(
        relation(source), sql.Literal(month), sql.Literal(low), sql.SQL(" AND text_sha256 < {}").format(sql.Literal(high)) if high is not None else sql.SQL(""))
    with psycopg.connect(DSN) as conn, conn.cursor().copy(query) as copy:
        copy.set_types(["bytea", "text"])
        rows = list(copy.rows())
    known = stored(min(digest for digest, _ in rows), max(digest for digest, _ in rows)) if rows and FRAGMENTS else []
    cleaned = [(digest, clean(body)) for digest, body in rows if not any(digest in digests for digests in known)]
    fresh = sorted((digest, text) for digest, text in cleaned if text)
    batches = token_batches(TOKENIZER, [text for _, text in fresh]) if fresh else []
    return (month, index), [digest for digest, _ in fresh], batches, len(rows), [digest for digest, text in cleaned if not text], time.perf_counter() - started


class Writer(threading.Thread):
    def __init__(self, emit):
        super().__init__(daemon=True)
        self.emit, self.items, self.error, self.seconds = emit, queue.Queue(maxsize=4), None, 0.

    def run(self):
        while (item := self.items.get()) is not None:
            if self.error is None:
                started = time.perf_counter()
                try:
                    self.emit(*item)
                except BaseException as error:
                    self.error = error
                self.seconds += time.perf_counter() - started

    def put(self, item):
        if self.error is not None:
            raise self.error
        self.items.put(item)

    def close(self):
        self.items.put(None)
        self.join()
        if self.error is not None:
            raise self.error


@timed
def encode(model, jobs, emit, initargs, empty):
    started = reported = time.perf_counter()
    texts = parts = read = 0
    gpu = prepare_seconds = 0.

    def progress():
        elapsed = time.perf_counter() - started
        LOG.info("text features parts=%d/%d bodies=%d new=%d texts_per_s=%.0f gpu_busy=%.0f%% prepare_seconds=%.0f write_seconds=%.1f eta_seconds=%.0f",
                 parts, len(jobs), read, texts, texts / elapsed if elapsed else 0., 100 * gpu / elapsed if elapsed else 0., prepare_seconds, writer.seconds,
                 (len(jobs) - parts) * elapsed / parts if parts else 0.)

    writer = Writer(emit)
    writer.start()
    with ProcessPoolExecutor(max_workers=PREPARE_WORKERS, initializer=start_worker, initargs=initargs) as pool:
        upcoming = iter(jobs)
        pending = deque(pool.submit(prepare, job) for job in islice(upcoming, 2 * PREPARE_WORKERS))
        while pending:
            future = pending.popleft()
            while True:
                try:
                    part, digests, batches, rows, blank, seconds = future.result(timeout=30)
                    break
                except TimeoutError:
                    progress()
            if (following := next(upcoming, None)) is not None:
                pending.append(pool.submit(prepare, following))
            prepare_seconds += seconds
            empty.setdefault(part[0], []).extend(blank)
            if digests:
                tick = time.perf_counter()
                features = model.host(model.features(batches, len(digests)))
                gpu += time.perf_counter() - tick
                writer.put((part, digests, features))
            texts, read, parts = texts + len(digests), read + rows, parts + 1
            if time.perf_counter() - reported >= 30:
                reported = time.perf_counter()
                progress()
    writer.close()
    progress()
    return {"bodies": read, "new_texts": texts, "parts": parts, "seconds": time.perf_counter() - started, "gpu_seconds": gpu, "prepare_seconds": prepare_seconds,
            "write_seconds": writer.seconds}


def scales(dataset):
    return np.array(json.loads(dataset.schema.metadata[SCALES]), dtype=np.float32)


def quantize(features, scale):
    steps = np.rint(features.astype(np.float32) / scale)
    return np.clip(steps, -127, 127).astype(np.int8), int(np.count_nonzero(np.abs(steps) > 127))


def arrow(digests, codes, scale):
    return pa.table({"text_sha256": pa.array(digests, pa.binary(32)),
                     "vector": pa.FixedSizeListArray.from_arrays(pa.array(codes.reshape(-1)), codes.shape[1])}).replace_schema_metadata({SCALES: json.dumps(scale.tolist())})


@timed
def write(loaded, path=TEXT_STORE, device="cuda", source="bodies", limit=None):
    done = json.loads(lance.dataset(path).schema.metadata.get(MONTHS, b"{}")) if path.exists() else {}
    months = [month for month, stamp in loaded.items() if done.get(month) != stamp]
    if not months:
        LOG.info("text vectors current store=%s months=%s", path, done)
        return {"skipped": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs = [(source, month, index) for month in months for index in range(HASH_PARTS)][:limit]
    ranges = fragments(path)
    LOG.info("text vectors source=%s months=%s store=%s parts=%d store_fragments=%d", source, months, path, len(jobs), len(ranges))
    scale, clipped = scales(lance.dataset(TEXT_STORE)), [0]
    from .model import load_model
    model = load_model(device)

    def emit(part, digests, features):
        codes, count = quantize(features(), scale)
        if count:
            LOG.info("text vectors part=%s clipped_values=%d of %d", part, count, codes.size)
        clipped[0] += count
        lance.write_dataset(arrow(digests, codes, scale), path, mode="append" if path.exists() else "create")

    empty = {}
    result = encode(model, jobs, emit, (path.parent / "texts.log", path, ranges), empty) | {"months": months, "clipped_values": clipped[0]}
    if path.exists() and limit is None:
        result["empty_bodies"] = record_empty(empty, months)
        lance.dataset(path).update_schema_metadata({MONTHS.decode(): json.dumps(loaded, sort_keys=True)})
    return result


@timed
def record_empty(empty, months):
    with psycopg.connect(DSN, autocommit=True) as conn:
        for month in months:
            conn.execute("DELETE FROM empty_bodies WHERE month = %s", [month])
            with conn.cursor().copy("COPY empty_bodies (month, text_sha256) FROM STDIN") as copy:
                for digest in empty.get(month, []):
                    copy.write_row((month, digest))
    return {month: len(empty.get(month, [])) for month in months}
