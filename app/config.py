"""Settings are read from environment variables each time, so tests can change them."""
import os

MAX_TEXT_CHARS = 50_000
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def get(name: str, default: str = "") -> str:
    return os.getenv(name, default)
