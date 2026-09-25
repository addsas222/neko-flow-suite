"""flow_maibot 共享层测试。纯标准库 + asyncio，可直接 python -m unittest 运行。

不联网：桥的端到端测试用假 transport 驱动 McpClient，走的是真实的 MaiBot
插件加载、@Tool 映射与调用派发路径。
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from typing import Annotated

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import schemas  # noqa: E402
from _shared.anysearch import AnySearchGateway  # noqa: E402
from _shared.bridge import (  # noqa: E402
    MaiBotBridge,
    ToolBinding,
    accepts_var_keyword,
    neko_tool_name,
    signature_schema,
)
from _shared.context import PluginContextProxy  # noqa: E402
from _shared.errors import (  # noqa: E402
    AmbiguousPluginError,
    BridgeError,
    CapabilityNotBridgedError,
    ComponentNotFoundError,
    ConfigError,
    McpError,
    NetworkTransportError,
    PluginLoadError,
)
from _shared.mcp_client import McpClient, normalize_tool_result, parse_message, sanitize  # noqa: E402
from _shared.sdk_compat import (  # noqa: E402
    ACTION,
    API,
    API_COMPONENT,
    COMMAND,
    EVENT_HANDLER,
    HOME_CARD,
    HOOK_HANDLER,
    LLM_PROVIDER,
    MESSAGE_GATEWAY,
    TOOL,
    Action,
    Command,
    EventHandler,
    HomeCard,
    HookHandler,
    LLMProvider,
    MaiBotPlugin,
    MessageGateway,
    Tool,
    WorkflowStep,
    collect_components,
    sdk_installed,
)
from _shared.settings import BridgeSettings  # noqa: E402

PLUGIN_DIR = Path(__file__).resolve().parents[1]
BUNDLED = "_shared/maibot_plugins/anysearch_plugin.py"
ENDPOINT = "https://api.anysearch.test/mcp"


def run(coro):
    return asyncio.run(coro)


def config(**anysearch) -> dict:
    return {"anysearch": {"endpoint": ENDPOINT, **anysearch}}


def config_with_bundled(**anysearch) -> dict:
    """显式装载内置 MaiBot 插件的配置（与 plugin.toml 的 [maibot.sdk] 等价）。"""
    return {
        "sdk": {"plugins": [{"path": BUNDLED, "id": "anysearch", "class_name": "AnySearchPlugin"}]},
        "anysearch": {"endpoint": ENDPOINT, **anysearch},
    }


class TestSchemas(unittest.TestCase):
    def test_capture_validates(self) -> None:
        self.assertEqual(schemas.validate_capture(), [])

    def test_capture_holds_both_tools(self) -> None:
        names = schemas.captured_names()
        self.assertIn("search", names)
        self.assertIn("batch_search", names)

    def test_brief_description_is_short_and_names_the_tool(self) -> None:
        brief = schemas.llm_description("search", mode="brief")
        self.assertLess(len(brief), 1200)
        self.assertIn("query", brief)

    def test_full_mode_passes_upstream_description_through(self) -> None:
        self.assertEqual(
            schemas.llm_description("search", mode="full"), schemas.tool_description("search")
        )

    def test_unknown_tool_has_no_description(self) -> None:
        self.assertEqual(schemas.llm_description("nope", mode="brief"), "")

    def test_input_schema_requires_query(self) -> None:
        schema = schemas.input_schema("search")
        self.assertEqual(schema.get("type"), "object")
        self.assertIn("query", schema.get("properties", {}))
        self.assertIn("query", schema.get("required", []))

    def test_batch_schema_requires_queries(self) -> None:
        schema = schemas.input_schema("batch_search")
        self.assertIn("queries", schema.get("properties", {}))
        self.assertIn("queries", schema.get("required", []))

    def test_llm_tool_definition_shape(self) -> None:
        definition = schemas.llm_tool_definition("search", description_mode="brief")
        self.assertEqual(definition["name"], "search")
        self.assertTrue(definition["description"])
        self.assertIn("properties", definition["parameters"])

    def test_input_schema_is_a_copy(self) -> None:
        schema = schemas.input_schema("search")
        schema["mutated"] = True
        self.assertNotIn("mutated", schemas.input_schema("search"))


class TestSettings(unittest.TestCase):
    def test_empty_config_falls_back_to_bundled_anysearch(self) -> None:
        settings = BridgeSettings.from_config({})
        self.assertEqual(len(settings.plugins), 1)
        spec = settings.plugins[0]
        self.assertEqual(spec.id, "anysearch")
        self.assertEqual(spec.class_name, "AnySearchPlugin")
        self.assertTrue(spec.path.endswith("anysearch_plugin.py"))
        self.assertTrue(spec.resolved_path(PLUGIN_DIR).is_file())
        self.assertTrue(settings.enabled)
        self.assertFalse(settings.strict_sdk)

    def test_none_config_is_tolerated(self) -> None:
        self.assertTrue(BridgeSettings.from_config(None).enabled)

    def test_empty_plugins_list_means_bundled_default(self) -> None:
        self.assertEqual(BridgeSettings.from_config({"sdk": {"plugins": []}}).plugins[0].id, "anysearch")

    def test_json_string_config_is_accepted(self) -> None:
        settings = BridgeSettings.from_config('{"anysearch": {"tools": ["search"]}}')
        self.assertEqual(settings.anysearch.tools, ("search",))

    def test_broken_json_string_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config("{not json")

    def test_non_mapping_config_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(["nope"])

    def test_non_mapping_string_config_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config("[1, 2]")

    def test_sdk_section_must_be_a_mapping(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"sdk": "nope"})

    def test_anysearch_section_must_be_a_mapping(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"anysearch": "nope"})

    def test_endpoint_defaults_to_https(self) -> None:
        self.assertTrue(BridgeSettings.from_config({}).anysearch.endpoint.startswith("https://"))

    def test_endpoint_must_be_http(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(config(endpoint="ftp://x.test/mcp"))

    def test_custom_endpoint_kept(self) -> None:
        self.assertEqual(BridgeSettings.from_config(config()).anysearch.endpoint, ENDPOINT)

    def test_unknown_tool_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(config(tools=["search", "nope"]))

    def test_tools_accept_comma_separated_string(self) -> None:
        settings = BridgeSettings.from_config(config(tools="search, batch_search"))
        self.assertEqual(settings.anysearch.tools, ("search", "batch_search"))

    def test_tools_dedupe_keeping_order(self) -> None:
        settings = BridgeSettings.from_config(config(tools=["search", "batch_search", "search"]))
        self.assertEqual(settings.anysearch.tools, ("search", "batch_search"))

    def test_empty_tools_falls_back_to_defaults(self) -> None:
        settings = BridgeSettings.from_config(config(tools=[]))
        self.assertEqual(settings.anysearch.tools, schemas.DEFAULT_TOOLS)

    def test_blank_tool_name_is_dropped(self) -> None:
        settings = BridgeSettings.from_config(config(tools=["search", "  "]))
        self.assertEqual(settings.anysearch.tools, ("search",))

    def test_tools_must_be_list_or_string(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(config(tools=7))

    def test_description_mode_is_validated(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(config(description_mode="verbose"))

    def test_description_mode_accepted(self) -> None:
        settings = BridgeSettings.from_config(config(description_mode="full"))
        self.assertEqual(settings.anysearch.description_mode, "full")

    def test_headers_normalized_to_strings(self) -> None:
        settings = BridgeSettings.from_config(config(headers={"x-probe": 1}))
        self.assertEqual(settings.anysearch.headers, {"x-probe": "1"})

    def test_numeric_bounds_are_clamped(self) -> None:
        settings = BridgeSettings.from_config(
            config(timeout_seconds=9999, max_chars=10, max_results=99)
        )
        self.assertEqual(settings.anysearch.timeout_seconds, 600.0)
        self.assertEqual(settings.anysearch.max_chars, 500)
        self.assertEqual(settings.anysearch.max_results, 10)

    def test_bad_number_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config(config(max_chars="abc"))

    def test_enabled_bridge_false_disables_every_spec(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"enabled_bridge": False}})
        self.assertTrue(settings.plugins)
        self.assertFalse(settings.enabled)
        self.assertTrue(all(not spec.enabled for spec in settings.plugins))

    def test_enabled_bridge_accepts_localized_booleans(self) -> None:
        self.assertTrue(BridgeSettings.from_config({"sdk": {"enabled_bridge": "开启"}}).enabled)
        self.assertFalse(BridgeSettings.from_config({"sdk": {"enabled_bridge": "off"}}).enabled)

    def test_bad_boolean_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"sdk": {"enabled_bridge": "maybe"}})

    def test_strict_sdk_flag(self) -> None:
        self.assertTrue(BridgeSettings.from_config({"sdk": {"strict_sdk": True}}).strict_sdk)

    def test_token_from_api_key(self) -> None:
        settings = BridgeSettings.from_config(config(api_key="k"))
        self.assertEqual(settings.anysearch.token, "k")
        self.assertEqual(settings.anysearch.token_source, "config")

    def test_token_from_environment(self) -> None:
        os.environ["FLOW_MAIBOT_TEST_KEY"] = "from-env"
        try:
            settings = BridgeSettings.from_config(config(api_key_env="FLOW_MAIBOT_TEST_KEY"))
            self.assertEqual(settings.anysearch.token, "from-env")
            self.assertEqual(settings.anysearch.token_source, "env:FLOW_MAIBOT_TEST_KEY")
        finally:
            del os.environ["FLOW_MAIBOT_TEST_KEY"]

    def test_config_key_wins_over_environment(self) -> None:
        os.environ["FLOW_MAIBOT_TEST_KEY"] = "from-env"
        try:
            settings = BridgeSettings.from_config(
                config(api_key="direct", api_key_env="FLOW_MAIBOT_TEST_KEY")
            )
            self.assertEqual(settings.anysearch.token, "direct")
            self.assertEqual(settings.anysearch.token_source, "config")
        finally:
            del os.environ["FLOW_MAIBOT_TEST_KEY"]
    def test_plugins_as_string_becomes_one_spec(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": BUNDLED}})
        self.assertEqual(len(settings.plugins), 1)
        self.assertEqual(settings.plugins[0].id, "anysearch_plugin")
        self.assertTrue(settings.plugins[0].resolved_path(PLUGIN_DIR).is_file())

    def test_bundled_alias_by_plugin_id(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": ["AnySearch"]}})
        self.assertEqual(settings.plugins[0].id, "anysearch")
        self.assertEqual(settings.plugins[0].path, BUNDLED)

    def test_bundled_alias_by_class_name(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": ["AnySearchPlugin"]}})
        self.assertEqual(settings.plugins[0].id, "anysearch")
        self.assertTrue(settings.plugins[0].resolved_path(PLUGIN_DIR).is_file())

    def test_bundled_alias_is_case_insensitive(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": ["anysearch"]}})
        self.assertEqual(settings.plugins[0].path, BUNDLED)

    def test_bundled_alias_in_entry_form(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": [{"path": "AnySearch"}]}})
        self.assertEqual(settings.plugins[0].path, BUNDLED)

    def test_unknown_path_is_left_to_the_loader(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": ["some/other.py"]}})
        self.assertEqual(settings.plugins[0].path, "some/other.py")

    def test_blank_plugin_string_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"sdk": {"plugins": ["   "]}})

    def test_plugins_entry_selects_class_and_config(self) -> None:
        settings = BridgeSettings.from_config(
            {
                "sdk": {
                    "plugins": [
                        {
                            "path": BUNDLED,
                            "class_name": "AnySearchPlugin",
                            "enabled": False,
                            "config": {"anysearch": {"tools": ["search"]}},
                        }
                    ]
                }
            }
        )
        spec = settings.plugins[0]
        self.assertEqual(spec.class_name, "AnySearchPlugin")
        self.assertFalse(spec.enabled)
        self.assertEqual(spec.config, {"anysearch": {"tools": ["search"]}})

    def test_plugins_entry_defaults_id_to_file_stem(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"plugins": [{"path": BUNDLED}]}})
        self.assertEqual(settings.plugins[0].id, "anysearch_plugin")

    def test_plugins_entry_needs_path(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"sdk": {"plugins": [{"id": "x"}]}})

    def test_plugins_must_be_a_list(self) -> None:
        with self.assertRaises(ConfigError):
            BridgeSettings.from_config({"sdk": {"plugins": 3}})

    # -- plugin.toml 的 [maibot] 三种等价写法 -------------------------------- #

    def test_plugin_toml_wrapper_table_is_unwrapped(self) -> None:
        """plugin.toml 里声明的配置必须真的生效，不能静默丢失。"""
        settings = BridgeSettings.from_config(
            {
                "maibot": {
                    "sdk": {"strict_sdk": True, "plugins": [BUNDLED]},
                    "anysearch": {"endpoint": ENDPOINT, "tools": ["search"]},
                }
            }
        )
        self.assertTrue(settings.strict_sdk)
        self.assertEqual(settings.plugins[0].path, BUNDLED)
        self.assertEqual(settings.anysearch.tools, ("search",))

    def test_wrapped_and_flat_shapes_agree(self) -> None:
        nested = BridgeSettings.from_config(config_with_bundled(tools=["search"]))
        wrapped = BridgeSettings.from_config(
            {
                "maibot": {
                    "sdk": {"plugins": [{"path": BUNDLED, "id": "anysearch"}]},
                    "anysearch": {"endpoint": ENDPOINT, "tools": ["search"]},
                }
            }
        )
        self.assertEqual(nested.anysearch, wrapped.anysearch)

    def test_flat_shape_hoists_sdk_keys(self) -> None:
        """plugin.toml 注释承诺的平铺写法：sdk 键直接写在段下。"""
        settings = BridgeSettings.from_config(
            {
                "enabled": False,
                "strict_sdk": True,
                "plugins": ["AnySearch"],
                "anysearch.endpoint": ENDPOINT,
                "anysearch.tools": ["search"],
            }
        )
        self.assertFalse(settings.enabled)
        self.assertTrue(settings.strict_sdk)
        self.assertEqual(settings.plugins[0].path, BUNDLED)
        self.assertEqual(settings.anysearch.endpoint, ENDPOINT)
        self.assertEqual(settings.anysearch.tools, ("search",))

    def test_flat_dotted_keys_merge_into_the_section(self) -> None:
        settings = BridgeSettings.from_config(
            {"anysearch": {"endpoint": ENDPOINT}, "anysearch.tools": ["search"]}
        )
        self.assertEqual(settings.anysearch.tools, ("search",))

    def test_explicit_sdk_key_wins_over_the_flat_one(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"strict_sdk": True}, "strict_sdk": False})
        self.assertTrue(settings.strict_sdk)

    def test_flat_shape_still_wins(self) -> None:
        settings = BridgeSettings.from_config(
            {"sdk": {"strict_sdk": False}, "anysearch": {"endpoint": ENDPOINT}, "junk": {"sdk": {}}}
        )
        self.assertFalse(settings.strict_sdk)
        self.assertEqual(settings.anysearch.endpoint, ENDPOINT)

    def test_unrelated_table_is_left_alone(self) -> None:
        settings = BridgeSettings.from_config({"unrelated": {"anything": 1}})
        self.assertEqual(settings.plugins[0].id, "anysearch")

    def test_non_mapping_table_is_left_alone(self) -> None:
        settings = BridgeSettings.from_config({"unrelated": "text"})
        self.assertEqual(settings.plugins[0].id, "anysearch")

    def test_missing_token_reports_none(self) -> None:
        settings = BridgeSettings.from_config(config(api_key_env="FLOW_MAIBOT_ABSENT"))
        self.assertEqual(settings.anysearch.token, "")
        self.assertEqual(settings.anysearch.token_source, "none")


class TestErrors(unittest.TestCase):
    def test_every_error_has_a_distinct_code(self) -> None:
        codes = [
            BridgeError.code,
            ConfigError.code,
            McpError.code,
            NetworkTransportError.code,
            PluginLoadError.code,
            ComponentNotFoundError.code,
            AmbiguousPluginError.code,
            CapabilityNotBridgedError.code,
        ]
        self.assertEqual(len(codes), len(set(codes)))

    def test_to_dict_carries_code_and_message(self) -> None:
        payload = ConfigError("配置坏了").to_dict()
        self.assertEqual(payload["code"], "config_error")
        self.assertEqual(payload["error"], "配置坏了")
        self.assertNotIn("detail", payload)

    def test_detail_only_when_present(self) -> None:
        payload = PluginLoadError("导入失败", detail="ImportError").to_dict()
        self.assertEqual(payload["detail"], "ImportError")

    def test_str_is_the_message(self) -> None:
        error = McpError("连不上")
        self.assertEqual(str(error), "连不上")
        self.assertIsInstance(error, BridgeError)

    def test_subclass_keeps_its_own_code(self) -> None:
        self.assertEqual(NetworkTransportError("x").code, "mcp_transport_error")


class TestMcpHelpers(unittest.TestCase):
    def test_sanitize_masks_long_secrets_only(self) -> None:
        self.assertEqual(sanitize("key=abcdefghij", ("abcdefghij",)), "key=***")
        self.assertEqual(sanitize("key=short", ("short",)), "key=short")

    def test_sanitize_without_secrets_is_a_noop(self) -> None:
        self.assertEqual(sanitize("plain text"), "plain text")

    def test_sanitize_ignores_empty_secret(self) -> None:
        self.assertEqual(sanitize("text", ("", None)), "text")

    def test_parse_plain_json(self) -> None:
        self.assertEqual(parse_message('{"result": {"ok": true}}'), {"result": {"ok": True}})

    def test_parse_sse_takes_the_last_parsable_message(self) -> None:
        body = "event: message\nid: 1\ndata: {\"a\": 1}\n\ndata: {\"a\": 2}\n\n"
        self.assertEqual(parse_message(body), {"a": 2})

    def test_parse_sse_ignores_comments(self) -> None:
        self.assertEqual(parse_message(": keep-alive\ndata: {\"a\": 1}\n"), {"a": 1})

    def test_parse_sse_without_json_raises(self) -> None:
        with self.assertRaises(McpError):
            parse_message("event: ping\ndata: not json\n")

    def test_parse_empty_body_raises(self) -> None:
        with self.assertRaises(McpError):
            parse_message("   ")

    def test_parse_garbage_raises(self) -> None:
        with self.assertRaises(McpError):
            parse_message("<html>nope</html>")

    def test_parse_non_object_raises(self) -> None:
        with self.assertRaises(McpError):
            parse_message("[1, 2]")

    def test_normalize_joins_text_blocks(self) -> None:
        result = normalize_tool_result(
            {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
        )
        self.assertEqual(result["text"], "a\n\nb")
        self.assertFalse(result["is_error"])
        self.assertFalse(result["truncated"])

    def test_normalize_ignores_non_text_blocks(self) -> None:
        result = normalize_tool_result({"content": [{"type": "image", "data": "xxx"}]})
        self.assertEqual(result["blocks"], [{"type": "image", "data": "xxx"}])
        self.assertIn("content", result["text"])

    def test_normalize_flags_errors(self) -> None:
        result = normalize_tool_result(
            {"isError": True, "content": [{"type": "text", "text": "boom"}]}
        )
        self.assertTrue(result["is_error"])
        self.assertEqual(result["text"], "boom")

    def test_normalize_truncates_long_text(self) -> None:
        result = normalize_tool_result({"content": [{"type": "text", "text": "x" * 50}]}, max_chars=10)
        self.assertEqual(result["text"], "x" * 10)
        self.assertTrue(result["truncated"])

    def test_normalize_keeps_structured_content(self) -> None:
        self.assertEqual(normalize_tool_result({"structuredContent": {"a": 1}})["structured"], {"a": 1})

    def test_normalize_survives_odd_input(self) -> None:
        self.assertEqual(normalize_tool_result("nope")["text"], "")
        self.assertEqual(normalize_tool_result(None)["truncated"], False)

    def test_client_requires_endpoint(self) -> None:
        client = McpClient("")
        with self.assertRaises(McpError):
            run(client._exchange("initialize", {}))


class TestBridgeHelpers(unittest.TestCase):
    def test_tool_name_joins_with_dot(self) -> None:
        self.assertEqual(neko_tool_name("anysearch", "search"), "anysearch.search")

    def test_tool_name_slugs_illegal_characters(self) -> None:
        self.assertEqual(neko_tool_name("my plugin!", "do/thing"), "my_plugin.do_thing")

    def test_tool_name_rejects_empty_parts(self) -> None:
        self.assertEqual(neko_tool_name("", "search"), "")
        self.assertEqual(neko_tool_name("anysearch", "!!!"), "")

    def test_tool_name_rejects_over_long_names(self) -> None:
        self.assertEqual(neko_tool_name("a" * 60, "b" * 20), "")

    def test_signature_schema_marks_required_and_types(self) -> None:
        def method(query: str, max_results: int = 5, **kwargs) -> None:
            del query, max_results, kwargs

        schema = signature_schema(method)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["query"], {"type": "string"})
        self.assertEqual(schema["properties"]["max_results"], {"type": "integer"})
        self.assertNotIn("kwargs", schema["properties"])
        self.assertEqual(schema["required"], ["query"])

    def test_signature_schema_reads_annotated_description(self) -> None:
        def method(query: Annotated[str, "搜索词"]) -> None:
            del query

        prop = signature_schema(method)["properties"]["query"]
        self.assertEqual(prop["type"], "string")
        self.assertEqual(prop["description"], "搜索词")

    def test_signature_schema_unions_optional_away(self) -> None:
        from typing import Optional

        def method(query: Optional[str] = None) -> None:
            del query

        self.assertEqual(signature_schema(method)["properties"]["query"]["type"], "string")

    def test_signature_schema_unions_pep604_optional_away(self) -> None:
        def method(query: str | None = None) -> None:
            del query

        self.assertEqual(signature_schema(method)["properties"]["query"]["type"], "string")

    def test_signature_schema_all_none_union_has_no_type(self) -> None:
        def method(query: "str | None" = None) -> None:
            del query

        self.assertNotIn("type", signature_schema(method)["properties"]["query"])

    def test_signature_schema_skips_private_and_self(self) -> None:
        def method(self, _hidden: str, visible: str) -> None:  # noqa: N805
            del self, _hidden, visible

        self.assertEqual(list(signature_schema(method)["properties"]), ["visible"])

    def test_signature_schema_survives_non_callable(self) -> None:
        self.assertEqual(signature_schema("nope"), {})

    def test_accepts_var_keyword(self) -> None:
        def with_kwargs(**kwargs) -> None:
            del kwargs

        def without(*, only: str) -> None:
            del only

        self.assertTrue(accepts_var_keyword(with_kwargs))
        self.assertFalse(accepts_var_keyword(without))

    def test_tool_binding_definitions(self) -> None:
        binding = ToolBinding(
            plugin_id="anysearch",
            component="search",
            name="anysearch.search",
            description="搜索",
            parameters={"type": "object"},
            schema_source="schemas",
        )
        definition = binding.to_definition()
        self.assertEqual(definition["name"], "anysearch.search")
        self.assertEqual(definition["plugin_id"], "anysearch")
        self.assertEqual(definition["schema_source"], "schemas")
        self.assertEqual(
            binding.to_capability_definition(),
            {"name": "anysearch.search", "description": "搜索", "parameters": {"type": "object"}},
        )


class TestSdkCompat(unittest.TestCase):
    def test_sdk_installed_returns_bool(self) -> None:
        self.assertIsInstance(sdk_installed(), bool)

    def test_tool_records_component_info(self) -> None:
        @Tool(name="search", description="搜索", parameters={"type": "object"})
        async def search(query: str) -> dict:
            del query
            return {}

        info = getattr(search, "__maibot_component_info__", None)
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "search")
        self.assertEqual(info.type, "TOOL")
        self.assertEqual(info.parameters_raw, {"type": "object"})
        self.assertEqual(info.invoke_method, "plugin.invoke_tool")

    def test_tool_defaults_name_to_function(self) -> None:
        @Tool(name="")
        async def lookup() -> None:
            return None

        self.assertEqual(getattr(lookup, "__maibot_component_info__").name, "lookup")

    def test_tool_brief_falls_back_to_description(self) -> None:
        @Tool(name="alpha", description="描述")
        async def alpha() -> None:
            return None

        self.assertEqual(getattr(alpha, "__maibot_component_info__").brief_description, "描述")

    def test_action_is_tool_equivalent_and_keeps_metadata(self) -> None:
        """Action 必须和 Tool 等价，且不能丢调用方给的 metadata（曾是 F823 真 bug）。"""

        @Action(name="act", description="做点什么", brief_description="简报", flagged=True)
        async def act() -> None:
            return None

        info = getattr(act, "__maibot_component_info__")
        self.assertEqual(info.type, TOOL)
        self.assertEqual(info.name, "act")
        self.assertEqual(info.invoke_method, "plugin.invoke_tool")
        self.assertEqual(info.metadata.get("legacy_component_type"), ACTION)
        self.assertEqual(info.metadata.get("flagged"), True)

    def test_action_collects_as_a_tool_component(self) -> None:
        class Plugin(MaiBotPlugin):
            @Action(name="alpha")
            async def alpha(self) -> None:
                return None

        found = collect_components(Plugin())
        self.assertEqual([(item.type, item.name) for item in found], [(TOOL, "alpha")])

    def test_command_records_its_pattern(self) -> None:
        @Command(name="ping", pattern=r"^ping$", aliases=["p"])
        async def ping() -> None:
            return None

        info = getattr(ping, "__maibot_component_info__")
        self.assertEqual(info.type, COMMAND)
        self.assertEqual(info.name, "ping")
        self.assertEqual(info.invoke_method, "plugin.invoke_command")
        self.assertEqual(info.metadata.get("command_pattern"), r"^ping$")
        self.assertEqual(info.metadata.get("aliases"), ["p"])

    def test_api_records_version_and_visibility(self) -> None:
        @API(name="lookup", version="2", public=True)
        async def lookup() -> None:
            return None

        info = getattr(lookup, "__maibot_component_info__")
        self.assertEqual(info.type, API_COMPONENT)
        self.assertEqual(info.version, "2")
        self.assertTrue(info.public)
        self.assertEqual(info.invoke_method, "plugin.invoke_api")

    def test_every_component_type_is_a_plain_string(self) -> None:
        """常量与工厂同名会让 type 变成函数对象；这里把每类都钉成字符串。"""
        cases = [
            (TOOL, Tool(name="a"), "plugin.invoke_tool"),
            (TOOL, Action(name="b"), "plugin.invoke_tool"),  # Action 归一为 Tool
            (COMMAND, Command(name="c"), "plugin.invoke_command"),
            (API_COMPONENT, API(name="d"), "plugin.invoke_api"),
            (EVENT_HANDLER, EventHandler(name="e", event_type="x"), "plugin.invoke_event"),
            (HOOK_HANDLER, HookHandler(name="f", hook="before_send"), "plugin.invoke_hook"),
            (
                MESSAGE_GATEWAY,
                MessageGateway("http", name="g"),
                "plugin.invoke_message_gateway",
            ),
            (
                LLM_PROVIDER,
                LLMProvider(name="h", client_type="openai"),
                "plugin.invoke_llm_provider",
            ),
            (HOME_CARD, HomeCard(name="i", title="卡片"), "plugin.invoke_home_card"),
        ]
        for expected, decorator, invoke_method in cases:
            with self.subTest(component=expected):

                @decorator
                async def handler() -> None:
                    return None

                info = getattr(handler, "__maibot_component_info__")
                self.assertIsInstance(info.type, str, f"{expected} 的 type 必须是字符串")
                self.assertEqual(info.type, expected)
                self.assertEqual(info.invoke_method, invoke_method)
                self.assertEqual(info.to_dict()["type"], expected)

    def test_collect_components_groups_by_string_type(self) -> None:
        class Plugin(MaiBotPlugin):
            @Tool(name="alpha")
            async def alpha(self) -> None:
                return None

            @API(name="beta")
            async def beta(self) -> None:
                return None

        types = {info.name: info.type for info in collect_components(Plugin())}
        self.assertEqual(types, {"alpha": TOOL, "beta": API_COMPONENT})

    def test_dynamic_api_registration_returns_a_string_type(self) -> None:
        plugin = MaiBotPlugin()

        async def handler(**_kwargs):
            return {"ok": True}

        declaration = plugin.register_dynamic_api("ping", handler, version="1")
        self.assertEqual(declaration["type"], API_COMPONENT)
        stored = plugin.get_dynamic_api_components()[0]
        self.assertEqual(stored["type"], API_COMPONENT)
        self.assertEqual(stored["name"], "ping")
        self.assertIn("handler_name", stored["metadata"])
        self.assertEqual(plugin.unregister_dynamic_api("ping"), True)

    def test_dynamic_api_requires_a_name(self) -> None:
        plugin = MaiBotPlugin()

        async def handler(**_kwargs):
            return {"ok": True}

        with self.assertRaises(ValueError):
            plugin.register_dynamic_api("   ", handler)

    def test_workflow_step_is_removed(self) -> None:
        with self.assertRaises(RuntimeError):
            WorkflowStep()

    def test_collect_components_finds_decorated_tools(self) -> None:
        class Plugin(MaiBotPlugin):
            @Tool(name="alpha")
            async def alpha(self) -> None:
                return None

            @Tool(name="beta")
            async def beta(self) -> None:
                return None

        self.assertEqual([info.name for info in collect_components(Plugin())], ["alpha", "beta"])

    def test_collect_components_dedupes_overrides(self) -> None:
        class Base(MaiBotPlugin):
            @Tool(name="shared")
            async def shared(self) -> None:
                return None

        class Child(Base):
            @Tool(name="shared")
            async def shared(self) -> None:  # noqa: F811
                return None

        self.assertEqual([info.name for info in collect_components(Child())], ["shared"])

    def test_collect_components_skips_undecorated(self) -> None:
        class Plugin(MaiBotPlugin):
            async def plain(self) -> None:
                return None

        self.assertEqual(collect_components(Plugin()), [])

    def test_plugin_base_tolerates_extra_init_arguments(self) -> None:
        plugin = MaiBotPlugin("positional", injected=1)
        self.assertEqual(plugin.get_plugin_config_data(), {})


class TestAnySearchGateway(unittest.TestCase):
    def _settings(self, **anysearch):
        return BridgeSettings.from_config(config(**anysearch)).anysearch

    def test_requires_endpoint(self) -> None:
        """endpoint 空串会退回默认值，所以构造门槛由 from_config 兜底。"""
        self.assertTrue(self._settings(endpoint="").endpoint)

    def test_empty_endpoint_falls_back_to_default(self) -> None:
        settings = BridgeSettings.from_config(config(endpoint=""))
        self.assertTrue(settings.anysearch.endpoint.startswith("https://"))

    def test_settings_object_requires_an_endpoint(self) -> None:
        from _shared.settings import AnySearchSettings

        with self.assertRaises(ConfigError):
            AnySearchGateway(AnySearchSettings(endpoint=""))

    def test_describe_never_leaks_the_token(self) -> None:
        gateway = AnySearchGateway(self._settings(api_key="super-secret-token"))
        self.assertTrue(gateway.token_available)
        describe = gateway.describe()
        self.assertEqual(describe["token_available"], True)
        self.assertEqual(describe["token_source"], "config")
        self.assertNotIn("super-secret-token", repr(describe))

    def test_describe_reports_settings(self) -> None:
        gateway = AnySearchGateway(self._settings(description_mode="full", max_results=4))
        describe = gateway.describe()
        self.assertEqual(describe["endpoint"], ENDPOINT)
        self.assertEqual(describe["description_mode"], "full")
        self.assertEqual(describe["max_results"], 4)
        self.assertEqual(describe["tools"], ["search", "batch_search"])

    def test_token_absent_is_reported_as_false(self) -> None:
        self.assertFalse(AnySearchGateway(self._settings()).token_available)

    def test_pick_drops_empty_values(self) -> None:
        gateway = AnySearchGateway(self._settings(max_results=6))
        payload = gateway._pick({"query": "x", "domain": "", "max_results": None}, ("query", "domain"))
        self.assertEqual(payload, {"query": "x", "max_results": 6})

    def test_pick_clamps_max_results(self) -> None:
        gateway = AnySearchGateway(self._settings(max_results=3))
        self.assertEqual(gateway._pick({"max_results": 99}, ("max_results",))["max_results"], 3)

    def test_pick_rejects_non_numeric_max_results(self) -> None:
        gateway = AnySearchGateway(self._settings())
        with self.assertRaises(McpError):
            gateway._pick({"max_results": "many"}, ("max_results",))

    def test_call_rejects_disabled_tool(self) -> None:
        gateway = AnySearchGateway(self._settings(tools=["search"]))
        with self.assertRaises(McpError):
            run(gateway.call("batch_search", {"queries": ["a", "b"]}))

    def test_search_requires_query(self) -> None:
        gateway = AnySearchGateway(self._settings())
        with self.assertRaises(McpError):
            run(gateway.search({"query": "   "}))

    def test_batch_search_requires_at_least_two(self) -> None:
        gateway = AnySearchGateway(self._settings())
        with self.assertRaises(McpError):
            run(gateway.batch_search({"queries": ["only one"]}))

    def test_batch_search_normalizes_strings(self) -> None:
        gateway = AnySearchGateway(self._settings(max_results=5))
        self.assertEqual(gateway._normalize_queries([" a ", "b"]), [{"query": "a"}, {"query": "b"}])

    def test_batch_search_rejects_bad_entries(self) -> None:
        gateway = AnySearchGateway(self._settings())
        with self.assertRaises(McpError):
            gateway._normalize_queries(["", "b"])
        with self.assertRaises(McpError):
            gateway._normalize_queries([{"query": ""}, {"query": "b"}])
        with self.assertRaises(McpError):
            gateway._normalize_queries([1, 2])

    def test_batch_search_caps_at_five_entries(self) -> None:
        gateway = AnySearchGateway(self._settings())
        self.assertEqual(len(gateway._normalize_queries([str(i) for i in range(8)])), 5)

    def test_clip_truncates_long_text(self) -> None:
        gateway = AnySearchGateway(self._settings(max_chars=500))
        clipped = gateway._clip({"text": "x" * 900})
        self.assertEqual(clipped["text"], "x" * 500)
        self.assertTrue(clipped["truncated"])

    def test_clip_leaves_short_text_alone(self) -> None:
        gateway = AnySearchGateway(self._settings(max_chars=50))
        self.assertEqual(gateway._clip({"text": "ok"}), {"text": "ok"})

    def test_search_end_to_end_through_fake_transport(self) -> None:
        calls = []

        def transport(url, body, headers, timeout):
            del url, timeout
            calls.append((body, dict(headers)))
            return 200, {}, '{"result": {"content": [{"type": "text", "text": "answer"}]}}'

        settings = self._settings(api_key="token-1234", max_results=2)
        gateway = AnySearchGateway(settings, transport=transport)
        result = run(gateway.search({"query": "who", "max_results": 99}))
        self.assertEqual(result["text"], "answer")
        self.assertFalse(result["is_error"])
        self.assertFalse(result["truncated"])
        self.assertIn(b"initialize", calls[0][0])
        self.assertNotIn(b"token-1234", calls[0][0])
        self.assertEqual(calls[0][1]["Authorization"], "Bearer token-1234")

    def test_http_error_is_masked(self) -> None:
        def transport(url, body, headers, timeout):
            del url, body, headers, timeout
            return 401, {}, "invalid token token-1234"

        gateway = AnySearchGateway(self._settings(api_key="token-1234"), transport=transport)
        with self.assertRaises(BridgeError) as caught:
            run(gateway.search({"query": "who"}))
        self.assertEqual(caught.exception.code, "mcp_error")
        self.assertNotIn("token-1234", str(caught.exception))

    def test_transport_failure_becomes_transport_error(self) -> None:
        import urllib.error

        def transport(url, body, headers, timeout):
            del url, body, headers, timeout
            raise urllib.error.URLError("dns dead")

        gateway = AnySearchGateway(self._settings(), transport=transport)
        with self.assertRaises(NetworkTransportError):
            run(gateway.search({"query": "who"}))

    def test_transport_timeout_is_named_as_such(self) -> None:
        import urllib.error

        def transport(url, body, headers, timeout):
            del url, body, headers, timeout
            raise urllib.error.URLError(TimeoutError("too slow"))

        gateway = AnySearchGateway(self._settings(), transport=transport)
        with self.assertRaises(NetworkTransportError) as caught:
            run(gateway.search({"query": "who"}))
        self.assertIn("超时", str(caught.exception))


async def _boom(capability, payload):
    del payload
    raise CapabilityNotBridgedError(f"not bridged: {capability}")


class TestPluginContextProxy(unittest.TestCase):
    def _proxy(self, gateway=None, **kwargs):
        return PluginContextProxy(plugin_id="anysearch", gateway=gateway or _boom, **kwargs)

    def test_known_capability_is_proxied_and_cached(self) -> None:
        proxy = self._proxy()
        self.assertEqual(proxy.capability("tool").name, "tool")
        self.assertIs(proxy.capability("tool"), proxy.tool)

    def test_unknown_capability_is_refused(self) -> None:
        proxy = self._proxy()
        with self.assertRaises(CapabilityNotBridgedError):
            proxy.teleport

    def test_underscore_attribute_is_not_a_capability(self) -> None:
        """ctx 上的私有名一律拒绝，不能变成一次网关调用。"""
        proxy = self._proxy()
        with self.assertRaises(CapabilityNotBridgedError):
            proxy._undefined
        with self.assertRaises(AttributeError):
            proxy.tool._hidden

    def test_degraded_mode_returns_none_on_unbridged_capability(self) -> None:
        proxy = self._proxy()
        self.assertIsNone(run(proxy.call_capability("tool.not_invented_yet")))

    def test_strict_mode_propagates_unbridged_capability(self) -> None:
        proxy = self._proxy(strict=True)
        with self.assertRaises(CapabilityNotBridgedError):
            run(proxy.call_capability("tool.not_invented_yet"))

    def test_capability_call_forwards_arguments(self) -> None:
        seen = []

        async def gateway(capability, payload):
            seen.append((capability, payload))
            return {"ok": True}

        proxy = self._proxy(gateway)
        self.assertEqual(run(proxy.tool.list(**{"limit": 2})), {"ok": True})
        self.assertEqual(seen, [("tool.list", {"limit": 2})])

    def test_capability_call_rejects_positional_arguments(self) -> None:
        async def gateway(capability, payload):
            del capability, payload
            return None

        proxy = self._proxy(gateway)
        with self.assertRaises(TypeError):
            run(proxy.tool.list("positional"))

    def test_unknown_capability_prefix_is_refused(self) -> None:
        proxy = self._proxy()
        with self.assertRaises(CapabilityNotBridgedError):
            run(proxy.call_capability("nope.whatever"))

    def test_call_capability_rejects_positional_arguments(self) -> None:
        async def gateway(capability, payload):
            del capability, payload
            return None

        proxy = self._proxy(gateway)
        with self.assertRaises(TypeError):
            run(proxy.call_capability("tool.list", "positional"))

    def test_call_host_method_whitelist(self) -> None:
        async def gateway(capability, payload):
            del capability, payload
            return "allowed"

        proxy = self._proxy(gateway)
        self.assertEqual(run(proxy.call_host_method("person.get_id")), "allowed")
        with self.assertRaises(PermissionError):
            run(proxy.call_host_method("shell.exec"))

    def test_call_host_method_refuses_cross_plugin_ids(self) -> None:
        async def gateway(capability, payload):
            del capability, payload
            return None

        proxy = self._proxy(gateway)
        with self.assertRaises(PermissionError):
            run(proxy.call_host_method("person.get_id", plugin_id="other"))

    def test_config_model_is_refused(self) -> None:
        proxy = self._proxy()
        with self.assertRaises(CapabilityNotBridgedError):
            proxy.config

    def test_plugin_config_round_trip(self) -> None:
        proxy = self._proxy()
        proxy.set_plugin_config({"tools": ["search"]})
        self.assertEqual(proxy.get_plugin_config_data(), {"tools": ["search"]})
        proxy.set_plugin_config("not a mapping")
        self.assertEqual(proxy.get_plugin_config_data(), {})

    def test_paths_default_to_maibot_convention(self) -> None:
        proxy = self._proxy()
        self.assertTrue(proxy.data_dir.endswith("data/plugins"))
        self.assertTrue(proxy.runtime_dir.endswith("temp/plugins"))

    def test_invoke_component_requires_an_invoker(self) -> None:
        async def invoker(name, kwargs):
            del name, kwargs
            return "invoked"

        proxy = self._proxy(invoker=invoker)
        self.assertEqual(run(proxy.invoke_component("search", query="x")), "invoked")
        closed = self._proxy()
        with self.assertRaises(CapabilityNotBridgedError):
            run(closed.invoke_component("search"))


class _CaptureStub:
    """用捕获件覆盖 schema；只对 anysearch 的 search 生效，其余交给装饰器。"""

    def lookup(self, plugin_id, component):
        if plugin_id == "anysearch" and component == "search":
            return {
                "description": "联网搜索（AnySearch）",
                "parameters": schemas.input_schema("search"),
            }
        return None


def _ok_transport(url, body, headers, timeout):
    del url, headers, timeout
    if b"tools/call" in body:
        return 200, {}, '{"result": {"content": [{"type": "text", "text": "answer"}]}}'
    return 200, {}, '{"result": {"tools": []}}'


def _failing_transport(url, body, headers, timeout):
    del url, body, headers, timeout
    return 500, {}, '{"error": {"code": -32000, "message": "upstream down"}}'


class TestBridgeEndToEnd(unittest.TestCase):
    """走真实路径：配置 -> 加载 MaiBot 插件 -> @Tool 映射 -> 调用派发。"""

    def _bridge(self, settings, transport, capability_handler=None):
        gateway = AnySearchGateway(settings.anysearch, transport=transport)
        return MaiBotBridge(
            settings,
            base_dir=PLUGIN_DIR,
            backend=gateway,
            capability_handler=capability_handler,
            schema_sources=[_CaptureStub()],
        )

    def test_loads_bundled_plugin_and_maps_two_tools(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled(api_key="token-1234"))

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            status = await bridge.load()
            return bridge, status

        bridge, status = run(scenario())
        self.assertEqual(status["problems"], [])
        self.assertEqual(
            sorted(item["name"] for item in bridge.tools()),
            ["anysearch.batch_search", "anysearch.search"],
        )
        self.assertEqual(bridge.resolve("anysearch.search"), ("anysearch", "search"))
        self.assertEqual([item["id"] for item in bridge.component_list()], ["anysearch"])
        self.assertEqual(bridge.backend_info()["token_available"], True)

    def test_bundled_spec_id_is_anysearch(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())
        self.assertEqual([spec.id for spec in settings.plugins], ["anysearch"])

    def test_alias_declaration_loads_the_same_tool_names(self) -> None:
        """写 "AnySearch" 别名和写完整路径，桥出来的工具名必须一致。"""
        alias = BridgeSettings.from_config({"sdk": {"plugins": ["AnySearch"]}})
        explicit = BridgeSettings.from_config({"sdk": {"plugins": [BUNDLED]}})
        self.assertEqual(
            alias.plugins[0].resolved_path(PLUGIN_DIR),
            explicit.plugins[0].resolved_path(PLUGIN_DIR),
        )
        self.assertEqual(alias.plugins[0].id, explicit.plugins[0].id.replace("anysearch_plugin", "anysearch"))
        self.assertEqual(alias.plugins[0].id, "anysearch")

        async def scenario():
            bridge = self._bridge(alias, _ok_transport)
            await bridge.load()
            return sorted(item["name"] for item in bridge.tools())

        self.assertEqual(run(scenario()), ["anysearch.batch_search", "anysearch.search"])

    def test_captured_schema_wins_over_the_decorator(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return {item["name"]: item for item in bridge.tools()}

        search = run(scenario())["anysearch.search"]
        self.assertEqual(search["schema_source"], "schemas")
        self.assertIn("query", search["parameters"].get("properties", {}))

    def test_decorator_schema_used_without_a_capture_override(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return {item["name"]: item for item in bridge.tools()}

        batch = run(scenario())["anysearch.batch_search"]
        self.assertEqual(batch["schema_source"], "decorator")
        self.assertIn("queries", batch["parameters"].get("properties", {}))

    def test_invoke_tool_returns_llm_payload(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return await bridge.invoke_tool("anysearch.search", {"query": "who"})

        result = run(scenario())
        self.assertFalse(result["is_error"])
        self.assertEqual(result["text"], "answer")
        self.assertFalse(result["truncated"])

    def test_invoke_tool_masks_unknown_tool(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return await bridge.invoke_tool("anysearch.absent", {})

        result = run(scenario())
        self.assertTrue(result["is_error"])
        self.assertEqual(result["error"], "component_not_found")

    def test_invoke_tool_masks_backend_errors(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _failing_transport)
            await bridge.load()
            return await bridge.invoke_tool("anysearch.search", {"query": "who"})

        self.assertTrue(run(scenario())["is_error"])

    def test_missing_query_is_a_tool_error_not_a_crash(self) -> None:
        """缺必填参数不许把宿主打爆：收敛成 is_error 的工具结果。"""
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return await bridge.invoke_tool("anysearch.search", {})

        result = run(scenario())
        self.assertTrue(result["is_error"])
        self.assertTrue(result["output"]["reason"])

    def test_disabled_bridge_loads_nothing(self) -> None:
        settings = BridgeSettings.from_config({"sdk": {"enabled_bridge": False}})

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            status = await bridge.load()
            await bridge.unload()
            return status

        self.assertEqual(run(scenario())["problems"], ["桥接层已停用"])

    def test_missing_plugin_file_becomes_a_problem(self) -> None:
        settings = BridgeSettings.from_config(
            '{"sdk": {"plugins": ["_shared/maibot_plugins/absent.py"]}}'
        )

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            return await bridge.load()

        status = run(scenario())
        self.assertTrue(any("absent" in problem for problem in status["problems"]))
        self.assertEqual(status["tools"], [])

    def _ctx_bridge(self, settings, capability_handler=None):
        """造一个带 ctx 能力转发的桥；handler 的语义与 _runtime.MaibotRuntime 一致。"""

        async def handler(plugin_id, capability, payload=None):
            data = dict(payload or {})
            if capability in {"tool.get_definitions", "tool_definitions", "get_definitions"}:
                return target.tool_definitions_for(plugin_id)
            if capability in {"tool.list", "tools"}:
                return {"tools": target.tools()}
            if capability in {"tool.call", "invoke"}:
                return await target.invoke_tool(
                    str(data.get("tool") or data.get("name") or ""), data.get("arguments") or data
                )
            raise CapabilityNotBridgedError(f"ctx.{capability} 未桥接到 NEKO 宿主")

        gateway = AnySearchGateway(settings.anysearch, transport=_ok_transport)
        target = MaiBotBridge(
            settings,
            base_dir=PLUGIN_DIR,
            backend=gateway,
            capability_handler=capability_handler or handler,
            schema_sources=[_CaptureStub()],
        )
        return target

    def test_capability_handler_bridges_ctx_calls(self) -> None:
        seen = []

        async def handler(plugin_id, capability, payload=None):
            seen.append((plugin_id, capability, dict(payload or {})))
            return {"tools": []}

        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._ctx_bridge(settings, capability_handler=handler)
            await bridge.load()
            return await bridge._plugins["anysearch"].instance.ctx.tool.list()

        self.assertEqual(run(scenario()), {"tools": []})
        self.assertEqual(seen, [("anysearch", "tool.list", {})])

    def test_plugin_context_definitions_match_the_bridge(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._ctx_bridge(settings)
            await bridge.load()
            return await bridge._plugins["anysearch"].instance.ctx.tool.get_definitions()

        definitions = run(scenario())
        self.assertEqual(
            sorted(item["name"] for item in definitions),
            ["anysearch.batch_search", "anysearch.search"],
        )

    def test_plugin_context_can_call_back_into_the_bridge(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._ctx_bridge(settings)
            await bridge.load()
            instance = bridge._plugins["anysearch"].instance
            return await instance.ctx.tool.call(tool="anysearch.search", arguments={"query": "who"})

        result = run(scenario())
        self.assertFalse(result["is_error"])
        self.assertEqual(result["text"], "answer")

    def test_unbridged_ctx_capability_raises_in_strict_mode(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._ctx_bridge(settings)
            await bridge.load()
            instance = bridge._plugins["anysearch"].instance
            instance.ctx._strict = True
            return await instance.ctx.call_capability("maisaka.reply", text="hi")

        with self.assertRaises(CapabilityNotBridgedError):
            run(scenario())

    def test_unload_resets_everything(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            await bridge.unload()
            return bridge.tools(), bridge.component_list()

        tools, plugins = run(scenario())
        self.assertEqual(tools, [])
        self.assertEqual(plugins, [])

    def test_status_shape_is_panel_ready(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            return bridge.status()

        status = run(scenario())
        for key in ("enabled", "plugin_count", "strict_sdk", "tool_count", "tools", "plugins"):
            self.assertIn(key, status)
        self.assertTrue(status["enabled"])
        self.assertEqual(status["plugin_count"], 1)
        self.assertEqual(status["tool_count"], 2)
        self.assertEqual(len(status["tools"]), 2)

    def test_reloading_twice_does_not_duplicate_tools(self) -> None:
        settings = BridgeSettings.from_config(config_with_bundled())

        async def scenario():
            bridge = self._bridge(settings, _ok_transport)
            await bridge.load()
            await bridge.load()
            return bridge.tools()

        self.assertEqual(len(run(scenario())), 2)



if __name__ == "__main__":
    unittest.main(verbosity=2)
