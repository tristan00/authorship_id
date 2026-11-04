import sys
from pathlib import Path

from . import knowledge

TARGET = Path(__file__).with_name("character_names.tsv")
FICTIONAL_CHARACTERS_ANY_SITELINK = (knowledge.Source("fictional character", "P31", "Q95074", True, "character", 1),
                                     knowledge.Source("Pokemon species", "P31", "Q3966183", True, "character", 1))


def generate(target=TARGET):
    knowledge.generate(target, FICTIONAL_CHARACTERS_ANY_SITELINK)


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
