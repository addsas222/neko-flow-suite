"""flow_eigenflux 的 N.E.K.O. 运行时入口：一个只会声明「不可用」的占位插件。

上游 phronesis-io/eigenflux 的许可证是 NOASSERTION——GitHub 的 /licenses API
无法把它识别成任何标准开源许可证。在没有可识别的许可证文本之前，不能假定允许
移植或再分发，所以本套件不移植、不分发它的任何代码，详见同目录 SOURCE.md。

这个插件存在的唯一理由：让目录成为宿主能加载的合法包（plugin.toml + NekoPluginBase
子类），而不是一个缺清单的残目录。它不 import 任何上游代码，也不含 _shared/，
因此不构成衍生作品。它暴露的唯一入口永远返回 Err，把理由讲清楚。
"""

from __future__ import annotations

from typing import Any

try:  # 在 N.E.K.O 宿主内
    from plugin.sdk.plugin import Err, NekoPluginBase, SdkError, neko_plugin, plugin_entry
except ImportError:  # 允许在套件仓库内单独导入做静态检查与冒烟

    class SdkError(Exception):
        """本地兜底，与插件 SDK 的同名错误保持一样的 message 属性。"""

        def __init__(self, message: str = "") -> None:
            super().__init__(message)
            self.message = message

    def Err(error: Any) -> dict[str, Any]:  # type: ignore[misc]
        message = getattr(error, "message", None) or str(error)
        return {"ok": False, "error": message}

    def neko_plugin(cls: type) -> type:  # type: ignore[misc]
        return cls

    def plugin_entry(**kwargs: Any):  # type: ignore[misc]
        def wrap(func: Any) -> Any:
            func._plugin_entry = kwargs
            return func

        return wrap

    class _LocalBase:
        """本地兜底基类：与插件 SDK 的 NekoPluginBase(ctx) 保持同形。"""

        def __init__(self, ctx: Any = None) -> None:
            self.ctx = ctx

    NekoPluginBase = _LocalBase  # type: ignore[assignment,misc]


UNAVAILABLE_REASON = (
    "上游许可证未识别：phronesis-io/eigenflux 的 license.key=other、"
    "spdx=NOASSERTION，GitHub 无法识别为任何标准开源许可证，"
    "因此在上游给出可识别的许可证之前不移植、不分发其任何代码。"
    "flow_eigenflux 目前只是来源登记，没有可供调用的功能。"
)


@neko_plugin
class FlowEigenfluxPlugin(NekoPluginBase):
    """占位插件：唯一入口只解释自己为什么不可用。"""

    @plugin_entry(
        id="status",
        name="状态",
        description="说明本插件为何不可用（上游许可证未识别，未移植代码）。",
    )
    async def status(self) -> dict:
        return Err(SdkError(UNAVAILABLE_REASON))
