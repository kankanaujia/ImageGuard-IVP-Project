"""Evidence hashing and safe upload validation helpers."""
import hashlib
from pathlib import Path

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def safe_extension(filename: str) -> str:
    # Return only the suffix; never use the supplied path as a storage path.
    return Path(filename).suffix.lower()
