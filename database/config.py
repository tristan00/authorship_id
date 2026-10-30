from pathlib import Path

PG = Path(r"C:\Users\trist\pg\pgsql\bin")
DATA = Path(r"C:\reddit_data\postgres")
DUMPS = Path(r"C:\reddit_data\dumps")
LOGS = Path(r"C:\reddit_data\logs")
PORT = 5499
DSN = f"host=localhost port={PORT} dbname=reddit user=postgres"
NO_AUTHOR = ["", "[deleted]", "[removed]"]

PARSERS = 16
TRANSFER_SLOTS = 64
SLOT_SIZE = 2**22
SCAN_WORKERS = 16
SORT_WORKERS = 8
SORT_MEMORY = "256MB"
INDEX_BUILDS = 2
INDEX_MEMORY = "2GB"
