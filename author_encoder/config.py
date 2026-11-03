from pathlib import Path

LUAR = ("rrivera1849/LUAR-MUD", "f1db50251805ed69b43cf4f72ea2f0e231f36a1c")
VECTOR_STORE = Path(r"C:\reddit_data\user_vectors.lance")
TEXT_STORE = Path(r"C:\reddit_data\text_vectors\bodies.lance")
VECTOR_WORK = Path(r"C:\reddit_data\vector_work")
DIMENSIONS = 512
TEXTS_PER_USER = 256
MAX_LENGTH = 192
BATCH_USERS = 256
TOKEN_BUDGET = 65536
CUDA_MEMORY = 12 * 2**30
HASH_PARTS = 1024
BUCKETS = 256
RECORD_BLOCKS = 65536
HEAD_TEXTS = 65536
EXACT_STORE = Path(r"C:\reddit_data\user_vectors_exact")
EXACT_CHUNK = 1 << 18
EXACT_THREADS = 8
CPU_THREADS = 8
FETCH_THREADS = 8
WHOLE_FRAGMENT_SHARE = .1
PREPARE_WORKERS = 4
MODEL_FILES = ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.json", "merges.txt")
