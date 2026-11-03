import threading

from attribute_model.config import TEXT_MODEL, read_targets
from attribute_model.text import predict_text
from author_encoder.config import VECTOR_STORE
from author_encoder.exact import nearest
from reddit_dumps import timed

NEIGHBOURS = 20
TEXT_LOCK = threading.Lock()
SEARCH_LOCK = threading.Lock()


@timed
def neighbours(name):
    if not VECTOR_STORE.exists():
        raise RuntimeError(f"The user vector store {VECTOR_STORE} is missing")
    with SEARCH_LOCK:
        return nearest(name, NEIGHBOURS)


@timed
def predict(text):
    with TEXT_LOCK:
        return predict_text(TEXT_MODEL, read_targets(), text)
