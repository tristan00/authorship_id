import msvcrt
import os
import time
from pathlib import Path

from . import LOG

ROOT = Path(r"C:\reddit_data\lock")
LOCK = ROOT / "intensive.lock"
QUEUE = ROOT / "queue"


def alive(path):
    try:
        with open(path, "r+") as probe:
            msvcrt.locking(probe.fileno(), msvcrt.LK_NBLCK, 1)
            msvcrt.locking(probe.fileno(), msvcrt.LK_UNLCK, 1)
    except PermissionError:
        return True
    except OSError:
        return path.exists()
    path.unlink(missing_ok=True)
    return False


class Hold:
    def __init__(self, name):
        self.name = name
        QUEUE.mkdir(parents=True, exist_ok=True)
        self.ticket = QUEUE / f"{'0' if os.environ.get('LOCK_PRIORITY') == 'high' else ''}{time.time_ns()}-{os.getpid()}"
        self.mark = open(self.ticket, "w")
        msvcrt.locking(self.mark.fileno(), msvcrt.LK_NBLCK, 1)
        started = time.perf_counter()
        while any(other.name < self.ticket.name and alive(other) for other in QUEUE.iterdir()):
            time.sleep(1)
        self.stream = open(LOCK, "a+")
        while True:
            try:
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                time.sleep(1)
        self.acquired = time.perf_counter()
        LOG.info("lock %s waited %.0fs", name, self.acquired - started)

    def close(self):
        self.stream.close()
        self.mark.close()
        self.ticket.unlink(missing_ok=True)
        LOG.info("lock %s held %.0fs", self.name, time.perf_counter() - self.acquired)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
