import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="claim_consolidation")
    parser.add_argument("command", choices=("consolidate", "sample", "labels", "fit", "evaluate"))
    parser.add_argument("--month")
    parser.add_argument("--dataset")
    parser.add_argument("--authors", type=int)
    parser.add_argument("--min-claims", type=int)
    parser.add_argument("--split", choices=("train", "validation"), default="validation")
    args = parser.parse_args()
    if args.command == "sample" and not (args.month and args.dataset and args.authors and args.min_claims):
        parser.error("sample needs --month, --dataset, --authors and --min-claims")
    if args.command in ("labels", "fit", "evaluate") and not (args.month and args.dataset):
        parser.error(f"{args.command} needs --month and --dataset")
    setup_logging(LOGS / "claim_consolidation.log")
    if args.command == "consolidate":
        from .consolidate import consolidate
        consolidate()
    elif args.command == "sample":
        from .sample import sample
        sample(args.month, args.dataset, args.min_claims, args.authors)
    elif args.command == "labels":
        from .labels import labels
        labels(args.month, args.dataset)
    elif args.command == "fit":
        from .fit import fit
        fit(args.month, args.dataset)
    else:
        from .evaluate import evaluate
        evaluate(args.month, args.dataset, args.split)


if __name__ == "__main__":
    main()
