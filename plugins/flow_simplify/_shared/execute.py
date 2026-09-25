"""执行与撤销：一次删除只动一个所有权边界，并留下可回滚的痕迹。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .proof import ProofRecord


@dataclass(slots=True)
class CutResult:
    """一次删除的操作回执。"""

    applied: bool = False
    subject: str = ""
    boundary: str = ""
    target: str = ""
    rollback: str = ""
    message: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "subject": self.subject,
            "boundary": self.boundary,
            "target": self.target,
            "rollback": self.rollback,
            "message": self.message,
            "warnings": list(self.warnings),
        }

def execute_cut(root: str, proof: ProofRecord, *, dry_run: bool = False) -> CutResult:
    """执行一次删除。

    这里只移动到一个可撤销的隔离目录，不做行级改写：行级改写必须由使用者
    在编辑器里完成，插件把"证明—执行—验证—撤销"框架固定下来。
    """
    result = CutResult(subject=proof.subject, boundary=proof.cut_boundary)
    if not proof.is_actionable():
        result.message = (
            "refusing an unproved cut; the proof record is missing required fields"
        )
        return result

    base = Path(root).expanduser()
    if not base.is_dir():
        result.message = f"repository path is not a directory: {base}"
        return result

    target = _locate(base, proof.location)
    if target is None:
        result.message = f"could not locate the cut boundary from {proof.location!r}"
        return result

    quarantine = base / ".simplify-quarantine"
    destination = quarantine / proof.subject.replace("/", "_")
    result.target = str(target)
    result.rollback = f"move {destination} back to {target}"

    if dry_run:
        result.applied = False
        result.message = "dry run; nothing moved"
        return result

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(destination))
    except (OSError, shutil.Error) as exc:
        result.message = f"move failed: {exc}"
        return result

    result.applied = True
    result.message = (
        "moved to quarantine; verification is still yours to run, and this "
        "result does not by itself prove broader runtime or user acceptance"
    )
    result.warnings.append(
        "a narrow green check does not establish runtime, deployment or user acceptance"
    )
    return result

def _locate(base: Path, location: str) -> Path | None:
    """从 location 字符串里取出 `path` 或 `path:line`。"""
    text = (location or "").strip()
    if not text:
        return None
    candidate = text.split(":", 1)[0].strip()
    if not candidate:
        return None
    target = Path(candidate)
    if not target.is_absolute():
        target = base / target
    target = target.resolve()
    if target.exists() and _inside(target, base.resolve()):
        return target
    return None

def _inside(target: Path, base: Path) -> bool:
    try:
        target.relative_to(base)
    except ValueError:
        return False
    return True
