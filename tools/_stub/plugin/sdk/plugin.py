"""N.E.K.O. 插件 SDK 的本地桩，仅供套件仓库的离线冒烟检查使用。

真实运行时由宿主提供 plugin.sdk.plugin；这里只提供同名的最小可导入面，
让 tools/smoke.py 在没有宿主的环境里也能验证插件入口类能被构造。
"""

from __future__ import annotations

from typing import Any


class SdkError(Exception):
    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


def Ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def Err(error: Any) -> dict[str, Any]:
    message = getattr(error, "message", None) or str(error)
    return {"ok": False, "error": message}


class NekoPluginBase:
    """最小基类：记录构造参数，提供 logger/router 占位。"""

    def __init__(self, ctx: Any = None) -> None:
        self.ctx = ctx

        class _Logger:
            def __getattr__(self, name: str):
                def _log(*args: Any, **kwargs: Any) -> None:
                    return None

                return _log

        self.logger = _Logger()

    def include_router(self, router: Any) -> None:
        return None

    def data_path(self, *parts: str) -> Any:
        from pathlib import Path

        return Path(*parts) if parts else Path(".")

    def cache_path(self, *parts: str) -> Any:
        from pathlib import Path

        return Path(*parts) if parts else Path(".")

    def register_dynamic_entry(self, **kwargs: Any) -> None:
        return None

    def unregister_dynamic_entry(self, entry_id: str) -> None:
        return None


def neko_plugin(cls: type) -> type:
    cls._is_neko_plugin = True
    return cls


def plugin_entry(**kwargs: Any):
    def wrap(func):
        func._plugin_entry = kwargs
        return func

    return wrap


def lifecycle(**kwargs: Any):
    def wrap(func):
        func._lifecycle = kwargs
        return func

    return wrap


def llm_tool(**kwargs: Any):
    def wrap(func):
        func._llm_tool = kwargs
        return func

    return wrap


def tr(text: str, **kwargs: Any) -> str:
    """i18n 助手的本地桩：原样返回，仅做格式化。"""
    try:
        return text.format(**kwargs) if kwargs else text
    except (KeyError, IndexError, ValueError):
        return text


class ui:
    """ui.context / ui.panel 等装饰器的本地桩。"""

    @staticmethod
    def context(**kwargs: Any):
        def wrap(func):
            func._ui_context = kwargs
            return func

        return wrap

    @staticmethod
    def panel(**kwargs: Any):
        def wrap(func):
            func._ui_panel = kwargs
            return func

        return wrap

    @staticmethod
    def guide(**kwargs: Any):
        def wrap(func):
            func._ui_guide = kwargs
            return func

        return wrap

    @staticmethod
    def action(**kwargs: Any):
        def wrap(func):
            func._ui_action = kwargs
            return func

        return wrap

    @staticmethod
    def card(**kwargs: Any):
        def wrap(func):
            func._ui_card = kwargs
            return func

        return wrap


class router:
    """PluginRouter 的本地桩。"""

    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix
        self.routes: list[Any] = []

    def route(self, *args: Any, **kwargs: Any):
        def wrap(func):
            self.routes.append(func)
            return func

        return wrap


PluginRouter = router
NekoRouter = router
Router = router
