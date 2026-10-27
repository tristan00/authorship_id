import json

import psycopg

from database import DSN, MONTH

from . import timed
from .config import ANNOTATIONS, READABLE, SAMPLE_MAX_BYTES, SAMPLE_PERCENT, SAMPLE_TEXTS

TEXTS = f"SELECT record_id, text FROM texts TABLESAMPLE SYSTEM (%s) WHERE text_status = ANY(%s) AND octet_length(text) <= %s AND {MONTH} = %s ORDER BY random() LIMIT %s"


@timed
def sample(month, names):
    with psycopg.connect(DSN) as conn:
        rows = conn.execute(TEXTS, [SAMPLE_PERCENT * len(names), list(READABLE), SAMPLE_MAX_BYTES, month, SAMPLE_TEXTS * len(names)]).fetchall()
    for index, name in enumerate(names):
        (ANNOTATIONS / month / name).mkdir(parents=True)
        (ANNOTATIONS / month / name / "records.jsonl").write_text("".join(json.dumps({"id": i, "text": t}, ensure_ascii=False) + "\n" for i, t in rows[index::len(names)]), encoding="utf-8")
