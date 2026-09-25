#!/usr/bin/env python3
"""Suite-wide guards: every entry exposed exactly once, and ruff clean.

For every plugin under plugins/ this checks that
  * every @plugin_entry has exactly one matching @ui.action -- a duplicate
    makes the panel render the same action twice, and a missing one means
    props.api.call(entryId) has nothing to dispatch to, which is how the
    Hosted UI panels end up dead
  * ruff 0.12.4 reports no findings under the repository's standard policy

Usage:
    python tools/check_suite.py            # report, exit 1 on any problem
    python tools/check_suite.py --no-ruff  # skip the (slower) ruff pass
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

BS = chr(92)
TAB = chr(9)
NL = chr(10)

RUFF_POLICY = NL.join(
    [
        'target-version = "py311"',
        "line-length = 120",
        'extend-exclude = ["vendor"]',
        "respect-gitignore = false",
        "",
        "[lint]",
        'select = ["E4", "E7", "E9", "F", "I"]',
        "",
    ]
)

ENTRY_RE = re.compile(
    "^[ " + TAB + "]*@plugin_entry" + BS + "(" + BS + "s*id=\"(?P<id>[A-Za-z0-9_.-]+)\"",
    re.M,
)
ACTION_RE = re.compile(
    "^[ " + TAB + "]*@ui" + BS + ".action" + BS + "(id=\"(?P<id>[A-Za-z0-9_.-]+)\"",
    re.M,
)


def plugin_dirs() -> list[Path]:
    return sorted(p for p in PLUGINS.iterdir() if p.is_dir())


def py_files(plugin: Path) -> list[Path]:
    return [f for f in sorted(plugin.rglob("*.py")) if "__pycache__" not in f.parts]


def check_exposure() -> list[str]:
    problems: list[str] = []
    for plugin in plugin_dirs():
        entries: set[str] = set()
        actions: dict[str, int] = {}
        for f in py_files(plugin):
            text = f.read_text(encoding="utf-8")
            entries.update(m.group("id") for m in ENTRY_RE.finditer(text))
            for m in ACTION_RE.finditer(text):
                key = m.group("id")
                actions[key] = actions.get(key, 0) + 1
        missing = sorted(entries - set(actions))
        orphans = sorted(set(actions) - entries)
        duplicates = {k: v for k, v in actions.items() if v > 1}
        print(f"{plugin.name:18} entries={len(entries):2d} exposed={len(actions):2d}", end="")
        if missing or orphans or duplicates:
            print("  PROBLEM")
            if missing:
                print(f"    not exposed: {missing}")
            if orphans:
                print(f"    action id has no entry: {orphans}")
            if duplicates:
                print(f"    duplicated: {duplicates}")
            problems.append(plugin.name)
        else:
            print("  ok")
    return problems


def check_ruff() -> list[str]:
    problems: list[str] = []
    cfg = ROOT / "_ruff_std.toml"
    cfg.write_text(RUFF_POLICY, encoding="utf-8")
    try:
        for plugin in plugin_dirs():
            r = subprocess.run(
                ["uvx", "ruff==0.12.4", "check", "--config", str(cfg),
                 "--output-format", "concise", "."],
                cwd=str(plugin),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            lines = [l.strip() for l in (r.stdout + r.stderr).splitlines() if l.strip()]
            if lines and lines[0] != "All checks passed!":
                print(f"  {plugin.name}: {lines[0]}")
                problems.append(plugin.name)
    finally:
        cfg.unlink(missing_ok=True)
    return problems


def main(argv: list[str]) -> int:
    exposure = check_exposure()
    dirty: list[str] = []
    if "--no-ruff" not in argv:
        print()
        dirty = check_ruff()

    if dirty:
        print(f"ruff: {len(dirty)} plugin(s) not clean")
    elif "--no-ruff" not in argv:
        print("ruff: all plugins clean")

    if exposure or dirty:
        print(f"\nFAILED: exposure={exposure or 'ok'} ruff={dirty or 'ok'}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
