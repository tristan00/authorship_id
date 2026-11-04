import sys
import urllib.parse
import urllib.request
from pathlib import Path

from . import timed

ONET = "https://www.onetcenter.org/dl_files/database/db_30_0_text/"
TARGET = Path(__file__).with_name("onet_titles.tsv")


def fields(name):
    with urllib.request.urlopen(ONET + urllib.parse.quote(name)) as response:
        return [line.split("\t") for line in response.read().decode("utf-8").splitlines()[1:]]


@timed
def generate(target=TARGET):
    rows = [(code[:7], "R", title) for code, title, _ in fields("Sample of Reported Titles.txt")]
    for code, title, short, _ in fields("Alternate Titles.txt"):
        rows += [(code[:7], "A", name) for name in (title, short) if name != "n/a"]
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.writelines("\t".join(row) + "\n" for row in dict.fromkeys(rows))


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
