import argparse
import json
from pathlib import Path

from reddit_dumps import setup_logging

from .config import DATA, MODEL, ROOT, TARGETS, TUNE, read_targets


def main():
    parser = argparse.ArgumentParser(prog="attribute_model")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("subreddits")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--data", type=Path, default=DATA)
    train = commands.add_parser("train")
    train.add_argument("--data", type=Path, default=DATA)
    train.add_argument("--output", type=Path, default=MODEL)
    predict = commands.add_parser("predict")
    predict.add_argument("--model", type=Path, default=MODEL)
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    user = commands.add_parser("user")
    user.add_argument("author")
    user.add_argument("--model", type=Path, default=MODEL)
    table = commands.add_parser("table")
    table.add_argument("--model", type=Path, default=MODEL)
    tune = commands.add_parser("tune")
    tune.add_argument("--data", type=Path, default=DATA)
    for command in (prepare, train, predict, user, table, tune):
        command.add_argument("--targets", type=Path, default=TARGETS)
    args = parser.parse_args()
    setup_logging(ROOT / "attribute_model.log")
    if args.command == "subreddits":
        from .features import build
        print(json.dumps(build()))
        return
    targets = read_targets(args.targets)
    if args.command == "prepare":
        from .data import prepare
        result = prepare(args.data, targets)
    elif args.command == "train":
        from .train import train
        result = train(args.data, args.output, targets)
    elif args.command == "predict":
        from .predict import predict_file
        result = predict_file(args.model, targets, args.input, args.output)
    elif args.command == "user":
        from .predict import predict_user
        result = predict_user(args.model, targets, args.author)
    elif args.command == "table":
        from .predict import predict_table
        result = predict_table(args.model, targets)
    else:
        from .tune import tune as run
        result = run(targets, args.data, TUNE / "account.json")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
