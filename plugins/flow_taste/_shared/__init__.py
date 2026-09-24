"""flow_taste 共享层：brief 推断、三旋钮、设计系统映射、反默认规则、硬门。

纯 Python 标准库，不依赖 N.E.K.O 插件进程，可独立测试。

来源：Leonxlnx/taste-skill（MIT），见 ../SOURCE.md。
"""

from __future__ import annotations

from .brief import (
    ANTI_DEFAULTS,
    AUDIENCES,
    OVERRIDES,
    PAGE_KINDS,
    QUIET_CONSTRAINTS,
    VIBES,
    Brief,
    BriefAmbiguous,
    DesignRead,
    anti_default_report,
    infer,
)
from .dials import (
    BASELINE,
    DIAL_INFERENCE,
    DIAL_NAMES,
    USE_CASE_PRESETS,
    Dials,
    adjust_for_redesign,
    clamp,
    defaults_for,
    midpoint,
    motion_gates,
    motion_motivated,
    normalize,
)
from .gates import GATES, Gate, GateReport, GateResult, evaluate
from .lint import RULES, Report, Finding, lint, lint_css, lint_files, lint_html, rule_ids
from .rules_core import SEVERITY_BLOCK, SEVERITY_DEMOTE, SEVERITY_WARN
from .systems import AESTHETICS, REAL_SYSTEMS, SystemChoice, SystemDecision, choose

__all__ = [
    "ANTI_DEFAULTS",
    "AESTHETICS",
    "AUDIENCES",
    "BASELINE",
    "DIAL_INFERENCE",
    "DIAL_NAMES",
    "GATES",
    "OVERRIDES",
    "PAGE_KINDS",
    "QUIET_CONSTRAINTS",
    "REAL_SYSTEMS",
    "RULES",
    "SEVERITY_BLOCK",
    "SEVERITY_DEMOTE",
    "SEVERITY_WARN",
    "USE_CASE_PRESETS",
    "VIBES",
    "Brief",
    "BriefAmbiguous",
    "DesignRead",
    "Dials",
    "Finding",
    "Gate",
    "GateReport",
    "GateResult",
    "Report",
    "SystemChoice",
    "SystemDecision",
    "adjust_for_redesign",
    "anti_default_report",
    "choose",
    "clamp",
    "defaults_for",
    "evaluate",
    "infer",
    "lint",
    "lint_css",
    "lint_files",
    "lint_html",
    "midpoint",
    "motion_gates",
    "motion_motivated",
    "normalize",
    "rule_ids",
]
