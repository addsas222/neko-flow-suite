"""把 DESIGN.md token 导出成可消费形态。

下游是「给 coding agent 一份能直接用的 CSS 自定义属性块」或「一份 token
清单」，所以这里只做机械转换，不改变上游 token 语义。
"""

from __future__ import annotations

from .entry import TOKEN_GROUPS, DesignEntry


def _kebab(name: str) -> str:
    return name.strip().lower().replace("_", "-").replace(" ", "-")


def to_css_variables(entry: DesignEntry, *, prefix: str = "") -> str:
    """导出 CSS 自定义属性块。prefix 为空时用 slug 作用域。"""
    scope = _kebab(prefix or entry.slug)
    lines = [f":root[data-design=\"{scope}\"] {{"]
    for group in TOKEN_GROUPS:
        values = getattr(entry, group)
        for key, value in values.items():
            lines.append(f"  --{scope}-{_kebab(group)}-{_kebab(key)}: {value};")
    lines.append("}")
    return "\n".join(lines)


def to_json_tokens(entry: DesignEntry) -> dict[str, dict[str, str]]:
    return {group: dict(getattr(entry, group)) for group in TOKEN_GROUPS}


def to_markdown_table(entry: DesignEntry) -> str:
    """上游形态：一份 token 清单表格。"""
    lines = [f"# {entry.name}", "", entry.description, ""]
    for group in TOKEN_GROUPS:
        values = getattr(entry, group)
        if not values:
            continue
        lines += [f"## {group}", "", "| token | value |", "| --- | --- |"]
        lines += [f"| `{key}` | `{value}` |" for key, value in values.items()]
        lines.append("")
    return "\n".join(lines)


def render_directory(catalog, *, fmt: str = "markdown") -> str:
    """把整个目录渲染成一份索引文档。"""
    lines = ["# DESIGN.md 目录", ""]
    for category, slugs in sorted(catalog.categories.items()):
        lines += [f"## {category}", ""]
        for slug in slugs:
            entry = catalog.entries[slug]
            lines.append(
                f"- **{entry.name}** (`{entry.slug}`) — {entry.token_count} tokens。"
                f" {entry.description[:120]}"
            )
        lines.append("")
    lines += ["", "<!-- 来源：VoltAgent/awesome-design-md（MIT） -->"]
    return "\n".join(lines)
