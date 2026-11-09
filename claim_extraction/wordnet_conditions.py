import sys
from pathlib import Path

import nltk

from . import timed

TARGET = Path(__file__).with_name("wordnet_conditions.txt")
ROOTS = ("ill_health.n.01", "disorder.n.01", "symptom.n.01")
GENERIC = ("ill_health.n.01", "illness.n.01", "disease.n.01", "disorder.n.01", "symptom.n.01")
OUTSIDE = ("plant_disease.n.01", "animal_disease.n.01", "mental_disorder.n.01")


def below(wordnet, name):
    root = wordnet.synset(name)
    return {root} | set(root.closure(lambda synset: synset.hyponyms()))


@timed
def generate(target=TARGET):
    nltk.download("wordnet", quiet=True)
    from nltk.corpus import wordnet
    tree = set().union(*(below(wordnet, name) for name in ROOTS)) - set().union(*(below(wordnet, name) for name in OUTSIDE)) - {wordnet.synset(name) for name in GENERIC}
    names = {lemma.replace("_", " ").lower() for synset in tree for lemma in synset.lemma_names() if len(lemma) > 3 and all(sense in tree for sense in wordnet.synsets(lemma))}
    target.write_text("".join(f"{name}\n" for name in sorted(names)), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
