"""flow_impeccable 的 N.E.K.O. 运行时入口。

规则层在 _shared/（纯标准库）；这里只做编排。
来源：pbakaus/impeccable（Apache-2.0），见本目录 SOURCE.md。
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

from ._shared.commands import ids, route  # noqa: E402
from ._shared.craftfloor import evaluate as evaluate_floor  # noqa: E402
from ._shared.passes import (  # noqa: E402
    Verification,
    batch_targets,
    plan_for,
    violates_bounded_policy,
)


@neko_plugin
class FlowImpeccablePlugin(NekoPluginBase):
    """设计命令路由 + 有界验证 + craft floor。"""

    @ui.action(id="route", label="路由请求")
    @plugin_entry(
        id="route",
        name="路由请求",
        description="把一句设计请求路由到对应的 impeccable 命令与 reference。",
    )
    async def route_request(
        self,
        request: Annotated[str, "用户的原始请求，如 make my spacing tighter"],
    ) -> dict:
        try:
            return Ok(route(request).to_dict())
        except Exception as exc:  # noqa: BLE001
            return Err(str(exc))

    @ui.action(id="commands", label="命令表")
    @plugin_entry(id="commands", name="命令表", description="列出全部命令与分组。")
    async def commands(self) -> dict:
        from ._shared.commands import COMMANDS

        return Ok(
            {
                "commands": [
                    {
                        "id": command.id,
                        "group": command.group,
                        "label": command.label,
                        "reference": command.reference,
                        "summary": command.summary,
                        "takes_target": command.takes_target,
                    }
                    for command in COMMANDS
                ],
                "ids": list(ids()),
            }
        )

    @ui.action(id="plan", label="有界验证计划")
    @plugin_entry(
        id="plan",
        name="有界验证计划",
        description="给出有界验证的轮次计划与批量检查目标。",
    )
    async def plan(
        self,
        scope: Annotated[str, "web / component / native"] = "web",
        rounds_used: Annotated[int, "已用的验证轮数"] = 0,
    ) -> dict:
        verification = Verification()
        for _ in range(max(0, rounds_used)):
            verification.record_round()
        return Ok(
            {
                "scope": scope,
                "passes": [pass_.name for pass_ in plan_for(scope)],
                "batch_targets": list(batch_targets(scope)),
                "verification": verification.to_dict(),
                "policy_violation": violates_bounded_policy(rounds_used, 1),
            }
        )

    @ui.action(id="craftfloor", label="Craft floor")
    @plugin_entry(
        id="craftfloor",
        name="Craft floor",
        description="判定一批评改是否踩了 craft floor 底线。",
    )
    async def craftfloor(
        self,
        changed_elements: Annotated[str, "逗号分隔：排版/间距/布局/颜色/交互/状态/无障碍/文案/响应式"],
        satisfied: Annotated[str, "逗号分隔已满足的底线 id"] = "",
    ) -> dict:
        return Ok(
            evaluate_floor(
                changed_elements=tuple(
                    item.strip() for item in changed_elements.split(",") if item.strip()
                ),
                satisfied=tuple(
                    item.strip() for item in satisfied.split(",") if item.strip()
                ),
            )
        )

    # -- Hosted UI ------------------------------------------------------

    @ui.context(id="dashboard")
    async def dashboard_context(self) -> dict:
        """plugin.toml 里的 context = "dashboard" 由这里提供 props.state。"""
        return {
            "labels": {
                "title": "Flow Impeccable",
                "subtitle": "设计命令路由",
                "route_hint": "命中多个关键词时不猜：把候选都带回，只问一次；没命中则走 shape。",
                "commands_hint": "命令分组：setup / new / enhance / fix / iterate。",
                "floor_hint": "先选改动涉及的元素类别，再判定是否踩了底线；非空即阻断。",
                "plan_hint": "不要开放式自检循环：build → inspect → fix → confirm，最多 2 轮。",
            },
            "plugin_id": self.plugin_id,
        }
