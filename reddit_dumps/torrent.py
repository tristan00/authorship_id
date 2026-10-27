import os
import time

import libtorrent as lt

from . import log, timed
from .config import ALERT_TIMEOUT, TORRENT_SETTINGS


@timed
def session():
    return lt.session({
        "user_agent": "reddit_dumps/libtorrent " + lt.__version__,
        "alert_mask": lt.alert_category.error | lt.alert_category.status | lt.alert_category.storage,
        **TORRENT_SETTINGS,
    })


def resume_path(save_path):
    return save_path.with_name(save_path.name + ".resume")


@timed
def add(ses, info, save_path, indices):
    resume = resume_path(save_path)
    params = lt.read_resume_data(resume.read_bytes()) if resume.exists() else lt.add_torrent_params()
    params.ti = info
    params.save_path = str(save_path)
    params.piece_priorities = []
    priorities = [0] * info.num_files()
    smallest = min(indices, key=info.layout().file_size)
    for index in indices:
        priorities[index] = 7 if index == smallest else 1
    params.file_priorities = priorities
    log.info("adding %s with %d files, resume data %s", info.info_hashes().v1, len(indices), resume.exists())
    return ses.add_torrent(params)


def completed(handle, info, indices):
    status = handle.status()
    if status.errc.value():
        raise RuntimeError(f"torrent {status.name} error on {status.error_file}: {status.errc.message()}")
    progress = handle.file_progress(lt.torrent_handle.piece_granularity)
    files = info.layout()
    return {index for index in indices if progress[index] == files.file_size(index)}


def log_alerts(alerts):
    for alert in alerts:
        if alert.category() & lt.alert_category.error:
            log.warning("libtorrent: %s", alert.message())


def wait_alert(ses, kind, failed, infohash):
    deadline = time.monotonic() + ALERT_TIMEOUT
    while time.monotonic() < deadline:
        ses.wait_for_alert(1000)
        alerts = ses.pop_alerts()
        log_alerts(alerts)
        for alert in alerts:
            if not isinstance(alert, (kind, failed)) or str(alert_infohash(alert)) != infohash:
                continue
            if isinstance(alert, failed):
                raise RuntimeError(alert.message())
            return alert
    raise TimeoutError(f"no {kind.__name__} for {infohash} within {ALERT_TIMEOUT}s")


def alert_infohash(alert):
    if isinstance(alert, lt.torrent_removed_alert):
        return alert.info_hashes.v1
    return alert.handle.info_hashes().v1


@timed
def remove(ses, handle, save_path):
    infohash = str(handle.info_hashes().v1)
    handle.save_resume_data()
    alert = wait_alert(ses, lt.save_resume_data_alert, lt.save_resume_data_failed_alert, infohash)
    resume = resume_path(save_path)
    temp = resume.with_name(resume.name + ".tmp")
    temp.write_bytes(lt.write_resume_data_buf(alert.params))
    os.replace(temp, resume)
    ses.remove_torrent(handle)
    wait_alert(ses, lt.torrent_removed_alert, (), infohash)
    log.info("removed torrent %s", infohash)


def describe(handle, started):
    status = handle.status()
    web = sum(1 for peer in handle.get_peer_info() if peer.connection_type in (lt.peer_info.web_seed, lt.peer_info.http_seed))
    average = status.total_payload_download / max(time.monotonic() - started, 1)
    eta = (status.total_wanted - status.total_wanted_done) / average / 60 if average else float("inf")
    return (
        f"{handle.info_hashes().v1} {status.state} {status.total_wanted_done / 1e9:.2f}/{status.total_wanted / 1e9:.2f} GB "
        f"now {status.download_rate / 1e6:.1f} MB/s average {average / 1e6:.1f} MB/s "
        f"peers={status.num_peers} seeds={status.num_seeds} web={web} eta={eta:.0f} min"
    )
