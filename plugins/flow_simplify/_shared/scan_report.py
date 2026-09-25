"""扫描执行与覆盖率记录。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .scan import SKIP_DIRS, SOURCE_SUFFIXES, Candidate, ScanReport


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

def scan_repository(root: Path, *, limit: int = 400) -> ScanReport:
    """对 root 做一次只读发现，返回候选线索与盲区。"""
    import re

    from .scan import _CLASS_RE, _DEF_RE

    root = Path(root)
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and not any(part in SKIP_DIRS for part in path.parts)
    ]
    files.sort()

    report = ScanReport(root=str(root))
    report.files = len(files)
    definitions: list[tuple[str, Path, int]] = []

    for path in files:
        text = _read(path)
        if text is None:
            report.skipped += 1
            continue
        report.lines += text.count("\n") + 1
        for match in _DEF_RE.finditer(text):
            definitions.append((match.group(1), path, text.count("\n", 0, match.start()) + 1))
        for match in _CLASS_RE.finditer(text):
            definitions.append((match.group(1), path, text.count("\n", 0, match.start()) + 1))

    counts: dict[str, int] = {}
    for path in files:
        text = _read(path)
        if text is None:
            continue
        for name in {name for name, _, _ in definitions}:
            hits = len(re.findall(r"\b" + re.escape(name) + r"\b", text))
            if hits:
                counts[name] = counts.get(name, 0) + hits

    for name, path, line in definitions[:limit]:
        references = counts.get(name, 0)
        if references <= 1:
            report.candidates.append(
                Candidate(
                    kind="private" if name.startswith("_") else "public",
                    subject=name,
                    path=_relative(root, path),
                    line=line,
                    detail="referenced only at its definition",
                    references=references,
                )
            )

    report.totals = {
        "definitions": len(definitions),
        "candidates": len(report.candidates),
    }
    report.blind_spots = _blind_spots(files)
    return report

def _blind_spots(files: list[Path]) -> list[str]:
    spots = [
        "dynamic registration and entry-point dispatch",
        "persisted data format and migration consumers",
        "generated and vendored surfaces",
        "consumers outside this repository",
    ]
    if not files:
        spots.insert(0, "no Python source found in scope")
    return spots

def _relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:  # pragma: no cover - defensive
        return str(path)

def tree_summary(root: Path, *, max_depth: int = 3) -> dict[str, Any]:
    """给面板用的浅层目录概览。"""
    root = Path(root)
    if not root.is_dir():
        return {"root": str(root), "exists": False}
    entries: list[dict[str, Any]] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        except OSError:
            return
        for child in children:
            if child.name in SKIP_DIRS:
                continue
            entries.append(
                {
                    "path": str(child.relative_to(root)),
                    "is_dir": child.is_dir(),
                    "depth": depth,
                }
            )
            if child.is_dir():
                walk(child, depth + 1)

    walk(root, 0)
    return {"root": str(root), "exists": True, "entries": entries[:200]}
