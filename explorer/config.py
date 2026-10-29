from pathlib import Path

STATIC = Path(__file__).with_name("static")
PORT = 8800
CONNECTIONS = 8
QUERY_SETTINGS = "-c max_parallel_workers_per_gather=8 -c parallel_setup_cost=10000"

TEXT_SORTS = ("author", "subreddit", "created_utc", "words", "claims", "incohesive", "outvoted")
TEXT_COUNTS = ("words", "claims", "incohesive", "outvoted")

PAGE = 50
EXCERPT = 160
