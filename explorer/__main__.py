import argparse
import logging
import socket
import threading
from http.server import ThreadingHTTPServer

from database import LOGS, use
from reddit_dumps import setup_logging, timed

from .store import connection
from .web import PORT, Handler

LOG = logging.getLogger("explorer")


class IPv6Server(ThreadingHTTPServer):
    address_family = socket.AF_INET6


@timed
def start():
    connection().command("SELECT 1")
    servers = [ThreadingHTTPServer(("127.0.0.1", PORT), Handler), IPv6Server(("::1", PORT), Handler)]
    threads = [threading.Thread(target=server.serve_forever, name=f"serve-{server.server_address[0]}") for server in servers]
    for thread in threads:
        thread.start()
    LOG.info("explorer listening on 127.0.0.1:%d and [::1]:%d", PORT, PORT)
    return threads


def main():
    parser = argparse.ArgumentParser(prog="explorer")
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    setup_logging(LOGS / "explorer.log")
    use(args.database)
    for thread in start():
        thread.join()


main()
