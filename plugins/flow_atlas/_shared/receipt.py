"""诊断与回执数据类型。这一层不依赖布局，可被所有检查模块复用。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

@dataclass(slots=True)
class Issue:
    """一条可行动的诊断。"""

    code: str
    severity: str
    subject: str
    message: str
    supported_fixes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "subject": self.subject,
            "message": self.message,
            "supported_fixes": list(self.supported_fixes),
        }

@dataclass(slots=True)
class Receipt:
    """一次校验的回执。"""

    ok: bool
    diagram_type: str
    quality_profile: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    spec_sha256: str = ""
    spec_bytes: int = 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "diagram_type": self.diagram_type,
            "quality_profile": self.quality_profile,
            "checks": {"passed": list(self.passed), "failed": list(self.failed)},
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "spec_sha256": self.spec_sha256,
            "spec_bytes": self.spec_bytes,
        }

def record(receipt: Receipt, check: str, ok: bool, issue: Issue | None = None) -> None:
    """把一次检查的结果记入回执。"""
    if ok:
        receipt.passed.append(check)
        return
    receipt.failed.append(check)
    if issue is not None:
        receipt.errors.append(issue)

def digest(payload: bytes) -> tuple[str, int]:
    """返回 payload 的 SHA-256 与字节数。"""
    return hashlib.sha256(payload).hexdigest(), len(payload)
