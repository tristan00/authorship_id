import subprocess
import time

from . import LOG, NO_AUTHOR, client, selected, timed
from .config import DISTRO, SERVER_MEMORY

WSL = ("wsl.exe", "-d", DISTRO, "-u", "root", "--", "bash", "-lc")
INSTALL = """
set -e
if ! command -v clickhouse-server >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq apt-transport-https ca-certificates curl gnupg
  curl -fsSL https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key | gpg --dearmor --yes -o /usr/share/keyrings/clickhouse-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" > /etc/apt/sources.list.d/clickhouse.list
  apt-get update -qq
  apt-get install -y -qq clickhouse-server clickhouse-client
fi
cat > /etc/clickhouse-server/config.d/authorship.xml <<EOF
<clickhouse>
  <listen_host>0.0.0.0</listen_host>
  <max_server_memory_usage>{memory}</max_server_memory_usage>
</clickhouse>
EOF
systemctl enable clickhouse-server
systemctl restart clickhouse-server
"""
TABLES = [
    """CREATE TABLE IF NOT EXISTS records (
        created_utc DateTime('UTC') CODEC(Delta, ZSTD(1)),
        record_id String CODEC(ZSTD(1)),
        record_type LowCardinality(String),
        author String CODEC(ZSTD(1)),
        subreddit String CODEC(ZSTD(1)),
        author_fullname Nullable(String) CODEC(ZSTD(1)),
        link_id String CODEC(ZSTD(1)),
        parent_id Nullable(String) CODEC(ZSTD(1)),
        author_flair_text Nullable(String) CODEC(ZSTD(1)),
        link_flair_text Nullable(String) CODEC(ZSTD(1)),
        post_hint LowCardinality(Nullable(String)),
        crosspost_parent Nullable(String) CODEC(ZSTD(1)),
        is_submitter Nullable(Bool),
        over_18 Nullable(Bool),
        is_self Nullable(Bool),
        text_status LowCardinality(String),
        text_sha256 FixedString(32)
    ) ENGINE = MergeTree ORDER BY (author, created_utc)""",
    """CREATE TABLE IF NOT EXISTS records_by_subreddit (
        subreddit String CODEC(ZSTD(1)),
        created_utc DateTime('UTC') CODEC(Delta, ZSTD(1)),
        record_type LowCardinality(String)
    ) ENGINE = MergeTree ORDER BY (subreddit, created_utc)""",
    "CREATE MATERIALIZED VIEW IF NOT EXISTS records_by_subreddit_feed TO records_by_subreddit AS SELECT subreddit, created_utc, record_type FROM records",
    """CREATE TABLE IF NOT EXISTS bodies (
        text_sha256 FixedString(32),
        text String CODEC(ZSTD(3)),
        words UInt32
    ) ENGINE = MergeTree ORDER BY text_sha256 SETTINGS index_granularity = 1024""",
    "CREATE TABLE IF NOT EXISTS months (month String, records UInt64, loaded_at DateTime('UTC') DEFAULT now()) ENGINE = MergeTree ORDER BY month",
    "CREATE TABLE IF NOT EXISTS author_counts (author String, texts UInt64, posts UInt64, first_seen DateTime('UTC'), last_seen DateTime('UTC')) ENGINE = MergeTree ORDER BY author",
    "CREATE TABLE IF NOT EXISTS subreddit_counts (subreddit String, texts UInt64, posts UInt64, first_seen DateTime('UTC'), last_seen DateTime('UTC')) ENGINE = MergeTree ORDER BY subreddit",
]
COUNTS = {
    "author": f"SELECT author, count() AS texts, countIf(record_type = 'post') AS posts, min(created_utc) AS first_seen, max(created_utc) AS last_seen "
              f"FROM records WHERE author NOT IN {NO_AUTHOR} GROUP BY author",
    "subreddit": "SELECT subreddit, count() AS texts, countIf(record_type = 'post') AS posts, min(created_utc) AS first_seen, max(created_utc) AS last_seen "
                 "FROM records_by_subreddit GROUP BY subreddit",
}


@timed
def setup():
    subprocess.run([*WSL, INSTALL.replace("{memory}", str(SERVER_MEMORY))], check=True)
    started = time.perf_counter()
    while True:
        try:
            LOG.info("clickhouse %s is up", client(database="default").command("SELECT version()"))
            break
        except Exception:
            if time.perf_counter() - started > 120:
                raise
            time.sleep(1)
    schema()


@timed
def schema():
    client(database="default").command(f"CREATE DATABASE IF NOT EXISTS {selected()}")
    db = client()
    for statement in TABLES:
        db.command(statement)
    for (name,) in db.query(f"SELECT name FROM system.tables WHERE database = '{selected()}' AND startsWith(name, '_tmp_replace_')").result_rows:
        db.command(f"DROP TABLE {name}")
        LOG.info("dropped leftover %s", name)


@timed
def counts():
    db = client()
    for key, query in COUNTS.items():
        db.command(f"DROP TABLE IF EXISTS {key}_counts_next")
        db.command(f"CREATE TABLE {key}_counts_next AS {key}_counts")
        db.command(f"INSERT INTO {key}_counts_next {query}")
        db.command(f"EXCHANGE TABLES {key}_counts_next AND {key}_counts")
        db.command(f"DROP TABLE {key}_counts_next")
        LOG.info("%s_counts rows=%s", key, db.command(f"SELECT count() FROM {key}_counts"))
