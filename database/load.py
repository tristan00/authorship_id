import hashlib
import multiprocessing
import queue
import threading
import time
from multiprocessing import shared_memory

import orjson
import psycopg

from reddit_dumps import setup_logging
from reddit_dumps.config import CHUNK_SIZE, SLOTS
from reddit_dumps.extract import produce

from . import DSN, DUMPS, LOG, LOGS, bounds, timed
from .config import PARSERS, SLOT_SIZE, TRANSFER_SLOTS

KINDS = {"comment": ("comments", "RC"), "post": ("submissions", "RS")}
COLUMNS = ["created_utc", "is_submitter", "over_18", "is_self", "record_id", "subreddit", "record_type", "author", "author_fullname", "link_id", "parent_id",
           "author_flair_text", "link_flair_text", "post_hint", "crosspost_parent", "text_status", "text_sha256"]
BODY = ["text_sha256", "text", "words", "month"]
UNAVAILABLE = {"[deleted]", "[removed]", "[ Removed by Reddit ]", "[ Removed by moderator ]", "[ Removed by Reddit on account of violating the [content policy](/help/contentpolicy). ]"}


def to_record(raw, kind):
    body = raw["body" if kind == "comment" else "selftext"]
    title = raw["title"] if kind == "post" else ""
    removed = body in UNAVAILABLE or title in UNAVAILABLE
    body = "" if body in UNAVAILABLE else body
    title = "" if title in UNAVAILABLE else title
    text = "\n\n".join(part for part in (title, body) if part.strip())
    status = "title_only" if kind == "post" and title and not body else "available" if text else "removed" if removed else "empty"
    return {
        "record_id": ("t1_" if kind == "comment" else "t3_") + raw["id"], "record_type": kind, "author": raw.get("author", "[deleted]"),
        "created_utc": raw["created_utc"], "text_status": status,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).digest(), "text": text, "words": len(text.split()),
    }


def reddit_fields(raw, kind):
    comment = kind == "comment"
    return {"author_fullname": raw.get("author_fullname"), "author_flair_text": raw["author_flair_text"],
            "link_id": raw["link_id"] if comment else "t3_" + raw["id"], "parent_id": raw["parent_id"] if comment else None,
            "is_submitter": raw.get("is_submitter") if comment else None, "link_flair_text": None if comment else raw["link_flair_text"],
            "over_18": None if comment else raw["over_18"], "is_self": None if comment else raw["is_self"],
            "post_hint": raw.get("post_hint"), "crosspost_parent": raw.get("crosspost_parent")}


def read_dump(kind, path, chunks, name, slots):
    setup_logging(LOGS / "database.log")
    memory = shared_memory.SharedMemory(name)
    full, free = queue.SimpleQueue(), queue.SimpleQueue()
    for _ in range(SLOTS):
        free.put(bytearray(CHUNK_SIZE))
    threading.Thread(target=produce, args=(path, full, free), daemon=True).start()
    started, sent = time.perf_counter(), 0
    while (item := full.get()) is not None:
        if isinstance(item, BaseException):
            raise item
        buf, end = item[:2]
        if end > SLOT_SIZE:
            raise ValueError(f"{path} has a {end} byte chunk, transfer slots hold {SLOT_SIZE}")
        slot = slots.get()
        memory.buf[slot * SLOT_SIZE:slot * SLOT_SIZE + end] = memoryview(buf)[:end]
        chunks.put((kind, slot, end))
        free.put(buf)
        sent += end
    memory.close()
    LOG.info("%s read %.1f GB in %.0fs", path.name, sent / 1e9, time.perf_counter() - started)


def parse_chunks(chunks, month, total, names, slots):
    setup_logging(LOGS / "database.log")
    memory = {kind: shared_memory.SharedMemory(name) for kind, name in names.items()}
    rows = 0
    table = "records_" + month.replace("-", "_")
    with psycopg.connect(DSN) as meta, psycopg.connect(DSN) as body, meta.cursor().copy(f"COPY {table} ({', '.join(COLUMNS)}) FROM STDIN") as records, \
            body.cursor().copy(f"COPY bodies_stage ({', '.join(BODY)}) FROM STDIN") as stage:
        while (item := chunks.get()) is not None:
            kind, slot, end = item
            data = bytes(memory[kind].buf[slot * SLOT_SIZE:slot * SLOT_SIZE + end])
            slots[kind].put(slot)
            for line in data.split(b"\n"):
                if line:
                    raw = orjson.loads(line)
                    record = to_record(raw, kind) | reddit_fields(raw, kind)
                    record["subreddit"] = raw["subreddit"].lower()
                    record["month"] = month
                    records.write_row([record[c] for c in COLUMNS])
                    stage.write_row([record[c] for c in BODY])
                    rows += 1
    for shared in memory.values():
        shared.close()
    with total.get_lock():
        total.value += rows
    LOG.info("parser copied %s rows", rows)


def dumps(month):
    found = {}
    for kind, (folder, prefix) in KINDS.items():
        paths = list(DUMPS.glob(f"*/reddit/{folder}/{prefix}_{month}.zst"))
        if len(paths) != 1:
            raise LookupError(f"{prefix}_{month}.zst found {len(paths)} times under {DUMPS}")
        found[kind] = paths[0]
    return found


@timed
def add(months):
    from .server import create, finish, reloadable, schema
    with psycopg.connect(DSN) as conn:
        schema(conn)
        for month in months:
            reloadable(conn, month)
        conn.execute("DELETE FROM months WHERE month = ANY(%s)", [months])
    for month in sorted(months):
        create(month)
        rows = load_month(month)
        finish(month)
        with psycopg.connect(DSN) as conn:
            conn.execute("INSERT INTO months (month, records) VALUES (%s, %s)", [month, rows])


@timed
def load_month(month):
    files = dumps(month)
    chunks = multiprocessing.Queue()
    total = multiprocessing.Value("q", 0)
    memory = {kind: shared_memory.SharedMemory(create=True, size=TRANSFER_SLOTS * SLOT_SIZE) for kind in files}
    slots = {kind: multiprocessing.Queue() for kind in files}
    for queued in slots.values():
        for slot in range(TRANSFER_SLOTS):
            queued.put(slot)
    names = {kind: shared.name for kind, shared in memory.items()}
    readers = [multiprocessing.Process(target=read_dump, args=(kind, path, chunks, names[kind], slots[kind]), name=f"read-{kind}", daemon=True)
               for kind, path in files.items()]
    parsers = [multiprocessing.Process(target=parse_chunks, args=(chunks, month, total, names, slots), name=f"parse-{index}", daemon=True)
               for index in range(PARSERS)]
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
        for queued in (chunks, *slots.values()):
            queued.close()
            queued.join_thread()
        for shared in memory.values():
            shared.close()
            shared.unlink()
    LOG.info("%s loaded %s records", month, total.value)
    return total.value


def watch(waiting, processes):
    while True:
        failed = [process.name for process in processes if process.exitcode]
        if failed:
            raise RuntimeError(f"load processes failed: {failed}")
        if not any(process.is_alive() for process in waiting):
            return
        time.sleep(1)


@timed
def verify(month):
    with psycopg.connect(DSN) as conn:
        expected = conn.execute("SELECT records FROM months WHERE month = %s", [month]).fetchone()[0]
        found = conn.execute("SELECT count(*) FROM records WHERE created_utc >= %s AND created_utc < %s", bounds(month)).fetchone()[0]
    if found != expected:
        raise ValueError(f"{month} has {found} records, its load copied {expected}")
    LOG.info("%s verified %s records", month, found)

