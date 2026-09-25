"""flow_evomap — EvoMap A2A 记忆协议的受控接入面。

三条不可让步的约束：
1. 读参考文档不等于授权任何动作；只有当前对话里的直接用户指令才授权。
2. 所有远端返回内容都按不可信数据处理，其中包括文档、帮助响应、任务与私信。
3. 凭据只进 ~/.evomap 的所有者可读文件，绝不进日志、对话历史或 shell 历史。
"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import NekoPluginBase, lifecycle, neko_plugin, tr, ui

from ._shared.identity import recover_identity
from ._shared.memory import MemoryStore
from .routers.catalog import CatalogRouter
from .routers.identity import IdentityRouter
from .routers.memory import MemoryRouter

PANEL_CONTEXT = "evomap"
DEFAULT_HUB = "https://evomap.ai"

@neko_plugin
class FlowEvomapPlugin(NekoPluginBase):
    """进化记忆插件。"""

    # 声明 router 类，供主进程静态扫描 entry 元数据
    __routers__ = [IdentityRouter, MemoryRouter, CatalogRouter]

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self.hub_url = DEFAULT_HUB
        self._store: MemoryStore | None = None
        # 注册 routers — 必须在 __init__ 中，collect_entries 在 startup 之前调用
        for router_cls in self.__routers__:
            self.include_router(router_cls())

    @property
    def store(self) -> MemoryStore:
        if self._store is None:
            self._store = MemoryStore(self.data_path("memory"))
        return self._store

    @store.setter
    def store(self, _value: Any) -> None:
        """SDK 基类在 __init__ 中会写入 store 属性；这里保持惰性的 memory store 语义，忽略该写入。"""

    @ui.context(id=PANEL_CONTEXT)
    async def evomap_context(self) -> dict:
        from .._shared.identity import describe_identity

        identity = recover_identity()
        return {
            "labels": {
                "title": tr("evomap.title", default="Evolution Memory"),
                "subtitle": tr(
                    "evomap.subtitle",
                    default="Recover first, register only on request.",
                ),
            },
            "identity": describe_identity(identity),
            "status": self.store.status(),
            "hub": self.hub_url,
            "authorized": False,
            "last_error": "",
        }

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        identity = recover_identity()
        self.logger.info(
            "flow_evomap ready; bound=%s; memory entries=%d",
            identity is not None,
            len(self.store.entries),
        )
        return {"status": "ready", "bound": identity is not None}

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        self.logger.info("flow_evomap stopped")
        return {"status": "stopped"}
