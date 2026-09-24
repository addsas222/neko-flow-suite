"""flow_designmd 共享层测试。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.catalog import CatalogError, assign_categories, scan
from _shared.emit import to_css_variables, to_json_tokens, to_markdown_table
from _shared.entry import TOKEN_GROUPS, parse_design_md

SAMPLE = """---
version: alpha
name: Claude-design-analysis
description: A warm-canvas editorial interface for Anthropic's Claude product.

colors:
  primary: "#cc785c"
  primary-active: "#a9583e"
  ink: "#141413"
  canvas: "#faf9f5"

typography:
  display-xl:
    fontFamily: "Copernicus, Tiempos Headline, serif"
    fontSize: 64px
    fontWeight: 400
---

# Claude Inspired Design System Analysis

Details moved to https://getdesign.md/claude/design-md
"""


class TestEntry(unittest.TestCase):
    def test_parses_front_matter(self) -> None:
        entry = parse_design_md(SAMPLE, slug="claude", source_path="/tmp/DESIGN.md")
        self.assertEqual(entry.slug, "claude")
        self.assertEqual(entry.name, "Claude-design-analysis")
        self.assertEqual(entry.version, "alpha")
        self.assertIn("warm-canvas", entry.description)

    def test_parses_token_groups(self) -> None:
        entry = parse_design_md(SAMPLE, slug="claude")
        self.assertEqual(entry.colors["primary"], "#cc785c")
        self.assertEqual(entry.colors["canvas"], "#faf9f5")
        self.assertEqual(entry.typography["display-xl-fontFamily"], "Copernicus, Tiempos Headline, serif")
        self.assertEqual(entry.typography["display-xl-fontSize"], "64px")

    def test_token_count(self) -> None:
        entry = parse_design_md(SAMPLE, slug="claude")
        # 4 colors + 4 typography leaves（display-xl 的 fontFamily/fontSize/fontWeight）
        self.assertGreaterEqual(entry.token_count, 7)

    def test_missing_front_matter_is_tolerated(self) -> None:
        entry = parse_design_md("# just a title\n", slug="broken")
        self.assertEqual(entry.slug, "broken")
        self.assertEqual(entry.token_count, 0)

    def test_all_token_groups_present(self) -> None:
        entry = parse_design_md(SAMPLE, slug="claude")
        for group in TOKEN_GROUPS:
            self.assertTrue(hasattr(entry, group), group)


class TestCatalog(unittest.TestCase):
    def _make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        for slug, name in (("claude", "Claude-design-analysis"), ("airbnb", "Airbnb")):
            directory = root / slug
            directory.mkdir(parents=True, exist_ok=True)
            body = SAMPLE.replace("Claude-design-analysis", name)
            (directory / "DESIGN.md").write_text(body, encoding="utf-8")
            (directory / "README.md").write_text("# readme\n", encoding="utf-8")
        return root

    def test_scan_finds_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = scan(self._make_root(tmp))
            self.assertEqual(len(catalog), 2)
            self.assertEqual(catalog.slugs(), ("airbnb", "claude"))

    def test_lookup_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = scan(self._make_root(tmp))
            self.assertEqual(catalog.lookup("Claude").slug, "claude")

    def test_lookup_unknown_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = scan(self._make_root(tmp))
            with self.assertRaises(KeyError):
                catalog.lookup("nope")

    def test_search_ranks_exact_slug_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = scan(self._make_root(tmp))
            self.assertEqual(catalog.search("claude")[0].slug, "claude")
            self.assertTrue(catalog.search("editorial interface"))

    def test_assign_categories_rebuckets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = scan(self._make_root(tmp))
            assign_categories(catalog, {"claude": "AI & LLM Platforms"})
            self.assertEqual(
                [entry.slug for entry in catalog.in_category("AI & LLM Platforms")], ["claude"]
            )

    def test_missing_root_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CatalogError):
                scan(Path(tmp) / "absent")

    def test_stats_counts_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stats = scan(self._make_root(tmp)).stats()
            self.assertEqual(stats["count"], 2)
            self.assertGreater(stats["tokens"], 0)


class TestEmit(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = parse_design_md(SAMPLE, slug="claude")

    def test_css_variables_are_scoped(self) -> None:
        css = to_css_variables(self.entry)
        self.assertIn(':root[data-design="claude"]', css)
        self.assertIn("--claude-colors-primary: #cc785c;", css)

    def test_json_tokens_grouped(self) -> None:
        tokens = to_json_tokens(self.entry)
        self.assertIn("colors", tokens)
        self.assertEqual(tokens["colors"]["primary"], "#cc785c")

    def test_markdown_table_lists_tokens(self) -> None:
        table = to_markdown_table(self.entry)
        self.assertIn("## colors", table)
        self.assertIn("| `primary` | `#cc785c` |", table)


if __name__ == "__main__":
    unittest.main(verbosity=2)
