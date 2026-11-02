import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import orjson
from psycopg.errors import QueryCanceled
from psycopg_pool import PoolTimeout

from . import LOG, STATIC, api, timed
from .config import HOSTS, IPV4, IPV6, PORT

FILES = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/app.css": ("app.css", "text/css; charset=utf-8")}
SECURITY = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}
GONE = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
ROUTES = (
    (("status",), lambda query: api.status()),
    (("starts",), lambda query: api.starts()),
    (("search",), lambda query: api.search(single(query, "q") or "")),
    (("author", None), lambda query, name: api.author(name)),
    (("author", None, "activity"), lambda query, name: api.author_activity(name)),
    (("author", None, "subreddits"), lambda query, name: api.author_subreddits(name)),
    (("author", None, "similar"), lambda query, name: api.author_similar(name)),
    (("author", None, "texts"), lambda query, name: api.author_texts(name, single(query, "before"))),
    (("subreddit", None, "activity"), lambda query, name: api.subreddit_activity(name)),
    (("subreddit", None, "posts"), lambda query, name: api.subreddit_posts(name, single(query, "before"))),
    (("subreddit", None, "authors"), lambda query, name: api.subreddit_authors(name)),
    (("text", None), lambda query, record_id: api.text(record_id)),
)


def single(query, name):
    values = query.get(name)
    return values[0] if values else None


def resolve(parts):
    for pattern, handler in ROUTES:
        if len(pattern) == len(parts) and all(part is None or part == value for part, value in zip(pattern, parts)):
            return handler, [value for part, value in zip(pattern, parts) if part is None]
    raise api.NotFound("There is nothing at this address.")


def answer(split):
    if "\x00" in unquote(split.path) or "\x00" in unquote(split.query):
        raise api.BadRequest("The address contains a character that cannot be searched.")
    handler, values = resolve([unquote(part) for part in split.path.split("/")[2:]])
    return handler(parse_qs(split.query, keep_blank_values=True), *values)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True
    timeout = 60

    def log_message(self, format, *args):
        pass

    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if content_type == "application/json" else "no-cache")
        for name, value in SECURITY.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)
        return status

    def error(self, status, message):
        return self.send(status, orjson.dumps({"error": message}), "application/json")

    def route(self):
        if self.headers.get("Host") not in HOSTS:
            return self.error(400, "This server only answers on localhost.")
        split = urlsplit(self.path)
        if split.path in FILES:
            name, content_type = FILES[split.path]
            return self.send(200, (STATIC / name).read_bytes(), content_type)
        if not split.path.startswith("/api/"):
            return self.error(404, "There is nothing at this address.")
        try:
            result = answer(split)
        except api.NotFound as error:
            return self.error(404, str(error))
        except api.BadRequest as error:
            return self.error(400, str(error))
        except (QueryCanceled, PoolTimeout):
            LOG.exception("timed out %s", self.path)
            return self.error(500, "This took too long to load. Try again in a moment.")
        except Exception:
            LOG.exception("failed %s", self.path)
            return self.error(500, "Something went wrong loading this. The details are in explorer.log.")
        return self.send(200, orjson.dumps(result), "application/json")

    def do_GET(self):
        started = time.perf_counter()
        try:
            status = self.route()
        except GONE:
            self.close_connection = True
            LOG.info("GET %s client left %.0fms", self.path, (time.perf_counter() - started) * 1000)
            return
        LOG.info("GET %s %d %.0fms", self.path, status, (time.perf_counter() - started) * 1000)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64


class ServerIPv6(Server):
    address_family = socket.AF_INET6


@timed
def serve():
    api.POOL.open(wait=True, timeout=30)
    with api.POOL, Server((IPV4, PORT), Handler) as server, ServerIPv6((IPV6, PORT), Handler) as server_ipv6:
        threading.Thread(target=server_ipv6.serve_forever, name="ipv6", daemon=True).start()
        LOG.info("serving on http://localhost:%d", PORT)
        server.serve_forever()
