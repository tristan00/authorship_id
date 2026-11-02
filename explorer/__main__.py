from database import LOGS
from reddit_dumps import setup_logging

from .server import serve


def main():
    setup_logging(LOGS / "explorer.log")
    serve()


if __name__ == "__main__":
    main()
