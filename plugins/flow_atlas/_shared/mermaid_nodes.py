"""Mermaid 节点登记、标签提取与消息切分。"""

from __future__ import annotations

import re
from typing import Any

from .mermaid import _ARROW_SPLIT, _LABEL, _NODE_STATEMENT
from .nodes import MAX_LABEL_CHARS

_ID_OK = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")


def ensure(nodes: dict[str, dict[str, Any]], statement: str) -> None:
    """把一个 Mermaid 语句登记为节点，尽量取出显示标签。"""
    text = statement.strip().rstrip(";")
    if not text or text == "end":
        return
    match = _NODE_STATEMENT.match(text)
    if not match:
        return
    node_id, rest = match.group(1), match.group(2)
    shape = _LABEL.match(rest)
    label = ""
    if shape:
        label = next((g for g in shape.groups() if g is not None), "")
    if node_id in nodes:
        if label and not nodes[node_id]["label"]:
            nodes[node_id]["label"] = label[:MAX_LABEL_CHARS]
        return
    nodes[node_id] = {
        "id": node_id,
        "label": (label or node_id)[:MAX_LABEL_CHARS],
        "primary": True,
    }


def strip_label(statement: str) -> str:
    """取 -->|label| 形态的标签；没有就返回空串。"""
    match = re.search(r"\|([^|]*)\|", statement)
    return match.group(1).strip() if match else ""


def split_message(statement: str) -> tuple[str, str, str, str] | None:
    """把一条时序消息拆成 来源 / 箭头 / 目标 / 文本。

    先按箭头切分，再校验两侧是合法 ID；这样带连字符的 ID 不会被箭头吃掉。
    """
    match = _ARROW_SPLIT.search(statement)
    if match is None:
        return None
    left = statement[: match.start()].strip()
    arrow = match.group(1)
    right = statement[match.end():]
    if ":" not in right:
        return None
    target, _, text = right.partition(":")
    target = target.strip()
    if not left or not target:
        return None
    if not _ID_OK.match(left) or not _ID_OK.match(target):
        return None
    return left, arrow, target, text.strip()
