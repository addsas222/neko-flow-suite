"""工作室角色轮换。

上游主张：一件像样的交付，顶级工作室不会只派一个人。你要依次成为每一个
角色；媒介变了，主导角色就要换——做幻灯片时别像网页，做动画时别像 Dashboard，
做 App 原型时别像说明书。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Role:
    id: str
    name: str
    owns: str
    failure_mode: str

ROLES: tuple[Role, ...] = (
    Role("art-director", "艺术总监", "定方向、判品味、砍掉不够好的",
         "做出「都还行」的平庸作品"),
    Role("brand-researcher", "品牌研究员", "找到真实资产（logo / 产品图 / UI），理解品牌气质",
         "凭想象画品牌，一眼假"),
    Role("visual-designer", "视觉设计师", "版式、色彩、字体、层级",
         "元素堆在一起，没有秩序"),
    Role("motion-designer", "动效设计师", "时间、缓动、节奏",
         "动画生硬，像 PPT 切换"),
    Role("frontend-engineer", "前端工程师", "把设计精确实现出来",
         "稿子好看，做出来走样"),
    Role("copywriter", "文案", "每一句话都为设计服务",
         "用 Lorem ipsum 或「标题文字」占位交付"),
)

#: 媒介 → 主导角色。
LEAD_BY_MEDIUM: dict[str, str] = {
    "web": "visual-designer",
    "slide": "art-director",
    "animation": "motion-designer",
    "app-prototype": "frontend-engineer",
    "infographic": "visual-designer",
}

def rotation_for(medium: str) -> tuple[Role, ...]:
    """给定媒介，给出角色轮换顺序：主导角色排最前。"""
    lead = LEAD_BY_MEDIUM.get(medium, "visual-designer")
    ordered = [role for role in ROLES if role.id == lead]
    ordered += [role for role in ROLES if role.id != lead]
    return tuple(ordered)

def check_coverage(medium: str, roles_done: tuple[str, ...]) -> dict[str, object]:
    """检查这次交付是否把该做的角色都做了一遍。"""
    expected = [role.id for role in rotation_for(medium)]
    missing = [role_id for role_id in expected if role_id not in roles_done]
    return {
        "medium": medium,
        "lead": LEAD_BY_MEDIUM.get(medium, "visual-designer"),
        "expected_order": expected,
        "missing": missing,
        "ok": not missing,
    }
