from pathlib import Path

DUMPS = Path(r"C:\reddit_data\dumps")
LOGS = Path(r"C:\reddit_data\logs")
DISTRO = "Ubuntu-24.04"
PORT = 8123
DATABASE = "reddit"
SERVER_MEMORY = 26_000_000_000
NO_AUTHOR = ("", "[deleted]", "[removed]")

PARSERS = 10
QUEUE_CHUNKS = 32
CONVERT_ROWS = 100_000
RECORD_BATCH = 500_000
BODY_BATCH = 250_000
SEND_BYTES = 1 << 22
BODY_RANGES = 32
