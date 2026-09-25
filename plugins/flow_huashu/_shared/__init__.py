"""flow_huashu 共享层：任务路由、三方向硬门、事实验证、工作室角色。

来源：alchaincyf/huashu-design（MIT），见 ../SOURCE.md。
"""

from __future__ import annotations

from .facts import (
    BANNED_PATTERNS,
    SAFE_PATTERNS,
    TRIGGERS,
    Claim,
    must_verify,
    scan,
    verification_checklist,
)
from .gate import STYLE_SOURCES, Direction, Gate, GateViolation, style_hint_preserves_choice
from .roles import LEAD_BY_MEDIUM, ROLES, Role, check_coverage, rotation_for
from .routing import ENTRIES, Route
from .routing import route as route_task

__all__ = [
    "BANNED_PATTERNS",
    "ENTRIES",
    "LEAD_BY_MEDIUM",
    "ROLES",
    "SAFE_PATTERNS",
    "STYLE_SOURCES",
    "TRIGGERS",
    "Claim",
    "Direction",
    "Gate",
    "GateViolation",
    "Role",
    "Route",
    "check_coverage",
    "must_verify",
    "rotation_for",
    "route_task",
    "scan",
    "style_hint_preserves_choice",
    "verification_checklist",
]
