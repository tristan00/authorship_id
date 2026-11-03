import calendar
import json
import threading
from datetime import datetime, timezone
from itertools import product

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from attribute_model.config import columns, read_targets
from database import DSN, NO_AUTHOR

from . import timed
from .config import ACTIVITY_TIMEOUT, KNOWN, PARENTS, POOL_MAX, POOL_MIN, POOL_WAIT, SEARCH, SEARCH_INPUT, SEARCH_VARIANT_CHARS, SESSION, SIMILAR, STARTS, WINDOW

POOL = ConnectionPool(DSN, min_size=POOL_MIN, max_size=POOL_MAX, timeout=POOL_WAIT, open=False, check=ConnectionPool.check_connection,
                      kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None, "options": SESSION})
PREDICTING = threading.Lock()

FIELDS = "record_id, record_type, author, subreddit, created_utc, text_status, text_sha256"
TOP_END = "\U0010FFFF"
AUTHOR_BRANCH = "(SELECT account AS author FROM author_predictions WHERE account >= %s AND account <= %s AND account ILIKE %s ORDER BY account LIMIT %s)"
SUBREDDIT_SKIP = """WITH RECURSIVE found AS (
    (SELECT subreddit FROM records WHERE subreddit >= %(low)s AND subreddit <= %(high)s ORDER BY subreddit LIMIT 1)
    UNION ALL
    SELECT (SELECT r.subreddit FROM records r WHERE r.subreddit > found.subreddit AND r.subreddit <= %(high)s ORDER BY r.subreddit LIMIT 1)
    FROM found WHERE found.subreddit IS NOT NULL
) SELECT subreddit FROM found WHERE subreddit IS NOT NULL LIMIT %(limit)s"""
PARENT_CHAIN = f"""WITH RECURSIVE chain AS (
    SELECT {FIELDS}, parent_id, 1 AS depth FROM records WHERE record_id = %(parent)s
    UNION ALL
    SELECT r.record_id, r.record_type, r.author, r.subreddit, r.created_utc, r.text_status, r.text_sha256, r.parent_id, chain.depth + 1
    FROM chain JOIN records r ON r.record_id = chain.parent_id WHERE chain.depth < %(levels)s
) SELECT * FROM chain ORDER BY depth DESC"""
CONSOLIDATED = """SELECT EXISTS (SELECT FROM consolidation WHERE months = (SELECT array_agg(month ORDER BY month) FROM months)
    AND started_at > (SELECT max(extracted_at) FROM months)) AS current"""
HOURS = "SELECT created_utc / 3600 AS hour, count(*) AS texts FROM records WHERE {} = %s GROUP BY 1"
AUTHOR_WHERE = """SELECT subreddit, count(*) AS texts FROM (SELECT subreddit FROM records WHERE author = %s ORDER BY created_utc DESC LIMIT %s) newest
    GROUP BY subreddit ORDER BY texts DESC, subreddit"""
SUBREDDIT_WHO = """SELECT author, count(*) AS texts FROM (SELECT author FROM records WHERE subreddit = %s ORDER BY created_utc DESC LIMIT %s) newest
    GROUP BY author ORDER BY texts DESC, author"""


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class Unavailable(Exception):
    pass


def require_author(conn, name):
    found = conn.execute("SELECT texts, posts, first_seen, last_seen FROM author_counts WHERE author = %s", [name]).fetchone()
    if found is None:
        raise NotFound(f"No author is named {name}. Author names are case sensitive.")
    return found


def require_subreddit(conn, name):
    found = conn.execute("SELECT texts, first_seen, last_seen FROM subreddit_counts WHERE subreddit = %s", [name]).fetchone()
    if found is None:
        raise NotFound(f"No subreddit is named {name}.")
    return found


def slow(conn, query, params):
    with conn.transaction():
        conn.execute(f"SET LOCAL statement_timeout = {ACTIVITY_TIMEOUT}")
        return conn.execute(query, params).fetchall()


def bodies_of(conn, rows):
    hashes = list({row["text_sha256"] for row in rows})
    return {row["text_sha256"]: row["text"] for row in conn.execute("SELECT text_sha256, text FROM bodies WHERE text_sha256 = ANY(%s)", [hashes])}


def split_text(row, text):
    if row["record_type"] == "post":
        title, _, body = text.partition("\n\n")
        return title, body
    return "", text


def full(conn, rows):
    bodies = bodies_of(conn, rows)
    shaped = []
    for row in rows:
        title, body = split_text(row, bodies.get(row["text_sha256"], ""))
        shaped.append({"record_id": row["record_id"], "type": row["record_type"], "author": row["author"], "author_page": row["author"] not in NO_AUTHOR,
                       "subreddit": row["subreddit"], "created_utc": row["created_utc"], "status": row["text_status"], "title": title, "body": body})
    return shaped


def claims_check(rows, consolidated):
    pending = [row["month"] for row in rows if row["extracted_at"] is None]
    if pending:
        return {"name": "Claims", "current": False, "detail": "Claims have not been extracted for " + ", ".join(pending) + "."}
    if not consolidated:
        return {"name": "Claims", "current": False, "detail": "Claims were extracted after the last consolidation, so stated attributes are behind."}
    return {"name": "Claims", "current": True, "detail": "Claims are consolidated across every loaded month."}


def predictions_check(published, run, loaded, protocol, targets):
    if published is None:
        return {"name": "Predictions", "current": False, "detail": "No predictions are published."}
    source, problems = published["source"], []
    if run is None or source["consolidation"] != run["run_id"]:
        problems.append("Predictions predate the current claims.")
    if source["months"] != loaded:
        problems.append("Predictions were made for different months than are loaded.")
    if source["protocol"] != protocol:
        problems.append("Predictions were made with a different author vector recipe.")
    if published["targets"] != targets:
        problems.append("The list of attributes to predict has changed since these predictions were made.")
    return {"name": "Predictions", "current": not problems, "detail": " ".join(problems) or "Predictions match the current claims."}


def vectors_check(stored, encoded, loaded):
    problems = []
    if encoded != loaded:
        problems.append("Text vectors do not cover the loaded months.")
    if stored is None:
        problems.append("Author vectors are missing or were built with a different recipe.")
    elif stored["months"] != loaded:
        problems.append("Author vectors do not cover the loaded months.")
    return {"name": "Vectors", "current": not problems, "detail": " ".join(problems) or "Text and author vectors cover every loaded month."}


def counts_check(counted, loaded):
    if counted != list(loaded):
        return {"name": "Counts", "current": False, "detail": "Author and subreddit counts do not cover the loaded months."}
    return {"name": "Counts", "current": True, "detail": "Author and subreddit counts cover every loaded month."}


@timed
def status():
    import lance

    from author_encoder.config import TEXT_STORE, VECTOR_STORE
    from author_encoder.index import PROTOCOL, source
    from author_encoder.texts import MONTHS

    with POOL.connection() as conn:
        rows = conn.execute("SELECT month, loaded_at, extracted_at FROM months ORDER BY month").fetchall()
        consolidated = conn.execute(CONSOLIDATED).fetchone()["current"]
        run = conn.execute("SELECT run_id::text AS run_id FROM consolidation").fetchone()
        published = conn.execute("SELECT source, targets FROM prediction").fetchone()
        counted = conn.execute("SELECT months FROM counted").fetchone()["months"]
    loaded = {row["month"]: str(row["loaded_at"]) for row in rows}
    encoded = json.loads(lance.dataset(TEXT_STORE).schema.metadata[MONTHS])
    return {"months": list(loaded), "checks": [claims_check(rows, consolidated), predictions_check(published, run, loaded, json.loads(PROTOCOL), read_targets()),
                                               vectors_check(source(VECTOR_STORE), encoded, loaded), counts_check(counted, loaded)]}


def common(conn):
    return {key: conn.execute(f"SELECT {key} AS name, texts FROM {key}_counts ORDER BY texts DESC, {key} LIMIT %s", [KNOWN]).fetchall() for key in ("author", "subreddit")}


def ranked(names, query, known):
    folded = query.lower()
    rank = {row["name"]: index for index, row in enumerate(row for row in known if row["name"].lower().startswith(folded))}
    return sorted(set(names) | set(rank), key=lambda name: (name.lower() != folded, rank.get(name, len(rank)), len(name), name.lower()))[:SEARCH]


@timed
def starts():
    with POOL.connection() as conn:
        found = common(conn)
    return {"authors": found["author"][:STARTS], "subreddits": found["subreddit"][:STARTS]}


def case_variants(text):
    return sorted({"".join(parts) for parts in product(*({char.lower(), char.upper()} for char in text[:SEARCH_VARIANT_CHARS]))})


def author_hits(conn, query):
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    patterns = [escaped + "%"] if len(query) <= SEARCH_VARIANT_CHARS else [escaped + "%", escaped]
    pairs = [(variant, pattern) for variant in case_variants(query) for pattern in patterns]
    params = [value for variant, pattern in pairs for value in (variant, variant + TOP_END, pattern, SEARCH)]
    names = {row["author"] for row in conn.execute(" UNION ALL ".join([AUTHOR_BRANCH] * len(pairs)), params)}
    names |= {row["author"] for row in conn.execute("SELECT author FROM author_counts WHERE author = %s", [query])}
    return names


def subreddit_hits(conn, query):
    return [row["subreddit"] for row in conn.execute(SUBREDDIT_SKIP, {"low": query, "high": query + TOP_END, "limit": SEARCH})]


@timed
def search(query):
    query = query.strip()
    if not query or len(query) > SEARCH_INPUT:
        return {"authors": [], "subreddits": []}
    with POOL.connection() as conn:
        known = common(conn)
        return {"authors": ranked(author_hits(conn, query), query, known["author"]), "subreddits": ranked(subreddit_hits(conn, query.lower()), query, known["subreddit"])}


def detail(prediction, attribute, kind):
    stored = columns(attribute, kind)
    return {"value": prediction[stored[0]]} | {column.removeprefix(attribute + "_"): prediction[column] for column in stored[1:]}


@timed
def author(name):
    with POOL.connection() as conn:
        require_author(conn, name)
        claims = conn.execute("SELECT attribute::text AS attribute, value, support, share FROM author_claims WHERE author = %s", [name]).fetchall()
        published = conn.execute("SELECT targets, interval_mass FROM prediction").fetchone()
        prediction = conn.execute("SELECT * FROM author_predictions WHERE account = %s", [name]).fetchone()
    targets = published["targets"]
    predicted = {attribute: detail(prediction, attribute, kind) for attribute, kind in targets.items()} if prediction else {}
    stated = {claim["attribute"]: claim for claim in claims}
    rows = [{"attribute": attribute, "kind": targets.get(attribute), "stated": stated.get(attribute), "predicted": predicted.get(attribute)} for attribute in sorted(stated.keys() | predicted.keys())]
    return {"name": name, "attributes": rows, "has_prediction": bool(predicted), "interval_mass": published["interval_mass"]}


def when(conn, column, name):
    months = {row["month"]: 0 for row in conn.execute("SELECT month FROM months ORDER BY month")}
    hours, days = [0] * 24, [0] * 7
    for row in slow(conn, HOURS.format(column), [name]):
        moment = datetime.fromtimestamp(row["hour"] * 3600, timezone.utc)
        hours[moment.hour] += row["texts"]
        days[moment.weekday()] += row["texts"]
        months[moment.strftime("%Y-%m")] += row["texts"]
    return {"hours": [{"hour": hour, "texts": texts} for hour, texts in enumerate(hours)],
            "weekdays": [{"day": calendar.day_name[day], "texts": texts} for day, texts in enumerate(days)],
            "months": [{"month": month, "texts": texts} for month, texts in months.items()]}


@timed
def author_activity(name):
    with POOL.connection() as conn:
        return require_author(conn, name) | when(conn, "author", name)


@timed
def author_subreddits(name):
    with POOL.connection() as conn:
        texts = require_author(conn, name)["texts"]
        rows = slow(conn, AUTHOR_WHERE, [name, WINDOW])
    return {"texts": texts, "counted": min(texts, WINDOW), "subreddits": rows}


@timed
def author_similar(name):
    with POOL.connection() as conn:
        require_author(conn, name)
    import numpy as np

    from author_encoder.config import USER_SEARCH
    from author_encoder.index import users, vector
    found = vector(name)
    if found is None:
        return {"similar": None}
    table = users().to_table(nearest={"column": "vector", "q": np.asarray(found["vector"], dtype=np.float32), "k": SIMILAR + 1, **USER_SEARCH}, columns=["author", "usable_texts", "_distance"])
    rows = [{"author": row["author"], "usable_texts": row["usable_texts"], "similarity": 1 - row["_distance"]} for row in table.to_pylist() if row["author"] != name]
    return {"similar": rows[:SIMILAR]}


@timed
def subreddit_activity(name):
    name = name.lower()
    with POOL.connection() as conn:
        return require_subreddit(conn, name) | when(conn, "subreddit", name)


@timed
def subreddit_authors(name):
    name = name.lower()
    with POOL.connection() as conn:
        texts = require_subreddit(conn, name)["texts"]
        rows = slow(conn, SUBREDDIT_WHO, [name, WINDOW])
    return {"texts": texts, "counted": min(texts, WINDOW), "authors": [row | {"author_page": row["author"] not in NO_AUTHOR} for row in rows]}


def chain_end(row, chain):
    if not row["parent_id"]:
        return None
    if not chain or (chain[0]["parent_id"] and len(chain) < PARENTS):
        return "outside"
    return "capped" if chain[0]["parent_id"] else None


@timed
def text(record_id):
    with POOL.connection() as conn:
        rows = conn.execute(f"SELECT {FIELDS}, parent_id, link_id FROM records WHERE record_id = %s", [record_id]).fetchall()
        if not rows:
            raise NotFound(f"No text has the id {record_id}.")
        row = rows[0]
        chain = conn.execute(PARENT_CHAIN, {"parent": row["parent_id"], "levels": PARENTS}).fetchall() if row["parent_id"] else []
        post = None
        if row["record_type"] == "comment":
            found = conn.execute(f"SELECT {FIELDS} FROM records WHERE record_id = %s", [row["link_id"]]).fetchall()
            post = {"record_id": found[0]["record_id"], "title": full(conn, found)[0]["title"]} if found else None
        return full(conn, [row])[0] | {"parents": full(conn, chain), "post": post, "chain_end": chain_end(row, chain)}


@timed
def predict(body):
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise BadRequest("Send a JSON object with a text string.")
    from attribute_model.config import TEXT_MODEL
    from attribute_model.text import predict_text
    with PREDICTING:
        try:
            return predict_text(TEXT_MODEL, read_targets(), body["text"])
        except (ValueError, RuntimeError) as error:
            raise Unavailable(str(error)) from error
