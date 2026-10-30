import psycopg
import torch
from psycopg.rows import dict_row

from database import DSN

from . import LOG, timed
from .config import DATA, MODEL, validate
from .data import prepare, source
from .predict import predict_table
from .train import train


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
    artifact = torch.load(MODEL, map_location="cpu", weights_only=True) if MODEL.exists() else None
    result = {"months": list(expected["months"]), "consolidation": expected["consolidation"]}
    if artifact is None or list(artifact["targets"].items()) != list(targets.items()) or artifact["source"] != expected:
        LOG.info("attribute model retrains for months=%s consolidation=%s", result["months"], result["consolidation"])
        result["prepared"] = prepare(DATA, targets)
        trained = train(DATA, MODEL, targets)
        model_id = result["model_id"] = trained["model_id"]
        result["validation_score"] = trained["validation_score"]
    else:
        model_id = artifact["model_id"]
        LOG.info("attribute model matches the consolidation")
    if predicted == model_id:
        LOG.info("attribute predictions match the model")
    else:
        result["predictions"] = predict_table(MODEL, targets)
    return result
