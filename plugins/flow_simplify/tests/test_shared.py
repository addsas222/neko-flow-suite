"""flow_simplify 共享层测试：只读发现、证明记录、授权门。"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import discover  # noqa: E402
from _shared.errors import ScopeError  # noqa: E402
from _shared.execute import execute_cut  # noqa: E402
from _shared.proof import ProofLedger, ProofRecord  # noqa: E402


def _write_tree(root: Path) -> None:
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "used.py").write_text(
        "def kept():\n    return 1\n\n\ndef call_it():\n    return kept()\n", encoding="utf-8"
    )
    (root / "pkg" / "orphan.py").write_text(
        "def only_defined_here():\n    return 2\n", encoding="utf-8"
    )
    (root / "pkg" / "orphan.pyc").write_bytes(b"\x00")

def test_scan_is_read_only_and_finds_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_tree(root)
        before = sorted(p.name for p in root.rglob("*"))

        discovery = discover(root, mode="survey", scope="broad")

        after = sorted(p.name for p in root.rglob("*"))
        assert before == after
        assert discovery.report is not None
        assert discovery.report.files == 2
        assert discovery.report.skipped == 0
        subjects = {finding.candidate for finding in discovery.findings}
        assert "only_defined_here" in subjects
        assert "kept" not in subjects

def test_blind_spots_are_recorded_not_omitted() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        discovery = discover(Path(tmp))
        assert discovery.report is not None
        assert "no Python source found in scope" in discovery.report.blind_spots
        assert any("persisted" in spot for spot in discovery.report.blind_spots)

def test_missing_directory_is_a_scope_error() -> None:
    try:
        discover(Path("E:/definitely-not-a-real-directory-xyz"))
    except ScopeError:
        return
    raise AssertionError("missing directory was not rejected")

def test_proof_record_needs_every_field_to_be_actionable() -> None:
    record = ProofRecord(subject="x")
    assert not record.is_actionable()
    for name in (
        "location",
        "burden",
        "consumers",
        "cut_boundary",
        "consequence",
        "verification",
        "net_complexity",
    ):
        setattr(record, name, "set")
    assert record.is_actionable()

def test_ledger_ranks_confidence_above_benefit() -> None:
    ledger = ProofLedger()
    proved = ProofRecord(subject="proved", confidence="proved", benefit="low")
    guessed = ProofRecord(subject="guessed", confidence="guess", benefit="high")
    for name in (
        "location",
        "burden",
        "consumers",
        "cut_boundary",
        "consequence",
        "verification",
        "net_complexity",
    ):
        setattr(proved, name, "set")
        setattr(guessed, name, "set")
    ledger.add(guessed)
    ledger.add(proved)
    assert [r.subject for r in ledger.ranked()] == ["proved", "guessed"]

def test_unproved_cut_is_refused() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_tree(root)
        result = execute_cut(str(root), ProofRecord(subject="x", location="pkg/orphan.py"))
        assert not result.applied
        assert (root / "pkg" / "orphan.py").exists()

def test_proved_cut_moves_to_quarantine_and_reports_rollback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_tree(root)
        record = ProofRecord(
            subject="orphan",
            location="pkg/orphan.py",
            burden="unused helper",
            consumers={"production": [], "test": []},
            cut_boundary="pkg/orphan.py",
            consequence="none observed",
            verification="pytest pkg",
            net_complexity="removes one obligation",
        )
        result = execute_cut(str(root), record)
        assert result.applied
        assert not (root / "pkg" / "orphan.py").exists()
        assert "back to" in result.rollback
        assert result.warnings

def test_execute_cut_refuses_paths_outside_the_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outside = Path(tmp).parent / "outside.py"
        outside.write_text("x = 1\n", encoding="utf-8")
        try:
            record = ProofRecord(
                subject="escape",
                location=str(outside),
                burden="b",
                consumers={},
                cut_boundary="c",
                consequence="d",
                verification="e",
                net_complexity="f",
            )
            result = execute_cut(str(root), record)
            assert not result.applied
        finally:
            outside.unlink(missing_ok=True)
