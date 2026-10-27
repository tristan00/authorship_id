import json
import sqlite3
import threading
import time
from functools import lru_cache

import numpy as np

from . import LOG, timed
from .config import DIMENSIONS, TEXTS_PER_USER, VECTOR_STORE


def connect(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


@timed
def status(path=VECTOR_STORE):
    if not path.is_file():
        return {"status": "not_built", "users": 0, "encoded": 0}
    with connect(path) as conn:
        return json.loads(conn.execute("SELECT value FROM metadata WHERE key='state'").fetchone()[0])


class VectorStore:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.signature = None
        self.authors = None
        self.positions = None
        self.vectors = None

    @timed
    def load(self):
        signature = self.path.stat().st_mtime_ns
        with self.lock:
            if signature == self.signature:
                return
            with connect(self.path) as conn:
                metadata = json.loads(conn.execute("SELECT value FROM metadata WHERE key='state'").fetchone()[0])
                if metadata["status"] != "ready":
                    raise ValueError("Vector store is not ready")
                count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
                vectors = np.empty((count, DIMENSIONS), dtype=np.float32)
                authors = []
                for index, (author, packed) in enumerate(conn.execute("SELECT author, vector FROM users ORDER BY author")):
                    if packed is None or len(packed) != DIMENSIONS * 4:
                        raise ValueError("Incomplete or invalid user vector")
                    vectors[index] = np.frombuffer(packed, dtype="<f4")
                    authors.append(author)
            if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1., atol=0.002):
                raise ValueError("User vectors must be finite and normalized")
            vectors.setflags(write=False)
            self.authors, self.positions, self.vectors = authors, {name: index for index, name in enumerate(authors)}, vectors
            self.signature = signature
            LOG.info("vector store loaded users=%d bytes=%d", count, vectors.nbytes)

    @timed
    def search(self, author, limit=50):
        if not 1 <= limit <= 200:
            raise ValueError("Similarity result limit must be between 1 and 200")
        self.load()
        if author not in self.positions:
            return None
        tick = time.perf_counter()
        position = self.positions[author]
        scores = np.einsum("ij,j->i", self.vectors, self.vectors[position], optimize=False)
        scores[position] = -np.inf
        count = min(limit, len(scores) - 1)
        if count < 1:
            return []
        selected = np.argpartition(-scores, count - 1)[:count]
        selected = selected[np.lexsort((selected, -scores[selected]))]
        result = [{"author": self.authors[index], "similarity": float(np.clip(scores[index], -1, 1))} for index in selected]
        LOG.info("vector search users=%d matches=%d seconds=%.4f", len(scores), len(result), time.perf_counter() - tick)
        return result

    @timed
    def vector(self, author):
        with connect(self.path) as conn:
            row = conn.execute("SELECT usable_texts, sample_ids, vector FROM users WHERE author=?", [author]).fetchone()
        if row is None or row[2] is None:
            return None
        return {"author": author, "usable_texts": row[0], "sampled_texts": TEXTS_PER_USER, "sample_ids": json.loads(row[1]), "dimensions": DIMENSIONS, "vector": np.frombuffer(row[2], dtype="<f4").tolist()}


@lru_cache(maxsize=1)
def store(path=VECTOR_STORE):
    return VectorStore(path)
