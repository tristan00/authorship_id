import json

import psycopg

from database import DSN, MONTH

from . import LOG, timed
from .config import ANNOTATIONS, READABLE, SAMPLE_MAX_BYTES, SAMPLE_PERCENT, SAMPLE_TEXTS, SPLITS
from .labels import split

TEXTS = f"SELECT record_id, text FROM texts TABLESAMPLE SYSTEM (%s) WHERE text_status = ANY(%s) AND octet_length(text) <= %s AND {MONTH} = %s ORDER BY random()"
WIDTHS = {name: upper - lower for (name, upper), lower in zip(SPLITS, (0, *(upper for _, upper in SPLITS)))}


@timed
def sample(month, names, splits):
    taken = {json.loads(line)["id"] for path in (ANNOTATIONS / month).glob("*/records.jsonl") for line in open(path, encoding="utf-8")}
    groups = {name: [] for name in splits} if splits else {None: []}
    need = SAMPLE_TEXTS * len(names)
    share = min(WIDTHS[name] for name in splits) / 100 if splits else 1
    LOG.info("sample taken=%d groups=%s need=%d percent=%s", len(taken), list(groups), need, SAMPLE_PERCENT * len(names) / share)
    with psycopg.connect(DSN) as conn, conn.cursor("sample") as cursor:
        cursor.itersize = 10_000
        cursor.execute(TEXTS, [SAMPLE_PERCENT * len(names) / share, list(READABLE), SAMPLE_MAX_BYTES, month])
        for record_id, text in cursor:
            group = groups.get(split(record_id) if splits else None)
            if group is not None and len(group) < need and record_id not in taken:
                group.append((record_id, text))
                if all(len(rows) == need for rows in groups.values()):
                    break
    if short := {key: len(rows) for key, rows in groups.items() if len(rows) < need}:
        raise ValueError(f"sample found fewer than {need} texts: {short}")
    for index, name in enumerate(names):
        (ANNOTATIONS / month / name).mkdir(parents=True)
        rows = [row for group in groups.values() for row in group[index::len(names)]]
        (ANNOTATIONS / month / name / "records.jsonl").write_text("".join(json.dumps({"id": i, "text": t}, ensure_ascii=False) + "\n" for i, t in rows), encoding="utf-8")
