"""桥接层配置的解析与校验。

配置形态（插件面板 JSON，等价于[[tool_configs]]的 config）：

    {
      "sdk":    {"enabled_bridge": true, "strict_sdk": false, "plugins": []},
      "anysearch": {"endpoint": "https://api.anysearch.com/mcp", "api_key": "",
                    "tools": ["search", "batch_search"], "description_mode": "brief"}
    }

设计约束：
    * 回显/日志/错误信息里都不出现密钥；
    * 解析阶段就把错误说清楚（错误信息是给人看的）；
    * 所有字段都有默认值，空配置也能启动（处于"未启用/降级"状态）。
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import schemas
from .errors import ConfigError

DEFAULT_ENDPOINT = "https://api.anysearch.com/mcp"
DEFAULT_API_KEY_ENV = "ANYSEARCH_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_CHARS = 24000
DEFAULT_MAX_RESULTS = 10
DEFAULT_TOOLS = schemas.DEFAULT_TOOLS
DEFAULT_DESCRIPTION_MODE = "brief"
DESCRIPTION_MODES = ("brief", "full")

#: 内置的 MaiBot 插件：规范 id -> 相对本插件目录的路径
BUNDLED_PLUGINS: dict[str, str] = {
    "anysearch": "_shared/maibot_plugins/anysearch_plugin.py",
}
#: 内置插件的好记别名；写插件 id / 类名 / 文件名 stem 都行，省得背源码相对路径。
BUNDLED_PLUGIN_ALIASES: dict[str, str] = {
    alias.casefold(): canonical
    for canonical, path in BUNDLED_PLUGINS.items()
    for alias in (canonical, Path(path).stem, f"{canonical}plugin")
}
#: 兼容旧常量：内置 AnySearch 插件的路径
BUNDLED_ANYSEARCH_PLUGIN = BUNDLED_PLUGINS["anysearch"]


@dataclass(frozen=True)
class MaiBotPluginSpec:
    """一个待加载的 MaiBot 插件。"""

    id: str
    path: str
    class_name: str = ""
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    def resolved_path(self, base_dir: Path | str) -> Path:
        candidate = Path(str(self.path)).expanduser()
        if not candidate.is_absolute():
            candidate = (Path(base_dir) / candidate).resolve()
        return candidate


@dataclass(frozen=True)
class AnySearchSettings:
    """AnySearch 网关配置。"""

    endpoint: str = DEFAULT_ENDPOINT
    token: str = ""
    token_source: str = "none"
    headers: dict[str, str] = field(default_factory=dict)
    tools: tuple[str, ...] = DEFAULT_TOOLS
    description_mode: str = DEFAULT_DESCRIPTION_MODE
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_chars: int = DEFAULT_MAX_CHARS
    max_results: int = DEFAULT_MAX_RESULTS


@dataclass(frozen=True)
class BridgeSettings:
    """整个桥的配置。"""

    plugins: tuple[MaiBotPluginSpec, ...] = ()
    anysearch: AnySearchSettings = AnySearchSettings()
    strict_sdk: bool = False

    @property
    def enabled(self) -> bool:
        return any(spec.enabled for spec in self.plugins)

    @classmethod
    def from_config(cls, data: Any, *, base_dir: Path | str | None = None) -> "BridgeSettings":
        del base_dir  # 路径解析在 MaiBotPluginSpec.resolved_path 里做，那里才知道 base_dir
        root = _normalize_config(_as_mapping(data, "插件配置"))
        sdk = _as_mapping(root.get("sdk", {}), "sdk")
        mcp = _as_mapping(root.get("anysearch", {}), "anysearch")

        enabled_bridge = _as_bool(sdk.get("enabled_bridge", True), "sdk.enabled_bridge")
        specs = _parse_plugins(sdk.get("plugins"), mcp)
        if not enabled_bridge:
            specs = tuple(
                MaiBotPluginSpec(spec.id, spec.path, spec.class_name, False, spec.config) for spec in specs
            )
        return cls(
            plugins=specs,
            anysearch=_parse_anysearch(mcp),
            strict_sdk=_as_bool(sdk.get("strict_sdk", False), "sdk.strict_sdk"),
        )


def _normalize_config(root: dict[str, Any]) -> dict[str, Any]:
    """把插件配置收敛成 :meth:`BridgeSettings.from_config` 认的扁形。

    ``plugin.toml`` 允许三种写法，语义完全等价：

    1. 标准形：``{"sdk": {...}, "anysearch": {...}}``
    2. 包装形：``{"maibot": {"sdk": {...}, "anysearch": {...}}}``（N.E.K.O. 的
       自定义配置表习惯会让顶层多套一层插件 id）
    3. 平铺形：``{"strict_sdk": true, "plugins": [...], "anysearch.endpoint": "..."}``
       —— ``sdk`` 下的键直接写在段里，``anysearch.`` 前缀用点号键展开

    另外 ``plugins`` 里写内置插件的 ID / 类名（如 ``"AnySearch"``）会自动补全成
    内置插件路径，省得用户背源码相对路径。
    """
    root = _unwrap_config(_flatten_dotted_keys(root))
    sdk = _as_mapping(root.get("sdk"), "sdk")
    for key, target in (("enabled", "enabled_bridge"), ("strict_sdk", "strict_sdk"), ("plugins", "plugins")):
        if key in root and target not in sdk:
            sdk[target] = root[key]
    if sdk:
        root["sdk"] = sdk
    return root


def _flatten_dotted_keys(root: dict[str, Any]) -> dict[str, Any]:
    """把 ``anysearch.endpoint`` 这类点号键收进 ``anysearch`` 子表。"""
    plain = {key: value for key, value in root.items() if "." not in key}
    for key, value in root.items():
        if "." not in key:
            continue
        head, _, tail = key.partition(".")
        if not head or not tail:
            continue
        section = plain.get(head)
        plain[head] = {**(section if isinstance(section, Mapping) else {}), tail: value}
    return plain


def _unwrap_config(root: dict[str, Any]) -> dict[str, Any]:
    """剥掉 ``plugin.toml`` 自定义配置表带来的那一层包装。

    N.E.K.O. 的习惯是让每个插件在 ``plugin.toml`` 里用插件 id 命名自己的配置表
    （本插件就是 ``[maibot]``），宿主交给插件时顶层会多套一层：:

        {"maibot": {"sdk": {...}, "anysearch": {...}}}

    而 ``data/config.json`` 与历史版本用的是不带包装的扁形。两者语义等价，所以
    这里统一剥成扁形。只在顶层没有 ``sdk``/``anysearch``、且恰好只有一个"里面
    确实装着 ``sdk``/``anysearch``"的表时才剥，避免把其他配置误当包装。
    """
    if "sdk" in root or "anysearch" in root:
        return root
    for value in root.values():
        if not isinstance(value, Mapping):
            continue
        inner = dict(value)
        if "sdk" in inner or "anysearch" in inner:
            return inner
    return root


def _as_mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
        except ValueError as exc:
            raise ConfigError(f"{name} 不是合法 JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} 必须是对象/JSON 对象")
    return dict(value)


def _as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on", "开启"):
            return True
        if text in ("0", "false", "no", "off", "关闭", ""):
            return False
    raise ConfigError(f"{name} 只能是布尔值")


def _as_str(value: Any, name: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    raise ConfigError(f"{name} 必须是字符串")


def _as_int(value: Any, name: str, *, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} 必须是整数") from exc
    return max(low, min(high, number))


def _bundled_specs(mcp: Mapping[str, Any]) -> tuple[MaiBotPluginSpec, ...]:
    """未指定插件时的默认：只加载内置的 AnySearch MaiBot 插件（mcp 段作为它的插件配置）。"""
    return (
        MaiBotPluginSpec(
            id="anysearch",
            path=BUNDLED_ANYSEARCH_PLUGIN,
            class_name="AnySearchPlugin",
            enabled=True,
            config=dict(mcp),
        ),
    )


def _resolve_plugin_path(value: Any, label: str) -> str:
    """内置插件的 ID / 类名 -> 相对路径；其余当成用户给的路径原样返回。"""
    path = _as_str(value, label)
    if not path:
        return ""
    canonical = BUNDLED_PLUGIN_ALIASES.get(path.casefold())
    return BUNDLED_PLUGINS[canonical] if canonical else path


def _default_plugin_id(declared: str, path: str) -> str:
    """别名（"AnySearch"/"AnySearchPlugin"）统一落到规范 id，别暴露文件名 stem。"""
    return BUNDLED_PLUGIN_ALIASES.get(declared.casefold(), Path(path).stem)


def _parse_plugins(value: Any, mcp: Mapping[str, Any]) -> tuple[MaiBotPluginSpec, ...]:
    raw = value
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()] or None
    # 未指定，或显式写了空数组：都按默认处理（停用整座桥请用 enabled_bridge=false）
    if raw is None or (isinstance(raw, list) and not raw):
        return _bundled_specs(mcp)
    if not isinstance(raw, list):
        raise ConfigError("sdk.plugins 必须是数组")

    specs: list[MaiBotPluginSpec] = []
    for index, item in enumerate(raw):
        label = f"sdk.plugins[{index}]"
        if isinstance(item, str):
            if not item.strip():
                raise ConfigError(f"{label} 不能是空字符串")
            path = _resolve_plugin_path(item, label)
            specs.append(
                MaiBotPluginSpec(
                    id=_default_plugin_id(item.strip(), path), path=path, config=dict(mcp)
                )
            )
            continue
        entry = _as_mapping(item, label)
        declared = _as_str(entry.get("path"), f"{label}.path")
        if not declared:
            raise ConfigError(f"{label}.path 不能为空")
        path = _resolve_plugin_path(entry.get("path"), f"{label}.path")
        specs.append(
            MaiBotPluginSpec(
                id=_as_str(entry.get("id") or _default_plugin_id(declared, path), f"{label}.id"),
                path=path,
                class_name=_as_str(entry.get("class_name"), f"{label}.class_name"),
                enabled=_as_bool(entry.get("enabled", True), f"{label}.enabled"),
                config=_as_mapping(entry.get("config"), f"{label}.config"),
            )
        )
    return tuple(specs)


def _parse_anysearch(mcp: Mapping[str, Any]) -> AnySearchSettings:
    endpoint = _as_str(mcp.get("endpoint") or DEFAULT_ENDPOINT, "anysearch.endpoint") or DEFAULT_ENDPOINT
    if not endpoint.startswith(("http://", "https://")):
        raise ConfigError("anysearch.endpoint 必须以 http:// 或 https:// 开头")

    token, token_source = _resolve_token(mcp)
    headers: dict[str, str] = {}
    for raw_key, raw_value in _as_mapping(mcp.get("headers"), "anysearch.headers").items():
        header_key = _as_str(raw_key, "anysearch.headers 键")
        if header_key:
            headers[header_key] = _as_str(raw_value, "anysearch.headers 值")

    mode = _as_str(mcp.get("description_mode") or DEFAULT_DESCRIPTION_MODE, "anysearch.description_mode")
    if mode not in DESCRIPTION_MODES:
        raise ConfigError(f"anysearch.description_mode 只能是 {DESCRIPTION_MODES} 之一，当前是 {mode!r}")

    timeout = float(
        _as_int(mcp.get("timeout_seconds") or int(DEFAULT_TIMEOUT_SECONDS), "anysearch.timeout_seconds", low=1, high=600)
    )
    return AnySearchSettings(
        endpoint=endpoint,
        token=token,
        token_source=token_source,
        headers=headers,
        tools=_parse_tools(mcp.get("tools")),
        description_mode=mode,
        timeout_seconds=timeout,
        max_chars=_as_int(mcp.get("max_chars") or DEFAULT_MAX_CHARS, "anysearch.max_chars", low=500, high=200000),
        max_results=_as_int(mcp.get("max_results") or DEFAULT_MAX_RESULTS, "anysearch.max_results", low=1, high=10),
    )


def _parse_tools(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_TOOLS
    if isinstance(raw, str):
        items = [item.strip() for item in raw.split(",") if item.strip()]
    elif isinstance(raw, list):
        items = [name for name in (_as_str(item, "anysearch.tools 项") for item in raw) if name]
    else:
        raise ConfigError("anysearch.tools 必须是数组，或用逗号分隔的字符串")

    known = set(schemas.captured_names()) | set(DEFAULT_TOOLS)
    unknown = [name for name in items if name not in known]
    if unknown:
        raise ConfigError(f"anysearch.tools 里有未捕获的工具: {unknown}（可用: {sorted(known)}）")
    return tuple(dict.fromkeys(items)) or DEFAULT_TOOLS


def _resolve_token(mcp: Mapping[str, Any]) -> tuple[str, str]:
    """按 api_key -> api_key_env 环境变量 -> ANYSEARCH_API_KEY 顺序取密钥。"""
    direct = _as_str(mcp.get("api_key"), "anysearch.api_key")
    if direct:
        return direct, "config"
    env_name = _as_str(mcp.get("api_key_env") or DEFAULT_API_KEY_ENV, "anysearch.api_key_env")
    if env_name and os.environ.get(env_name):
        return os.environ[env_name], f"env:{env_name}"
    return "", "none"
