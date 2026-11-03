import json
import re
from itertools import product

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from attribute_model.config import columns, read_targets
from database import DSN, NO_AUTHOR

from . import timed
from .config import CLAIMS, EXCERPT, EXCERPT_READ, GROUPS, PAGE, PARENTS, POOL_MAX, POOL_MIN, POOL_WAIT, POST_SCAN, RECENT, SEARCH, SEARCH_INPUT, SEARCH_VARIANT_CHARS, SESSION, SIMILAR, STARTS

POOL = ConnectionPool(DSN, min_size=POOL_MIN, max_size=POOL_MAX, timeout=POOL_WAIT, open=False, check=ConnectionPool.check_connection,
                      kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None, "options": SESSION})

CURSOR = re.compile(r"(\d{1,15}):(t[13]_[0-9a-z]{1,20})")
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
STATISTICS = """SELECT s.attname, s.most_common_vals::text::text[] AS names, s.most_common_freqs AS shares, c.reltuples
    FROM pg_stats s JOIN pg_class c ON c.oid = 'records'::regclass
    WHERE s.schemaname = 'public' AND s.tablename = 'records' AND s.inherited AND s.attname IN ('author', 'subreddit')"""


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


def cursor_of(before):
    if before is None:
        return None
    match = CURSOR.fullmatch(before)
    if match is None:
        raise BadRequest("That page position is not valid.")
    return int(match[1]), match[2]


def keyset(cursor):
    return ("", []) if cursor is None else (" AND created_utc <= %s AND (created_utc, record_id) < (%s, %s)", [cursor[0], cursor[0], cursor[1]])


def position(row):
    return f"{row['created_utc']}:{row['record_id']}"


def require_author(conn, name):
    if name in NO_AUTHOR or not conn.execute("SELECT EXISTS (SELECT FROM records WHERE author = %s) AS found", [name]).fetchone()["found"]:
        raise NotFound(f"No author is named {name}. Author names are case sensitive.")


def require_subreddit(conn, name):
    if not conn.execute("SELECT EXISTS (SELECT FROM records WHERE subreddit = %s) AS found", [name]).fetchone()["found"]:
        raise NotFound(f"No subreddit is named {name}.")


def bodies_of(conn, rows, length=None):
    hashes = list({row["text_sha256"] for row in rows})
    text = "text" if length is None else f"left(text, {int(length)}) AS text"
    return {row["text_sha256"]: row["text"] for row in conn.execute(f"SELECT text_sha256, {text} FROM bodies WHERE text_sha256 = ANY(%s)", [hashes])}


def split_text(row, text):
    if row["record_type"] == "post":
        title, _, body = text.partition("\n\n")
        return title, body
    return "", text


def base_shape(row):
    return {"record_id": row["record_id"], "type": row["record_type"], "author": row["author"], "author_page": row["author"] not in NO_AUTHOR,
            "subreddit": row["subreddit"], "created_utc": row["created_utc"], "status": row["text_status"]}


def listed(conn, rows):
    bodies = bodies_of(conn, rows, EXCERPT_READ)
    shaped = []
    for row in rows:
        title, body = split_text(row, bodies.get(row["text_sha256"], ""))
        flat = " ".join(body.split())
        shaped.append(base_shape(row) | {"title": title, "excerpt": flat if len(flat) <= EXCERPT else flat[:EXCERPT].rstrip() + "..."})
    return shaped


def full(conn, rows):
    bodies = bodies_of(conn, rows)
    shaped = []
    for row in rows:
        title, body = split_text(row, bodies.get(row["text_sha256"], ""))
        shaped.append(base_shape(row) | {"title": title, "body": body})
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
    loaded = {row["month"]: str(row["loaded_at"]) for row in rows}
    encoded = json.loads(lance.dataset(TEXT_STORE).schema.metadata[MONTHS])
    return {"months": list(loaded), "checks": [claims_check(rows, consolidated), predictions_check(published, run, loaded, json.loads(PROTOCOL), read_targets()),
                                               vectors_check(source(VECTOR_STORE), encoded, loaded)]}


def common(conn):
    found = {"author": [], "subreddit": []}
    for row in conn.execute(STATISTICS).fetchall():
        found[row["attname"]] = [{"name": name, "texts": round(share * row["reltuples"])} for name, share in zip(row["names"], row["shares"]) if name not in NO_AUTHOR]
    return found


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
    if query not in NO_AUTHOR:
        names |= {row["author"] for row in conn.execute("SELECT author FROM records WHERE author = %s LIMIT 1", [query])}
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


@timed
def author(name):
    with POOL.connection() as conn:
        require_author(conn, name)
        claims = conn.execute("SELECT attribute::text AS attribute, value FROM author_claims WHERE author = %s ORDER BY 1 LIMIT %s", [name, CLAIMS]).fetchall()
        published = conn.execute("SELECT targets FROM prediction").fetchone()
        prediction = conn.execute("SELECT * FROM author_predictions WHERE account = %s", [name]).fetchone()
    predicted = {attribute: prediction[columns(attribute, kind)[0]] for attribute, kind in published["targets"].items()} if prediction and published else {}
    stated = {claim["attribute"]: claim["value"] for claim in claims}
    rows = [{"attribute": attribute, "stated": stated.get(attribute), "predicted": predicted.get(attribute)} for attribute in sorted(stated.keys() | predicted.keys())]
    return {"name": name, "attributes": rows, "has_prediction": bool(predicted)}


@timed
def author_activity(name):
    with POOL.connection() as conn:
        require_author(conn, name)
        return conn.execute("""SELECT count(*) AS texts, count(*) FILTER (WHERE record_type = 'post') AS posts, min(created_utc) AS first_seen, max(created_utc) AS last_seen
            FROM records WHERE author = %s""", [name]).fetchone()


@timed
def author_subreddits(name):
    with POOL.connection() as conn:
        require_author(conn, name)
        rows = conn.execute("""SELECT subreddit, count(*) AS texts FROM (SELECT subreddit FROM records WHERE author = %s ORDER BY created_utc DESC LIMIT %s) newest
            GROUP BY subreddit ORDER BY texts DESC, subreddit LIMIT %s""", [name, RECENT, GROUPS]).fetchall()
    return {"window": RECENT, "subreddits": rows}


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
    rows = [{"author": row["author"], "usable_texts": row["usable_texts"], "similarity": max(-1.0, min(1.0, 1 - row["_distance"]))} for row in table.to_pylist() if row["author"] != name]
    return {"similar": rows[:SIMILAR]}


@timed
def author_texts(name, before):
    condition, params = keyset(cursor_of(before))
    with POOL.connection() as conn:
        require_author(conn, name)
        rows = conn.execute(f"SELECT {FIELDS} FROM records WHERE author = %s{condition} ORDER BY created_utc DESC, record_id DESC LIMIT %s", [name, *params, PAGE + 1]).fetchall()
        return {"texts": listed(conn, rows[:PAGE]), "next": position(rows[PAGE - 1]) if len(rows) > PAGE else None}


@timed
def subreddit_activity(name):
    name = name.lower()
    with POOL.connection() as conn:
        require_subreddit(conn, name)
        return {"name": name} | conn.execute("SELECT count(*) AS texts, min(created_utc) AS first_seen, max(created_utc) AS last_seen FROM records WHERE subreddit = %s", [name]).fetchone()


@timed
def subreddit_posts(name, before):
    name = name.lower()
    condition, params = keyset(cursor_of(before))
    with POOL.connection() as conn:
        require_subreddit(conn, name)
        rows = conn.execute(f"SELECT {FIELDS} FROM records WHERE subreddit = %s{condition} ORDER BY created_utc DESC, record_id DESC LIMIT %s", [name, *params, POST_SCAN]).fetchall()
        posts, stop = [], len(rows)
        for index, row in enumerate(rows):
            if row["record_type"] == "post":
                posts.append(row)
                if len(posts) == PAGE:
                    stop = index + 1
                    break
        more = stop < len(rows) or len(rows) == POST_SCAN
        return {"texts": listed(conn, posts), "next": position(rows[stop - 1]) if more else None}


@timed
def subreddit_authors(name):
    name = name.lower()
    with POOL.connection() as conn:
        require_subreddit(conn, name)
        rows = conn.execute("""SELECT author, count(*) AS texts FROM (SELECT author FROM records WHERE subreddit = %s ORDER BY created_utc DESC LIMIT %s) newest
            WHERE author <> ALL(%s) GROUP BY author ORDER BY texts DESC, author LIMIT %s""", [name, RECENT, NO_AUTHOR, GROUPS]).fetchall()
    return {"window": RECENT, "authors": rows}


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
