import json

import psycopg

from database import DSN, bounds

from . import LOG, timed
from .config import ANNOTATIONS, READABLE, SAMPLE_MAX_BYTES, SAMPLE_PERCENT, SAMPLE_TEXTS, SPLITS
from .labels import split

TEXTS = """SELECT r.record_id, b.text FROM (SELECT record_id, text_sha256 FROM records TABLESAMPLE SYSTEM (%s) WHERE text_status = ANY(%s)
           AND created_utc >= %s AND created_utc < %s ORDER BY random()) r CROSS JOIN LATERAL (SELECT text FROM bodies b WHERE b.text_sha256 = r.text_sha256 AND octet_length(b.text) <= %s) b"""
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
        cursor.execute(TEXTS, [SAMPLE_PERCENT * len(names) / share, list(READABLE), *bounds(month), SAMPLE_MAX_BYTES])
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
