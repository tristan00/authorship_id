import argparse

from database import LOGS
from reddit_dumps import setup_logging
from reddit_dumps.catalog import month_index


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    month_index(args.start)
    month_index(args.end)
    setup_logging(LOGS / "pipeline.log")
    from .run import run
    run(args.start, args.end)


if __name__ == "__main__":
    main()
