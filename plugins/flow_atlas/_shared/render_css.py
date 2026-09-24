"""产物样式：语义类 + CSS 变量，深浅两套主题。"""

from __future__ import annotations

CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --text: #e6edf3; --muted: #8b949e;
  --node-fill: #182030; --node-stroke: #2f4a6d; --node-fill-alt: #1a2230;
  --node-stroke-alt: #3d5470; --accent: #58a6ff; --accent-alt: #bc8cff;
  --muted-stroke: #3a4553; --edge: #6e7d92; --grid: #141a22;
}
html[data-theme="light"] {
  --bg: #ffffff; --panel: #f6f8fa; --text: #1f2328; --muted: #59636e;
  --node-fill: #eef4ff; --node-stroke: #8ab4f8; --node-fill-alt: #f3f0ff;
  --node-stroke-alt: #b39ddb; --accent: #0969da; --accent-alt: #8250df;
  --muted-stroke: #c7ced6; --edge: #8c959f; --grid: #eef1f4;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", "Noto Sans SC", sans-serif; }
.atlas-top { display: flex; gap: 16px; align-items: flex-end; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--muted-stroke); flex-wrap: wrap; }
.atlas-title { margin: 0; font-size: 18px; font-weight: 650; }
.atlas-sub { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.atlas-tools { display: flex; gap: 8px; align-items: center; }
.atlas-input, .atlas-btn { background: var(--panel); color: var(--text);
  border: 1px solid var(--muted-stroke); border-radius: 8px; padding: 6px 10px; font-size: 12px; }
.atlas-btn { cursor: pointer; }
.atlas-btn:hover { border-color: var(--accent); }
.atlas-views { display: flex; gap: 6px; padding: 8px 20px 0; flex-wrap: wrap; }
.atlas-view-btn { background: var(--panel); color: var(--muted); border: 1px solid transparent;
  border-radius: 999px; padding: 4px 12px; font-size: 12px; cursor: pointer; }
.atlas-view-btn[aria-pressed="true"] { color: var(--text); border-color: var(--accent); }
.atlas-stage { display: flex; height: calc(100vh - 128px); }
.atlas-canvas { position: relative; flex: 1; overflow: hidden; cursor: grab;
  background-image: radial-gradient(var(--grid) 1px, transparent 1px); background-size: 22px 22px; }
.atlas-canvas:active { cursor: grabbing; }
.atlas-svg { width: 100%; height: 100%; display: block; }
.atlas-bg { fill: transparent; }
.atlas-group > rect { fill: color-mix(in srgb, var(--panel) 60%, transparent);
  stroke: var(--muted-stroke); stroke-dasharray: 4 6; }
.atlas-group-label { fill: var(--muted); font-size: 12px; font-weight: 600; }
.atlas-lifelines > line { stroke: var(--muted-stroke); stroke-dasharray: 3 5; }
.atlas-node { cursor: pointer; }
.atlas-node-shape { stroke-width: 1.5; }
.atlas-node-accent { stroke-width: 3; stroke-linecap: round; }
.atlas-node-mark { fill: var(--muted); font-size: 13px; }
.atlas-node-label { fill: var(--text); font-size: 13px; font-weight: 600; }
.atlas-node-kind { fill: var(--muted); font-size: 10px; letter-spacing: .04em; }
.atlas-node:focus-visible > .atlas-node-shape { stroke: var(--accent); stroke-width: 2.5; }
.atlas-node[data-dim="1"] { opacity: .22; }
.atlas-edge-hit { stroke: transparent; stroke-width: 16; fill: none; }
.atlas-edge-line { stroke: var(--edge); stroke-width: 1.6; fill: none; }
.atlas-arrow-head { fill: var(--edge); }
.atlas-edge-label { fill: var(--muted); font-size: 11px; }
.atlas-edge[data-dim="1"] { opacity: .2; }
.atlas-detail { width: 320px; border-left: 1px solid var(--muted-stroke); background: var(--panel);
  padding: 16px; overflow: auto; }
.atlas-detail h2 { margin: 0 0 4px; font-size: 15px; }
.atlas-detail dl { display: grid; grid-template-columns: 88px 1fr; gap: 6px 10px; margin: 12px 0 0; }
.atlas-detail dt { color: var(--muted); font-size: 12px; }
.atlas-detail dd { margin: 0; font-size: 12px; }
.atlas-detail ul { margin: 8px 0 0; padding-left: 18px; font-size: 12px; }
@media (prefers-reduced-motion: no-preference) {
  .atlas-edge-line[data-trace="1"] { stroke-dasharray: 6 8; animation: atlas-flow 1s linear infinite; }
  @keyframes atlas-flow { to { stroke-dashoffset: -14; } }
}
"""


def render_css() -> str:
    return CSS.strip()
