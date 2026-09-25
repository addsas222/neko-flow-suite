"""flow_maibot 共享层：MaiBot 插件 -> NEKO LLM 工具的桥。

分层：
    * ``schemas``      AnySearch 工具元数据（捕获自上游 MCP 端点）
    * ``settings``     桥接层配置解析与校验
    * ``errors``       可安全回显的脱敏异常
    * ``context``      MaiBot ``PluginContext`` 的兼容代理
    * ``sdk_compat``   MaiBot Plugin SDK 公开接口的重写实现
    * ``mcp_client``   纯标准库的 MCP streamable-http 客户端
    * ``anysearch``    MCP 网关（参数清洗 + 结果裁剪 + 错误归一）
    * ``bridge``       MaiBot 插件加载、@Tool 映射与调用分发

``_shared/maibot_plugins/`` 下放的是"生态证据"：用 MaiBot SDK 公开接口写的
插件本体，真 MaiBot 环境与 NEKO 桥接态共用同一份代码。MaiBot Plugin SDK 为
LGPL-3.0，署名见插件根目录的 NOTICE.md。
"""

from __future__ import annotations

from .anysearch import AnySearchGateway
from .bridge import MaiBotBridge, ToolBinding, neko_tool_name
from .context import PluginContextProxy, PluginPaths
from .errors import (
    AmbiguousPluginError,
    BridgeError,
    CapabilityNotBridgedError,
    ComponentNotFoundError,
    ConfigError,
    McpError,
    NetworkTransportError,
    PluginLoadError,
)
from .mcp_client import McpClient, normalize_tool_result
from .schemas import validate_capture
from .sdk_compat import MaiBotPlugin, Tool
from .settings import BridgeSettings, MaiBotPluginSpec

__all__ = [
    "AmbiguousPluginError",
    "AnySearchGateway",
    "BridgeError",
    "BridgeSettings",
    "CapabilityNotBridgedError",
    "ComponentNotFoundError",
    "ConfigError",
    "MaiBotBridge",
    "MaiBotPlugin",
    "MaiBotPluginSpec",
    "McpClient",
    "McpError",
    "NetworkTransportError",
    "PluginContextProxy",
    "PluginLoadError",
    "PluginPaths",
    "Tool",
    "ToolBinding",
    "neko_tool_name",
    "normalize_tool_result",
    "validate_capture",
]
