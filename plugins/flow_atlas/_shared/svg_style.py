"""SVG 样式映射与转义助手。"""

from __future__ import annotations

import html
from typing import Any

PALETTE: dict[str, dict[str, str]] = {
    "": {"fill": "var(--node-fill)", "stroke": "var(--node-stroke)", "accent": "var(--accent)"},
    "service": {"fill": "var(--node-fill)", "stroke": "var(--node-stroke)", "accent": "var(--accent)"},
    "store": {"fill": "var(--node-fill-alt)", "stroke": "var(--node-stroke-alt)",
              "accent": "var(--accent-alt)"},
    "gateway": {"fill": "var(--node-fill-alt)", "stroke": "var(--node-stroke-alt)",
                "accent": "var(--accent-alt)"},
    "external": {"fill": "var(--node-fill-alt)", "stroke": "var(--node-stroke-alt)",
                 "accent": "var(--muted-stroke)"},
    "actor": {"fill": "var(--node-fill-alt)", "stroke": "var(--node-stroke-alt)",
              "accent": "var(--accent-alt)"},
    "state": {"fill": "var(--node-fill)", "stroke": "var(--node-stroke)", "accent": "var(--accent)"},
    "job": {"fill": "var(--node-fill-alt)", "stroke": "var(--node-stroke-alt)",
            "accent": "var(--accent-alt)"},
}

KIND_MARK: dict[str, str] = {
    "store": "▤",
    "gateway": "⇄",
    "external": "◇",
    "actor": "☺",
    "state": "●",
    "job": "⚙",
}


def num(value: Any) -> str:
    """把坐标收成稳定的短十进制，避免产物字节抖动。"""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def attr(value: Any) -> str:
    return html.escape(str(value), quote=True)


def palette_for(kind: str) -> dict[str, str]:
    return PALETTE.get(kind, PALETTE[""])


def mark_for(kind: str) -> str:
    return KIND_MARK.get(kind, "")
