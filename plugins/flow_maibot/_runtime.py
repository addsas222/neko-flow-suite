"""flow_maibot 的 N.E.K.O. 运行时入口。

分层：``_shared/`` 是可独立测试的纯标准库实现（含 MaiBot SDK 公开接口的重写与
MCP 客户端）；这里只做进程内编排：

* 用宿主配置构造 :class:`MaiBotBridge`，把 :class:`AnySearchGateway` 作为后端
  与 ``capability_handler`` 接进 MaiBot 插件的 ctx
* 把桥产出的 :class:`ToolBinding` 注册成 NEKO 原生 LLM 工具（宿主签名协商）
* 给 Hosted UI 面板提供 ``@ui.context`` 状态与两个入口动作

任何一步失败都收敛成状态里的 ``problems``，绝不把异常抛给宿主。
"""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

try:  # 在 N.E.K.O 宿主内
    from plugin.sdk.plugin import (
        Err,
        NekoPluginBase,
        Ok,
        lifecycle,
        neko_plugin,
        plugin_entry,
        tr,
        ui,
    )
except ImportError:  # 允许在套件仓库内单独导入做静态检查
    NekoPluginBase = object  # type: ignore[assignment,misc]

    def Ok(data: Any) -> dict[str, Any]:  # type: ignore[assignment]
        return {"ok": True, "data": data}

    def Err(error: Any) -> dict[str, Any]:  # type: ignore[assignment]
        return {"ok": False, "error": str(error)}

    def neko_plugin(cls: type) -> type:  # type: ignore[assignment]
        return cls

    def plugin_entry(**kwargs: Any):  # type: ignore[assignment]
        def wrap(func):  # type: ignore[no-untyped-def]
            func._plugin_entry = kwargs  # type: ignore[attr-defined]
            return func

        return wrap

    def lifecycle(**kwargs: Any):  # type: ignore[assignment]
        def wrap(func):  # type: ignore[no-untyped-def]
            func._lifecycle = kwargs  # type: ignore[attr-defined]
            return func

        return wrap

    def tr(text: str, **kwargs: Any) -> str:  # type: ignore[assignment]
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError, ValueError):
            return text

    class _UiFallback:
        """ui.context / ui.action 的本地兜底，签名与插件 SDK 一致。"""

        @staticmethod
        def context(**kwargs: Any):
            def wrap(func):  # type: ignore[no-untyped-def]
                func._ui_context = kwargs  # type: ignore[attr-defined]
                return func

            return wrap

        @staticmethod
        def action(**kwargs: Any):
            def wrap(func):  # type: ignore[no-untyped-def]
                func._ui_action = kwargs  # type: ignore[attr-defined]
                return func

            return wrap

    ui = _UiFallback  # type: ignore[assignment]

from ._shared import schemas  # noqa: E402
from ._shared.anysearch import AnySearchGateway  # noqa: E402
from ._shared.bridge import MaiBotBridge, ToolBinding  # noqa: E402
from ._shared.errors import BridgeError, CapabilityNotBridgedError  # noqa: E402
from ._shared.settings import BUNDLED_ANYSEARCH_PLUGIN, BridgeSettings  # noqa: E402

#: plugin.toml 里 ``[[plugin.ui.panel]]`` 的 context id
PANEL_CONTEXT = "maibot"
#: 桥给 MaiBot ctx 的 capability_handler 用的命名空间
CAPABILITY = "maibot"
#: 宿主配置缺省落在插件数据目录下的这个文件
CONFIG_FILE = "config.json"
#: 捕获到的上游 schema 归属的 MaiBot 插件 id
SCHEMA_PLUGIN_ID = "anysearch"
#: 宿主侧可能存在的 LLM 工具注册入口，按优先级探测。
REGISTER_HINTS = (
    "register_llm_tool",
    "register_tool",
    "register_capability",
    "register_dynamic_entry",
)
#: 上面的反操作；宿主没提供时只清本地账本。
UNREGISTER_HINTS = (
    "unregister_llm_tool",
    "unregister_tool",
    "unregister_capability",
    "unregister_dynamic_entry",
)

#: 参数名别名：宿主签名在离线环境里无法核对，所以只把值喂给它认得的那个名字。
ARG_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "tool_name", "id", "entry_id", "tool"),
    "description": ("description", "desc", "summary", "documentation"),
    "parameters": (
        "parameters",
        "schema",
        "input_schema",
        "parameters_schema",
        "args_schema",
    ),
    "handler": ("handler", "callback", "capability_handler", "fn", "invoke", "executor"),
    "capability": ("capability", "capability_name", "group", "namespace", "prefix"),
}


class CapturedSchemaSource:
    """把上游捕获到的 schema 交给桥，优先级高于装饰器元数据。

    只在组件名命中 ``captured/anysearch_tools.json`` 时给结果；其余组件返回
    ``None``，让桥按「装饰器元数据 -> 函数签名」自己判断。
    """

    def __init__(self, plugin_id: str = SCHEMA_PLUGIN_ID, *, mode: str = "brief") -> None:
        self._plugin_id = str(plugin_id or "").strip()
        self._mode = "full" if str(mode or "") == "full" else "brief"

    @property
    def mode(self) -> str:
        return self._mode

    def lookup(self, plugin_id: str, component: str) -> dict[str, Any] | None:
        if self._plugin_id and str(plugin_id or "").strip() != self._plugin_id:
            return None
        name = str(component or "").strip()
        if name not in schemas.CAPTURED_TOOLS:
            return None
        return {
            "description": schemas.llm_description(name, mode=self._mode),
            "parameters": schemas.input_schema(name),
        }


# --------------------------------------------------------------------------- #
# 宿主 LLM 工具注册协商
# --------------------------------------------------------------------------- #
def _bind_arguments(
    target: Callable[..., Any], values: Sequence[tuple[str, Any]]
) -> tuple[dict[str, Any], set[str]] | None:
    """把 (规范名, 值) 映射到宿主形参上。

    返回 (调用参数, 实际绑定成功的规范名)。宿主签名在离线环境里无法核对，所以
    先按别名匹配形参名，匹配不上的按顺序填剩下的位置槽；一个都填不上就返回
    ``None``，让调用方记 problem 而不是瞎传。
    """
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return None
    parameters = list(signature.parameters.values())
    if any(item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters):
        return dict(values), {canonical for canonical, _ in values}

    keyword = {
        item.name
        for item in parameters
        if item.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    bound: dict[str, Any] = {}
    used: set[str] = set()
    spare: list[tuple[str, Any]] = []
    for canonical, value in values:
        alias = next(
            (name for name in ARG_ALIASES.get(canonical, (canonical,)) if name in keyword),
            None,
        )
        if alias is None:
            spare.append((canonical, value))
            continue
        bound[alias] = value
        used.add(canonical)
    slots = [
        item.name
        for item in parameters
        if item.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and item.name not in bound
    ]
    for (canonical, value), slot in zip(spare, slots):
        bound[slot] = value
        used.add(canonical)
    return bound, used

class LlmToolRegistry:
    """NEKO LLM 工具的注册 / 卸载协商层。

    宿主的 LLM 工具 API 在离线环境里无法核对，因此这里不绑定某一个具体签名：
    按 :data:`REGISTER_HINTS` / :data:`UNREGISTER_HINTS` 在 ctx 与插件实例上
    探测入口，再用参数名别名把 name / description / parameters / handler /
    capability 映射到宿主认得的形参上。探测或注册失败只记 problem，绝不把异常
    抛给宿主调用方——桥接层不能让面板点一下就崩。
    """

    def __init__(self, *, logger: Any = None) -> None:
        self._logger = logger
        self._register: Callable[..., Any] | None = None
        self._unregister: Callable[..., Any] | None = None
        self._handlers: dict[str, Callable[..., Any]] = {}
        self.problems: list[str] = []

    # -- 探测 -------------------------------------------------------- #

    @property
    def mechanism(self) -> str:
        """面板展示用的协商结果描述。"""
        if self._register is None:
            return "unavailable"
        owner = getattr(self._register, "__self__", None)
        prefix = f"{type(owner).__name__}." if owner is not None else ""
        name = getattr(self._register, "__name__", "register_llm_tool")
        return f"{prefix}{name}"

    @property
    def registered(self) -> list[str]:
        return sorted(self._handlers)

    def attach(self, *owners: Any) -> str:
        """探测宿主入口；无论结果如何都返回机制名。"""
        self._register = self._find(owners, REGISTER_HINTS)
        self._unregister = self._find(owners, UNREGISTER_HINTS)
        if self._register is None:
            self.problems.append(
                "宿主缺少 LLM 工具注册入口（已探测 "
                + "/".join(REGISTER_HINTS)
                + "）；MaiBot 工具已加载，但不会进入模型工具表"
            )
            if self._logger is not None:
                self._logger.warning("宿主缺少 LLM 工具注册入口，工具只落在桥内")
        return self.mechanism

    @staticmethod
    def _find(owners: Sequence[Any], hints: Sequence[str]) -> Callable[..., Any] | None:
        for owner in owners:
            if owner is None:
                continue
            for hint in hints:
                target = getattr(owner, hint, None)
                if callable(target):
                    return target
        return None

    # -- 注册 / 卸载 -------------------------------------------------- #

    def register(self, binding: ToolBinding, handler: Callable[..., Any]) -> tuple[bool, str]:
        if self._register is None:
            return False, "no_register_entrypoint"
        values: tuple[tuple[str, Any], ...] = (
            ("name", binding.name),
            ("description", binding.description),
            ("parameters", binding.parameters),
            ("handler", handler),
            ("capability", CAPABILITY),
        )
        bound = _bind_arguments(self._register, values)
        if bound is None or "handler" not in bound[1]:
            self.problems.append(f"宿主注册入口的形参与工具契约不匹配，未注册 {binding.name}")
            return False, "signature_mismatch"
        try:
            self._register(**bound[0])
        except Exception as exc:  # noqa: BLE001 - 宿主拒绝注册也要保持面板可用
            self.problems.append(f"注册 {binding.name} 失败：{type(exc).__name__}")
            return False, type(exc).__name__
        self._handlers[binding.name] = handler
        return True, "registered"

    def unregister(self, name: str) -> bool:
        """撤销一个已注册工具；宿主没有卸载入口时只清本地账本。"""
        self._handlers.pop(name, None)
        if self._unregister is None:
            if name:
                self.problems.append(f"宿主缺少卸载入口，{name} 已从账本移除")
            return False
        bound = _bind_arguments(self._unregister, (("name", name),))
        if bound is None or "name" not in bound[1]:
            return False
        try:
            self._unregister(**bound[0])
        except Exception as exc:  # noqa: BLE001 - 卸载失败只影响日志
            self.problems.append(f"卸载 {name} 失败：{type(exc).__name__}")
            return False
        return True

    def unregister_all(self) -> None:
        for name in self.registered:
            self.unregister(name)

    def reset(self) -> None:
        """清掉协商结果与问题；宿主对象变化（重新注入 ctx）时使用。"""
        self.unregister_all()
        self._register = None
        self._unregister = None
        self.problems.clear()

# --------------------------------------------------------------------------- #
# 进程内编排
# --------------------------------------------------------------------------- #
class MaibotRuntime:
    """宿主进程里的 MaiBot 桥：加载插件、注册 LLM 工具、提供状态。

    任何一步失败都收敛成 ``status()["problems"]`` 里的一条脱敏摘要：宿主面板
    可以随时重载，但桥自身绝不把异常抛给宿主。
    """

    def __init__(
        self,
        *,
        base_dir: Path | str,
        data_root: Path | str | None = None,
        logger: Any = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self._data_root = Path(data_root).resolve() if data_root else self.base_dir / "data"
        self._logger = logger or logging.getLogger("flow_maibot.runtime")
        self._bridge: MaiBotBridge | None = None
        self._settings: BridgeSettings | None = None
        self._config: dict[str, Any] = {}
        self._registry = LlmToolRegistry(logger=self._logger)
        self.attached = False
        self.last_error = ""

    # -- 状态 -------------------------------------------------------- #

    @property
    def registry(self) -> LlmToolRegistry:
        return self._registry

    @property
    def bridge(self) -> MaiBotBridge | None:
        return self._bridge

    def tool_definitions(self) -> list[dict[str, Any]]:
        return self._bridge.tools() if self._bridge is not None else []

    def status(self) -> dict[str, Any]:
        """面板与测试用的完整状态；problems 是脱敏后的摘要。"""
        bridge = self._bridge
        problems = list(self._registry.problems)
        if bridge is not None:
            problems += bridge.problems
        return {
            "attached": self.attached,
            "mechanism": self._registry.mechanism,
            "registered": self._registry.registered,
            "tool_count": len(self.tool_definitions()),
            "tools": self.tool_definitions(),
            "plugins": bridge.component_list() if bridge is not None else [],
            "backend": bridge.backend_info() if bridge is not None else {},
            "config": self.config_summary(),
            "problems": problems,
            "last_error": self.last_error,
        }

    def config_summary(self) -> dict[str, Any]:
        """面板用的配置摘要：只给非敏感字段，绝不回显密钥。"""
        if self._settings is None:
            return {}
        anysearch = self._settings.anysearch
        return {
            "enabled": self._settings.enabled,
            "strict_sdk": self._settings.strict_sdk,
            "plugin_ids": [spec.id for spec in self._settings.plugins],
            "endpoint": anysearch.endpoint,
            "endpoint_host": _host_of(anysearch.endpoint),
            "token_source": anysearch.token_source,
            "tools": list(anysearch.tools),
            "description_mode": anysearch.description_mode,
            "timeout_seconds": anysearch.timeout_seconds,
            "max_chars": anysearch.max_chars,
            "max_results": anysearch.max_results,
        }
    # -- 生命周期 ---------------------------------------------------- #

    async def attach(self, config: Any = None, *, owners: Sequence[Any] = ()) -> dict[str, Any]:
        """按配置把 MaiBot 插件加载起来，并注册对应的 NEKO LLM 工具。"""
        self.attached = False
        self.last_error = ""
        merged = self._merge_config(config)
        try:
            settings = BridgeSettings.from_config(merged, base_dir=self.base_dir)
        except BridgeError as exc:
            self.last_error = exc.message
            self._registry.problems.append(exc.message)
            return self.status()

        self._settings = settings
        self._registry.reset()
        self._registry.attach(*owners)

        bridge = MaiBotBridge(
            settings,
            base_dir=self.base_dir,
            logger=self._logger,
            backend=_build_backend(settings),
            capability_handler=self.capability_handler,
            schema_sources=[CapturedSchemaSource(mode=settings.anysearch.description_mode)],
            data_root=self._data_root,
        )
        try:
            await bridge.load()
        except Exception as exc:  # noqa: BLE001 - 加载失败收敛成状态
            self.last_error = type(exc).__name__
            self._registry.problems.append(f"桥加载失败：{type(exc).__name__}")
            return self.status()
        self._bridge = bridge
        self._register_tools()
        self.attached = settings.enabled and bool(bridge.tool_bindings())
        return self.status()

    async def detach(self) -> dict[str, Any]:
        """卸载 MaiBot 插件并撤销已注册的 LLM 工具。"""
        if self._bridge is not None:
            try:
                await self._bridge.unload()
            except Exception as exc:  # noqa: BLE001 - 卸载失败只影响状态
                self.last_error = type(exc).__name__
                self._registry.problems.append(f"桥卸载失败：{type(exc).__name__}")
        self._bridge = None
        self._registry.unregister_all()
        self.attached = False
        return self.status()

    async def refresh(
        self, config: Any = None, *, owners: Sequence[Any] = ()
    ) -> dict[str, Any]:
        """重新采集状态：给了配置就整体重载，否则只补注册漏掉的工具。"""
        if self._bridge is None or config is not None:
            return await self.attach(config, owners=owners)
        self._register_tools()
        return self.status()

    async def invoke(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """LLM 工具调用入口：名字必须是桥注册过的 NEKO 工具名。"""
        bridge = self._bridge
        if bridge is None:
            return {
                "is_error": True,
                "error": "bridge_not_loaded",
                "output": {"reason": "MaiBot 桥尚未载入"},
            }
        try:
            return await bridge.invoke_tool(name, dict(arguments or {}))
        except BridgeError as exc:
            return {"is_error": True, "error": "bridge_error", "output": {"reason": exc.message}}
    # -- 内部 -------------------------------------------------------- #

    def _register_tools(self) -> None:
        bridge = self._bridge
        if bridge is None:
            return
        for binding in bridge.tool_bindings():
            handler = _make_handler(bridge, binding.name)
            self._registry.register(binding, handler)

    async def capability_handler(
        self, plugin_id: str, capability: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        """MaiBot 插件 ctx.<capability>() 的落点：只桥已知的几类，其余明确报错。"""
        name = str(capability or "").strip().lower()
        bridge = self._bridge
        if bridge is None:
            raise CapabilityNotBridgedError(f"ctx.{name} 不可用：MaiBot 桥尚未载入")
        data = dict(payload or {})
        if name in {"tool.get_definitions", "tool_definitions", "get_definitions"}:
            return bridge.tool_definitions_for(plugin_id)
        if name in {"tool.list", "tools"}:
            return {"tools": bridge.tools()}
        if name in {"tool.call", "invoke"}:
            target = str(data.get("tool") or data.get("name") or "")
            return await bridge.invoke_tool(target, data.get("arguments") or data)
        raise CapabilityNotBridgedError(f"ctx.{name} 未桥接到 NEKO 宿主")

    def _merge_config(self, config: Any) -> dict[str, Any]:
        """宿主配置 + ``data/config.json`` 合并（宿主优先），再归一到桥的配置形态。"""
        merged: dict[str, Any] = {}
        for source in (self._read_config_file(), _as_plain_mapping(config)):
            for key, value in source.items():
                if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
        merged = _normalize_config(merged)
        self._config = merged
        return merged

    def _read_config_file(self) -> dict[str, Any]:
        path = self._data_root / CONFIG_FILE
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self._registry.problems.append(f"{CONFIG_FILE} 解析失败：{type(exc).__name__}")
            return {}
        return _as_plain_mapping(data)


# --------------------------------------------------------------------------- #
# 模块级小工具
# --------------------------------------------------------------------------- #
def _make_handler(bridge: MaiBotBridge, name: str) -> Callable[..., Any]:
    """生成稳定的工具 handler：宿主侧签名随协商变化，实现始终走桥。"""

    async def handler(arguments: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        payload = dict(arguments or {})
        payload.update(kwargs)
        return await bridge.invoke_tool(name, payload)

    handler.__name__ = f"flow_maibot_{_slug_of(name)}"
    return handler


def _build_backend(settings: BridgeSettings) -> AnySearchGateway:
    return AnySearchGateway(settings.anysearch)


def _as_plain_mapping(value: Any) -> dict[str, Any]:
    """宿主配置可能是 dict / JSON 字符串 / None，统一成字符串键的字典。"""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
        except ValueError:
            return {}
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _slug_of(name: str) -> str:
    """工具名 -> Python 标识符，用于 handler 的 __name__。"""
    return "".join(item if item.isalnum() else "_" for item in str(name)).strip("_")


def _host_of(endpoint: str) -> str:
    """endpoint -> host，面板展示用；不带 scheme 时原样返回。"""
    text = str(endpoint or "")
    marker = "://"
    if marker not in text:
        return text
    tail = text.split(marker, 1)[1]
    return tail.split("/", 1)[0]


# --------------------------------------------------------------------------- #
# 宿主配置归一（面板/配置文件 -> BridgeSettings.from_config 认得的形态）
# --------------------------------------------------------------------------- #
#: 平铺键 -> ``sdk.*``；``[maibot]`` 段和点号键都能命中。
SDK_KEY_ALIASES: dict[str, str] = {
    "enabled": "enabled_bridge",
    "bridge": "enabled_bridge",
    "bridge_enabled": "enabled_bridge",
    "enabled_bridge": "enabled_bridge",
    "strict": "strict_sdk",
    "strict_sdk": "strict_sdk",
    "plugins": "plugins",
    "plugin_ids": "plugins",
    "plugin_list": "plugins",
    "plugin_paths": "plugins",
}

#: 平铺键 / ``anysearch.*`` 点号键 -> ``anysearch.*``。
ANYSEARCH_KEY_ALIASES: dict[str, str] = {
    "endpoint": "endpoint",
    "url": "endpoint",
    "api_key": "api_key",
    "token": "api_key",
    "key": "api_key",
    "api_key_env": "api_key_env",
    "token_env": "api_key_env",
    "headers": "headers",
    "tools": "tools",
    "description_mode": "description_mode",
    "timeout_seconds": "timeout_seconds",
    "timeout": "timeout_seconds",
    "max_chars": "max_chars",
    "max_results": "max_results",
}

#: ``description_mode`` 只认 brief / full，其余常见写法归一旁路。
DESCRIPTION_MODE_ALIASES: dict[str, str] = {
    "brief": "brief",
    "short": "brief",
    "minimal": "brief",
    "full": "full",
    "detailed": "full",
}

#: 内置的 MaiBot 插件：配置里写 ID / 类名 / 文件名都能命中。
BUNDLED_PLUGINS: dict[str, dict[str, str]] = {
    "anysearch": {
        "id": "anysearch",
        "path": BUNDLED_ANYSEARCH_PLUGIN,
        "class_name": "AnySearchPlugin",
    },
    "anysearchplugin": {
        "id": "anysearch",
        "path": BUNDLED_ANYSEARCH_PLUGIN,
        "class_name": "AnySearchPlugin",
    },
}


def _bundled_plugin(text: Any) -> dict[str, str] | None:
    """插件 ID / 类名 / 文件名 -> 内置插件 spec；不认识就返回 ``None``。"""
    key = "".join(char for char in str(text or "").lower() if char.isalnum())
    return BUNDLED_PLUGINS.get(key)


def _normalize_plugin_item(item: Any) -> Any:
    """单个插件条目：写 ID 就补全内置路径，其余原样交给配置层校验。"""
    if isinstance(item, Mapping):
        entry = _as_plain_mapping(item)
        plugin_id = str(entry.get("id") or "").strip()
        path = str(entry.get("path") or "").strip()
        bundled = _bundled_plugin(plugin_id) or (_bundled_plugin(path) if path else None)
        if bundled is not None:
            entry.setdefault("id", bundled["id"])
            entry.setdefault("path", bundled["path"])
            entry.setdefault("class_name", bundled["class_name"])
        return entry
    text = str(item).strip()
    if not text:
        return None
    bundled = _bundled_plugin(text)
    return dict(bundled) if bundled is not None else text


def _normalize_plugins(value: Any) -> Any:
    """插件清单 -> 配置层认得的形态；结构不认识就原样返回，让配置层报错。"""
    if value is None:
        return []
    if isinstance(value, str):
        items: list[Any] = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = list(value)
    else:
        return value
    normalized = [entry for entry in (_normalize_plugin_item(item) for item in items) if entry]
    return normalized


def _unwrap_section(raw: dict[str, Any]) -> dict[str, Any]:
    """宿主可能把插件配置整段包在插件 id 下，这里拆一层。"""
    if len(raw) != 1:
        return raw
    key = str(next(iter(raw))).strip().lower()
    value = next(iter(raw.values()))
    if key in {PANEL_CONTEXT, "flow_maibot"} and isinstance(value, Mapping):
        return _as_plain_mapping(value)
    return raw


def _normalize_config(config: Any) -> dict[str, Any]:
    """把宿主配置归一成 :meth:`BridgeSettings.from_config` 认得的形态。

    三种写法都收：

    1. ``{"sdk": {...}, "anysearch": {...}}``：桥的原生形态，原样透传；
    2. ``[maibot]`` 段平铺：``{"enabled": true, "plugins": ["AnySearch"], ...}``；
    3. 点号平铺：``{"anysearch.endpoint": "...", "enabled": false}``。

    另外把 ``token`` 归一到 ``api_key``、把 ``description_mode`` 的常见别名归一到
    ``brief`` / ``full``、把插件 ID 归一到内置插件路径。认得清的坏值丢掉，让字段
    回到默认值，而不是让整个桥起不来；结构坏了才原样交给配置层报错。
    """
    raw = _unwrap_section(_as_plain_mapping(config))
    sdk = _as_plain_mapping(raw.get("sdk"))
    anysearch = _as_plain_mapping(raw.get("anysearch"))

    for key, value in raw.items():
        lowered = str(key).strip().lower()
        if lowered.startswith("anysearch."):
            section, alias = anysearch, ANYSEARCH_KEY_ALIASES.get(lowered.split(".", 1)[1])
        elif lowered in SDK_KEY_ALIASES:
            section, alias = sdk, SDK_KEY_ALIASES[lowered]
        elif lowered in ANYSEARCH_KEY_ALIASES:
            section, alias = anysearch, ANYSEARCH_KEY_ALIASES[lowered]
        else:
            continue
        if alias is not None and alias not in section:
            section[alias] = value

    mode = anysearch.get("description_mode")
    if isinstance(mode, str):
        anysearch["description_mode"] = DESCRIPTION_MODE_ALIASES.get(mode.strip().lower(), "brief")
    # token_source 由配置层自己推导（api_key / env / none），配置里写什么都不算。
    for section in (sdk, anysearch):
        for derived in ("token_source", "secret", "api_secret"):
            section.pop(derived, None)
    if "plugins" in sdk:
        sdk["plugins"] = _normalize_plugins(sdk["plugins"])

    normalized: dict[str, Any] = {}
    if sdk:
        normalized["sdk"] = sdk
    if anysearch:
        normalized["anysearch"] = anysearch
    return normalized

# --------------------------------------------------------------------------- #
# 插件入口
# --------------------------------------------------------------------------- #
#: 宿主 ctx 上可能承载插件配置的属性名，按优先级探测。
HOST_CONFIG_ATTRS = ("config", "plugin_config", "settings", "plugin_config_data", "tool_config")


def host_config(ctx: Any) -> dict[str, Any]:
    """从宿主 ctx 取插件配置；离线环境下取不到就返回空配置。"""
    for name in HOST_CONFIG_ATTRS:
        value = getattr(ctx, name, None)
        if isinstance(value, Mapping) and value:
            return _as_plain_mapping(value)
    return {}


def _panel_status(status: dict[str, Any]) -> dict[str, Any]:
    """面板用的状态瘦身：工具描述截断，其余原样。"""
    tools: list[dict[str, Any]] = []
    for item in status.get("tools", []):
        description = str(item.get("description", ""))
        tools.append(
            {
                "name": item.get("name", ""),
                "description": description[:200],
                "plugin_id": item.get("plugin_id", ""),
                "component": item.get("component", ""),
                "schema_source": item.get("schema_source", ""),
            }
        )
    return {
        "attached": bool(status.get("attached")),
        "mechanism": status.get("mechanism", ""),
        "tool_count": status.get("tool_count", len(tools)),
        "tools": tools,
        "plugins": status.get("plugins", []),
        "backend": status.get("backend", {}),
        "config": status.get("config", {}),
        "problems": status.get("problems", []),
        "last_error": status.get("last_error", ""),
    }


@neko_plugin
class FlowMaibotPlugin(NekoPluginBase):
    """MaiBot 插件工具桥：把 MaiBot @Tool 注册成 NEKO 原生 LLM 工具。"""

    def __init__(self, ctx: Any = None) -> None:
        super().__init__(ctx)
        self._runtime: MaibotRuntime | None = None

    # -- 运行时 ------------------------------------------------------ #

    @property
    def runtime(self) -> MaibotRuntime:
        if self._runtime is None:
            self._runtime = MaibotRuntime(
                base_dir=Path(__file__).resolve().parent,
                data_root=self._data_root(),
                logger=getattr(self, "logger", None),
            )
        return self._runtime

    def _data_root(self) -> Path:
        """优先用宿主给的数据目录；宿主没提供就退回插件内 data/。"""
        fallback = Path(__file__).resolve().parent / "data"
        getter = getattr(self, "data_path", None)
        if not callable(getter):
            return fallback
        try:
            return Path(getter("maibot"))
        except Exception:  # noqa: BLE001 - 宿主没给数据目录就用插件内目录
            return fallback

    def _hosts(self) -> tuple[Any, ...]:
        """LLM 工具注册入口的探测对象：先宿主 ctx，再插件实例。"""
        return (getattr(self, "ctx", None), self)
    # -- 生命周期 ---------------------------------------------------- #

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        """启动即按宿主配置把桥建起来；失败只进状态，不阻断宿主启动。"""
        status = await self.runtime.attach(
            host_config(getattr(self, "ctx", None)), owners=self._hosts()
        )
        self.logger.info(
            "flow_maibot 桥就绪：attached=%s tools=%s mechanism=%s",
            status.get("attached"),
            status.get("tool_count"),
            status.get("mechanism"),
        )
        return {
            "attached": bool(status.get("attached")),
            "tools": [item["name"] for item in status.get("tools", [])],
            "mechanism": status.get("mechanism", ""),
            "problems": status.get("problems", []),
        }

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        """卸载 MaiBot 插件并撤销 LLM 工具注册。"""
        status = await self.runtime.detach()
        self.logger.info("flow_maibot 桥已卸载")
        return {"attached": False, "problems": status.get("problems", [])}

    # -- UI ---------------------------------------------------------- #

    @ui.context(id=PANEL_CONTEXT)
    async def maibot_context(self) -> dict:
        """plugin.toml 里 context = "maibot" 的面板状态。"""
        return _panel_status(self.runtime.status()) | {
            "labels": {
                "title": tr("maibot.title", default="MaiBot 工具桥"),
                "subtitle": tr(
                    "maibot.subtitle",
                    default="把 MaiBot 插件工具注册成 NEKO 原生 LLM 工具。",
                ),
                "attach": tr("maibot.action.attach", default="载入 / 卸载"),
                "refresh": tr("maibot.action.refresh", default="刷新状态"),
                "tools": tr("maibot.tools", default="已注册工具"),
                "problems": tr("maibot.problems", default="问题清单"),
            }
        }
    @ui.action(id="attach", label="桥接开关")
    @plugin_entry(
        id="attach",
        name="桥接开关",
        description="载入或卸载 MaiBot 插件，并注册/注销对应的 NEKO LLM 工具。",
        kind="service",
    )
    async def attach(
        self,
        action: Annotated[
            str, "load = 载入并注册工具；unload = 卸载并撤销注册"
        ] = "load",
    ) -> dict:
        try:
            if str(action).strip().lower() in {"unload", "off", "stop", "detach"}:
                status = await self.runtime.detach()
            else:
                status = await self.runtime.attach(
                    host_config(getattr(self, "ctx", None)), owners=self._hosts()
                )
            return Ok(_panel_status(status))
        except Exception as exc:  # noqa: BLE001 - 面板动作必须转 Err
            return Err(str(exc))

    @ui.action(id="refresh", label="刷新状态")
    @plugin_entry(
        id="refresh",
        name="刷新状态",
        description="重新采集桥接状态：MaiBot 插件、已注册工具、后端与问题清单。",
        kind="service",
    )
    async def refresh(self) -> dict:
        try:
            status = await self.runtime.refresh(
                host_config(getattr(self, "ctx", None)), owners=self._hosts()
            )
            return Ok(_panel_status(status))
        except Exception as exc:  # noqa: BLE001 - 面板动作必须转 Err
            return Err(str(exc))


__all__ = ["FlowMaibotPlugin", "MaibotRuntime"]