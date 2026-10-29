from collections import Counter, defaultdict


def claims(lines):
    for line in lines:
        source, _, claim = line.partition(" ")
        field, _, value = claim.partition(": ")
        yield source, field, value


def consolidate(evidence):
    values = defaultdict(list)
    for _, field, value in evidence:
        values[field].append(value)
    result = {}
    for field, found in values.items():
        ranked = Counter(found).most_common(2)
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            result[field] = ranked[0][0]
    return result
