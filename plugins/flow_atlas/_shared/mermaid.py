"""Mermaid 导入：flowchart / graph、sequenceDiagram、stateDiagram-v2。

只覆盖三种最常用的输入形态；解析结果再走同一条校验与渲染流水线。
"""

from __future__ import annotations

import re
from typing import Any

from .errors import SpecError
from .nodes import MAX_LABEL_CHARS

_FLOW_HEAD = re.compile(r"^\s*(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)\s*$", re.I)
_SEQUENCE_HEAD = re.compile(r"^\s*sequenceDiagram\s*$", re.I)
_STATE_HEAD = re.compile(r"^\s*stateDiagram(?:-v2)?\s*$", re.I)
_SEQ_MESSAGE = re.compile(r"^\s*(\S+)\s*(-->>|->>|-->|-\.->|->|--)\s*(\S+)\s*:\s*(.*)$")
_ARROW_SPLIT = re.compile(r"(-->>|->>|-->|-\.->|->|--)")
_PIPE_LABEL = re.compile(r"\|([^|]*)\|")
_SEQ_PARTICIPANT = re.compile(
    r"^\s*(?:participant|actor)\s+([A-Za-z0-9_.-]+)(?:\s+as\s+(.+))?$", re.I
)
_STATE_TRANSITION = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*-->\s*([A-Za-z0-9_.-]+)\s*:\s*(.*)$")
_FLOW_EDGE = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\))?\s*"
    r"(-->|---|-\.->|==>)\s*(?:\|[^|]*\|)?\s*"
    r"([A-Za-z0-9_.-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\))?\s*$"
)
_NODE_STATEMENT = re.compile(r"^([A-Za-z0-9_.-]+)\s*(.*)$")
_LABEL = re.compile(r"^\s*(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|\(\(([^)]*)\)\))\s*$")

def parse_mermaid(source: str, *, title: str = "") -> dict[str, Any]:
    """把 Mermaid 源码解析成 flow_atlas 规格字典。"""
    if not isinstance(source, str) or not source.strip():
        raise SpecError("mermaid source is empty")

    lines = [
        line
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith("%%")
    ]
    if not lines:
        raise SpecError("mermaid source has no statements")

    head = lines[0]
    if _SEQUENCE_HEAD.match(head):
        from .mermaid_nodes import ensure
        from .mermaid_sequence import parse_sequence

        return parse_sequence(lines[1:], title, ensure)
    if _STATE_HEAD.match(head):
        from .mermaid_nodes import ensure
        from .mermaid_sequence import parse_states

        return parse_states(lines[1:], title, ensure)
    return parse_flow(lines, title)

def parse_flow(lines: list[str], title: str) -> dict[str, Any]:
    from .mermaid_nodes import ensure, strip_label

    if not _FLOW_HEAD.match(lines[0]):
        raise SpecError("first line must declare flowchart <dir> or graph <dir>")

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    for line in lines[1:]:
        statement = line.strip().rstrip(";")
        if statement.startswith("subgraph ") or statement in ("end", "}"):
            continue
        match = _FLOW_EDGE.match(statement)
        if match:
            source, arrow, target = match.group(1), match.group(2), match.group(3)
            label = strip_label(statement)
            ensure(nodes, source)
            ensure(nodes, target)
            edges.append(
                {
                    "id": f"{source}->{target}",
                    "source": source,
                    "target": target,
                    "label": label[:MAX_LABEL_CHARS],
                    "kind": "async" if arrow == "-.->" else "flow",
                }
            )
            continue
        ensure(nodes, statement)

    if not nodes:
        raise SpecError("flowchart declared no nodes")
    return {
        "type": "workflow",
        "schema_version": 2,
        "title": title or "Mermaid flowchart",
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {"quality_profile": "showcase"},
    }
