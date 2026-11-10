import argparse
import sys

from database import LOGS
from reddit_dumps import setup_logging

from . import catalog, log
from .download import arrivals


def main():
    parser = argparse.ArgumentParser(prog="reddit_dumps")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    setup_logging(LOGS / "download.log")
    try:
        for _ in arrivals(catalog.month_range(args.start, args.end)):
            pass
    except Exception:
        log.exception("download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
