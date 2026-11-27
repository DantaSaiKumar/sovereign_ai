from pathlib import Path
import os
from urllib.parse import urlparse

APP_NAME = "Sovereign AI Workbench"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SOVEREIGN_DATA_DIR", ROOT / "data")).expanduser().resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "sovereign.db"

# Deliberately restrict inference to this computer. Do not point this at a cloud endpoint.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
GENERAL_MODEL = os.getenv("SOVEREIGN_GENERAL_MODEL", "qwen2.5:1.5b")
VISION_MODEL = os.getenv("SOVEREIGN_VISION_MODEL", "moondream")
MAX_UPLOAD_MB = int(os.getenv("SOVEREIGN_MAX_UPLOAD_MB", "25"))
MAX_TEXT_CHARS = 1_000_000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 140
TOP_K = 4
AGENT_MAX_STEPS = 6

def validate_local_ollama_url(url: str = OLLAMA_BASE_URL) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "http" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Sovereign mode only permits an Ollama endpoint on this computer.")
    if parsed.port not in (None, 11434):
        # A custom local port is acceptable; host restriction is the security boundary.
        pass
    return url.rstrip("/")

def ensure_dirs():
    for path in (DATA_DIR, UPLOAD_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
