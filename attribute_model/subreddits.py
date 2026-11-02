import json
from functools import lru_cache

import lance
import numpy as np
import psycopg
import pyarrow as pa
import pyarrow.compute as pc
import scipy.sparse as sparse
from pyarrow import csv
from sklearn.utils.extmath import randomized_svd

from author_encoder.config import VECTOR_STORE
from database import DSN, NO_AUTHOR

from . import LOG, timed, write_json
from .config import SUBREDDIT_CHUNK, SUBREDDIT_RANK, SUBREDDIT_SAMPLE, SUBREDDIT_TOP, SUBREDDITS

COUNTS = "COPY (SELECT author, subreddit, count(*) FROM records WHERE author <> ALL(%s) GROUP BY author, subreddit) TO STDOUT (FORMAT CSV)"
ONE = "SELECT subreddit, count(*) FROM records WHERE author = %s GROUP BY subreddit"
PARALLEL = ("SET max_parallel_workers_per_gather = 12", "SET work_mem = '512MB'", "SET parallel_setup_cost = 0", "SET parallel_tuple_cost = 0")
VECTORS = SUBREDDITS / "vectors.npy"
FACTORS = SUBREDDITS / "factors.npy"
IDF = SUBREDDITS / "idf.npy"
NAMES = SUBREDDITS / "names.json"
MANIFEST = SUBREDDITS / "manifest.json"
TYPES = {"author": pa.string(), "subreddit": pa.string(), "records": pa.int32()}


@timed
def read_counts():
    chunks = bytearray()
    with psycopg.connect(DSN) as conn:
        for setting in PARALLEL:
            conn.execute(setting)
        with conn.cursor().copy(COUNTS, [NO_AUTHOR]) as copy:
            for chunk in copy:
                chunks += chunk
    table = csv.read_csv(pa.BufferReader(chunks), read_options=csv.ReadOptions(column_names=list(TYPES)), convert_options=csv.ConvertOptions(column_types=TYPES, strings_can_be_null=False))
    LOG.info("subreddit counts rows=%d", table.num_rows)
    return table


def normalized(rows, columns, values, idf, shape):
    matrix = sparse.csr_matrix((np.log1p(values) * idf[columns], (rows, columns)), shape=shape, dtype=np.float32)
    norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(1)).ravel())
    return sparse.diags(1 / np.maximum(norms, 1e-6)).dot(matrix).tocsr()


@timed
def fitted(rows, columns, values, idf, authors):
    chosen = rows % SUBREDDIT_SAMPLE == 0
    matrix = normalized(rows[chosen] // SUBREDDIT_SAMPLE, columns[chosen], values[chosen], idf, (authors // SUBREDDIT_SAMPLE + 1, len(idf)))
    LOG.info("subreddit sample shape=%s nonzeros=%d", matrix.shape, matrix.nnz)
    return randomized_svd(matrix, n_components=SUBREDDIT_RANK, n_iter=3, random_state=0)[2].astype(np.float32)


@timed
def projected(rows, columns, values, idf, factors, authors):
    matrix = normalized(rows, columns, values, idf, (authors, len(idf)))
    vectors = np.lib.format.open_memmap(VECTORS, mode="w+", dtype=np.float16, shape=(authors, SUBREDDIT_RANK))
    transposed = factors.T
    for start in range(0, authors, SUBREDDIT_CHUNK):
        vectors[start:start + SUBREDDIT_CHUNK] = (matrix[start:start + SUBREDDIT_CHUNK] @ transposed).astype(np.float16)
    vectors.flush()


def source():
    store = lance.dataset(VECTOR_STORE)
    return json.loads(store.schema.metadata[b"source"])["months"], store.count_rows()


def current():
    if not MANIFEST.exists():
        return False
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    months, authors = source()
    return manifest["months"] == months and manifest["authors"] == authors


def stored():
    if not current():
        raise ValueError("Subreddit vectors do not match the user vector store; run attribute_model subreddits")
    return np.load(VECTORS, mmap_mode="r")


@timed
def build():
    SUBREDDITS.mkdir(parents=True, exist_ok=True)
    MANIFEST.unlink(missing_ok=True)
    months, authors = source()
    names = lance.dataset(VECTOR_STORE).to_table(columns=["author"], scan_in_order=True)["author"].combine_chunks()
    table = read_counts()
    counted = pc.value_counts(table["subreddit"])
    order = np.argsort(-counted.field(1).to_numpy(), kind="stable")[:SUBREDDIT_TOP]
    top = counted.field(0).take(pa.array(order))
    idf = np.log(authors / counted.field(1).take(pa.array(order)).to_numpy().astype(np.float64)).astype(np.float32)
    rows = pc.fill_null(pc.index_in(table["author"], value_set=names), -1).to_numpy()
    columns = pc.fill_null(pc.index_in(table["subreddit"], value_set=top), -1).to_numpy()
    keep = (rows >= 0) & (columns >= 0)
    rows, columns, values = rows[keep].astype(np.int64), columns[keep].astype(np.int64), table["records"].to_numpy()[keep].astype(np.float32)
    del table, keep, names
    LOG.info("subreddit nonzeros=%d authors=%d subreddits=%d", len(rows), authors, len(idf))
    factors = fitted(rows, columns, values, idf, authors)
    projected(rows, columns, values, idf, factors, authors)
    np.save(FACTORS, factors)
    np.save(IDF, idf)
    write_json(NAMES, top.to_pylist())
    write_json(MANIFEST, {"months": months, "authors": authors, "rank": SUBREDDIT_RANK})
    return {"authors": authors, "subreddits": len(idf)}


@lru_cache(maxsize=1)
def loaded():
    return {name: index for index, name in enumerate(json.loads(NAMES.read_text(encoding="utf-8")))}, np.load(IDF), np.load(FACTORS)


def vector(author):
    names, idf, factors = loaded()
    with psycopg.connect(DSN) as conn:
        found = [(names[subreddit], count) for subreddit, count in conn.execute(ONE, [author]) if subreddit in names]
    if not found:
        return np.zeros(SUBREDDIT_RANK, dtype=np.float32)
    columns, values = (np.array(column) for column in zip(*found))
    weights = np.log1p(values.astype(np.float32)) * idf[columns]
    return (weights / max(float(np.linalg.norm(weights)), 1e-6)) @ factors[:, columns].T
