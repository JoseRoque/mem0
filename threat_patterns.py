"""Very small threat pattern scanner used by MemoryStore.

This is a stub for demo purposes. Replace with a real scanner as needed.
"""
from typing import Optional

def first_threat_message(text: str, scope: str = "strict") -> Optional[str]:
    # naive: reject entries containing script tags or SQL-like injection hints
    if not text:
        return None
    lowered = text.lower()
    if "<script" in lowered or "drop table" in lowered or "rm -rf" in lowered:
        return "Blocked: suspicious content detected"
    return None
