import multiprocessing

import psycopg

from claim_consolidation.consolidate import consolidate
from claim_extraction.config import EXTRACT_WORKERS
from claim_extraction.run import run as extract
from database import DSN, LOGS
from database.load import add, verify
from explorer.prepare import prepare
from reddit_dumps import setup_logging
from reddit_dumps.catalog import load_catalog, month_index
from reddit_dumps.download import delete, download, files

from . import LOG, timed

CONSOLIDATED = """SELECT EXISTS (SELECT FROM consolidation WHERE months = (SELECT array_agg(month ORDER BY month) FROM months)
    AND started_at > (SELECT max(extracted_at) FROM months))"""
EXPLORED = "SELECT EXISTS (SELECT FROM explorer_totals WHERE run_id = (SELECT run_id FROM consolidation))"


def loaded(month):
    with psycopg.connect(DSN) as conn:
        return conn.execute("SELECT to_regclass('months') IS NOT NULL").fetchone()[0] and \
            conn.execute("SELECT EXISTS (SELECT FROM months WHERE month = %s)", [month]).fetchone()[0]


def current(table, query):
    with psycopg.connect(DSN) as conn:
        return conn.execute("SELECT to_regclass(%s)", [table]).fetchone()[0] is not None and conn.execute(query).fetchone()[0]


def following(month):
    index = month_index(month) + 1
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def background(target, *args):
    process = multiprocessing.Process(target=target, args=args, name=target.__name__)
    process.start()
    return process


@timed
def wait(process):
    process.join()
    if process.exitcode:
        raise RuntimeError(f"{process.name} failed with exit code {process.exitcode}")


@timed
def fetch(month):
    if loaded(month):
        LOG.info("%s is loaded, no download", month)
        return
    download([month])


@timed
def prefetch(month):
    setup_logging(LOGS / "download.log")
    if loaded(month) or not any(start <= month <= end for start, end, _ in load_catalog()):
        LOG.info("%s is loaded or not published, no download", month)
        return
    download([month])


@timed
def load(month):
    if loaded(month):
        LOG.info("%s is loaded", month)
        return
    add([month])


@timed
def clean(month):
    if not files(month):
        LOG.info("%s has no dumps left", month)
        return
    verify(month)
    delete(month)


@timed
def consolidation():
    if current("consolidation", CONSOLIDATED):
        LOG.info("consolidation covers every extracted month")
        return
    consolidate()


@timed
def vectors():
    setup_logging(LOGS / "pipeline.log")
    from author_encoder.update import update, users
    LOG.info("vectors %s", update())
    LOG.info("users %s", users())


@timed
def explorer():
    if current("explorer_totals", EXPLORED):
        LOG.info("explorer matches the consolidation")
        return
    prepare()


@timed
def run(month):
    fetch(month)
    upcoming = background(prefetch, following(month))
    try:
        load(month)
        clean(month)
        encoder = background(vectors)
        try:
            extract(EXTRACT_WORKERS)
            consolidation()
            explorer()
        finally:
            wait(encoder)
    finally:
        wait(upcoming)
