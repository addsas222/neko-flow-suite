"""只读扫描：发现候选线索。

静态检查只提供线索，不能单独证明一次删除是安全的。所有产出都是待追踪的
lead，直到运行时消费者和契约被检查过。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "dist", "build", "vendor", ".tox", ".idea",
}
SOURCE_SUFFIXES = {".py"}

_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)


@dataclass(slots=True)
class Candidate:
    """一条待证明的线索。"""

    kind: str
    subject: str
    path: str
    line: int
    detail: str = ""
    references: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "subject": self.subject,
            "path": self.path,
            "line": self.line,
            "detail": self.detail,
            "references": self.references,
        }


@dataclass(slots=True)
class ScanReport:
    """一次只读扫描的结果。"""

    root: str
    files: int = 0
    skipped: int = 0
    lines: int = 0
    totals: dict[str, int] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "files": self.files,
            "skipped": self.skipped,
            "lines": self.lines,
            "totals": dict(self.totals),
            "candidates": [c.to_dict() for c in self.candidates],
            "blind_spots": list(self.blind_spots),
        }
