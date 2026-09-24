"""生命周期 / 状态机布局：状态排在圆环上，迁移按角度取最短表达。"""

from __future__ import annotations

import math
from typing import Any

from .errors import LayoutError
from .geometry import Box, Layout, PlacedNode, Point, RoutedEdge
from .layout import (
    CYCLE_BULGE,
    CYCLE_RADIUS_MIN,
    NODE_H,
    NODE_W,
    PAD_X,
    PAD_Y,
    TITLE_H,
    grid,
)
from .nodes import Node
from .spec import Diagram


def layout_cycle(diagram: Diagram) -> Layout:
    states = list(diagram.nodes)
    if not states:
        states = [Node(id=p.id, label=p.label, kind="state") for p in diagram.participants]
    if not states:
        raise LayoutError("lifecycle diagram needs states or participants")

    count = len(states)
    radius = max(CYCLE_RADIUS_MIN, 34.0 * count / (2.0 * math.pi))
    center_x = radius + NODE_W / 2.0 + PAD_X
    center_y = radius + NODE_H / 2.0 + PAD_Y

    index_of: dict[str, int] = {}
    nodes: list[PlacedNode] = []
    for index, state in enumerate(states):
        index_of[state.id] = index
        angle = -math.pi / 2.0 + 2.0 * math.pi * index / count
        nodes.append(
            PlacedNode(
                id=state.id,
                box=Box(
                    center_x + radius * math.cos(angle) - NODE_W / 2.0,
                    center_y + radius * math.sin(angle) - NODE_H / 2.0,
                    NODE_W,
                    NODE_H,
                ),
                label=state.label,
                kind=state.kind or "state",
                group=state.group,
                detail=state.detail,
                primary=state.primary or index == 0,
                layer=index,
            )
        )

    placed = {node.id: node for node in nodes}
    edges: list[RoutedEdge] = []
    for order, edge in enumerate(diagram.edges):
        source = placed.get(edge.source)
        target = placed.get(edge.target)
        if source is None or target is None:
            continue
        path = _transition_path(edge, source, target, center_x, center_y, index_of)
        label_at = None
        if edge.label and path:
            mid = path[len(path) // 2]
            label_at = Point(mid.x, mid.y - 12.0)
        edges.append(
            RoutedEdge(
                id=edge.id or f"t{order}",
                source=edge.source,
                target=edge.target,
                label=edge.label,
                kind=edge.kind or "guard",
                points=path,
                label_at=label_at,
                detail=edge.detail,
            )
        )

    span_x = 2.0 * (radius + NODE_W / 2.0) + PAD_X * 2
    span_y = 2.0 * (radius + NODE_H / 2.0) + PAD_Y * 2
    return Layout(
        width=grid(span_x + TITLE_H),
        height=grid(span_y + TITLE_H),
        nodes=nodes,
        edges=edges,
        groups=[],
        diagram_type="lifecycle",
    )


def _transition_path(
    edge: Any,
    source: PlacedNode,
    target: PlacedNode,
    center_x: float,
    center_y: float,
    index_of: dict[str, int],
) -> list[Point]:
    """相邻状态走被顶起的外弦，跨状态迁移走近似直线。"""
    if abs(index_of.get(edge.source, 0) - index_of.get(edge.target, 0)) == 1:
        mid_x = (source.box.cx + target.box.cx) / 2.0
        mid_y = (source.box.cy + target.box.cy) / 2.0
        dx, dy = mid_x - center_x, mid_y - center_y
        norm = math.hypot(dx, dy) or 1.0
        return [
            source.right,
            Point(mid_x + dx / norm * CYCLE_BULGE, mid_y + dy / norm * CYCLE_BULGE),
            target.left,
        ]
    return [source.right, target.left]
