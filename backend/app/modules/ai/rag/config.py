import os
from pathlib import Path

# ---------- REDIS ----------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ---------- CHROMA ----------
# Lokální persistentní úložiště vektorové DB
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = (BASE_DIR / "chroma_db").as_posix()
CHROMA_COLLECTION = "product_descriptions"

# ---------- EMBEDDINGS ----------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ---------- MEDIA ----------
MEDIA_ROOT = os.getenv(
    "MEDIA_ROOT",
    "backend/app/static/media"
)
