import hashlib
import pickle
import re
import sys
import unicodedata
import zlib
from concurrent.futures import ThreadPoolExecutor
from re import _constants as C, _parser as parser

import hyperscan

from . import LOG, timed
from .config import CACHE, CHUNKS, WORKERS

FLAGS = hyperscan.HS_FLAG_PREFILTER | hyperscan.HS_FLAG_UTF8 | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_SINGLEMATCH | hyperscan.HS_FLAG_ALLOWEMPTY
CLASSES = ("w", "d", "s")
CODES = [code for code in range(0x80, 0x110000) if not 0xD800 <= code < 0xE000]
VERSION = b"\0".join([hyperscan.__version__.encode(), unicodedata.unidata_version.encode(), sys.version.encode()])


def mentioned(patterns):
    codes = set()

    def walk(items):
        for op, av in items:
            if op in (C.LITERAL, C.NOT_LITERAL):
                codes.add(av)
            elif op is C.RANGE:
                codes.update(range(av[0], av[1] + 1))
            elif op is C.IN:
                walk(av)
            elif op is C.SUBPATTERN:
                walk(av[3])
            elif op is C.BRANCH:
                for alternative in av[1]:
                    walk(alternative)
            elif op in (C.MAX_REPEAT, C.MIN_REPEAT, C.POSSESSIVE_REPEAT):
                walk(av[2])
            elif op in (C.ASSERT, C.ASSERT_NOT):
                walk(av[1])
            elif op is C.ATOMIC_GROUP:
                walk(av)

    for pattern in patterns:
        walk(list(parser.parse(pattern.pattern, pattern.flags)))
    return codes


def signature(char):
    return tuple(bool(re.fullmatch(rf"\{name}", char)) for name in CLASSES)


def cached(name, key, build):
    path = CACHE / f"{name}_{hashlib.sha256(key).hexdigest()[:24]}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    value = build()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(value))
    return value


def disagreeing():
    probe = hyperscan.Database()
    probe.compile(expressions=[rf"\A\{name}\z".encode() for name in CLASSES], ids=list(range(len(CLASSES))), elements=len(CLASSES),
                  flags=[hyperscan.HS_FLAG_UTF8 | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_SINGLEMATCH] * len(CLASSES))
    scratch = hyperscan.Scratch(probe)
    differing = set()
    for code in CODES:
        seen = set()
        probe.scan(chr(code).encode(), match_event_handler=noted, context=seen, scratch=scratch)
        if tuple(index in seen for index in range(len(CLASSES))) != signature(chr(code)):
            differing.add(code)
    return differing


@timed
def translation(patterns):
    differing = cached("classes", VERSION, disagreeing)
    used = mentioned(patterns)
    if stranded := differing & used:
        raise ValueError(f"patterns mention characters whose classes differ between python and hyperscan: {sorted(map(hex, stranded))[:20]}")
    needed = {code: signature(chr(code)) for code in differing}
    stand_ins, wanted = {}, set(needed.values())
    for code in CODES:
        if code not in differing and code not in used and (key := signature(chr(code))) in wanted and key not in stand_ins:
            stand_ins[key] = chr(code)
            if len(stand_ins) == len(wanted):
                break
    return {code: stand_ins[key] for code, key in needed.items()}


def rejected(expression):
    try:
        hyperscan.Database().compile(expressions=[expression], ids=[0], elements=1, flags=[FLAGS])
    except hyperscan.error as error:
        return str(error)
    return None


def chunk(entries):
    failed = [ident for ident, expression in entries if rejected(expression)]
    accepted = [(ident, expression) for ident, expression in entries if ident not in failed]
    database = hyperscan.Database()
    database.compile(expressions=[expression for _, expression in accepted], ids=[ident for ident, _ in accepted], elements=len(accepted), flags=[FLAGS] * len(accepted))
    return {"database": hyperscan.dumpb(database), "failed": failed}


def stored(entries):
    return cached("prefilter", b"\0".join([VERSION, *(str(ident).encode() + b"=" + expression for ident, expression in entries)]), lambda: chunk(entries))


@timed
def compiled(patterns):
    buckets = [[] for _ in range(CHUNKS)]
    for ident, pattern in enumerate(patterns):
        buckets[zlib.crc32(pattern.pattern.encode()) % CHUNKS].append((ident, pattern.pattern.encode()))
    with ThreadPoolExecutor(WORKERS) as pool:
        parts = list(pool.map(stored, buckets))
    failed = [ident for part in parts for ident in part["failed"]]
    for ident in failed:
        LOG.info("prefilter rejected index=%d pattern=%.120r", ident, patterns[ident].pattern)
    return [hyperscan.loadb(part["database"], hyperscan.HS_MODE_BLOCK) for part in parts], failed


class Prefilter:
    def __init__(self, patterns):
        self.databases, failed = compiled(patterns)
        self.translation = translation(patterns)
        self.always = frozenset(failed)
        self.scratches = [hyperscan.Scratch(database) for database in self.databases]

    def flagged(self, lowered):
        found = set(self.always)
        data = (lowered if lowered.isascii() else lowered.translate(self.translation)).encode()
        for database, scratch in zip(self.databases, self.scratches):
            database.scan(data, match_event_handler=noted, context=found, scratch=scratch)
        return found


def noted(ident, start, end, flags, found):
    found.add(ident)
