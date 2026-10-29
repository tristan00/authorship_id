import json
import queue
import threading
import time
from collections import deque
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
from .config import PART_PAGES, PREPARE_WORKERS, TEXT_STORE
from .tokens import load_tokenizer, token_batches

SCALES = b"int8_scales"
TOKENIZER = None


def relation(source):
    return sql.Identifier(*source.split("."))


@timed
def table_pages(source):
    with psycopg.connect(DSN) as conn:
        return conn.execute(sql.SQL("SELECT pg_relation_size({}::regclass) / current_setting('block_size')::int").format(sql.Literal(source))).fetchone()[0]


def start_worker(log):
    global TOKENIZER
    setup_logging(log)
    TOKENIZER = load_tokenizer()


def prepare(job):
    source, first = job
    started = time.perf_counter()
    query = sql.SQL("COPY (SELECT text_sha256, text FROM {} WHERE ctid >= {} AND ctid < {}) TO STDOUT").format(
        relation(source), sql.Literal(f"({first},0)"), sql.Literal(f"({first + PART_PAGES},0)"))
    with psycopg.connect(DSN) as conn, conn.cursor().copy(query) as copy:
        copy.set_types(["bytea", "text"])
        rows = [(digest, text) for digest, raw in copy.rows() if (text := clean(raw))]
    batches = token_batches(TOKENIZER, [text for _, text in rows]) if rows else []
    return first, [digest for digest, _ in rows], batches, time.perf_counter() - started


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
def encode(model, jobs, emit, log):
    started = reported = time.perf_counter()
    texts = parts = 0
    gpu = prepare_seconds = 0.

    def progress():
        elapsed = time.perf_counter() - started
        LOG.info("text features parts=%d/%d texts=%d texts_per_s=%.0f gpu_busy=%.0f%% prepare_seconds=%.0f write_seconds=%.1f eta_seconds=%.0f",
                 parts, len(jobs), texts, texts / elapsed if elapsed else 0., 100 * gpu / elapsed if elapsed else 0., prepare_seconds, writer.seconds,
                 (len(jobs) - parts) * elapsed / parts if parts else 0.)

    writer = Writer(emit)
    writer.start()
    with ProcessPoolExecutor(max_workers=PREPARE_WORKERS, initializer=start_worker, initargs=(log,)) as pool:
        upcoming = iter(jobs)
        pending = deque(pool.submit(prepare, job) for job in islice(upcoming, 2 * PREPARE_WORKERS))
        while pending:
            future = pending.popleft()
            while True:
                try:
                    first, digests, batches, seconds = future.result(timeout=30)
                    break
                except TimeoutError:
                    progress()
            if (following := next(upcoming, None)) is not None:
                pending.append(pool.submit(prepare, following))
            prepare_seconds += seconds
            if digests:
                tick = time.perf_counter()
                features = model.features(batches, len(digests)).cpu().numpy()
                gpu += time.perf_counter() - tick
                writer.put((first, digests, features))
            texts += len(digests)
            parts += 1
            if time.perf_counter() - reported >= 30:
                reported = time.perf_counter()
                progress()
    writer.close()
    progress()
    return {"texts": texts, "parts": parts, "seconds": time.perf_counter() - started, "gpu_seconds": gpu, "prepare_seconds": prepare_seconds,
            "write_seconds": writer.seconds}


def scales(dataset):
    return np.array(json.loads(dataset.schema.metadata[SCALES]), dtype=np.float32)


def quantize(features, scale):
    steps = np.rint(features.astype(np.float32) / scale)
    return np.clip(steps, -127, 127).astype(np.int8), int(np.count_nonzero(np.abs(steps) > 127))


def arrow(first, digests, codes, scale):
    return pa.table({"text_sha256": pa.array(digests, pa.binary(32)), "part": pa.array(np.full(len(digests), first, dtype=np.int32)),
                     "vector": pa.FixedSizeListArray.from_arrays(pa.array(codes.reshape(-1)), codes.shape[1])}).replace_schema_metadata({SCALES: json.dumps(scale.tolist())})


@timed
def done_parts(path):
    if not path.exists():
        return set()
    return set(lance.dataset(path).to_table(columns=["part"]).column("part").unique().to_pylist())


@timed
def write(source, path, device="cuda", limit=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    done = done_parts(path)
    firsts = [first for first in range(0, table_pages(source), PART_PAGES) if first not in done]
    jobs = [(source, first) for first in firsts[:limit]]
    LOG.info("text vectors source=%s store=%s parts_total=%d parts_done=%d parts_now=%d", source, path, len(firsts) + len(done), len(done), len(jobs))
    scale, clipped = scales(lance.dataset(TEXT_STORE)), [0]
    from .model import load_model
    model = load_model(device)

    def emit(first, digests, features):
        codes, count = quantize(features, scale)
        if count:
            LOG.info("text vectors part=%d clipped_values=%d of %d", first, count, codes.size)
        clipped[0] += count
        lance.write_dataset(arrow(first, digests, codes, scale), path, mode="append" if path.exists() else "create")

    return encode(model, jobs, emit, path.parent / "texts.log") | {"clipped_values": clipped[0]}

