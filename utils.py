"""Simple atomic write helper used by MemoryStore.

Writes data to a temp file then renames into place for atomicity.
"""
from pathlib import Path
import tempfile
import os


def atomic_write_text(path: Path, text: str, tmp_prefix: str = ".tmp_"):
    path_parent = path.parent
    path_parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=tmp_prefix, dir=str(path_parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise
