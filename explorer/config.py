from pathlib import Path

STATIC = Path(__file__).with_name("static")
PORT = 8800
CONNECTIONS = 8

TEXT_SORTS = ("author", "subreddit", "created_utc", "words", "claims", "incohesive", "outvoted")
TEXT_COUNTS = ("words", "claims", "incohesive", "outvoted")

PAGE = 50
EXCERPT = 160
