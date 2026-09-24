"""反默认规则引擎：把上游的硬规则变成可扫描源码的规则表。

用法：
    from _shared.lint import lint_html
    report = lint_html(source_text)
    if report.blocked: ...
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules_core import (
    RULES_CORE,
    SEVERITY_BLOCK,
    SEVERITY_DEMOTE,
    SEVERITY_WARN,
    Rule,
)
from .rules_copy import RULES_COPY

RULES: tuple[Rule, ...] = RULES_CORE + RULES_COPY


@dataclass(slots=True)
class Finding:
    rule_id: str
    severity: str
    line: int
    column: int
    message: str
    fix: str
    evidence: str = ""
    override: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "fix": self.fix,
            "evidence": self.evidence,
            "override": self.override,
        }


@dataclass(slots=True)
class Report:
    findings: list[Finding] = field(default_factory=list)
    scanned: int = 0
    where: str = "snippet"

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    def by_severity(self, severity: str) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == severity]

    @property
    def blocked(self) -> bool:
        return bool(self.by_severity(SEVERITY_BLOCK))

    def verdict(self) -> str:
        if self.blocked:
            return "blocked"
        if self.findings:
            return "warn"
        return "clean"

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict(),
            "scanned": self.scanned,
            "counts": {
                SEVERITY_BLOCK: len(self.by_severity(SEVERITY_BLOCK)),
                SEVERITY_WARN: len(self.by_severity(SEVERITY_WARN)),
                SEVERITY_DEMOTE: len(self.by_severity(SEVERITY_DEMOTE)),
            },
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def render(self) -> str:
        lines = [f"verdict: {self.verdict()}"]
        for finding in self.findings:
            lines.append(
                f"[{finding.severity}] {finding.rule_id} {finding.line}:{finding.column}"
                f" {finding.message} -> {finding.fix}"
            )
        return "\n".join(lines)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def lint(text: str, *, where: str = "snippet") -> Report:
    """扫描一段 HTML/CSS/TSX 源码，返回可阻断的报告。"""
    report = Report(scanned=len(text.splitlines()))
    offsets = _line_offsets(text)

    for rule in RULES:
        for match in rule.matches(text):
            start = match.start()
            line_no = 1
            for index, offset in enumerate(offsets):
                if offset > start:
                    line_no = index
                    break
            column = start - offsets[line_no - 1] + 1
            report.findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    line=line_no,
                    column=column,
                    message=rule.message,
                    fix=rule.fix,
                    evidence=match.group(0)[:80],
                    override=rule.override,
                )
            )

    report.findings.sort(key=lambda f: (f.line, f.column, f.rule_id))
    report.where = where
    return report


def lint_files(paths: list[str]) -> Report:
    """扫描若干文件并汇总成一个报告。"""
    from pathlib import Path

    combined = Report()
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        combined.extend(lint(text, where=path).findings)
    combined.scanned = len(paths)
    return combined


def lint_html(text: str) -> Report:
    return lint(text)


def lint_css(text: str) -> Report:
    return lint(text)


def rule_ids() -> tuple[str, ...]:
    return tuple(rule.id for rule in RULES)


def rules_for(severity: str) -> tuple[Rule, ...]:
    return tuple(rule for rule in RULES if rule.severity == severity)
