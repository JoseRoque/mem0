"""Example provider scaffold adapted for mem0.

Provides a simple in-memory provider for demonstration and tests.
"""
from __future__ import annotations
import json
import threading
import time
from typing import Any, Dict, List, Optional
from memory_provider import MemoryProvider, RecallStatus, INDICATOR_GLYPH, spawn_context_thread

class ExampleMemoryProvider(MemoryProvider):
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._last_recall = None

    @property
    def name(self) -> str:
        return "example"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        # Start a background indexer if desired (demo only)
        def _indexer():
            while True:
                time.sleep(10)
                # noop in demo
        thr = spawn_context_thread(_indexer, name=f"{self.name}-indexer")
        thr.start()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        with self._lock:
            info = self._sessions.get(session_id, {"items": []})
            items = info.get("items", [])
            self._last_recall = RecallStatus(provider_label=self.name, count=len(items))
            return "\n".join(items[-5:]) if items else ""

    def recall_status(self) -> Optional[RecallStatus]:
        return self._last_recall

    def get_tool_schemas(self) -> List[dict]:
        return []

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        return json.dumps({"success": False, "error": "no tools"})

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "", messages: Optional[list] = None, **kwargs) -> None:
        with self._lock:
            info = self._sessions.setdefault(session_id, {"items": []})
            info["items"].append(user_content)

    def shutdown(self) -> None:
        return None
