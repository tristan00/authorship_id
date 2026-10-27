import argparse
from pathlib import Path

from reddit_dumps import setup_logging

from .config import ROOT


def main():
    parser = argparse.ArgumentParser(prog="demographic_model")
    parser.add_argument("command", choices=("train", "test"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(root.parent / f"{root.name}_{args.command}.log")
    if args.command == "train":
        from .train import train
        train(root)
    else:
        from .evaluate import test
        test(root)


if __name__ == "__main__":
    main()
