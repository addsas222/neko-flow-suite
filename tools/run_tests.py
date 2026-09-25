#!/usr/bin/env python3
"""跑所有插件的单元测试与冒烟检查。

套件里的测试文件混用两种风格：`unittest.TestCase` 与 pytest 风格的裸
`assert` 函数。环境里不一定装了 pytest，所以这里自带一个最小收集器，
两种都跑。

用法：
    python tools/run_tests.py             # 全部
    python tools/run_tests.py flow_taste  # 单个
    python tools/run_tests.py --quiet     # 只打汇总
"""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import traceback
import unittest
from pathlib import Path

#: Windows 控制台默认 GBK，必须强制 UTF-8，否则中文摘要会把脚本自己打炸。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, io.UnsupportedOperation):
        pass

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def run_plugin(name: str, verbose: bool) -> tuple[int, int, list[str]]:
    """返回 (通过数, 失败数, 失败详情)。"""
    directory = PLUGINS / name
    added = [p for p in (str(directory), str(PLUGINS)) if p not in sys.path]
    for path in reversed(added):
        sys.path.insert(0, path)

    passed = failed = 0
    details: list[str] = []

    try:
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        functions: list = []

        for path in sorted((directory / "tests").glob("test_*.py")):
            try:
                module = load_module(path)
            except Exception:
                failed += 1
                details.append(f"[import] {path.name}\n{traceback.format_exc(limit=3)}")
                continue

            for attr in vars(module).values():
                if isinstance(attr, type) and issubclass(attr, unittest.TestCase):
                    suite.addTests(loader.loadTestsFromTestCase(attr))
            for attr_name, attr in vars(module).items():
                if attr_name.startswith("test_") and callable(attr):
                    functions.append((f"{path.stem}.{attr_name}", attr))

        if suite.countTestCases():
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
            passed += result.testsRun - len(result.failures) - len(result.errors)
            failed += len(result.failures) + len(result.errors)
            for case, tb in result.failures + result.errors:
                details.append(f"[unittest] {case.id()}\n{tb}")

        for label, func in functions:
            try:
                func()
                passed += 1
                if verbose:
                    print(f"    ok   {label}")
            except Exception:
                failed += 1
                details.append(f"[pytest-style] {label}\n{traceback.format_exc(limit=4)}")
                if verbose:
                    print(f"    FAIL {label}")
    finally:
        # 每个插件的 _shared / _runtime 都是同名顶层模块，必须逐个清除，
        # 否则后一个插件会拿到前一个插件的 _shared。
        for key in [
            k
            for k in list(sys.modules)
            if k.startswith(("_shared", "_runtime"))
            or k in (name, f"{name}._shared", f"{name}._runtime")
        ]:
            del sys.modules[key]
        for path in added:
            if path in sys.path:
                sys.path.remove(path)

    return passed, failed, details


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    verbose = "--quiet" not in argv

    names = args or sorted(p.name for p in PLUGINS.iterdir() if p.is_dir())

    total_pass = total_fail = 0
    broken: list[str] = []

    for name in names:
        if not ((PLUGINS / name / "tests").is_dir() and any((PLUGINS / name / "tests").glob("test_*.py"))):
            print(f"skip {name}（无 test_*.py）")
            continue

        passed, failed, details = run_plugin(name, verbose)
        total_pass += passed
        total_fail += failed
        print(f"=== {name}: {'OK' if not failed else 'FAILED'}  {passed} passed, {failed} failed")
        for detail in details:
            print(detail)
        if failed:
            broken.append(name)

    tsx = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_tsx.py"), "--strict"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if (tsx.stdout or "").strip():
        print((tsx.stdout or "").strip())

    print()
    smoke = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "smoke.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print((smoke.stdout or "").strip())

    if broken:
        print(f"\n失败：{', '.join(broken)}")
        return 1
    if tsx.returncode != 0:
        print("\n失败：TSX 面板存在裸导入或契约错误（见 tools/check_tsx.py）")
        return 1
    if smoke.returncode != 0:
        return 1
    print(f"\n全部通过：测试 {total_pass} passed / {total_fail} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
