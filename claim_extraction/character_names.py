import sys
from pathlib import Path

import nltk

from . import knowledge

TARGET = Path(__file__).with_name("character_names.tsv")
FICTIONAL_CHARACTERS_ANY_SITELINKS = (knowledge.Source("fictional character", "P31", "Q95074", True, "character", 0),
                                      knowledge.Source("Pokemon species", "P31", "Q3966183", True, "character", 0))


def ordinary_words():
    words = {word for word in nltk.corpus.brown.words() if word.islower()}
    words.update(nltk.corpus.stopwords.words("english"))
    words.update(name.lower() for name in nltk.corpus.names.words())
    words.update(line.split("\t", 1)[0] for line in knowledge.GAZETTEER.read_text(encoding="utf-8").splitlines()[1:])
    return words


def dictionary_words():
    nltk.download("words", quiet=True)
    nltk.download("wordnet", quiet=True)
    return {word.lower() for word in nltk.corpus.words.words()} | {lemma.lower() for lemma in nltk.corpus.wordnet.all_lemma_names()} | ordinary_words()


def marked(lines, dictionary):
    for line in lines:
        key, attribute, value, links, surfaces, common = line.split("\t")
        yield line if common or key not in dictionary else "\t".join((key, attribute, value, links, surfaces, "1"))


def generate(target=TARGET):
    knowledge.generate(target, FICTIONAL_CHARACTERS_ANY_SITELINKS)
    ordinary = ordinary_words()
    header, *rows = target.read_text(encoding="utf-8").splitlines()
    linked_or_unusual = [row for row in rows if int(row.split("\t")[3]) >= 1 or set(row.split("\t", 1)[0].split()) - ordinary]
    keys = {row.split("\t", 1)[0] for row in linked_or_unusual}
    unusual_first_words = {}
    for row in linked_or_unusual:
        key, _, value, _, _, common = row.split("\t")
        first = key.split()[0]
        if " " in key and not common and first.isalpha() and len(first) > 2 and first not in keys and first not in ordinary:
            unusual_first_words.setdefault(first, value)
    lines = linked_or_unusual + [f"{first}\tcharacter\t{value}\t0\t{first.title()}\t" for first, value in unusual_first_words.items()]
    target.write_text(header + "\n" + "".join(line + "\n" for line in sorted(marked(lines, dictionary_words()))), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
