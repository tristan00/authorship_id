import hashlib
import multiprocessing
import queue
import threading
import time

import orjson
import psycopg

from reddit_dumps import setup_logging
from reddit_dumps.config import CHUNK_SIZE, SLOTS
from reddit_dumps.extract import produce

from . import DSN, DUMPS, LOG, LOGS, MONTH, timed
from .config import PARSERS, SCAN_WORKERS

KINDS = {"comment": ("comments", "RC"), "post": ("submissions", "RS")}
COLUMNS = ["record_id", "subreddit", "record_type", "author", "author_fullname", "created_utc", "link_id", "parent_id", "is_submitter", "author_flair_text",
           "link_flair_text", "over_18", "is_self", "post_hint", "crosspost_parent", "text_status", "text_sha256", "text"]
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
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "text": text,
    }


def reddit_fields(raw, kind):
    comment = kind == "comment"
    return {"author_fullname": raw.get("author_fullname"), "author_flair_text": raw["author_flair_text"],
            "link_id": raw["link_id"] if comment else "t3_" + raw["id"], "parent_id": raw["parent_id"] if comment else None,
            "is_submitter": raw.get("is_submitter") if comment else None, "link_flair_text": None if comment else raw["link_flair_text"],
            "over_18": None if comment else raw["over_18"], "is_self": None if comment else raw["is_self"],
            "post_hint": raw.get("post_hint"), "crosspost_parent": raw.get("crosspost_parent")}


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


def parse_chunks(chunks):
    setup_logging(LOGS / "database.log")
    rows = 0
    with psycopg.connect(DSN) as conn, conn.cursor().copy(f"COPY texts ({', '.join(COLUMNS)}) FROM STDIN") as copy:
        while (item := chunks.get()) is not None:
            kind, data = item
            for line in data.split(b"\n"):
                if line:
                    raw = orjson.loads(line)
                    record = to_record(raw, kind) | reddit_fields(raw, kind)
                    record["subreddit"] = raw["subreddit"].lower()
                    copy.write_row([record[c] for c in COLUMNS])
                    rows += 1
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
    from .server import indexes, schema
    with psycopg.connect(DSN) as conn:
        schema(conn)
    for month in months:
        load_month(month)
    indexes()
    with psycopg.connect(DSN) as conn:
        conn.execute(f"ALTER TABLE texts SET (parallel_workers = {SCAN_WORKERS})")
        conn.execute("ANALYZE texts")


@timed
def load_month(month):
    files = dumps(month)
    chunks = multiprocessing.Queue(maxsize=4 * PARSERS)
    readers = [multiprocessing.Process(target=read_dump, args=(kind, path, chunks), name=f"read-{kind}", daemon=True) for kind, path in files.items()]
    parsers = [multiprocessing.Process(target=parse_chunks, args=(chunks,), name=f"parse-{index}", daemon=True) for index in range(PARSERS)]
    processes = readers + parsers
    try:
        with psycopg.connect(DSN) as conn:
            clear(conn, month)
        for process in processes:
            process.start()
        watch(readers, processes)
        for _ in parsers:
            chunks.put(None)
        watch(parsers, processes)
        with psycopg.connect(DSN) as conn:
            conn.execute("INSERT INTO months (month) VALUES (%s) ON CONFLICT (month) DO UPDATE SET loaded_at = now()", [month])
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            if process.pid is not None:
                process.join()
                process.close()
        chunks.close()
        chunks.join_thread()


def watch(waiting, processes):
    while True:
        failed = [process.name for process in processes if process.exitcode]
        if failed:
            raise RuntimeError(f"load processes failed: {failed}")
        if not any(process.is_alive() for process in waiting):
            return
        time.sleep(1)


@timed
def clear(conn, month):
    LOG.info("%s cleared %s texts", month, conn.execute(f"DELETE FROM texts WHERE {MONTH} = %s", [month]).rowcount)
