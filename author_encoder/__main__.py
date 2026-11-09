import argparse
import json
from pathlib import Path

from database import LOGS
from reddit_dumps import setup_logging

from . import write_json
from .config import TEXTS_PER_USER


def main():
    parser = argparse.ArgumentParser(prog="author_encoder", description="Pretrained LUAR author vectors and cosine similarity.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("download", help="Download the pinned pretrained model and tokenizer.")
    commands.add_parser("texts", help=f"Build author_texts with up to {TEXTS_PER_USER} distinct readable texts per author, unless its loaded months and code are unchanged.")
    vectors = commands.add_parser("vectors", help="Encode author_texts into author_vectors, resuming by author part and restarting when the texts or encoder change.")
    vectors.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    encode = commands.add_parser("encode", help="Read JSONL users and write JSONL vectors.", description=f'Each input line: {{"author": "name", "texts": ["text", ...]}}. Each author needs at least one usable text; up to {TEXTS_PER_USER} are sampled reproducibly. Output includes the 512-dimensional vector and sampled input indices.')
    encode.add_argument("--input", type=Path, required=True)
    encode.add_argument("--output", type=Path, required=True, help="A new JSONL output file.")
    encode.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    for name, description in (("similar", "Find the closest authors by cosine similarity."), ("vector", "Read an author's saved vector.")):
        command = commands.add_parser(name, help=description)
        command.add_argument("author")
        command.add_argument("--output", type=Path, help="Write JSON to this file instead of stdout.")
        if name == "similar":
            command.add_argument("--limit", type=int, default=50, choices=range(1, 201), metavar="1..200")
    args = parser.parse_args()
    setup_logging(LOGS / f"author_encoder_{args.command}.log")
    if args.command == "download":
        from .model import download
        result = {"model_directory": download()}
    elif args.command == "texts":
        from .store import build
        result = build()
    elif args.command == "vectors":
        from .predict import encode_store
        result = encode_store(args.device)
    elif args.command == "encode":
        from .predict import encode_file
        result = encode_file(args.input, args.output, args.device)
    else:
        from .store import similar, vector
        result = similar(args.author, args.limit) if args.command == "similar" else vector(args.author)
        if result is None:
            parser.error(f"No vector for {args.author}.")
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
            return
    print(json.dumps(result))


if __name__ == "__main__":
    main()
