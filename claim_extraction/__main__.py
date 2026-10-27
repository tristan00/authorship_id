import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_extraction")
    parser.add_argument("command", choices=("sample",))
    parser.add_argument("--month", required=True)
    parser.add_argument("--datasets", nargs="+", required=True)
    args = parser.parse_args()
    setup_logging(LOGS / "claim_extraction.log")
    from .sample import sample
    sample(args.month, args.datasets)


if __name__ == "__main__":
    main()
