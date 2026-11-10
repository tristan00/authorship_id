import argparse
import json
from pathlib import Path

from database import use
from reddit_dumps import setup_logging

from .config import ROOT, data, model, text_data, text_model


def main():
    parser = argparse.ArgumentParser(prog="attribute_model")
    parser.add_argument("--database", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--data", type=Path)
    train = commands.add_parser("train")
    train.add_argument("--data", type=Path)
    train.add_argument("--output", type=Path)
    predict = commands.add_parser("predict")
    predict.add_argument("--model", type=Path)
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    user = commands.add_parser("user")
    user.add_argument("author")
    user.add_argument("--model", type=Path)
    table = commands.add_parser("table")
    table.add_argument("--model", type=Path)
    commands.add_parser("prepare-text")
    commands.add_parser("train-text")
    text = commands.add_parser("text")
    text.add_argument("text")
    text.add_argument("--model", type=Path)
    args = parser.parse_args()
    setup_logging(ROOT / "attribute_model.log")
    use(args.database)
    for name, value in (("data", data), ("output", model)):
        if getattr(args, name, False) is None:
            setattr(args, name, value())
    if getattr(args, "model", False) is None:
        args.model = text_model() if args.command == "text" else model()
    if args.command == "prepare":
        from .data import prepare
        result = prepare(args.data)
    elif args.command == "train":
        from .train import train
        result = train(args.data, args.output)
    elif args.command == "predict":
        from .predict import predict_file
        result = predict_file(args.model, args.input, args.output)
    elif args.command == "user":
        from .predict import predict_user
        result = predict_user(args.model, args.author)
    elif args.command == "prepare-text":
        from .text import prepare_text
        result = prepare_text(text_data(), data())
    elif args.command == "train-text":
        from .config import TEXT_PARAMETERS
        from .train import train
        result = train(text_data(), text_model(), TEXT_PARAMETERS)
    elif args.command == "text":
        from .text import predict_text
        result = predict_text(args.model, args.text)
    else:
        from .predict import predict_table
        result = predict_table(args.model)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
