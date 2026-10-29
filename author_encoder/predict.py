import hashlib
import json
from itertools import islice
from pathlib import Path
from tempfile import NamedTemporaryFile

from . import LOG, clean, timed
from .config import BATCH_USERS, DIMENSIONS, TEXTS_PER_USER
from .model import load_model
from .tokens import load_tokenizer, token_batches


def records(stream):
    authors = set()
    for line_number, line in enumerate(stream, 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict) or not isinstance(record.get("author"), str) or not record["author"].strip():
            raise ValueError(f"Line {line_number}: author must be a nonempty string")
        author = record["author"]
        if author in authors:
            raise ValueError(f"Line {line_number}: duplicate author {author}")
        authors.add(author)
        texts = record.get("texts")
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise ValueError(f"Line {line_number}: texts must be a list of strings")
        usable = [(index, cleaned) for index, text in enumerate(texts) if (cleaned := clean(text))]
        if len(usable) < TEXTS_PER_USER:
            raise ValueError(f"Line {line_number}: {author} needs at least {TEXTS_PER_USER} usable texts")
        selected = sorted(usable, key=lambda item: hashlib.sha256(f"luar-user-vector-64-v1:{author}:{item[0]}:{item[1]}".encode()).digest())[:TEXTS_PER_USER]
        yield {"author": author, "usable_texts": len(usable), "sampled_texts": TEXTS_PER_USER, "sample_indices": [index for index, _ in selected], "dimensions": DIMENSIONS}, [text for _, text in selected]


@timed
def encode_file(source, output, device="cuda"):
    if output.exists():
        raise FileExistsError(output)
    model = load_model(device)
    tokenizer = load_tokenizer()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    count = 0
    try:
        with source.open(encoding="utf-8") as stream, NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, prefix=output.name + ".", suffix=".tmp", delete=False) as target:
            temporary = Path(target.name)
            incoming = records(stream)
            while batch := list(islice(incoming, BATCH_USERS)):
                texts = [text for _, texts in batch for text in texts]
                features = model.features(token_batches(tokenizer, texts), len(texts))
                vectors = model.users(features.reshape(len(batch), TEXTS_PER_USER, -1))
                for (metadata, _), vector in zip(batch, vectors, strict=True):
                    target.write(json.dumps(metadata | {"vector": vector.tolist()}) + "\n")
                count += len(batch)
                LOG.info("encoded users=%d output=%s", count, output)
            if not count:
                raise ValueError("Input contains no users")
        temporary.rename(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"users": count, "dimensions": DIMENSIONS, "output": str(output)}
