#!/usr/bin/env python3
"""套件冒烟检查：逐个导入每个插件的 _shared 层与其插件入口类。

用法：
    python tools/smoke.py            # 检查全部插件
    python tools/smoke.py flow_taste # 只检查一个
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
STUB = Path(__file__).resolve().parent / "_stub"


def check(name: str) -> list[str]:
    problems: list[str] = []
    directory = PLUGINS / name

    added: list[str] = []
    for path in (str(STUB), str(directory), str(PLUGINS)):
        if path not in sys.path:
            sys.path.insert(0, path)
            added.append(path)

    try:
        try:
            importlib.import_module("_shared")
        except Exception:
            problems.append(f"{name}._shared 导入失败：\n{traceback.format_exc(limit=4)}")

        try:
            module = importlib.import_module(name)
            exported = [key for key in vars(module) if key.endswith("Plugin")]
            if not exported:
                problems.append(f"{name}.__init__ 没有导出 *Plugin 类")
        except Exception:
            problems.append(f"{name}.__init__ 导入失败：\n{traceback.format_exc(limit=4)}")
    finally:
        # 每个插件都自带顶层 _shared / _runtime 模块名，必须逐个清除，否则跨插件撞名。
        for key in [
            k
            for k in list(sys.modules)
            if k
            in (
                "_shared",
                "_runtime",
                "_runtime_part1",
                "_runtime_part2",
            )
            or k.startswith(("_shared.", "_runtime."))
        ]:
            del sys.modules[key]
        sys.modules.pop(name, None)
        for key in [k for k in list(sys.modules) if k.startswith(name + ".")]:
            del sys.modules[key]
        for path in added:
            if path in sys.path:
                sys.path.remove(path)

    return problems


def main(argv: list[str]) -> int:
    if argv and argv[0] != "all":
        names = argv
    else:
        names = sorted(
            p.name for p in PLUGINS.iterdir() if p.is_dir() and (p / "__init__.py").is_file()
        )

    failures = 0
    for name in names:
        problems = check(name)
        if problems:
            failures += 1
            print(f"FAIL {name}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"ok   {name}")

    print(f"\n{failures} 个插件有问题 / 共 {len(names)} 个")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
