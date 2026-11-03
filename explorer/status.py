import json

import lance

from attribute_model.config import read_targets
from author_encoder.config import TEXT_STORE, VECTOR_STORE
from author_encoder.exact import current
from author_encoder.index import PROTOCOL, source
from author_encoder.texts import MONTHS
from reddit_dumps import timed

from .store import POOL

CONSOLIDATED = """SELECT EXISTS (SELECT FROM consolidation WHERE months = (SELECT array_agg(month ORDER BY month) FROM months)
                                 AND started_at > (SELECT max(extracted_at) FROM months)) AS current"""


def check(name, current, detail):
    return {"name": name, "current": current, "detail": detail}


def listed(months):
    return ", ".join(sorted(months)) if months else "no months"


def compare(name, built, loaded):
    if sorted(built) == sorted(loaded):
        return f"{name} were built from earlier loads of {listed(m for m in loaded if built[m] != loaded[m])}."
    return f"{name} cover {listed(built)}; loaded months are {listed(loaded)}."


@timed
def facts():
    with POOL.connection() as conn:
        return {"months": conn.execute("SELECT month, loaded_at, extracted_at FROM months ORDER BY month").fetchall(),
                "consolidated": conn.execute(CONSOLIDATED).fetchone()["current"],
                "run": conn.execute("SELECT run_id::text AS run_id FROM consolidation ORDER BY started_at DESC LIMIT 1").fetchone(),
                "prediction": conn.execute("SELECT source, targets FROM prediction").fetchone(),
                "counted": conn.execute("SELECT months FROM counted").fetchone()}


def claims(months, consolidated):
    if not months:
        return check("Claims", False, "No months are loaded.")
    missing = [row["month"] for row in months if row["extracted_at"] is None]
    if missing:
        return check("Claims", False, f"Claims are not extracted for {listed(missing)}.")
    if not consolidated:
        return check("Claims", False, "Consolidation is behind the latest claim extraction.")
    return check("Claims", True, f"Claims are extracted and consolidated for all {len(months)} loaded months.")


def predictions(prediction, run, loaded):
    if prediction is None:
        return check("Predictions", False, "No prediction is published.")
    origin = prediction["source"]
    if run is None:
        return check("Predictions", False, "No consolidation run exists.")
    if origin["consolidation"] != run["run_id"]:
        return check("Predictions", False, f"Predictions come from consolidation {origin['consolidation']}; the latest run is {run['run_id']}.")
    if origin["months"] != loaded:
        return check("Predictions", False, compare("Predictions", origin["months"], loaded))
    if origin["protocol"] != json.loads(PROTOCOL):
        return check("Predictions", False, "Predictions were built with a different author vector protocol.")
    if prediction["targets"] != read_targets():
        return check("Predictions", False, "Predictions were built for different targets than targets.json.")
    return check("Predictions", True, f"Predictions match the latest consolidation, the vector protocol, the targets and all {len(loaded)} loaded months.")


def vectors(loaded):
    if not TEXT_STORE.exists():
        return check("Vectors", False, "The text vector store is missing.")
    metadata = lance.dataset(TEXT_STORE).schema.metadata
    if metadata is None or MONTHS not in metadata:
        return check("Vectors", False, "The text vector store records no months.")
    texts = json.loads(metadata[MONTHS])
    if texts != loaded:
        return check("Vectors", False, compare("Text vectors", texts, loaded))
    built = source(VECTOR_STORE)
    if built is None:
        return check("Vectors", False, "The user vector store is missing or was built with a different protocol.")
    if built["months"] != loaded:
        return check("Vectors", False, compare("User vectors", built["months"], loaded))
    if not current():
        return check("Vectors", False, "Exact search data does not match the user vector store.")
    return check("Vectors", True, f"Text and user vectors cover all {len(loaded)} loaded months, and exact search data matches them.")


def counts(counted, loaded):
    if counted is None:
        return check("Counts", False, "No counts are recorded.")
    if counted["months"] != loaded:
        return check("Counts", False, f"Counts cover {listed(counted['months'])}; loaded months are {listed(loaded)}.")
    return check("Counts", True, f"Counts cover all {len(loaded)} loaded months.")


@timed
def checks():
    known = facts()
    loaded = {row["month"]: str(row["loaded_at"]) for row in known["months"]}
    return [claims(known["months"], known["consolidated"]), predictions(known["prediction"], known["run"], loaded), vectors(loaded), counts(known["counted"], list(loaded))]
