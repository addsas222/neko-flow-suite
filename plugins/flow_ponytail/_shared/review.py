"""过度设计审查：信号发现、删除清单与技术债台账。

信号不是判决。每条 finding 都要指出"删掉什么、由谁验证"，否则只是噪音。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEBT_MARKER = "ponytail:"

SIGNALS: tuple[tuple[str, str, str], ...] = (
    (
        "speculative-generality",
        "为一个还不存在的用例预留分支",
        "删掉这个分支，或把它接到一个真实调用方",
    ),
    (
        "unused-parameter",
        "形参没有任何消费者",
        "删掉形参，并修掉调用点",
    ),
    (
        "commentary-excuse",
        "注释在解释为什么绕过问题",
        "修掉被绕过的问题，然后删掉注释",
    ),
    (
        "config-without-choice",
        "配置项只有一个取值被使用过",
        "删掉配置项，把唯一取值写进代码",
    ),
    (
        "reimplemented-stdlib",
        "重写了标准库已有的能力",
        "换成标准库调用",
    ),
)

_SPECULATIVE = re.compile(r"^\s*if\s+.*(?:elif\s+.*)?:\s*$")
_UNUSED_PARAM = re.compile(r"^\s*(?:async\s+)?def\s+\w+\(([^)]*)\)")
_PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b")
_CONFIG_DEFAULT = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:os\.getenv|CONFIG|SETTINGS)")


@dataclass(slots=True)
class ReviewFinding:
    """一条可行动的过度设计信号。"""

    code: str
    path: str
    line: int
    subject: str
    evidence: str
    delete: str
    verified_by: str = "the smallest check that would fail if this deletion were wrong"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "subject": self.subject,
            "evidence": self.evidence,
            "delete": self.delete,
            "verified_by": self.verified_by,
        }


@dataclass(slots=True)
class DebtNote:
    """一条被推迟的简化，带标记与行号。"""

    path: str
    line: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line, "text": self.text}


@dataclass(slots=True)
class ReviewReport:
    """一次审查的结果。"""

    target: str
    files: int = 0
    findings: list[ReviewFinding] = field(default_factory=list)
    debt: list[DebtNote] = field(default_factory=list)
    delete_list: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "files": self.files,
            "findings": [f.to_dict() for f in self.findings],
            "debt": [d.to_dict() for d in self.debt],
            "delete_list": list(self.delete_list),
        }
