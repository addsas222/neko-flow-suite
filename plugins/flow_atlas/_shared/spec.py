"""类型化规格模型（Diagram）。

一张图由一份小而严格的 JSON 文档描述。渲染是确定性的：同一份规格永远
产出同一份产物字节。作者先写规格，再交给校验和布局，最后才交给渲染器。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import SpecError
from .nodes import (
    DIAGRAM_TYPES,
    MAX_CURATED_VIEWS,
    MAX_EDGES,
    MAX_NODES,
    QUALITY_PROFILES,
    SCHEMA_VERSION,
    Edge,
    Group,
    Message,
    Node,
    Participant,
    _ANIMATIONS,
    build_edge,
    build_group,
    build_message,
    build_node,
    build_participant,
    check_references,
)


@dataclass(slots=True)
class Diagram:
    """一份完整的图规格。"""

    type: str = "architecture"
    schema_version: int = SCHEMA_VERSION
    title: str = ""
    description: str = ""
    quality_profile: str = "showcase"
    animation: str = "none"
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    participants: list[Participant] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    views: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Any) -> Diagram:
        """把任意 JSON 值解析成 Diagram，失败时抛出 SpecError。"""
        if not isinstance(raw, dict):
            raise SpecError("diagram specification must be a JSON object")

        raw_type = str(raw.get("type", "architecture")).strip()
        if raw_type not in DIAGRAM_TYPES:
            raise SpecError(
                f"unknown diagram type {raw_type!r}; expected one of {', '.join(DIAGRAM_TYPES)}"
            )

        meta = raw.get("meta") or {}
        if not isinstance(meta, dict):
            raise SpecError("meta must be a JSON object")

        profile = str(meta.get("quality_profile", "showcase")).strip() or "showcase"
        if profile not in QUALITY_PROFILES:
            raise SpecError(
                f"unknown quality_profile {profile!r}; expected one of {', '.join(QUALITY_PROFILES)}"
            )

        animation = str(meta.get("animation", "none")).strip() or "none"
        if animation not in _ANIMATIONS:
            raise SpecError(
                f"unknown animation {animation!r}; expected one of {', '.join(_ANIMATIONS)}"
            )

        schema_version = raw.get("schema_version", SCHEMA_VERSION)
        if not isinstance(schema_version, int):
            raise SpecError("schema_version must be an integer")

        if len(_as_list(raw.get("nodes"))) > MAX_NODES:
            raise SpecError(f"a diagram holds at most {MAX_NODES} nodes")
        if len(_as_list(raw.get("edges"))) > MAX_EDGES:
            raise SpecError(f"a diagram holds at most {MAX_EDGES} edges")

        diagram = cls(
            type=raw_type,
            schema_version=schema_version,
            title=str(raw.get("title", "")).strip()[:96],
            description=str(raw.get("description", "")).strip()[:600],
            quality_profile=profile,
            animation=animation,
        )

        for entry in _as_list(raw.get("nodes")):
            diagram.nodes.append(build_node(entry))
        for entry in _as_list(raw.get("edges")):
            diagram.edges.append(build_edge(entry))
        for entry in _as_list(raw.get("groups")):
            diagram.groups.append(build_group(entry))
        for entry in _as_list(raw.get("participants")):
            diagram.participants.append(build_participant(entry))
        for entry in _as_list(raw.get("messages")):
            diagram.messages.append(build_message(entry))

        views = _as_list(meta.get("views"))
        if len(views) > MAX_CURATED_VIEWS:
            raise SpecError(f"meta.views holds at most {MAX_CURATED_VIEWS} curated chapters")
        diagram.views = [view for view in views if isinstance(view, dict)]

        check_references(diagram)
        return diagram

    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def group_map(self) -> dict[str, Group]:
        return {group.id: group for group in self.groups}

    def participant_map(self) -> dict[str, Participant]:
        return {participant.id: participant for participant in self.participants}

    def participant_ids(self) -> set[str]:
        return {participant.id for participant in self.participants}

    def primary_count(self) -> int:
        return sum(1 for node in self.nodes if node.primary)

    def outgoing(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges if edge.source == node_id]

    def incoming(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges if edge.target == node_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "schema_version": self.schema_version,
            "title": self.title,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "groups": [group.to_dict() for group in self.groups],
            "participants": [p.to_dict() for p in self.participants],
            "messages": [m.to_dict() for m in self.messages],
            "meta": {
                "quality_profile": self.quality_profile,
                "animation": self.animation,
                "views": list(self.views),
            },
        }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError("expected a JSON array")
    return value


def from_dict(raw: Any) -> Diagram:
    """见 Diagram.from_dict。"""
    return Diagram.from_dict(raw)
