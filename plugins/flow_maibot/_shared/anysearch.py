"""AnySearch MCP 网关。

这一层是 MaiBot 插件（``@Tool``）与 :mod:`mcp_client` 之间的适配器：
    * 参数清洗：只放行上游 inputSchema 里声明的字段，并对 max_results 兜底封顶
    * 错误归一：底层异常统一转成脱敏后的 McpError
    * 结果裁剪：按配置的 max_chars 二次截断，防止把 1MB 搜索结果塞进提示词
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import schemas
from .errors import ConfigError, McpError
from .mcp_client import McpClient, Transport
from .settings import AnySearchSettings

#: search 允许透传的上游字段（其余字段由插件侧自行处理，不透传）
SEARCH_ARGS: tuple[str, ...] = (
    "query",
    "max_results",
    "domain",
    "sub_domain",
    "sub_domain_params",
    "exclude",
    "only_once",
)

#: batch_search 允许透传的上游字段
BATCH_SEARCH_ARGS: tuple[str, ...] = (
    "queries",
    "max_results",
    "domain",
    "sub_domain",
    "sub_domain_params",
    "exclude",
    "only_once",
)

MAX_BATCH_QUERIES = 5


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


class AnySearchGateway:
    """AnySearch 的薄封装：参数清洗 + 结果裁剪 + 错误归一。"""

    def __init__(
        self,
        settings: AnySearchSettings,
        *,
        transport: Transport | None = None,
        client_version: str = "0.1.0",
    ) -> None:
        if not settings.endpoint:
            raise ConfigError("anysearch.endpoint 未配置")
        self._settings = settings
        self._client = McpClient(
            settings.endpoint,
            token=settings.token,
            headers=settings.headers,
            timeout=settings.timeout_seconds,
            client_name="flow_maibot",
            client_version=client_version,
            transport=transport,
        )

    # -- 基本信息 ------------------------------------------------------

    @property
    def settings(self) -> AnySearchSettings:
        return self._settings

    @property
    def endpoint(self) -> str:
        return self._settings.endpoint

    @property
    def token_available(self) -> bool:
        """只回答"有没有密钥"，绝不回显密钥本身。"""
        return bool(self._settings.token)

    def describe(self) -> dict[str, Any]:
        """诊断信息，可安全回显到插件面板（不含密钥）。"""
        return {
            "endpoint": self._settings.endpoint,
            "token_source": self._settings.token_source,
            "token_available": self.token_available,
            "tools": list(self._settings.tools),
            "description_mode": self._settings.description_mode,
            "timeout_seconds": self._settings.timeout_seconds,
            "max_chars": self._settings.max_chars,
            "max_results": self._settings.max_results,
        }

    # -- 参数清洗 ------------------------------------------------------

    def _pick(self, arguments: Mapping[str, Any], allowed: tuple[str, ...]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key in allowed:
            if key not in arguments:
                continue
            value = arguments[key]
            if value is None or value == "":
                continue
            payload[key] = value
        raw = payload.get("max_results")
        try:
            payload["max_results"] = max(
                1, min(int(self._settings.max_results if raw is None else raw), self._settings.max_results)
            )
        except (TypeError, ValueError):
            raise McpError("max_results 必须是 1-10 的整数") from None
        return payload

    def _clip(self, result: dict[str, Any]) -> dict[str, Any]:
        text = str(result.get("text", ""))
        limit = self._settings.max_chars
        if limit > 0 and len(text) > limit:
            result = dict(result)
            result["text"] = text[:limit]
            result["truncated"] = True
        return result

    # -- 工具调用 ------------------------------------------------------

    async def search(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """tools/call: search（单条查询）。"""
        return await self.call(schemas.SEARCH, arguments)

    async def batch_search(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """tools/call: batch_search（并行 2-5 条查询）。"""
        return await self.call(schemas.BATCH_SEARCH, arguments)

    async def call(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name not in self._settings.tools:
            raise McpError(f"工具 {name} 未在 anysearch.tools 中启用")
        payload = self._pick(arguments, SEARCH_ARGS if name == schemas.SEARCH else BATCH_SEARCH_ARGS)
        if name == schemas.SEARCH:
            query = _clean_text(payload.get("query"))
            if not query:
                raise McpError("search 需要非空的 query 字段")
            payload["query"] = query
        else:
            payload["queries"] = self._normalize_queries(payload.get("queries"))
        return self._clip(await self._client.call_tool(name, payload))

    def _normalize_queries(self, queries: Any) -> list[Any]:
        if not isinstance(queries, list) or len(queries) < 2:
            raise McpError(f"batch_search 需要 2-{MAX_BATCH_QUERIES} 条 queries")
        normalized: list[Any] = []
        for entry in queries:
            if isinstance(entry, str):
                query = _clean_text(entry)
                if not query:
                    raise McpError(f"batch_search 的 queries 里存在空 query: {entry!r}")
                normalized.append({"query": query})
            elif isinstance(entry, Mapping):
                if not _clean_text(entry.get("query")):
                    raise McpError(f"batch_search 的 queries 每条都需要非空 query: {dict(entry)!r}")
                normalized.append({key: value for key, value in entry.items() if value not in (None, "")})
            else:
                raise McpError(f"batch_search 的 queries 只接受字符串或对象，当前是 {type(entry).__name__}")
        return normalized[:MAX_BATCH_QUERIES]

    # -- 探测 ----------------------------------------------------------

    async def list_tools(self) -> list[dict[str, Any]]:
        return await self._client.list_tools()

    async def probe(self) -> dict[str, Any]:
        """连通性自检：initialize + tools/list，不调用计费工具。"""
        info = await self._client.initialize(force=True)
        tools = await self._client.list_tools()
        discovered = sorted(str(tool.get("name", "")) for tool in tools if isinstance(tool, dict))
        missing = [name for name in self._settings.tools if name not in discovered]
        server_name = str(info.get("name", "") or "") if isinstance(info, dict) else ""
        return {
            "ok": not missing,
            "endpoint": self.endpoint,
            "server": server_name,
            "session_id": self._client.session_id,
            "discovered_tools": discovered,
            "missing_tools": missing,
            "token_available": self.token_available,
            "token_source": self._settings.token_source,
        }

    async def close(self) -> None:
        await self._client.close()
