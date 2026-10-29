from datetime import datetime, timezone

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from database import DSN

from . import timed
from .config import CONNECTIONS, EXCERPT, PAGE

POOL = ConnectionPool(DSN, kwargs={"row_factory": dict_row}, min_size=CONNECTIONS, max_size=CONNECTIONS, open=False)


class NotFound(Exception):
    pass


def connect():
    return POOL.connection()


def like(text):
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def user_filter(query, sub):
    if sub:
        return "author ILIKE %s AND subs @> ARRAY[%s]::text[]", [like(query.strip()), sub]
    return "author ILIKE %s", [like(query.strip())]


def excerpt(row):
    return {"removed": "[removed]", "empty": ""}.get(row["text_status"], " ".join(row["text"].split())[:EXCERPT])


@timed
def search(query):
    pattern = like(query.strip())
    with connect() as conn:
        users = conn.execute("SELECT author, texts, posts, first_utc, last_utc, subs FROM explorer_authors WHERE author ILIKE %s ORDER BY texts DESC, author LIMIT %s",
                             [pattern, PAGE]).fetchall()
        total = conn.execute("SELECT count(*) AS n FROM explorer_authors WHERE author ILIKE %s", [pattern]).fetchone()["n"]
        subs = conn.execute("SELECT subreddit, texts, authors FROM explorer_subreddits WHERE subreddit ILIKE %s ORDER BY texts DESC", [pattern]).fetchall()
    return {"query": query, "users": users, "userTotal": total, "subs": subs}


@timed
def subreddits():
    with connect() as conn:
        return conn.execute("SELECT subreddit, texts, posts, authors, first_utc, last_utc FROM explorer_subreddits ORDER BY texts DESC, subreddit").fetchall()


@timed
def users_page(query, sub, offset):
    condition, params = user_filter(query, sub)
    with connect() as conn:
        return conn.execute(f"""SELECT author, texts, posts, cardinality(subs) AS subs, first_utc, last_utc FROM explorer_authors
                                WHERE {condition} ORDER BY texts DESC, author LIMIT %s OFFSET %s""", [*params, PAGE, offset]).fetchall()


@timed
def users(query, sub):
    condition, params = user_filter(query, sub)
    with connect() as conn:
        total = conn.execute(f"SELECT count(*) AS n FROM explorer_authors WHERE {condition}", params).fetchone()["n"]
    return {"total": total, "users": users_page(query, sub, 0)}


def tree(rows, root):
    children = {}
    for row in rows:
        children.setdefault(row["parent_id"], []).append(row)
    out = []

    def walk(record_id, depth):
        for child in children.get(record_id, []):
            out.append({**child, "depth": depth, "text": excerpt(child)})
            walk(child["record_id"], depth + 1)

    ids = {r["record_id"] for r in rows}
    post = root in ids
    for record_id in [root] + sorted({r["parent_id"] for r in rows if r["parent_id"] not in ids and r["parent_id"] not in (None, root)}):
        walk(record_id, int(post))
    if post:
        row = next(r for r in rows if r["record_id"] == root)
        out.insert(0, {**row, "depth": 0, "text": excerpt(row)})
    return out


def title(row):
    return row["text"].split("\n\n", 1)[0] if row and row["record_type"] == "post" and row["text"] else None


@timed
def text(record_id):
    with connect() as conn:
        record = conn.execute("SELECT r.*, b.text FROM records r JOIN bodies b USING (text_sha256) WHERE r.record_id = %s", [record_id]).fetchone()
        if record is None:
            raise NotFound(record_id)
        thread = conn.execute("""SELECT r.record_id, r.author, r.created_utc, r.parent_id, r.record_type, r.text_status, b.text
                                 FROM records r JOIN bodies b USING (text_sha256) WHERE r.link_id = %s ORDER BY r.created_utc""", [record["link_id"]]).fetchall()
        claims = conn.execute("""SELECT c.field, c.value, c.start_char, c.end_char, s.record_id IS NOT NULL AS suspect
                                 FROM text_claims c LEFT JOIN suspect_claim_texts s ON s.record_id = %s AND s.attribute = c.field AND s.value = c.value
                                 WHERE c.text_sha256 = %s ORDER BY c.start_char, c.field""", [record_id, record["text_sha256"]]).fetchall()
    rows = {r["record_id"]: r for r in thread}
    parent = rows.get(record["parent_id"])
    return {
        **{k: record[k] for k in ("record_id", "subreddit", "record_type", "author", "created_utc", "text_status", "text")},
        "title": title(record),
        "parent": record["parent_id"] and {"record_id": record["parent_id"], "author": parent and parent["author"], "present": parent is not None},
        "post": {"record_id": record["link_id"], "title": title(rows.get(record["link_id"])), "present": record["link_id"] in rows},
        "thread": tree(thread, record["link_id"]), "threadComments": sum(r["record_type"] == "comment" for r in thread),
        "claims": claims,
    }


@timed
def similar_users(author, limit=50):
    from author_encoder.index import similar, users
    if (index := users()) is None:
        return {"status": "not_built", "indexed_users": 0, "users": []}
    matches = similar(author, limit)
    if matches is None:
        return {"status": "ineligible", "minimum_texts": 64, "users": []}
    with connect() as conn:
        records = conn.execute("SELECT author, texts, subs[1:5] AS top_subreddits FROM explorer_authors WHERE author=ANY(%s)", [[item["author"] for item in matches]]).fetchall()
    details = {item["author"]: item for item in records}
    missing = [item["author"] for item in matches if item["author"] not in details]
    if missing:
        raise NotFound("User metadata is missing for the vector index")
    return {"status": "ready", "indexed_users": index.count_rows(), "sampled_texts": 64, "users": [details[item["author"]] | {"similarity": item["similarity"]} for item in matches]}


@timed
def user_vector(author):
    from author_encoder.index import users, vector
    if users() is None:
        return {"status": "not_built", "indexed_users": 0}
    found = vector(author)
    if found is None:
        return {"status": "ineligible", "minimum_texts": 64}
    return {"status": "ready", **found}


@timed
def user_trends(author):
    with connect() as conn:
        rows = conn.execute("""SELECT (created_utc / 3600) * 3600 AS hour, count(*) FILTER (WHERE record_type = 'post') AS posts, count(*) AS texts
            FROM records WHERE author = %s GROUP BY 1 ORDER BY 1""", [author]).fetchall()
    if not rows:
        raise NotFound(author)
    first, last = (rows[i]['hour'] // 86400 * 86400 for i in (0, -1))
    days = {day: {'day': day, 'posts': 0, 'texts': 0} for day in range(first, last + 86400, 86400)}
    hours = [{'hour': hour, 'posts': 0, 'texts': 0} for hour in range(24)]
    weekdays = [{'weekday': weekday, 'posts': 0, 'texts': 0} for weekday in range(7)]
    for row in rows:
        instant = datetime.fromtimestamp(row['hour'], timezone.utc)
        for bucket in (days[row['hour'] // 86400 * 86400], hours[instant.hour], weekdays[instant.weekday()]):
            bucket['posts'] += row['posts']
            bucket['texts'] += row['texts']
    return {'days': list(days.values()), 'hours': hours, 'weekdays': weekdays}


@timed
def user_claims(author):
    from claim_extraction.config import FIELDS, NUMERIC
    with connect() as conn:
        run = conn.execute("SELECT finished_at FROM consolidation").fetchone()
        rows = conn.execute("SELECT attribute, value, candidates FROM author_claims WHERE author = %s", [author]).fetchall()
        evidence = conn.execute("""SELECT c.field AS attribute, c.source, c.source_key, t.subreddit, c.value, t.created_utc,
                                          CASE WHEN a.value = c.value THEN 'accepted' ELSE 'outvoted' END AS state, s.record_id IS NOT NULL AS suspect
                                   FROM claim_evidence c
                                   LEFT JOIN author_claims a ON a.author = c.author AND a.attribute = c.field
                                   LEFT JOIN records t ON c.source = 'text' AND t.record_id = c.source_key
                                   LEFT JOIN suspect_claim_texts s ON c.source = 'text' AND s.record_id = c.source_key AND s.attribute = c.field AND s.value = c.value
                                   WHERE c.author = %s ORDER BY c.field, t.created_utc""", [author]).fetchall()

    def value(attribute, text):
        return float(text) if attribute in NUMERIC else text

    def stats(attribute):
        rows = [item for item in evidence if item["attribute"] == attribute]
        return {"observations": len(rows), "sources": {source: sum(item["source"] == source for item in rows) for source in ("text", "flair")},
                "effective_units": len({item["source_key"] for item in rows if item["source"] == "text"})}

    targets = [{"attribute": row["attribute"], "target": {
        "value": value(row["attribute"], row["value"]),
        "candidates": [{"value": value(row["attribute"], item["value"]), "support": item["support"]} for item in row["candidates"]],
        "outvoted": sum(item["attribute"] == row["attribute"] and item["state"] == "outvoted" for item in evidence),
        "stats": stats(row["attribute"])}} for row in rows]
    return {"finished": run["finished_at"], "fields": list(FIELDS), "targets": targets, "evidence": evidence}


@timed
def user_predictions(author):
    with connect() as conn:
        run = conn.execute("""SELECT r.run_id, r.folds, r.manifest FROM demographic_state s JOIN demographic_runs r USING (run_id)
                              WHERE r.status = 'ready' AND r.consolidation_run = (SELECT run_id FROM consolidation)""").fetchone()
        if run is None:
            raise NotFound("No published demographic model for the current consolidation")
        row = conn.execute("SELECT attributes, fold FROM demographic_predictions WHERE run_id = %s AND author = %s", [run["run_id"], author.lower()]).fetchone()
    if row is None:
        return {"status": "ineligible", "minimum_texts": run["manifest"]["sampled_texts"]}
    return {"status": "ready", "attributes": row["attributes"], "fold": row["fold"] + 1, "folds": run["folds"], "run_id": str(run["run_id"]),
            "sampled_texts": run["manifest"]["sampled_texts"]}


FLAGGED_TEXT = "EXISTS (SELECT 1 FROM suspect_claim_texts s WHERE s.record_id = x.record_id)"
FLAGGED = {"": "TRUE", "yes": FLAGGED_TEXT, "no": f"NOT {FLAGGED_TEXT}"}
USER_TEXTS = """(SELECT t.record_id, t.author, t.subreddit, t.record_type, t.created_utc, b.words,
                        coalesce(e.claims, 0) AS claims, coalesce(e.incohesive, 0) AS incohesive, coalesce(e.outvoted, 0) AS outvoted
                 FROM records t JOIN bodies b USING (text_sha256) LEFT JOIN explorer_texts e USING (record_id) WHERE t.author = %(user)s)"""


def source(filters):
    return "explorer_texts" if filters["user"] is None else USER_TEXTS


def text_filter(filters):
    conditions = ["author ILIKE %(author)s", "subreddit ILIKE %(sub)s", FLAGGED[filters["flagged"]],
                  *(f"{column} BETWEEN %({column}_low)s AND %({column}_high)s" for column in filters["ranges"])]
    if filters["type"]:
        conditions.append("record_type = %(type)s")
    return " AND ".join(conditions)


def patterns(filters):
    bounds = {f"{column}_{side}": value for column, pair in filters["ranges"].items() for side, value in zip(("low", "high"), pair)}
    return {**filters, **bounds, "author": like(filters["author"]), "sub": like(filters["sub"])}


@timed
def texts_page(filters, offset):
    order = f"{filters['sort']} {filters['dir']}, record_id {filters['dir']}"
    with connect() as conn:
        return conn.execute(f"""SELECT x.*, ARRAY(SELECT concat_ws(' ', s.attribute, s.value) FROM suspect_claim_texts s WHERE s.record_id = x.record_id ORDER BY 1) AS suspect
                                FROM {source(filters)} x WHERE {text_filter(filters)} ORDER BY {order} LIMIT %(limit)s OFFSET %(offset)s""",
                            {**patterns(filters), "limit": PAGE, "offset": offset}).fetchall()


@timed
def texts(filters):
    with connect() as conn:
        total = conn.execute(f"SELECT count(*) AS n FROM {source(filters)} x WHERE {text_filter(filters)}", patterns(filters)).fetchone()["n"]
    return {"total": total, "texts": texts_page(filters, 0)}


@timed
def flag(record_id, attribute, value, suspect):
    with connect() as conn:
        if suspect:
            conn.execute("INSERT INTO suspect_claim_texts (record_id, attribute, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", [record_id, attribute, value])
        else:
            conn.execute("DELETE FROM suspect_claim_texts WHERE record_id = %s AND attribute = %s AND value = %s", [record_id, attribute, value])
    return {"record_id": record_id, "attribute": attribute, "value": value, "suspect": suspect}


@timed
def user(author):
    with connect() as conn:
        summary = conn.execute("SELECT * FROM explorer_authors WHERE author = %s", [author]).fetchone()
        if summary is None:
            raise NotFound(author)
    return {"summary": summary}


@timed
def subreddit_posts(sub, offset):
    with connect() as conn:
        return conn.execute("""
            SELECT t.record_id, t.author, t.created_utc, t.text_status, left(b.text, 400) AS text,
                   (SELECT count(*) FROM records c WHERE c.link_id = t.record_id AND c.record_type = 'comment') AS comments
            FROM records t JOIN bodies b USING (text_sha256) WHERE t.subreddit = %s AND t.record_type = 'post'
            ORDER BY t.created_utc DESC, t.record_id LIMIT %s OFFSET %s""", [sub, PAGE, offset]).fetchall()


@timed
def subreddit_authors(sub, offset):
    with connect() as conn:
        return conn.execute("""SELECT author AS name, texts FROM explorer_activity WHERE subreddit = %s AND named
                               ORDER BY texts DESC, author LIMIT %s OFFSET %s""", [sub, PAGE, offset]).fetchall()


@timed
def subreddit(sub):
    with connect() as conn:
        summary = conn.execute("SELECT * FROM explorer_subreddits WHERE subreddit = %s", [sub]).fetchone()
        if summary is None:
            raise NotFound(sub)
    return {"summary": summary, "posts": subreddit_posts(sub, 0), "authors": subreddit_authors(sub, 0)}
