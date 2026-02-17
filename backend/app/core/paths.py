from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]  # kořen backend/

if os.getenv("RUNNING_IN_DOCKER"):
    UPLOAD_DIR = Path("/app/static/uploads")
else:
    UPLOAD_DIR = BASE_DIR / "static" / "uploads"
