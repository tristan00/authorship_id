import os
import subprocess
from pathlib import Path

from attribute_model.config import DATA, MODEL, read_targets
from database import LOGS, host
from database.load import load_month
from database.server import counts, schema
from reddit_dumps.catalog import month_range
from reddit_dumps.download import delete, download

from . import LOG, timed

EXTRACTOR = Path(__file__).parents[1] / "extractor"


@timed
def claims(command):
    subprocess.run(["cargo", "build", "--release"], cwd=EXTRACTOR, check=True)
    with open(LOGS / "claim_extraction.log", "a", encoding="utf-8") as log:
        subprocess.run([str(EXTRACTOR / "target" / "release" / "claims"), command, "--host", host(), "--threads", str(os.cpu_count() - 2)], check=True, stderr=log)


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
    targets = read_targets()
    claims("run")
    claims("flairs")
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
