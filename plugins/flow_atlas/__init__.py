"""flow_atlas — 把工作流、架构、时序、数据流与生命周期画成可导出的自包含 HTML。

移植自 tt-a1i/archify 的创作契约：先写规格，再校验，最后才交付。渲染是
确定性的——同一份规格永远产出同一份产物字节。
"""

from __future__ import annotations

from typing import Any

from plugin.sdk.plugin import NekoPluginBase, lifecycle, neko_plugin, ui

from ._shared.artifacts import list_specs
from ._shared.labels import context
from .routers.gallery import GalleryRouter
from .routers.mermaid import MermaidRouter
from .routers.specs import SpecRouter

PANEL_CONTEXT = "atlas"

@neko_plugin
class FlowAtlasPlugin(NekoPluginBase):
    """工作流图谱插件。"""

    # 声明 router 类，供主进程静态扫描 entry 元数据
    __routers__ = [SpecRouter, MermaidRouter, GalleryRouter]

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        # 注册 routers — 必须在 __init__ 中，collect_entries 在 startup 之前调用
        for router_cls in self.__routers__:
            self.include_router(router_cls())

    @ui.context(id=PANEL_CONTEXT)
    async def atlas_context(self) -> dict:
        """Hosted UI 面板状态。"""
        directory = self.data_path("diagrams")
        directory.mkdir(parents=True, exist_ok=True)
        return context(saved=list_specs(directory))

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        directory = self.data_path("diagrams")
        directory.mkdir(parents=True, exist_ok=True)
        self.logger.info("flow_atlas ready; diagram dir=%s", directory)
        return {"status": "ready"}

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        self.logger.info("flow_atlas stopped")
        return {"status": "stopped"}
