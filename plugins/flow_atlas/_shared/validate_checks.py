"""规格检查：图种、引用完整性、主节点预算与视图预算。"""

from __future__ import annotations

from .layout_checks import (
    check_edges_endpoint,
    check_label_clearance,
    check_no_node_crossing,
    check_no_node_overlap,
    check_nodes_nonempty,
)
from .receipt import SEVERITY_ERROR, Issue, Receipt, record
from .nodes import MAX_CURATED_VIEWS, MAX_PRIMARY_NODES
from .spec import Diagram

DIAGRAM_TYPES_OK = ("architecture", "workflow", "sequence", "dataflow", "lifecycle")


def check_type(diagram: Diagram, receipt: Receipt) -> None:
    record(
        receipt,
        "spec.type",
        diagram.type in DIAGRAM_TYPES_OK,
        Issue(
            "SPEC_TYPE",
            SEVERITY_ERROR,
            "type",
            f"unsupported diagram type {diagram.type!r}",
            ("choose a supported diagram type",),
        ),
    )


def check_references(diagram: Diagram, receipt: Receipt) -> None:
    known = set(diagram.node_map()) | diagram.participant_ids()
    dangling = [
        edge.id
        for edge in diagram.edges
        if edge.source not in known or edge.target not in known
    ]
    record(
        receipt,
        "spec.references",
        not dangling,
        Issue(
            "SPEC_DANGLING",
            SEVERITY_ERROR,
            ", ".join(sorted(dangling)),
            "these edges reference undeclared subjects",
            ("declare the missing node or participant", "remove the edge"),
        ),
    )


def check_primary_budget(diagram: Diagram, receipt: Receipt) -> None:
    over = diagram.primary_count() - MAX_PRIMARY_NODES
    record(
        receipt,
        "spec.primary_budget",
        over <= 0,
        Issue(
            "SPEC_PRIMARY_BUDGET",
            SEVERITY_ERROR,
            f"{diagram.primary_count()} primary nodes",
            f"a diagram keeps at most {MAX_PRIMARY_NODES} primary nodes",
            ("mark fewer nodes primary", "split into two diagrams"),
        ),
    )


def check_views_budget(diagram: Diagram, receipt: Receipt) -> None:
    over = len(diagram.views) - MAX_CURATED_VIEWS
    record(
        receipt,
        "spec.views_budget",
        over <= 0,
        Issue(
            "SPEC_VIEWS_BUDGET",
            SEVERITY_ERROR,
            f"{len(diagram.views)} views",
            f"meta.views keeps at most {MAX_CURATED_VIEWS} curated chapters",
            ("drop the least useful chapter",),
        ),
    )


__all__ = [
    "DIAGRAM_TYPES_OK",
    "check_edges_endpoint",
    "check_label_clearance",
    "check_no_node_crossing",
    "check_no_node_overlap",
    "check_nodes_nonempty",
    "check_primary_budget",
    "check_references",
    "check_type",
    "check_views_budget",
]
