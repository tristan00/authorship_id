import threading

import numpy as np

from attribute_model.config import TEXT_MODEL, read_targets
from attribute_model.text import predict_text
from author_encoder.config import USER_SEARCH, VECTOR_STORE
from author_encoder.index import users, vector
from reddit_dumps import timed

NEIGHBOURS = 20
TEXT_LOCK = threading.Lock()


@timed
def neighbours(name):
    if not VECTOR_STORE.exists():
        raise RuntimeError(f"The user vector store {VECTOR_STORE} is missing")
    found = vector(name)
    if found is None:
        return None
    table = users().to_table(nearest={"column": "vector", "q": np.asarray(found["vector"], dtype=np.float32), "k": NEIGHBOURS + 1, **USER_SEARCH},
                             columns=["author", "usable_texts", "_distance"])
    rows = zip(table.column("author").to_pylist(), table.column("usable_texts").to_pylist(), table.column("_distance").to_pylist())
    return [{"author": author, "similarity": 1 - distance, "usable_texts": usable} for author, usable, distance in rows if author != name][:NEIGHBOURS]


@timed
def predict(text):
    with TEXT_LOCK:
        return predict_text(TEXT_MODEL, read_targets(), text)
