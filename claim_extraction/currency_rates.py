import sys
import urllib.request
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from . import timed

ENDPOINT = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
HEADERS = {"User-Agent": "authorship-id-lexicon/1.0"}
TARGET = Path(__file__).with_name("currency_rates.tsv")
CUBE = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"


@timed
def generate(target=TARGET):
    with urllib.request.urlopen(urllib.request.Request(ENDPOINT, headers=HEADERS), timeout=90) as response:
        root = ElementTree.fromstring(response.read())
    day = next(cube for cube in root.iter(CUBE) if cube.get("time"))
    per_euro = {cube.get("currency").lower(): float(cube.get("rate")) for cube in day.iter(CUBE) if cube.get("currency")}
    per_euro["eur"] = 1.0
    dollars = per_euro["usd"]
    rows = sorted((code, dollars / rate) for code, rate in per_euro.items())
    target.write_text("".join(f"{code}\t{value:.6g}\t{day.get('time')}\n" for code, value in rows), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
