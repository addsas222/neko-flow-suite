"""语料目录：扫描 design-md/ 树，提供 lookup 与 search。

对应上游 VoltAgent/awesome-design-md 的 design-md/<slug>/DESIGN.md 布局。
套件只做索引与导出工具，不重分发 DESIGN.md 正文。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .entry import DesignEntry, parse_design_md

#: 上游 README 分类映射（由 tools/build_categories.py 生成）。
CATEGORIES_FILE = Path(__file__).resolve().parents[1] / "data" / "categories.json"

#: 分类映射缺失时的兜底分类。
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "AI & LLM Platforms",
    "Developer Tools",
    "Design & Creative",
    "Automotive",
    "Crypto & Fintech",
    "Enterprise",
    "Consumer",
)


def default_categories() -> dict[str, str]:
    """读取随插件发布的分类映射。"""
    if not CATEGORIES_FILE.is_file():
        return {}
    try:
        return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


class CatalogError(Exception):
    pass


@dataclass(slots=True)
class Catalog:
    root: Path
    entries: dict[str, DesignEntry] = field(default_factory=dict)
    categories: dict[str, list[str]] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.entries)

    def slugs(self) -> tuple[str, ...]:
        return tuple(sorted(self.entries))

    def lookup(self, slug: str) -> DesignEntry:
        wanted = slug.strip().lower()
        if wanted in self.entries:
            return self.entries[wanted]
        for entry in self.entries.values():
            if entry.name.lower() == wanted or entry.slug == wanted:
                return entry
        raise KeyError(f"no DESIGN.md for {slug!r}")

    def search(self, term: str) -> list[DesignEntry]:
        needle = term.strip().lower()
        if not needle:
            return list(self.entries.values())
        scored: list[tuple[int, DesignEntry]] = []
        for entry in self.entries.values():
            haystack = entry.search_text()
            score = haystack.count(needle)
            if entry.slug == needle or entry.name.lower() == needle:
                score += 50
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1].slug))
        return [entry for _, entry in scored]

    def in_category(self, category: str) -> list[DesignEntry]:
        return [self.entries[slug] for slug in self.categories.get(category, [])]

    def stats(self) -> dict[str, object]:
        return {
            "count": len(self.entries),
            "categories": {name: len(slugs) for name, slugs in self.categories.items()},
            "tokens": sum(entry.token_count for entry in self.entries.values()),
        }


def scan(root: str | Path, *, categorise: bool = True) -> Catalog:
    """扫描 design-md/<slug>/DESIGN.md。"""
    base = Path(root)
    if not base.is_dir():
        raise CatalogError(f"design-md root not found: {base}")

    catalog = Catalog(root=base)
    for directory in sorted(base.iterdir()):
        if not directory.is_dir():
            continue
        design_md = directory / "DESIGN.md"
        if not design_md.is_file():
            continue
        text = design_md.read_text(encoding="utf-8", errors="replace")
        entry = parse_design_md(text, slug=directory.name, source_path=str(design_md))
        catalog.entries[entry.slug] = entry
        catalog.categories.setdefault(entry.category, []).append(entry.slug)

    if not catalog.entries:
        raise CatalogError(f"no DESIGN.md found under {base}")

    if categorise:
        assign_categories(catalog, default_categories())
    return catalog


def assign_categories(catalog: Catalog, mapping: dict[str, str]) -> None:
    """按 slug → 分类覆盖默认归类。"""
    catalog.categories = {}
    for slug, category in mapping.items():
        if slug in catalog.entries:
            catalog.entries[slug].category = category
            catalog.categories.setdefault(category, []).append(slug)
    for slug, entry in catalog.entries.items():
        if slug not in mapping:
            catalog.categories.setdefault(entry.category, []).append(slug)
