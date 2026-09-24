"""flow_huashu 的 N.E.K.O. 运行时入口。

规则层在 _shared/（纯标准库）；这里只做编排。
来源：alchaincyf/huashu-design（MIT），见本目录 SOURCE.md。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

try:
    from plugin.sdk.plugin import NekoPluginBase, Ok, Err, neko_plugin, plugin_entry
except ImportError:
    NekoPluginBase = object  # type: ignore[assignment,misc]
    Ok = lambda data: {"ok": True, "data": data}  # type: ignore[assignment]
    Err = lambda error: {"ok": False, "error": str(error)}  # type: ignore[assignment]
    neko_plugin = lambda cls: cls  # type: ignore[assignment]

    def plugin_entry(**kwargs):  # type: ignore[no-untyped-def]
        def wrap(func):  # type: ignore[no-untyped-def]
            func._plugin_entry = kwargs  # type: ignore[attr-defined]
            return func

        return wrap


_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _shared.facts import scan, verification_checklist  # noqa: E402
from _shared.gate import Direction, Gate, GateViolation  # noqa: E402
from _shared.roles import check_coverage, rotation_for  # noqa: E402
from _shared.routing import route as route_task  # noqa: E402


@neko_plugin
class FlowHuashuPlugin(NekoPluginBase):
    """三方向硬门 + 事实验证 + 工作室角色轮换。"""

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
