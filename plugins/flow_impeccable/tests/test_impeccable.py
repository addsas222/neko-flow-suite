"""flow_impeccable 共享层测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.commands import by_id, commands_in, ids, route
from _shared.craftfloor import evaluate
from _shared.passes import Verification, batch_targets, violates_bounded_policy


class TestCommands(unittest.TestCase):
    def test_ids_are_unique_and_cover_groups(self) -> None:
        found = ids()
        self.assertEqual(len(found), len(set(found)))
        for group in ("setup", "new", "enhance", "fix", "iterate"):
            self.assertTrue(commands_in(group), group)

    def test_explicit_command_wins(self) -> None:
        result = route("typeset the hero")
        self.assertEqual(result.command.id, "typeset")
        self.assertEqual(result.reference, "reference/typeset.md")

    def test_alias_teach_maps_to_init(self) -> None:
        self.assertEqual(by_id("teach").id, "init")
        self.assertEqual(by_id("craft").id, "shape")

    def test_keyword_routing(self) -> None:
        self.assertEqual(route("make my spacing tighter").command.id, "layout")
        self.assertEqual(route("diagnose the performance").command.id, "optimize")
        self.assertEqual(route("too much going on, calm it down").command.id, "quieter")

    def test_ambiguous_request_does_not_guess(self) -> None:
        result = route("redesign the layout and make it bolder")
        self.assertTrue(result.ambiguous_with)
        self.assertIn("也可能适用", result.reason)

    def test_unspecific_request_goes_to_shape(self) -> None:
        result = route("make it nicer")
        self.assertEqual(result.command.id, "shape")

    def test_unknown_command_raises(self) -> None:
        with self.assertRaises(KeyError):
            by_id("nope")

class TestPasses(unittest.TestCase):
    def test_first_pass_is_build(self) -> None:
        self.assertEqual(Verification().next_pass().name, "build")

    def test_one_confirm_round_then_stop(self) -> None:
        verification = Verification()
        verification.record_round(open_findings=["a"])
        self.assertEqual(verification.next_pass().name, "fix")
        verification.record_round(fixed=1)
        self.assertTrue(verification.must_stop)
        self.assertEqual(verification.verdict(), "stop")

    def test_clean_run_stops_after_one_round(self) -> None:
        verification = Verification()
        verification.record_round()
        self.assertEqual(verification.verdict(), "pass")
        self.assertEqual(verification.next_pass().name, "confirm")

    def test_batch_targets_include_both_viewports(self) -> None:
        self.assertEqual(batch_targets("web"), ("desktop", "mobile"))
        self.assertEqual(batch_targets("native"), ("phone", "tablet", "desktop"))

    def test_open_ended_self_qa_is_flagged(self) -> None:
        message = violates_bounded_policy(rounds=3, open_findings=2)
        self.assertIn("停止自检循环", message)
        self.assertIsNone(violates_bounded_policy(rounds=1, open_findings=2))

class TestCraftFloor(unittest.TestCase):
    def test_missing_floor_blocks(self) -> None:
        result = evaluate(changed_elements=("排版", "颜色"), satisfied=("text-scale",))
        self.assertFalse(result["ok"])
        self.assertIn("contrast", result["missing"])

    def test_satisfied_floor_passes(self) -> None:
        result = evaluate(
            changed_elements=("排版",), satisfied=("text-scale", "measure", "line-height")
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["directive"], "无阻断项。")

    def test_unrelated_changes_are_not_blocked(self) -> None:
        result = evaluate(changed_elements=("文案",), satisfied=("no-placeholder-copy",))
        self.assertTrue(result["ok"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
