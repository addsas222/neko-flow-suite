"""flow_huashu 的 N.E.K.O. 运行时入口。

规则层在 _shared/（纯标准库）；这里只做编排。
来源：alchaincyf/huashu-design（MIT），见本目录 SOURCE.md。
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

from ._shared.facts import scan, verification_checklist  # noqa: E402
from ._shared.gate import Direction, Gate, GateViolation  # noqa: E402
from ._shared.roles import check_coverage, rotation_for  # noqa: E402
from ._shared.routing import route as route_task  # noqa: E402


@neko_plugin
class FlowHuashuPlugin(NekoPluginBase):
    """三方向硬门 + 事实验证 + 工作室角色轮换。"""

    @ui.action(id="route", label="任务路由")
    @plugin_entry(
        id="route",
        name="任务路由",
        description="扫任务路由表，叠加出入口链；命中新视觉设计必然要求三方向硬门。",
    )
    async def route(
        self,
        task: Annotated[str, "用户原始任务描述"],
    ) -> dict:
        try:
            return Ok(route_task(task).to_dict())
        except Exception as exc:  # noqa: BLE001
            return Err(str(exc))

    @ui.action(id="gate", label="三方向硬门")
    @plugin_entry(
        id="gate",
        name="三方向硬门",
        description="登记三个方向、等用户选定；未选定就进入执行会被拒绝。",
    )
    async def gate(
        self,
        directions: Annotated[str, "逗号分隔的方向标签，至少 3 个"],
        chosen: Annotated[int, "用户选定的索引；-1 表示尚未选定"] = -1,
        style_hint: Annotated[str, "风格词；不豁免选择权"] = "",
        brand_named: Annotated[bool, "是否点了品牌名"] = False,
    ) -> dict:
        gate = Gate()
        gate.open(style_hint=style_hint, brand_named=brand_named)
        try:
            parsed = [
                Direction(label=label.strip(), hypothesis="")
                for label in directions.split(",")
                if label.strip()
            ]
            gate.offer(parsed)
        except ValueError as exc:
            return Err(str(exc))

        if chosen >= 0:
            try:
                gate.choose(chosen)
            except (GateViolation, IndexError) as exc:
                return Err(str(exc))

        payload = gate.to_dict()
        try:
            payload["selected"] = gate.enter_production().label
        except GateViolation as exc:
            payload["blocked"] = str(exc)
        return Ok(payload)

    @ui.action(id="facts", label="事实验证")
    @plugin_entry(
        id="facts",
        name="事实验证",
        description="扫文案里的未经验证事实断言，并给出开工前检索清单。",
    )
    async def facts(
        self,
        text: Annotated[str, "要检查的文案或断言"],
        subject: Annotated[str, "待检索的主体，如 大疆 Pocket 4"] = "",
    ) -> dict:
        claims = scan(text)
        return Ok(
            {
                "claims": [claim.to_dict() for claim in claims],
                "must_verify": bool(claims),
                "checklist": verification_checklist(subject) if subject else [],
            }
        )

    @ui.action(id="roles", label="工作室角色")
    @plugin_entry(id="roles", name="工作室角色", description="按媒介给出角色轮换顺序与覆盖检查。")
    async def roles(
        self,
        medium: Annotated[str, "web / slide / animation / app-prototype / infographic"] = "web",
        roles_done: Annotated[str, "逗号分隔已完成的角色 id"] = "",
    ) -> dict:
        return Ok(
            {
                "rotation": [
                    {"id": role.id, "name": role.name, "owns": role.owns,
                     "failure_mode": role.failure_mode}
                    for role in rotation_for(medium)
                ],
                "coverage": check_coverage(
                    medium,
                    tuple(item.strip() for item in roles_done.split(",") if item.strip()),
                ),
            }
        )

    # -- Hosted UI ------------------------------------------------------

    @ui.context(id="dashboard")
    async def dashboard_context(self) -> dict:
        """plugin.toml 里的 context = "dashboard" 由这里提供 props.state。"""
        return {
            "labels": {
                "title": "Flow Huashu",
                "subtitle": "三方向硬门",
                "route_hint": "先扫路由表，多信号按行序叠加入口链，而不是二选一。",
                "gate_hint": "指定风格/品牌不豁免：必须出三个差异化方向，等用户选定才能进入执行。",
                "facts_hint": "涉及具体产品/技术的断言，先检索再写，禁止凭训练语料断言。",
            },
            "plugin_id": self.plugin_id,
        }
