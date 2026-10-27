import os
import re
import urllib.request
import xml.etree.ElementTree as ET

import libtorrent as lt

from . import log, timed
from .config import CATALOG_URL, HTTP_TIMEOUT, TORRENT_URL, USER_AGENT

TITLE = re.compile(r"Reddit comments/submissions (\d{4}-\d{2})(?: to (\d{4}-\d{2}))?")
MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
PREFIX = {"comments": "RC", "submissions": "RS"}


def month_index(month):
    if not MONTH.fullmatch(month):
        raise ValueError(f"bad month {month!r}, expected YYYY-MM")
    return int(month[:4]) * 12 + int(month[5:]) - 1


def month_range(start, end):
    first, last = month_index(start), month_index(end)
    if first > last:
        raise ValueError(f"start {start} is after end {end}")
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in range(first, last + 1)]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return response.read()


@timed
def load_catalog():
    entries = []
    for item in ET.fromstring(fetch(CATALOG_URL)).iter("item"):
        match = TITLE.fullmatch(item.findtext("title"))
        if match:
            entries.append((match[1], match[2] or match[1], item.findtext("infohash").lower()))
    log.info("catalog lists %d reddit torrents", len(entries))
    return entries


def resolve(entries, month):
    covering = sorted(
        (month_index(end) - month_index(start), infohash)
        for start, end, infohash in entries
        if start <= month <= end
    )
    if not covering:
        raise LookupError(f"no torrent in catalog covers {month}")
    if len(covering) > 1 and covering[0][0] == covering[1][0]:
        raise LookupError(f"several equally narrow torrents cover {month}: {covering}")
    return covering[0][1]


@timed
def torrent_info(infohash, dumps):
    path = dumps / f"{infohash}.torrent"
    if not path.exists():
        dumps.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(fetch(TORRENT_URL.format(infohash)))
        os.replace(temp, path)
    info = lt.torrent_info(str(path))
    if str(info.info_hashes().v1) != infohash:
        raise ValueError(f"{path} has infohash {info.info_hashes().v1}, expected {infohash}")
    return info


def file_index(info, month, kind):
    wanted = f"reddit/{kind}/{PREFIX[kind]}_{month}.zst"
    files = info.layout()
    matches = [i for i in range(files.num_files()) if files.file_path(i).replace("\\", "/") == wanted]
    if len(matches) != 1:
        raise LookupError(f"{wanted} found {len(matches)} times in torrent {info.info_hashes().v1}")
    return matches[0]
