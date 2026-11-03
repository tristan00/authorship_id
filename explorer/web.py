import json
import logging
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg
from psycopg_pool import PoolTimeout

from reddit_dumps import timed

from .api import Failure, dispatch

LOG = logging.getLogger("explorer")
PORT = 8800
HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}", f"[::1]:{PORT}"}
STATIC = Path(__file__).with_name("static")
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
BODY_LIMIT = 1 << 20
SECURITY = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}
FILES = {"/": STATIC / "index.html"} | {"/" + path.relative_to(STATIC).as_posix(): path for path in STATIC.rglob("*") if path.is_file() and path.suffix in TYPES}


class Handler(BaseHTTPRequestHandler):
    server_version = "explorer"
    sys_version = ""

    def handle_one_request(self):
        self.started = time.perf_counter()
        super().handle_one_request()

    def log_request(self, code="-", size="-"):
        LOG.info("%s %s %s %.1fms", self.command, self.path, int(code), (time.perf_counter() - self.started) * 1000)

    def log_message(self, format, *args):
        LOG.warning("http %s", format % args)

    def end_headers(self):
        for name, value in SECURITY.items():
            self.send_header(name, value)
        super().end_headers()

    def do_GET(self):
        self.serve("GET")

    def do_POST(self):
        self.serve("POST")

    def serve(self, method):
        if self.headers["Host"] not in HOSTS:
            return self.send(421, "application/json", json.dumps({"error": f"Host {self.headers['Host']} is not served here"}).encode())
        url = urlsplit(self.path)
        if url.path.startswith("/api/"):
            return self.answer(method, url)
        if method == "GET" and url.path in FILES:
            return self.send(200, TYPES[FILES[url.path].suffix], read_static(FILES[url.path]))
        self.send(404, "text/plain; charset=utf-8", f"No file {url.path}".encode())

    def answer(self, method, url):
        try:
            parts = [unquote(part) for part in url.path.removeprefix("/api/").split("/")]
            code, payload = 200, dispatch(method, parts, parse_qs(url.query, keep_blank_values=True), self.body() if method == "POST" else None)
        except Failure as failure:
            code, payload = failure.code, {"error": str(failure)}
        except psycopg.errors.QueryCanceled as error:
            code, payload = 504, {"error": f"Database query cancelled: {str(error).strip()}"}
        except (psycopg.OperationalError, PoolTimeout) as error:
            code, payload = 503, {"error": f"Database unavailable: {str(error).strip()}"}
        except Exception as error:
            LOG.exception("api failure %s %s", method, self.path)
            code, payload = 500, {"error": f"{type(error).__name__}: {error}"}
        self.send(code, "application/json", json.dumps(payload).encode())

    def body(self):
        length = self.headers["Content-Length"]
        if length is None or not length.isdigit():
            raise Failure(411, "A Content-Length header is required")
        if int(length) > BODY_LIMIT:
            raise Failure(413, f"The request body is larger than {BODY_LIMIT} bytes")
        try:
            return json.loads(self.rfile.read(int(length)))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Failure(400, f"The request body is not valid JSON: {error}")

    def send(self, code, kind, data):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@timed
def read_static(path):
    return path.read_bytes()
