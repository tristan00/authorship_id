import argparse

from database import LOGS, use
from reddit_dumps import setup_logging
from reddit_dumps.catalog import month_index


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--database", required=True)
    stages = parser.add_mutually_exclusive_group()
    stages.add_argument("--derive-only", action="store_true")
    stages.add_argument("--load-only", action="store_true")
    args = parser.parse_args()
    if not args.derive_only and not (args.start and args.end):
        parser.error("--start and --end are required unless --derive-only")
    if not args.derive_only:
        month_index(args.start)
        month_index(args.end)
    setup_logging(LOGS / "pipeline.log")
    use(args.database)
    from .run import run
    run(args.start, args.end, not args.derive_only, not args.load_only)


if __name__ == "__main__":
    main()
