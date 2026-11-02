import argparse
import json
from pathlib import Path

from reddit_dumps import setup_logging

from .config import DATA, MODEL, ROOT, TARGETS, TEXT_DATA, TEXT_MODEL, TEXT_PARAMETERS, TUNE, read_targets


def main():
    parser = argparse.ArgumentParser(prog="attribute_model")
    commands = parser.add_subparsers(dest="command", required=True)
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
    update = commands.add_parser("update")
    subreddits = commands.add_parser("subreddits")
    text_prepare = commands.add_parser("text-prepare")
    text_train = commands.add_parser("text-train")
    tune = commands.add_parser("tune")
    text_tune = commands.add_parser("text-tune")
    text = commands.add_parser("text")
    text.add_argument("text")
    for command in (prepare, train, predict, user, table, update, subreddits, text_prepare, text_train, tune, text_tune, text):
        command.add_argument("--targets", type=Path, default=TARGETS)
    args = parser.parse_args()
    targets = read_targets(args.targets)
    setup_logging(ROOT / "attribute_model.log")
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
    elif args.command == "subreddits":
        from .subreddits import build
        result = build()
    elif args.command == "update":
        from .update import update
        result = update(targets)
    elif args.command == "text-prepare":
        from .text import prepare
        result = prepare(TEXT_DATA, targets)
    elif args.command == "text-train":
        from .text import load_text
        from .train import train
        result = train(TEXT_DATA, TEXT_MODEL, targets, TEXT_PARAMETERS, load_text)
    elif args.command == "tune":
        from .train import load_data
        from .tune import tune as run
        result = run(targets, load_data, DATA, TUNE / "account.json")
    elif args.command == "text-tune":
        from .text import load_text
        from .tune import tune as run
        result = run(targets, load_text, TEXT_DATA, TUNE / "text.json")
    else:
        from .text import predict_text
        result = predict_text(TEXT_MODEL, targets, args.text)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
