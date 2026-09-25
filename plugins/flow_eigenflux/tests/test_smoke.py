"""flow_eigenflux 的占位插件测试。

上游 phronesis-io/eigenflux 的许可证是 NOASSERTION，无法识别成任何标准开源
许可证，所以本插件不移植、不分发上游的任何代码；但仍然必须以合法插件的形态
存在（plugin.toml + NekoPluginBase 子类），否则宿主会把它当成坏包。

这里校验四件事：
1. plugin.toml 是合法清单，且把自己关成「不自动启动 / 不参与 Agent 分派」；
2. 入口类能被导入，并真的带 @plugin_entry 元数据；
3. 唯一入口必然失败，且把「上游许可证未识别」讲清楚；
4. 目录里没有任何上游代码——全插件只有 __init__.py 一个 .py。
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for _path in (str(HERE), str(HERE.parent)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _plugin_module():
    """sys.path 就绪之后才导入；模块级导入会踩 E402。"""
    return importlib.import_module("flow_eigenflux")


def _entry_class():
    return getattr(_plugin_module(), "FlowEigenfluxPlugin")


def test_manifest_is_a_valid_but_disabled_plugin() -> None:
    manifest = HERE / "plugin.toml"
    assert manifest.is_file()
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    plugin = data["plugin"]

    # 文档要求 [plugin] 至少给出 id / name / version / entry 四个字段。
    assert plugin["id"] == "flow_eigenflux"
    assert plugin["name"]
    assert plugin["version"]
    assert plugin["entry"] == "plugin.plugins.flow_eigenflux:FlowEigenfluxPlugin"
    assert plugin["type"] == "plugin"

    # 禁用态：不自动启动，也不交给 Agent 分派。
    assert plugin["passive"] is True
    assert data["plugin_runtime"]["auto_start"] is False
    assert data["plugin_runtime"]["enabled"] is True

    # 没有真实能力可卖，就不该开 UI / store / i18n 这些段。
    assert "ui" not in plugin
    assert "store" not in plugin
    assert "i18n" not in plugin


def test_entry_class_is_importable_and_declares_one_entry() -> None:
    assert _plugin_module().FlowEigenfluxPlugin is _entry_class()
    meta = getattr(_entry_class().status, "_plugin_entry", None)
    assert meta is not None, "status 必须带 @plugin_entry 元数据"
    assert meta["id"] == "status"


async def _call_status() -> dict:
    plugin = _entry_class()(None)
    result = await plugin.status()
    # 宿主里的 Err 可能返回 Result 对象；套件仓库里固定是 dict。
    return result if isinstance(result, dict) else dict(vars(result))


def test_only_entry_always_fails_with_the_license_reason() -> None:
    payload = asyncio.run(_call_status())
    assert payload["ok"] is False
    error = str(payload["error"])
    assert "NOASSERTION" in error
    assert "未识别" in error
    assert "不移植" in error


def test_no_upstream_code_is_shipped() -> None:
    assert not (HERE / "_shared").exists(), "不移植的插件不该有 _shared 实现层"
    shipped = [
        path
        for path in HERE.rglob("*.py")
        if "__pycache__" not in path.parts and path.name != "test_smoke.py"
    ]
    assert [path.name for path in shipped] == ["__init__.py"]


def test_plugin_is_documented_as_not_portable() -> None:
    text = (HERE / "SOURCE.md").read_text(encoding="utf-8")
    assert "phronesis-io/eigenflux" in text
    assert "NOASSERTION" in text
    assert "不移植" in text


def test_notice_says_reference_only() -> None:
    text = (HERE / "NOTICE").read_text(encoding="utf-8")
    assert "不包含其任何代码" in text
    assert "NOASSERTION" in text

