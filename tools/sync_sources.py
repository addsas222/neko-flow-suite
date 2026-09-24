#!/usr/bin/env python3
"""从 sources.json 生成每个插件的 SOURCE.md 与 NOTICE。

单一事实来源：sources.json。改来源只改这个文件，然后重跑本脚本。

用法：
    python tools/sync_sources.py            # 写文件
    python tools/sync_sources.py --check    # 只校验不写，退出码非 0 表示有插件缺来源
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
REGISTRY = ROOT / "sources.json"

HEADER = """<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->"""


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def all_entries(registry: dict) -> list[dict]:
    return list(registry.get("sources", [])) + list(registry.get("design_sources", []))


def render_source_md(entry: dict, suite: dict) -> str:
    url = entry.get("upstream_url") or "(待确认)"
    ref = entry.get("ref", "")
    branch = entry.get("branch", "")
    stars = entry.get("stars")
    lines = [
        HEADER,
        "",
        f"# {entry['plugin']} · 来源",
        "",
        f"**上游项目**：[{entry['key']}]({url})  ",
        f"**上游仓库**：`{entry.get('upstream_repo') or '(待确认)'}`  ",
        f"**上游许可证**：{entry.get('license', '待确认')}  ",
        f"**基线引用**：`{ref}`" + (f"（branch `{branch}`）" if branch else "") + "  ",
    ]
    if stars:
        lines.append(f"**上游 star 数**：{stars:,}（采集于 2026-09-24）  ")
    lines += [
        f"**本套件中的形态**：{entry['group']} 组插件，插件 ID `{entry['plugin']}`  ",
        f"**套件仓库**：{suite['repo']}  ",
        "",
        "## 它做什么",
        "",
        entry.get("summary", ""),
        "",
        "## 移植了什么",
        "",
    ]
    lines += [f"- {item}" for item in entry.get("ported", [])]
    lines += [
        "",
        "## 边界与差异",
        "",
        entry.get("notes", ""),
        "",
        "## 合规",
        "",
        f"上游以 {entry.get('license', '待确认')} 发布。本插件的移植代码沿用该许可证；"
        "套件自身的编排代码以 MIT 发布。上游的商标、品牌资产与素材不在本仓库内重分发。",
        "",
        "见同目录 `NOTICE` 获取完整署名。",
        "",
    ]
    return "\n".join(lines)


def render_notice(entry: dict, suite: dict) -> str:
    url = entry.get("upstream_url") or "(待确认)"
    return "\n".join(
        [
            HEADER,
            "",
            f"NOTICE · {entry['plugin']}",
            "",
            f"本插件移植自 {entry['key']}（{url}）。",
            f"上游许可证：{entry.get('license', '待确认')}",
            f"基线引用：{entry.get('ref', '')}",
            "",
            f"{entry['plugin']} 的编排与胶水代码：",
            f"Copyright (c) 2026 {suite['repo'].rsplit('/', 1)[-1]} contributors，MIT。",
            "",
            "上游项目的版权与商标归其作者所有。",
            "",
        ]
    )


def main(argv: list[str]) -> int:
    registry = load_registry()
    suite = registry["suite"]
    entries = all_entries(registry)
    by_plugin = {entry["plugin"]: entry for entry in entries}

    check_only = "--check" in argv
    problems: list[str] = []

    if not PLUGINS.is_dir():
        print(f"plugins directory missing: {PLUGINS}", file=sys.stderr)
        return 2

    for plugin_dir in sorted(p for p in PLUGINS.iterdir() if p.is_dir()):
        entry = by_plugin.get(plugin_dir.name)
        if entry is None:
            problems.append(f"{plugin_dir.name}: 没有登记来源，请补进 sources.json")
            continue
        for name, text in (
            ("SOURCE.md", render_source_md(entry, suite)),
            ("NOTICE", render_notice(entry, suite)),
        ):
            target = plugin_dir / name
            if check_only:
                if not target.is_file():
                    problems.append(f"{plugin_dir.name}: 缺 {name}")
            else:
                target.write_text(text, encoding="utf-8")
                print(f"wrote {target.relative_to(ROOT)}")

    registered = set(by_plugin)
    existing = {p.name for p in PLUGINS.iterdir() if p.is_dir()}
    for name in sorted(registered - existing):
        problems.append(f"sources.json 登记了 {name}，但 plugins/ 下没有该目录")

    if problems:
        print("\n问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"\nOK：{len(existing)} 个插件全部有来源标注" + ("（--check 模式）" if check_only else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
