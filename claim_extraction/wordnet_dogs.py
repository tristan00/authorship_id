import sys
from pathlib import Path

import nltk

from . import timed

TARGET = Path(__file__).with_name("wordnet_dogs.txt")


@timed
def generate(target=TARGET):
    nltk.download("wordnet", quiet=True)
    from nltk.corpus import wordnet
    root = wordnet.synset("dog.n.01")
    tree = {root} | set(root.closure(lambda synset: synset.hyponyms()))
    names = set()
    for synset in tree:
        for lemma in synset.lemma_names():
            senses = wordnet.synsets(lemma, pos=wordnet.NOUN)
            if senses and senses[0] in tree:
                names.add(lemma.replace("_", " ").lower())
    target.write_text("\n".join(sorted(names)) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
