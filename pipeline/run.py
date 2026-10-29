import psycopg

from claim_consolidation.consolidate import consolidate
from claim_extraction.config import EXTRACT_WORKERS
from claim_extraction.run import run as extract
from database import DSN
from database.load import add, verify
from explorer.prepare import prepare
from reddit_dumps.download import delete, download, files

from . import LOG, timed

CONSOLIDATED = """SELECT EXISTS (SELECT FROM consolidation WHERE months = (SELECT array_agg(month ORDER BY month) FROM months)
    AND started_at > (SELECT max(extracted_at) FROM months))"""
EXPLORED = "SELECT EXISTS (SELECT FROM explorer_totals WHERE run_id = (SELECT run_id FROM consolidation))"


def loaded(month):
    with psycopg.connect(DSN) as conn:
        return conn.execute("SELECT EXISTS (SELECT FROM months WHERE month = %s)", [month]).fetchone()[0]


def current(table, query):
    with psycopg.connect(DSN) as conn:
        return conn.execute("SELECT to_regclass(%s)", [table]).fetchone()[0] is not None and conn.execute(query).fetchone()[0]


@timed
def fetch(month):
    if loaded(month):
        LOG.info("%s is loaded, no download", month)
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
    from author_encoder.update import update
    LOG.info("vectors %s", update())


@timed
def explorer():
    if current("explorer_totals", EXPLORED):
        LOG.info("explorer matches the consolidation")
        return
    prepare()


@timed
def run(month):
    fetch(month)
    load(month)
    clean(month)
    extract(EXTRACT_WORKERS)
    consolidation()
    vectors()
    explorer()
