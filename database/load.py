from reddit_dumps.catalog import month_range

from . import DUMPS, LOG, bounds, client, in_range, sha_ranges, timed

KINDS = {"comment": ("comments", "RC"), "post": ("submissions", "RS")}
STAGE = "CREATE TABLE bodies_stage (text_sha256 FixedString(32), text String CODEC(ZSTD(1)), words UInt32) ENGINE = MergeTree ORDER BY text_sha256"


def dumps(month):
    found = {}
    for kind, (folder, prefix) in KINDS.items():
        paths = list(DUMPS.glob(f"*/reddit/{folder}/{prefix}_{month}.zst"))
        if len(paths) != 1:
            raise LookupError(f"{prefix}_{month}.zst found {len(paths)} times under {DUMPS}")
        found[kind] = paths[0]
    return found


@timed
def parse_month(month):
    from pipeline.run import rust
    files = dumps(month)
    parsed = int(rust("database/loader", "loader", "month", "database.log", "--comments", str(files["comment"]), "--posts", str(files["post"])))
    LOG.info("%s parsed %s records", month, parsed)
    return parsed


@timed
def merge_bodies():
    db = client(optimize_aggregation_in_order=1)
    for low, high in sha_ranges():
        db.command(f"INSERT INTO bodies SELECT text_sha256, any(text), any(words) FROM bodies_stage WHERE {in_range('text_sha256', low, high)} "
                   f"AND text_sha256 NOT IN (SELECT text_sha256 FROM bodies WHERE {in_range('text_sha256', low, high)}) GROUP BY text_sha256")
    LOG.info("bodies rows=%s", db.command("SELECT count() FROM bodies"))


@timed
def unload(month):
    low, high = bounds(month)
    window = f"created_utc >= {low} AND created_utc < {high}"
    db = client()
    db.command("DROP TABLE IF EXISTS reload_candidates")
    db.command(f"CREATE TABLE reload_candidates ENGINE = MergeTree ORDER BY text_sha256 AS SELECT DISTINCT text_sha256 FROM records WHERE {window}")
    db.command(f"DELETE FROM records WHERE {window}")
    db.command(f"DELETE FROM records_by_subreddit WHERE {window}")
    db.command(f"DELETE FROM months WHERE month = '{month}'")
    LOG.info("%s unloaded, candidates=%s", month, db.command("SELECT count() FROM reload_candidates"))


@timed
def collect_orphans():
    db = client()
    db.command("DROP TABLE IF EXISTS reload_orphans")
    db.command("CREATE TABLE reload_orphans ENGINE = MergeTree ORDER BY text_sha256 AS SELECT text_sha256 FROM reload_candidates WHERE text_sha256 NOT IN "
               "(SELECT text_sha256 FROM records WHERE text_sha256 IN (SELECT text_sha256 FROM reload_candidates))")
    db.command("DELETE FROM bodies WHERE text_sha256 IN (SELECT text_sha256 FROM reload_orphans)")
    LOG.info("orphan bodies removed=%s", db.command("SELECT count() FROM reload_orphans"))
    db.command("DROP TABLE reload_orphans")
    db.command("DROP TABLE reload_candidates")


@timed
def load_month(month):
    low, high = bounds(month)
    db = client()
    reload = db.command(f"SELECT count() FROM records WHERE created_utc >= {low} AND created_utc < {high}") > 0
    if reload:
        unload(month)
    db.command("DROP TABLE IF EXISTS bodies_stage")
    db.command(STAGE)
    parsed = parse_month(month)
    stored = db.command(f"SELECT count() FROM records WHERE created_utc >= {low} AND created_utc < {high}")
    if stored != parsed:
        raise ValueError(f"{month} parsed {parsed} records but records holds {stored} in its range")
    merge_bodies()
    db.command("DROP TABLE bodies_stage")
    if reload:
        collect_orphans()
    db.command(f"INSERT INTO months (month, records) VALUES ('{month}', {parsed})")
    LOG.info("%s loaded %s records", month, parsed)


@timed
def add(start, end):
    from .server import counts, schema
    schema()
    for month in month_range(start, end):
        load_month(month)
    counts()
