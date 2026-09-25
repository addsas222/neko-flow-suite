"""flow_simplify — 用证据证明并移除代码库里的偶然复杂度。

移植自 tt-a1i/simplify-codebase 的工作流：Survey（只读审计）与 Change
（授权修改）分开，Focused 与 Broad 分开。删掉多少行只是佐证；真正的收益是
删掉一个需要长期维护的事实、状态、契约或概念。
"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import NekoPluginBase, Ok, lifecycle, neko_plugin, plugin_entry, tr, ui

from .routers.change import ChangeRouter
from .routers.survey import SurveyRouter


@neko_plugin
class FlowSimplifyPlugin(NekoPluginBase):
    """代码瘦身插件。"""

    # 声明 router 类，供主进程静态扫描 entry 元数据
    __routers__ = [SurveyRouter, ChangeRouter]

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        # 注册 routers — 必须在 __init__ 中，collect_entries 在 startup 之前调用
        for router_cls in self.__routers__:
            self.include_router(router_cls())

    @ui.action(id="guide", label="使用方式")
    @plugin_entry(
        id="guide",
        name="使用方式",
        description="Survey 与 Change 的权威模式说明。",
        llm_result_fields=["modes", "scopes", "principle"],
    )
    async def guide(self, **_):
        return Ok(
            {
                "modes": {
                    "survey": "read-only audit; report ranked evidence and blind spots",
                    "change": "prove each cut, implement within scope, validate the surviving contract",
                },
                "scopes": {
                    "focused": "cover one named boundary thoroughly before expanding outward",
                    "broad": "partition the system and account for every in-scope domain",
                },
                "principle": (
                    "Deleting lines of code is supporting evidence, not the objective. "
                    "A successful run may conclude that the surface is already justified."
                ),
            }
        )

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self.logger.info("flow_simplify ready; survey mode is read-only")
        return {"status": "ready"}

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        self.logger.info("flow_simplify stopped")
        return {"status": "stopped"}

    @ui.context(id="simplify")
    async def simplify_context(self) -> dict:
        """Hosted UI 面板状态。"""
        directory = self.data_path("audits")
        directory.mkdir(parents=True, exist_ok=True)
        survey = self._router("survey")
        last = getattr(survey, "last_report", None) or {}
        return {
            "labels": {
                "title": tr("simplify.title", default="Codebase Simplify"),
                "subtitle": tr("simplify.subtitle", default="Prove first, then delete."),
            },
            "last_report": last,
            "audit_dir": str(directory),
            "last_error": "",
        }

    def _router(self, name: str):
        for router in self.list_routers():
            if router.name == name:
                return router
        return None

