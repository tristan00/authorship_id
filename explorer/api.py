import datetime
import itertools

from author_encoder import clean
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


def day_range(first, last):
    day, end = datetime.date.fromisoformat(first), datetime.date.fromisoformat(last)
    while day <= end:
        yield day.isoformat()
        day += datetime.timedelta(days=1)


def counted(row, fields):
    return {field: 0 if row is None else row[field] for field in fields}


def when(rows, fields):
    found = {dimension: {row[dimension]: row for row in rows if row["dimension"] == dimension} for dimension in ("hour", "weekday", "day")}
    days = found["day"]
    return {"hour": [{"hour": hour} | counted(found["hour"].get(hour), fields) for hour in range(24)],
            "weekday": [{"weekday": WEEKDAYS[day - 1]} | counted(found["weekday"].get(day), fields) for day in range(1, 8)],
            "day": [{"day": day} | counted(days.get(day), fields) for day in (day_range(min(days), max(days)) if days else ())]}


def single(params, name):
    values = params.get(name, [])
    if len(values) > 1:
        raise Failure(400, f"Give the query parameter {name} at most once")
    return values[0].strip() if values and values[0].strip() else None


def date(params, name):
    value = single(params, name)
    if value is None:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise Failure(400, f"{name} must be a date like 2026-05-01")


def midnight(day):
    return int(datetime.datetime.combine(day, datetime.time(), datetime.UTC).timestamp())


def filters(params):
    found = {}
    kind = single(params, "type")
    if kind is not None:
        if kind not in ("post", "comment"):
            raise Failure(400, "type must be post or comment")
        found["type"] = kind
    for name in ("subreddit", "author"):
        value = single(params, name)
        if value is not None:
            found[name] = value
    start, end = date(params, "from"), date(params, "to")
    if start is not None:
        found["start"] = midnight(start)
    if end is not None:
        found["end"] = midnight(end + datetime.timedelta(days=1))
    before = single(params, "before")
    if before is not None:
        at, _, record = before.partition(":")
        if not at.isdigit() or not record:
            raise Failure(400, "before must look like <unix seconds>:<record id>")
        found |= {"before_at": int(at), "before_id": record}
    return found


def page(records):
    return {"records": records, "next": f"{records[-1]['at']}:{records[-1]['record_id']}" if len(records) == store.PAGE else None}


@timed
def home():
    return {"subreddits": store.top_subreddits(), "authors": store.top_authors()} | store.overview()


@timed
def author_summary(name):
    require_author(name)
    return store.author_counts(name) | {"subreddits": store.author_subreddits(name)}


@timed
def subreddit_summary(name):
    return require_subreddit(name)


@timed
def author_records(name, params):
    require_author(name)
    return page(store.author_records(name, filters(params)))


@timed
def subreddit_records(name, params):
    require_subreddit(name)
    return page(store.subreddit_records(name, filters(params)))


@timed
def subreddit_authors(name, params):
    require_subreddit(name)
    return {"subreddit": name, "authors": store.subreddit_authors(name, filters(params))}


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
    row = None if targets is None else store.predicted(name, targets)
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
    require_subreddit(name)
    rows = store.subreddit_patterns(name)
    total = next(row for row in rows if row["dimension"] == "total")
    return {"subreddit": name, "totals": {"texts": total["texts"], "posts": total["posts"], "first_seen": total["first_seen"], "last_seen": total["last_seen"]}} | when(rows, ("texts", "posts"))


@timed
def similar(name):
    require_author(name)
    found = models.neighbours(name)
    return {"author": name, "vector": found is not None,
            "similar": [] if found is None else [{"author": row["author"], "similarity": round(row["similarity"], 4), "usable_texts": row["texts"]} for row in found["neighbours"]]}


@timed
def predict(body):
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise Failure(400, "Send a JSON object with a string field text")
    if not clean(body["text"]):
        return {"status": "empty"}
    result = models.predict(body["text"])
    return {"status": "ready", "tokens": result["tokens"], "truncated": result["truncated"],
            "attributes": [{"name": key, "predicted": result["attributes"][key]} for key in sorted(result["attributes"])]}


def dispatch(method, parts, params, body):
    match method, parts:
        case "GET", ["home"]:
            return home()
        case "GET", ["status"]:
            return data_status()
        case "GET", ["search"]:
            return search(params)
        case "GET", ["author", name, "summary"]:
            return author_summary(name)
        case "GET", ["author", name, "records"]:
            return author_records(name, params)
        case "GET", ["subreddit", name, "summary"]:
            return subreddit_summary(name)
        case "GET", ["subreddit", name, "records"]:
            return subreddit_records(name, params)
        case "GET", ["subreddit", name, "authors"]:
            return subreddit_authors(name, params)
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
