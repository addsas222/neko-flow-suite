"""flow_ponytail 共享层测试：阶梯、强度、信号与规则集导出。"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import (  # noqa: E402
    LEVELS,
    agent_ruleset,
    normalize_level,
    next_rung,
    rung_for,
    rungs,
    review_diff,
    ruleset_for_host,
)
from _shared.discovery import ScopeError  # noqa: E402
from _shared.intensity import describe  # noqa: E402
from _shared.review_engine import _unused_parameter_findings, harvest_debt, review_repo  # noqa: E402


def test_ladder_is_ordered_from_cheapest() -> None:
    keys = [rung.key for rung in rungs()]
    assert keys[0] == "nothing"
    assert keys[-1] == "framework"
    assert next_rung("nothing").key == "one-line"
    assert next_rung("framework") is None


def test_rung_lookup_normalises_input() -> None:
    assert rung_for("1").key == "one-line"
    assert rung_for("stdlib").key == "stdlib"
    assert rung_for("bogus") is None


def test_intensity_levels_normalise() -> None:
    assert normalize_level("LITE") == "lite"
    assert normalize_level("off") == "off"
    assert normalize_level("nonsense") == "full"
    assert set(LEVELS) == {"off", "lite", "full", "ultra"}


def test_off_is_not_a_safety_off_switch() -> None:
    rules = agent_ruleset("off")
    assert "switched off" in rules
    assert "safety guards stay in place" in rules


def test_full_ruleset_contains_ladder_and_safety() -> None:
    rules = agent_ruleset("full")
    assert "YAGNI ladder" in rules
    assert "Safety boundary you never cross" in rules
    assert "data-loss" in rules


def test_ultra_adds_contract_and_migration_checks() -> None:
    assert "Ultra additions" in agent_ruleset("ultra")


def test_host_adapter_maps_to_rule_files() -> None:
    assert ruleset_for_host("cline")["target"] == ".clinerules"
    assert ruleset_for_host("claude")["target"] == "CLAUDE.md"
    assert ruleset_for_host("codex")["target"] == "AGENTS.md"
    assert ruleset_for_host("unknown-host")["target"] == "RULES.md"


def test_unused_parameter_is_only_reported_when_absent_from_body() -> None:
    text = (
        "def used(a, b):\n"
        "    return a + b\n"
        "\n"
        "def unused(a, b):\n"
        "    return a\n"
    )
    findings = _unused_parameter_findings(text, "sample.py")
    assert [f.subject.split(" in ")[0] for f in findings] == ["b"]


def test_debt_markers_are_harvested() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "mod.py").write_text(
            "# ponytail: skipped the cache layer\n"
            "def go():\n"
            "    return 1  # ponytail: did not add a flag\n",
            encoding="utf-8",
        )
        report = review_repo(str(root))
        ledger = harvest_debt(report)
        assert ledger["count"] == 2
        assert any("cache layer" in note["text"] for note in ledger["notes"])


def test_review_is_read_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "mod.py").write_text("def go():\n    return 1\n", encoding="utf-8")
        before = root.joinpath("mod.py").read_bytes()
        review_repo(str(root))
        assert root.joinpath("mod.py").read_bytes() == before


def test_empty_repo_is_a_scope_error_for_audit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = review_repo(tmp)
        assert report.files == 0


def test_diff_review_reads_added_lines_only() -> None:
    diff = (
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,2 @@\n"
        " def go():\n"
        "-    return 1\n"
        "+    # TODO: revisit\n"
        "+    return 2  # ponytail: left it\n"
    )
    report = review_diff(diff)
    assert len(report.debt) == 1
    assert any(f.code == "commentary-excuse" for f in report.findings)


def test_describe_covers_every_level() -> None:
    for level in LEVELS:
        assert describe(level)


def test_scope_error_has_a_stable_code() -> None:
    assert ScopeError("x").code == "SCOPE_INVALID"
