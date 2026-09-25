"""几何检查：节点不重叠、边端点有效、标签有余量、边不穿过无关节点。"""

from __future__ import annotations

from .geometry import Box, Layout, Point
from .receipt import SEVERITY_ERROR, Issue, Receipt, record

LABEL_CLEARANCE = 8.0

def check_nodes_nonempty(placed: Layout, receipt: Receipt) -> None:
    record(
        receipt,
        "layout.nodes_nonempty",
        bool(placed.nodes),
        Issue(
            "LAYOUT_EMPTY",
            SEVERITY_ERROR,
            "diagram",
            "layout produced no nodes",
            ("add at least one node",),
        ),
    )

def check_no_node_overlap(placed: Layout, receipt: Receipt) -> None:
    collisions: list[str] = []
    for index, first in enumerate(placed.nodes):
        for second in placed.nodes[index + 1 :]:
            if first.box.intersects(second.box.inflate(-1.0)):
                collisions.append(f"{first.id}~{second.id}")
    record(
        receipt,
        "layout.no_node_overlap",
        not collisions,
        Issue(
            "LAYOUT_NODE_OVERLAP",
            SEVERITY_ERROR,
            ", ".join(collisions[:4]),
            "these node boxes overlap",
            ("shorten the affected branch", "split the layer", "remove one node"),
        ),
    )

def check_edges_endpoint(placed: Layout, receipt: Receipt) -> None:
    invalid = [
        edge.id
        for edge in placed.edges
        if placed.node_by_id(edge.source) is None
        or placed.node_by_id(edge.target) is None
        or len(edge.points) < 2
    ]
    record(
        receipt,
        "layout.edges_endpoint_valid",
        not invalid,
        Issue(
            "LAYOUT_EDGE_ENDPOINT",
            SEVERITY_ERROR,
            ", ".join(invalid[:4]),
            "these edges do not connect two placed nodes",
            ("declare both endpoints", "remove the edge"),
        ),
    )

def check_label_clearance(placed: Layout, receipt: Receipt) -> None:
    """关系标签不得压住另一条路由或节点。"""
    boxes: list[tuple[str, Box]] = []
    for edge in placed.edges:
        if edge.label and edge.label_at is not None:
            boxes.append(
                (
                    edge.id,
                    Box(
                        edge.label_at.x - LABEL_CLEARANCE,
                        edge.label_at.y - LABEL_CLEARANCE,
                        estimate_label_w(edge.label),
                        2 * LABEL_CLEARANCE + 6.0,
                    ),
                )
            )
    crowded: list[str] = []
    for index, (first_id, first_box) in enumerate(boxes):
        for second_id, second_box in boxes[index + 1 :]:
            if first_box.intersects(second_box) and first_id != second_id:
                crowded.append(f"{first_id}~{second_id}")
    for edge_id, box in boxes:
        for node in placed.nodes:
            if point_in(Point(box.x, box.y), node.box.inflate(-2.0)):
                crowded.append(f"{edge_id}~{node.id}")
    record(
        receipt,
        "layout.edge_label_clearance",
        not crowded,
        Issue(
            "LAYOUT_LABEL_CROWDED",
            SEVERITY_ERROR,
            ", ".join(sorted(set(crowded))[:4]),
            "a relationship label masks another route or a node",
            ("shorten the label", "drop the label", "apply one via control"),
        ),
    )

def check_no_node_crossing(placed: Layout, receipt: Receipt) -> None:
    """边不得穿过与它无关的不透明节点。"""
    crossings: list[str] = []
    for edge in placed.edges:
        endpoints = {edge.source, edge.target}
        for node in placed.nodes:
            if node.id in endpoints:
                continue
            if any(point_in(point, node.box.inflate(-2.0)) for point in edge.points):
                crossings.append(f"{edge.id}~{node.id}")
    record(
        receipt,
        "layout.edge_no_node_crossing",
        not crossings,
        Issue(
            "LAYOUT_EDGE_CROSSES_NODE",
            SEVERITY_ERROR,
            ", ".join(sorted(set(crossings))[:4]),
            "an edge crosses an unrelated node",
            ("add one via hop", "reroute by changing the branch", "split the layer"),
        ),
    )

def point_in(point: Point, box: Box) -> bool:
    return box.x <= point.x <= box.x + box.w and box.y <= point.y <= box.y + box.h

def estimate_label_w(label: str) -> float:
    width = 0.0
    for ch in label:
        width += 12.0 if ord(ch) > 0x2E80 else 6.6
    return min(width, 260.0)
