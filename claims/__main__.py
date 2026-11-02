import argparse
import json

from database import LOGS
from reddit_dumps import setup_logging

from .config import FLAIR_AUTHORS


def main():
    parser = argparse.ArgumentParser(prog="claims")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample")
    sample.add_argument("--uniform", type=int, required=True)
    sample.add_argument("--authors", type=int, required=True)
    annotate = commands.add_parser("annotate")
    annotate.add_argument("dataset")
    commands.add_parser("fandom")
    gold = commands.add_parser("text-gold")
    gold.add_argument("--dataset", default="uniform")
    gold.add_argument("--limit", type=int, required=True)
    commands.add_parser("verify")
    commands.add_parser("cotrain")
    flairs = commands.add_parser("flairs")
    flairs.add_argument("--minimum-authors", type=int, default=FLAIR_AUTHORS)
    commands.add_parser("flairs-load")
    commands.add_parser("names")
    commands.add_parser("places")
    rename = commands.add_parser("rename")
    rename.add_argument("old")
    rename.add_argument("new")
    commands.add_parser("train")
    extract = commands.add_parser("extract")
    extract.add_argument("--reset", action="store_true")
    commands.add_parser("consolidate")
    commands.add_parser("redecide")
    commands.add_parser("extractor-report")
    commands.add_parser("author-gold")
    commands.add_parser("thresholds")
    args = parser.parse_args()
    setup_logging(LOGS / "claims.log")
    result = None
    if args.command == "sample":
        from .sample import sample as run
        run(args.uniform, args.authors)
    elif args.command == "annotate":
        from .annotate import extract as run
        run(args.dataset)
    elif args.command == "fandom":
        from .annotate import fandom as run
        run()
    elif args.command == "text-gold":
        from .annotate import gold as run
        run(args.dataset, args.limit)
    elif args.command == "flairs":
        from .flairs import annotate as run
        run(args.minimum_authors)
    elif args.command == "flairs-load":
        from .flairs import load
        load()
    elif args.command == "names":
        from .names import annotate, apply, extracted
        annotate(extracted())
        apply()
    elif args.command == "places":
        from .places import annotate as run
        run()
    elif args.command == "rename":
        from .rename import rename as run
        result = run(args.old, args.new)
    elif args.command == "verify":
        from .annotate import verify
        verify()
    elif args.command == "cotrain":
        from .cotrain import propose
        propose()
    elif args.command == "train":
        from .extractor import fit
        fit()
    elif args.command == "extract":
        from .extract import run
        run(args.reset)
    elif args.command == "consolidate":
        from .consolidate import consolidate
        consolidate()
    elif args.command == "redecide":
        from .consolidate import redecide
        redecide()
    elif args.command == "extractor-report":
        from .evaluate import extractor
        result = extractor()
    elif args.command == "author-gold":
        from .evaluate import author_gold
        author_gold()
    else:
        from .evaluate import thresholds
        result = thresholds()
    if result is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
