import functools
import inspect
import logging
import time

log = logging.getLogger("reddit_dumps")


def setup_logging(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(processName)s %(threadName)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(path, encoding="utf-8")],
        force=True,
    )


def timed(fn):
    name = f"{fn.__module__}.{fn.__qualname__}"

    if inspect.isgeneratorfunction(fn):
        @functools.wraps(fn)
        def generator(*args, **kwargs):
            log.info("enter %s", name)
            start = time.perf_counter()
            try:
                return (yield from fn(*args, **kwargs))
            finally:
                log.info("exit %s %.2fs", name, time.perf_counter() - start)

        return generator

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        log.info("enter %s", name)
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            log.info("exit %s %.2fs", name, time.perf_counter() - start)

    return wrapper
