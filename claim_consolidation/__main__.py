import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_consolidation")
    parser.add_argument("command", choices=("consolidate", "sample", "evaluate"))
    parser.add_argument("--month")
    parser.add_argument("--dataset")
    parser.add_argument("--authors", type=int)
    parser.add_argument("--split", default="validation")
    args = parser.parse_args()
    if args.command == "sample" and not (args.month and args.dataset and args.authors):
        parser.error("sample needs --month, --dataset and --authors")
    if args.command == "evaluate" and not (args.month and args.dataset):
        parser.error("evaluate needs --month and --dataset")
    setup_logging(LOGS / "claim_consolidation.log")
    if args.command == "consolidate":
        from .consolidate import consolidate
        consolidate()
    elif args.command == "sample":
        from .sample import sample
        sample(args.month, args.dataset, args.authors)
    else:
        from .evaluate import evaluate
        evaluate(args.month, args.dataset, args.split)


if __name__ == "__main__":
    main()
