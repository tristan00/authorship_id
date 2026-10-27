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
    index = commands.add_parser("index", help="Read the database, sample 64 usable texts per eligible user and write a resumable SQLite vector store.")
    index.add_argument("--store", type=Path, default=VECTOR_STORE)
    index.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    encode = commands.add_parser("encode", help="Read JSONL users and write JSONL vectors.", description='Each input line: {"author": "name", "texts": ["text", ...]}. Each author needs at least 64 usable texts; 64 are sampled reproducibly. Output includes the 512-dimensional vector and sampled input indices.')
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
    elif args.command == "index":
        from .index import build
        from .store import status
        build(args.store, args.device)
        result = status(args.store)
    elif args.command == "encode":
        from .predict import encode_file
        result = encode_file(args.input, args.output, args.device)
    else:
        from .store import status, store
        if status(args.store)["status"] != "ready":
            parser.error("The vector store is not ready; run index first.")
        index = store(args.store)
        result = index.search(args.author, args.limit) if args.command == "similar" else index.vector(args.author)
        if result is None:
            parser.error(f"No vector for {args.author}; users need at least 64 usable texts.")
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
            return
    print(json.dumps(result))


if __name__ == "__main__":
    main()
