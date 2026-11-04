import hashlib
import multiprocessing
import queue
import threading
import time

import orjson
import pyarrow as pa

from reddit_dumps import setup_logging
from reddit_dumps.catalog import month_range
from reddit_dumps.config import CHUNK_SIZE, SLOTS
from reddit_dumps.extract import produce

from . import DUMPS, LOG, LOGS, bounds, client, in_range, sha_ranges, timed
from .config import BODY_BATCH, CONVERT_ROWS, PARSERS, QUEUE_CHUNKS, RECORD_BATCH, SEND_BYTES

KINDS = {"comment": ("comments", "RC"), "post": ("submissions", "RS")}
UNAVAILABLE = {"[deleted]", "[removed]", "[ Removed by Reddit ]", "[ Removed by moderator ]",
               "[ Removed by Reddit on account of violating the [content policy](/help/contentpolicy). ]"}
RECORDS = pa.schema([("created_utc", pa.uint32()), ("record_id", pa.string()), ("record_type", pa.string()), ("author", pa.string()), ("subreddit", pa.string()),
                     ("author_fullname", pa.string()), ("link_id", pa.string()), ("parent_id", pa.string()), ("author_flair_text", pa.string()),
                     ("link_flair_text", pa.string()), ("post_hint", pa.string()), ("crosspost_parent", pa.string()), ("is_submitter", pa.bool_()),
                     ("over_18", pa.bool_()), ("is_self", pa.bool_()), ("text_status", pa.string()), ("text_sha256", pa.binary(32))])
BODIES = pa.schema([("text_sha256", pa.binary(32)), ("text", pa.string()), ("words", pa.uint32())])
STAGE = "CREATE TABLE bodies_stage (text_sha256 FixedString(32), text String CODEC(ZSTD(1)), words UInt32) ENGINE = MergeTree ORDER BY text_sha256"


def rows(raw, kind):
    comment = kind == "comment"
    body = raw["body" if comment else "selftext"]
    title = "" if comment else raw["title"]
    removed = body in UNAVAILABLE or title in UNAVAILABLE
    body = "" if body in UNAVAILABLE else body
    title = "" if title in UNAVAILABLE else title
    text = "\n\n".join(part for part in (title, body) if part.strip())
    status = "title_only" if not comment and title and not body else "available" if text else "removed" if removed else "empty"
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    record = (int(raw["created_utc"]), ("t1_" if comment else "t3_") + raw["id"], kind, raw["author"], raw["subreddit"].lower(), raw.get("author_fullname"),
              raw["link_id"] if comment else "t3_" + raw["id"], raw["parent_id"] if comment else None, raw["author_flair_text"],
              None if comment else raw["link_flair_text"], raw.get("post_hint"), raw.get("crosspost_parent"),
              raw.get("is_submitter") if comment else None, None if comment else raw["over_18"], None if comment else raw["is_self"], status, digest)
    return record, (digest, text, len(text.split())) if text else None


def batch(schema, rows):
    return pa.RecordBatch.from_arrays([pa.array(column, type=field.type) for column, field in zip(zip(*rows), schema)], schema=schema)


def send(db, name, schema, batches):
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as writer:
        for item in batches:
            writer.write_batch(item)
    payload = memoryview(sink.getvalue())
    db.raw_insert(name, insert_block=(payload[offset:offset + SEND_BYTES] for offset in range(0, len(payload), SEND_BYTES)), fmt="ArrowStream")


class Pending:
    def __init__(self, db, name, schema, limit):
        self.db, self.name, self.schema, self.limit = db, name, schema, limit
        self.rows, self.batches, self.count = [], [], 0

    def add(self, row):
        self.rows.append(row)
        if len(self.rows) >= CONVERT_ROWS:
            self.convert()
            if self.count >= self.limit:
                self.flush()

    def convert(self):
        if self.rows:
            self.batches.append(batch(self.schema, self.rows))
            self.count += len(self.rows)
            self.rows.clear()

    def flush(self):
        self.convert()
        if self.batches:
            send(self.db, self.name, self.schema, self.batches)
            self.batches.clear()
            self.count = 0


def read_dump(kind, path, chunks):
    setup_logging(LOGS / "database.log")
    full, free = queue.SimpleQueue(), queue.SimpleQueue()
    for _ in range(SLOTS):
        free.put(bytearray(CHUNK_SIZE))
    threading.Thread(target=produce, args=(path, full, free), daemon=True).start()
    started, sent = time.perf_counter(), 0
    while (item := full.get()) is not None:
        if isinstance(item, BaseException):
            raise item
        buf, end = item[:2]
        chunks.put((kind, bytes(buf[:end])))
        free.put(buf)
        sent += end
    LOG.info("%s read %.1f GB in %.0fs", path.name, sent / 1e9, time.perf_counter() - started)


def parse_chunks(chunks, total):
    setup_logging(LOGS / "database.log")
    pa.set_memory_pool(pa.system_memory_pool())
    db = client()
    records, bodies, count = Pending(db, "records", RECORDS, RECORD_BATCH), Pending(db, "bodies_stage", BODIES, BODY_BATCH), 0
    while (item := chunks.get()) is not None:
        kind, block = item
        for line in block.split(b"\n"):
            if line:
                record, body = rows(orjson.loads(line), kind)
                records.add(record)
                if body:
                    bodies.add(body)
                count += 1
    records.flush()
    bodies.flush()
    with total.get_lock():
        total.value += count
    LOG.info("parser inserted %s records", count)


def dumps(month):
    found = {}
    for kind, (folder, prefix) in KINDS.items():
        paths = list(DUMPS.glob(f"*/reddit/{folder}/{prefix}_{month}.zst"))
        if len(paths) != 1:
            raise LookupError(f"{prefix}_{month}.zst found {len(paths)} times under {DUMPS}")
        found[kind] = paths[0]
    return found


def watch(waiting, processes):
    while True:
        failed = [process.name for process in processes if process.exitcode]
        if failed:
            raise RuntimeError(f"load processes failed: {failed}")
        if not any(process.is_alive() for process in waiting):
            return
        time.sleep(1)


@timed
def parse_month(month):
    files = dumps(month)
    chunks = multiprocessing.Queue(QUEUE_CHUNKS)
    total = multiprocessing.Value("q", 0)
    readers = [multiprocessing.Process(target=read_dump, args=(kind, path, chunks), name=f"read-{kind}", daemon=True) for kind, path in files.items()]
    parsers = [multiprocessing.Process(target=parse_chunks, args=(chunks, total), name=f"parse-{index}", daemon=True) for index in range(PARSERS)]
    processes = readers + parsers
    try:
        for process in processes:
            process.start()
        watch(readers, processes)
        for _ in parsers:
            chunks.put(None)
        watch(parsers, processes)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            if process.pid is not None:
                process.join()
                process.close()
        chunks.close()
        chunks.join_thread()
    LOG.info("%s parsed %s records", month, total.value)
    return total.value


@timed
def merge_bodies():
    db = client(optimize_aggregation_in_order=1)
    for low, high in sha_ranges():
        db.command(f"INSERT INTO bodies SELECT text_sha256, any(text), any(words) FROM bodies_stage WHERE {in_range('text_sha256', low, high)} "
                   f"AND text_sha256 NOT IN (SELECT text_sha256 FROM bodies WHERE {in_range('text_sha256', low, high)}) GROUP BY text_sha256")
    LOG.info("bodies rows=%s", db.command("SELECT count() FROM bodies"))


@timed
def unload(month):
    low, high = bounds(month)
    window = f"created_utc >= {low} AND created_utc < {high}"
    db = client()
    db.command("DROP TABLE IF EXISTS reload_candidates")
    db.command(f"CREATE TABLE reload_candidates ENGINE = MergeTree ORDER BY text_sha256 AS SELECT DISTINCT text_sha256 FROM records WHERE {window}")
    db.command(f"DELETE FROM records WHERE {window}")
    db.command(f"DELETE FROM records_by_subreddit WHERE {window}")
    db.command(f"DELETE FROM months WHERE month = '{month}'")
    LOG.info("%s unloaded, candidates=%s", month, db.command("SELECT count() FROM reload_candidates"))


@timed
def collect_orphans():
    db = client()
    db.command("DROP TABLE IF EXISTS reload_orphans")
    db.command("CREATE TABLE reload_orphans ENGINE = MergeTree ORDER BY text_sha256 AS SELECT text_sha256 FROM reload_candidates WHERE text_sha256 NOT IN "
               "(SELECT text_sha256 FROM records WHERE text_sha256 IN (SELECT text_sha256 FROM reload_candidates))")
    db.command("DELETE FROM bodies WHERE text_sha256 IN (SELECT text_sha256 FROM reload_orphans)")
    LOG.info("orphan bodies removed=%s", db.command("SELECT count() FROM reload_orphans"))
    db.command("DROP TABLE reload_orphans")
    db.command("DROP TABLE reload_candidates")


@timed
def load_month(month):
    low, high = bounds(month)
    db = client()
    reload = db.command(f"SELECT count() FROM records WHERE created_utc >= {low} AND created_utc < {high}") > 0
    if reload:
        unload(month)
    db.command("DROP TABLE IF EXISTS bodies_stage")
    db.command(STAGE)
    parsed = parse_month(month)
    stored = db.command(f"SELECT count() FROM records WHERE created_utc >= {low} AND created_utc < {high}")
    if stored != parsed:
        raise ValueError(f"{month} parsed {parsed} records but records holds {stored} in its range")
    merge_bodies()
    db.command("DROP TABLE bodies_stage")
    if reload:
        collect_orphans()
    db.command(f"INSERT INTO months (month, records) VALUES ('{month}', {parsed})")
    LOG.info("%s loaded %s records", month, parsed)


@timed
def add(start, end):
    from .server import counts, schema
    schema()
    for month in month_range(start, end):
        load_month(month)
    counts()
