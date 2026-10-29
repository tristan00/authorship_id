import argparse

from database import LOGS
from reddit_dumps import setup_logging
from reddit_dumps.catalog import month_index


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    month_index(args.month)
    setup_logging(LOGS / "pipeline.log")
    from .run import run
    run(args.month)


if __name__ == "__main__":
    main()
