"""审查引擎：对 diff 文本或仓库路径跑信号，并收割技术债标记。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .review import (
    _CONFIG_DEFAULT,
    _PLACEHOLDER,
    _SPECULATIVE,
    _UNUSED_PARAM,
    DEBT_MARKER,
    DebtNote,
    ReviewFinding,
    ReviewReport,
    SIGNALS,
)

MAX_FINDINGS = 200
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "dist", "build", "vendor", ".tox",
}


def review_diff(diff: str, *, target: str = "diff") -> ReviewReport:
    """审查一段 diff 文本：只看新增行。"""
    report = ReviewReport(target=target)
    path = ""
    for raw in (diff or "").splitlines():
        if raw.startswith("+++ b/"):
            path = raw[len("+++ b/"):].strip()
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            report.findings.extend(_scan_line(raw[1:], path, 1))
        if raw.startswith("+") and DEBT_MARKER in raw:
            report.debt.append(DebtNote(path=path, line=1, text=raw[1:].strip()))
    report.findings = report.findings[:MAX_FINDINGS]
    report.delete_list = _delete_list(report)
    return report


def review_repo(root: str, *, limit: int = 400) -> ReviewReport:
    """对仓库做只读审查。"""
    base = Path(root or "").expanduser()
    report = ReviewReport(target=str(base))
    if not base.is_dir():
        return report

    files = [
        path
        for path in base.rglob("*.py")
        if path.is_file() and not any(part in SKIP_DIRS for part in path.parts)
    ]
    files.sort()
    report.files = len(files)

    for path in files[:limit]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(base))
        report.findings.extend(_unused_parameter_findings(text, rel))
        for index, line in enumerate(text.splitlines(), start=1):
            report.findings.extend(_scan_line(line, rel, index))
            if DEBT_MARKER in line:
                report.debt.append(DebtNote(path=rel, line=index, text=line.strip()))

    report.findings = _dedupe(report.findings)[:MAX_FINDINGS]
    report.delete_list = _delete_list(report)
    return report


def _unused_parameter_findings(text: str, rel: str) -> list[ReviewFinding]:
    """只在形参确实没有出现在函数体里时才报。"""
    lines = text.splitlines()
    findings: list[ReviewFinding] = []
    for index, line in enumerate(lines):
        match = _UNUSED_PARAM.match(line)
        if not match:
            continue
        signature = match.group(1).strip()
        if not signature or signature.startswith(("*",)):
            continue
        body = _function_body(lines, index)
        for raw in signature.split(","):
            name = raw.split(":")[0].split("=")[0].strip().lstrip("*")
            if not name or name in ("self", "cls", "*", "**", "_", "**_"):
                continue
            if not re.search(r"\b" + re.escape(name) + r"\b", body):
                findings.append(
                    _finding(
                        "unused-parameter",
                        rel,
                        index + 1,
                        f"{name} in {signature[:40]}",
                        "parameter never read in the body",
                        "delete the parameter and fix the call sites",
                    )
                )
    return findings


def _function_body(lines: list[str], start: int) -> str:
    indent = len(lines[start]) - len(lines[start].lstrip())
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            continue
        current = len(line) - len(line.lstrip())
        if current <= indent and line.strip():
            break
        collected.append(line)
    return "\n".join(collected)


def _dedupe(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    seen: set[tuple[str, int, str]] = set()
    unique: list[ReviewFinding] = []
    for finding in findings:
        key = (finding.path, finding.line, finding.code)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def _scan_line(line: str, path: str, line_no: int) -> list[ReviewFinding]:
    found: list[ReviewFinding] = []
    stripped = line.strip()
    if not stripped:
        return found

    # 注释信号要能在注释行上报警，其他信号只在代码行上报警。
    if _PLACEHOLDER.search(stripped):
        found.append(
            _finding(
                "commentary-excuse",
                path,
                line_no,
                stripped[:48],
                "placeholder comment left in the added code",
                "fix the thing being worked around, then delete the comment",
            )
        )
    if stripped.startswith("#"):
        return found

    for code, label, delete in SIGNALS:
        if code == "speculative-generality" and _SPECULATIVE.match(line):
            found.append(_finding(code, path, line_no, "conditional branch", label, delete))
        if code == "config-without-choice" and _CONFIG_DEFAULT.match(line):
            found.append(_finding(code, path, line_no, stripped[:48], "single-valued setting", delete))
        if code == "reimplemented-stdlib" and _reimplements_stdlib(stripped):
            found.append(_finding(code, path, line_no, stripped[:48], "stdlib reimplementation", delete))
    return found


def _finding(
    code: str, path: str, line_no: int, subject: str, evidence: str, delete: str
) -> ReviewFinding:
    return ReviewFinding(
        code=code,
        path=path,
        line=line_no,
        subject=subject,
        evidence=evidence,
        delete=delete,
    )


def _reimplements_stdlib(stripped: str) -> bool:
    """只对函数定义声明本身报警，避免把普通调用也算成重写。"""
    lowered = stripped.lower()
    if not lowered.startswith(("def ", "async def ")):
        return False
    return any(name in lowered for name in ("flatten", "chunk", "dedupe", "merge_dict", "deep_get"))


def _delete_list(report: ReviewReport) -> list[str]:
    seen: list[str] = []
    for finding in report.findings:
        entry = f"{finding.path}:{finding.line} {finding.subject}"
        if entry not in seen:
            seen.append(entry)
    return seen


def harvest_debt(report: ReviewReport) -> dict[str, Any]:
    """把技术债标记汇总成台账，让"以后再改"不会变成"永远不改"。"""
    return {
        "count": len(report.debt),
        "notes": [note.to_dict() for note in report.debt],
        "next": "turn every ponytail: marker into one change with an explicit boundary",
    }
