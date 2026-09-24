"""规格入口：校验、诊断、交付。"""

from __future__ import annotations

import json
from typing import Any

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.artifacts import digest, list_specs, snapshot_spec, write_artifact
from .._shared.errors import SpecError
from .._shared.layout import layout
from .._shared.render import render_html
from .._shared.spec import Diagram, from_dict
from .._shared.validate import validate


class SpecRouter(PluginRouter):
    """把一份规格变成经过校验的自包含 HTML 产物。"""

    def __init__(self) -> None:
        super().__init__(name="specs")

    def _render_dir(self) -> Any:
        plugin = self.main_plugin
        directory = plugin.data_path("diagrams")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _prepare(self, spec: Any, *, quality: str = "showcase"):
        if isinstance(spec, str):
            spec = json.loads(spec)
        if not isinstance(spec, dict):
            raise SpecError("spec must be a JSON object")
        if quality in ("standard", "showcase"):
            meta = dict(spec.get("meta") or {})
            meta["quality_profile"] = quality
            spec = {**spec, "meta": meta}
        return from_dict(spec)

    @ui.action(id="validate_diagram", label="Validate")
    @plugin_entry(
        id="validate_diagram",
        name="校验图规格",
        description="运行全部工件检查，返回可行动的诊断与回执。",
        input_schema={
            "type": "object",
            "properties": {
                "spec": {"type": "object", "description": "图规格 JSON"},
                "quality": {"type": "string", "enum": ["standard", "showcase"], "default": "showcase"},
            },
            "required": ["spec"],
        },
        llm_result_fields=["ok", "error_count", "warning_count"],
    )
    async def validate_diagram(self, spec: Any, quality: str = "showcase", **_):
        diagram = self._prepare(spec, quality=quality)
        receipt = validate(diagram)
        return Ok(receipt.to_dict())

    @ui.action(id="deliver_diagram", label="Deliver")
    @plugin_entry(
        id="deliver_diagram",
        name="交付图产物",
        description="校验通过后冻结规格快照并渲染自包含 HTML 产物。",
        input_schema={
            "type": "object",
            "properties": {
                "spec": {"type": "object", "description": "图规格 JSON"},
                "name": {"type": "string", "description": "产物文件名主干"},
                "quality": {"type": "string", "enum": ["standard", "showcase"], "default": "showcase"},
            },
            "required": ["spec"],
        },
        llm_result_fields=["ok", "artifact_path", "spec_sha256", "artifact_sha256"],
    )
    async def deliver_diagram(self, spec: Any, name: str = "", quality: str = "showcase", **_):
        diagram = self._prepare(spec, quality=quality)
        receipt = validate(diagram)
        if not receipt.ok:
            return Err(
                SpecError(
                    "validation failed: "
                    + "; ".join(f"{issue.code} {issue.message}" for issue in receipt.errors)
                )
            )

        directory = self._render_dir()
        artifact_name = name or diagram.title or diagram.type
        snapshot = snapshot_spec(directory, artifact_name, diagram.to_dict())
        artifact_path = write_artifact(directory, artifact_name, render_html(diagram))
        artifact_bytes = artifact_path.read_bytes()

        return Ok(
            {
                "ok": True,
                "artifact_path": str(artifact_path),
                "artifact_name": artifact_path.name,
                "spec_path": str(snapshot),
                "artifact_bytes": len(artifact_bytes),
                "spec_bytes": receipt.spec_bytes,
                "spec_sha256": receipt.spec_sha256,
                "artifact_sha256": digest(artifact_bytes),
                "quality_profile": receipt.quality_profile,
                "checks_passed": receipt.passed,
            }
        )

    @ui.action(id="layout_report", label="Layout report")
    @plugin_entry(
        id="layout_report",
        name="布局诊断",
        description="返回稳定的编译器几何回执，用于定位几何冲突。",
        input_schema={
            "type": "object",
            "properties": {"spec": {"type": "object"}},
            "required": ["spec"],
        },
        llm_result_fields=["width", "height", "node_count", "edge_count"],
    )
    async def layout_report(self, spec: Any, **_):
        diagram = self._prepare(spec)
        placed = layout(diagram)
        report = placed.to_dict()
        report["node_count"] = len(placed.nodes)
        report["edge_count"] = len(placed.edges)
        return Ok(report)

    @ui.action(id="list_diagrams", label="Saved specs")
    @plugin_entry(
        id="list_diagrams",
        name="已保存规格",
        description="列出插件数据目录中已保存的图规格。",
        input_schema={"type": "object", "properties": {}},
    )
    async def list_diagrams(self, **_):
        return Ok({"specs": list_specs(self._render_dir())})
