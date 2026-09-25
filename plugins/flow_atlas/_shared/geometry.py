"""几何原语：坐标点、包围盒、已放置主体、已路由关系与布局结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Point:
    x: float
    y: float

@dataclass(slots=True)
class Box:
    """轴对齐包围盒。"""

    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def inflate(self, margin: float) -> Box:
        return Box(self.x - margin, self.y - margin, self.w + 2 * margin, self.h + 2 * margin)

    def intersects(self, other: Box) -> bool:
        return (
            self.x < other.x + other.w
            and other.x < self.x + self.w
            and self.y < other.y + other.h
            and other.y < self.y + self.h
        )

    def contains(self, point: Point) -> bool:
        return self.x <= point.x <= self.x + self.w and self.y <= point.y <= self.y + self.h

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

@dataclass(slots=True)
class PlacedNode:
    id: str
    box: Box
    label: str
    kind: str = ""
    group: str = ""
    detail: str = ""
    primary: bool = False
    tags: tuple[str, ...] = ()
    layer: int = 0

    @property
    def left(self) -> Point:
        return Point(self.box.x, self.box.cy)

    @property
    def right(self) -> Point:
        return Point(self.box.x + self.box.w, self.box.cy)

    @property
    def top(self) -> Point:
        return Point(self.box.cx, self.box.y)

    @property
    def bottom(self) -> Point:
        return Point(self.box.cx, self.box.y + self.box.h)

@dataclass(slots=True)
class RoutedEdge:
    id: str
    source: str
    target: str
    label: str = ""
    kind: str = "flow"
    points: list[Point] = field(default_factory=list)
    label_at: Point | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "kind": self.kind,
            "points": [{"x": p.x, "y": p.y} for p in self.points],
            "label_at": (
                {"x": self.label_at.x, "y": self.label_at.y} if self.label_at else None
            ),
            "detail": self.detail,
        }

@dataclass(slots=True)
class PlacedGroup:
    id: str
    label: str
    box: Box

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "box": self.box.to_dict()}

@dataclass(slots=True)
class Layout:
    """一次布局的全部几何结果。"""

    width: float
    height: float
    nodes: list[PlacedNode]
    edges: list[RoutedEdge]
    groups: list[PlacedGroup]
    lanes: list[str] = field(default_factory=list)
    diagram_type: str = "architecture"
    warnings: list[str] = field(default_factory=list)

    def node_by_id(self, node_id: str) -> PlacedNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagram_type": self.diagram_type,
            "width": self.width,
            "height": self.height,
            "nodes": [
                {**n.box.to_dict(), "id": n.id, "label": n.label, "kind": n.kind, "group": n.group}
                for n in self.nodes
            ],
            "groups": [g.to_dict() for g in self.groups],
            "edges": [e.to_dict() for e in self.edges],
            "lanes": list(self.lanes),
            "warnings": list(self.warnings),
        }
