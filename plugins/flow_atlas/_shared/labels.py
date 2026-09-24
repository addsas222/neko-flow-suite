"""Hosted UI 文案 key 与上下文构造。"""

from __future__ import annotations

from plugin.sdk.plugin import tr

LABEL_KEYS: dict[str, str] = {
    "title": "atlas.title",
    "subtitle": "atlas.subtitle",
    "validate": "atlas.actions.validate",
    "deliver": "atlas.actions.deliver",
    "report": "atlas.actions.report",
    "mermaid": "atlas.actions.mermaid",
    "render": "atlas.actions.render",
    "list": "atlas.actions.list",
    "example": "atlas.actions.example",
    "spec": "atlas.fields.spec",
    "quality": "atlas.fields.quality",
    "name": "atlas.fields.name",
    "source": "atlas.fields.source",
}

DEFAULTS: dict[str, str] = {
    "title": "Workflow Atlas",
    "subtitle": "Write the spec, validate it, then deliver.",
    "validate": "Validate spec",
    "deliver": "Deliver artifact",
    "report": "Layout report",
    "mermaid": "Convert Mermaid",
    "render": "Render Mermaid",
    "list": "Saved specs",
    "example": "Example spec",
    "spec": "Diagram spec JSON",
    "quality": "Quality profile",
    "name": "Artifact name",
    "source": "Mermaid source",
}


def labels() -> dict[str, str]:
    """面板用到的本地文案。"""
    return {name: tr(key, default=DEFAULTS[name]) for name, key in LABEL_KEYS.items()}


def context(*, saved: list[dict], error: str = "") -> dict:
    """@ui.context(id="atlas") 的返回体，直接进入 props.state。"""
    return {
        "labels": labels(),
        "saved_specs": saved,
        "last_error": error,
        "stats": {"saved": len(saved)},
    }
