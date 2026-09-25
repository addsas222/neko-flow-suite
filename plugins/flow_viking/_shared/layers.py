"""L0 / L1 / L2 分层记忆。

L0 是一行摘要，用于先扫描再决定读什么；L1 是结构化摘要；L2 是完整内容。
读取顺序永远是 L0 → 需要时 L1 → 确实需要 L2。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

L0 = "l0"
L1 = "l1"
L2 = "l2"
LAYERS = (L0, L1, L2)

L0_MAX_CHARS = 120
L1_MAX_CHARS = 600

@dataclass(slots=True)
class LayerRecord:
    """一个主体在某一层上的表示。"""

    path: str
    layer: str
    summary: str = ""
    content: str = ""
    tags: tuple[str, ...] = ()
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise ValueError(f"unknown layer {self.layer!r}")
        self.tags = tuple(self.tags) if not isinstance(self.tags, tuple) else self.tags

    @property
    def is_summary(self) -> bool:
        return self.layer in (L0, L1)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "layer": self.layer,
            "summary": self.summary,
            "tags": list(self.tags),
            "updated_at": self.updated_at,
        }
        if self.layer == L2:
            payload["content"] = self.content
        return payload

def demote(content: str, *, target_layer: str = L0) -> str:
    """把完整内容压成某一层的摘要。"""
    text = (content or "").strip()
    if not text:
        return ""
    if target_layer == L0:
        first = next((line for line in text.splitlines() if line.strip()), "")
        return first[:L0_MAX_CHARS]
    if target_layer == L1:
        return text[:L1_MAX_CHARS]
    return text

def promote(record: LayerRecord, *, target_layer: str = L2) -> LayerRecord:
    """把某一层提升到更完整的一层。"""
    if target_layer == L2:
        return LayerRecord(
            path=record.path,
            layer=L2,
            summary=record.summary,
            content=record.content,
            tags=record.tags,
            updated_at=record.updated_at,
        )
    return LayerRecord(
        path=record.path,
        layer=target_layer,
        summary=demote(record.content or record.summary, target_layer=target_layer),
        content="",
        tags=record.tags,
        updated_at=record.updated_at,
    )

@dataclass(slots=True)
class MemoryEntry:
    """一次提交进记忆系统的条目。"""

    path: str
    content: str
    source: str = ""
    tags: tuple[str, ...] = ()
    pinned: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "source": self.source,
            "tags": list(self.tags),
            "pinned": self.pinned,
            "chars": len(self.content or ""),
        }

@dataclass(slots=True)
class CommitResult:
    """一次提交的回执。"""

    committed: bool = False
    path: str = ""
    layer: str = L2
    summary: str = ""
    extracted: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "committed": self.committed,
            "path": self.path,
            "layer": self.layer,
            "summary": self.summary,
            "extracted": list(self.extracted),
            "message": self.message,
        }
