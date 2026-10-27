CATALOG_URL = "https://academictorrents.com/database.xml"
TORRENT_URL = "https://academictorrents.com/download/{}.torrent"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

KINDS = ("submissions", "comments")
MAX_ACTIVE_MONTHS = 2
PROGRESS_SECONDS = 30

ALERT_TIMEOUT = 120
HTTP_TIMEOUT = 120
TORRENT_SETTINGS = {
    "listen_interfaces": "0.0.0.0:6881",
    "enable_upnp": False,
    "enable_natpmp": False,
    "urlseed_pipeline_size": 10,
    "urlseed_max_request_bytes": 64 * 1024 * 1024,
}
MAX_WINDOW_SIZE = 2**31

CHUNK_SIZE = 2**20
READ_SIZE = 2**22
SLOTS = 4
