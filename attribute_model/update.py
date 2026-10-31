import psycopg
import torch
from psycopg.rows import dict_row

from database import DSN

from . import LOG, timed
from .config import DATA, MODEL, TEXT_DATA, TEXT_MODEL, TEXT_PARAMETERS, validate
from .data import prepare, source
from .predict import predict_table
from .text import load_text
from .text import prepare as prepare_text
from .train import train


def stale(path, targets, expected):
    if not path.exists():
        return True
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    return list(artifact["targets"].items()) != list(targets.items()) or artifact["source"] != expected


def published(conn):
    if conn.execute("SELECT to_regclass('prediction') AS name").fetchone()["name"] is None:
        return None
    row = conn.execute("SELECT model_id::text FROM prediction").fetchone()
    return row and row["model_id"]


@timed
def update(targets):
    targets = validate(targets)
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        expected, predicted = source(conn), published(conn)
    result = {"months": list(expected["months"]), "consolidation": expected["consolidation"]}
    if stale(MODEL, targets, expected):
        LOG.info("attribute model retrains for months=%s consolidation=%s", result["months"], result["consolidation"])
        result["prepared"] = prepare(DATA, targets)
        trained = train(DATA, MODEL, targets)
        model_id = result["model_id"] = trained["model_id"]
        result["validation_score"] = trained["validation_score"]
    else:
        model_id = torch.load(MODEL, map_location="cpu", weights_only=True)["model_id"]
        LOG.info("attribute model matches the consolidation")
    if stale(TEXT_MODEL, targets, expected):
        result["text_prepared"] = prepare_text(TEXT_DATA, targets)
        result["text_model_id"] = train(TEXT_DATA, TEXT_MODEL, targets, TEXT_PARAMETERS, load_text)["model_id"]
    if predicted == model_id:
        LOG.info("attribute predictions match the model")
    else:
        result["predictions"] = predict_table(MODEL, targets)
    return result
