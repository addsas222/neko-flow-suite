"""时序图布局：会话方作泳道头，消息按顺序自上而下排列。"""

from __future__ import annotations

from .errors import LayoutError
from .geometry import Box, Layout, PlacedNode, Point, RoutedEdge
from .layout import (
    GAP_X,
    NODE_H,
    NODE_W,
    PAD_X,
    PAD_Y,
    SEQUENCE_ROW_GAP,
    TITLE_H,
    grid,
)
from .spec import Diagram


def layout_sequence(diagram: Diagram) -> Layout:
    participants = diagram.participants
    if not participants:
        raise LayoutError("sequence diagram needs participants")
    if not diagram.messages:
        raise LayoutError("sequence diagram needs at least one message")

    nodes: list[PlacedNode] = []
    lanes: list[str] = []
    for index, participant in enumerate(participants):
        nodes.append(
            PlacedNode(
                id=participant.id,
                box=Box(PAD_X + index * (NODE_W + GAP_X), PAD_Y, NODE_W, NODE_H),
                label=participant.label,
                kind="actor",
                primary=True,
            )
        )
        lanes.append(participant.id)

    by_id = {node.id: node for node in nodes}
    first_row_y = PAD_Y + NODE_H + SEQUENCE_ROW_GAP
    edges: list[RoutedEdge] = []

    for order, message in enumerate(diagram.messages):
        source = by_id.get(message.source)
        target = by_id.get(message.target)
        if source is None or target is None:
            continue
        y = first_row_y + order * SEQUENCE_ROW_GAP
        start = Point(source.box.cx, y)
        end = Point(target.box.cx, y)
        if message.kind == "async":
            end = Point(target.box.cx - 9.0, y)
        label_at = Point(min(start.x, end.x) + abs(end.x - start.x) / 2.0, y - 10.0)
        edges.append(
            RoutedEdge(
                id=f"m{order}-{message.source}-{message.target}",
                source=message.source,
                target=message.target,
                label=message.text,
                kind=message.kind,
                points=[start, end],
                label_at=label_at,
                detail=message.detail,
            )
        )

    if not edges:
        raise LayoutError("no message referenced a declared participant")

    bottom = first_row_y + (len(edges) - 1) * SEQUENCE_ROW_GAP
    lifeline_bottom = bottom + SEQUENCE_ROW_GAP
    width = (len(participants)) * (NODE_W + GAP_X) - GAP_X + PAD_X * 2

    return Layout(
        width=grid(width),
        height=grid(lifeline_bottom + PAD_Y + TITLE_H),
        nodes=nodes,
        edges=edges,
        groups=[],
        lanes=lanes,
        diagram_type="sequence",
    )
