import json

from author_encoder.predict import vectors_source
from reddit_dumps import timed

from .store import connection, first, rows

PARTS = 256
TABLES = ("months", "extracted_parts", "author_claims", "author_counts", "author_texts_source", "encoded_parts", "author_predictions")


def check(name, current, detail):
    return {"name": name, "current": current, "detail": detail}


def listed(months):
    return ", ".join(sorted(months)) if months else "no months"


@timed
def facts():
    built = {row["name"]: row["changed"] for row in rows("SELECT name, toUnixTimestamp(metadata_modification_time) AS changed FROM system.tables "
                                                        "WHERE database = currentDatabase() AND name IN {names:Array(String)}", {"names": list(TABLES)})}
    months = rows("SELECT month, toString(loaded_at) AS loaded, toUnixTimestamp(loaded_at) AS at FROM months ORDER BY month") if "months" in built else []
    parts = "SELECT count() AS parts, uniqExact({column}) AS sources, any({column}) AS fingerprint, toUnixTimestamp(max(finished_at)) AS finished FROM {table}"
    return {"built": built, "months": {row["month"]: row["loaded"] for row in months}, "loaded": max((row["at"] for row in months), default=0),
            "extracted": first(parts.format(column="build", table="extracted_parts")) if "extracted_parts" in built else None,
            "encoded": first(parts.format(column="source", table="encoded_parts")) if "encoded_parts" in built else None,
            "texts": "author_texts_source" in built,
            "prediction": json.loads(first("SELECT comment FROM system.tables WHERE database = currentDatabase() AND name = 'author_predictions'")["comment"]) if "author_predictions" in built else None}


def complete(name, done):
    if done is None:
        return f"{name} has not run."
    if done["parts"] != PARTS or done["sources"] != 1:
        return f"{name} finished {done['parts']} of {PARTS} parts from {done['sources']} sources."
    return None


def claims(known):
    built, extracted = known["built"], known["extracted"]
    problem = complete("Claim extraction", extracted)
    if problem:
        return check("Claims", False, problem)
    if extracted["finished"] < known["loaded"]:
        return check("Claims", False, "Claim extraction is older than the latest load.")
    if built.get("author_claims", 0) < extracted["finished"]:
        return check("Claims", False, "Consolidation is behind the latest claim extraction.")
    return check("Claims", True, None)


def vectors(known):
    encoded = known["encoded"]
    if not known["texts"]:
        return check("Vectors", False, "Author texts are not built.")
    problem = complete("Vector encoding", encoded)
    if problem:
        return check("Vectors", False, problem)
    ranges = [(row["low"], row["high"]) for row in rows("SELECT low, high FROM encoded_parts ORDER BY part")]
    if vectors_source(connection(), ranges) != encoded["fingerprint"]:
        return check("Vectors", False, "Author vectors were encoded from other author texts or encoder code.")
    if encoded["finished"] < known["loaded"]:
        return check("Vectors", False, "Author vectors are older than the latest load.")
    return check("Vectors", True, None)


def predictions(known):
    prediction, built, months = known["prediction"], known["built"], known["months"]
    if prediction is None:
        return check("Predictions", False, "No prediction is published.")
    source = prediction["source"]["months"]
    if source != months:
        return check("Predictions", False, f"Predictions cover {listed(source)}; loaded months are {listed(months)}.")
    inputs = max(built.get("author_claims", 0), (known["encoded"] or {"finished": 0})["finished"])
    if built["author_predictions"] < inputs:
        return check("Predictions", False, "Predictions are older than the claims or vectors they were trained on.")
    return check("Predictions", True, None)


def counts(known):
    if known["built"].get("author_counts", 0) < known["loaded"]:
        return check("Counts", False, "Counts are missing or older than the latest load.")
    return check("Counts", True, None)


@timed
def checks():
    known = facts()
    if not known["months"]:
        return [check("Months", False, "No months are loaded.")]
    return [check("Months", True, None), claims(known), vectors(known), predictions(known), counts(known)]
