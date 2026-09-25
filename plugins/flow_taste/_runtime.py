"""flow_taste 的 N.E.K.O. 运行时入口。

规则与逻辑都在 _shared/（纯标准库，可独立测试）；这里只做进程内编排，
把 _shared 的能力暴露成插件入口。
"""

from __future__ import annotations

from typing import Annotated

try:  # 在 N.E.K.O 宿主内
    from plugin.sdk.plugin import (
        Err,
        NekoPluginBase,
        Ok,
        neko_plugin,
        plugin_entry,
        ui,
    )
except ImportError:  # 允许在套件仓库内单独导入做静态检查
    NekoPluginBase = object  # type: ignore[assignment,misc]
    Ok = lambda data: {"ok": True, "data": data}  # type: ignore[assignment]
    Err = lambda error: {"ok": False, "error": str(error)}  # type: ignore[assignment]
    neko_plugin = lambda cls: cls  # type: ignore[assignment]

    class _UiFallback:
        """ui.context / ui.action 的本地兜底，签名与插件 SDK 一致。"""

        @staticmethod
        def context(**kwargs):
            def wrap(func):
                func._ui_context = kwargs
                return func

            return wrap

        @staticmethod
        def action(**kwargs):
            def wrap(func):
                func._ui_action = kwargs
                return func

            return wrap

    ui = _UiFallback

    def plugin_entry(**kwargs):  # type: ignore[no-untyped-def]
        def wrap(func):  # type: ignore[no-untyped-def]
            func._plugin_entry = kwargs  # type: ignore[attr-defined]
            return func

        return wrap


import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _shared.brief import Brief, DesignRead, infer  # noqa: E402
from _shared.dials import Dials, defaults_for  # noqa: E402
from _shared.gates import evaluate  # noqa: E402
from _shared.lint import lint_files, lint_html, rule_ids  # noqa: E402


@neko_plugin
class FlowTastePlugin(NekoPluginBase):
    """反 AI 味设计门禁。来源：Leonxlnx/taste-skill（MIT）。见本目录 SOURCE.md。"""

    @ui.action(id="read", label="Design read")
    @plugin_entry(
        id="read",
        name="Design read",
        description="从需求推断单行 design read 与三旋钮推荐值。",
    )
    async def read(
        self,
        page_kind: Annotated[str, "landing-saas / portfolio-dev / editorial 等"],
        vibe: Annotated[str, "minimalist / linear-style / awwwards 等"],
        audience: Annotated[str, "b2b-buyer / design-consumer / recruiter 等"] = "general-public",
        constraints: Annotated[str, "逗号分隔的静默约束，如 public-sector,accessibility-first"] = "",
    ) -> dict:
        try:
            brief = Brief(
                page_kind=page_kind,
                vibe=vibe,
                audience=audience,
                constraints=tuple(
                    item.strip() for item in constraints.split(",") if item.strip()
                ),
            )
            design_read: DesignRead = infer(brief)
            dials: Dials = defaults_for(design_read.vibe, design_read.page_kind)
            return Ok(
                {
                    "read": design_read.to_dict(),
                    "dials": dials.as_dict(),
                    "gates": [
                        "design-read-declared",
                        "dials-declared",
                        "anti-defaults-cleared",
                    ],
                }
            )
        except Exception as exc:  # noqa: BLE001 - 跨进程必须转 Err
            return Err(str(exc))

    @ui.action(id="lint", label="反默认扫描")
    @plugin_entry(
        id="lint",
        name="反默认扫描",
        description="扫描 HTML/CSS/TSX 源码，命中 block 级规则即阻断。",
    )
    async def lint(
        self,
        source: Annotated[str, "要扫描的源码片段"] = "",
        files: Annotated[str, "逗号分隔的文件路径；给了就忽略 source"] = "",
    ) -> dict:
        try:
            paths = [item.strip() for item in files.split(",") if item.strip()]
            report = lint_files(paths) if paths else lint_html(source)
            return Ok(report.to_dict())
        except Exception as exc:  # noqa: BLE001
            return Err(str(exc))

    @ui.action(id="rules", label="规则表")
    @plugin_entry(id="rules", name="规则表", description="列出全部反默认规则。")
    async def rules(self) -> dict:
        return Ok({"rules": list(rule_ids()), "count": len(rule_ids())})

    @ui.action(id="preflight", label="交付前硬门")
    @plugin_entry(
        id="preflight",
        name="交付前硬门",
        description="按 design read + 旋钮跑一遍 pre-flight 硬门。",
        kind="service",
    )
    async def preflight(
        self,
        design_read: Annotated[str, "单行 design read"] = "",
        variance: Annotated[int, "DESIGN_VARIANCE 1..10"] = 8,
        motion: Annotated[int, "MOTION_INTENSITY 1..10"] = 6,
        density: Annotated[int, "VISUAL_DENSITY 1..10"] = 4,
        page_moves: Annotated[bool, "页面是否真的在动"] = True,
        motion_reasons: Annotated[bool, "每个动画是否都有一句话理由"] = True,
        copy_audited: Annotated[bool, "是否逐句重读过文案"] = True,
    ) -> dict:
        report = evaluate(
            design_read=design_read,
            dials=Dials(variance, motion, density),
            declared={
                "design-read-declared": bool(design_read.strip()),
                "dials-declared": True,
                "anti-defaults-cleared": True,
                "one-system": True,
                "deps-verified": True,
                "viewport-stable": True,
                "grid-over-flex-math": True,
                "motion-motivated": motion_reasons,
                "motion-claims-match": page_moves,
                "copy-self-audit": copy_audited,
                "no-fake-precision": True,
                "theme-locked": True,
                "icon-family-single": True,
                "no-handrolled-svg": True,
            },
        )
        return Ok(report.to_dict())

    # -- Hosted UI ------------------------------------------------------

    @ui.context(id="dashboard")
    async def dashboard_context(self) -> dict:
        """plugin.toml 里的 context = "dashboard" 由这里提供 props.state。"""
        return {
            "labels": {
                "title": "Flow Taste",
                "subtitle": "反 AI 味设计门禁",
                "read_hint": "生成任何代码之前先拿 design read：单行 design read + 三旋钮推荐值。",
            },
            "plugin_id": self.plugin_id,
        }
