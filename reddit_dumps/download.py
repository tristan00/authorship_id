import shutil
import time
from dataclasses import dataclass

from database import DUMPS

from . import catalog, log, timed, torrent
from .config import KINDS, MAX_ACTIVE_MONTHS, PROGRESS_SECONDS


@dataclass
class Job:
    month: str
    infohash: str
    info: object
    files: dict
    handle: object = None
    started: float = 0.0

    @property
    def save_path(self):
        return DUMPS / self.infohash


@timed
def build_jobs(months):
    entries = catalog.load_catalog()
    infos = {}
    jobs = []
    for month in months:
        infohash = catalog.resolve(entries, month)
        if infohash not in infos:
            infos[infohash] = catalog.torrent_info(infohash, DUMPS)
        info = infos[infohash]
        files = {kind: catalog.file_index(info, month, kind) for kind in KINDS}
        jobs.append(Job(month, infohash, info, files))
        log.info("%s -> %s %s", month, infohash,
                 {info.layout().file_path(i): f"{info.layout().file_size(i) / 1e9:.2f} GB" for i in files.values()})
    return jobs


def start_jobs(ses, pending, active):
    for job in list(pending):
        if len(active) >= MAX_ACTIVE_MONTHS:
            return
        if any(other.infohash == job.infohash for other in active):
            continue
        pending.remove(job)
        job.handle = torrent.add(ses, job.info, job.save_path, job.files.values())
        job.started = time.monotonic()
        active.append(job)
        log.info("downloading %s", job.month)


@timed
def download(months):
    ses = torrent.session()
    pending, active = build_jobs(months), []
    last = 0.0
    while pending or active:
        start_jobs(ses, pending, active)
        torrent.log_alerts(ses.pop_alerts())
        for job in list(active):
            if len(torrent.completed(job.handle, job.info, job.files.values())) == len(job.files):
                torrent.remove(ses, job.handle, job.save_path)
                active.remove(job)
                log.info("%s done in %.0f min", job.month, (time.monotonic() - job.started) / 60)
        if time.monotonic() - last >= PROGRESS_SECONDS:
            last = time.monotonic()
            for job in active:
                log.info("%s %s", job.month, torrent.describe(job.handle, job.started))
            log.info("pending months %d, active %d", len(pending), len(active))
        time.sleep(1)


def files(month):
    return list(DUMPS.glob(f"*/reddit/*/R[CS]_{month}.zst"))


@timed
def delete(month):
    for path in files(month):
        path.unlink()
        log.info("deleted %s", path)
        save_path = path.parents[2]
        if not any(save_path.rglob("*.zst")):
            shutil.rmtree(save_path)
            torrent.resume_path(save_path).unlink(missing_ok=True)
            save_path.with_name(save_path.name + ".torrent").unlink(missing_ok=True)
            log.info("deleted torrent %s", save_path.name)
