#!/usr/bin/env python3
"""Guard the Hosted TSX panels against imports the surface iframe cannot resolve.

The plugin-manager compiles ui/*.tsx inside a sandboxed iframe. Bare module
specifiers such as "react" do not resolve there, and the panel fails to load
with the reported error:

    Bare import 'react' cannot resolve inside the surface iframe; import only
    relative helpers and '@neko/plugin-ui'

Only relative helpers and "@neko/plugin-ui" are allowed. The exported
components and hooks live in plugin/sdk/hosted-ui/index.d.ts of the N.E.K.O.
repository.

Rules per file (default: all plugins/*/ui/*.tsx):
  * import specifiers must be relative or "@neko/plugin-ui"
  * a default-exported function component must exist
  * that component must take PluginSurfaceProps from "@neko/plugin-ui"
  * no class components, dangerouslySetInnerHTML or require()

Implemented with regex only: TSX is not valid Python, so ast is unusable here.

Usage:
    python tools/check_tsx.py          # report, always exit 0
    python tools/check_tsx.py --strict # exit 1 on any finding
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

ALLOWED_SPECIFIERS = ("@neko/plugin-ui",)

IMPORT_RE = re.compile(r"""^[ \t]*import\s+(?:type\s+)?.*?from\s+['"]([^'"]+)['"]""", re.M)
DEFAULT_CLASS_RE = re.compile(r"^[ \t]*export\s+default\s+class\b", re.M)
DEFAULT_FN_RE = re.compile(
    r"""^[ \t]*export\s+default\s+(?:async\s+)?function\s+(\w+)[ \t]*\(([^)]*)\)""",
    re.M,
)
CLASS_COMPONENT_RE = re.compile(r"^[ \t]*class\s+\w+\s+extends\b", re.M)


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        rel = Path(path.name)
    text = path.read_text(encoding="utf-8")

    for specifier in IMPORT_RE.findall(text):
        if specifier.startswith(".") or specifier in ALLOWED_SPECIFIERS:
            continue
        problems.append(
            f"{rel}: bare import '{specifier}' cannot resolve inside the surface "
            "iframe; import only relative helpers and '@neko/plugin-ui'"
        )

    if DEFAULT_CLASS_RE.search(text) or CLASS_COMPONENT_RE.search(text):
        problems.append(f"{rel}: class components are not supported by the runtime")

    match = DEFAULT_FN_RE.search(text)
    if match is None:
        problems.append(f"{rel}: no default-exported function component")
    elif "PluginSurfaceProps" not in match.group(2):
        problems.append(
            f"{rel}: the default component `{match.group(1)}` does not take "
            "PluginSurfaceProps, so it will not receive state/actions/api"
        )

    # Match the JSX usage, not a mention inside a comment.
    if re.search(r"dangerouslySetInnerHTML\s*=", text):
        problems.append(f"{rel}: dangerouslySetInnerHTML is unsupported")
    if "require(" in text:
        problems.append(f"{rel}: require() is unsupported")

    return problems


def panels(roots: list[str] | None = None) -> list[Path]:
    if roots:
        return [Path(p) for p in roots]
    found = sorted(PLUGINS.glob("*/ui/*.tsx"))
    return found + sorted(PLUGINS.glob("*/ui/*.jsx"))


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    strict = "--strict" in argv
    found = panels(args)
    if not found:
        print("no TSX panels found")
        return 0

    problems: list[str] = []
    for path in found:
        problems += check_file(path)

    for problem in problems:
        print(problem)
    print(f"\n{len(found)} panel(s) checked, {len(problems)} problem(s)")
    return 1 if (problems and strict) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
