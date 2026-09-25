"""发现门面：把扫描、覆盖率与排序合成一次调查结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .proof import ProofRecord
from .scan import ScanReport
from .scan_report import scan_repository, tree_summary


@dataclass(slots=True)
class Finding:
    """一次调查交付给上层的单元：线索、它的证明状态与下一步所需证据。"""

    candidate: str
    kind: str
    path: str
    line: int
    references: int
    proof_state: str = "unproved"
    next_fact: str = ""
    confidence: str = "guess"
    benefit: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate,
            "kind": self.kind,
            "path": self.path,
            "line": self.line,
            "references": self.references,
            "proof_state": self.proof_state,
            "next_fact": self.next_fact,
            "confidence": self.confidence,
            "benefit": self.benefit,
        }

@dataclass(slots=True)
class Discovery:
    """一次只读调查的完整结果。"""

    mode: str
    scope: str
    root: str
    report: ScanReport | None = None
    findings: list[Finding] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "scope": self.scope,
            "root": self.root,
            "report": self.report.to_dict() if self.report else None,
            "findings": [f.to_dict() for f in self.findings],
            "coverage": dict(self.coverage),
        }

def discover(root: Path, *, mode: str = "survey", scope: str = "broad") -> Discovery:
    """跑一次只读调查。mode 与 scope 只影响记录方式，不改变发现手段。"""
    root = Path(root)
    if not root.is_dir():
        from .errors import ScopeError

        raise ScopeError(f"repository path is not a directory: {root}")

    report = scan_repository(root)
    findings = [
        Finding(
            candidate=candidate.subject,
            kind=candidate.kind,
            path=candidate.path,
            line=candidate.line,
            references=candidate.references,
            next_fact=(
                "name every runtime consumer before ranking this candidate"
                if candidate.references <= 1
                else "confirm the surviving consumers keep their contract"
            ),
        )
        for candidate in report.candidates
    ]
    return Discovery(
        mode=mode,
        scope=scope,
        root=str(root),
        report=report,
        findings=findings,
        coverage={
            "files": report.files,
            "lines": report.lines,
            "blind_spots": list(report.blind_spots),
            "tree": tree_summary(root),
        },
    )

def record_from_finding(finding: Finding) -> ProofRecord:
    """把一条线索升级成待填写的证明记录。"""
    return ProofRecord(
        subject=finding.candidate,
        location=f"{finding.path}:{finding.line}",
        consumers={},
        unresolved=[finding.next_fact],
        confidence=finding.confidence,
        benefit=finding.benefit,
        verdict="unresolved",
    )
