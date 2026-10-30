import argparse
import json
from pathlib import Path

from reddit_dumps import setup_logging

from . import write_json
from .config import VECTOR_STORE


def main():
    parser = argparse.ArgumentParser(prog="author_encoder", description="Pretrained LUAR user vectors and cosine similarity.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("download", help="Download the pinned pretrained model and tokenizer.")
    update = commands.add_parser("update", help="Encode the bodies missing from the text vector store.")
    update.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    commands.add_parser("users", help="Add the loaded months missing from the user vectors, recomputing only the users they change.")
    encode = commands.add_parser("encode", help="Read JSONL users and write JSONL vectors.", description='Each input line: {"author": "name", "texts": ["text", ...]}. Each author needs at least one usable text; up to 256 are sampled reproducibly. Output includes the 512-dimensional vector and sampled input indices.')
    encode.add_argument("--input", type=Path, required=True)
    encode.add_argument("--output", type=Path, required=True, help="A new JSONL output file.")
    encode.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    for name, description in (("similar", "Find the closest indexed users by cosine similarity."), ("vector", "Read a user's saved vector and sampled record IDs.")):
        command = commands.add_parser(name, help=description)
        command.add_argument("author")
        command.add_argument("--store", type=Path, default=VECTOR_STORE)
        command.add_argument("--output", type=Path, help="Write JSON to this file instead of stdout.")
        if name == "similar":
            command.add_argument("--limit", type=int, default=50, choices=range(1, 201), metavar="1..200")
    args = parser.parse_args()
    root = args.output.parent if args.command == "encode" else getattr(args, "store", VECTOR_STORE).parent
    root.mkdir(parents=True, exist_ok=True)
    setup_logging(root / f"{args.command}.log")
    if args.command == "download":
        from .model import download
        result = {"model_directory": download()}
    elif args.command == "update":
        from .update import update
        result = update(args.device)
    elif args.command == "users":
        from .update import users
        result = users()
    elif args.command == "encode":
        from .predict import encode_file
        result = encode_file(args.input, args.output, args.device)
    else:
        from .index import similar, users, vector
        if users(args.store) is None:
            parser.error("The user vector store is not built; run users first.")
        result = similar(args.author, args.limit, args.store) if args.command == "similar" else vector(args.author, args.store)
        if result is None:
            parser.error(f"No vector for {args.author}; users need at least one usable text.")
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
            return
    print(json.dumps(result))


if __name__ == "__main__":
    main()
