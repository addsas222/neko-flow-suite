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
        "| 插件 | 上游 | 许可证 | 状态 | 基线引用 | star | 汇总 |",
        "|---|---|---|---|---|---|---|",
    ]

    for key, _title in GROUPS:
        for entry in registry.get(key, []):
            url = entry.get("upstream_url") or "（待确认）"
            name = entry.get("upstream_repo") or "（待确认）"
            ref = entry.get("ref", "")
            stars = f"{entry['stars']:,}" if entry.get("stars") else "—"
            status = "不移植" if entry.get("porting_status") == "blocked" else "已移植"
            lines.append(
                f"| `{entry['plugin']}` | [{name}]({url}) | {entry.get('license', '待确认')} "
                f"| {status} | `{ref}` | {stars} | {entry.get('summary', '')} |"
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
                f"- 移植状态："
                + (
                    f"不移植 —— {entry['porting_block']}"
                    if entry.get("porting_status") == "blocked"
                    else "已移植"
                ),
                f"- 基线引用：`{entry.get('ref', '')}`"
                + (f"（branch `{entry['branch']}`）" if entry.get("branch") else ""),
                f"- 分组：{entry['group']}",
                "",
                entry.get("summary", ""),
                "",
                "移植清单：",
                "",
            ]
            if entry.get("porting_status") == "blocked":
                lines += ["  - （无。只登记来源与设计说明，不含上游代码。）"]
            else:
                lines += [f"  - {item}" for item in entry.get("ported", [])]
            lines += ["", f"边界与差异：{entry.get('notes', '')}", ""]

    lines += [
        "## 上游许可证要点",
        "",
        "- MIT（archify、simplify-codebase、ponytail、taste-skill、huashu-design、",
        "  awesome-design-md）：保留版权声明与许可证声明即可分发与修改。",
        "- Apache-2.0（OpenViking、impeccable）：额外要求声明修改、保留 NOTICE、",
        "  并在改动文件里标注。已在各插件 `NOTICE` 中落实。",
        "- GPL-3.0（evomap / EvoMap/evolver）：强 copyleft，衍生作品必须以 GPL-3.0",
        "  整体分发，与本套件的 MIT 冲突。**不移植**；若要引入须拆为独立 GPL-3.0 仓库，",
        "  并从本套件的 MIT 分发中移除。",
        "- NOASSERTION（eigenflux / phronesis-io/eigenflux）：GitHub 未识别为任何标准",
        "  开源许可证，不能假定允许移植或再分发。**不移植**，待上游给出明确许可证文本后",
        "  再评估。",
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
