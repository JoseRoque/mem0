"""Minimal writable MemoryStore adapted from Hermes' tools/memory_tool_store.py.

This is a trimmed, self-contained version intended for reuse. It stores
entries in files under <app_home>/memories/MEMORY.md and USER.md separated by
an ENTRY_DELIMITER.

Not all Hermes edge-cases are included; adapt drift detection, locking and
threat-scanning for production use.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

from utils import atomic_write_text
from constants import get_app_home
from threat_patterns import first_threat_message as _first_threat_message

ENTRY_DELIMITER = "\n§\n"
MEMORY_FILENAME = "MEMORY.md"
USER_FILENAME = "USER.md"


def _scan_memory_content(content: str) -> Optional[str]:
    return _first_threat_message(content, scope="strict")


class MemoryStore:
    def __init__(self, memory_char_limit: int = 2200, user_char_limit: int = 1375,
                 memory_enabled: bool = True, user_profile_enabled: bool = True):
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        self.memory_enabled = memory_enabled
        self.user_profile_enabled = user_profile_enabled
        self._system_prompt_snapshot = {"memory": "", "user": ""}

    # path helpers
    def _mem_dir(self) -> Path:
        return get_app_home() / "memories"

    def _path_for(self, target: str) -> Path:
        fname = USER_FILENAME if target == "user" else MEMORY_FILENAME
        return self._mem_dir() / fname

    def _char_limit(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    def _entries_for(self, target: str) -> List[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set_entries(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    # file read/write
    def _read_raw_checked(self, path: Path) -> Tuple[str, bool]:
        if not path.exists():
            return "", True
        try:
            return path.read_text(encoding="utf-8-sig"), True
        except (OSError, UnicodeDecodeError):
            return "", False

    def _parse_entries(self, raw: str) -> List[str]:
        return [e for e in (x.strip() for x in raw.split(ENTRY_DELIMITER)) if e]

    def _write_file(self, path: Path, entries: List[str]):
        atomic_write_text(path, ENTRY_DELIMITER.join(entries), tmp_prefix=".mem_")

    # load and snapshot
    def load_from_disk(self):
        for target in ("memory", "user"):
            path = self._path_for(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            raw, ok = self._read_raw_checked(path)
            if not ok:
                # keep empty lists on unreadable file
                self._set_entries(target, [])
                self._system_prompt_snapshot[target] = ""
                continue
            entries = list(dict.fromkeys(self._parse_entries(raw)))
            # simple threat replacement in snapshot
            def _sanitize(e):
                findings = _first_threat_message(e, scope="strict") if e and not e.startswith("[BLOCKED:") else None
                return e if not findings else f"[BLOCKED: {findings}]"
            self._set_entries(target, entries)
            self._system_prompt_snapshot[target] = ENTRY_DELIMITER.join(_sanitize(e) for e in entries) if entries else ""

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        return self._system_prompt_snapshot.get(target) or None

    # mutation primitives: add/patch/remove and an atomic batch
    def add(self, target: str, content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}
        if _scan_memory_content(content):
            return {"success": False, "error": "Content blocked by policy."}

        def _add(entries, limit):
            if content in entries:
                return entries, "Entry already exists."
            if len(ENTRY_DELIMITER.join(entries + [content])) > limit:
                return {"success": False, "error": "Would exceed char limit."}
            return entries + [content], "Entry added."

        return self._mutate(target, _add, skip_drift=True)

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        if not old_text.strip():
            return {"success": False, "error": "old_text cannot be empty."}
        return self._edit(target, old_text.strip(), None, None)

    def patch(self, target: str, old_text: str, new_text: str, matched_entry: Optional[str] = None) -> Dict[str, Any]:
        if not old_text or not new_text:
            return {"success": False, "error": "old_text and new_text are required."}
        return self._patch(target, old_text, new_text, matched_entry)

    def apply_batch(self, target: str, operations: List[dict]) -> Dict[str, Any]:
        return self._batch(target, operations, commit=True)

    # internal helpers adapted/simplified
    def _mutate(self, target: str, mutate, *, skip_drift: bool = False) -> Dict[str, Any]:
        path = self._path_for(target)
        raw, read_ok = self._read_raw_checked(path)
        if not read_ok:
            return {"success": False, "error": "Could not read existing file; aborting to avoid data loss."}
        entries = list(dict.fromkeys(self._parse_entries(raw)))
        self._set_entries(target, entries)
        result = mutate(self._entries_for(target), self._char_limit(target))
        if isinstance(result, dict):
            return result
        new_entries, message = result[0], result[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_file(path, new_entries)
        # refresh snapshot for new entries
        self._system_prompt_snapshot[target] = ENTRY_DELIMITER.join(new_entries)
        return {"success": True, "message": message, "target": target}

    def _locate(self, entries: List[str], old_text: str) -> Optional[int]:
        for i, e in enumerate(entries):
            if e == old_text or old_text in e:
                return i
        return None

    def _edit(self, target: str, old_text: str, new_content: Optional[str], matched_entry: Optional[str] = None) -> Dict[str, Any]:
        def _apply(entries, limit):
            idx = self._locate(entries, old_text)
            if idx is None:
                return {"success": False, "error": "No entry matched."}
            if new_content is None:
                replaced = entries[:idx] + entries[idx+1:]
                return replaced, "Entry removed."
            replaced = entries[:idx] + [new_content] + entries[idx+1:]
            if len(ENTRY_DELIMITER.join(replaced)) > limit:
                return {"success": False, "error": "Replacement would exceed limit."}
            return replaced, "Entry replaced."
        return self._mutate(target, _apply)

    def _patch(self, target: str, old_text: str, new_text: str, matched_entry: Optional[str] = None) -> Dict[str, Any]:
        def _apply(entries, limit):
            idx = self._locate(entries, old_text)
            if idx is None:
                return {"success": False, "error": "No entry matched."}
            entry = entries[idx]
            patched = entry.replace(old_text, new_text, 1)
            if patched == entry:
                return {"success": False, "error": "Patch is a no-op."}
            entries[idx] = patched
            if len(ENTRY_DELIMITER.join(entries)) > limit:
                return {"success": False, "error": "Patch would exceed char limit."}
            return entries, "Entry patched."
        return self._mutate(target, _apply)

    def _batch(self, target: str, operations: List[dict], commit: bool) -> Dict[str, Any]:
        if not operations:
            return {"success": False, "error": "operations list is empty."}
        ops = [op or {} for op in operations]
        def _apply(entries, limit):
            working = list(entries)
            for op in ops:
                act = op.get("action")
                content = op.get("content", "")
                old_text = op.get("old_text", "")
                if act == "add":
                    if content not in working:
                        working.append(content)
                elif act == "remove":
                    idx = self._locate(working, old_text)
                    if idx is None:
                        return {"success": False, "error": f"No entry matched '{old_text}' in batch."}
                    working.pop(idx)
                elif act == "patch":
                    idx = self._locate(working, old_text)
                    if idx is None:
                        return {"success": False, "error": f"No entry matched '{old_text}' in batch."}
                    working[idx] = working[idx].replace(old_text, content, 1)
                else:
                    return {"success": False, "error": f"Unknown action {act}"}
            if len(ENTRY_DELIMITER.join(working)) > limit:
                return {"success": False, "error": "Batch would exceed char limit."}
            return working, f"Applied {len(ops)} operation(s)."
        return self._mutate(target, _apply, skip_drift=not commit)
