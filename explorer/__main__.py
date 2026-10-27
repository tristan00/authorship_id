import argparse

from database import LOGS
from reddit_dumps import setup_logging


def main():
    parser = argparse.ArgumentParser(prog="explorer")
    parser.add_argument("command", choices=("prepare", "serve"))
    command = parser.parse_args().command
    setup_logging(LOGS / "explorer.log")
    if command == "prepare":
        from .prepare import prepare
        prepare()
    else:
        from .server import serve
        serve()


if __name__ == "__main__":
    main()
