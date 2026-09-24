"""sequenceDiagram 与 stateDiagram 的 Mermaid 导入。"""

from __future__ import annotations

from typing import Any

from .errors import SpecError
from .errors import SpecError
from .mermaid import _SEQ_PARTICIPANT, _STATE_TRANSITION
from .mermaid_nodes import split_message
from .nodes import MAX_LABEL_CHARS
from typing import Any


def parse_sequence(lines: list[str], title: str, ensure: Any) -> dict[str, Any]:
    participants: list[dict[str, str]] = []
    seen: set[str] = set()
    messages: list[dict[str, Any]] = []

    for line in lines:
        statement = line.strip()
        declared = _SEQ_PARTICIPANT.match(statement)
        if declared:
            pid = declared.group(1)
            label = (declared.group(2) or pid).strip()
            if pid not in seen:
                seen.add(pid)
                participants.append({"id": pid, "label": label[:MAX_LABEL_CHARS]})
            continue
        parts = split_message(statement)
        if parts:
            source, arrow, target, text = parts
            for pid in (source, target):
                if pid not in seen:
                    seen.add(pid)
                    participants.append({"id": pid, "label": pid})
            messages.append(
                {
                    "source": source,
                    "target": target,
                    "text": text[:MAX_LABEL_CHARS],
                    "kind": "async" if "--" in arrow else "sync",
                }
            )

    if not participants:
        raise SpecError("sequenceDiagram declared no participants")
    return {
        "type": "sequence",
        "schema_version": 2,
        "title": title or "Mermaid sequence",
        "participants": participants,
        "messages": messages,
        "meta": {"quality_profile": "showcase"},
    }


def parse_states(lines: list[str], title: str, ensure: Any) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    for line in lines:
        statement = line.strip()
        if statement.startswith("[*]"):
            continue
        transition = _STATE_TRANSITION.match(statement)
        if transition:
            source, target, label = transition.groups()
            ensure(nodes, source)
            ensure(nodes, target)
            edges.append(
                {
                    "id": f"{source}->{target}",
                    "source": source,
                    "target": target,
                    "label": label.strip()[:MAX_LABEL_CHARS],
                    "kind": "guard",
                }
            )
            continue
        ensure(nodes, statement)

    if not nodes:
        raise SpecError("stateDiagram declared no states")
    return {
        "type": "lifecycle",
        "schema_version": 2,
        "title": title or "Mermaid state",
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {"quality_profile": "showcase"},
    }
