"""Survey 入口：只读审计，交付覆盖范围、排序后的证明记录与盲区。"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.discovery import discover, record_from_finding
from .._shared.errors import ScopeError, SimplifyError
from .._shared.proof import ProofLedger


class SurveyRouter(PluginRouter):
    """只读审计。不写入目标仓库，不修改任何文件。"""

    def __init__(self) -> None:
        super().__init__(name="survey")
        self._ledger: ProofLedger | None = None
        self.last_report: dict = {}

    def _resolve_root(self, path: str) -> Any:
        from pathlib import Path

        candidate = (path or "").strip()
        if not candidate:
            raise ScopeError("a repository path is required")
        root = Path(candidate).expanduser()
        if not root.is_dir():
            raise ScopeError(f"repository path is not a directory: {root}")
        return root.resolve()

    @ui.action(id="audit_repo", label="Audit")
    @plugin_entry(
        id="audit_repo",
        name="只读审计仓库",
        description="返回覆盖范围、排序后的候选线索、盲区与下一步所需证据。不修改任何文件。",
        input_schema={
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "仓库绝对路径"},
                "mode": {"type": "string", "enum": ["survey"], "default": "survey"},
                "scope": {"type": "string", "enum": ["focused", "broad"], "default": "broad"},
            },
            "required": ["root"],
        },
        llm_result_fields=["mode", "scope", "files", "lines", "finding_count"],
    )
    async def audit_repo(self, root: str, mode: str = "survey", scope: str = "broad", **_):
        try:
            resolved = self._resolve_root(root)
        except ScopeError as exc:
            return Err(exc)

        try:
            discovery = discover(resolved, mode=mode, scope=scope)
        except SimplifyError as exc:
            return Err(exc)

        ledger = ProofLedger()
        for finding in discovery.findings:
            ledger.add(record_from_finding(finding))
        self._ledger = ledger

        report = discovery.to_dict()
        report["finding_count"] = len(discovery.findings)
        report["files"] = discovery.report.files if discovery.report else 0
        report["lines"] = discovery.report.lines if discovery.report else 0
        report["ledger"] = ledger.to_dict()
        self.last_report = report
        return Ok(report)

    @ui.action(id="audit_findings", label="Findings")
    @plugin_entry(
        id="audit_findings",
        name="查看证明记录",
        description="返回上一次审计的排序后证明记录与未决问题。",
        input_schema={"type": "object", "properties": {}},
    )
    async def audit_findings(self, **_):
        if self._ledger is None:
            return Ok({"records": [], "unresolved": [], "hint": "run audit_repo first"})
        return Ok(self._ledger.to_dict())

    @ui.action(id="audit_boundary", label="Boundaries")
    @plugin_entry(
        id="audit_boundary",
        name="边界与生命周期提醒",
        description="列出审计时必须谨慎对待的保护面，作为检查清单而不是省略理由。",
        input_schema={"type": "object", "properties": {}},
    )
    async def audit_boundary(self, **_):
        return Ok(
            {
                "protections": [
                    "authorization and trust-boundary validation",
                    "security isolation and input validation",
                    "data-loss prevention and stored-format compatibility",
                    "concurrency, cancellation, readiness and cleanup ownership",
                    "generated files, shared assets and consumers outside the repo",
                    "ADRs, RFCs and architecture constraints that still apply",
                ],
                "rule": (
                    "Removing a reachable capability, supported interface, stored "
                    "representation or compatibility path is a product decision. "
                    "Describe the consequence and obtain direction."
                ),
            }
        )
