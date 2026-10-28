import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_consolidation")
    parser.add_argument("command", choices=("consolidate", "sample"))
    parser.add_argument("--month")
    parser.add_argument("--dataset")
    parser.add_argument("--authors", type=int)
    args = parser.parse_args()
    if args.command == "sample" and not (args.month and args.dataset and args.authors):
        parser.error("sample needs --month, --dataset and --authors")
    setup_logging(LOGS / "claim_consolidation.log")
    if args.command == "consolidate":
        from .consolidate import consolidate
        consolidate()
    else:
        from .sample import sample
        sample(args.month, args.dataset, args.authors)


if __name__ == "__main__":
    main()
