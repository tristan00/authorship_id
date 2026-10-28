import argparse
from pathlib import Path

from database import LOGS
from reddit_dumps import setup_logging

from .config import EXTRACT_WORKERS


def main():
    parser = argparse.ArgumentParser(prog="claim_extraction")
    parser.add_argument("command", choices=("sample", "labels", "fit", "evaluate", "extract"))
    parser.add_argument("--month", required=True)
    parser.add_argument("--datasets", nargs="+")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--splits", nargs="+", choices=("train", "validation", "test"))
    parser.add_argument("--start", type=Path)
    parser.add_argument("--workers", type=int, default=EXTRACT_WORKERS)
    parser.add_argument("--pages", type=int, nargs=2)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.command == "fit" and args.start is None:
        parser.error("fit needs --start, the weights file whose cutoffs start the tuning")
    if args.command != "extract" and not args.datasets:
        parser.error(f"{args.command} needs --datasets")
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
    elif args.command == "evaluate":
        from .evaluate import evaluate
        for dataset in args.datasets:
            evaluate(args.month, dataset, args.split)
    else:
        from .run import run
        run(args.month, args.workers, args.pages, args.reset)


if __name__ == "__main__":
    main()
