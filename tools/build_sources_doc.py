#!/usr/bin/env python3
"""从 sources.json 生成人类可读的 SOURCES.md。

与 tools/sync_sources.py 共用同一个登记表，避免两处漂移。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "sources.json"
OUT = ROOT / "SOURCES.md"

GROUPS = (
    ("design_sources", "UI / UX 设计类"),
    ("sources", "工作流类"),
)


def main(argv: list[str]) -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    suite = registry["suite"]

    lines = [
        "# 来源登记表",
        "",
        "> 本文件由 tools/build_sources_doc.py 从 sources.json 生成，请勿手改。",
        "",
        f"套件仓库：{suite['repo']}",
        "",
        suite["policy"],
        "",
        "| 插件 | 上游 | 许可证 | 基线引用 | star | 汇总 |",
        "|---|---|---|---|---|---|",
    ]

    for key, _title in GROUPS:
        for entry in registry.get(key, []):
            url = entry.get("upstream_url") or "（待确认）"
            name = entry.get("upstream_repo") or "（待确认）"
            ref = entry.get("ref", "")
            stars = f"{entry['stars']:,}" if entry.get("stars") else "—"
            lines.append(
                f"| `{entry['plugin']}` | [{name}]({url}) | {entry.get('license', '待确认')} "
                f"| `{ref}` | {stars} | {entry.get('summary', '')} |"
            )

    lines += ["", "## 逐条详情", ""]

    for key, title in GROUPS:
        lines += [f"### {title}", ""]
        for entry in registry.get(key, []):
            lines += [
                f"#### `{entry['plugin']}` — {entry['key']}",
                "",
                f"- 上游：[{entry.get('upstream_repo') or '（待确认）'}]"
                f"({entry.get('upstream_url') or '（待确认）'})",
                f"- 许可证：{entry.get('license', '待确认')}",
                f"- 基线引用：`{entry.get('ref', '')}`"
                + (f"（branch `{entry['branch']}`）" if entry.get("branch") else ""),
                f"- 分组：{entry['group']}",
                "",
                entry.get("summary", ""),
                "",
                "移植清单：",
                "",
            ]
            lines += [f"  - {item}" for item in entry.get("ported", [])]
            lines += ["", f"边界与差异：{entry.get('notes', '')}", ""]

    lines += [
        "## 上游许可证要点",
        "",
        "- MIT（archify、simplify-codebase、ponytail、taste-skill、huashu-design、",
        "  awesome-design-md）：保留版权声明与许可证声明即可分发与修改。",
        "- Apache-2.0（OpenViking、impeccable）：额外要求声明修改、保留 NOTICE、",
        "  并在改动文件里标注。已在各插件 `NOTICE` 中落实。",
        "- 待确认（evomap、eigenflux）：确认上游仓库与许可证前，不发布其移植代码。",
        "",
    ]

    text = "\n".join(lines).rstrip() + "\n"
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != text:
            print("SOURCES.md 与 sources.json 不一致，请跑 tools/build_sources_doc.py。", file=sys.stderr)
            return 1
        print("OK：SOURCES.md 与 sources.json 一致。")
        return 0

    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}（{len(text.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
