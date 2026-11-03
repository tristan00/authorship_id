from pathlib import Path

STATIC = Path(__file__).with_name("static")
IPV4 = "127.0.0.1"
IPV6 = "::1"
PORT = 8800
HOSTS = {f"localhost:{PORT}", f"{IPV4}:{PORT}", f"[{IPV6}]:{PORT}"}

POOL_MIN = 2
POOL_MAX = 16
POOL_WAIT = 8
SESSION = "-c statement_timeout=5000 -c default_transaction_read_only=on"

SEARCH = 12
SEARCH_INPUT = 64
SEARCH_VARIANT_CHARS = 3
STARTS = 12
PAGE = 25
RECENT = 1000
POST_SCAN = 2000
GROUPS = 12
SIMILAR = 20
PARENTS = 20
CLAIMS = 200
EXCERPT_READ = 1000
EXCERPT = 240
