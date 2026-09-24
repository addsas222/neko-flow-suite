"""图库入口：示例规格与常见产品标识查询。

示例只提供字段形状，不提供事实；作者必须自己写稳定的 ID 和领域措辞。
"""

from __future__ import annotations

from plugin.sdk.plugin import Ok, PluginRouter, plugin_entry, ui

EXAMPLES: dict[str, dict] = {
    "architecture": {
        "type": "architecture",
        "schema_version": 2,
        "title": "Service topology",
        "description": "Replace every label with your own domain wording.",
        "nodes": [
            {"id": "edge", "label": "Edge", "kind": "gateway", "primary": True},
            {"id": "core", "label": "Core", "kind": "service", "primary": True},
            {"id": "store", "label": "Store", "kind": "store"},
            {"id": "vendor", "label": "Vendor", "kind": "external"},
        ],
        "edges": [
            {"id": "edge->core", "source": "edge", "target": "core", "label": "route"},
            {"id": "core->store", "source": "core", "target": "store", "kind": "reads"},
            {"id": "core->vendor", "source": "core", "target": "vendor", "kind": "async", "label": "sync"},
        ],
        "meta": {"quality_profile": "showcase"},
    },
    "workflow": {
        "type": "workflow",
        "schema_version": 2,
        "title": "Review workflow",
        "nodes": [
            {"id": "draft", "label": "Draft", "primary": True},
            {"id": "review", "label": "Review", "primary": True},
            {"id": "ship", "label": "Ship", "primary": True},
        ],
        "edges": [
            {"id": "draft->review", "source": "draft", "target": "review", "label": "submit"},
            {"id": "review->draft", "source": "review", "target": "draft", "label": "request changes"},
            {"id": "review->ship", "source": "review", "target": "ship", "label": "approve"},
        ],
        "meta": {"quality_profile": "showcase"},
    },
    "sequence": {
        "type": "sequence",
        "schema_version": 2,
        "title": "Request lifecycle",
        "participants": [
            {"id": "user", "label": "User"},
            {"id": "plugin", "label": "Plugin"},
            {"id": "core", "label": "Core"},
        ],
        "messages": [
            {"source": "user", "target": "plugin", "text": "invoke entry"},
            {"source": "plugin", "target": "core", "text": "ask for state"},
            {"source": "core", "target": "plugin", "text": "state snapshot", "kind": "async"},
        ],
        "meta": {"quality_profile": "showcase"},
    },
    "lifecycle": {
        "type": "lifecycle",
        "schema_version": 2,
        "title": "Run lifecycle",
        "nodes": [
            {"id": "queued", "label": "Queued"},
            {"id": "running", "label": "Running"},
            {"id": "done", "label": "Done"},
            {"id": "failed", "label": "Failed"},
        ],
        "edges": [
            {"id": "queued->running", "source": "queued", "target": "running", "label": "start"},
            {"id": "running->done", "source": "running", "target": "done", "label": "finish"},
            {"id": "running->failed", "source": "running", "target": "failed", "label": "raise"},
        ],
        "meta": {"quality_profile": "showcase"},
    },
}


class GalleryRouter(PluginRouter):
    """提供示例与创作提示，不修改用户数据。"""

    def __init__(self) -> None:
        super().__init__(name="gallery")

    @ui.action(id="diagram_types", label="Diagram types")
    @plugin_entry(
        id="diagram_types",
        name="支持的图种",
        description="列出支持的图种与对应的规格字段形状。",
        input_schema={"type": "object", "properties": {}},
    )
    async def diagram_types(self, **_):
        return Ok(
            {
                "types": ["architecture", "workflow", "sequence", "dataflow", "lifecycle"],
                "budgets": {
                    "max_primary_nodes": 12,
                    "max_curated_views": 5,
                    "max_nodes": 120,
                    "max_edges": 240,
                },
                "note": "Examples give field shape only. Invent your own stable IDs and wording.",
            }
        )

    @ui.action(id="example_spec", label="Example")
    @plugin_entry(
        id="example_spec",
        name="示例规格",
        description="取一种图种的示例规格，用于核对字段形状。",
        input_schema={
            "type": "object",
            "properties": {
                "diagram_type": {
                    "type": "string",
                    "enum": ["architecture", "workflow", "sequence", "lifecycle"],
                }
            },
            "required": ["diagram_type"],
        },
        llm_result_fields=["type", "title"],
    )
    async def example_spec(self, diagram_type: str, **_):
        example = EXAMPLES.get(diagram_type)
        if example is None:
            return Ok({"error": f"no example for {diagram_type!r}"})
        return Ok({"type": diagram_type, "title": example["title"], "spec": example})
