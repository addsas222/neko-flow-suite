"""MaiBot SDK 公开接口的兼容实现。

NEKO 插件进程里不依赖任何 MaiBot SDK 代码；本文件按 SDK 的 *公开签名* 重写
（MaiBot Plugin SDK 为 LGPL-3.0，源码另行存放，见 NOTICE.md）。

因此 MaiBot 插件可以这样写，两种环境都能跑：

    try:
        from maibot_sdk.plugin import MaiBotPlugin
        from maibot_sdk.components import Tool
    except ImportError:  # NEKO 桥接态
        from sdk_compat import MaiBotPlugin, Tool

提供的接口子集：
    组件装饰器 Tool / Action / Command / API / EventHandler / HookHandler /
    HomeCard / MessageGateway / LLMProvider，以及 MaiBotPlugin 基类
    （get_components / set_plugin_config / register_dynamic_api / invoke_component /
    on_load / on_unload / on_config_update / ctx）。
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

COMPONENT_INFO_ATTR = "__maibot_component_info__"

# 组件类型（与 SDK ComponentType 的取值一致）
# 注意：`API` 这个名字被装饰器工厂占了，所以常量必须另起名，否则工厂会在导入后
# 覆盖常量，`ComponentInfo.type` 就会变成函数对象而不是字符串。
TOOL = "TOOL"
ACTION = "ACTION"
COMMAND = "COMMAND"
API_COMPONENT = "API"
EVENT_HANDLER = "EVENT_HANDLER"
HOOK_HANDLER = "HOOK_HANDLER"
MESSAGE_GATEWAY = "MESSAGE_GATEWAY"
LLM_PROVIDER = "LLM_PROVIDER"
HOME_CARD = "HOME_CARD"


@dataclass
class ComponentInfo:
    """SDK ``ComponentInfo`` 的等价结构（不引入 pydantic）。"""

    name: str
    type: str
    description: str = ""
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    # Tool / Action 专有
    brief_description: str = ""
    detailed_description: str = ""
    parameters_raw: dict[str, Any] = field(default_factory=dict)
    parameters: list[Any] = field(default_factory=list)
    invoke_method: str = ""
    # API 专有
    version: str = "1"
    public: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
            "brief_description": self.brief_description,
            "detailed_description": self.detailed_description,
            "parameters_raw": dict(self.parameters_raw),
            "invoke_method": self.invoke_method,
            "version": self.version,
            "public": self.public,
        }


def _parameters_schema(parameters: Any) -> dict[str, Any]:
    """只认 dict 形态的参数 schema；list 形态由真 SDK 处理。"""
    return dict(parameters) if isinstance(parameters, dict) else {}


def Tool(
    name: str,
    description: str = "",
    brief_description: str = "",
    detailed_description: str = "",
    parameters: Any = None,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Tool 组件装饰器（dict 参数形态由本桥处理）。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        brief = str(brief_description or description or name).strip()
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=TOOL,
            description=brief,
            metadata=dict(metadata),
            brief_description=brief,
            detailed_description=str(detailed_description or "").strip(),
            parameters_raw=_parameters_schema(parameters),
            parameters=list(parameters) if isinstance(parameters, list) else [],
            invoke_method="plugin.invoke_tool",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def Action(
    name: str,
    description: str = "",
    brief_description: str = "",
    detailed_description: str = "",
    parameters: Any = None,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """兼容入口：与 Tool 等价（SDK 内部已把 Action 归一为 Tool）。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        merged = {**metadata, "legacy_component_type": ACTION}
        return Tool(
            name,
            description,
            brief_description,
            detailed_description,
            parameters,
            **merged,
        )(func)

    return decorator


def Command(
    name: str,
    description: str = "",
    pattern: str = "",
    aliases: list[str] | None = None,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Command 组件装饰器。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=COMMAND,
            description=str(description or ""),
            metadata={**metadata, "command_pattern": pattern, "aliases": list(aliases or [])},
            invoke_method="plugin.invoke_command",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def API(
    name: str,
    description: str = "",
    version: str = "1",
    public: bool = False,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """API 组件装饰器。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=API_COMPONENT,
            description=str(description or ""),
            metadata=dict(metadata),
            invoke_method="plugin.invoke_api",
            version=str(version or "1").strip() or "1",
            public=bool(public),
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def EventHandler(
    name: str,
    description: str = "",
    event_type: str = "on_message",
    intercept_message: bool = False,
    weight: int = 0,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """EventHandler 组件装饰器。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=EVENT_HANDLER,
            description=str(description or ""),
            metadata={
                **metadata,
                "event_type": str(event_type or "on_message"),
                "intercept_message": bool(intercept_message),
                "weight": int(weight),
            },
            invoke_method="plugin.invoke_event",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def HookHandler(
    hook: str,
    *,
    name: str = "",
    description: str = "",
    mode: str = "blocking",
    order: str = "normal",
    timeout_ms: int = 0,
    error_policy: str = "skip",
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """命名 Hook 处理器。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        normalized_hook = str(hook or "").strip()
        if not normalized_hook:
            raise ValueError("HookHandler 的 hook 不能为空")
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=HOOK_HANDLER,
            description=str(description or ""),
            metadata={
                **metadata,
                "hook": normalized_hook,
                "mode": str(mode or "blocking"),
                "order": str(order or "normal"),
                "timeout_ms": int(timeout_ms),
                "error_policy": str(error_policy or "skip"),
            },
            invoke_method="plugin.invoke_hook",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def HomeCard(
    name: str,
    title: str,
    content: Any = "",
    *,
    description: str = "",
    link_url: str = "",
    link_label: str = "",
    icon: str = "",
    width: str = "medium",
    order: int = 1000,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """WebUI 首页卡片。"""
    normalized_name = str(name or "").strip()
    if not normalized_name:
        raise ValueError("HomeCard 的 name 不能为空")
    normalized_title = str(title or "").strip()
    if not normalized_title:
        raise ValueError("HomeCard 的 title 不能为空")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=normalized_name,
            type=HOME_CARD,
            description=str(description or ""),
            metadata={
                **metadata,
                "title": normalized_title,
                "content": content,
                "link_url": str(link_url or ""),
                "link_label": str(link_label or ""),
                "icon": str(icon or ""),
                "width": str(width or "medium").strip().lower() or "medium",
                "order": int(order),
            },
            invoke_method="plugin.invoke_home_card",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def MessageGateway(
    route_type: str,
    *,
    name: str = "",
    description: str = "",
    platform: str = "",
    protocol: str = "",
    account_id: str = "",
    scope: str = "",
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """消息网关组件。"""
    normalized = str(route_type or "").strip().lower()
    resolved = {"recv": "receive", "recive": "receive", "send": "send", "duplex": "duplex"}.get(normalized, "receive")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=str(name or func.__name__),
            type=MESSAGE_GATEWAY,
            description=str(description or ""),
            metadata={
                "route_type": resolved,
                "platform": str(platform or ""),
                "protocol": str(protocol or ""),
                "account_id": str(account_id or ""),
                "scope": str(scope or ""),
                **metadata,
            },
            invoke_method="plugin.invoke_message_gateway",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def LLMProvider(
    client_type: str,
    *,
    name: str = "",
    description: str = "",
    version: str = "1.0.0",
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """LLM Provider 组件。"""
    normalized_type = str(client_type or "").strip()
    if not normalized_type:
        raise ValueError("LLMProvider 的 client_type 不能为空")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        info = ComponentInfo(
            name=str(name or normalized_type),
            type=LLM_PROVIDER,
            description=str(description or ""),
            metadata={"client_type": normalized_type, "version": str(version or "1.0.0"), **metadata},
            invoke_method="plugin.invoke_llm_provider",
        )
        setattr(func, COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def WorkflowStep(*args: Any, **kwargs: Any) -> Any:
    """SDK 2.0 已移除该入口，只给出明确错误。"""
    raise RuntimeError("`WorkflowStep` 已移除，请改用 `HookHandler`。这是一个不向后兼容更改。")


def collect_components(instance: Any) -> list[ComponentInfo]:
    """收集实例上被装饰器标记的组件（按 MRO 顺序，子类覆盖父类）。"""
    found: list[ComponentInfo] = []
    seen: set[tuple[str, str]] = set()
    for owner in reversed(type(instance).__mro__):
        for attribute, value in vars(owner).items():
            info = getattr(value, COMPONENT_INFO_ATTR, None)
            if not isinstance(info, ComponentInfo) or not hasattr(instance, attribute):
                continue
            key = (info.type, info.name)
            if key in seen:
                continue
            seen.add(key)
            found.append(info)
    return sorted(found, key=lambda item: (item.type, item.name))


def sdk_installed() -> bool:
    """环境里是否安装了真 MaiBot SDK。"""
    import importlib.util

    return importlib.util.find_spec("maibot_sdk") is not None


class MaiBotPlugin:
    """MaiBot SDK 插件基类的兼容实现（形状一致，不引入 SDK 代码）。"""

    plugin_name: str = ""
    description: str = ""
    config_model: Any = None
    config_reload_subscriptions: tuple[str, ...] = ()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """忽略多余参数：桥接层可能注入额外关键字。"""
        del args, kwargs
        self._ctx = None
        self._dynamic_api_components: dict[str, dict[str, Any]] = {}
        self._dynamic_api_handlers: dict[str, Callable[..., Any]] = {}
        self._plugin_config_data: dict[str, Any] = {}

    # -- 日志 ----------------------------------------------------------

    def _get_logger(self) -> Any:
        if self._ctx is not None:
            return self._ctx.logger
        return logging.getLogger("flow_maibot.sdk_compat")

    @property
    def logger(self) -> Any:
        return self._get_logger()

    # -- 配置 ----------------------------------------------------------

    @classmethod
    def get_config_model(cls) -> Any:
        return None

    @classmethod
    def has_config_model(cls) -> bool:
        return False

    @classmethod
    def build_default_config(cls) -> dict[str, Any]:
        return {}

    @classmethod
    def build_config_schema(cls, **kwargs: Any) -> dict[str, Any]:
        return {}

    def normalize_plugin_config(self, config_data: Any) -> tuple[dict[str, Any], bool]:
        return (dict(config_data) if isinstance(config_data, dict) else {}), False

    def set_plugin_config(self, config_data: Any) -> None:
        normalized, _ = self.normalize_plugin_config(config_data)
        self._plugin_config_data = normalized

    def get_plugin_config_data(self) -> dict[str, Any]:
        return dict(self._plugin_config_data)

    def get_default_config(self) -> dict[str, Any]:
        return type(self).build_default_config()

    def get_webui_config_schema(self, **kwargs: Any) -> dict[str, Any]:
        return type(self).build_config_schema(**kwargs)

    @property
    def config(self):
        raise RuntimeError("本兼容层未声明 config_model，无法通过 config 访问强类型配置")

    # -- 上下文 --------------------------------------------------------

    @property
    def ctx(self):
        if self._ctx is None:
            raise RuntimeError("插件上下文尚未初始化，请在桥接环境下运行")
        return self._ctx

    def _set_context(self, ctx: Any) -> None:
        self._ctx = ctx

    # -- 组件 ----------------------------------------------------------

    def get_components(self) -> list[dict[str, Any]]:
        return [info.to_dict() for info in collect_components(self)] + self.get_dynamic_api_components()

    def get_llm_providers(self) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def _build_dynamic_api_key(name: str, version: str) -> str:
        return f"{str(name or '').strip()}@{str(version or '1').strip() or '1'}"

    def register_dynamic_api(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        version: str = "1",
        public: bool = False,
        handler_name: str = "",
        **metadata: Any,
    ) -> dict[str, Any]:
        """注册动态 API；返回可直接同步给宿主的组件声明。"""
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("动态 API 名称不能为空")
        normalized_version = str(version or "1").strip() or "1"
        resolved = str(handler_name or f"dynamic_api__{normalized_name}__{normalized_version}").strip()
        component_metadata: dict[str, Any] = {
            "description": description,
            "version": normalized_version,
            "public": bool(public),
            "dynamic": True,
            "handler_name": resolved,
            **metadata,
        }
        self._dynamic_api_components[self._build_dynamic_api_key(normalized_name, normalized_version)] = {
            "name": normalized_name,
            "type": API_COMPONENT,
            "metadata": component_metadata,
        }
        self._dynamic_api_handlers[resolved] = handler
        return {"name": normalized_name, "type": API_COMPONENT, "metadata": dict(component_metadata)}

    def unregister_dynamic_api(self, name: str, *, version: str = "1") -> bool:
        component = self._dynamic_api_components.pop(self._build_dynamic_api_key(name, version), None)
        if component is None:
            return False
        handler_name = str(component["metadata"].get("handler_name", "") or "").strip()
        if handler_name and not any(
            str(candidate["metadata"].get("handler_name", "") or "").strip() == handler_name
            for candidate in self._dynamic_api_components.values()
        ):
            self._dynamic_api_handlers.pop(handler_name, None)
        return True

    def clear_dynamic_apis(self) -> None:
        self._dynamic_api_components.clear()
        self._dynamic_api_handlers.clear()

    def get_dynamic_api_components(self) -> list[dict[str, Any]]:
        return [
            {"name": item["name"], "type": item["type"], "metadata": dict(item["metadata"])}
            for item in self._dynamic_api_components.values()
        ]

    async def invoke_component(self, component_name: str, **kwargs: Any) -> Any:
        """为动态 API 提供默认分发。"""
        handler = self._dynamic_api_handlers.get(component_name)
        if handler is None:
            raise AttributeError(f"插件未注册动态组件处理器: {component_name}")
        if inspect.iscoroutinefunction(handler):
            return await handler(**kwargs)
        result = handler(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    # -- 生命周期 ------------------------------------------------------

    async def on_load(self) -> None:
        raise NotImplementedError("插件必须实现 on_load() 来处理加载生命周期")

    async def on_unload(self) -> None:
        raise NotImplementedError("插件必须实现 on_unload() 来处理卸载生命周期")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        raise NotImplementedError("插件必须实现 on_config_update() 来处理配置热重载")
