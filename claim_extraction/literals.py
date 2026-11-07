import re
from re import _constants as C, _parser as parser

CAP = 64
WIDTH = 3
COMBINATIONS = 27
EVERY = "".join(chr(code) for code in range(0x110000) if not 0xD800 <= code < 0xE000)
FOLD = str.maketrans({**{char: "0" for char in re.findall(r"\d", EVERY)}, **{char: " " for char in re.findall(r"\s", EVERY)}, "ı": "i", "İ": "i", "K": "k", "ſ": "s"})
CLASSES = {C.CATEGORY_DIGIT: "0", C.CATEGORY_SPACE: " "}
EMPTY = frozenset({""})


def folded(chars, flags, cased):
    if not (flags & re.I or cased):
        return frozenset(char.translate(FOLD) for char in chars)
    if not all(char.isascii() or char.lower() == char.upper() for char in chars):
        return None
    return frozenset(char.lower().translate(FOLD) for char in chars)


def product(left, right):
    if left is None or right is None or len(left) * len(right) > CAP:
        return None
    return frozenset(a + b for a in left for b in right)


def charset(items, flags, cased):
    found = set()
    for op, av in items:
        if op is C.LITERAL:
            found.add(chr(av))
        elif op is C.RANGE and av[1] - av[0] < 16:
            found.update(map(chr, range(av[0], av[1] + 1)))
        elif op is C.CATEGORY and av in CLASSES:
            found.add(CLASSES[av])
        else:
            return None
    return folded(found, flags, cased)


def usable(group):
    return bool(group) and "" not in group


def strength(option):
    return sum(1 if char.isalpha() else 2 for char in option if not char.isspace())


def quality(group):
    return (min(map(strength, group)), -len(group)) if usable(group) else (0, 0)


def best(*groups):
    return max(filter(usable, groups), key=quality, default=None)


def ranked(exact, groups):
    return sorted(filter(usable, {*groups, exact} - {None}), key=quality, reverse=True)[:WIDTH]


def either(parts):
    choices = [ranked(exact, groups) for exact, groups in parts]
    if not all(choices):
        return []
    combinations = [[]]
    for options in choices:
        combinations = [[*combination, option] for combination in combinations for option in options]
        if len(combinations) > COMBINATIONS:
            return [frozenset().union(*(options[0] for options in choices))]
    return [frozenset().union(*combination) for combination in combinations]


def node(op, av, flags, cased):
    if op is C.LITERAL:
        return folded({chr(av)}, flags, cased), []
    if op is C.IN:
        return charset(av, flags, cased), []
    if op in (C.AT, C.ASSERT, C.ASSERT_NOT):
        return EMPTY, []
    if op is C.SUBPATTERN:
        group, add, remove, inner = av
        return sequence(inner, (flags | add) & ~remove, cased)
    if op is C.ATOMIC_GROUP:
        return sequence(av, flags, cased)
    if op is C.BRANCH:
        parts = [sequence(alternative, flags, cased) for alternative in av[1]]
        exact = None if any(e is None for e, _ in parts) else frozenset().union(*(e for e, _ in parts))
        return (exact if exact is not None and len(exact) <= CAP else None), either(parts)
    if op in (C.MAX_REPEAT, C.MIN_REPEAT, C.POSSESSIVE_REPEAT):
        low, high, inner = av
        exact, groups = sequence(inner, flags, cased)
        if low == 0:
            return (exact | EMPTY if exact is not None and high == 1 else None), []
        if low == high == 1:
            return exact, groups
        if low == high and exact is not None:
            joined = EMPTY
            for _ in range(low):
                joined = product(joined, exact)
            if joined is not None:
                return joined, groups
        return None, [*groups, exact] if exact is not None else groups
    return None, []


def sequence(items, flags, cased):
    current, groups, whole = EMPTY, [], True
    for op, av in items:
        exact, inner = node(op, av, flags, cased)
        groups.extend(inner)
        joined = product(current, exact)
        if joined is None:
            groups.append(current)
            current, whole = exact if exact is not None else EMPTY, False
        else:
            current = joined
    if whole:
        return current, groups
    return None, [*groups, current]


def requirements(pattern, cased, shortest):
    parsed = parser.parse(pattern.pattern, pattern.flags)
    exact, groups = sequence(list(parsed), parsed.state.flags, cased)
    return sorted({group for group in (*groups, exact) if group is not None and usable(group) and min(map(strength, group)) >= shortest}, key=sorted)


NEEDS, OWNERS = [], []
INDEX = [None, ()]
SPELLED = {"0": r"\d", " ": r"\s", "i": "[iı]", "s": "[sſ]"}


def register(groups):
    if INDEX[0] is not None:
        raise ValueError("scans must be created before their expressions are built")
    if not groups:
        return None
    NEEDS.append(frozenset(range(len(OWNERS), len(OWNERS) + len(groups))))
    OWNERS.extend((len(NEEDS) - 1, group) for group in groups)
    return len(NEEDS) - 1


def spelled(option):
    return "".join(SPELLED.get(char) or re.escape(char) for char in option)


def expressions():
    INDEX[0] = [slot for slot, _ in OWNERS]
    return [re.compile("|".join(sorted(map(spelled, group)))) for _, group in OWNERS]


def original(lowered):
    (text, _), (primed, _) = INDEX[1]
    return text if primed is lowered else None


def prime(text, lowered, hits):
    slots = {slot for slot in {INDEX[0][ident] for ident in hits} if NEEDS[slot] <= hits}
    INDEX[1] = ((text, slots), (lowered, slots))


class Scan:
    def __init__(self, compiled):
        self.compiled, self.pattern, self.flags, self.groups, self.groupindex = compiled, compiled.pattern, compiled.flags, compiled.groups, compiled.groupindex
        self.slot = register(requirements(compiled, True, 3))

    def possible(self, string):
        if self.slot is None:
            return True
        for primed, slots in INDEX[1]:
            if primed is string:
                return self.slot in slots
        return True

    def finditer(self, string, *bounds):
        return self.compiled.finditer(string, *bounds) if self.possible(string) else iter(())

    def search(self, string, *bounds):
        return self.compiled.search(string, *bounds) if self.possible(string) else None

    def match(self, string, *bounds):
        return self.compiled.match(string, *bounds) if self.possible(string) else None

    def fullmatch(self, string, *bounds):
        return self.compiled.fullmatch(string, *bounds) if self.possible(string) else None

    def findall(self, string, *bounds):
        return self.compiled.findall(string, *bounds) if self.possible(string) else []

    def sub(self, *arguments, **options):
        return self.compiled.sub(*arguments, **options)

    def split(self, *arguments, **options):
        return self.compiled.split(*arguments, **options)


def scan(pattern, flags=0):
    return Scan(re.compile(pattern, flags))
