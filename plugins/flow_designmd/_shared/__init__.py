"""flow_designmd 共享层：DESIGN.md 语料索引与导出。

来源：VoltAgent/awesome-design-md（MIT），见 ../SOURCE.md。
"""

from __future__ import annotations

from .catalog import (
    CATEGORIES_FILE,
    DEFAULT_CATEGORIES,
    Catalog,
    CatalogError,
    assign_categories,
    default_categories,
    scan,
)
from .emit import render_directory, to_css_variables, to_json_tokens, to_markdown_table
from .entry import TOKEN_GROUPS, DesignEntry, parse_design_md

__all__ = [
    "CATEGORIES_FILE",
    "DEFAULT_CATEGORIES",
    "TOKEN_GROUPS",
    "Catalog",
    "CatalogError",
    "DesignEntry",
    "assign_categories",
    "default_categories",
    "parse_design_md",
    "render_directory",
    "scan",
    "to_css_variables",
    "to_json_tokens",
    "to_markdown_table",
]
