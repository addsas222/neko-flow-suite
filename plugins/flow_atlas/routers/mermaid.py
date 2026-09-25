"""Mermaid 入口：把 Mermaid 源码转成规格，再走同一条校验与交付流水线。"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.artifacts import digest, snapshot_spec, write_artifact
from .._shared.errors import SpecError
from .._shared.mermaid import parse_mermaid
from .._shared.render import render_html
from .._shared.spec import from_dict
from .._shared.validate import validate


class MermaidRouter(PluginRouter):
    """粘贴一段 Mermaid，得到一份规格或一份产物。"""

    def __init__(self) -> None:
        super().__init__(name="mermaid")

    def _render_dir(self) -> Any:
        directory = self.main_plugin.data_path("diagrams")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @ui.action(id="convert_mermaid", label="Convert")
    @plugin_entry(
        id="convert_mermaid",
        name="转换 Mermaid",
        description="把 Mermaid flowchart / sequenceDiagram / stateDiagram 转成图规格。",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Mermaid 源码"},
                "title": {"type": "string", "description": "图标题"},
            },
            "required": ["source"],
        },
        llm_result_fields=["type", "title", "node_count", "edge_count"],
    )
    async def convert_mermaid(self, source: str, title: str = "", **_):
        try:
            spec = parse_mermaid(source, title=title)
        except SpecError as exc:
            return Err(exc)
        diagram = from_dict(spec)
        return Ok(
            {
                "spec": diagram.to_dict(),
                "type": diagram.type,
                "title": diagram.title,
                "node_count": len(diagram.nodes),
                "edge_count": len(diagram.edges),
                "participant_count": len(diagram.participants),
                "message_count": len(diagram.messages),
            }
        )

    @ui.action(id="render_mermaid", label="Render")
    @plugin_entry(
        id="render_mermaid",
        name="渲染 Mermaid",
        description="转换并直接交付自包含 HTML 产物；校验失败时不写任何文件。",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "name": {"type": "string", "description": "产物文件名主干"},
                "title": {"type": "string"},
            },
            "required": ["source"],
        },
        llm_result_fields=["ok", "artifact_path", "spec_sha256"],
    )
    async def render_mermaid(self, source: str, name: str = "", title: str = "", **_):
        try:
            spec = parse_mermaid(source, title=title)
        except SpecError as exc:
            return Err(exc)

        diagram = from_dict(spec)
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
        snapshot_spec(directory, artifact_name, diagram.to_dict())
        artifact_path = write_artifact(directory, artifact_name, render_html(diagram))
        artifact_bytes = artifact_path.read_bytes()
        return Ok(
            {
                "ok": True,
                "artifact_path": str(artifact_path),
                "artifact_name": artifact_path.name,
                "artifact_bytes": len(artifact_bytes),
                "spec_sha256": receipt.spec_sha256,
                "artifact_sha256": digest(artifact_bytes),
            }
        )
