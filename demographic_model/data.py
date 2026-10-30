import gzip
import hashlib
import uuid
from collections import defaultdict
from functools import lru_cache

import lance
import numpy as np
import orjson
import psycopg

from author_encoder.config import DIMENSIONS, LUAR, MAX_LENGTH, TEXTS_PER_USER, VECTOR_STORE
from claim_extraction.config import FIELDS, NUMERIC
from database import DSN, timed

from .config import FOLDS, PARAMETERS, PARTIAL


def write_json(path, value):
    path.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))


def bucket(author, purpose, count):
    value = hashlib.sha256(f"demographic:{PARAMETERS['seed']}:{purpose}:{author}".encode()).digest()
    return int.from_bytes(value[:8], "big") % count


@timed
def export(root):
    root.mkdir(parents=True, exist_ok=False)
    vectors = lance.dataset(VECTOR_STORE)
    with psycopg.connect(DSN) as conn:
        metadata = {"protocol": orjson.loads(vectors.schema.metadata[b"protocol"]), "users": vectors.count_rows(), "version": vectors.version}
        expected = {"model": list(LUAR), "dimensions": DIMENSIONS, "minimum_usable_texts": 1, "maximum_sampled_texts": TEXTS_PER_USER, "max_tokens_per_text": MAX_LENGTH,
                    "preprocessing": "author_encoder.clean"}
        if any(metadata["protocol"][key] != value for key, value in expected.items()):
            raise ValueError("Saved user encodings do not match the configured encoder")
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        run = conn.execute("SELECT run_id::text FROM consolidation").fetchone()
        if run is None:
            raise ValueError("Consolidated targets are not available")
        authors = [author.lower() for author in vectors.to_table(columns=["author"]).column("author").to_pylist()]
        if not authors or len(authors) != len(set(authors)):
            raise ValueError("Encoded authors must be nonempty and unique ignoring case")
        write_json(root / "authors.json", authors)
        folds = np.array([bucket(author, "outer", FOLDS) for author in authors], dtype=np.uint8)
        np.save(root / "folds.npy", folds)
        embeddings = np.lib.format.open_memmap(root / "embeddings.npy", mode="w+", dtype=np.float32, shape=(len(authors), DIMENSIONS))
        index = 0
        for batch in vectors.to_batches(columns=["author", "sample_ids", "vector"]):
            values = batch.column("vector").flatten().to_numpy().reshape(-1, DIMENSIONS)
            for author, samples in zip(batch.column("author").to_pylist(), batch.column("sample_ids").to_pylist()):
                if not 1 <= len(set(samples)) == len(samples) <= TEXTS_PER_USER or author.lower() != authors[index]:
                    raise ValueError(f"Invalid saved encoding for {author}")
                index += 1
            if not np.isfinite(values).all():
                raise ValueError("Saved user encodings must be finite")
            embeddings[index - len(values):index] = values
        if index != len(authors):
            raise ValueError("Saved user encodings changed while they were exported")
        embeddings.flush()
        conn.execute("CREATE TEMP TABLE demographic_authors(author text PRIMARY KEY)")
        with conn.cursor().copy("COPY demographic_authors(author) FROM STDIN") as copy:
            for author in authors:
                copy.write_row((author,))
        conn.execute("ANALYZE demographic_authors")
        rows = conn.execute("""SELECT a.author, c.attribute, c.value FROM author_claims c JOIN demographic_authors a ON a.author = lower(c.author)
                               ORDER BY a.author, c.attribute""").fetchall()
        counts = {field: sum(attribute == field for _, attribute, _ in rows) for field in FIELDS}
        fields = list(FIELDS)
        nodes = sorted({(f"{attribute}:{value}", attribute, value, "value") for _, attribute, value in rows if attribute in fields and attribute not in NUMERIC})
        with gzip.open(root / "targets.jsonl.gz", "wb", compresslevel=1) as stream:
            for author, attribute, value in rows:
                if attribute in fields:
                    stream.write(orjson.dumps((author, attribute, target(attribute, value))) + b"\n")
        write_json(root / "taxonomy.json", {"nodes": [list(node) for node in nodes], "edges": []})
        manifest = {"run_id": str(uuid.uuid4()), "consolidation_run": run[0], "fields": fields, "users": len(authors), "folds": FOLDS, "parameters": PARAMETERS,
                    "target_counts": {field: counts[field] for field in fields}, "vector_store": str(VECTOR_STORE),
                    "vector_metadata": metadata, "sampled_texts": TEXTS_PER_USER}
        write_json(root / "manifest.json", manifest)
    return manifest


def target(attribute, value):
    if attribute in NUMERIC:
        item = {"shape": "numeric_cluster", "unit": None, "members": [{"low": float(value), "high": float(value)}]}
    else:
        item = {"shape": "node", "facet": "value", "node": f"{attribute}:{value}", "polarity": "positive"}
    return {"accepted": [item], "alternatives": [], "unresolved": []}


def split_users(authors, folds, excluded):
    validation = np.array([bucket(author, f"validation:{excluded}", 10) == 0 for author in authors])
    return np.where(folds == excluded, 2, validation.astype(np.uint8))


def cover_validation(root, authors, splits):
    positions = {author: index for index, author in enumerate(authors)}
    holders = defaultdict(set)
    with gzip.open(root / "targets.jsonl.gz", "rb") as stream:
        for line in stream:
            author, attribute, _ = orjson.loads(line)
            if splits[positions[author]] != 2:
                holders[attribute].add(positions[author])
    covered = splits.copy()
    for field, indices in sorted(holders.items()):
        if len(indices) >= 2 and not any(covered[index] == 1 for index in indices):
            covered[min(indices, key=lambda index: bucket(authors[index], f"cover:{field}", 2 ** 32))] = 1
    return covered


def bounded(value, attribute):
    low, high = NUMERIC[attribute]
    share = (value - low) / (high - low)
    return -np.inf if share <= 0 else np.inf if share >= 1 else float(np.log(share) - np.log1p(-share))


def intervals(item, attribute):
    values = []
    for member in item["members"]:
        low, high = member["low"], member["high"]
        if low is not None and low == high:
            low, high = low - .5, high + .5
        values.append((bounded(low, attribute) if low is not None else -np.inf, bounded(high, attribute) if high is not None else np.inf))
    merged = []
    for low, high in sorted(values):
        if merged and low <= merged[-1][1]:
            merged[-1][1] = max(high, merged[-1][1])
        else:
            merged.append([low, high])
    return merged


@timed
def compile_targets(root, authors, splits, reference=None):
    positions = {author: index for index, author in enumerate(authors)}
    fields = orjson.loads((root / "manifest.json").read_bytes())["fields"]
    taxonomy = orjson.loads((root / "taxonomy.json").read_bytes())
    nodes = {row[0]: row[1:] for row in taxonomy["nodes"]}
    children, parents = defaultdict(set), defaultdict(set)
    for parent, child in taxonomy["edges"]:
        children[parent].add(child)
        parents[child].add(parent)

    @lru_cache(None)
    def descendants(node):
        result = {node}
        for child in children[node]:
            result.update(descendants(child))
        return frozenset(result)

    @lru_cache(None)
    def path(node):
        return frozenset({node}.union(*(path(parent) for parent in parents[node])))

    heads = [dict(head) for head in reference["heads"]] if reference is not None else []
    numbers = [dict(number) for number in reference["numbers"]] if reference is not None else []
    queries, query_keys = [], {}
    head_keys = {(head["attribute"], head["facet"], tuple(head["namespaces"])): index for index, head in enumerate(heads)}
    number_keys = {tuple(number["key"]): index for index, number in enumerate(numbers)}
    users = [[] for _ in authors]

    def node_query(attribute, facet, roots, train, positive, strict=False):
        namespaces = tuple(sorted({nodes[node][0] for node in roots}))
        key = (attribute, facet, namespaces)
        if key not in head_keys:
            if reference is not None:
                return None
            head_keys[key] = len(heads)
            heads.append({"attribute": attribute, "facet": facet, "namespaces": namespaces})
        head = head_keys[key]
        roots = tuple(sorted(set(roots)))
        key = (head, roots, strict)
        if key not in query_keys:
            query_keys[key] = len(queries)
            queries.append({"head": head, "roots": roots, "strict": strict, "positive_train": 0})
        query = query_keys[key]
        queries[query]["positive_train"] += int(train and positive)
        return query

    def atoms(attribute, item, train):
        shape = item["shape"]
        if shape == "numeric_cluster":
            key = (attribute, item["unit"], item.get("currency"), item.get("period"))
            if key not in number_keys:
                if reference is not None:
                    return [{"kind": "unknown"}]
                number_keys[key] = len(numbers)
                numbers.append({"key": key, "centers": [], "train": 0})
            index = number_keys[key]
            bounds = intervals(item, attribute)
            if train:
                numbers[index]["train"] += 1
                for low, high in bounds:
                    finite = [value for value in (low, high) if np.isfinite(value)]
                    if finite:
                        numbers[index]["centers"].append(float(np.mean(finite)))
            result = [{"kind": "numeric", "number": index, "bounds": bounds}]
            if attribute == "income":
                node = "income_context:" + orjson.dumps(key).decode()
                nodes[node] = ["income_context", orjson.dumps(key[1:]).decode(), "unit_context"]
                result += atoms(attribute, {"shape": "node", "node": node, "facet": "unit_context", "polarity": "positive"}, train)
            return result
        if shape != "node":
            raise ValueError(f"Unsupported target shape: {shape}")
        negative = item["polarity"] == "negative"
        above = sorted(path(item["node"]) - {item["node"]}) if attribute in PARTIAL and not negative else []
        queries = [node_query(attribute, item["facet"], [item["node"]], train, not negative)] + [node_query(attribute, item["facet"], [node], train, True, True) for node in above]
        return [{"kind": "node", "query": query, "negative": negative} if query is not None else {"kind": "unknown"} for query in queries]

    with gzip.open(root / "targets.jsonl.gz", "rb") as stream:
        for line in stream:
            author, attribute, target = orjson.loads(line)
            index = positions[author]
            if (reference is None and splits[index] == 2) or (reference is not None and splits[index] != 2):
                continue
            train = reference is None and splits[index] == 0
            groups = [[atoms(attribute, item, train)] for item in target["accepted"]]
            for alternative in target["alternatives"]:
                values = [option["all_of"] for option in alternative["any_of"]]
                if all(len(value) == 1 and value[0]["shape"] == "node" and value[0]["polarity"] == "positive" for value in values) and len({value[0]["facet"] for value in values}) == 1:
                    query = node_query(attribute, values[0][0]["facet"], [value[0]["node"] for value in values], train, True)
                    groups.append([[{"kind": "node", "query": query, "negative": False}] if query is not None else [{"kind": "unknown"}]])
                else:
                    groups.append([[atom for item in value for atom in atoms(attribute, item, train)] for value in values])
            if not groups:
                raise ValueError(f"Empty target for {author}: {attribute}")
            users[index].append({"attribute": fields.index(attribute), "groups": groups})
    namespaces = defaultdict(list)
    for node, (namespace, _, _) in sorted(nodes.items()):
        namespaces[namespace].append(node)
    for index, head in enumerate(heads):
        if reference is None:
            catalog = sorted(node for namespace in head["namespaces"] for node in namespaces[namespace])
            null = f"unasserted:{index}"
            catalog.append(null)
            nodes[null] = ["unasserted", "unasserted", "unasserted"]
            head.update(catalog=catalog, labels=[nodes[node][1] for node in catalog], kinds=[nodes[node][2] for node in catalog])
        else:
            catalog = head["catalog"]
        positions = {node: local for local, node in enumerate(catalog)}
        prior = np.full(len(catalog), .01 / len(catalog), dtype=np.float64) if reference is None else head["prior"].copy()
        rows, columns, count = [], [], 0
        for query in queries:
            if query["head"] != index:
                continue
            query["local"] = count
            expand = descendants if head["attribute"] in PARTIAL else lambda node: {node}
            members = sorted({positions[node] for root in query["roots"] for node in expand(root) - ({root} if query["strict"] else set()) if node in positions})
            if reference is None and members:
                prior[members] += query["positive_train"] / len(members)
            rows.extend([count] * len(members))
            columns.extend(members)
            count += 1
        head.update(prior=prior / prior.sum(), matrix=np.array([rows, columns], dtype=np.int64), query_count=count)
    for number in numbers if reference is None else []:
        centers = np.asarray(number.pop("centers"))
        number["center"] = float(np.median(centers)) if len(centers) else 0.
        number["scale"] = max(float(np.quantile(centers, .75) - np.quantile(centers, .25)), 1.) if len(centers) else 1.
    return {"users": users, "heads": heads, "queries": queries, "numbers": numbers, "fields": fields}
