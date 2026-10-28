import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_extraction")
    parser.add_argument("command", choices=("sample", "labels", "fit", "evaluate"))
    parser.add_argument("--month", required=True)
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--split", default="validation")
    args = parser.parse_args()
    setup_logging(LOGS / "claim_extraction.log")
    if args.command == "sample":
        from .sample import sample
        sample(args.month, args.datasets)
    elif args.command == "labels":
        from .labels import labels
        labels(args.month, args.datasets[0])
    elif args.command == "fit":
        from .fit import fit
        fit(args.month, args.datasets[0])
    else:
        from .evaluate import evaluate
        evaluate(args.month, args.datasets[0], args.split)


if __name__ == "__main__":
    main()
