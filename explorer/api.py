import itertools
from collections import Counter
from datetime import datetime, timezone

from database import NO_AUTHOR
from reddit_dumps import timed

from . import models, status, store

QUERY_LIMIT = 64
CASED_PREFIX = 3
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class Failure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require_author(name):
    if name in NO_AUTHOR:
        raise Failure(404, f"'{name}' is a placeholder, not an author")
    if store.author_counts(name) is None:
        raise Failure(404, f"No author named '{name}'")


def require_subreddit(name):
    found = store.subreddit_counts(name)
    if found is None:
        raise Failure(404, f"No subreddit named '{name}'")
    return found


def escape_like(text):
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def case_variants(text):
    forms = [sorted({form for form in (char.lower(), char.upper(), char) if len(form) == 1}) for char in text]
    return ["".join(chosen) for chosen in itertools.product(*forms)]


def month_range(first, last):
    year, month = map(int, first.split("-"))
    while f"{year:04d}-{month:02d}" <= last:
        yield f"{year:04d}-{month:02d}"
        year, month = year + month // 12, month % 12 + 1


def counted(row, fields):
    return {field: 0 if row is None else row[field] for field in fields}


def when(rows, fields):
    found = {dimension: {row[dimension]: row for row in rows if row["dimension"] == dimension} for dimension in ("hour", "weekday", "month")}
    months = found["month"]
    return {"hour": [{"hour": hour} | counted(found["hour"].get(hour), fields) for hour in range(24)],
            "weekday": [{"weekday": WEEKDAYS[day - 1]} | counted(found["weekday"].get(day), fields) for day in range(1, 8)],
            "month": [{"month": month} | counted(months.get(month), fields) for month in (month_range(min(months), max(months)) if months else ())]}


def folded(buckets):
    sums = {"hour": Counter(), "weekday": Counter(), "month": Counter()}
    for bucket in buckets:
        moment = datetime.fromtimestamp(bucket["bucket"] * 3600, timezone.utc)
        sums["hour"][moment.hour] += bucket["texts"]
        sums["weekday"][moment.isoweekday()] += bucket["texts"]
        sums["month"][moment.strftime("%Y-%m")] += bucket["texts"]
    return [{"dimension": dimension, dimension: key, "texts": texts} for dimension, counted in sums.items() for key, texts in counted.items()]


@timed
def home():
    return {"subreddits": store.top_subreddits(), "authors": store.top_authors()}


@timed
def data_status():
    return {"checks": status.checks()}


@timed
def search(params):
    values = params.get("q")
    if values is None:
        raise Failure(400, "The search query parameter q is missing")
    if len(values) != 1:
        raise Failure(400, "Give the search query parameter q once")
    query = values[0].strip()
    if not query:
        raise Failure(400, "The search query is empty")
    if len(query) > QUERY_LIMIT:
        raise Failure(400, f"The search query is longer than {QUERY_LIMIT} characters")
    authors = [] if query in NO_AUTHOR else store.find_authors(query, case_variants(query[:CASED_PREFIX]), escape_like(query) + "%")
    return {"query": query, "authors": authors, "subreddits": store.find_subreddits(query.lower())}


@timed
def profile(name):
    require_author(name)
    claims = store.stated(name)
    targets = store.prediction_targets()
    row = None if targets is None else store.predicted(name, list(targets))
    if row is None:
        return {"author": name, "published": False, "attributes": [{"name": key, "stated": claims[key]} for key in sorted(claims)]}
    return {"author": name, "published": True,
            "attributes": [{"name": key, "stated": claims.get(key), "predicted": row[key] if key in targets else None} for key in sorted(set(targets) | set(claims))]}


@timed
def author_patterns(name):
    require_author(name)
    rows = store.author_patterns(name)
    total = next(row for row in rows if row["dimension"] == "total")
    where = sorted(({"subreddit": row["subreddit"], "texts": row["texts"], "posts": row["posts"]} for row in rows if row["dimension"] == "where"),
                   key=lambda entry: (-entry["texts"], entry["subreddit"]))
    return {"author": name, "totals": {"texts": total["texts"], "posts": total["posts"], "subreddits": total["spread"],
                                       "first_seen": total["first_seen"], "last_seen": total["last_seen"]},
            "where": where} | when(rows, ("texts", "posts"))


@timed
def subreddit_patterns(name):
    total = require_subreddit(name)
    return {"subreddit": name, "totals": {"texts": total["texts"], "posts": total["posts"], "first_seen": total["first_seen"], "last_seen": total["last_seen"]}} | when(folded(store.subreddit_patterns(name)), ("texts",))


@timed
def similar(name):
    require_author(name)
    try:
        found = models.neighbours(name)
    except RuntimeError as error:
        raise Failure(503, str(error))
    return {"author": name, "vector": found is not None, "similar": [] if found is None else found}


@timed
def predict(body):
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise Failure(400, "Send a JSON object with a string field text")
    try:
        result = models.predict(body["text"])
    except (ValueError, RuntimeError) as error:
        raise Failure(503, str(error))
    if result["status"] == "empty":
        return {"status": "empty"}
    return {"status": "ready", "tokens": result["tokens"], "truncated": result["truncated"],
            "attributes": [{"name": key, "predicted": result["attributes"][key]["value"]} for key in sorted(result["attributes"])]}


def dispatch(method, parts, params, body):
    match method, parts:
        case "GET", ["home"]:
            return home()
        case "GET", ["status"]:
            return data_status()
        case "GET", ["search"]:
            return search(params)
        case "GET", ["author", name, "profile"]:
            return profile(name)
        case "GET", ["author", name, "patterns"]:
            return author_patterns(name)
        case "GET", ["author", name, "similar"]:
            return similar(name)
        case "GET", ["subreddit", name, "patterns"]:
            return subreddit_patterns(name)
        case "POST", ["predict"]:
            return predict(body)
    raise Failure(404, f"No endpoint {method} /api/{'/'.join(parts)}")
