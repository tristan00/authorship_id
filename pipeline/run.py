import os
import subprocess
from pathlib import Path

from attribute_model.config import data, model
from database import LOGS, host, selected
from database.load import load_month
from database.server import counts, schema
from reddit_dumps.catalog import month_range
from reddit_dumps.download import delete, download

from . import LOG, timed

ROOT = Path(__file__).parents[1]


@timed
def rust(crate, binary, command, log, *args):
    subprocess.run(["cargo", "build", "--release"], cwd=ROOT / crate, check=True)
    with open(LOGS / log, "a", encoding="utf-8") as out:
        return subprocess.run([str(ROOT / crate / "target" / "release" / binary), command, *args, "--host", host(), "--database", selected(), "--threads", str(os.cpu_count() - 2)],
                              check=True, stdout=subprocess.PIPE, stderr=out, text=True).stdout


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
    from attribute_model.config import TEXT_PARAMETERS, text_data, text_model
    from attribute_model.data import prepare
    from attribute_model.predict import predict_table
    from attribute_model.text import prepare_text
    from attribute_model.train import train
    from author_encoder.predict import encode_store
    from author_encoder.store import build
    rust("extractor", "claims", "run", "claim_extraction.log")
    rust("extractor", "claims", "flairs", "claim_extraction.log")
    rust("consolidator", "consolidate", "run", "consolidation.log")
    build()
    encode_store()
    prepare(data())
    train(data(), model())
    predict_table(model())
    prepare_text(text_data(), data())
    train(text_data(), text_model(), TEXT_PARAMETERS)


@timed
def run(start, end, loading, deriving):
    if loading:
        load(start, end)
    if deriving:
        derive()
