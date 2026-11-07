import hashlib
import pickle
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from re import _constants as C, _parser as parser

import hyperscan

from . import LOG, timed
from .config import CACHE, WORKERS

FLAGS = hyperscan.HS_FLAG_PREFILTER | hyperscan.HS_FLAG_UTF8 | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_SINGLEMATCH | hyperscan.HS_FLAG_ALLOWEMPTY
CLASSES = ("w", "d", "s")
CODES = [code for code in range(0x80, 0x110000) if not 0xD800 <= code < 0xE000]


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


def disagreeing():
    probe = hyperscan.Database()
    probe.compile(expressions=[rf"\A\{name}\z".encode() for name in CLASSES], ids=list(range(len(CLASSES))), elements=len(CLASSES),
                  flags=[hyperscan.HS_FLAG_UTF8 | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_SINGLEMATCH] * len(CLASSES))
    scratch = hyperscan.Scratch(probe)
    found = {}
    for code in CODES:
        char, seen = chr(code), set()
        probe.scan(char.encode(), match_event_handler=lambda ident, start, end, flags, context: context.add(ident), context=seen, scratch=scratch)
        found[code] = tuple(index in seen for index in range(len(CLASSES)))
    return {code for code in CODES if found[code] != signature(chr(code))}, found


def translation(patterns):
    differing, seen = disagreeing()
    used = mentioned(patterns)
    stranded = differing & used
    if stranded:
        raise ValueError(f"patterns mention characters whose classes differ between python and hyperscan: {sorted(map(hex, stranded))[:20]}")
    stand_ins = {}
    for code in CODES:
        if code not in differing and code not in used and (key := signature(chr(code))) not in stand_ins and seen[code] == key:
            stand_ins[key] = chr(code)
    return {code: stand_ins[signature(chr(code))] for code in differing}


def rejected(expression):
    try:
        hyperscan.Database().compile(expressions=[expression], ids=[0], elements=1, flags=[FLAGS])
    except hyperscan.error as error:
        return str(error)
    return None


@timed
def compiled(patterns):
    expressions = [pattern.pattern.encode() for pattern in patterns]
    key = hashlib.sha256(b"\0".join([hyperscan.__version__.encode(), unicodedata.unidata_version.encode(), sys.version.encode(), *expressions])).hexdigest()[:24]
    path = CACHE / f"prefilter_{key}.pkl"
    if path.exists():
        stored = pickle.loads(path.read_bytes())
        return hyperscan.loadb(stored["database"], hyperscan.HS_MODE_BLOCK), stored["failed"], stored["translation"]
    with ThreadPoolExecutor(WORKERS) as pool:
        failed = [index for index, error in enumerate(pool.map(rejected, expressions)) if error]
    for index in failed:
        LOG.info("prefilter rejected index=%d pattern=%.120r", index, patterns[index].pattern)
    accepted = [index for index in range(len(expressions)) if index not in failed]
    database = hyperscan.Database()
    database.compile(expressions=[expressions[index] for index in accepted], ids=accepted, elements=len(accepted), flags=[FLAGS] * len(accepted))
    table = translation(patterns)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps({"database": hyperscan.dumpb(database), "failed": failed, "translation": table}))
    LOG.info("prefilter compiled patterns=%d failed=%d translated=%d", len(accepted), len(failed), len(table))
    return database, failed, table


class Prefilter:
    def __init__(self, patterns):
        self.database, failed, self.translation = compiled(patterns)
        self.always = frozenset(failed)
        self.scratch = hyperscan.Scratch(self.database)

    def flagged(self, lowered):
        found = set(self.always)
        self.database.scan((lowered if lowered.isascii() else lowered.translate(self.translation)).encode(), match_event_handler=noted, context=found, scratch=self.scratch)
        return found


def noted(ident, start, end, flags, found):
    found.add(ident)
