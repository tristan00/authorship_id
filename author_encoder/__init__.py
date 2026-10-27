import logging
import re
import unicodedata

import orjson

from reddit_dumps import timed

LOG = logging.getLogger("author_encoder")
__all__ = ["LOG", "clean", "timed", "write_json"]


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    temporary.replace(path)


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(?m)^\s*>.*$", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", " URL ", text, flags=re.I)
    text = re.sub(r"(?<!\w)/?[ur]/[\w-]+", " MENTION ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()
