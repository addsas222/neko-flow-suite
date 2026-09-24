"""SVG 装配、语义视图按钮与运行时数据导出。"""

from __future__ import annotations

import json
from typing import Any

from .svg_shapes import arrow_defs, render_edge, render_group, render_lifelines, render_node
from .svg_style import attr, num, text


def render_body(diagram: Any, placed: Any) -> str:
    parts: list[str] = [
        f'<svg class="atlas-svg" viewBox="0 0 {num(placed.width)} {num(placed.height)}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{attr(diagram.title or diagram.type)}">',
        "<defs>",
        arrow_defs(),
        "</defs>",
        f'<rect class="atlas-bg" x="0" y="0" width="{num(placed.width)}" '
        f'height="{num(placed.height)}"></rect>',
    ]
    for group in placed.groups:
        parts.append(render_group(group))
    if placed.lanes and placed.diagram_type == "sequence":
        parts.append(render_lifelines(placed))
    for edge in placed.edges:
        parts.append(render_edge(edge))
    for node in placed.nodes:
        parts.append(render_node(node))
    parts.append("</svg>")
    return "\n".join(parts)


def render_views(diagram: Any) -> str:
    buttons: list[str] = []
    for view in diagram.views:
        if not isinstance(view, dict):
            continue
        buttons.append(
            f'<button class="atlas-view-btn" type="button" data-view="{attr(view.get("id", ""))}" '
            f'aria-pressed="false">{text(view.get("title", view.get("id", "")))}</button>'
        )
    if not buttons:
        return ""
    buttons.append(
        '<button class="atlas-view-btn" type="button" data-view="__all" '
        'aria-pressed="true">All</button>'
    )
    return "".join(buttons)


def export_payload(diagram: Any, placed: Any) -> str:
    """给运行时的稳定数据：含邻接关系，不含布局内部字段。"""
    payload = {
        "type": diagram.type,
        "title": diagram.title,
        "description": diagram.description,
        "quality_profile": diagram.quality_profile,
        "animation": diagram.animation,
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "kind": node.kind,
                "group": node.group,
                "detail": node.detail,
                "primary": node.primary,
                "tags": list(node.tags),
                "links": [e.target for e in placed.edges if e.source == node.id],
                "linked_from": [e.source for e in placed.edges if e.target == node.id],
            }
            for node in placed.nodes
        ],
    }
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
