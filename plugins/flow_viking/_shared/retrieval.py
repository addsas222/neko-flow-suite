"""检索：目录先行 + 词法排序，保留周边上下文。

检索在向量排序之前先按目录范围收窄，因此 Agent 能搜索某个项目或记忆子树，
保留它的周边上下文，并在知识演进时重组它。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .fsstore import VDir, VFile, VirtualFS
from .vpath import VPath, parse

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")

@dataclass(slots=True)
class RetrievalHit:
    """一次检索命中。"""

    path: str
    score: float
    summary: str
    kind: str
    directory: str
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": round(self.score, 4),
            "summary": self.summary,
            "kind": self.kind,
            "directory": self.directory,
            "snippet": self.snippet,
        }

def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())

def search(
    fs: VirtualFS,
    query: str,
    *,
    scope: str = "viking://",
    limit: int = 10,
    include_content: bool = False,
) -> list[RetrievalHit]:
    """在 scope 子树内做词法检索。"""
    root = parse(scope)
    wanted = tokens(query)
    if not wanted:
        return []

    documents: list[tuple[Any, str]] = []
    for node in fs.descendants(root.to_url()):
        if isinstance(node, VFile):
            documents.append((node, node.summary + " " + node.content))
        elif isinstance(node, VDir):
            documents.append((node, node.summary + " " + " ".join(node.names())))

    frequencies = _term_frequencies(wanted)
    total = len(documents) or 1
    hits: list[RetrievalHit] = []

    for node, text in documents:
        score = _score(text, wanted, frequencies, total)
        if score <= 0:
            continue
        hits.append(
            RetrievalHit(
                path=node.path,
                score=score,
                summary=_summary_of(node),
                kind="dir" if isinstance(node, VDir) else "file",
                directory=str(VPath(parse(node.path).raw, parse(node.path).segments[:-1])),
                snippet=_snippet(text, wanted, include_content),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.path))
    return hits[: max(1, limit)]

def grep(fs: VirtualFS, pattern: str, *, scope: str = "viking://", limit: int = 20) -> list[dict[str, Any]]:
    """在 scope 子树内逐文件查找。"""
    root = parse(scope)
    regex = re.compile(pattern)
    matches: list[dict[str, Any]] = []
    for node in fs.descendants(root.to_url()):
        if not isinstance(node, VFile):
            continue
        for line_no, line in enumerate(node.content.splitlines(), start=1):
            if regex.search(line):
                matches.append(
                    {"path": node.path, "line": line_no, "text": line.strip()[:200]}
                )
                if len(matches) >= max(1, limit):
                    return matches
    return matches

def find(
    fs: VirtualFS,
    query: str,
    *,
    scope: str = "viking://",
    limit: int = 10,
) -> list[RetrievalHit]:
    """语义查找：先扫 L0/L1 摘要，再决定是否展开内容。"""
    hits = search(fs, query, scope=scope, limit=limit, include_content=False)
    if hits:
        return hits
    # 摘要层没有命中时再退回内容层，避免一开始就读全部 L2。
    return search(fs, query, scope=scope, limit=limit, include_content=True)

def _summary_of(node: Any) -> str:
    if isinstance(node, VDir):
        return node.summary
    if isinstance(node, VFile):
        return node.summary
    return ""

def _snippet(text: str, wanted: list[str], include_content: bool) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(token in line.lower() for token in wanted):
            return line[:200] if include_content else line[:120]
    return ""

def _term_frequencies(wanted: list[str]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for token in wanted:
        counts[token] = counts.get(token, 0) + 1
    return counts

def _score(text: str, wanted: list[str], frequencies: dict[str, float], total: int) -> float:
    lowered = text.lower()
    score = 0.0
    for token, frequency in frequencies.items():
        hits = lowered.count(token)
        if not hits:
            continue
        idf = math.log((total + 1) / (1 + (1 if frequency else 0)))
        score += (1.0 + math.log(hits)) * max(idf, 0.25)
    return score
