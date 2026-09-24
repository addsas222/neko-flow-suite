#!/usr/bin/env python3
"""从上游 README 的 Collection 段落生成 flow_designmd 的分类映射。

用法：
    python tools/build_categories.py <awesome-design-md checkout> \
        [--out plugin/plugins/flow_designmd/data/categories.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "flow_designmd"
    / "data"
    / "categories.json"
)


def extract(readme: Path) -> dict[str, str]:
    text = readme.read_text(encoding="utf-8")
    match = re.search(r"##\s*Collection(.*)\Z", text, re.DOTALL)
    if match is None:
        raise SystemExit("README 里找不到 Collection 段落")

    mapping: dict[str, str] = {}
    category = "Uncategorised"
    for line in match.group(1).splitlines():
        if line.startswith("### "):
            category = line[4:].strip()
            continue
        if line.startswith("#### "):
            continue
        # 目录条目形如 - [**Claude**](https://getdesign.md/claude/design-md) - ...
        for slug in re.findall(r"getdesign\.md/([a-z0-9-]+)/design-md", line):
            mapping.setdefault(slug, category)
    if not mapping:
        raise SystemExit("Collection 段落里没解析出任何条目")
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path, help="awesome-design-md 检出的根目录")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="只对比不写")
    args = parser.parse_args(argv)

    readme = args.checkout / "README.md"
    if not readme.is_file():
        print(f"找不到 {readme}", file=sys.stderr)
        return 2

    mapping = extract(readme)
    payload = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if current != payload:
            print(f"{args.out} 与上游 README 不一致，请重跑本脚本。", file=sys.stderr)
            return 1
        print(f"OK：{len(mapping)} 条分类映射与上游一致。")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    print(f"wrote {args.out}（{len(mapping)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
