"""虚拟文件系统：目录、文件与节点模型。

每个目录都带一份生成的摘要，因此 Agent 可以先扫摘要再决定读什么。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .errors import ConflictError, NotFoundError
from .layers import L0, L1, L2, LayerRecord, demote
from .vpath import parse


@dataclass(slots=True)
class VFile:
    """一个文件：L0/L1 摘要常驻，L2 内容按需读取。"""

    path: str
    content: str = ""
    summary: str = ""
    abstract: str = ""
    tags: tuple[str, ...] = ()
    updated_at: float = 0.0

    def refresh(self, *, now: float | None = None) -> None:
        text = (self.content or "").strip()
        self.summary = demote(text, target_layer=L0)
        self.abstract = demote(text, target_layer=L1)
        self.updated_at = now if now is not None else time.time()

    def layer(self, layer: str) -> LayerRecord:
        if layer == L2:
            return LayerRecord(self.path, L2, self.summary, self.content, self.tags, self.updated_at)
        if layer == L1:
            return LayerRecord(self.path, L1, self.abstract, "", self.tags, self.updated_at)
        return LayerRecord(self.path, L0, self.summary, "", self.tags, self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "file",
            "path": self.path,
            "summary": self.summary,
            "chars": len(self.content or ""),
            "tags": list(self.tags),
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class VDir:
    """一个目录：自带摘要与成员清单。"""

    path: str
    children: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    updated_at: float = 0.0

    def refresh(self, *, now: float | None = None) -> None:
        self.updated_at = now if now is not None else time.time()

    @property
    def summary(self) -> str:
        names = self.names()
        return ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")

    def names(self) -> list[str]:
        return sorted(self.children)

    def get(self, name: str) -> Any | None:
        return self.children.get(name)

    def put(self, name: str, node: Any) -> None:
        self.children[name] = node
        self.refresh()

    def remove(self, name: str) -> None:
        self.children.pop(name, None)
        self.refresh()

    def layer(self, layer: str) -> LayerRecord:
        listing = "\n".join(self.names())
        if layer == L2:
            return LayerRecord(self.path, L2, self.summary, listing, self.tags, self.updated_at)
        if layer == L1:
            return LayerRecord(self.path, L1, self.summary, "", self.tags, self.updated_at)
        return LayerRecord(self.path, L0, self.summary, "", self.tags, self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "dir",
            "path": self.path,
            "summary": self.summary,
            "children": len(self.children),
            "updated_at": self.updated_at,
        }


VNode = VFile | VDir

class VirtualFS:
    """以 viking:// 为根的树。"""

    def __init__(self) -> None:
        self.root = VDir("viking://")

    def node(self, path: str) -> VNode | None:
        current: VNode = self.root
        for segment in parse(path).segments:
            if not isinstance(current, VDir):
                return None
            nxt = current.get(segment)
            if nxt is None:
                return None
            current = nxt
        return current

    def require(self, path: str) -> VNode:
        node = self.node(path)
        if node is None:
            raise NotFoundError(f"not found: {path}")
        return node

    def require_dir(self, path: str) -> VDir:
        node = self.require(path)
        if not isinstance(node, VDir):
            raise ConflictError(f"not a directory: {path}")
        return node

    def require_file(self, path: str) -> VFile:
        node = self.require(path)
        if not isinstance(node, VFile):
            raise ConflictError(f"not a file: {path}")
        return node

    def parent_dir(self, path: str) -> VDir:
        return self.require_dir(parse(path).parent.to_url())

    def mkdir(self, path: str) -> VDir:
        parsed = parse(path)
        current = self.root
        for segment in parsed.segments:
            existing = current.get(segment)
            if existing is None:
                new_dir = VDir(parse(current.path + "/" + segment).to_url())
                current.put(segment, new_dir)
                current = new_dir
                continue
            if isinstance(existing, VFile):
                raise ConflictError(f"a file already exists at {existing.path}")
            current = existing
        current.refresh()
        return current

    def write(self, path: str, content: str, *, tags: tuple[str, ...] = ()) -> VFile:
        parsed = parse(path)
        self.mkdir(parsed.parent.to_url())
        directory = self.parent_dir(path)
        existing = directory.get(parsed.name)
        if isinstance(existing, VDir):
            raise ConflictError(f"a directory already exists at {path}")
        if existing is None:
            existing = VFile(path)
            directory.put(parsed.name, existing)
        existing.content = content
        existing.tags = tuple(tags)
        existing.refresh()
        return existing

    def try_write(self, path: str, content: str, *, tags: tuple[str, ...] = ()) -> VFile | None:
        """写文件，但失败时返回 None 而不抛出。

        恢复持久化树时使用：单个坏条目不应让整棵树加载失败。
        """
        try:
            return self.write(path, content, tags=tags)
        except (ConflictError, NotFoundError, PathError, ValueError):
            return None

    def try_mkdir(self, path: str) -> VDir | None:
        """创建目录，但失败时返回 None 而不抛出。"""
        try:
            return self.mkdir(path)
        except (ConflictError, PathError, ValueError):
            return None

    def remove(self, path: str) -> None:
        parsed = parse(path)
        if parsed.is_root:
            raise ConflictError("refusing to remove the viking:// root")
        self.parent_dir(path).remove(parsed.name)

    def ls(self, path: str) -> list[dict[str, Any]]:
        node = self.require(path)
        if isinstance(node, VDir):
            return [child.to_dict() for child in (node.get(n) for n in node.names()) if child]
        return [node.to_dict()]

    def tree(self, path: str, *, max_depth: int = 3) -> list[dict[str, Any]]:
        node = self.require(path)
        if not isinstance(node, VDir):
            return [node.to_dict()]
        collected: list[dict[str, Any]] = []

        def walk(directory: VDir, depth: int) -> None:
            collected.append(directory.to_dict())
            if depth >= max_depth:
                return
            for name in directory.names():
                child = directory.get(name)
                if isinstance(child, VDir):
                    walk(child, depth + 1)
                elif child is not None:
                    collected.append(child.to_dict())

        walk(node, 0)
        return collected

    def descendants(self, path: str) -> list[VNode]:
        node = self.require(path)
        if not isinstance(node, VDir):
            return [node]
        collected: list[VNode] = []

        def walk(directory: VDir) -> None:
            for name in directory.names():
                child = directory.get(name)
                if child is None:
                    continue
                collected.append(child)
                if isinstance(child, VDir):
                    walk(child)

        walk(node)
        return collected

    def all_files(self) -> list[VFile]:
        return [node for node in self.descendants("viking://") if isinstance(node, VFile)]
