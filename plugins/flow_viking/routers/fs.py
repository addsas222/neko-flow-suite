"""文件系统入口：ls / tree / read / write / mkdir / rm / grep / find。"""

from __future__ import annotations

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.errors import VikingError
from .._shared.layers import L0, L1, L2


class FsRouter(PluginRouter):
    """像操作文件一样操作 Agent 的上下文。"""

    def __init__(self) -> None:
        super().__init__(name="fs")

    def _fs(self):
        return self.main_plugin.fs

    def _persist(self) -> bool:
        return self.main_plugin.persist()

    def _handle(self, action):
        try:
            return Ok(action())
        except VikingError as exc:
            return Err(exc)

    @ui.action(id="viking_ls", label="ls")
    @plugin_entry(
        id="viking_ls",
        name="列出目录",
        description="列出一个 viking:// 目录的成员，含每个目录的生成摘要。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "default": "viking://"}},
        },
        llm_result_fields=["count", "entries"],
    )
    async def viking_ls(self, path: str = "viking://", **_):
        entries = self._fs().ls(path)
        return self._handle(lambda: {"count": len(entries), "entries": entries})

    @ui.action(id="viking_tree", label="tree")
    @plugin_entry(
        id="viking_tree",
        name="目录树",
        description="返回带深度上限的目录树。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "viking://"},
                "depth": {"type": "integer", "minimum": 1, "maximum": 6, "default": 3},
            },
        },
    )
    async def viking_tree(self, path: str = "viking://", depth: int = 3, **_):
        return self._handle(
            lambda: {"entries": self._fs().tree(path, max_depth=max(1, min(depth, 6)))}
        )

    @ui.action(id="viking_read", label="read")
    @plugin_entry(
        id="viking_read",
        name="读取",
        description="按层读取：l0 一行摘要、l1 结构化摘要、l2 完整内容。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "layer": {"type": "string", "enum": [L0, L1, L2], "default": L1},
            },
            "required": ["path"],
        },
        llm_result_fields=["path", "layer", "summary"],
    )
    async def viking_read(self, path: str, layer: str = L1, **_):
        def read() -> dict:
            node = self._fs().require(path)
            return node.layer(layer).to_dict()

        return self._handle(read)

    @ui.action(id="viking_write", label="write")
    @plugin_entry(
        id="viking_write",
        name="写入",
        description="写入一个文件；目录自动创建，摘要自动重新生成。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["path", "content"],
        },
        llm_result_fields=["path", "summary", "persisted"],
    )
    async def viking_write(self, path: str, content: str, tags: list | None = None, **_):
        def write() -> dict:
            node = self._fs().write(
                path, content, tags=tuple(t for t in (tags or []) if isinstance(t, str))
            )
            return {**node.to_dict(), "persisted": self._persist()}

        return self._handle(write)

    @ui.action(id="viking_mkdir", label="mkdir")
    @plugin_entry(
        id="viking_mkdir",
        name="创建目录",
        description="创建目录，包括中间层。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    async def viking_mkdir(self, path: str, **_):
        return self._handle(lambda: self._fs().mkdir(path).to_dict())

    @ui.action(id="viking_rm", label="rm")
    @plugin_entry(
        id="viking_rm",
        name="删除",
        description="删除一个文件或目录。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    async def viking_rm(self, path: str, **_):
        def remove() -> dict:
            self._fs().remove(path)
            return {"removed": path, "persisted": self._persist()}

        return self._handle(remove)
