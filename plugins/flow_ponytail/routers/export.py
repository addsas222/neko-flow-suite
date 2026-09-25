"""导出入口：把方法论与强度设置交给外部编码 Agent。"""

from __future__ import annotations

from plugin.sdk.plugin import Ok, PluginRouter, plugin_entry, ui

from .._shared.intensity import LEVELS, describe, normalize_level
from .._shared.rules import HOST_ADAPTERS, agent_ruleset, ruleset_for_host


class ExportRouter(PluginRouter):
    """给 Cline / Claude Code / Codex 等外部宿主导出规则集。"""

    def __init__(self) -> None:
        super().__init__(name="export")

    @ui.action(id="ponytail_ruleset", label="Ruleset")
    @plugin_entry(
        id="ponytail_ruleset",
        name="导出规则集",
        description="导出可直接粘贴到外部 Agent 规则文件的紧凑规则文本。",
        input_schema={
            "type": "object",
            "properties": {"level": {"type": "string", "enum": list(LEVELS)}},
        },
        llm_result_fields=["level", "target", "rules"],
    )
    async def ponytail_ruleset(self, level: str = "full", **_):
        normalized = normalize_level(level)
        return Ok(
            {
                "level": normalized,
                "description": describe(normalized),
                "rules": agent_ruleset(normalized),
                "hosts": dict(HOST_ADAPTERS),
            }
        )

    @ui.action(id="ponytail_ruleset_for_host", label="Ruleset for host")
    @plugin_entry(
        id="ponytail_ruleset_for_host",
        name="按宿主导出",
        description="为指定外部宿主返回目标文件名与规则文本。",
        input_schema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "claude / cline / codex / cursor / ..."},
                "level": {"type": "string", "enum": list(LEVELS)},
            },
            "required": ["host"],
        },
        llm_result_fields=["host", "target"],
    )
    async def ponytail_ruleset_for_host(self, host: str, level: str = "full", **_):
        payload = ruleset_for_host(host, level)
        payload["description"] = describe(normalize_level(level))
        return Ok(payload)

    @ui.action(id="ponytail_intensity", label="Intensity")
    @plugin_entry(
        id="ponytail_intensity",
        name="强度等级",
        description="查看或归一化强度等级。",
        input_schema={
            "type": "object",
            "properties": {"level": {"type": "string"}},
        },
    )
    async def ponytail_intensity(self, level: str = "", **_):
        if level:
            return Ok({"requested": level, "normalized": normalize_level(level),
                       "description": describe(level)})
        return Ok(
            {
                "levels": [
                    {"level": name, "description": describe(name)} for name in LEVELS
                ],
                "note": "off 不是关闭安全护栏；护栏是基线，不是本插件的功能。",
            }
        )
