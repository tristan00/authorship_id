import re
from collections import defaultdict

from .literals import scan

FOLDED = str.maketrans({"’": "'", "‘": "'", "´": "'", "ʼ": "'", "＇": "'", "`": "'", "İ": "I"})
MASKED = re.compile(r"https?://\S+|www\.\S+|\]\([^)\s]*\)|^[ \t]*(?:>|&gt;)[^\n]*", re.M)
I = r"(?:i'm|im|i am|iam|i m|i'am|i'?ve been|i've always been)"
HEDGE = re.compile(r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|wants to|trying to|tryna|going to|gonna|might|maybe|someday|used to|"
                   r"not|never|no longer|anymore|former|formerly|when i was|back when|before i was)\b|n't\b")
SELF_HEDGE = re.compile(r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|trying to|going to|gonna|might|maybe|used to|not|never|no longer|anymore|"
                        r"when i was|back when)\b|n't\b")
TAGGED = re.compile(r"$^")
TAG = r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?([mf])|([mf])\s?(\d{2}))(?![\w'%])"
FOR = r"(?<![a-z0-9])(?:(\d{2})\s*)?[\[\(]?\s*(nb|[mf])[mf]?\s*4\s*(?:[mfatr]|me|r|nb)\w*\s*[\]\)]?(?:\s*[-–|:#]?\s*(\d{2})(?!\d))?"
BOT_TEXT = scan(r"\bi am a bot\b|\bperformed automatically\b|\bplease (?:make sure|include|read)\b|\bpost (?:has been |was )?removed\b|\bmust (?:include|contain)\b")


def prepared(text):
    text = text.translate(FOLDED)
    return MASKED.sub(lambda match: " " * len(match.group()), text)


def clause(text, start):
    return max(text.rfind(mark, 0, start) for mark in ".!?\n;,") + 1


def question(text, end):
    stop = min((found for found in (text.find(mark, end) for mark in ".!\n") if found >= 0), default=len(text))
    return "?" in text[end:stop]


def hedged(text, start, end, pattern=HEDGE):
    if pattern is TAGGED:
        return False
    return bool(pattern.search(text, max(clause(text, start), start - 40), start)) or question(text, end)


def rule(attribute, pattern, value, hedge=HEDGE):
    return attribute, re.compile(pattern), value, hedge


class Gated:
    def __init__(self, compiled, gate):
        self.compiled, self.gate, self.pattern = compiled, gate, compiled.pattern

    def finditer(self, text):
        return self.compiled.finditer(text) if self.gate(text) else iter(())


def words(*anchors):
    return re.compile("|".join(map(re.escape, anchors))).search


def needs(entry, *anchors):
    attribute, pattern, value, hedge = entry
    return attribute, Gated(pattern, words(*anchors)), value, hedge


def fixed(result):
    return lambda match: result


def group(table, number=1):
    return lambda match: table.get(match.group(number))


class Names:
    def __init__(self, names):
        self.index = defaultdict(list)
        for name in names:
            tokens = name.split(" ")
            self.index[max(tokens, key=len)].append(frozenset(tokens))

    def within(self, words):
        return any(tokens <= words for word in self.index.keys() & words for tokens in self.index[word])
