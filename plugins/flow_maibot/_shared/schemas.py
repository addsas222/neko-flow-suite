"""AnySearch 工具元数据。

captured/anysearch_tools.json 是从 AnySearch MCP 端点 tools/list 原样落盘的
数据（未做任何改写），作为上游契约的凭据：
    * description_mode = "brief"：用本文件的 BRIEF_DESCRIPTIONS 精炼描述
    * description_mode = "full" ：原样透传上游 description
inputSchema 始终原样透传，参数校验只依赖 captures 里的副本。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CAPTURE_PATH = Path(__file__).resolve().parent / "captured" / "anysearch_tools.json"

_CAPTURE: dict[str, Any] = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))

ENDPOINT: str = _CAPTURE.get("endpoint", "")
PROTOCOL: str = _CAPTURE.get("protocol", "mcp-streamable-http")
CAPTURED_AT: str = _CAPTURE.get("captured_at", "")
CAPTURED_TOOLS: dict[str, dict[str, Any]] = _CAPTURE.get("tools", {})

SEARCH = "search"
BATCH_SEARCH = "batch_search"
DEFAULT_TOOLS: tuple[str, ...] = (SEARCH, BATCH_SEARCH)

#: 上游 schema 里必须存在的根属性名（拿来校验捕获数据是否完整）
_EXPECTED_PROPERTIES: dict[str, tuple[str, ...]] = {
    SEARCH: ("query",),
    BATCH_SEARCH: ("queries",),
}

#: 交给 LLM 的精炼描述：控制在 300 字以内，只保留"什么时候用 + 必填参数 +
#: 常见错误"，避免把上游 1.2 万字的说明整段塞进提示词。
BRIEF_DESCRIPTIONS: dict[str, str] = {
    SEARCH: (
        "联网搜索（AnySearch）。适合任何需要外部信息的问题：事实、新闻、人物、公司、产品、地点、价格、"
        "事件、研究资料，或验证、对比某个说法。\n"
        "参数 query：必填，单一意图的自然语言查询。max_results：可选，1-10，默认 10。\n"
        "domain 可选用于垂类检索（academic/code/finance/legal/health/travel 等），"
        "但一旦传了 domain，就必须先用 get_sub_domains 拿到 sub_domain 和 sub_domain_params，"
        "否则会失败；普通检索请把 domain、sub_domain、sub_domain_params 全部省略。\n"
        "一次只查一个意图。多个独立查询改用 batch_search。"
    ),
    BATCH_SEARCH: (
        "联网并行搜索（AnySearch）。一条调用同时跑 2-5 个独立查询，比连续调用 search 更省上下文。\n"
        "参数 queries：必填，字符串数组，最多 5 项，每项结构与 search 相同（query 必填；"
        "domain/sub_domain/sub_domain_params 可选，垂类查询同样需要先从 get_sub_domains 取值）。\n"
        "适合横向比较、同一主题多角度调研、general+垂类混合检索。"
    ),
}


def captured_names() -> tuple[str, ...]:
    """返回捕获到的全部工具名。"""
    return tuple(CAPTURED_TOOLS)


def tool_description(name: str) -> str:
    """上游原始描述（可能很长）。"""
    return str(CAPTURED_TOOLS.get(name, {}).get("description", ""))


def llm_description(name: str, *, mode: str = "brief") -> str:
    """按配置返回给 LLM 的描述。"""
    if mode == "full":
        text = tool_description(name)
        if text:
            return text
    return BRIEF_DESCRIPTIONS.get(name, tool_description(name))


def output_schema(name: str) -> dict[str, Any]:
    schema = CAPTURED_TOOLS.get(name, {}).get("outputSchema")
    return schema if isinstance(schema, dict) else {}


def annotations(name: str) -> dict[str, Any]:
    value = CAPTURED_TOOLS.get(name, {}).get("annotations")
    return value if isinstance(value, dict) else {}


def input_schema(name: str) -> dict[str, Any]:
    """上游 inputSchema 原样返回。"""
    schema = CAPTURED_TOOLS.get(name, {}).get("inputSchema")
    return dict(schema) if isinstance(schema, dict) else {}


def llm_tool_definition(name: str, *, description_mode: str = "brief") -> dict[str, Any]:
    """NEKO @llm_tool 用的定义表。"""
    return {
        "name": name,
        "description": llm_description(name, mode=description_mode),
        "parameters": input_schema(name),
    }


def validate_capture() -> list[str]:
    """自检：捕获数据里每个默认工具都有可用的 schema。"""
    problems: list[str] = []
    for name in DEFAULT_TOOLS:
        entry = CAPTURED_TOOLS.get(name)
        if not entry:
            problems.append(f"缺少 {name} 的捕获数据")
            continue
        properties = entry.get("inputSchema", {}).get("properties", {})
        for required_property in _EXPECTED_PROPERTIES[name]:
            if required_property not in properties:
                problems.append(f"{name} 的 schema 缺少属性 {required_property}")
        if not str(entry.get("description", "")).strip():
            problems.append(f"{name} 的捕获数据缺少描述")
    return problems
