"""DESIGN.md 语料条目模型。

design-md/<slug>/DESIGN.md 的 front matter 是 Google Stitch 定义的纯文本设计
系统文档：colors / typography / spacing / radius / motion / copy 等 token。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

#: catalog 的顶层 token 分组。
TOKEN_GROUPS: tuple[str, ...] = ("colors", "typography", "spacing", "radius", "shadow", "motion")


@dataclass(slots=True)
class DesignEntry:
    slug: str
    name: str
    description: str
    version: str = "alpha"
    category: str = "Uncategorised"
    raw_groups: dict[str, dict[str, object]] = field(default_factory=dict)
    source_path: str = ""

    @property
    def colors(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("colors", {}))

    @property
    def typography(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("typography", {}))

    @property
    def spacing(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("spacing", {}))

    @property
    def radius(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("radius", {}))

    @property
    def shadow(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("shadow", {}))

    @property
    def motion(self) -> dict[str, str]:
        return flatten(self.raw_groups.get("motion", {}))

    @property
    def token_count(self) -> int:
        return sum(len(getattr(self, group)) for group in TOKEN_GROUPS)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "token_count": self.token_count,
            "colors": dict(self.colors),
            "typography": dict(self.typography),
        }
        for group in ("spacing", "radius", "shadow", "motion"):
            values = getattr(self, group)
            if values:
                payload[group] = dict(values)
        return payload

    def search_text(self) -> str:
        return " ".join(
            [self.slug, self.name, self.description, self.category,
             " ".join(self.colors), " ".join(self.typography)]
        ).lower()


def _split_body(
    front_matter: str,
) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    """把 front matter 拆成顶层扁平键值 + 分组嵌套树。

    Stitch 的 front matter 是「YAML 风格但完全不严格」的缩进块：顶层
    `key: value`，分组下两空格缩进， token 内部还可再嵌一层。这里用缩进
    栈判定层级，不引入 YAML 依赖。
    """
    flat: dict[str, str] = {}
    root: dict[str, dict[str, object]] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]

    for raw_line in front_matter.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        container = stack[-1][1]

        if value:
            if indent == 0:
                flat[key] = value
            container[key] = value
        else:
            child: dict[str, object] = {}
            container[key] = child
            stack.append((indent, child))

    return flat, root


def flatten(group: dict[str, object], prefix: str = "") -> dict[str, str]:
    """把嵌套 token 树拍平成 `a-b-c: value` 路径。"""
    out: dict[str, str] = {}
    for key, value in group.items():
        path = f"{prefix}-{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = str(value)
    return out


def parse_design_md(text: str, *, slug: str = "", source_path: str = "") -> DesignEntry:
    """解析一份 DESIGN.md。"""
    match = _FRONT_MATTER.match(text)
    if match is None:
        return DesignEntry(
            slug=slug,
            name=slug,
            description="",
            source_path=source_path,
        )

    flat, grouped = _split_body(match.group(1))

    # 顶层若直接写了颜色键（没有 colors: 分组），补一个 colors 组。
    loose_colours = {
        key: value for key, value in flat.items() if _looks_like_colour(value)
    }
    if loose_colours:
        grouped.setdefault("colors", {}).update(loose_colours)

    return DesignEntry(
        slug=slug or flat.get("name", "").lower().replace(" ", "-"),
        name=flat.get("name", slug),
        description=flat.get("description", ""),
        version=flat.get("version", "alpha"),
        raw_groups=grouped,
        source_path=source_path,
    )


def _looks_like_colour(value: str) -> bool:
    return bool(re.fullmatch(r"#[0-9a-fA-F]{3,8}", value.strip()))
