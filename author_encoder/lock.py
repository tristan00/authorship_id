import msvcrt
from contextlib import contextmanager
from time import perf_counter

from . import LOG


@contextmanager
def index_lock(path):
    started = perf_counter()
    lock = path.with_suffix(path.suffix + ".lock")
    with lock.open("a+b") as handle:
        if lock.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError(f"Another encoder process is writing {path}") from error
        try:
            LOG.info("index lock acquired path=%s", path)
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            LOG.info("index lock released seconds=%.3f", perf_counter() - started)
