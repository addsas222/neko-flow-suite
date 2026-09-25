"""AnySearch 的 MaiBot 插件：把 MCP 搜索能力暴露成 LLM Tool。

这个文件就是"证据"：它只用 MaiBot Plugin SDK 的公开接口写，
在真 MaiBot 环境里直接 ``from maibot_sdk...``，在 NEKO 桥接态下
自动落到 :mod:`sdk_compat`，两边的代码完全一致。

网关（真正的 MCP 客户端）不在 SDK 的控制范围里，因此：
    * NEKO 桥加载后调用 :meth:`attach_backend` 注入 :class:`AnySearchGateway`
    * 真 MaiBot 环境由宿方设置模块级 ``GATEWAY_FACTORY``（见 docs/guide.md）

Tool 处理器统一返回 NEKO 侧可直接转给 LLM 的结果：::

    {"is_error": False, "text": "...", "truncated": False, ...}
"""

from __future__ import annotations

from typing import Any

try:  # 真 MaiBot 环境
    from maibot_sdk.components import Tool
    from maibot_sdk.plugin import MaiBotPlugin
except ImportError:  # NEKO 桥接态
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

    from sdk_compat import MaiBotPlugin, Tool

#: (factory) -> backend；真 MaiBot 环境下由宿方赋值，NEKO 桥会自动注入。
GATEWAY_FACTORY: Any = None

PLUGIN_NAME = "anysearch"
PLUGIN_DESCRIPTION = "AnySearch MCP 联网搜索：search / batch_search"

SEARCH_BRIEF = (
    "联网搜索（AnySearch）。适合任何需要外部信息的问题：事实、新闻、人物、公司、产品、地点、"
    "价格、事件、研究资料，或验证/对比某个说法。"
)
SEARCH_DETAILED = (
    "联网搜索（AnySearch）。\n"
    "参数：query 必填（单一意图的自然语言查询）；max_results 可选（1-10，默认 10）。\n"
    "domain 可选用于垂类检索（academic/code/finance/legal/health/travel 等），"
    "但一旦传了 domain，就必须先用 get_sub_domains 拿到 sub_domain 与 sub_domain_params，否则会失败；"
    "普通检索请把 domain / sub_domain / sub_domain_params 全部省略。\n"
    "一次只查一个意图；多个独立查询改用 batch_search。"
)

BATCH_BRIEF = (
    "联网并行搜索（AnySearch）。一条调用同时跑 2-5 个独立查询，比连续调用 search 更省上下文。"
)
BATCH_DETAILED = (
    "联网并行搜索（AnySearch），单次调用并行执行 2-5 条查询。\n"
    "参数：queries 必填，字符串或对象数组（2-5 项）；每项结构与 search 相同"
    "（query 必填；domain / sub_domain / sub_domain_params 可选，垂类查询同样需要先从 "
    "get_sub_domains 取值）。\n"
    "适合横向比较、同一主题多角度调研、general + 垂类混合检索。"
)


class AnySearchPlugin(MaiBotPlugin):
    """把 AnySearch 的两个工具暴露为 MaiBot Tool 组件。"""

    plugin_name = PLUGIN_NAME
    description = PLUGIN_DESCRIPTION

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._backend: Any = None

    # -- 网关注入 ------------------------------------------------------

    def attach_backend(self, backend: Any) -> None:
        """NEKO 桥在这里注入 AnySearchGateway。"""
        self._backend = backend

    @property
    def backend(self) -> Any:
        if self._backend is None:
            raise RuntimeError(
                "AnySearch 网关未注入：NEKO 桥会在加载时调用 attach_backend()；"
                "真 MaiBot 环境请先设置模块级 GATEWAY_FACTORY。"
            )
        return self._backend

    # -- 生命周期 ------------------------------------------------------

    async def on_load(self) -> None:
        if self._backend is None and GATEWAY_FACTORY is not None:
            self._backend = GATEWAY_FACTORY(self.get_plugin_config_data())
        if self._backend is None:
            self.logger.error("AnySearch 网关不可用，search / batch_search 会直接返回错误")
            return
        describe = getattr(self._backend, "describe", None)
        info = describe() if callable(describe) else {}
        self.logger.info(
            "AnySearch 已就绪：%s（密钥来源 %s）",
            info.get("endpoint", "unknown"),
            info.get("token_source", "none"),
        )

    async def on_unload(self) -> None:
        close = getattr(self._backend, "close", None)
        if callable(close):
            result = close()
            if hasattr(result, "__await__"):
                await result
        self._backend = None

    # -- 工具 ----------------------------------------------------------

    @Tool(
        name="search",
        brief_description=SEARCH_BRIEF,
        detailed_description=SEARCH_DETAILED,
        description=f"{SEARCH_BRIEF} 参数 query：必填，单一意图的自然语言查询。",
    )
    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> dict[str, Any]:
        """单条查询的联网搜索。"""
        result = await self.backend.search({"query": query, "max_results": max_results, **kwargs})
        return self._normalize(result)

    @Tool(
        name="batch_search",
        brief_description=BATCH_BRIEF,
        detailed_description=BATCH_DETAILED,
        description=f"{BATCH_BRIEF} 参数 queries：必填，2-5 个查询。",
    )
    async def batch_search(self, queries: list[Any], **kwargs: Any) -> dict[str, Any]:
        """并行跑 2-5 条独立查询。"""
        result = await self.backend.batch_search({"queries": queries, **kwargs})
        return self._normalize(result)

    @staticmethod
    def _normalize(result: Any) -> dict[str, Any]:
        """把网关结果收敛成统一契约，缺字段时也能安全返回。"""
        if not isinstance(result, dict):
            return {"is_error": True, "text": str(result or "AnySearch 返回了空结果"), "truncated": False}
        payload = dict(result)
        payload.setdefault("is_error", False)
        payload.setdefault("text", "")
        if not payload.get("text") and not payload.get("structured"):
            payload["text"] = "（AnySearch 未返回内容）"
        return payload
