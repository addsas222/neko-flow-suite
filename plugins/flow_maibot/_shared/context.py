"""MaiBot PluginContext 的兼容代理。

MaiBot 插件里到处是 ``self.ctx.xxx.yyy(...)``。NEKO 宿主是另一套能力体系，
这一层把 "ctx.<capability>.<method>(...)" 翻译成一次网关回调：

    ``await gateway(f"{capability}.{method}", arguments)``

网关由 NEKO 侧提供（_runtime.py），因此：
    * strict 模式：不支持的能力直接抛 CapabilityNotBridgedError
    * degraded 模式（默认）：记一条日志后返回 None，插件继续跑

本文件只做"形状"兼容，不含任何 MaiBot SDK 代码（见 NOTICE.md）。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import CapabilityNotBridgedError

Gateway = Callable[[str, dict[str, Any]], Awaitable[Any]]
Invoker = Callable[[str, dict[str, Any]], Awaitable[Any]]

#: MaiBot SDK ctx 的能力对象（见 maibot_sdk/context/capability_types.py）
CAPABILITY_NAMES: tuple[str, ...] = (
    "api",
    "chat",
    "component",
    "config",
    "db",
    "emoji",
    "frequency",
    "gateway",
    "knowledge",
    "llm",
    "maisaka",
    "message",
    "person",
    "render",
    "send",
    "statistics",
    "tool",
)

#: call_host_method 白名单（与 SDK PluginContext.call_host_method 一致）
ALLOWED_HOST_METHODS: frozenset[str] = frozenset(
    {
        "chat_message.create",
        "chat_message.create_filtered",
        "chat.get",
        "chat.get_all",
        "person.get_id",
        "person.get_name",
        "person.get_person_id",
        "person.get_person_name",
        "emoji.get_all",
        "emoji.get_info",
        "emoji.get_desc",
        "emoji.get_all_desc",
    }
)


@dataclass(frozen=True)
class PluginPaths:
    """MaiBot 约定的插件数据目录。"""

    data_dir: str = "data/plugins"
    runtime_dir: str = "temp/plugins"

    def resolve(self, plugin_id: str, *, data_root: Path | str | None = None) -> tuple[Path, Path]:
        base = Path(data_root) if data_root else Path.cwd()
        return base / self.data_dir / plugin_id, base / self.runtime_dir / plugin_id


class BridgedLogger:
    """把 MaiBot 风格的 logger 调用接到标准库 logging。"""

    def __init__(self, logger: logging.Logger, *, prefix: str = "") -> None:
        self._logger = logger
        self._prefix = prefix

    def _render(self, message: str) -> str:
        return f"{self._prefix}{message}" if self._prefix else str(message)

    def can_send(self) -> bool:
        return True

    def can_send_notice(self) -> bool:
        return True

    def debug(self, message: str, *args: Any) -> None:
        self._logger.debug(self._render(message), *args)

    def info(self, message: str, *args: Any) -> None:
        self._logger.info(self._render(message), *args)

    def success(self, message: str, *args: Any) -> None:
        self._logger.info(self._render(message), *args)

    def notice(self, message: str, *args: Any) -> None:
        self._logger.info(self._render(message), *args)

    def warning(self, message: str, *args: Any) -> None:
        self._logger.warning(self._render(message), *args)

    warn = warning

    def warning_once(self, message: str, *args: Any) -> None:
        self._logger.warning(self._render(message), *args)

    def error(self, message: str, *args: Any) -> None:
        self._logger.error(self._render(message), *args)

    error_once = error

    def critical(self, message: str, *args: Any) -> None:
        self._logger.critical(self._render(message), *args)

    critical_once = critical

    def exception(self, message: str, *args: Any) -> None:
        self._logger.exception(self._render(message), *args)


class _CapabilityCall:
    """可 await 的延迟调用对象，兼容 ``await ctx.config.get("x")`` 的写法。"""

    def __init__(self, context: "PluginContextProxy", capability: str, method: str) -> None:
        self._context = context
        self._capability = capability
        self._method = method

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[Any]:
        if args:
            raise TypeError(f"ctx.{self._capability}.{self._method}() 只接受关键字参数")
        return self._context.call_capability(f"{self._capability}.{self._method}", **kwargs)

    def __await__(self):  # pragma: no cover - 允许直接 await 能力方法本身
        return self._context.call_capability(f"{self._capability}.{self._method}").__await__()


class CapabilityProxy:
    """ctx.<capability> 代理：任意方法调用都会成为一次网关请求。"""

    def __init__(self, context: "PluginContextProxy", name: str) -> None:
        self._context = context
        self.name = name

    def __getattr__(self, item: str) -> _CapabilityCall:
        if item.startswith("_"):
            raise AttributeError(item)
        return _CapabilityCall(self._context, self.name, item)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<CapabilityProxy {self.name}>"


class PluginContextProxy:
    """MaiBot PluginContext 的兼容实现。"""

    def __init__(
        self,
        *,
        plugin_id: str,
        gateway: Gateway,
        invoker: Invoker | None = None,
        strict: bool = False,
        paths: PluginPaths | None = None,
        logger_name: str = "",
        component_registry: Any = None,
    ) -> None:
        self._plugin_id = plugin_id
        self._gateway = gateway
        self._invoker = invoker
        self._strict = strict
        self.paths = paths or PluginPaths()
        self._component_registry = component_registry
        self._cache: dict[str, CapabilityProxy] = {}
        self._logger = BridgedLogger(
            logging.getLogger(logger_name or f"plugin.{plugin_id}"), prefix=f"[{plugin_id}] "
        )
        self._plugin_config: dict[str, Any] = {}

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def logger(self) -> BridgedLogger:
        return self._logger

    @property
    def data_dir(self) -> str:
        return str(self.paths.data_dir)

    @property
    def runtime_dir(self) -> str:
        return str(self.paths.runtime_dir)

    def __getattr__(self, name: str) -> CapabilityProxy:
        if name in CAPABILITY_NAMES:
            return self.capability(name)
        raise CapabilityNotBridgedError(f"ctx.{name} 不在桥接的能力清单内")

    def capability(self, name: str) -> CapabilityProxy:
        proxy = self._cache.get(name)
        if proxy is None:
            proxy = CapabilityProxy(self, name)
            self._cache[name] = proxy
        return proxy

    # -- 插件配置 ------------------------------------------------------

    def set_plugin_config(self, value: Any) -> None:
        self._plugin_config = dict(value) if isinstance(value, dict) else {}

    def get_plugin_config_data(self) -> dict[str, Any]:
        return dict(self._plugin_config)

    @property
    def config(self):
        raise CapabilityNotBridgedError("本桥不提供 SDK 的配置模型（未安装 pydantic 契约模型）")

    # -- 能力调用 ------------------------------------------------------

    async def call_capability(self, capability: str, *_args: Any, **kwargs: Any) -> Any:
        if _args:
            raise TypeError("call_capability() 只接受关键字参数")
        if capability.split(".", 1)[0] not in CAPABILITY_NAMES:
            raise CapabilityNotBridgedError(f"未知能力 {capability!r}")
        try:
            return await self._gateway(capability, dict(kwargs))
        except CapabilityNotBridgedError:
            if self._strict:
                raise
            self._logger.debug("能力 %s 未实现，按降级策略返回 None", capability)
            return None

    async def call_host_method(
        self, method: str, *, plugin_id: str = "", payload: Any = None, timeout_ms: int | None = None
    ) -> Any:
        """与 SDK 一致：只放行白名单内的宿主接口。"""
        if plugin_id and plugin_id != self._plugin_id:
            raise PermissionError("不允许跨插件调用 call_host_method")
        if method not in ALLOWED_HOST_METHODS:
            raise PermissionError(f"未批准的方法: {method}")
        return await self._gateway(f"host.{method}", {"payload": payload, "timeout_ms": timeout_ms})

    # -- 组件互调 ------------------------------------------------------

    async def invoke_component(self, name: str, **_kwargs: Any) -> Any:
        if self._invoker is None:
            raise CapabilityNotBridgedError("本桥未开放 invoke_component")
        return await self._invoker(name, dict(_kwargs))

    def register_component(self, info: Any, method: Callable[..., Any]) -> Any:
        if self._component_registry is None:
            raise CapabilityNotBridgedError("本桥未开放 register_component")
        return self._component_registry.register(info, method)

    def unregister_component(self, component_type: Any, name: str) -> bool:
        if self._component_registry is None:
            raise CapabilityNotBridgedError("本桥未开放 unregister_component")
        return self._component_registry.unregister(component_type, name)
