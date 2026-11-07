import argparse

from database import LOGS
from reddit_dumps import setup_logging
from reddit_dumps.catalog import month_index


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--derive-only", action="store_true")
    args = parser.parse_args()
    if not args.derive_only and not (args.start and args.end):
        parser.error("--start and --end are required unless --derive-only")
    if not args.derive_only:
        month_index(args.start)
        month_index(args.end)
    setup_logging(LOGS / "pipeline.log")
    from .run import run
    run(args.start, args.end, not args.derive_only)


if __name__ == "__main__":
    main()
