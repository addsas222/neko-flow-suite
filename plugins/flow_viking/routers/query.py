"""查询入口：grep / find / reload。"""

from __future__ import annotations

from plugin.sdk.plugin import Ok, PluginRouter, plugin_entry, ui

from .._shared.errors import VikingError
from .._shared.retrieval import find, grep
from .._shared.store import load


class QueryRouter(PluginRouter):
    """目录先行 + 词法排序的检索面。"""

    def __init__(self) -> None:
        super().__init__(name="query")

    def _fs(self):
        return self.main_plugin.fs

    def _handle(self, action):
        try:
            return Ok(action())
        except VikingError as exc:
            from plugin.sdk.plugin import Err

            return Err(exc)

    @ui.action(id="viking_grep", label="grep")
    @plugin_entry(
        id="viking_grep",
        name="检索文本",
        description="在子树内逐文件查找正则。",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "viking://"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["pattern"],
        },
        llm_result_fields=["matches"],
    )
    async def viking_grep(self, pattern: str, path: str = "viking://", limit: int = 20, **_):
        return self._handle(
            lambda: {"matches": grep(self._fs(), pattern, scope=path, limit=limit)}
        )

    @ui.action(id="viking_find", label="find")
    @plugin_entry(
        id="viking_find",
        name="语义查找",
        description="先在 l0/l1 摘要层检索，需要时才展开内容。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "default": "viking://"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
        llm_result_fields=["hits"],
    )
    async def viking_find(self, query: str, path: str = "viking://", limit: int = 10, **_):
        return self._handle(
            lambda: {
                "hits": [hit.to_dict() for hit in find(self._fs(), query, scope=path, limit=limit)]
            }
        )

    @ui.action(id="viking_reload", label="Reload tree")
    @plugin_entry(
        id="viking_reload",
        name="从磁盘重载",
        description="放弃内存中的改动，从磁盘重新加载整棵树。",
        input_schema={"type": "object", "properties": {}},
    )
    async def viking_reload(self, **_):
        def reload() -> dict:
            plugin = self.main_plugin
            plugin._fs = load(plugin.data_path("viking"))
            return {"files": len(plugin.fs.all_files()), "reloaded": True}

        return self._handle(reload)

    @ui.action(id="viking_summary", label="Summaries")
    @plugin_entry(
        id="viking_summary",
        name="全树摘要",
        description="只返回 l0 摘要，用于先扫描再决定读什么。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "default": "viking://"}},
        },
    )
    async def viking_summary(self, path: str = "viking://", **_):
        def summarize() -> dict:
            return {
                "path": path,
                "summaries": [
                    {"path": node.path, "summary": node.summary}
                    for node in self._fs().descendants(path)
                ],
            }

        return self._handle(summarize)
