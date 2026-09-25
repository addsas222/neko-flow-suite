"""渲染编排：产出自包含 HTML。

产物包含主题切换、平移缩放、搜索、聚焦、语义视图与真实导出。这些是读者
能力，不是作者的额外工作；meta.animation = "trace" 才开启动效。
"""

from __future__ import annotations

import html
from typing import Any

from .layout import layout
from .render_css import render_css
from .render_runtime import render_runtime
from .render_svg import export_payload, render_body, render_views
from .spec import Diagram

TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ — N.E.K.O. flow_atlas</title>
<style>
__CSS__
</style>
</head>
<body>
<header class="atlas-top">
  <div class="atlas-titles">
    <h1 class="atlas-title">__TITLE__</h1>
    <p class="atlas-sub">__SUBTITLE__</p>
  </div>
  <div class="atlas-tools">
    <input id="atlas-search" class="atlas-input" type="search" placeholder="Search subjects"
      aria-label="Search subjects">
    <button id="atlas-fit" class="atlas-btn" type="button">Fit</button>
    <button id="atlas-theme" class="atlas-btn" type="button">Theme</button>
    <button id="atlas-export-svg" class="atlas-btn" type="button">Export SVG</button>
    <button id="atlas-export-png" class="atlas-btn" type="button">Export PNG</button>
  </div>
</header>
<nav class="atlas-views" id="atlas-views" hidden>__VIEWS__</nav>
<main class="atlas-stage">
  <div class="atlas-canvas" id="atlas-canvas" tabindex="0">
__BODY__
  </div>
  <aside class="atlas-detail" id="atlas-detail" hidden></aside>
</main>
<script type="application/json" id="atlas-data">__DATA__</script>
<script>
__RUNTIME__
</script>
</body>
</html>
"""

def render_html(diagram: Diagram, placed: Any | None = None) -> str:
    """把规格渲染成自包含 HTML。"""
    placed = placed if placed is not None else layout(diagram)
    title = html.escape(diagram.title or diagram.type, quote=True)
    subtitle = html.escape(diagram.description or diagram.type, quote=True)
    return (
        TEMPLATE.replace("__TITLE__", title)
        .replace("__SUBTITLE__", subtitle)
        .replace("__CSS__", render_css())
        .replace("__VIEWS__", render_views(diagram))
        .replace("__BODY__", render_body(diagram, placed))
        .replace("__DATA__", export_payload(diagram, placed))
        .replace("__RUNTIME__", render_runtime())
    )
