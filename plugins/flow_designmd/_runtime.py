"""flow_designmd 的 N.E.K.O. 运行时入口。

语料索引层在 _shared/（纯标准库）；这里只做编排。
来源：VoltAgent/awesome-design-md（MIT），见本目录 SOURCE.md。
"""

from __future__ import annotations

from typing import Annotated

try:
    from plugin.sdk.plugin import (
        Err,
        NekoPluginBase,
        Ok,
        neko_plugin,
        plugin_entry,
        ui,
    )
except ImportError:
    NekoPluginBase = object  # type: ignore[assignment,misc]
    def Ok(data):  # type: ignore[assignment]
        return {"ok": True, "data": data}
    def Err(error):  # type: ignore[assignment]
        return {"ok": False, "error": str(error)}
    def neko_plugin(cls):  # type: ignore[assignment]
        return cls

    class _UiFallback:
        """ui.context / ui.action 的本地兜底，签名与插件 SDK 一致。"""

        @staticmethod
        def context(**kwargs):
            def wrap(func):
                func._ui_context = kwargs
                return func

            return wrap

        @staticmethod
        def action(**kwargs):
            def wrap(func):
                func._ui_action = kwargs
                return func

            return wrap

    ui = _UiFallback

    def plugin_entry(**kwargs):  # type: ignore[no-untyped-def]
        def wrap(func):  # type: ignore[no-untyped-def]
            func._plugin_entry = kwargs  # type: ignore[attr-defined]
            return func

        return wrap

from ._shared.catalog import Catalog, CatalogError, scan  # noqa: E402
from ._shared.emit import (  # noqa: E402
    render_directory,
    to_css_variables,
    to_json_tokens,
    to_markdown_table,
)

#: 进程内缓存，避免每次入口重扫整个语料树。
_CACHE: dict[str, Catalog] = {}

def _load(root: str) -> Catalog:
    if root not in _CACHE:
        _CACHE[root] = scan(root)
    return _CACHE[root]

@neko_plugin
class FlowDesignMdPlugin(NekoPluginBase):
    """DESIGN.md 语料索引与导出。"""

    @ui.action(id="scan", label="扫描语料")
    @plugin_entry(id="scan", name="扫描语料", description="扫描 design-md 根目录并建索引。")
    async def scan_root(
        self,
        root: Annotated[str, "design-md 目录的绝对路径"] = "design-md",
    ) -> dict:
        try:
            catalog = _load(root)
            return Ok({"root": str(catalog.root), **catalog.stats()})
        except CatalogError as exc:
            return Err(str(exc))

    @ui.action(id="lookup", label="查条目")
    @plugin_entry(id="lookup", name="查条目", description="按 slug 或名字取一份 DESIGN.md。")
    async def lookup(
        self,
        slug: Annotated[str, "slug 或名字，如 claude"],
        root: Annotated[str, "design-md 目录"] = "design-md",
    ) -> dict:
        try:
            return Ok(_load(root).lookup(slug).to_dict())
        except (CatalogError, KeyError) as exc:
            return Err(str(exc))

    @ui.action(id="search", label="检索语料")
    @plugin_entry(
        id="search",
        name="检索语料",
        description="按关键词检索，命中 slug/名字加权最高。",
        llm_result_fields=["count", "results"],
    )
    async def search(
        self,
        term: Annotated[str, "检索词"],
        limit: Annotated[int, "最多返回几条"] = 10,
        root: Annotated[str, "design-md 目录"] = "design-md",
    ) -> dict:
        try:
            catalog = _load(root)
        except CatalogError as exc:
            return Err(str(exc))
        results = catalog.search(term)[: max(1, min(limit, 50))]
        return Ok(
            {
                "count": len(results),
                "results": [
                    {
                        "slug": entry.slug,
                        "name": entry.name,
                        "category": entry.category,
                        "token_count": entry.token_count,
                        "description": entry.description[:200],
                    }
                    for entry in results
                ],
            }
        )

    @ui.action(id="export", label="导出 token")
    @plugin_entry(
        id="export",
        name="导出 token",
        description="把一份 DESIGN.md 导出为 css / json / markdown。",
    )
    async def export(
        self,
        slug: Annotated[str, "slug 或名字"],
        fmt: Annotated[str, "css / json / markdown"] = "css",
        root: Annotated[str, "design-md 目录"] = "design-md",
    ) -> dict:
        try:
            entry = _load(root).lookup(slug)
        except (CatalogError, KeyError) as exc:
            return Err(str(exc))

        if fmt == "css":
            return Ok({"slug": entry.slug, "css": to_css_variables(entry)})
        if fmt == "json":
            return Ok({"slug": entry.slug, "tokens": to_json_tokens(entry)})
        if fmt == "markdown":
            return Ok({"slug": entry.slug, "markdown": to_markdown_table(entry)})
        return Err(f"unsupported format {fmt!r}; expected css / json / markdown")

    @ui.action(id="directory", label="目录索引")
    @plugin_entry(
        id="directory",
        name="目录索引",
        description="把整个语料渲染成分类目录文档。",
        llm_result_fields=["markdown"],
    )
    async def directory(
        self,
        root: Annotated[str, "design-md 目录"] = "design-md",
    ) -> dict:
        try:
            catalog = _load(root)
        except CatalogError as exc:
            return Err(str(exc))
        return Ok({"markdown": render_directory(catalog)})

    # -- Hosted UI ------------------------------------------------------

    @ui.context(id="dashboard")
    async def dashboard_context(self) -> dict:
        """plugin.toml 里的 context = "dashboard" 由这里提供 props.state。"""
        return {
            "labels": {
                "title": "Flow DesignMD",
                "subtitle": "DESIGN.md 语料索引",
                "root_hint": "指向 design-md/<slug>/DESIGN.md 布局的根目录；语料不在本仓库内。",
                "search_hint": "命中 slug 或名字时加权最高。",
            },
            "plugin_id": self.plugin_id,
        }
