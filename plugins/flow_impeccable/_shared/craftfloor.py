"""Craft floor：动手改 UI 前必须读一遍的底线清单。

对应上游 reference/craft-floor.md。每条是「不做到就不算交付」的底线，
按界面元素分类。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FloorItem:
    id: str
    element: str
    requirement: str

FLOOR: tuple[FloorItem, ...] = (
    FloorItem("text-scale", "排版", "字号阶梯成体系：display / title / body / caption 各司其职，不出现随手写的 15px"),
    FloorItem("measure", "排版", "正文行宽控制在 ~65ch 内，超宽必读崩"),
    FloorItem("line-height", "排版", "正文行高 >= 1.5；标题行高可压到 1.0-1.15"),
    FloorItem("spacing-scale", "间距", "间距来自单一标尺（4/8 的倍数），不允许 13px、17px 这类野值"),
    FloorItem("alignment", "布局", "同一区块内的元素共享至少一条对齐轴"),
    FloorItem("contrast", "颜色", "正文对比度满足 WCAG AA（4.5:1），大字号 3:1"),
    FloorItem("focus-ring", "交互", "键盘焦点环可见且不被 outline:none 抹掉"),
    FloorItem("hit-area", "交互", "可点击目标不小于 24x24（触屏 44x44）"),
    FloorItem("empty-state", "状态", "空状态是设计过的，不是一片空白或一句 No data"),
    FloorItem("loading-state", "状态", "加载态有结构占位，避免布局跳动"),
    FloorItem("error-state", "状态", "错误态说明发生了什么、下一步做什么"),
    FloorItem("reduced-motion", "无障碍", "prefers-reduced-motion 下动画关闭或降级"),
    FloorItem("keyboard-path", "无障碍", "所有交互都有一条纯键盘可达路径"),
    FloorItem("no-placeholder-copy", "文案", "不出现 Lorem ipsum、TODO、占位标题"),
    FloorItem("responsive-collapse", "响应式", "窄屏下信息层级重排，而不是横向溢出"),
)

def items_for(element: str) -> tuple[FloorItem, ...]:
    return tuple(item for item in FLOOR if item.element == element)

def blocking_after(changed: tuple[str, ...]) -> tuple[FloorItem, ...]:
    """改动涉及的元素类别，必须过对应底线。"""
    return tuple(item for item in FLOOR if item.element in changed)

def evaluate(
    *,
    changed_elements: tuple[str, ...],
    satisfied: tuple[str, ...],
) -> dict[str, object]:
    """判定一批评改是否踩了 craft floor。

    changed_elements: 本次改动涉及的元素类别（排版/间距/布局/颜色/交互/状态/无障碍/文案/响应式）
    satisfied: 已满足的 FloorItem.id
    """
    applicable = blocking_after(changed_elements)
    missing = [item for item in applicable if item.id not in satisfied]
    return {
        "applicable": [item.id for item in applicable],
        "missing": [item.id for item in missing],
        "ok": not missing,
        "directive": (
            "无阻断项。"
            if not missing
            else "补齐以下底线后再交付：" + ", ".join(item.id for item in missing)
        ),
    }
