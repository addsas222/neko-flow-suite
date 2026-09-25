"""本地记忆存储与 recall：作为多后端记忆层的默认实现。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .redact import redact

MAX_ENTRIES = 2000
STORE_NAME = "memory.json"

@dataclass(slots=True)
class MemoryEntry:
    """一条已脱敏的记忆。"""

    entry_id: str
    text: str
    tags: tuple[str, ...] = ()
    source: str = ""
    created_at: float = 0.0
    hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "text": self.text,
            "tags": list(self.tags),
            "source": self.source,
            "created_at": self.created_at,
            "hits": self.hits,
        }

@dataclass(slots=True)
class MemoryStore:
    """本地 JSON 记忆存储。"""

    directory: Path
    entries: dict[str, MemoryEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.directory = Path(self.directory)
        self._load()

    def _load(self) -> None:
        target = self.directory / STORE_NAME
        if not target.is_file():
            return
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        entries = raw.get("entries") if isinstance(raw, dict) else None
        if not isinstance(entries, list):
            return
        for item in entries:
            if not isinstance(item, dict):
                continue
            entry_id = item.get("entry_id")
            text = item.get("text")
            if not isinstance(entry_id, str) or not isinstance(text, str):
                continue
            self.entries[entry_id] = MemoryEntry(
                entry_id=entry_id,
                text=text,
                tags=tuple(t for t in item.get("tags", []) if isinstance(t, str)),
                source=str(item.get("source", "")),
                created_at=float(item.get("created_at", 0.0) or 0.0),
                hits=int(item.get("hits", 0) or 0),
            )

    def _save(self) -> bool:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "entries": [e.to_dict() for e in self.entries.values()]}
        temporary = self.directory / (STORE_NAME + ".tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
            )
            temporary.replace(self.directory / STORE_NAME)
        except OSError:
            return False
        return True

    def record(
        self,
        entry_id: str,
        text: str,
        *,
        tags: tuple[str, ...] = (),
        source: str = "",
    ) -> MemoryEntry:
        cleaned = redact(text, strict=False)
        if not (entry_id or "").strip():
            raise ValueError("entry_id is required")
        entry = MemoryEntry(
            entry_id=entry_id.strip(),
            text=cleaned,
            tags=tuple(tags),
            source=source,
            created_at=time.time(),
        )
        self.entries[entry.entry_id] = entry
        self._trim()
        self._save()
        return entry

    def recall(self, query: str, *, limit: int = 10, scope: str = "") -> list[dict[str, Any]]:
        wanted = [token for token in (query or "").lower().split() if token]
        if not wanted:
            return []
        scored: list[tuple[int, MemoryEntry]] = []
        for entry in self.entries.values():
            if scope and scope not in entry.tags and scope != entry.source:
                continue
            haystack = (entry.text + " " + " ".join(entry.tags)).lower()
            score = sum(haystack.count(token) for token in wanted)
            if score:
                entry.hits += 1
                scored.append((score, entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1].entry_id))
        return [entry.to_dict() for _, entry in scored[: max(1, limit)]]

    def _trim(self) -> None:
        if len(self.entries) <= MAX_ENTRIES:
            return
        ordered = sorted(self.entries.values(), key=lambda e: e.created_at)
        for entry in ordered[: len(self.entries) - MAX_ENTRIES]:
            self.entries.pop(entry.entry_id, None)

    def status(self) -> dict[str, Any]:
        return {
            "backend": "local",
            "entries": len(self.entries),
            "tags": sorted({tag for entry in self.entries.values() for tag in entry.tags}),
        }

def record(store: MemoryStore, entry_id: str, text: str, **kwargs: Any) -> MemoryEntry:
    return store.record(entry_id, text, **kwargs)

def recall(store: MemoryStore, query: str, **kwargs: Any) -> list[dict[str, Any]]:
    return store.recall(query, **kwargs)
