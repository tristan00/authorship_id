from attribute_model.config import DATA, MODEL, read_targets
from database.load import load_month
from database.server import counts, schema
from reddit_dumps.catalog import month_range
from reddit_dumps.download import delete, download

from . import LOG, timed


@timed
def load(start, end):
    schema()
    for month in month_range(start, end):
        download([month])
        load_month(month)
        delete(month)
        LOG.info("%s done", month)
    counts()


@timed
def derive():
    from attribute_model.data import prepare
    from attribute_model.predict import predict_table
    from attribute_model.train import train
    from author_encoder.predict import encode_store
    from author_encoder.store import build
    from claim_consolidation.consolidate import consolidate
    from claim_extraction.run import extract, extract_flairs
    targets = read_targets()
    extract()
    extract_flairs()
    consolidate()
    build()
    encode_store()
    prepare(DATA, targets)
    train(DATA, MODEL, targets)
    predict_table(MODEL, targets)


@timed
def run(start, end, loading=True):
    if loading:
        load(start, end)
    derive()
