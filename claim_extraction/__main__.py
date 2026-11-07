import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_extraction")
    parser.add_argument("command", choices=("extract",))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    setup_logging(LOGS / "claim_extraction.log")
    from .run import extract
    extract(args.reset)


if __name__ == "__main__":
    main()
