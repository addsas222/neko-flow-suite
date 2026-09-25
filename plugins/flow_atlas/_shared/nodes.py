"""成员模型与构造器：Node / Edge / Group / Participant / Message。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import SpecError

DIAGRAM_TYPES: tuple[str, ...] = (
    "architecture",
    "workflow",
    "sequence",
    "dataflow",
    "lifecycle",
)
QUALITY_PROFILES: tuple[str, ...] = ("standard", "showcase")
EDGE_KINDS: tuple[str, ...] = ("flow", "async", "data", "reads", "writes", "guard", "rollback")

SCHEMA_VERSION = 2
MAX_PRIMARY_NODES = 12
MAX_CURATED_VIEWS = 5
MAX_NODES = 120
MAX_EDGES = 240
MAX_LABEL_CHARS = 96

_NODE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")
_ANIMATIONS = ("none", "trace")

@dataclass(slots=True)
class Node:
    """图中的主体。"""

    id: str
    label: str = ""
    kind: str = ""
    group: str = ""
    detail: str = ""
    primary: bool = False
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NODE_ID_RE.match(self.id):
            raise SpecError(f"invalid node id: {self.id!r}")
        self.label = (self.label or self.id).strip()[:MAX_LABEL_CHARS]
        self.detail = (self.detail or "").strip()[:400]
        if isinstance(self.tags, list):
            self.tags = tuple(str(t) for t in self.tags)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "group": self.group,
            "detail": self.detail,
            "primary": self.primary,
            "tags": list(self.tags),
        }

@dataclass(slots=True)
class Edge:
    """两个主体之间的关系。"""

    id: str
    source: str
    target: str
    label: str = ""
    kind: str = "flow"
    via: tuple[str, ...] = ()
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise SpecError(f"edge {self.id!r} needs both source and target")
        if self.source == self.target:
            raise SpecError(f"edge {self.id!r} is a self loop")
        self.label = (self.label or "").strip()[:MAX_LABEL_CHARS]
        self.detail = (self.detail or "").strip()[:400]
        if isinstance(self.via, list):
            self.via = tuple(str(v) for v in self.via)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "kind": self.kind,
            "via": list(self.via),
            "detail": self.detail,
        }

@dataclass(slots=True)
class Group:
    """分区块，把节点收进同一个语义容器。"""

    id: str
    label: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        self.label = (self.label or self.id).strip()[:MAX_LABEL_CHARS]
        self.detail = (self.detail or "").strip()[:400]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "detail": self.detail}

@dataclass(slots=True)
class Participant:
    """时序图的会话方。"""

    id: str
    label: str = ""

    def __post_init__(self) -> None:
        self.label = (self.label or self.id).strip()[:MAX_LABEL_CHARS]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label}

@dataclass(slots=True)
class Message:
    """时序图里的一条消息。"""

    source: str
    target: str
    text: str = ""
    kind: str = "sync"
    detail: str = ""

    def __post_init__(self) -> None:
        self.text = (self.text or "").strip()[:MAX_LABEL_CHARS]
        self.detail = (self.detail or "").strip()[:400]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "text": self.text,
            "kind": self.kind,
            "detail": self.detail,
        }

def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError("expected a JSON array")
    return value

def build_node(entry: Any) -> Node:
    if not isinstance(entry, dict):
        raise SpecError("each node must be a JSON object")
    node_id = entry.get("id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise SpecError("node.id is required")
    return Node(
        id=node_id.strip(),
        label=str(entry.get("label", "") or ""),
        kind=str(entry.get("kind", "") or ""),
        group=str(entry.get("group", "") or ""),
        detail=str(entry.get("detail", "") or ""),
        primary=bool(entry.get("primary", False)),
        tags=tuple(str(t) for t in _as_list(entry.get("tags"))),
    )

def build_edge(entry: Any) -> Edge:
    if not isinstance(entry, dict):
        raise SpecError("each edge must be a JSON object")
    source = entry.get("source") or entry.get("from")
    target = entry.get("target") or entry.get("to")
    if not isinstance(source, str) or not isinstance(target, str):
        raise SpecError("edge.source and edge.target are required strings")
    return Edge(
        id=str(entry.get("id") or f"{source}->{target}"),
        source=source.strip(),
        target=target.strip(),
        label=str(entry.get("label", "") or ""),
        kind=str(entry.get("kind", "flow") or "flow"),
        via=tuple(str(v) for v in _as_list(entry.get("via"))),
        detail=str(entry.get("detail", "") or ""),
    )

def build_group(entry: Any) -> Group:
    if not isinstance(entry, dict):
        raise SpecError("each group must be a JSON object")
    group_id = entry.get("id")
    if not isinstance(group_id, str) or not group_id.strip():
        raise SpecError("group.id is required")
    return Group(
        id=group_id.strip(),
        label=str(entry.get("label", "") or ""),
        detail=str(entry.get("detail", "") or ""),
    )

def build_participant(entry: Any) -> Participant:
    if not isinstance(entry, dict):
        raise SpecError("each participant must be a JSON object")
    pid = entry.get("id") or entry.get("label")
    if not isinstance(pid, str) or not pid.strip():
        raise SpecError("participant.id is required")
    return Participant(id=pid.strip(), label=str(entry.get("label", "") or ""))

def build_message(entry: Any) -> Message:
    if not isinstance(entry, dict):
        raise SpecError("each message must be a JSON object")
    source = entry.get("source") or entry.get("from")
    target = entry.get("target") or entry.get("to")
    if not isinstance(source, str) or not isinstance(target, str):
        raise SpecError("message.source and message.target are required strings")
    return Message(
        source=source.strip(),
        target=target.strip(),
        text=str(entry.get("text", "") or entry.get("label", "") or ""),
        kind=str(entry.get("kind", "sync") or "sync"),
        detail=str(entry.get("detail", "") or ""),
    )

def check_references(diagram: Any) -> None:
    """所有关系必须指向已声明的主体。"""
    known = set(diagram.node_map())
    participants = diagram.participant_ids()

    for edge in diagram.edges:
        for ref in (edge.source, edge.target):
            if ref not in known:
                raise SpecError(f"edge {edge.id!r} references undeclared subject {ref!r}")
        for hop in edge.via:
            if hop not in known:
                raise SpecError(f"edge {edge.id!r} routes through undeclared subject {hop!r}")

    for node in diagram.nodes:
        if node.group and node.group not in diagram.group_map():
            raise SpecError(f"node {node.id!r} belongs to undeclared group {node.group!r}")

    for message in diagram.messages:
        for ref in (message.source, message.target):
            if ref not in participants:
                raise SpecError(f"message {message.text!r} references undeclared participant {ref!r}")
