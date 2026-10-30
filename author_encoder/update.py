import json
import os
import shutil
from contextlib import contextmanager
from datetime import timedelta

import lance
import psycopg

from database import DSN

from . import LOG, timed
from .config import TEXT_STORE, VECTOR_STORE, VECTOR_WORK
from .index import build
from .lock import index_lock
from .texts import MONTHS, write


@contextmanager
def scratch():
    shutil.rmtree(VECTOR_WORK, ignore_errors=True)
    VECTOR_WORK.mkdir(parents=True)
    saved = {name: os.environ.get(name) for name in ("TMP", "TEMP")}
    os.environ.update(TMP=str(VECTOR_WORK), TEMP=str(VECTOR_WORK))
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(VECTOR_WORK, ignore_errors=True)


@timed
def cleanup(*paths):
    return {path.name: str(lance.dataset(path).cleanup_old_versions(older_than=timedelta(0), delete_unverified=True)) for path in paths if path.exists()}


@timed
def months():
    with psycopg.connect(DSN) as conn:
        return {month: str(loaded) for month, loaded in conn.execute("SELECT month, loaded_at FROM months ORDER BY month")}


@timed
def update(device="cuda"):
    with index_lock(TEXT_STORE), scratch():
        loaded = months()
        LOG.info("text vector update months=%s", loaded)
        texts = write(loaded, TEXT_STORE, device)
        cleaned = cleanup(TEXT_STORE)
    return {"months": loaded, "texts": texts, "cleanup": cleaned}


@timed
def users():
    with index_lock(TEXT_STORE), scratch():
        loaded = months()
        encoded = json.loads(lance.dataset(TEXT_STORE).schema.metadata[MONTHS])
        if encoded != loaded:
            raise ValueError(f"Text vectors cover {encoded}, not the loaded months {loaded}; run update first")
        LOG.info("user vector update months=%s", loaded)
        built = build(loaded, VECTOR_STORE, TEXT_STORE)
        cleaned = cleanup(VECTOR_STORE)
    return {"months": loaded, "users": built, "cleanup": cleaned}
