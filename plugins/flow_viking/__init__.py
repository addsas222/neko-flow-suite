"""flow_viking — 一套 viking:// 虚拟文件系统式的上下文数据库。

移植自 volcengine/OpenViking 的思想：把上下文组织成一棵可导航的虚拟文件系
统，每个目录都带生成的摘要，Agent 像操作文件一样 ls / tree / read / write /
grep / find，并能打开任意目录检视与编辑 Agent 到底知道什么。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plugin.sdk.plugin import NekoPluginBase, lifecycle, neko_plugin, tr, ui

from ._shared.fsstore import VirtualFS
from ._shared.store import load, save
from .routers.fs import FsRouter
from .routers.memory import MemoryRouter

PANEL_CONTEXT = "viking"


@neko_plugin
class FlowVikingPlugin(NekoPluginBase):
    """上下文数据库插件。"""

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self._fs: VirtualFS | None = None
        self.include_router(FsRouter())
        self.include_router(MemoryRouter())

    # -- state ----------------------------------------------------------

    @property
    def fs(self) -> VirtualFS:
        if self._fs is None:
            self._fs = load(self.data_path("viking"))
        return self._fs

    def persist(self) -> bool:
        return save(self.fs, self.data_path("viking"))

    @property
    def root_dir(self) -> Path:
        return self.data_path("viking")

    # -- UI -------------------------------------------------------------

    @ui.context(id=PANEL_CONTEXT)
    async def viking_context(self) -> dict:
        fs = self.fs
        files = fs.all_files()
        return {
            "labels": {
                "title": tr("viking.title", default="Context Database"),
                "subtitle": tr("viking.subtitle", default="One filesystem for everything the agent knows."),
            },
            "stats": {
                "files": len(files),
                "chars": sum(len(file.content or "") for file in files),
            },
            "tree": fs.tree("viking://", max_depth=2),
            "last_error": "",
        }

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self.root_dir.mkdir(parents=True, exist_ok=True)
        files = self.fs.all_files()
        self.logger.info("flow_viking ready; %d file(s) restored", len(files))
        return {"status": "ready", "files": len(files)}

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        saved = self.persist()
        self.logger.info("flow_viking stopped; persisted=%s", saved)
        return {"status": "stopped", "persisted": saved}
