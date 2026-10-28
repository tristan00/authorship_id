import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_flair")
    parser.add_argument("command", choices=("load",))
    parser.parse_args()
    setup_logging(LOGS / "claim_flair.log")
    from .load import load
    load()


if __name__ == "__main__":
    main()
