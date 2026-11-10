import argparse

from reddit_dumps import setup_logging

from . import LOGS, use


def main():
    parser = argparse.ArgumentParser(prog="database")
    parser.add_argument("command", choices=("setup", "add", "counts"))
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    setup_logging(LOGS / "database.log")
    use(args.database)
    if args.command == "setup":
        from .server import setup
        setup()
    elif args.command == "counts":
        from .server import counts
        counts()
    else:
        from .load import add
        add(args.start, args.end)


if __name__ == "__main__":
    main()
