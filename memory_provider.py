"""MemoryProvider ABC and small context-thread helpers.

Adapted from Hermes agent's agent/memory_provider.py (trimmed).
"""
from __future__ import annotations

import contextvars
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

INDICATOR_GLYPH = "🧠"


def ctx_bound(fn: Callable[..., Any]) -> Callable[..., Any]:
    ctx = contextvars.copy_context()
    return lambda *args, **kwargs: ctx.run(fn, *args, **kwargs)


def spawn_context_thread(target: Callable[..., Any], *, name: str, daemon: bool = True,
                         args: tuple = (), kwargs: Optional[dict[str, Any]] = None) -> threading.Thread:
    return threading.Thread(target=ctx_bound(target), args=args, kwargs=kwargs or {}, name=name, daemon=daemon)


@dataclass(frozen=True)
class RecallStatus:
    provider_label: str
    count: int
    glyph: str = INDICATOR_GLYPH


class MemoryProvider(ABC):
    """Abstract base for memory providers.

    Implement initialize(), is_available(), prefetch(), get_tool_schemas(),
    handle_tool_call(), sync_turn(), shutdown() at minimum.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        raise NotImplementedError

    def system_prompt_block(self) -> str:
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        return None

    def recall_status(self) -> Optional[RecallStatus]:
        return None

    @abstractmethod
    def get_tool_schemas(self) -> List[dict]:
        return []

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "", messages: Optional[list[dict]] = None, **kwargs) -> None:
        return None

    def shutdown(self) -> None:
        return None
