import csv
import http.client
import io
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, namedtuple
from pathlib import Path

import nltk

from . import timed

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "authorship-id-lexicon/1.0", "Accept": "text/csv"}
TARGET = Path(__file__).with_name("knowledge.tsv")
GAZETTEER = Path(__file__).with_name("gazetteer.tsv")
Source = namedtuple("Source", "name property root subclasses attribute minimum_sitelinks")
SOURCES = (Source("video game", "P31", "Q7889", True, "video_game", 3),
           Source("video game series", "P31", "Q7058673", True, "video_game", 3),
           Source("television series", "P31", "Q5398426", True, "franchise", 5),
           Source("anime television series", "P31", "Q63952888", True, "franchise", 3),
           Source("manga series", "P31", "Q21198342", True, "franchise", 3),
           Source("film series", "P31", "Q24856", True, "franchise", 3),
           Source("media franchise", "P31", "Q196600", True, "franchise", 3),
           Source("book series", "P31", "Q277759", True, "franchise", 3),
           Source("comic book series", "P31", "Q14406742", True, "franchise", 3),
           Source("novel", "P7937", "Q8261", True, "franchise", 10),
           Source("fictional character", "P31", "Q95074", True, "character", 3),
           Source("musical group", "P31", "Q215380", True, "artist", 5),
           Source("musician", "P106", "Q639669", True, "artist", 10),
           Source("singer", "P106", "Q177220", True, "artist", 10),
           Source("rapper", "P106", "Q2252262", True, "artist", 10),
           Source("athlete", "P106", "Q2066131", True, "athlete", 20),
           Source("actor", "P106", "Q33999", True, "celebrity", 20),
           Source("comedian", "P106", "Q245068", True, "celebrity", 10),
           Source("YouTuber", "P106", "Q17125263", True, "creator", 3),
           Source("online streamer", "P106", "Q57414145", True, "creator", 3),
           Source("podcaster", "P106", "Q15077007", True, "creator", 3),
           Source("YouTube channel", "P31", "Q17558136", True, "creator", 3),
           Source("novelist", "P106", "Q6625963", True, "author", 10),
           Source("writer", "P106", "Q36180", False, "author", 40))
CHUNK = 200
SUBCLASSES = "SELECT DISTINCT ?class WHERE {{ ?class wdt:P279* wd:{root} }}"
MEMBERS = """SELECT ?item ?links ?name ?alias ?language WHERE {{ VALUES ?class {{ {classes} }} ?item wdt:{property} ?class ; wikibase:sitelinks ?links . {human} FILTER(?links >= {minimum})
{{ ?item rdfs:label ?name BIND(0 AS ?alias) }} UNION {{ ?item skos:altLabel ?name BIND(1 AS ?alias) }} BIND(LANG(?name) AS ?language) FILTER(?language IN ("en", "mul")) }}"""
HUMAN = "?item wdt:P31 wd:Q5 ."
WORD = re.compile(r"\w+")
SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv"})
BRACKETED = re.compile(r"\s*[(\[][^)\]]*[)\]]")
TRAILING = re.compile(r"\s+[(\[][^)\]]*[)\]]?\s*$")
CLUB = re.compile(r"\s+(?:football club|f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?)$")
VAGUE = frozenset("this that the these those my our his her their him them it its he she they one game games movie movies film films show shows book books series song songs album albums character characters team teams player players author authors artist artists band bands music".split())
FILMS = Path(__file__).with_name("films.tsv")
FILM_SOURCES = (Source("film", "P31", "Q11424", True, "franchise", 10),)
CLUBS = Path(__file__).with_name("clubs.tsv")
CLUB_SOURCES = (Source("sports team", "P31", "Q12973014", True, "sports_team", 20), Source("sports club", "P31", "Q847017", True, "sports_team", 20))
NONWORD_TITLES = Path(__file__).with_name("nonword_titles.tsv")
COMMON_WORDS = Path(__file__).with_name("common_words.tsv")
TITLE_ATTRIBUTES = frozenset({"franchise", "video_game"})
SCHOOLS = Path(__file__).with_name("schools.tsv")
DEMONYMS = Path(__file__).with_name("demonyms.tsv")
SCHOOL_SOURCES = (Source("university", "P31", "Q3918", True, "school_attended", 5),
                  Source("college", "P31", "Q189004", True, "school_attended", 5),
                  Source("higher education institution", "P31", "Q38723", True, "school_attended", 5))
SCHOOL_EXCLUSIONS = (Source("learned society", "P31", "Q955824", True, "school_attended", 5),)
SCHOOL_TYPES = frozenset("university universities universidad universidade université universität università universiteit uni college colleges institute institution school schools univ state tech academy polytechnic politecnico conservatory seminary faculty campus".split())
SCHOOL_VAGUE = frozenset("midwest baptist dominican colegio técnico tecnico metropolitana statale renda unica chung spartans msm kpi eur aut sse unu bfs".split())
DESCRIBING = 10
AMBIGUITY = 3
SHORT = 4
SHORT_SITELINKS = 20


def fetched(query):
    request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({"query": query}).encode(), headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code == 429:
            time.sleep(int(error.headers.get("Retry-After", 60)))
            return fetched(query)
        return None
    except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError):
        return None
    header, *rows = csv.reader(io.StringIO(text))
    return None if "Exception" in text[-3000:] or any(len(row) != len(header) for row in rows) else rows


def subclasses(root):
    return sorted({row[0].rsplit("/", 1)[1] for row in fetched(SUBCLASSES.format(root=root))})


def members(source, classes):
    rows = fetched(MEMBERS.format(classes=" ".join("wd:" + code for code in classes), property=source.property, minimum=source.minimum_sitelinks, human=HUMAN if source.property == "P106" else ""))
    if rows is not None:
        return rows
    if len(classes) == 1:
        raise TimeoutError(source.name + " " + classes[0])
    half = len(classes) // 2
    return members(source, classes[:half]) + members(source, classes[half:])


def fan_value(attribute, text):
    text = TRAILING.sub("", text).removeprefix("the ")
    if attribute == "sports_team":
        text = CLUB.sub("", text)
    return text if set(text.split()) - VAGUE else None


def folded(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def forms(name, surnamed):
    name = BRACKETED.sub("", name).strip()
    primary = [name, name.removeprefix("The ")]
    secondary = [side.strip() for side in name.split(": ", 1)] if ": " in name else []
    if surnamed and len(parts := [part for part in name.split() if part.rstrip(".,").lower() not in SUFFIXES]) > 1:
        secondary.append(parts[-1])
    return [(form, rank) for rank, group in enumerate((primary, secondary)) for raw in group for form in (raw, folded(raw))]


@timed
def generate(target=TARGET, sources=SOURCES):
    nltk.download("brown", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("names", quiet=True)
    words = {}
    for word in nltk.corpus.brown.words():
        if word.islower():
            words[word] = words.get(word, 0) + 1
    stop = frozenset(nltk.corpus.stopwords.words("english"))
    places = {line.split("\t", 1)[0] for line in GAZETTEER.read_text(encoding="utf-8").splitlines()[1:]}
    given = frozenset(name.lower() for name in nltk.corpus.names.words())
    items = {}
    for source in sources:
        classes = subclasses(source.root) if source.subclasses else [source.root]
        for start in range(0, len(classes), CHUNK):
            for item, links, name, alias, language in members(source, classes[start:start + CHUNK]):
                entry = items.setdefault((source.attribute, item.rsplit("/", 1)[1]), {"links": int(links), "labels": {}, "names": set(), "person": source.property == "P106"})
                entry["names"].add(name)
                if alias == "0":
                    entry["labels"][language] = name
    best = {}
    for (attribute, code), entry in items.items():
        label = entry["labels"].get("en") or entry["labels"].get("mul")
        if not label or not (value := fan_value(attribute, BRACKETED.sub("", label).strip().lower())):
            continue
        for name in entry["names"]:
            for form, rank in forms(name, entry["person"] and name == label):
                tokens = WORD.findall(form)
                key = " ".join(tokens).lower()
                content = [token for token in key.split() if token not in stop]
                if not content or len(key) < 2 or not re.search(r"[^\W\d_]", key) or (entry["person"] and name != label and len(content) == 1 and content[0] in given):
                    continue
                order = (rank, -entry["links"], int(code[1:]))
                current = best.get((key, attribute))
                common = all(words.get(token, 0) >= 3 for token in content) or key in places or (len(content) == 1 and content[0] in given)
                if current is None or order < current[0]:
                    best[(key, attribute)] = (order, value, entry["links"], {" ".join(tokens)} if rank or len(content) == 1 or common else set(), common)
                elif order == current[0] and current[3]:
                    current[3].add(" ".join(tokens))
    primary = {key for (key, _), (order, *_) in best.items() if order[0] == 0}
    best = {(key, attribute): row for (key, attribute), row in best.items() if row[0][0] == 0 or key not in primary}
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("key\tattribute\tvalue\tsitelinks\tcased\tcommon\n")
        for (key, attribute), (_, value, links, cased, common) in sorted(best.items()):
            out.write(f"{key}\t{attribute}\t{value}\t{links}\t{'|'.join(sorted(cased))}\t{'1' if common else ''}\n")


@timed
def generate_films(target=FILMS, sources=FILM_SOURCES):
    generate(target, sources)


@timed
def generate_clubs(target=CLUBS, sources=CLUB_SOURCES):
    generate(target, sources)


@timed
def generate_nonword_titles(target=NONWORD_TITLES, lexicon=TARGET):
    nltk.download("wordnet", quiet=True)
    dictionary = frozenset(nltk.corpus.wordnet.all_lemma_names())
    forms = set()
    with open(lexicon, encoding="utf-8") as rows:
        next(rows)
        for line in rows:
            key, attribute, value, links, surfaces, common = line.rstrip("\n").split("\t")
            if attribute in TITLE_ATTRIBUTES:
                forms.update(form for surface in filter(None, surfaces.split("|")) if " " not in surface and (form := surface.lower()).capitalize() == surface and form not in dictionary and nltk.corpus.wordnet.morphy(form) is None)
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("form\n")
        out.writelines(form + "\n" for form in sorted(forms))


@timed
def generate_common_words(target=COMMON_WORDS):
    nltk.download("wordnet", quiet=True)
    common, proper = set(), set()
    for synset in nltk.corpus.wordnet.all_synsets():
        for lemma in synset.lemmas():
            name = lemma.name()
            (common if name.islower() else proper).add(name.lower())
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("word\n")
        out.writelines(word + "\n" for word in sorted(common - proper) if "_" not in word and WORD.fullmatch(word))


@timed
def generate_schools(target=SCHOOLS, sources=SCHOOL_SOURCES, exclusions=SCHOOL_EXCLUSIONS):
    nltk.download("brown", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("names", quiet=True)
    nltk.download("words", quiet=True)
    nltk.download("wordnet", quiet=True)
    words = Counter(word for word in nltk.corpus.brown.words() if word.islower())
    stop = frozenset(nltk.corpus.stopwords.words("english"))
    places = {line.split("\t", 1)[0] for line in GAZETTEER.read_text(encoding="utf-8").splitlines()[1:]}
    demonyms = {line.split("\t", 1)[0] for line in DEMONYMS.read_text(encoding="utf-8").splitlines()[1:]}
    dictionary = frozenset(COMMON_WORDS.read_text(encoding="utf-8").splitlines()[1:]) | {word for word in nltk.corpus.words.words() if word.islower()}
    given = frozenset(name.lower() for name in nltk.corpus.names.words())

    def ordinary(token):
        return words[token] >= 3 or token in dictionary or nltk.corpus.wordnet.morphy(token) in dictionary

    def acronym(key, value):
        initials = iter(token[0] for token in WORD.findall(value))
        return all(char in initials for char in key)

    items, excluded = {}, set()
    for source in exclusions:
        classes = subclasses(source.root)
        for start in range(0, len(classes), CHUNK):
            excluded.update(row[0] for row in members(source, classes[start:start + CHUNK]))
    for source in sources:
        classes = subclasses(source.root) if source.subclasses else [source.root]
        for start in range(0, len(classes), CHUNK):
            for item, links, name, alias, language in members(source, classes[start:start + CHUNK]):
                if item in excluded:
                    continue
                entry = items.setdefault(item.rsplit("/", 1)[1], {"links": int(links), "labels": {}, "names": set()})
                entry["names"].add(name)
                if alias == "0":
                    entry["labels"][language] = name
    labels = {code: label for code, entry in items.items() if (label := entry["labels"].get("en") or entry["labels"].get("mul"))}
    values = {code: " ".join(BRACKETED.sub("", label).lower().split()) for code, label in labels.items()}
    usage = Counter(token for value in set(values.values()) for token in set(WORD.findall(value)))
    describing = SCHOOL_TYPES | stop | {token for token, count in usage.items() if count >= DESCRIBING and (words[token] >= 3 or token in demonyms)}
    candidates = {}
    for code, value in values.items():
        entry = items[code]
        for name in entry["names"]:
            for form, rank in forms(name, False):
                key = " ".join(WORD.findall(form)).lower()
                tokens = key.split()
                content = [token for token in tokens if token not in describing]
                if len(key) < 3 or not content or not re.search(r"[^\W\d_]", key) or "_" in key:
                    continue
                common = not SCHOOL_TYPES & set(tokens) and (all(map(ordinary, content)) or key in places or key in demonyms or key in SCHOOL_VAGUE or tokens[-1] in places and set(tokens[:-1]) <= describing or (len(content) == 1 and content[0] in given)) or (len(tokens) == 1 and len(key) <= SHORT and (entry["links"] < SHORT_SITELINKS or not acronym(key, value)))
                candidates.setdefault(key, []).append(((2 * rank + (name != labels[code]), -entry["links"], int(code[1:])), value, entry["links"], common))
    with open(target, "w", encoding="utf-8", newline="\n") as out:
        out.write("key\tvalue\tsitelinks\tcommon\n")
        for key, found in sorted(candidates.items()):
            found.sort()
            order, value, links, common = found[0]
            if not any(rival[0][0] == order[0] and rival[1] != value and rival[2] * AMBIGUITY > links for rival in found[1:]):
                out.write(f"{key}\t{value}\t{links}\t{'1' if common else ''}\n")



if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
    generate_films()
    generate_clubs()
    generate_nonword_titles()
    generate_common_words()
    generate_schools()
