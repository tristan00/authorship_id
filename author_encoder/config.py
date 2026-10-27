from pathlib import Path

LUAR = ("rrivera1849/LUAR-MUD", "f1db50251805ed69b43cf4f72ea2f0e231f36a1c")
VECTOR_STORE = Path(r"D:\reddit_data\user_vectors\pretrained_luar_64.sqlite3")
DIMENSIONS = 512
TEXTS_PER_USER = 64
MAX_LENGTH = 192
BATCH_USERS = 256
ENCODE_BATCH = 1024
CPU_THREADS = 8
SOURCE_WORKERS = 16
PREPARE_WORKERS = 8
MODEL_FILES = ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.json", "merges.txt")
