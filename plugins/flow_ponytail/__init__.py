"""flow_ponytail — 让外部编码 Agent 像屋里最懒的资深工程师那样思考。

移植自 DietrichGebert/ponytail：最好的代码是你没写的那段。这个插件不替你
改代码；它把 YAGNI 阶梯、删除清单、强度等级和不可越过的安全边界固化成可以
直接交给外部 Agent 的规则集。
"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import Ok, NekoPluginBase, lifecycle, neko_plugin, plugin_entry, tr, ui

from ._shared.intensity import LEVELS, describe, normalize_level
from .routers.export import ExportRouter
from .routers.review import ReviewRouter

PANEL_CONTEXT = "ponytail"


@neko_plugin
class FlowPonytailPlugin(NekoPluginBase):
    """极简教练插件。"""

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self.include_router(ReviewRouter())
        self.include_router(ExportRouter())
        self._level = normalize_level("full")

    @ui.context(id=PANEL_CONTEXT)
    async def ponytail_context(self) -> dict:
        return {
            "labels": {
                "title": tr("ponytail.title", default="Lazy Senior Dev"),
                "subtitle": tr("ponytail.subtitle", default="The best code is the code you never wrote."),
            },
            "levels": [{"level": name, "description": describe(name)} for name in LEVELS],
            "active_level": self._level,
            "last_error": "",
        }

    @plugin_entry(
        id="set_level",
        name="设置强度",
        description="设置极简规则的强度等级；off 不是关闭安全护栏。",
        input_schema={
            "type": "object",
            "properties": {"level": {"type": "string", "enum": list(LEVELS)}},
            "required": ["level"],
        },
        llm_result_fields=["level", "description"],
    )
    async def set_level(self, level: str, **_):
        self._level = normalize_level(level)
        return Ok({"level": self._level, "description": describe(self._level)})

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self.logger.info("flow_ponytail ready at level=%s", self._level)
        return {"status": "ready", "level": self._level}

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        self.logger.info("flow_ponytail stopped")
        return {"status": "stopped"}
