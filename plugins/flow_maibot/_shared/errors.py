"""flow_maibot 桥接层的异常类型。

所有异常的 message 都必须是已脱敏文本：它会经 Ok/Err 回到插件面板，也可能被
LLM 看到，因此严禁夹带 Authorization header、API key、原始 payload。
"""

from __future__ import annotations

from typing import Any


class BridgeError(Exception):
    """桥接层错误基类。"""

    code = "bridge_error"

    def __init__(self, message: str, *, detail: str = "") -> None:
        super().__init__(str(message))
        self.message = str(message)
        self.detail = str(detail)

    def to_dict(self) -> dict[str, Any]:
        """转成 Err 用的负载；detail 只在面板调试时有用。"""
        payload: dict[str, Any] = {"code": self.code, "error": self.message}
        if self.detail:
            payload["detail"] = self.detail
        return payload

    def __str__(self) -> str:
        return self.message


class ConfigError(BridgeError):
    """插件配置不合法或不完整。"""

    code = "config_error"


class McpError(BridgeError):
    """MCP 传输或协议层错误。"""

    code = "mcp_error"


class NetworkTransportError(McpError):
    """底层 HTTP 传输失败（连不上、DNS、超时）。"""

    code = "mcp_transport_error"


class PluginLoadError(BridgeError):
    """MaiBot 插件文件加载失败。"""

    code = "plugin_load_error"


class ComponentNotFoundError(BridgeError):
    """被调用的组件在已加载插件里不存在。"""

    code = "component_not_found"


class AmbiguousPluginError(BridgeError):
    """一个模块里出现多个候选插件类，无法自动挑选。"""

    code = "ambiguous_plugin"


class CapabilityNotBridgedError(BridgeError):
    """MaiBot 插件请求了本桥不转发的能力。"""

    code = "capability_not_bridged"
