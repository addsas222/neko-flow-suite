"""flow_atlas 共享层测试：规格、Mermaid 导入、校验确定性。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import from_dict, layout, parse_mermaid, render_html, validate  # noqa: E402
from _shared.errors import SpecError  # noqa: E402

FLOW = """flowchart LR
  A[Start] --> B{Guard?}
  B -->|yes| C[Run]
  B -->|no| D[Skip]
  C --> E[End]
  D --> E
"""
SEQ = """sequenceDiagram
  participant U as User
  participant S as Server
  U->>S: invoke
  S-->>U: result
"""
STATE = """stateDiagram-v2
  [*] --> Draft
  Draft --> Review: submit
  Review --> Shipped: approve
"""


def test_flow_mermaid_parses_edges_and_labels() -> None:
    spec = parse_mermaid(FLOW)
    diagram = from_dict(spec)
    assert diagram.type == "workflow"
    assert len(diagram.nodes) == 5
    assert len(diagram.edges) == 5
    labels = {edge.label for edge in diagram.edges}
    assert "yes" in labels and "no" in labels


def test_sequence_mermaid_parses_participants() -> None:
    diagram = from_dict(parse_mermaid(SEQ))
    assert diagram.type == "sequence"
    assert [p.id for p in diagram.participants] == ["U", "S"]
    assert len(diagram.messages) == 2
    assert diagram.messages[0].text == "invoke"


def test_state_mermaid_maps_to_lifecycle() -> None:
    diagram = from_dict(parse_mermaid(STATE))
    assert diagram.type == "lifecycle"
    assert {n.id for n in diagram.nodes} == {"Draft", "Review", "Shipped"}


def test_render_is_deterministic() -> None:
    first = render_html(from_dict(parse_mermaid(FLOW)))
    second = render_html(from_dict(parse_mermaid(FLOW)))
    assert first == second
    assert "http://" not in first.replace("http://www.w3.org/2000/svg", "")


def test_artifact_is_self_contained() -> None:
    html = render_html(from_dict(parse_mermaid(FLOW)))
    assert "<svg" in html
    assert "atlas-canvas" in html
    assert "XMLSerializer" in html  # real export, not a stub


def test_dangling_reference_is_rejected() -> None:
    try:
        from_dict(
            {"type": "architecture", "nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "b"}]}
        )
    except SpecError as exc:
        assert "undeclared" in str(exc)
    else:  # pragma: no cover - the call above must raise
        raise AssertionError("dangling reference was accepted")


def test_primary_budget_is_enforced() -> None:
    spec = {
        "type": "architecture",
        "nodes": [{"id": f"n{i}", "primary": True} for i in range(13)],
        "edges": [{"source": f"n{i}", "target": f"n{i + 1}"} for i in range(12)],
        "meta": {"quality_profile": "showcase"},
    }
    receipt = validate(from_dict(spec))
    assert not receipt.ok
    assert any(issue.code == "SPEC_PRIMARY_BUDGET" for issue in receipt.errors)


def test_empty_source_is_rejected() -> None:
    for bad in ("", "   ", "flowchart TD", "just words"):
        try:
            parse_mermaid(bad)
        except SpecError:
            continue
        raise AssertionError(f"accepted invalid source: {bad!r}")


def test_layout_is_stable_for_the_same_spec() -> None:
    first = layout(from_dict(parse_mermaid(FLOW))).to_dict()
    second = layout(from_dict(parse_mermaid(FLOW))).to_dict()
    assert first == second


def test_bad_quality_profile_is_rejected() -> None:
    try:
        from_dict({"type": "architecture", "nodes": [{"id": "a"}], "meta": {"quality_profile": "x"}})
    except SpecError:
        return
    raise AssertionError("unknown quality profile was accepted")
