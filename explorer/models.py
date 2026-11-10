import threading

from attribute_model.config import text_model
from attribute_model.text import predict_text
from author_encoder.store import similar
from reddit_dumps import timed

NEIGHBOURS = 20
TEXT_LOCK = threading.Lock()


@timed
def neighbours(name):
    return similar(name, NEIGHBOURS)


@timed
def predict(text):
    with TEXT_LOCK:
        return predict_text(text_model(), text)
