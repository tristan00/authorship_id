import csv
import io
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from . import timed

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "authorship-id-lexicon/1.0", "Accept": "text/csv"}
TARGET = Path(__file__).with_name("adhd_drugs.txt")
QUERY = ('SELECT ?name (GROUP_CONCAT(DISTINCT ?condition; separator="|") AS ?conditions) WHERE { ?item wdt:P2175 wd:Q181923 ; rdfs:label ?name ; wdt:P2175 ?treated . '
         '?treated rdfs:label ?condition . FILTER(LANG(?name) = "en") FILTER(LANG(?condition) = "en") '
         'FILTER NOT EXISTS { ?item wdt:P31 ?brand . VALUES ?brand { wd:Q167270 wd:Q28885102 } } } GROUP BY ?name')
BROADER = {"depression", "major depressive disorder", "pain", "arterial hypertension", "nicotine dependence", "fatigue"}
PLAIN = re.compile(r"[a-z][a-z0-9 -]*[a-z0-9]")
MARKS = re.compile(r"®|™|&reg;?")


@timed
def generate(target=TARGET):
    request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({"query": QUERY}).encode(), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=90) as response:
        header, *rows = csv.reader(io.StringIO(response.read().decode("utf-8")))
    names = sorted({name for raw, conditions in rows if PLAIN.fullmatch(name := MARKS.sub("", raw).strip().lower()) and not BROADER & set(conditions.split("|"))})
    target.write_text("".join(name + "\n" for name in names), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
