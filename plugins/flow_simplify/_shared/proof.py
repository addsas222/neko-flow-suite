"""证明记录：每个候选都必须能被定位、被证明、被验证。

原则：删掉多少行只是佐证。真正的收益是删掉一个需要长期维护的事实、状态、
契约或概念。找不到真实消费者的候选应当保留，而不是为了输出结果强行删除。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CONFIDENCE_RANK = {"proved": 3, "likely": 2, "guess": 1}
BENEFIT_RANK = {"high": 3, "medium": 2, "low": 1}
VERDICTS = ("keep", "cut", "merge", "unresolved")

REQUIRED_FIELDS = (
    "location",
    "burden",
    "consumers",
    "cut_boundary",
    "consequence",
    "verification",
    "net_complexity",
)


@dataclass(slots=True)
class ProofRecord:
    """一条候选的完整证明。"""

    subject: str
    location: str = ""
    burden: str = ""
    consumers: dict[str, list[str]] = field(default_factory=dict)
    cut_boundary: str = ""
    consequence: str = ""
    verification: str = ""
    net_complexity: str = ""
    confidence: str = "guess"
    benefit: str = "medium"
    verdict: str = "unresolved"
    unresolved: list[str] = field(default_factory=list)
    notes: str = ""

    def is_actionable(self) -> bool:
        """只有填满全部必填字段的候选才能被排序或执行。"""
        return all(getattr(self, name, "") for name in REQUIRED_FIELDS)

    def rank(self) -> tuple[int, int]:
        return (CONFIDENCE_RANK.get(self.confidence, 0), BENEFIT_RANK.get(self.benefit, 0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "location": self.location,
            "burden": self.burden,
            "consumers": dict(self.consumers),
            "cut_boundary": self.cut_boundary,
            "consequence": self.consequence,
            "verification": self.verification,
            "net_complexity": self.net_complexity,
            "confidence": self.confidence,
            "benefit": self.benefit,
            "verdict": self.verdict,
            "unresolved": list(self.unresolved),
            "notes": self.notes,
            "actionable": self.is_actionable(),
        }


class ProofLedger:
    """一次审计或修改会话内的证明记录集合。"""

    def __init__(self) -> None:
        self._records: dict[str, ProofRecord] = {}

    def add(self, record: ProofRecord) -> ProofRecord:
        if not record.subject:
            raise ValueError("a proof record needs a subject")
        self._records[record.subject] = record
        return record

    def get(self, subject: str) -> ProofRecord | None:
        return self._records.get(subject)

    def all(self) -> list[ProofRecord]:
        return list(self._records.values())

    def ranked(self) -> list[ProofRecord]:
        """按置信度优先、收益其次排序；不把高价值猜测排在已证明的小删除之前。"""
        return sorted(self.all(), key=lambda r: r.rank(), reverse=True)

    def unresolved(self) -> list[ProofRecord]:
        return [r for r in self.all() if r.unresolved]

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [record.to_dict() for record in self.ranked()],
            "unresolved": [record.subject for record in self.unresolved()],
        }


def rank(records: list[ProofRecord]) -> list[ProofRecord]:
    """见 ProofLedger.ranked。"""
    return sorted(records, key=lambda r: r.rank(), reverse=True)
