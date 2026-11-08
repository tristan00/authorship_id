import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_consolidation")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("consolidate")
    parser.parse_args()
    setup_logging(LOGS / "consolidation.log")
    from .consolidate import consolidate
    consolidate()


if __name__ == "__main__":
    main()
