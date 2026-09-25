"""MaiBot 插件 -> NEKO LLM 工具的桥。

职责边界（桥本身不认识任何具体 MaiBot 插件）：
    * 按 :mod:`.settings` 的清单动态导入 MaiBot 插件模块（只依赖
      :mod:`.sdk_compat` 重写的公开接口，绝不 import maibot_sdk）
    * 给插件注入 :class:`~.context.PluginContextProxy`、数据目录与后端网关
    * 把 ``@Tool`` 组件映射成 NEKO ``register_llm_tool`` 可用的
      name/description/parameters 三元组
    * 把 LLM 传来的 kwargs 派发回组件处理器，并把结果收敛成 NEKO 工具结果

工具描述/参数的外部补充来自 :class:`SchemaSource`（由 _runtime 注册），
因此"参数 schema"与"调用逻辑"解耦：MaiBot 源码不必改，也能拿到捕获版参数。
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from . import sdk_compat
from .context import PluginContextProxy, PluginPaths
from .errors import (
    AmbiguousPluginError,
    BridgeError,
    CapabilityNotBridgedError,
    ComponentNotFoundError,
    PluginLoadError,
)
from .sdk_compat import COMPONENT_INFO_ATTR, TOOL, MaiBotPlugin
from .settings import BridgeSettings, MaiBotPluginSpec

#: MaiBot 插件降级导入时用的兼容模块别名（保证桥与插件共用同一份 sdk_compat）
COMPAT_ALIAS = "sdk_compat"

#: NEKO LLM 工具名分隔符；name 允许 [A-Za-z0-9_.-]{1,64}（见 docs/tool-calling.txt）
TOOL_NAME_SEPARATOR = "."
#: 动态导入模块用的前缀，避免与插件自身模块名冲突
MODULE_PREFIX = "flow_maibot_dynamic"
#: 上游结果里允许回给 LLM 的字段（其余只是噪声，塞回去只会烧上下文）
LLM_PAYLOAD_FIELDS = ("text", "structured", "truncated", "is_error")
#: structured 超过该长度就丢掉，避免单次工具结果把上下文塞爆
STRUCTURED_MAX_CHARS = 4000
#: NEKO 工具名上限（见 docs/tool-calling.txt）
TOOL_NAME_MAX_LENGTH = 64
#: 注解文本 -> JSON Schema 类型
JSON_TYPE_BY_NAME = {
    "str": "string",
    "string": "string",
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "list": "array",
    "tuple": "array",
    "set": "array",
    "sequence": "array",
    "dict": "object",
    "mapping": "object",
}


# --------------------------------------------------------------------------- #
# 小工具函数
# --------------------------------------------------------------------------- #
async def _maybe_await(value: Any) -> Any:
    """同步函数或异步函数的结果都能接着用。"""
    if inspect.isawaitable(value):
        return await value
    return value


def _annotation_text(annotation: Any) -> str:
    """注解 -> 可读文本；``X | None`` 归约成 ``X``，免得可选参数丢类型。"""
    if annotation is inspect.Parameter.empty or annotation is None:
        return ""
    origin = getattr(annotation, "__origin__", None)
    if origin is Union or getattr(origin, "__name__", "") == "UnionType":
        members = [item for item in getattr(annotation, "__args__", ()) if item is not type(None)]
        if members:
            return _annotation_text(members[0])
        return ""
    if isinstance(annotation, str):
        return annotation.strip()
    return str(getattr(annotation, "__name__", None) or annotation).strip()


def _split_top_level(text: str) -> tuple[str, str]:
    """按顶层逗号切一刀，返回 (头, 尾)；用于拆 Annotated[...]。"""
    depth = 0
    quote = ""
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
        elif char in "[({":
            depth += 1
        elif char in "])}":
            depth -= 1
        elif char == "," and depth == 0:
            return text[:index], text[index + 1 :]
    return text, ""


def _first_quoted(text: str) -> str:
    for match in re.finditer(r"['\"]([^'\"]*)['\"]", text):
        return match.group(1)
    return ""


def _schema_property(annotation_text: str) -> dict[str, Any]:
    """把 Python 注解文本翻译成最小可用的 JSON Schema property。"""
    text = str(annotation_text or "").strip()
    if not text:
        return {}
    description = ""
    inner = text
    match = re.match(r"^Annotated\[(?P<rest>.*)\]$", text, re.S)
    if match:
        head, tail = _split_top_level(match.group("rest"))
        inner, description = head.strip(), _first_quoted(tail)
    if inner.endswith("| None") or inner.endswith("|None"):
        inner = inner.split("|")[0].strip()
    wrapper = re.match(r"^(?:Optional|Union)\[(?P<rest>.*)\]$", inner, re.S)
    if wrapper:
        inner = _split_top_level(wrapper.group("rest"))[0].strip()
    if "[" in inner:
        inner = inner.split("[", 1)[0].strip()
    if "." in inner:
        inner = inner.rsplit(".", 1)[-1]
    kind = JSON_TYPE_BY_NAME.get(inner.strip().lower(), "")
    prop: dict[str, Any] = {"type": kind} if kind else {}
    if description:
        prop["description"] = description
    return prop


def _slug(text: str) -> str:
    """把任意字符串收敛成工具名可用的片段。"""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text or "").strip()).strip("_")


def neko_tool_name(plugin_id: str, component: str) -> str:
    """MaiBot 组件名 -> NEKO LLM 工具名；不合法时返回空串。"""
    head = _slug(plugin_id)
    tail = _slug(component).rstrip("_")
    if not head or not tail:
        return ""
    name = f"{head}{TOOL_NAME_SEPARATOR}{tail}"
    if len(name) > TOOL_NAME_MAX_LENGTH:
        return ""
    return name if re.fullmatch(r"[A-Za-z0-9_.-]+", name) else ""


def signature_schema(method: Callable[..., Any]) -> dict[str, Any]:
    """从函数签名推断一份最小 JSON Schema（对字符串注解同样有效）。"""
    if not callable(method):
        return {}
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return {}
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        if parameter.name in ("self", "cls") or parameter.name.startswith("_"):
            continue
        properties[parameter.name] = _schema_property(_annotation_text(parameter.annotation))
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def accepts_var_keyword(method: Callable[..., Any]) -> bool:
    """处理器是否接受 **kwargs；不接受时把 LLM 多传的参数挡掉。"""
    if not callable(method):
        return False
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _llm_payload(payload: Any) -> Any:
    """只保留 LLM 需要的字段，其余一律丢掉（去噪 + 控 token）。"""
    if not isinstance(payload, dict):
        return payload
    slim: dict[str, Any] = {key: payload[key] for key in LLM_PAYLOAD_FIELDS if key in payload}
    structured = slim.get("structured")
    if structured is not None:
        try:
            size = len(json.dumps(structured, ensure_ascii=False, default=str))
        except (TypeError, ValueError):
            size = 0
        if size > STRUCTURED_MAX_CHARS:
            slim.pop("structured", None)
            slim["structured_omitted"] = size
    return slim


# --------------------------------------------------------------------------- #
# 桥接数据结构
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolBinding:
    """一个 MaiBot @Tool 组件在 NEKO 侧的形态。"""

    plugin_id: str
    component: str
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    schema_source: str = "decorator"

    def to_definition(self) -> dict[str, Any]:
        """给 register_llm_tool / 面板用的描述。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "plugin_id": self.plugin_id,
            "component": self.component,
            "schema_source": self.schema_source,
        }

    def to_capability_definition(self) -> dict[str, Any]:
        """只保留 MaiBot ctx.tool.get_definitions 需要的字段。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class LoadedPlugin:
    """已加载的 MaiBot 插件实例及其探明的组件。"""

    spec: MaiBotPluginSpec
    instance: Any
    module_name: str
    class_name: str
    components: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def describe(self) -> dict[str, Any]:
        types: dict[str, int] = {}
        for item in self.components:
            key = str(item.get("type", "?"))
            types[key] = types.get(key, 0) + 1
        return {
            "id": self.spec.id,
            "class": f"{self.module_name}:{self.class_name}",
            "path": str(self.spec.path),
            "components": len(self.components),
            "component_types": types,
            "notes": list(self.notes),
        }


class SchemaSource:
    """外部补充工具描述/参数的接口（mixin 或对象均可）。"""

    def lookup(self, plugin_id: str, component: str) -> Mapping[str, Any] | None:  # pragma: no cover
        raise NotImplementedError


def _import_module(path: Path, module_name: str) -> Any:
    if not path.is_file():
        raise PluginLoadError(f"MaiBot 插件文件不存在: {path}")
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"无法为 {path.name} 创建模块 spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    # 让插件里的 `from sdk_compat import ...` 落到桥这份兼容层，避免两份类对象
    sys.modules.setdefault(COMPAT_ALIAS, sdk_compat)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - 导入失败必须转成可控错误
        sys.modules.pop(module_name, None)
        raise PluginLoadError(
            f"导入 {path.name} 失败：{type(exc).__name__}", detail=type(exc).__name__
        ) from exc
    return module


def _find_plugin_class(module: Any, spec: MaiBotPluginSpec) -> type:
    """在当前模块内找 MaiBotPlugin 子类；导入来的类不算数。"""
    candidates: list[tuple[str, type]] = []
    for name, obj in vars(module).items():
        if not isinstance(obj, type) or obj is MaiBotPlugin:
            continue
        if not issubclass(obj, MaiBotPlugin):
            continue
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        candidates.append((name, obj))
    if spec.class_name:
        for name, obj in candidates:
            if name == spec.class_name:
                return obj
        raise PluginLoadError(f"模块里找不到插件类 {spec.class_name}")
    if not candidates:
        raise PluginLoadError("模块里没有 MaiBotPlugin 子类")
    if len(candidates) > 1:
        names = ", ".join(sorted(name for name, _ in candidates))
        raise AmbiguousPluginError(f"插件模块里有多个插件类({names})，请在配置里指定 class_name")
    _, plugin_class = candidates[0]
    return plugin_class


def _component_info(value: Any) -> Mapping[str, Any] | None:
    """取装饰器留下的组件信息（支持 staticmethod/classmethod 包装）。"""
    candidates = (value, getattr(value, "__func__", None))
    for candidate in candidates:
        if candidate is None:
            continue
        info = getattr(candidate, COMPONENT_INFO_ATTR, None)
        if info is None:
            continue
        data = getattr(info, "__dict__", None)
        if isinstance(data, Mapping):
            return {str(key): item for key, item in data.items() if not str(key).startswith("_")}
        if isinstance(info, Mapping):
            return info
    return None


def _find_component_method(instance: Any, component: str) -> Callable[..., Any] | None:
    """按组件名找绑定方法，@Tool 优先，其次按属性名排序保证确定性。

    先按装饰器标记筛选，再取实例属性：这样不会触发插件里的 property
    （兼容层的 ``config`` 就是会抛错的 property）。
    """
    hits: list[tuple[int, str, Callable[..., Any]]] = []
    for klass in type(instance).__mro__:
        for name, value in vars(klass).items():
            info = _component_info(value)
            if info is None or str(info.get("name", "")) != component:
                continue
            method = getattr(instance, name, None)
            if not callable(method):
                continue
            weight = 0 if str(info.get("type", "")) == TOOL else 1
            hits.append((weight, name, method))
    if not hits:
        return None
    hits.sort(key=lambda item: (item[0], item[1]))
    return hits[0][2]


def _plain(value: Any) -> Any:
    """把 Mapping/序列深拷贝成纯 dict/list，供 JSON Schema 直接使用。"""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _error_code(name: str) -> str:
    return f"{re.sub(r'[^a-z0-9_.]+', '_', str(name).lower()).strip('_')}_failed"


# --------------------------------------------------------------------------- #
# 桥
# --------------------------------------------------------------------------- #
class MaiBotBridge:
    """MaiBot 插件 <-> NEKO LLM 工具的双向桥。

    Parameters
    ----------
    settings:
        桥接层配置（要加载哪些 MaiBot 插件、严格模式等）。
    base_dir:
        相对路径的解析基准，默认插件根目录。
    logger:
        可选日志器，默认 ``flow_maibot.bridge``。
    backend:
        注入给实现了 ``attach_backend`` 的 MaiBot 插件的后端网关
        （AnySearchGateway）；不注入时插件按 MaiBot 自带方式建网关。
    capability_handler:
        ``async (plugin_id, capability, payload) -> Any``；桥把
        ``ctx.<capability>`` 调用转给它，未提供时一律视为"未桥接能力"。
    schema_sources:
        :class:`SchemaSource` 序列，用于补齐工具描述/参数 schema。
    data_root:
        桥的可写根目录，每个 MaiBot 插件拿 ``data/plugins/<id>`` 与
        ``temp/plugins/<id>``。
    """

    def __init__(
        self,
        settings: BridgeSettings,
        *,
        base_dir: Path | str | None = None,
        logger: logging.Logger | None = None,
        backend: Any = None,
        capability_handler: Callable[..., Any] | None = None,
        schema_sources: Sequence[Any] = (),
        data_root: Path | str | None = None,
    ) -> None:
        self._settings = settings
        self._base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parents[1]
        self._logger = logger or logging.getLogger("flow_maibot.bridge")
        self._backend = backend
        self._capability_handler = capability_handler
        self._schema_sources = list(schema_sources)
        self._data_root = Path(data_root) if data_root else None
        self._plugins: dict[str, LoadedPlugin] = {}
        self._problems: list[str] = []
        self._names: dict[str, tuple[str, str]] = {}
        self._backends: list[Any] = []

    # -- 生命周期 ---------------------------------------------------------- #
    async def load(self) -> dict[str, Any]:
        """加载所有启用中的 MaiBot 插件；单个插件失败只记问题，不影响其余。"""
        self._problems = []
        await self.unload()
        if not self._settings.enabled:
            self._problems.append("桥接层已停用")
            return self.status()
        for spec in self._settings.plugins:
            if not spec.enabled:
                self._logger.info("MaiBot 插件 %s 已停用，跳过加载", spec.id)
                continue
            try:
                loaded = await self._load_spec(spec)
            except BridgeError as exc:
                self._problems.append(f"{spec.id}: {exc.message}")
                self._logger.warning("加载 MaiBot 插件 %s 失败：%s", spec.id, exc.message)
                continue
            except Exception as exc:  # noqa: BLE001 - 未知异常也不能掀翻宿主
                self._problems.append(f"{spec.id}: {type(exc).__name__}")
                self._logger.warning(
                    "加载 MaiBot 插件 %s 时发生未知异常：%s", spec.id, type(exc).__name__
                )
                continue
            self._plugins[spec.id] = loaded
        self._names = {
            binding.name: (binding.plugin_id, binding.component)
            for binding in self.tool_bindings()
        }
        return self.status()

    async def unload(self) -> None:
        """卸载所有插件并关闭后端；不抛异常。"""
        for plugin_id in sorted(self._plugins):
            loaded = self._plugins[plugin_id]
            try:
                await _maybe_await(loaded.instance.on_unload())
            except Exception:  # noqa: BLE001 - 卸载失败只影响日志
                self._logger.warning("卸载 MaiBot 插件 %s 失败", plugin_id, exc_info=True)
        self._plugins.clear()
        self._names.clear()
        if self._backend is not None:
            self._backends.clear()
            try:
                await _maybe_await(self._backend.close())
            except Exception:  # noqa: BLE001 - 关闭后端失败不影响宿主退出
                self._logger.warning("关闭 AnySearch 网关失败", exc_info=True)

    async def _load_spec(self, spec: MaiBotPluginSpec) -> LoadedPlugin:
        path = spec.resolved_path(self._base_dir)
        module_name = f"{MODULE_PREFIX}_{_slug(spec.id).replace('.', '_').replace('-', '_')}"
        module = _import_module(path, module_name)
        plugin_class = _find_plugin_class(module, spec)
        instance = plugin_class()
        loaded = LoadedPlugin(
            spec=spec, instance=instance, module_name=module_name, class_name=plugin_class.__name__
        )
        self._inject(loaded)
        await _maybe_await(instance.on_load())
        self._collect_components(loaded)
        return loaded

    def _inject(self, loaded: LoadedPlugin) -> None:
        """按 MaiBot 生命周期顺位注入：后端 -> 配置 -> ctx。"""
        instance = loaded.instance
        if self._backend is not None and callable(getattr(instance, "attach_backend", None)):
            instance.attach_backend(self._backend)
            self._backends.append(self._backend)
        callbacks = getattr(instance, "set_plugin_config", None)
        if callable(callbacks):
            callbacks(dict(loaded.spec.config or {}))
        setter = getattr(instance, "_set_context", None)
        if callable(setter):
            setter(self._build_context(loaded.spec.id))

    def _build_context(self, plugin_id: str) -> PluginContextProxy:
        data_dir = runtime_dir = None
        if self._data_root is not None:
            data_dir = self._data_root / "data" / "plugins" / plugin_id
            runtime_dir = self._data_root / "temp" / "plugins" / plugin_id
            for directory in (data_dir, runtime_dir):
                directory.mkdir(parents=True, exist_ok=True)
        return PluginContextProxy(
            plugin_id=plugin_id,
            gateway=self._make_gateway(plugin_id),
            invoker=self._make_invoker(plugin_id),
            strict=self._settings.strict_sdk,
            paths=PluginPaths(data_dir=str(data_dir or ""), runtime_dir=str(runtime_dir or "")),
            logger_name=f"flow_maibot.bridge.{plugin_id}",
        )

    def _make_gateway(self, plugin_id: str) -> Callable[..., Any]:
        async def gateway(capability: str, payload: dict[str, Any]) -> Any:
            if self._capability_handler is None:
                raise CapabilityNotBridgedError(f"ctx.{capability} 未桥接到 NEKO 宿主")
            return await self._capability_handler(plugin_id, capability, dict(payload or {}))

        return gateway

    def _make_invoker(self, plugin_id: str) -> Callable[..., Any]:
        async def invoker(component: str, arguments: Mapping[str, Any] | None = None) -> Any:
            return await self.invoke(plugin_id, component, arguments)

        return invoker

    def _collect_components(self, loaded: LoadedPlugin) -> None:
        getter = getattr(loaded.instance, "get_components", None)
        if not callable(getter):
            loaded.notes.append("插件没有 get_components()，跳过组件探明")
            return
        try:
            raw = getter()
        except Exception as exc:  # noqa: BLE001 - 组件探明失败不能掀翻加载流程
            loaded.notes.append(f"get_components() 失败：{type(exc).__name__}")
            return
        for item in raw or []:
            if isinstance(item, Mapping):
                loaded.components.append(_plain(item))

    # -- 工具映射 ---------------------------------------------------------- #
    def tool_bindings(self) -> list[ToolBinding]:
        """把所有 @Tool 组件映射成 NEKO 工具；坏组件只记 note，不抛异常。"""
        bindings: list[ToolBinding] = []
        used: set[str] = set()
        for plugin_id in sorted(self._plugins):
            loaded = self._plugins[plugin_id]
            for component in loaded.components:
                if str(component.get("type", "")) != TOOL:
                    continue
                name = str(component.get("name", "")).strip()
                method = _find_component_method(loaded.instance, name)
                tool_name = neko_tool_name(plugin_id, name)
                if method is None:
                    loaded.notes.append(f"组件 {name} 找不到方法，未注册工具")
                    continue
                if not tool_name:
                    loaded.notes.append(f"组件 {name} 无法生成合法 NEKO 工具名，未注册")
                    continue
                if tool_name in used:
                    loaded.notes.append(f"工具名 {tool_name} 冲突，未注册")
                    continue
                description, parameters, source = self._tool_schema(loaded, component, method)
                used.add(tool_name)
                bindings.append(
                    ToolBinding(
                        plugin_id=plugin_id,
                        component=name,
                        name=tool_name,
                        description=description,
                        parameters=parameters,
                        schema_source=source,
                    )
                )
        return bindings

    def _lookup_schema(self, plugin_id: str, component: str) -> Mapping[str, Any] | None:
        for source in self._schema_sources:
            try:
                data = source.lookup(plugin_id, component)
            except Exception as exc:  # noqa: BLE001 - 单个 schema 源失败不该阻断桥
                self._logger.warning(
                    "schema 源 %s 查询 %s/%s 失败: %s",
                    type(source).__name__,
                    plugin_id,
                    component,
                    type(exc).__name__,
                )
                continue
            if isinstance(data, Mapping) and (data.get("description") or data.get("parameters")):
                return data
        return None

    def _tool_schema(
        self, loaded: LoadedPlugin, component: Mapping[str, Any], method: Callable[..., Any]
    ) -> tuple[str, dict[str, Any], str]:
        """描述/参数的取值优先级：schemas 捕获件 -> 装饰器元数据 -> 函数签名。"""
        name = str(component.get("name", ""))
        description = ""
        parameters: dict[str, Any] = {}
        override = self._lookup_schema(loaded.spec.id, name)
        if override is not None:
            description = str(override.get("description") or "").strip()
            raw = override.get("parameters")
            if isinstance(raw, Mapping):
                parameters = _plain(raw)
        if not description:
            description = str(component.get("detailed_description") or "").strip()
        if not description:
            description = str(component.get("description") or "").strip()
        if not parameters:
            raw = component.get("parameters_raw")
            if isinstance(raw, Mapping):
                parameters = _plain(raw)
        if not parameters:
            parameters = signature_schema(method) or {"type": "object", "properties": {}}
        if not description:
            description = name
        priority = "signature"
        if override is not None and (parameters or description):
            priority = "schemas"
        elif str(component.get("detailed_description") or component.get("description") or "") or isinstance(
            component.get("parameters_raw"), Mapping
        ):
            priority = "decorator"
        return description, parameters, priority

    # -- 调用 -------------------------------------------------------------- #
    def resolve(self, name: str) -> tuple[str, str]:
        """NEKO 工具名 -> (plugin_id, component)。"""
        target = self._names.get(str(name or "").strip())
        if target is None:
            raise ComponentNotFoundError(f"未注册的 NEKO 工具: {name}")
        return target

    async def invoke(
        self,
        plugin_id: str,
        component: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        """直接调用某个 MaiBot 组件，返回原始结果（不做 NEKO 侧裁剪）。"""
        loaded = self._plugins.get(str(plugin_id))
        if loaded is None:
            raise PluginLoadError(f"MaiBot 插件 {plugin_id} 未加载或已停用")
        method = _find_component_method(loaded.instance, str(component))
        if method is None:
            raise ComponentNotFoundError(f"插件 {plugin_id} 没有组件 {component}")
        payload = dict(arguments or {})
        schema = signature_schema(method)
        declared = {str(key) for key in (schema.get("properties") or {})}
        if declared and not accepts_var_keyword(method):
            payload = {key: value for key, value in payload.items() if key in declared}
        return await _maybe_await(method(**payload))

    async def invoke_tool(
        self, name: str, arguments: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """按 NEKO 工具结果协议把结果交回给 LLM（成功给 payload，失败给 is_error）。"""
        plugin_id = ""
        component = ""
        try:
            plugin_id, component = self.resolve(name)
            payload = await self.invoke(plugin_id, component, arguments)
        except BridgeError as exc:
            return {
                "output": {"reason": exc.message},
                "is_error": True,
                "error": exc.code or _error_code(name),
            }
        except Exception as exc:  # noqa: BLE001 - 异常统一转成工具结果，别把宿主打爆
            self._logger.warning("调用工具 %s 失败：%s", name, type(exc).__name__)
            return {
                "output": {"reason": f"{type(exc).__name__}"},
                "is_error": True,
                "error": _error_code(name),
            }
        slim = _llm_payload(payload)
        if isinstance(slim, dict) and slim.get("is_error"):
            return {"output": slim, "is_error": True, "error": _error_code(name)}
        return slim if isinstance(slim, dict) else {"output": slim}

    # -- 状态 -------------------------------------------------------------- #
    def tools(self) -> list[dict[str, Any]]:
        return [binding.to_definition() for binding in self.tool_bindings()]

    def tool_definitions_for(self, plugin_id: str) -> list[dict[str, Any]]:
        """MaiBot 侧 ctx.tool.get_definitions() 需要的数据。"""
        return [
            binding.to_capability_definition()
            for binding in self.tool_bindings()
            if binding.plugin_id == plugin_id
        ]

    def component_list(self) -> list[dict[str, Any]]:
        return [self._plugins[key].describe() for key in sorted(self._plugins)]

    def has_tool(self, name: str) -> bool:
        return str(name or "").strip() in self._names

    def backend_info(self) -> dict[str, Any]:
        describe = getattr(self._backend, "describe", None)
        if not callable(describe):
            return {"attached": self._backend is not None}
        try:
            info = describe()
        except Exception as exc:  # noqa: BLE001
            return {"attached": True, "error": type(exc).__name__}
        return dict(info) if isinstance(info, Mapping) else {"attached": True, "detail": str(info)[:200]}

    def status(self) -> dict[str, Any]:
        bindings = self.tool_bindings()
        return {
            "enabled": self._settings.enabled,
            "strict_sdk": self._settings.strict_sdk,
            "plugin_count": len(self._plugins),
            "plugins": self.component_list(),
            "problems": list(self._problems),
            "tool_count": len(bindings),
            "tools": [binding.to_definition() for binding in bindings],
            "backend": self.backend_info(),
        }

    @property
    def problems(self) -> list[str]:
        """加载过程中记录的问题（脱敏后的摘要）。"""
        return list(self._problems)
