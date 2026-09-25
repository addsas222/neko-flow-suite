"""单个 SVG 图元的渲染。"""

from __future__ import annotations

from typing import Any

from .svg_style import attr, mark_for, num, palette_for, text

ARROW_DEF = (
    '<marker id="atlas-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
    'markerHeight="7" orient="auto-start-reverse">'
    '<path class="atlas-arrow-head" d="M0,0 L10,5 L0,10 z"></path></marker>'
)

def arrow_defs() -> str:
    return ARROW_DEF

def render_group(group: Any) -> str:
    return (
        f'<g class="atlas-group" data-group="{attr(group.id)}">'
        f'<rect x="{num(group.box.x)}" y="{num(group.box.y)}" rx="16" '
        f'width="{num(group.box.w)}" height="{num(group.box.h)}"></rect>'
        f'<text class="atlas-group-label" x="{num(group.box.x + 12)}" '
        f'y="{num(group.box.y + 18)}">{text(group.label or group.id)}</text></g>'
    )

def render_lifelines(placed: Any) -> str:
    parts = ['<g class="atlas-lifelines">']
    for node in placed.nodes:
        parts.append(
            f'<line x1="{num(node.box.cx)}" y1="{num(node.box.y + 56.0)}" '
            f'x2="{num(node.box.cx)}" y2="{num(placed.height - 40.0)}"></line>'
        )
    parts.append("</g>")
    return "".join(parts)

def render_edge(edge: Any) -> str:
    if len(edge.points) < 2:
        return ""
    d = path_of(edge.points)
    dashes = ' stroke-dasharray="6 5"' if edge.kind == "async" else ""
    label = ""
    if edge.label and edge.label_at is not None:
        label = (
            f'<text class="atlas-edge-label" x="{num(edge.label_at.x)}" '
            f'y="{num(edge.label_at.y)}">{text(edge.label)}</text>'
        )
    return (
        f'<g class="atlas-edge" data-edge="{attr(edge.id)}" data-kind="{attr(edge.kind)}">'
        f'<path class="atlas-edge-hit" d="{d}"></path>'
        f'<path class="atlas-edge-line{dashes}" d="{d}" marker-end="url(#atlas-arrow)"></path>'
        f"{label}</g>"
    )

def path_of(points: Any) -> str:
    commands = [f"M {num(points[0].x)} {num(points[0].y)}"]
    for point in points[1:]:
        commands.append(f"L {num(point.x)} {num(point.y)}")
    return " ".join(commands)

def render_node(node: Any) -> str:
    style = palette_for(node.kind)
    mark = mark_for(node.kind)
    accent = ""
    if mark:
        accent = (
            f'<text class="atlas-node-mark" x="{num(node.box.x + 12)}" '
            f'y="{num(node.box.y + 24)}">{text(mark)}</text>'
        )
    return (
        f'<g class="atlas-node" data-node="{attr(node.id)}" data-kind="{attr(node.kind)}" '
        f'data-tags="{attr(",".join(node.tags))}" data-group="{attr(node.group)}" '
        f'data-primary="{1 if node.primary else 0}" data-detail="{attr(node.detail)}" '
        f'tabindex="0" role="button">'
        f'<rect class="atlas-node-shape" x="{num(node.box.x)}" y="{num(node.box.y)}" rx="12" '
        f'width="{num(node.box.w)}" height="{num(node.box.h)}" fill="{style["fill"]}" '
        f'stroke="{style["stroke"]}"></rect>'
        f'<line class="atlas-node-accent" x1="{num(node.box.x)}" y1="{num(node.box.y + 8)}" '
        f'x2="{num(node.box.x)}" y2="{num(node.box.y + node.box.h - 8)}" '
        f'stroke="{style["accent"]}"></line>'
        f"{accent}"
        f'<text class="atlas-node-label" x="{num(node.box.x + 34)}" '
        f'y="{num(node.box.y + 32)}">{text(node.label)}</text>'
        f'<text class="atlas-node-kind" x="{num(node.box.x + 34)}" '
        f'y="{num(node.box.y + 48)}">{text(node.kind or node.id)}</text>'
        f"</g>"
    )
