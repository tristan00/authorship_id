import mimetypes
import re
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import orjson

from . import LOG, PORT, STATIC, api, timed
from .config import TEXT_COUNTS, TEXT_SORTS

ROUTES = {
    ("search",): lambda q: api.search(q.get("q", [""])[0]),
    ("search", "subs"): lambda q: api.search_subs(q.get("q", [""])[0], offset(q)),
    ("totals",): lambda q: api.totals(),
    ("users",): lambda q: api.users(q.get("q", [""])[0], q.get("sub", [""])[0]),
    ("users", "page"): lambda q: api.users_page(q.get("q", [""])[0], q.get("sub", [""])[0], offset(q)),
    ("subreddits",): lambda q: api.subreddits(offset(q)),
    ("texts",): lambda q: api.texts(text_filters(q)),
    ("texts", "page"): lambda q: api.texts_page(text_filters(q), offset(q)),
    ("text", None): lambda q, record_id: api.text(record_id),
    ("user", None): lambda q, name: api.user(name),
    ("user", None, "texts"): lambda q, name: api.texts(text_filters(q, name)),
    ("user", None, "texts", "page"): lambda q, name: api.texts_page(text_filters(q, name), offset(q)),
    ("user", None, "trends"): lambda q, name: api.user_trends(name),
    ("user", None, "claims"): lambda q, name: api.user_claims(name),
    ("user", None, "predictions"): lambda q, name: api.user_predictions(name),
    ("user", None, "similar"): lambda q, name: api.similar_users(name, limit(q)),
    ("user", None, "vector"): lambda q, name: api.user_vector(name),
    ("subreddit", None): lambda q, name: api.subreddit(name),
    ("subreddit", None, "posts"): lambda q, name: api.subreddit_posts(name, offset(q)),
    ("subreddit", None, "authors"): lambda q, name: api.subreddit_authors(name, offset(q)),
}
POSTS = {
    ("suspect",): lambda body: api.flag(body["record_id"], body["attribute"], body["value"], body["suspect"]),
}
FLAG = {"record_id": str, "attribute": str, "value": str, "suspect": bool}


class BadRequest(Exception):
    pass


def integer(query, name):
    try:
        value = int(query[name][0])
    except (KeyError, ValueError) as error:
        raise BadRequest(f"{name} must be a nonnegative integer") from error
    if value < 0 or value > 2**63 - 1:
        raise BadRequest(f"{name} is outside the database integer range")
    return value


def offset(query):
    return integer(query, "offset")


def limit(query):
    value = integer(query, "limit") if "limit" in query else 50
    if value < 1 or value > 200:
        raise BadRequest("limit must be between 1 and 200")
    return value


def count_span(text):
    if not text.isdigit():
        raise BadRequest(f"{text!r} is not a whole number")
    return int(text), int(text) + 1


def day_span(text):
    match = re.fullmatch(r"(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", text)
    if match is None:
        raise BadRequest(f"{text!r} is not a date like 2026, 2026-02 or 2026-02-05")
    year, month, day = (int(g) if g else None for g in match.groups())
    try:
        start = datetime(year, month or 1, day or 1, tzinfo=timezone.utc)
    except ValueError as error:
        raise BadRequest(f"{text!r} is not a real date") from error
    end = start + timedelta(days=1) if day else start.replace(year=year + month // 12, month=month % 12 + 1) if month else start.replace(year=year + 1)
    return int(start.timestamp()), int(end.timestamp())


TEXT_RANGES = {"created_utc": day_span} | dict.fromkeys(TEXT_COUNTS, count_span)
RANGE = re.compile(r"\s*(?:(?P<low>[^<>=.]+?)\s*\.\.\s*(?P<high>[^<>=.]+?)|(?P<op><=|>=|<|>|=)?\s*(?P<value>[^<>=.]+?))\s*")
TOP = 2**62


def span(text, unit):
    match = RANGE.fullmatch(text)
    if match is None:
        raise BadRequest(f"{text!r} should look like 5, >5, <=5 or 2..8")
    if match["low"]:
        return unit(match["low"])[0], unit(match["high"])[1] - 1
    start, end = unit(match["value"])
    return {"=": (start, end - 1), ">": (end, TOP), ">=": (start, TOP), "<": (0, start - 1), "<=": (0, end - 1)}[match["op"] or "="]


def text_filters(query, user=None):
    names = (("sort", "outvoted" if user is None else "created_utc"), ("dir", "desc"), ("flagged", ""), ("type", ""), ("author", ""), ("sub", ""))
    filters = {name: query.get(name, [default])[0].strip() for name, default in names}
    if filters["sort"] not in TEXT_SORTS or filters["dir"] not in ("asc", "desc") or filters["flagged"] not in api.FLAGGED or filters["type"] not in ("", "post", "comment"):
        raise BadRequest("sort, dir, flagged or type has an unknown value")
    ranges = {column: span(query[column][0], unit) for column, unit in TEXT_RANGES.items() if query.get(column, [""])[0].strip()}
    return filters | {"ranges": ranges, "user": user}


def route(parts):
    for key, handler in ROUTES.items():
        if len(key) == len(parts) and all(k is None or k == p for k, p in zip(key, parts)):
            return handler, [p for k, p in zip(key, parts) if k is None]
    return None, None


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, kind):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.timed(self.respond)

    def do_POST(self):
        self.timed(self.receive)

    def timed(self, method):
        start = time.perf_counter()
        try:
            method()
        finally:
            LOG.info("%s %s %.3fs", self.command, self.path, time.perf_counter() - start)

    def answer(self, handler):
        if handler is None:
            self.send(404, b'{"error":"no such endpoint"}', "application/json")
            return
        try:
            self.send(200, orjson.dumps(handler()), "application/json")
        except api.NotFound as missing:
            self.send(404, orjson.dumps({"error": f"not found: {missing}"}), "application/json")
        except BadRequest as error:
            self.send(400, orjson.dumps({"error": str(error)}), "application/json")

    def body(self):
        try:
            body = orjson.loads(self.rfile.read(int(self.headers["Content-Length"])))
        except (TypeError, ValueError) as error:
            raise BadRequest("body must be JSON") from error
        if not isinstance(body, dict) or any(not isinstance(body.get(k), kind) for k, kind in FLAG.items()):
            raise BadRequest("body needs record_id, attribute, value and suspect")
        return body

    def receive(self):
        parts = [unquote(p) for p in urlsplit(self.path).path.strip("/").split("/") if p]
        handler = POSTS.get(tuple(parts[1:])) if parts[:1] == ["api"] else None
        self.answer(handler and (lambda: handler(self.body())))

    def respond(self):
        url = urlsplit(self.path)
        parts = [unquote(p) for p in url.path.strip("/").split("/") if p]
        if parts[:1] == ["api"]:
            handler, args = route(parts[1:])
            self.answer(handler and (lambda: handler(parse_qs(url.query), *args)))
        else:
            path = STATIC / (parts[-1] if parts and parts[0] == "static" and len(parts) == 2 else "index.html")
            kind = mimetypes.guess_type(path.name)[0]
            if path.parent == STATIC and path.is_file() and kind is not None:
                self.send(200, path.read_bytes(), kind + "; charset=utf-8")
            else:
                self.send(404, b"not found", "text/plain")

    def log_message(self, *args):
        pass


@timed
def serve():
    LOG.info("serving on http://localhost:%d", PORT)
    with api.POOL, ThreadingHTTPServer(("localhost", PORT), Handler) as server:
        server.serve_forever()
