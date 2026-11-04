from database.load import load_month
from database.server import counts, schema
from reddit_dumps.catalog import month_range
from reddit_dumps.download import delete, download

from . import LOG, timed


@timed
def run(start, end):
    schema()
    for month in month_range(start, end):
        download([month])
        load_month(month)
        delete(month)
        LOG.info("%s done", month)
    counts()
