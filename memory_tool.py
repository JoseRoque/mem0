"""Small example of how to call MemoryStore as a simple tool wrapper.

This file demonstrates the path from a tool-like call into MemoryStore methods.
"""
import json
from memory_store import MemoryStore

_store = None

def load_store():
    global _store
    if _store is None:
        _store = MemoryStore()
        _store.load_from_disk()
    return _store


def memory_tool(action: str | None = None, target: str = "memory", content: str | None = None, old_text: str | None = None, operations: list | None = None):
    store = load_store()
    if operations:
        return json.dumps(store.apply_batch(target, operations))
    if action == "add":
        return json.dumps(store.add(target, content or ""))
    if action == "remove":
        return json.dumps(store.remove(target, old_text or ""))
    if action == "patch":
        return json.dumps(store.patch(target, old_text or "", content or ""))
    return json.dumps({"success": False, "error": "Unknown action"})
