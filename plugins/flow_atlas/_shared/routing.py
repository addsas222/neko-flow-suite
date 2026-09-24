"""自动正交路由与分组框计算。"""

from __future__ import annotations

from typing import Any

from .geometry import Box, PlacedGroup, PlacedNode, Point, RoutedEdge
from .layout import GROUP_LABEL_H, GROUP_PAD, values_close
from .spec import Diagram


def route_edges(diagram: Diagram, nodes: list[PlacedNode]) -> list[RoutedEdge]:
    """自动正交路由：相邻层直连，跨层走一次肘形折弯，远距离绕出节点上方。"""
    placed = {node.id: node for node in nodes}
    routed: list[RoutedEdge] = []

    for edge in diagram.edges:
        source = placed.get(edge.source)
        target = placed.get(edge.target)
        if source is None or target is None:
            continue

        path = edge_path(edge, source, target)
        label_at = None
        if edge.label and len(path) >= 2:
            mid = path[len(path) // 2]
            label_at = Point(mid.x + 8.0, mid.y - 10.0)

        routed.append(
            RoutedEdge(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                label=edge.label,
                kind=edge.kind,
                points=path,
                label_at=label_at,
                detail=edge.detail,
            )
        )
    return routed


def edge_path(edge: Any, source: PlacedNode, target: PlacedNode) -> list[Point]:
    delta = target.layer - source.layer
    if abs(delta) == 1:
        if delta > 0:
            start, end = source.right, target.left
        else:
            start, end = source.left, target.right
        if values_close(start.y, end.y, 1.0):
            return [start, end]
        mid_x = (start.x + end.x) / 2.0
        return [start, Point(mid_x, start.y), Point(mid_x, end.y), end]

    if delta > 0:
        start, end = source.top, target.top
    else:
        start, end = source.bottom, target.bottom
    mid_y = (start.y + end.y) / 2.0
    return [start, Point(start.x, mid_y), Point(end.x, mid_y), end]


def place_groups(diagram: Diagram, nodes: list[PlacedNode]) -> list[PlacedGroup]:
    placed: list[PlacedGroup] = []
    for group in diagram.groups:
        members = [node for node in nodes if node.group == group.id]
        if not members:
            continue
        x0 = min(node.box.x for node in members)
        y0 = min(node.box.y for node in members)
        x1 = max(node.box.x + node.box.w for node in members)
        y1 = max(node.box.y + node.box.h for node in members)
        placed.append(
            PlacedGroup(
                id=group.id,
                label=group.label,
                box=Box(
                    x0 - GROUP_PAD,
                    y0 - GROUP_PAD - GROUP_LABEL_H,
                    (x1 - x0) + GROUP_PAD * 2,
                    (y1 - y0) + GROUP_PAD * 2 + GROUP_LABEL_H,
                ),
            )
        )
    return placed
