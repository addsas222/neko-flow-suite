"""布局调度：按图种分发到对应的布局器。

布局的目标是可预测而不是最优：同一份规格永远得到同一份几何解。作者通过
via / label 修几何，通过诊断报告发现冲突，而不是手写坐标。
"""

from __future__ import annotations

from typing import Any

from .geometry import Layout
from .spec import Diagram

NODE_W = 168.0
NODE_H = 56.0
GAP_X = 96.0
GAP_Y = 40.0
PAD_X = 48.0
PAD_Y = 48.0
GROUP_PAD = 20.0
GROUP_LABEL_H = 22.0
SEQUENCE_ROW_GAP = 46.0
TITLE_H = 72.0
CYCLE_RADIUS_MIN = 180.0
CYCLE_BULGE = 26.0

def layout(diagram: Diagram) -> Layout:
    """为规格计算几何解。"""
    if diagram.type == "sequence":
        from .sequence_layout import layout_sequence

        return layout_sequence(diagram)
    if diagram.type == "lifecycle":
        from .cycle_layout import layout_cycle

        return layout_cycle(diagram)
    from .layered_layout import layout_layered

    return layout_layered(diagram)

def values_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol

def grid(value: float) -> float:
    """把浮点收进稳定的两位小数，避免产物字节抖动。"""
    return round(value + 1e-9, 2)

def touches_border(point: Any, box: Any) -> Any:
    """点正好落在上/下边上时返回规范化后的点，否则返回 None。"""
    if values_close(point.y, box.y, 0.5) and box.x - 0.5 <= point.x <= box.x + box.w + 0.5:
        return _point(point.x, box.y)
    if values_close(point.y, box.y + box.h, 0.5) and box.x - 0.5 <= point.x <= box.x + box.w + 0.5:
        return _point(point.x, box.y + box.h)
    return None

def _point(x: float, y: float) -> Any:
    from .geometry import Point

    return Point(x, y)
