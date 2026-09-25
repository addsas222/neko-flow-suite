"""审查入口：diff 审查、仓库审计、债务台账与外部 Agent 规则集导出。"""

from __future__ import annotations

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.discovery import ScopeError
from .._shared.intensity import LEVELS, describe, normalize_level
from .._shared.ladder import next_rung, rung_for, rungs
from .._shared.review_engine import harvest_debt, review_diff, review_repo


class ReviewRouter(PluginRouter):
    """面向外部 Agent 的极简教练。"""

    def __init__(self) -> None:
        super().__init__(name="review")

    @ui.action(id="review_diff", label="Review diff")
    @plugin_entry(
        id="review_diff",
        name="审查 diff",
        description="审查一段 diff，返回过度设计信号与删除清单。",
        input_schema={
            "type": "object",
            "properties": {"diff": {"type": "string"}, "level": {"type": "string", "enum": list(LEVELS)}},
            "required": ["diff"],
        },
        llm_result_fields=["finding_count", "delete_list"],
    )
    async def review_diff(self, diff: str, level: str = "full", **_):
        normalized = normalize_level(level)
        if normalized == "off":
            return Ok(
                {
                    "level": normalized,
                    "findings": [],
                    "note": describe(normalized),
                }
            )
        report = review_diff(diff)
        return Ok(
            {
                "level": normalized,
                "target": report.target,
                "finding_count": len(report.findings),
                "findings": [f.to_dict() for f in report.findings],
                "delete_list": report.delete_list,
            }
        )

    @ui.action(id="audit_ponytail", label="Audit repo")
    @plugin_entry(
        id="audit_ponytail",
        name="审计仓库",
        description="对整个仓库做过度设计审计，只读。",
        input_schema={
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "level": {"type": "string", "enum": list(LEVELS)},
            },
            "required": ["root"],
        },
        llm_result_fields=["files", "finding_count", "debt_count"],
    )
    async def audit_ponytail(self, root: str, level: str = "full", **_):
        normalized = normalize_level(level)
        if normalized == "off":
            return Ok({"level": normalized, "findings": [], "note": describe(normalized)})
        report = review_repo(root)
        if not report.files:
            return Err(ScopeError(f"no Python source found under {root}"))
        return Ok(
            {
                "level": normalized,
                "target": report.target,
                "files": report.files,
                "finding_count": len(report.findings),
                "findings": [f.to_dict() for f in report.findings],
                "delete_list": report.delete_list,
                "debt": harvest_debt(report),
            }
        )

    @ui.action(id="ponytail_debt", label="Debt ledger")
    @plugin_entry(
        id="ponytail_debt",
        name="技术债台账",
        description="收割 ponytail: 标记，避免“以后再改”变成“永远不改”。",
        input_schema={
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
        llm_result_fields=["count"],
    )
    async def ponytail_debt(self, root: str, **_):
        report = review_repo(root)
        return Ok(harvest_debt(report))

    @ui.action(id="ponytail_ladder", label="YAGNI ladder")
    @plugin_entry(
        id="ponytail_ladder",
        name="YAGNI 阶梯",
        description="返回阶梯各级与下一级更贵的答案。",
        input_schema={
            "type": "object",
            "properties": {"rung": {"type": "string"}},
        },
    )
    async def ponytail_ladder(self, rung: str = "", **_):
        current = rung_for(rung) if rung else None
        nxt = next_rung(rung) if rung else None
        return Ok(
            {
                "rungs": [r.to_dict() for r in rungs()],
                "current": current.to_dict() if current else None,
                "next": nxt.to_dict() if nxt else None,
            }
        )
