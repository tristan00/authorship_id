import csv
import io
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from . import health, timed

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "authorship-id-lexicon/1.0", "Accept": "text/csv"}
TARGET = Path(__file__).with_name("foreign_conditions.tsv")
LANGUAGES = ("es", "pt", "fr", "de", "it", "nl", "pl")
CODES = ("P494", "P4229", "P7807", "P493", "P1692", "P663", "P1930")
QUERY = ("SELECT DISTINCT ?en ?lang ?name ?kind WHERE {{ VALUES ?en {{ {names} }} ?item rdfs:label ?en . FILTER EXISTS {{ ?item {codes} ?code }} "
         "VALUES ?kind {{ rdfs:label skos:altLabel }} ?item ?kind ?name . BIND(LANG(?name) AS ?lang) FILTER(?lang IN ({languages})) }}")
VALUE_ITEMS = {"Q12131": ("physical_condition", "physical disability"), "Q1179623": ("physical_condition", "physical disability"), "Q12029": ("mental_condition", "addiction"),
               "Q59344393": ("mental_condition", "neurodivergent, unspecified")}
ITEM_QUERY = ("SELECT DISTINCT ?item ?lang ?name ?kind WHERE {{ VALUES ?item {{ {items} }} VALUES ?kind {{ rdfs:label skos:altLabel }} ?item ?kind ?name . BIND(LANG(?name) AS ?lang) "
              "FILTER(?lang IN ({languages})) }}")
SHORT = 4
PLAIN = re.compile(r"[^\W\d_](?:[\w' -]*\w)?")
BATCH = 300


def english():
    pairs = {}
    for attribute, table in (("physical_condition", health.PHYSICAL), ("mental_condition", health.MENTAL_LOOSE), ("physical_condition", health.WORDNET_CONDITIONS)):
        for name, value in table.items():
            pairs.setdefault(re.sub(r"^(?:an?|the) ", "", name), set()).add((attribute, value))
    return {name: values.pop() for name, values in pairs.items() if len(values) == 1}


def spellings(name):
    return {name, name[0].upper() + name[1:], name.title(), *([name.upper()] if len(name) <= 6 else [])}


def fetch(query):
    request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({"query": query}).encode(), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=180) as response:
        header, *rows = csv.reader(io.StringIO(response.read().decode("utf-8")))
    return rows


@timed
def generate(target=TARGET):
    known = english()
    lookup = {spelling: name for name in sorted(known) for spelling in spellings(name)}
    spelled = sorted(lookup)
    languages = ", ".join(f'"{lang}"' for lang in LANGUAGES)
    rows = [(known[lookup[en]], lang, name, kind) for start in range(0, len(spelled), BATCH)
            for en, lang, name, kind in fetch(QUERY.format(names=" ".join('"' + spelling.replace("\\", "\\\\").replace('"', '\\"') + '"@en' for spelling in spelled[start:start + BATCH]),
                                                     codes="|".join("wdt:" + code for code in CODES), languages=languages))]
    rows += [(VALUE_ITEMS[item.rsplit("/", 1)[1]], lang, name, kind) for item, lang, name, kind in fetch(ITEM_QUERY.format(items=" ".join("wd:" + item for item in VALUE_ITEMS), languages=languages))]
    found = {}
    for pair, lang, name, kind in rows:
        label = name.translate(str.maketrans({"’": "'", "‘": "'"})).strip().lower()
        if PLAIN.fullmatch(label) and (len(label) > SHORT or len(label) == SHORT and (kind.endswith("label") and "#" in kind or name.isupper())):
            found.setdefault((lang, label), set()).add(pair)
    rows = sorted((lang, label, *values.pop()) for (lang, label), values in found.items() if len(values) == 1)
    target.write_text("".join("\t".join(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
