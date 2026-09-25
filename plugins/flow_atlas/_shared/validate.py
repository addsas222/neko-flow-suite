"""校验入口：运行全部工件检查并产出回执。

诊断回答"这条边该改哪个字段"，回执回答"这份规格是什么字节"。两者不混谈：
诊断是可行动的，回执是确定性的。
"""

from __future__ import annotations

import json

from .errors import AtlasError
from .layout import layout
from .receipt import SEVERITY_ERROR, Issue, Receipt, digest, record
from .spec import Diagram
from .validate_checks import (
    check_edges_endpoint,
    check_label_clearance,
    check_no_node_crossing,
    check_no_node_overlap,
    check_nodes_nonempty,
    check_primary_budget,
    check_references,
    check_type,
    check_views_budget,
)

# showcase 验收要求全部通过的工件检查。
ARTIFACT_CHECKS: tuple[str, ...] = (
    "spec.type",
    "spec.references",
    "spec.primary_budget",
    "spec.views_budget",
    "layout.nodes_nonempty",
    "layout.no_node_overlap",
    "layout.edges_endpoint_valid",
    "layout.edge_label_clearance",
    "layout.edge_no_node_crossing",
)

__all__ = [
    "ARTIFACT_CHECKS",
    "Issue",
    "Receipt",
    "record",
    "validate",
]

def validate(diagram: Diagram, *, wants_showcase: bool = True) -> Receipt:
    """运行工件检查。默认按 showcase 判定。"""
    receipt = Receipt(
        ok=False,
        diagram_type=diagram.type,
        quality_profile=diagram.quality_profile,
    )
    payload = json.dumps(diagram.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    receipt.spec_sha256, receipt.spec_bytes = digest(payload)

    check_type(diagram, receipt)
    check_references(diagram, receipt)
    check_primary_budget(diagram, receipt)
    check_views_budget(diagram, receipt)

    try:
        placed = layout(diagram)
    except AtlasError as exc:
        record(
            receipt,
            "layout.nodes_nonempty",
            False,
            Issue(
                code=exc.code,
                severity=SEVERITY_ERROR,
                subject="diagram",
                message=str(exc),
                supported_fixes=("add at least one node", "fix the reported subject"),
            ),
        )
        for name in ARTIFACT_CHECKS:
            if name not in receipt.passed and name not in receipt.failed:
                receipt.failed.append(name)
        return receipt

    check_nodes_nonempty(placed, receipt)
    check_no_node_overlap(placed, receipt)
    check_edges_endpoint(placed, receipt)
    check_label_clearance(placed, receipt)
    check_no_node_crossing(placed, receipt)

    is_showcase = wants_showcase and diagram.quality_profile == "showcase"
    all_passed = set(receipt.passed) == set(ARTIFACT_CHECKS)
    receipt.ok = (not receipt.errors) and (all_passed if is_showcase else True)
    return receipt
