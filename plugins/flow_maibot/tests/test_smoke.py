"""flow_maibot 脚手架自检：manifest、面板、指南、入口配对都要真的在。

这些是 `check_suite.py` 与 `check_tsx.py` 之外、只有本插件才知道的约束，所以放
在插件自己的测试里，避免"代码改了、manifest 没跟上"这种只在上宿主机时才炸的问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PLUGIN_DIR = Path(__file__).resolve().parents[1]
SUITE_ROOT = PLUGIN_DIR.parent.parent
BUNDLED = "_shared/maibot_plugins/anysearch_plugin.py"
ENDPOINT = "https://api.anysearch.test/mcp"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_plugin_manifest_exists() -> None:
    manifest = PLUGIN_DIR / "plugin.toml"
    assert manifest.is_file()
    text = read(manifest)
    assert 'id = "flow_maibot"' in text
    assert 'entry = "plugin.plugins.flow_maibot:FlowMaibotPlugin"' in text


def test_declared_files_exist() -> None:
    """manifest 里声明的每个文件都必须真的在：面板/指南缺失会变成死入口。"""
    text = read(PLUGIN_DIR / "plugin.toml")
    entries = re.findall(r'^\s*entry\s*=\s*"([^"]+)"', text, re.M)
    assert entries, "plugin.toml 没有声明任何 entry"
    for entry in entries:
        if entry.startswith("plugin.plugins."):
            continue
        path = PLUGIN_DIR / entry
        assert path.is_file(), f"plugin.toml 声明了 {entry} 但文件不存在"


def test_entry_class_is_exported() -> None:
    import flow_maibot

    assert flow_maibot.FlowMaibotPlugin.__name__ == "FlowMaibotPlugin"
    assert flow_maibot.__all__ == ["FlowMaibotPlugin"]


def test_every_plugin_entry_has_one_ui_action() -> None:
    """镜像 check_suite 的配对规则：缺 @ui.action 的面板按钮点不动。"""
    entries = set()
    actions: dict[str, int] = {}
    entry_re = re.compile(r'^[ \t]*@plugin_entry\(\s*id="(?P<id>[A-Za-z0-9_.-]+)"', re.M)
    action_re = re.compile(r'^[ \t]*@ui\.action\(id="(?P<id>[A-Za-z0-9_.-]+)"', re.M)
    for path in sorted(PLUGIN_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = read(path)
        entries.update(match.group("id") for match in entry_re.finditer(text))
        for match in action_re.finditer(text):
            key = match.group("id")
            actions[key] = actions.get(key, 0) + 1
    assert entries, "没有 @plugin_entry"
    assert not (entries - set(actions)), f"未暴露给面板: {sorted(entries - set(actions))}"
    assert not (set(actions) - entries), f"多余的 ui.action: {sorted(set(actions) - entries)}"
    duplicates = {key: count for key, count in actions.items() if count > 1}
    assert not duplicates, f"重复的 ui.action: {duplicates}"


def test_panel_context_matches_manifest() -> None:
    """@ui.context 的 id 必须和 manifest 里的 context 对得上，否则 state 无处可取。"""
    text = read(PLUGIN_DIR / "plugin.toml")
    declared = re.search(r'^\s*context\s*=\s*"([^"]+)"', text, re.M)
    assert declared, "plugin.toml 的面板没有声明 context"
    runtime = read(PLUGIN_DIR / "_runtime.py")
    assert f'PANEL_CONTEXT = "{declared.group(1)}"' in runtime, (
        "_runtime.py 的 PANEL_CONTEXT 与 manifest 声明的 context 不一致"
    )


def test_ruff_policy_file_present() -> None:
    policy = PLUGIN_DIR / "ruff.toml"
    assert policy.is_file()
    text = read(policy)
    assert 'target-version = "py311"' in text
    assert 'line-length = 120' in text
    assert 'select = ["E4", "E7", "E9", "F", "I"]' in text


def test_captured_schema_evidence_is_committed() -> None:
    capture = PLUGIN_DIR / "_shared" / "captured" / "anysearch_tools.json"
    assert capture.is_file(), "缺少上游捕获数据，schema 就没有凭据了"
    from _shared import schemas

    assert schemas.validate_capture() == []


def test_bundled_maibot_plugin_loads_through_the_bridge() -> None:
    from _shared.bridge import MaiBotBridge
    from _shared.settings import BridgeSettings

    settings = BridgeSettings.from_config(
        {"sdk": {"plugins": [{"path": "_shared/maibot_plugins/anysearch_plugin.py", "id": "anysearch"}]}}
    )
    bridge = MaiBotBridge(settings, base_dir=PLUGIN_DIR)

    import asyncio

    status = asyncio.run(bridge.load())
    problems = status["problems"]
    asyncio.run(bridge.unload())
    assert problems == [], problems
    assert sorted(item["name"] for item in status["tools"]) == [
        "anysearch.batch_search",
        "anysearch.search",
    ]


def test_no_secrets_in_the_plugin_tree() -> None:
    """令牌只能来自环境变量或宿主配置，不能硬编码在随包文件里。

    tests/ 里放的是假 fixture（而且是显式测"不回显密钥"的用例），不扫。
    """
    suspects = []
    for path in sorted(PLUGIN_DIR.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(PLUGIN_DIR)
        if relative.parts[0] == "tests" or relative.suffix not in {".py", ".toml", ".json", ".md"}:
            continue
        text = read(path)
        for pattern in (r"api_key\s*=\s*[\"'][^\"'\s]{8,}", r"Bearer\s+[A-Za-z0-9._-]{16,}"):
            if re.search(pattern, text):
                suspects.append(f"{relative.as_posix()}: {pattern}")
    assert not suspects, suspects


def test_suite_level_guards_present() -> None:
    """套件守卫本身要在：改坏它们是比改坏插件更危险的事。"""
    for name in ("check_suite.py", "check_tsx.py", "run_tests.py", "smoke.py"):
        assert (SUITE_ROOT / "tools" / name).is_file(), f"tools/{name} 不见了"


def test_guide_documents_every_configurable_key() -> None:
    """指南列的键必须都是 from_config 真认的；漏一个用户就配不上。"""
    from _shared.settings import BridgeSettings

    text = read(PLUGIN_DIR / "docs" / "guide.md")
    probe = {
        "sdk.enabled_bridge": {"sdk": {"enabled_bridge": False}},
        "sdk.strict_sdk": {"sdk": {"strict_sdk": True}},
        "sdk.plugins": {"sdk": {"plugins": [BUNDLED]}},
        "anysearch.endpoint": {"anysearch": {"endpoint": ENDPOINT}},
        "anysearch.api_key": {"anysearch": {"endpoint": ENDPOINT, "api_key": "k"}},
        "anysearch.api_key_env": {"anysearch": {"api_key_env": "FLOW_MAIBOT_ABSENT"}},
        "anysearch.headers": {"anysearch": {"endpoint": ENDPOINT, "headers": {"x-a": "1"}}},
        "anysearch.tools": {"anysearch": {"endpoint": ENDPOINT, "tools": ["search"]}},
        "anysearch.description_mode": {"anysearch": {"endpoint": ENDPOINT, "description_mode": "full"}},
        "anysearch.timeout_seconds": {"anysearch": {"endpoint": ENDPOINT, "timeout_seconds": 30}},
        "anysearch.max_chars": {"anysearch": {"endpoint": ENDPOINT, "max_chars": 1000}},
        "anysearch.max_results": {"anysearch": {"endpoint": ENDPOINT, "max_results": 5}},
    }
    assert probe, "probe 表不能空"
    for key in probe:
        assert f"`{key}`" in text, f"指南没有记录 {key}"
        BridgeSettings.from_config(probe[key])  # 不抛 ConfigError 才算真认这个键


def test_guide_documents_both_entries() -> None:
    """插件入口都要在指南里出现，否则用户不知道面板按钮背后是什么。"""
    text = read(PLUGIN_DIR / "docs" / "guide.md")
    for entry in ("attach", "refresh"):
        assert entry in text, f"指南没有写 {entry} 入口"
    assert "maibot" in text, "指南没有说明面板上下文"


def test_readme_lists_the_bundled_plugin_and_no_deps() -> None:
    text = read(PLUGIN_DIR / "README.md")
    assert "FlowMaibotPlugin" in text
    assert "anysearch_plugin.py" in text
    assert "no third-party dependencies" in text
    assert "NOTICE" in text

def test_sources_registry_covers_every_plugin() -> None:
    """sync_sources.py --check 的等价断言：漏登记来源会让 SOURCE.md 静默漂移。"""
    import json

    registry = json.loads((SUITE_ROOT / "sources.json").read_text(encoding="utf-8"))
    registered = {entry["plugin"] for entry in registry["sources"] + registry["design_sources"]}
    existing = {path.name for path in (SUITE_ROOT / "plugins").iterdir() if path.is_dir()}
    assert registered == existing, f"登记表与 plugins/ 不一致：{registered ^ existing}"


def test_source_md_and_notice_are_generated_and_not_stale() -> None:
    """SOURCE.md / NOTICE 是生成物；手改过只有 --check 才发现得了。"""
    import subprocess
    import sys as _sys

    for name in ("SOURCE.md", "NOTICE"):
        text = read(PLUGIN_DIR / name)
        assert "由 tools/sync_sources.py" in text, f"{name} 不是生成物，请不要手改"

    proc = subprocess.run(
        [_sys.executable, str(SUITE_ROOT / "tools" / "sync_sources.py"), "--check"],
        cwd=str(SUITE_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, (proc.stdout + proc.stderr) or "sync_sources.py --check 失败"
    assert "OK" in proc.stdout, proc.stdout


def test_source_md_claims_no_upstream_code() -> None:
    """本插件不含任何上游源码——这条边界必须在生成的署名里讲清楚。"""
    source = read(PLUGIN_DIR / "SOURCE.md")
    notice = read(PLUGIN_DIR / "NOTICE")
    for text in (source, notice):
        assert "已适配" in text or "适配" in text
        assert "MIT" in text
        # 绝不能出现「移植代码沿用上游许可证」这类错误表述
        assert "移植代码沿用该许可证" not in text
        assert "移植代码沿用 LGPL-3.0" not in text
    assert "不包含其任何上游代码" in notice

