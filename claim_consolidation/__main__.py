import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_consolidation")
    parser.add_argument("command", choices=("consolidate",))
    parser.parse_args()
    setup_logging(LOGS / "claim_consolidation.log")
    from .consolidate import consolidate
    consolidate()


if __name__ == "__main__":
    main()
