"""纯标准库的 MCP（streamable-http）客户端。

只依赖标准库，插件进程可以直接跑，也方便离线测试：
    * transport 是可注入的同步函数 (url, body, headers, timeout) -> (status, headers, text)
    * 网络调用走 asyncio.to_thread，不会卡住插件事件循环
    * 响应同时兼容 application/json 与 text/event-stream（SSE）
    * 错误文本一律脱敏，绝不回带 Authorization / API key
"""

from __future__ import annotations

import asyncio
import itertools
import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from .errors import McpError, NetworkTransportError

Transport = Callable[[str, bytes, dict[str, str], float], tuple[int, Mapping[str, str], str]]

_DEFAULT_PROTOCOL_VERSION = "2025-03-26"
_SESSION_HEADER = "mcp-session-id"


def sanitize(text: str, secrets: tuple[str, ...] = ()) -> str:
    """把密钥打码后返回，可安全用于错误信息。"""
    cleaned = str(text or "")
    for secret in secrets:
        value = str(secret or "")
        if len(value) >= 8:
            cleaned = cleaned.replace(value, "***")
    return cleaned


def _normalize_transport_error(exc: BaseException, endpoint: str, timeout: float) -> NetworkTransportError:
    """把 urllib 传输异常归一成 NetworkTransportError；供任意 transport 复用。"""
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return NetworkTransportError(f"连接 MCP 端点超时（{timeout:g}s）")
    return NetworkTransportError(f"无法连接 MCP 端点 {endpoint}: {reason}")


def _default_transport(
    url: str, body: bytes, headers: dict[str, str], timeout: float
) -> tuple[int, Mapping[str, str], str]:
    """urllib 版传输实现：HTTP 错误也返回 body，交给上层判断。"""
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), dict(response.headers), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        try:
            payload = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 - 读不到 body 不影响错误传播
            payload = ""
        return int(exc.code), dict(exc.headers or {}), payload
    except urllib.error.URLError as exc:
        raise _normalize_transport_error(exc, url, timeout) from exc


def parse_message(text: str) -> dict[str, Any]:
    """解析 MCP 响应体：优先按 SSE 解析，失败再按纯 JSON 解析。"""
    raw = str(text or "").strip()
    if not raw:
        raise McpError("MCP 端点返回了空响应体")

    if "data:" in raw or raw.startswith("event:"):
        chunks: list[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith(("event:", "id:", ":")):
                continue
            if line.startswith("data:"):
                chunks.append(line[5:].strip())
        for chunk in reversed(chunks):
            try:
                parsed = json.loads(chunk)
            except (TypeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return parsed
        raise McpError("MCP 端点的 SSE 响应里没有可用的 JSON-RPC 消息")

    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise McpError(f"MCP 端点返回了无法解析的响应: {sanitize(raw[:200])}") from exc
    if not isinstance(parsed, dict):
        raise McpError("MCP 端点返回了非对象响应")
    return parsed


def normalize_tool_result(result: Any, *, max_chars: int = 24000) -> dict[str, Any]:
    """把 tools/call 结果统一成 {is_error, text, blocks, structured, truncated}。"""
    payload = result if isinstance(result, dict) else {}
    raw_blocks = payload.get("content")
    blocks = [block for block in raw_blocks if isinstance(block, dict)] if isinstance(raw_blocks, list) else []
    texts = [str(block.get("text", "")) for block in blocks if str(block.get("type", "")) == "text"]
    text = "\n\n".join(item for item in texts if item).strip()
    if not text:
        text = json.dumps(payload, ensure_ascii=False) if payload else ""
    truncated = len(text) > max_chars
    return {
        "is_error": bool(payload.get("isError", False)),
        "text": text[:max_chars],
        "blocks": blocks,
        "structured": payload.get("structuredContent"),
        "truncated": truncated,
    }


class McpClient:
    """最小可用的 MCP 客户端：initialize / tools/list / tools/call。"""

    def __init__(
        self,
        endpoint: str,
        *,
        token: str = "",
        headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
        client_name: str = "flow_maibot",
        client_version: str = "0.1.0",
        protocol_version: str = _DEFAULT_PROTOCOL_VERSION,
        transport: Transport | None = None,
        session_id: str = "",
    ) -> None:
        self.endpoint = str(endpoint or "").strip()
        self.timeout = float(timeout)
        self.client_name = client_name
        self.client_version = client_version
        self.protocol_version = protocol_version
        self._token = str(token or "")
        self._extra_headers = dict(headers or {})
        self._transport: Transport = transport or _default_transport
        self._session_id = str(session_id or "")
        self._ids = itertools.count(1)
        self._initialized = False

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": f"{self.client_name}/{self.client_version}",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        headers.update(self._extra_headers)
        return headers

    @property
    def session_id(self) -> str:
        return self._session_id

    async def _exchange(
        self, method: str, params: dict[str, Any] | None, *, notify: bool = False
    ) -> dict[str, Any]:
        if not self.endpoint:
            raise McpError("MCP 端点未配置")
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notify:
            message["id"] = next(self._ids)
        message["params"] = params or {}
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        try:
            status, headers, text = await asyncio.to_thread(
                self._transport, self.endpoint, body, self._headers(), self.timeout
            )
        except NetworkTransportError:
            raise
        except urllib.error.URLError as exc:
            raise _normalize_transport_error(exc, self.endpoint, self.timeout) from exc
        self._capture_session(headers)
        if status < 200 or status >= 300:
            raise McpError(f"MCP 端点返回 HTTP {status}: {sanitize(text[:200], (self._token,))}")
        if notify:
            return {}
        response = parse_message(text)
        if isinstance(response.get("error"), dict):
            error = response["error"]
            raise McpError(f"MCP 错误 {error.get('code', '?')}: {error.get('message', '')}")
        result = response.get("result")
        return result if isinstance(result, dict) else {}

    def _capture_session(self, headers: Mapping[str, str]) -> None:
        for key, value in dict(headers).items():
            if str(key).lower() == _SESSION_HEADER and value:
                self._session_id = str(value)

    async def initialize(self, *, force: bool = False) -> dict[str, Any]:
        """建会话；已初始化时直接返回空结果。"""
        if self._initialized and not force:
            return {}
        result = await self._exchange(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": self.client_name, "version": self.client_version},
            },
        )
        await self._exchange("notifications/initialized", {}, notify=True)
        self._initialized = True
        info = result.get("serverInfo")
        return info if isinstance(info, dict) else {}

    async def list_tools(self) -> list[dict[str, Any]]:
        """返回端点声明的工具列表（未初始化时自动 initialize）。"""
        await self.initialize()
        result = await self._exchange("tools/list", {})
        tools = result.get("tools")
        return [tool for tool in tools if isinstance(tool, dict)] if isinstance(tools, list) else []

    async def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """调用一个工具并返回规范化结果。"""
        await self.initialize()
        result = await self._exchange("tools/call", {"name": str(name), "arguments": dict(arguments or {})})
        return normalize_tool_result(result)

    async def close(self) -> None:
        """无状态客户端，只重置会话标记。"""
        self._initialized = False
