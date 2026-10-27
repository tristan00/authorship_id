import argparse

from reddit_dumps import setup_logging

from . import LOGS


def main():
    parser = argparse.ArgumentParser(prog="database")
    parser.add_argument("command", choices=("build", "add"))
    parser.add_argument("--months", nargs="+")
    args = parser.parse_args()
    setup_logging(LOGS / "database.log")
    if args.command == "build":
        from .server import init
        init()
    else:
        from .load import add
        add(args.months)


if __name__ == "__main__":
    main()
