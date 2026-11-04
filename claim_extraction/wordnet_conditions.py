import sys
from pathlib import Path

import nltk

from . import timed

TARGET = Path(__file__).with_name("wordnet_conditions.tsv")
ROOTS = ("ill_health.n.01", "disorder.n.01", "symptom.n.01")
GENERIC = ("ill_health.n.01", "illness.n.01", "disease.n.01", "disorder.n.01", "symptom.n.01")
OUTSIDE = ("plant_disease.n.01", "animal_disease.n.01", "mental_disorder.n.01")
VALUES = (("cancer.n.01", "cancer"), ("diabetes.n.01", "diabetes"), ("autoimmune_disease.n.01", "autoimmune disease"), ("skin_disease.n.01", "skin condition"),
          ("respiratory_disease.n.01", "respiratory condition or allergy"), ("allergy.n.01", "respiratory condition or allergy"),
          ("cardiovascular_disease.n.01", "heart or blood condition"), ("blood_disease.n.01", "heart or blood condition"), ("visual_impairment.n.01", "vision or hearing impairment"),
          ("eye_disease.n.01", "vision or hearing impairment"), ("hearing_impairment.n.01", "vision or hearing impairment"))


def below(wordnet, name):
    root = wordnet.synset(name)
    return {root} | set(root.closure(lambda synset: synset.hyponyms()))


@timed
def generate(target=TARGET):
    nltk.download("wordnet", quiet=True)
    from nltk.corpus import wordnet
    tree = set().union(*(below(wordnet, name) for name in ROOTS)) - set().union(*(below(wordnet, name) for name in OUTSIDE)) - {wordnet.synset(name) for name in GENERIC}
    groups = [(below(wordnet, name), value) for name, value in VALUES]
    names = {}
    for synset in tree:
        for lemma in synset.lemma_names():
            senses = wordnet.synsets(lemma)
            if len(lemma) > 3 and all(sense in tree for sense in senses):
                names[lemma.replace("_", " ").lower()] = next((value for group, value in groups if senses[0] in group), "other physical condition")
    target.write_text("".join(f"{name}\t{names[name]}\n" for name in sorted(names)), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
