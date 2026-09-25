"""Change 入口：在获得明确授权后，按所有权边界执行并验证一次简化。"""

from __future__ import annotations

import json
from typing import Any

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.errors import AuthorityError, ScopeError
from .._shared.proof import ProofRecord

REQUIRED_FIELDS = (
    "location",
    "burden",
    "consumers",
    "cut_boundary",
    "consequence",
    "verification",
    "net_complexity",
)

class ChangeRouter(PluginRouter):
    """授权修改。一次只处理一个所有权边界，完成并验证后才进入下一个。"""

    def __init__(self) -> None:
        super().__init__(name="change")

    @ui.action(id="plan_cut", label="Plan cut")
    @plugin_entry(
        id="plan_cut",
        name="规划一次删除",
        description="把一份证明记录补全并检查；缺字段时不进入执行。",
        input_schema={
            "type": "object",
            "properties": {
                "record": {"type": "object", "description": "证明记录"},
            },
            "required": ["record"],
        },
        llm_result_fields=["subject", "actionable", "missing_fields"],
    )
    async def plan_cut(self, record: Any, **_):
        if isinstance(record, str):
            record = json.loads(record)
        if not isinstance(record, dict):
            return Err(ScopeError("record must be a JSON object"))

        proof = ProofRecord(
            subject=str(record.get("subject", "")).strip(),
            location=str(record.get("location", "")),
            burden=str(record.get("burden", "")),
            consumers=record.get("consumers", {}) or {},
            cut_boundary=str(record.get("cut_boundary", "")),
            consequence=str(record.get("consequence", "")),
            verification=str(record.get("verification", "")),
            net_complexity=str(record.get("net_complexity", "")),
            confidence=str(record.get("confidence", "guess")),
            benefit=str(record.get("benefit", "medium")),
            verdict=str(record.get("verdict", "unresolved")),
            unresolved=list(record.get("unresolved", []) or []),
            notes=str(record.get("notes", "")),
        )
        missing = [name for name in REQUIRED_FIELDS if not getattr(proof, name, "")]
        return Ok(
            {
                "subject": proof.subject,
                "actionable": proof.is_actionable(),
                "missing_fields": missing,
                "record": proof.to_dict(),
                "next": (
                    "verify the surviving contract, then execute this one boundary"
                    if not missing
                    else "supply the missing fields before executing"
                ),
            }
        )

    @ui.action(id="apply_cut", label="Apply cut")
    @plugin_entry(
        id="apply_cut",
        name="执行已证明的删除",
        description="在明确授权下执行一次删除，并给出撤销路径。",
        input_schema={
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "record": {"type": "object", "description": "完整证明记录"},
                "authorize": {"type": "boolean", "description": "用户已明确授权此次改动"},
            },
            "required": ["root", "record", "authorize"],
        },
        llm_result_fields=["applied", "rollback", "boundary"],
    )
    async def apply_cut(self, root: str, record: Any, authorize: bool, **_):
        if not authorize:
            return Err(
                AuthorityError(
                    "this change needs explicit authorization; rerun with authorize=true"
                )
            )
        if isinstance(record, str):
            record = json.loads(record)
        if not isinstance(record, dict):
            return Err(ScopeError("record must be a JSON object"))

        proof = ProofRecord(
            subject=str(record.get("subject", "")).strip(),
            location=str(record.get("location", "")),
            burden=str(record.get("burden", "")),
            consumers=record.get("consumers", {}) or {},
            cut_boundary=str(record.get("cut_boundary", "")),
            consequence=str(record.get("consequence", "")),
            verification=str(record.get("verification", "")),
            net_complexity=str(record.get("net_complexity", "")),
            verdict=str(record.get("verdict", "unresolved")),
        )
        missing = [name for name in REQUIRED_FIELDS if not getattr(proof, name, "")]
        if missing:
            return Err(
                AuthorityError(
                    "refusing an unproved cut; missing " + ", ".join(missing)
                )
            )

        from .._shared.execute import execute_cut

        result = execute_cut(root, proof)
        return Ok(result.to_dict())

    @ui.action(id="verdict_guide", label="判断口径")
    @plugin_entry(
        id="verdict_guide",
        name="判断口径",
        description="列出保留、降级与不可判定的条件。",
        input_schema={"type": "object", "properties": {}},
    )
    async def verdict_guide(self, **_):
        return Ok(
            {
                "keep_when": [
                    "a real consumer exists",
                    "dynamic reachability remains unresolved",
                    "a current decision still owns the design",
                    "the change merely relocates complexity",
                    "the result is outside scope or retires no meaningful obligation",
                    "the available check cannot distinguish success from accidental breakage",
                ],
                "default": "keep rather than cut to produce a result",
            }
        )
