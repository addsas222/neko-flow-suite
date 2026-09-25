"""viking:// 路径：解析、归一化、连接与相对解析。

所有路径都以 viking:// 开头。相对解析只在同一个根内发生，不允许越出根。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import PathError

SCHEME = "viking://"
ROOT = "viking://"
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_FORBIDDEN = {"..", ".", ""}

@dataclass(frozen=True, slots=True)
class VPath:
    """一个已解析的 viking:// 路径。"""

    raw: str
    segments: tuple[str, ...]

    @property
    def is_root(self) -> bool:
        return not self.segments

    @property
    def parent(self) -> "VPath":
        if self.is_root:
            return self
        return VPath(SCHEME, self.segments[:-1])

    @property
    def name(self) -> str:
        return self.segments[-1] if self.segments else ""

    def child(self, name: str) -> "VPath":
        return parse(SCHEME + "/".join((*self.segments, name)))

    def to_url(self) -> str:
        return SCHEME + "/".join(self.segments)

    def relative_to(self, base: "VPath") -> str:
        """返回相对 base 的路径；不在 base 之下时抛出 PathError。"""
        if len(base.segments) > len(self.segments):
            raise PathError(f"{self.to_url()} is not under {base.to_url()}")
        if self.segments[: len(base.segments)] != base.segments:
            raise PathError(f"{self.to_url()} is not under {base.to_url()}")
        return "/".join(self.segments[len(base.segments):])

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.to_url()

def normalize(value: str) -> str:
    """把任意输入收敛成规范的 viking:// URL。"""
    return parse(value).to_url()

def parse(value: str) -> VPath:
    """解析一个 viking:// 路径。"""
    if not isinstance(value, str) or not value.strip():
        raise PathError("a viking:// path is required")

    text = value.strip()
    if not text.lower().startswith(SCHEME):
        text = SCHEME + text.lstrip("/")

    body = text[len(SCHEME):].strip("/")
    if not body:
        return VPath(SCHEME, ())

    segments: list[str] = []
    for segment in body.split("/"):
        piece = segment.strip()
        if piece in _FORBIDDEN or piece not in _SEGMENT_RE.pattern and not _SEGMENT_RE.match(piece):
            raise PathError(f"invalid path segment: {segment!r}")
        if not _SEGMENT_RE.match(piece):
            raise PathError(f"invalid path segment: {segment!r}")
        segments.append(piece)

    if len(segments) > 16:
        raise PathError("a viking:// path holds at most 16 segments")
    return VPath(SCHEME, tuple(segments))

def join(base: str, *parts: str) -> str:
    """把若干段拼到 base 之下。"""
    path = parse(base)
    for part in parts:
        if not part:
            continue
        path = path.child(str(part).strip("/"))
    return path.to_url()

def resolve(base: str, target: str) -> str:
    """把 target 解析成基于 base 的绝对 viking:// 路径。

    target 已经是 viking:// 时直接返回；否则作为 base 的子路径。
    """
    if str(target).strip().lower().startswith(SCHEME):
        return normalize(target)
    return join(base, target)

def is_ancestor(candidate: VPath, other: VPath) -> bool:
    """candidate 是否是 other 的祖先（含自身）。"""
    return other.segments[: len(candidate.segments)] == candidate.segments
