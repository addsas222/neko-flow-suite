"""分层布局（architecture / workflow / dataflow）。"""

from __future__ import annotations

from .errors import LayoutError
from .geometry import Box, Layout, PlacedNode
from .layout import (
    GAP_X,
    GAP_Y,
    NODE_H,
    NODE_W,
    PAD_X,
    PAD_Y,
    TITLE_H,
    grid,
)
from .routing import place_groups, route_edges
from .spec import Diagram


def layout_layered(diagram: Diagram) -> Layout:
    nodes = _place_layers(diagram)
    if not nodes:
        raise LayoutError("diagram has no nodes to lay out")

    max_layer = max(node.layer for node in nodes)
    by_layer: dict[int, list[PlacedNode]] = {}
    for node in nodes:
        by_layer.setdefault(node.layer, []).append(node)

    tallest = max(len(layer_nodes) for layer_nodes in by_layer.values())
    canvas_h = max(tallest * (NODE_H + GAP_Y) - GAP_Y, NODE_H)
    canvas_w = (max_layer + 1) * (NODE_W + GAP_X) - GAP_X

    for layer, layer_nodes in by_layer.items():
        block_h = len(layer_nodes) * (NODE_H + GAP_Y) - GAP_Y
        offset = (canvas_h - block_h) / 2.0
        for index, node in enumerate(layer_nodes):
            node.box = Box(
                x=PAD_X + layer * (NODE_W + GAP_X),
                y=PAD_Y + offset + index * (NODE_H + GAP_Y),
                w=NODE_W,
                h=NODE_H,
            )

    groups = place_groups(diagram, nodes)
    edges = route_edges(diagram, nodes)
    width = canvas_w + PAD_X * 2 + TITLE_H
    height = canvas_h + PAD_Y * 2 + TITLE_H
    if groups:
        width = max(width, max(g.box.x + g.box.w for g in groups) + PAD_X)

    return Layout(
        width=grid(width),
        height=grid(height),
        nodes=nodes,
        edges=edges,
        groups=groups,
        diagram_type=diagram.type,
    )


def _place_layers(diagram: Diagram) -> list[PlacedNode]:
    """按最长路径分配层；环上的回边被忽略以打破循环。"""
    ids = [node.id for node in diagram.nodes]
    index_of = {node_id: i for i, node_id in enumerate(ids)}
    successors: dict[str, list[str]] = {node_id: [] for node_id in ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in ids}

    for edge in diagram.edges:
        if edge.source in successors and edge.target in successors:
            successors[edge.source].append(edge.target)
            indegree[edge.target] += 1

    ready = [node_id for node_id in ids if indegree[node_id] == 0]
    order: list[str] = []
    while ready:
        ready.sort(key=lambda n: index_of[n])
        current = ready.pop(0)
        order.append(current)
        for nxt in successors[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    if len(order) < len(ids):
        seen = set(order)
        order.extend(node_id for node_id in ids if node_id not in seen)

    layer_of: dict[str, int] = {}
    for node_id in order:
        incoming = diagram.incoming(node_id)
        if not incoming:
            layer_of[node_id] = 0
        else:
            layer_of[node_id] = max(layer_of.get(edge.source, 0) for edge in incoming) + 1

    placed: list[PlacedNode] = []
    for node in diagram.nodes:
        placed.append(
            PlacedNode(
                id=node.id,
                box=Box(0.0, 0.0, NODE_W, NODE_H),
                label=node.label,
                kind=node.kind,
                group=node.group,
                detail=node.detail,
                primary=node.primary,
                tags=node.tags,
                layer=layer_of.get(node.id, 0),
            )
        )
    placed.sort(key=lambda n: (n.layer, index_of[n.id]))
    return placed
