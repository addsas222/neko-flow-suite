"""flow_huashu 共享层测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.facts import must_verify, scan, verification_checklist
from _shared.gate import Direction, Gate, GateViolation
from _shared.roles import check_coverage, rotation_for
from _shared.routing import route as route_task


class TestRouting(unittest.TestCase):
    def test_new_visual_work_always_requires_the_gate(self) -> None:
        result = route_task("做个好看的页面")
        self.assertTrue(result.gate_required)
        self.assertTrue(any("三方向硬门" in entry for entry in result.entry_chain))

    def test_style_hint_does_not_exempt_the_gate(self) -> None:
        result = route_task("做个苹果宣传片风格的 30s 动画")
        self.assertTrue(result.gate_required)
        self.assertIn("launch film/品牌宣传片", result.hits)

    def test_brand_mention_chains_fact_verification(self) -> None:
        result = route_task("给 DJI 做发布动画")
        self.assertIn("提到具体品牌/产品名", result.hits)
        self.assertIn("product-facts.md", result.required_reading)

    def test_deck_routes_to_deck_chain(self) -> None:
        result = route_task("做个咖啡主题的 PPT")
        self.assertIn("幻灯片/PPT", result.hits)
        self.assertTrue(any("deck" in entry for entry in result.entry_chain))

    def test_no_signal_falls_back_to_standard_flow(self) -> None:
        result = route_task("整理一下目录结构")
        self.assertEqual(result.hits, ())
        self.assertEqual(result.entry_chain, ("标准流程",))

class TestGate(unittest.TestCase):
    def _directions(self) -> list[Direction]:
        return [
            Direction("深空暗场版", "暗场+产品色沉浸"),
            Direction("大白底衬线版", "编辑式排版+大留白"),
            Direction("玻璃质感版", "半透明层叠+高光描边"),
        ]

    def test_entering_production_without_choice_is_violation(self) -> None:
        gate = Gate()
        gate.open(style_hint="apple级")
        gate.offer(self._directions())
        with self.assertRaises(GateViolation):
            gate.enter_production()

    def test_two_directions_is_not_enough(self) -> None:
        gate = Gate()
        gate.open()
        with self.assertRaises(ValueError):
            gate.offer(self._directions()[:2])

    def test_choice_then_production_allowed(self) -> None:
        gate = Gate()
        gate.open()
        gate.offer(self._directions())
        gate.choose(1, rationale="和产品调性最贴")
        self.assertEqual(gate.enter_production().label, "大白底衬线版")
        self.assertEqual(gate.state, "chosen")

    def test_choosing_before_offering_fails(self) -> None:
        gate = Gate()
        gate.open()
        with self.assertRaises(GateViolation):
            gate.choose(0)

    def test_out_of_range_choice_fails(self) -> None:
        gate = Gate()
        gate.open()
        gate.offer(self._directions())
        with self.assertRaises(IndexError):
            gate.choose(9)

    def test_there_is_no_bypass(self) -> None:
        self.assertEqual(Gate().bypass_reason(), "")

class TestFacts(unittest.TestCase):
    def test_memory_based_claim_is_flagged(self) -> None:
        claims = scan("我记得 Nano Banana Pro 还没发布。")
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].needs_verification)

    def test_clean_sentence_passes(self) -> None:
        self.assertEqual(scan("按你给的尺寸排一个三栏布局。"), [])

    def test_version_claim_is_flagged(self) -> None:
        self.assertTrue(must_verify("这个 SDK 目前是 v2.3 版本"))

    def test_checklist_leads_with_search(self) -> None:
        checklist = verification_checklist("大疆 Pocket 4")
        self.assertIn("大疆 Pocket 4", checklist[0])
        self.assertIn("product-facts.md", checklist[-2])

class TestRoles(unittest.TestCase):
    def test_animation_leads_with_motion_designer(self) -> None:
        self.assertEqual(rotation_for("animation")[0].id, "motion-designer")

    def test_slide_leads_with_art_director(self) -> None:
        self.assertEqual(rotation_for("slide")[0].id, "art-director")

    def test_app_prototype_leads_with_frontend(self) -> None:
        self.assertEqual(rotation_for("app-prototype")[0].id, "frontend-engineer")

    def test_all_roles_required(self) -> None:
        result = check_coverage("web", ("visual-designer", "copywriter"))
        self.assertFalse(result["ok"])
        self.assertIn("art-director", result["missing"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
