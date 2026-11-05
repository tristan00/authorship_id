import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import babel
import nltk

from . import timed

GEONAMES = "https://download.geonames.org/export/dump/"
TARGET = Path(__file__).with_name("gazetteer.tsv")
WIKIDATA = "https://query.wikidata.org/sparql?"
FOREIGN = Path(__file__).with_name("demonyms.tsv")
COPULA_LANGUAGES = ("es", "pt", "fr", "de", "it", "nl")
TOKEN = re.compile(r"[^\W_]+")
LOCALES = ("es", "de", "fr", "pt", "it", "pl", "nl")
STOPWORDS = ("spanish", "german", "french", "portuguese", "italian", "dutch")
MONTHS = frozenset("january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday".split())
PREFIX = re.compile(r"^(?:state of |province of |region of |city of )")
SUFFIX = re.compile(r"^(?:state of |province of |region of |city of |departamento de |provincia de |estado de )|(?: oblast| province| region| governorate| prefecture| state| voivodeship| county"
                    r"| district| krai| kray| republic| autonomous region| territory| department| division)$")
FEDERATIONS = ("US", "CA", "AU")


def fields(name):
    with urllib.request.urlopen(GEONAMES + name) as response:
        data = response.read()
    if name.endswith(".zip"):
        data = zipfile.ZipFile(io.BytesIO(data)).read(name.replace(".zip", ".txt"))
    return [line.rstrip("\n").split("\t") for line in io.StringIO(data.decode("utf-8"), newline=None) if not line.startswith("#")]


def key(name):
    return " ".join(TOKEN.findall(name.lower()))


@timed
def generate(target=TARGET):
    nltk.download("brown", quiet=True)
    nltk.download("stopwords", quiet=True)
    words = Counter(word for word in nltk.corpus.brown.words() if word.islower())
    stop = frozenset(nltk.corpus.stopwords.words("english"))
    excluded = stop | frozenset(word for language in STOPWORDS for word in nltk.corpus.stopwords.words(language))
    common = lambda name: all(words[token] >= 3 or token in stop for token in name.split())
    countries = {row[0]: (row[4], int(row[7] or 0)) for row in fields("countryInfo.txt")}
    admin = {row[0]: (row[1], row[2]) for row in fields("admin1CodesASCII.txt")}
    cities = sorted(((int(row[14] or 0), row[1], row[2], row[8], f"{row[8]}.{row[10]}") for row in fields("cities15000.zip")), reverse=True)
    rows = {}

    def add(name, kind, value, region, country, cased=None):
        name = key(name)
        if name and name not in rows and len(name) > 2 and name not in excluded and name not in MONTHS:
            rows[name] = (kind, value.lower(), PREFIX.sub("", region.lower()), country.lower(), cased if cased == "town" else "1" if (common(name) if cased is None else cased) else "")

    ranked = sorted(countries.items(), key=lambda item: -item[1][1])
    for code, (name, _) in ranked:
        add(name, "country", name, "", name, False)
    for code, (name, _) in ranked:
        for locale in LOCALES:
            if local := babel.Locale(locale).territories.get(code):
                add(local, "country", name, "", name)
    for population, name, ascii, country, region in cities:
        if population >= 1_000_000:
            for variant in (name, ascii):
                add(variant, "city", name, admin.get(region, ("", ""))[0], countries[country][0])
    order = [(code, names) for code, names in sorted(admin.items(), key=lambda item: -countries.get(item[0].split(".")[0], ("", 0))[1]) if code.split(".")[0] in countries]
    seats = {(region, key(variant)) for _, name, ascii, country, region in cities if country not in FEDERATIONS for variant in (name, ascii)}
    towns = {}
    for population, name, ascii, country, region in cities:
        for variant in (name, ascii):
            towns.setdefault(key(variant), []).append((population, region))
    contested = {code.split(".")[0] for code, names in admin.items() for variant in names for name in (key(variant), SUFFIX.sub("", key(variant))) if any(region != code for _, region in towns.get(name, ()))}
    sizes = {f"{row[8]}.{row[10]}": int(row[14] or 0) for country in sorted(contested) for row in fields(f"{country}.zip") if row[7] == "ADM1"}
    outgrown = lambda code, name: any(population > sizes.get(code, 0) for population, region in towns.get(name, ()) if region != code)
    for code, names in order:
        for variant in names:
            if not common(key(variant)) and (code, key(variant)) not in seats and not outgrown(code, key(variant)):
                add(variant, "region", names[0], names[0], countries[code.split(".")[0]][0])
    for code, names in order:
        for variant in names:
            if (short := SUFFIX.sub("", key(variant))) != key(variant) and not common(short) and not outgrown(code, short):
                add(short, "region", names[0], names[0], countries[code.split(".")[0]][0])
    for _, name, ascii, country, region in cities:
        for variant in (name, ascii):
            add(variant, "city", name, admin.get(region, ("", ""))[0], countries[country][0])
            if (short := key(variant)).startswith(("st ", "saint ")):
                add(short.replace("st ", "saint ", 1) if short.startswith("st ") else short.replace("saint ", "st ", 1), "city", name, admin.get(region, ("", ""))[0], countries[country][0])
    squashed = {name.replace(" ", "") for name in rows if " " in name}
    for population, name, ascii, country, region in sorted(((int(row[14] or 0), row[1], row[2], row[8], f"{row[8]}.{row[10]}") for row in fields("cities5000.zip")), reverse=True):
        for variant in (name, ascii):
            if population < 15000 and not common(key(variant)) and key(variant).replace(" ", "") not in squashed and not any(" ".join(key(variant).split()[cut:]) in rows or " ".join(key(variant).split()[:cut]) in rows for cut in range(1, len(key(variant).split()))):
                add(variant, "city", name, admin.get(region, ("", ""))[0], countries[country][0], "town")
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("key\tkind\tvalue\tregion\tcountry\tcased\n")
        out.writelines("\t".join((name, *row)) + "\n" for name, row in rows.items())


@timed
def foreign(target=FOREIGN):
    nltk.download("brown", quiet=True)
    nltk.download("stopwords", quiet=True)
    english = frozenset(nltk.corpus.stopwords.words("english")) | {word for word, count in Counter(word for word in nltk.corpus.brown.words() if word.islower()).items() if count >= 3}
    countries = {row[0]: row[4].lower() for row in fields("countryInfo.txt")}
    query = "SELECT ?code ?demonym WHERE { ?country wdt:P297 ?code; wdt:P1549 ?demonym. FILTER(LANG(?demonym) IN (%s)) }" % ", ".join(f'"{language}"' for language in COPULA_LANGUAGES)
    request = urllib.request.Request(WIKIDATA + urllib.parse.urlencode({"query": query, "format": "json"}), headers={"User-Agent": "claim-extraction"})
    found = {}
    for item in json.loads(urllib.request.urlopen(request).read())["results"]["bindings"]:
        if (country := countries.get(item["code"]["value"])) and (name := key(item["demonym"]["value"])) and " " not in name and name not in english:
            found.setdefault(name, set()).add(country)
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("demonym\tcountry\n")
        out.writelines(f"{name}\t{next(iter(owners))}\n" for name, owners in sorted(found.items()) if len(owners) == 1)


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
    foreign()
