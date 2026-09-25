"""三方向硬门。

上游铁律：任何会产出新视觉设计的任务，100% 必须先出三个方向初稿给用户选，
指定风格/品牌也不豁免。风格词收窄的是解释空间，不豁免选择权。
"""

from __future__ import annotations

from dataclasses import dataclass, field

STYLE_SOURCES: tuple[str, ...] = (
    "网页 20 种",
    "PPT 20 种",
    "信息图 20 种",
)

class GateViolation(Exception):
    """未经用户选定就进入执行的越权。"""

@dataclass(frozen=True, slots=True)
class Direction:
    label: str
    hypothesis: str
    medium: str = "web"

@dataclass(slots=True)
class Gate:
    """三方向硬门状态机。

    状态流转：closed -> opened -> offered(>=3) -> chosen -> passed
    未到 chosen 就调用 enter_production() 会抛 GateViolation。
    """

    state: str = "closed"
    directions: list[Direction] = field(default_factory=list)
    chosen: int = -1
    style_hint: str = ""
    brand_named: bool = False
    rationale: str = ""

    def open(self, *, style_hint: str = "", brand_named: bool = False) -> None:
        self.state = "opened"
        self.style_hint = style_hint
        self.brand_named = brand_named

    def offer(self, directions: list[Direction]) -> None:
        """登记候选方向。少于 3 个不算数。"""
        if len(directions) < 3:
            raise ValueError(
                f"三方向硬门要求至少 3 个方向，收到 {len(directions)} 个。"
            )
        self.directions = list(directions)
        self.state = "offered"

    def choose(self, index: int, *, rationale: str = "") -> None:
        if self.state != "offered":
            raise GateViolation("还没有候选方向可供选择。")
        if not 0 <= index < len(self.directions):
            raise IndexError(f"方向索引越界：{index}")
        self.chosen = index
        self.rationale = rationale
        self.state = "chosen"

    def selected(self) -> Direction:
        if self.chosen < 0:
            raise GateViolation("用户尚未选定方向。")
        return self.directions[self.chosen]

    def enter_production(self) -> Direction:
        """进入正式执行的唯一入口；未选定即抛错。"""
        if self.state != "chosen":
            raise GateViolation(
                "三方向硬门未通过：必须先出三版真实初稿并等用户选定。"
                "指定风格/品牌不豁免。"
            )
        return self.selected()

    def bypass_reason(self) -> str:
        """没有任何豁免路径——永远返回空。"""
        return ""

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "style_hint": self.style_hint,
            "brand_named": self.brand_named,
            "directions": [
                {"label": d.label, "hypothesis": d.hypothesis, "medium": d.medium}
                for d in self.directions
            ],
            "chosen": self.chosen,
            "rationale": self.rationale,
        }

def style_hint_preserves_choice(hint: str) -> bool:
    """风格词只收窄解释空间，不豁免选择权——恒为 True，用于自检。"""
    return bool(hint.strip())
