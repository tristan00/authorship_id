import argparse
from pathlib import Path

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_extraction")
    parser.add_argument("command", choices=("sample", "labels", "fit", "evaluate"))
    parser.add_argument("--month", required=True)
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--splits", nargs="+", choices=("train", "validation", "test"))
    parser.add_argument("--start", type=Path)
    args = parser.parse_args()
    if args.command == "fit" and args.start is None:
        parser.error("fit needs --start, the weights file whose cutoffs start the tuning")
    setup_logging(LOGS / "claim_extraction.log")
    if args.command == "sample":
        from .sample import sample
        sample(args.month, args.datasets, args.splits)
    elif args.command == "labels":
        from .labels import labels
        for dataset in args.datasets:
            labels(args.month, dataset)
    elif args.command == "fit":
        from .fit import fit
        fit(args.month, args.datasets, args.start)
    else:
        from .evaluate import evaluate
        for dataset in args.datasets:
            evaluate(args.month, dataset, args.split)


if __name__ == "__main__":
    main()
