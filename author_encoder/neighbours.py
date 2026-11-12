import numpy as np

from database import client

from . import LOG, timed

REDUCED = 128
SAMPLE = 100
SHORTLIST = 500


@timed
def reduce():
    db = client()
    sample = db.query_np(f"SELECT vector FROM author_vectors WHERE cityHash64(author) % {SAMPLE} = 7")
    vectors = np.stack(sample[:, 0]).astype(np.float64)
    values, axes = np.linalg.eigh(vectors.T @ vectors)
    components = axes[:, ::-1][:, :REDUCED].T.astype(np.float32)
    kept = float(values[::-1][:REDUCED].sum() / values.sum())
    db.command("CREATE OR REPLACE TABLE author_axes (position UInt16, axis Array(Float32)) ENGINE = MergeTree ORDER BY position")
    db.insert("author_axes", list(enumerate(components.tolist())), column_names=("position", "axis"))
    db.command("DROP TABLE IF EXISTS author_reduced_next")
    db.command("CREATE TABLE author_reduced_next (author String CODEC(ZSTD(1)), reduced Array(BFloat16)) ENGINE = MergeTree ORDER BY author")
    rows = db.command("INSERT INTO author_reduced_next WITH (SELECT groupArray(axis) FROM (SELECT axis FROM author_axes ORDER BY position)) AS axes "
                      f"SELECT author, CAST([{', '.join(f'dotProduct(vector, axes[{axis}])' for axis in range(1, REDUCED + 1))}] AS Array(BFloat16)) FROM author_vectors").written_rows
    db.command("CREATE TABLE IF NOT EXISTS author_reduced AS author_reduced_next")
    db.command("EXCHANGE TABLES author_reduced_next AND author_reduced")
    db.command("DROP TABLE author_reduced_next")
    LOG.info("author_reduced rows=%d dimensions=%d sample=%d kept=%.3f", rows, REDUCED, len(vectors), kept)
    return {"rows": rows, "dimensions": REDUCED, "sample": len(vectors), "kept": kept}


@timed
def similar(author, limit):
    db = client()
    if not db.command("SELECT count() FROM author_vectors WHERE author = {author:String}", parameters={"author": author}):
        return None
    rows = db.query("WITH (SELECT vector FROM author_vectors WHERE author = {author:String}) AS target, (SELECT reduced FROM author_reduced WHERE author = {author:String}) AS sketch "
                    "SELECT author, texts, 1 - cosineDistance(vector, target) AS similarity FROM author_vectors WHERE author IN "
                    "(SELECT author FROM author_reduced WHERE author != {author:String} ORDER BY dotProduct(reduced, sketch) DESC LIMIT {shortlist:UInt32}) "
                    "ORDER BY similarity DESC LIMIT {limit:UInt32}", parameters={"author": author, "limit": limit, "shortlist": SHORTLIST}).result_rows
    return {"author": author, "neighbours": [{"author": name, "texts": texts, "similarity": similarity} for name, texts, similarity in rows]}
