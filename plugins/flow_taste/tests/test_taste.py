"""flow_taste 共享层测试。纯标准库，可直接 python -m unittest 运行。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.brief import Brief, BriefAmbiguous, DesignRead, anti_default_report, infer
from _shared.dials import (
    Dials,
    adjust_for_redesign,
    clamp,
    defaults_for,
    motion_gates,
    motion_motivated,
    normalize,
)
from _shared.gates import GATES, evaluate
from _shared.lint import lint, rule_ids
from _shared.systems import choose


class TestBrief(unittest.TestCase):
    def test_infer_produces_one_line_read(self) -> None:
        read = infer(Brief(page_kind="landing-saas", audience="b2b-buyer", vibe="linear-style"))
        self.assertIsInstance(read, DesignRead)
        self.assertIn("Reading this as: landing-saas for b2b-buyer", read.render())
        self.assertIn("linear-style language", read.render())

    def test_ambiguous_brief_asks_exactly_one_question(self) -> None:
        with self.assertRaises(BriefAmbiguous) as ctx:
            infer(Brief())
        self.assertIn("Linear-clean", ctx.exception.question)
        self.assertEqual(ctx.exception.question.count("?"), 1)

    def test_quiet_constraint_overrides_vibe(self) -> None:
        read = infer(
            Brief(
                page_kind="landing-saas",
                audience="general-public",
                vibe="awwwards",
                constraints=("public-sector",),
            )
        )
        self.assertEqual(read.vibe, "trust-first")
        self.assertEqual(read.constraints, ("public-sector",))

    def test_anti_default_report_mentions_gradients(self) -> None:
        read = infer(Brief(page_kind="editorial", vibe="minimalist"))
        self.assertTrue(any("gradient" in item for item in anti_default_report(read)))

    def test_public_sector_family_is_official(self) -> None:
        read = infer(
            Brief(
                page_kind="landing-saas",
                audience="procurement",
                vibe="serious-b2b",
                constraints=("public-sector",),
            )
        )
        self.assertIn("govuk-frontend", read.family)


class TestDials(unittest.TestCase):
    def test_baseline_is_8_6_4(self) -> None:
        self.assertEqual(str(Dials()), "8 / 6 / 4")

    def test_vibe_range_clamps_preset(self) -> None:
        dials = defaults_for("minimalist", "landing-saas")
        self.assertEqual(dials.variance, 6)
        self.assertEqual(dials.motion, 4)
        self.assertEqual(dials.density, 3)

    def test_playful_gets_high_motion(self) -> None:
        self.assertGreaterEqual(defaults_for("awwwards", "landing-agency").motion, 8)

    def test_clamp_keeps_range(self) -> None:
        self.assertEqual(clamp(0), 1)
        self.assertEqual(clamp(99), 10)
        self.assertEqual(normalize(Dials(0, 99, 4)), Dials(1, 10, 4))

    def test_motion_gates_track_dial(self) -> None:
        self.assertFalse(motion_gates(Dials(8, 4, 4))["page_must_actually_move"])
        self.assertTrue(motion_gates(Dials(8, 7, 4))["perpetual_micro_interactions"])
        self.assertFalse(motion_motivated(Dials(8, 4, 4)))
        self.assertTrue(motion_motivated(Dials(8, 5, 4)))

    def test_redesign_modes(self) -> None:
        base = Dials(5, 4, 3)
        self.assertEqual(adjust_for_redesign(base, "preserve").motion, 5)
        self.assertEqual(adjust_for_redesign(base, "preserve").variance, 5)
        self.assertEqual(adjust_for_redesign(base, "overhaul").variance, 7)
        self.assertEqual(adjust_for_redesign(base, "overhaul").motion, 6)


class TestLint(unittest.TestCase):
    def test_h_screen_blocks(self) -> None:
        report = lint('<div className="h-screen">x</div>')
        self.assertEqual(report.verdict(), "blocked")
        self.assertIn("h-screen-hero", [f.rule_id for f in report.findings])

    def test_fraunces_blocks(self) -> None:
        report = lint("font-family: Fraunces, serif;")
        self.assertTrue(report.blocked)
        self.assertIn("serif-fraunces-default", [f.rule_id for f in report.findings])

    def test_clean_snippet_passes(self) -> None:
        report = lint('<div className="min-h-[100dvh] max-w-[1400px] mx-auto">ok</div>')
        self.assertEqual(report.verdict(), "clean")

    def test_purple_gradient_warns_with_line_numbers(self) -> None:
        report = lint('class="bg-gradient-to-r from-purple-500 to-indigo-600"')
        self.assertEqual(report.verdict(), "warn")
        finding = report.findings[0]
        self.assertEqual(finding.line, 1)
        self.assertGreaterEqual(finding.column, 1)
        self.assertTrue(finding.fix)

    def test_lorem_blocks(self) -> None:
        self.assertTrue(lint("<p>Lorem ipsum dolor</p>").blocked)

    def test_rule_ids_are_unique(self) -> None:
        ids = rule_ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 10)


class TestGates(unittest.TestCase):
    def test_everything_declared_passes(self) -> None:
        declared = {gate.id: True for gate in GATES}
        declared["page_moves"] = True
        declared["motion_reasons"] = True
        report = evaluate(design_read="Reading this as: x", dials=Dials(), declared=declared)
        self.assertTrue(report.ok, report.to_dict())

    def test_missing_declarations_block(self) -> None:
        report = evaluate(design_read="", dials=Dials())
        self.assertFalse(report.ok)
        self.assertIn("design-read-declared", [r.gate_id for r in report.failed])

    def test_static_page_allowed_at_low_motion(self) -> None:
        declared = {gate.id: True for gate in GATES}
        report = evaluate(
            design_read="read",
            dials=Dials(5, 4, 2),
            declared={**declared, "page_moves": False},
        )
        self.assertTrue(report.ok, report.to_dict())

    def test_high_motion_without_actual_movement_blocks(self) -> None:
        declared = {gate.id: True for gate in GATES}
        report = evaluate(
            design_read="read",
            dials=Dials(8, 7, 4),
            declared={**declared, "page_moves": False},
        )
        self.assertIn("motion-claims-match", [r.gate_id for r in report.failed])


class TestSystems(unittest.TestCase):
    def test_public_sector_picks_official(self) -> None:
        decision = choose("US public-sector / trust-first")
        self.assertEqual(decision.kind, "official")
        self.assertEqual(decision.name, "uswds")

    def test_aesthetic_is_honest(self) -> None:
        decision = choose("Brutalism")
        self.assertEqual(decision.kind, "aesthetic")
        self.assertIn("原生 CSS", decision.directive)

    def test_unknown_signal_falls_back_honestly(self) -> None:
        self.assertIn("借用", choose("something nobody catalogued").directive)


if __name__ == "__main__":
    unittest.main(verbosity=2)
