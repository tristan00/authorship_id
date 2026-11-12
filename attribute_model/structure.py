import json
from pathlib import Path

import torch

from . import LOG, timed, write_json

HAND = Path(__file__).with_name("structure.json")
DERIVED = "parents.json"
SHARE = .5
PLACES = """
WITH counts AS (SELECT value, uniqExact(author) AS n FROM author_claims WHERE attribute = {attribute:String} GROUP BY value),
pairs AS (SELECT a.value AS child, b.value AS parent, uniqExact(a.author) AS together FROM author_claims AS a INNER JOIN author_claims AS b ON a.author = b.author AND a.attribute = b.attribute
          WHERE a.attribute = {attribute:String} AND a.value != b.value GROUP BY child, parent)
SELECT p.child, argMin(p.parent, c2.n) FROM pairs AS p INNER JOIN counts AS c1 ON p.child = c1.value INNER JOIN counts AS c2 ON p.parent = c2.value
WHERE c2.n > c1.n AND p.together >= {share:Float64} * c1.n GROUP BY p.child
"""
GROUPS = """
WITH single AS (SELECT author, any(value) AS child FROM author_claims WHERE attribute = {attribute:String} GROUP BY author HAVING count() = 1),
totals AS (SELECT child, count() AS n FROM single GROUP BY child),
pairs AS (SELECT s.child AS child, g.value AS grp, count() AS together FROM single AS s INNER JOIN author_claims AS g ON s.author = g.author WHERE g.attribute = {group:String} GROUP BY child, grp)
SELECT p.child, argMax(p.grp, p.together) FROM pairs AS p INNER JOIN totals AS t ON p.child = t.child GROUP BY p.child, t.n HAVING max(p.together) >= {share:Float64} * t.n
"""


def hand():
    return json.loads(HAND.read_text(encoding="utf-8"))


def edges(tree, parent=None, found=None):
    found = [] if found is None else found
    for name, children in tree.items():
        found.append((name, parent))
        edges(children, name, found)
    return found


@timed
def derive(directory):
    from database import client
    db = client()
    parents = {}
    for name, spec in hand().items():
        if "places" in spec:
            rows = db.query(PLACES, parameters={"attribute": name, "share": SHARE}).result_rows
        elif "groups" in spec:
            rows = db.query(GROUPS, parameters={"attribute": name, "group": spec["groups"], "share": SHARE}).result_rows
        else:
            continue
        parents[name] = dict(rows)
        LOG.info("structure derived %s parents=%d", name, len(rows))
    write_json(Path(directory) / DERIVED, parents)
    return parents


def tree(nodes, groupings, values, single, **extra):
    return {"kind": "tree", "nodes": nodes, "groupings": groupings, "values": values, "single": single, **extra}


def from_edges(catalog, groupings, aliases, single):
    nodes = list(dict.fromkeys([name for found in groupings.values() for name, _ in found]))
    index = {name: position for position, name in enumerate(nodes)}
    parents = {key: [-2] * len(nodes) for key in groupings}
    for key, found in groupings.items():
        for name, parent in found:
            parents[key][index[name]] = -1 if parent is None else index[parent]
    return tree(nodes, parents, [index[aliases.get(value, value)] for value in catalog], single)


def derived(catalog, parents, groups, single):
    nodes = list(dict.fromkeys(list(groups) + list(catalog)))
    index = {name: position for position, name in enumerate(nodes)}
    found = [-1] * len(nodes)
    for name in catalog:
        if parents.get(name) in index and parents[name] != name:
            found[index[name]] = index[parents[name]]
    for start in range(len(nodes)):
        seen, current = {start}, found[start]
        while current >= 0:
            if current in seen:
                raise ValueError(f"derived parents loop at {nodes[start]}")
            seen.add(current)
            current = found[current]
    return tree(nodes, {"tree": found}, [index[name] for name in catalog], single, group_values=[index[name] for name in groups])


@timed
def build(manifest, directory):
    structures, specs = {}, hand()
    parents = json.loads((Path(directory) / DERIVED).read_text(encoding="utf-8"))
    catalogs = manifest["catalogs"]
    for name, kind in manifest["targets"].items():
        spec, catalog, single = specs.get(name, {}), catalogs.get(name), kind != "set"
        if kind == "numeric":
            structures[name] = {"kind": "number"}
        elif "scale" in spec:
            position = {value: index for index, value in enumerate(spec["scale"])}
            structures[name] = {"kind": "scale", "names": spec["scale"], "values": [position[value] for value in catalog], "single": single, "born": spec.get("born")}
        elif "grid" in spec:
            grid = spec["grid"]
            cells = [grid["cells"][value] for value in catalog]
            structures[name] = {"kind": "grid", "shape": [len(grid["rows"]), len(grid["columns"])], "values": [row * len(grid["columns"]) + column for row, column in cells], "names": catalog}
        elif "tree" in spec or "groupings" in spec:
            structures[name] = from_edges(catalog, {key: edges(found) for key, found in spec.get("groupings", {"tree": spec.get("tree")}).items()}, spec.get("aliases", {}), single)
        elif "places" in spec or "groups" in spec:
            groups = catalogs[spec["groups"]] if "groups" in spec else []
            structures[name] = derived(catalog, parents[name], groups, single) | ({"groups": spec["groups"]} if "groups" in spec else {})
        else:
            structures[name] = tree(list(catalog), {"tree": [-1] * len(catalog)}, list(range(len(catalog))), single)
    for name in specs["mbti"]["axes"]:
        structures[name]["axes"] = specs["mbti"]["axes"]
    for name, structure in structures.items():
        if structure["kind"] == "tree":
            LOG.info("structure %s nodes=%d roots=%d groupings=%s", name, len(structure["nodes"]), sum(all(parents[node] < 0 for parents in structure["groupings"].values())
                                                                                                         for node in range(len(structure["nodes"]))), list(structure["groupings"]))
    return structures


def key_of(rows, nodes, size):
    return rows * (size + 1) + nodes


class Graph:
    def __init__(self, structure, device):
        self.size = len(structure["nodes"])
        self.groupings = {key: torch.tensor(parents, dtype=torch.long, device=device) for key, parents in structure["groupings"].items()}
        self.values = torch.tensor(structure["values"], dtype=torch.long, device=device)
        self.group_values = torch.tensor(structure.get("group_values", []), dtype=torch.long, device=device)
        lists = [{node} for node in range(self.size)]
        changed = True
        while changed:
            changed = False
            for parents in structure["groupings"].values():
                for child, parent in enumerate(parents):
                    if parent >= 0 and not lists[parent] <= lists[child]:
                        lists[child] |= lists[parent]
                        changed = True
        width = max(len(found) for found in lists)
        self.ancestors = torch.tensor([sorted(found) + [self.size] * (width - len(found)) for found in lists], dtype=torch.long, device=device)

    def closure(self, rows, nodes, proper=False):
        found = self.ancestors[nodes]
        keep = (found < self.size) & ((found != nodes[:, None]) if proper else True)
        return rows[:, None].expand_as(found)[keep], found[keep]

    def deepest(self, rows, nodes):
        unique = torch.unique(key_of(rows, nodes, self.size))
        rows, nodes = unique // (self.size + 1), unique % (self.size + 1)
        covered = torch.isin(unique, key_of(*self.closure(rows, nodes, proper=True), self.size))
        return rows[~covered], nodes[~covered]

    @timed
    def information(self, indptr, nodes):
        rows = torch.repeat_interleave(torch.arange(len(indptr) - 1, device=nodes.device), indptr.diff())
        unique = torch.unique(key_of(*self.closure(rows, nodes), self.size))
        labeled = max(int((indptr.diff() > 0).sum()), 1)
        share = torch.bincount(unique % (self.size + 1), minlength=self.size + 1)[:self.size].double() / labeled
        return -torch.log2(share.clamp_min(.5 / labeled))


def csr(rows, values, count):
    order = torch.argsort(rows, stable=True)
    indptr = torch.zeros(count + 1, dtype=torch.long, device=rows.device)
    indptr[1:] = torch.cumsum(torch.bincount(rows, minlength=count), 0)
    return indptr, values[order]


def members(column, labels, sets, count):
    if column in sets:
        indptr, values = sets[column]
        return torch.repeat_interleave(torch.arange(count, device=indptr.device), indptr.diff()), values.long()
    rows = torch.isfinite(labels[:, column]).nonzero().squeeze(1)
    return rows, labels[rows, column].long()


def truth(structure, column, columns, labels, sets, graph):
    count = len(labels)
    rows, values = members(column, labels, sets, count)
    if structure["kind"] == "tree":
        nodes = graph.values[values]
        if structure.get("groups"):
            group_rows, group_values = members(columns[structure["groups"]], labels, sets, count)
            rows, nodes = torch.cat([rows, group_rows]), torch.cat([nodes, graph.group_values[group_values]])
        return csr(*graph.deepest(rows, nodes), count)
    if structure["kind"] in ("scale", "grid"):
        return csr(rows, torch.tensor(structure["values"], device=labels.device)[values], count)
    return csr(rows, values, count)
