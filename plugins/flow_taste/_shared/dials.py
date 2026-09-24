"""三个旋钮：DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY。

对应上游 SKILL.md 第 1 节。全文其余规则都由这三个全局变量把关；上游明确
要求不要起别名（LAYOUT_VARIANCE、ANIM_LEVEL 之类一律不许）。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

DIAL_NAMES: tuple[str, ...] = ("DESIGN_VARIANCE", "MOTION_INTENSITY", "VISUAL_DENSITY")

#: 上游第 1.A 节：design read → 旋钮区间。
DIAL_INFERENCE: dict[str, tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = {
    "minimalist": ((5, 6), (3, 4), (2, 3)),
    "calm": ((5, 6), (3, 4), (2, 3)),
    "editorial": ((5, 6), (3, 4), (2, 3)),
    "linear-style": ((5, 6), (3, 4), (2, 3)),
    "premium-consumer": ((7, 8), (5, 7), (3, 4)),
    "apple-y": ((7, 8), (5, 7), (3, 4)),
    "playful": ((9, 10), (8, 10), (3, 4)),
    "awwwards": ((9, 10), (8, 10), (3, 4)),
    "agency-y": ((9, 10), (8, 10), (3, 4)),
    "brutalist": ((8, 10), (5, 8), (3, 4)),
    "dark-tech": ((7, 9), (6, 8), (4, 5)),
    "glassy": ((6, 8), (5, 7), (3, 4)),
    "serious-b2b": ((5, 6), (4, 5), (5, 6)),
    "trust-first": ((3, 4), (2, 3), (4, 5)),
}

#: 上游第 1.B 节：用例预设。
USE_CASE_PRESETS: dict[str, tuple[int, int, int]] = {
    "landing-saas": (7, 6, 4),
    "landing-consumer": (7, 6, 3),
    "landing-agency": (9, 8, 3),
    "landing-event": (9, 7, 4),
    "portfolio-dev": (6, 5, 4),
    "portfolio-designer": (8, 7, 3),
    "portfolio-studio": (8, 7, 3),
    "editorial": (6, 4, 3),
    "redesign-preserve": (7, 6, 4),
    "redesign-overhaul": (9, 8, 4),
    "public-sector": (3, 2, 5),
}

BASELINE: tuple[int, int, int] = (8, 6, 4)


@dataclass(frozen=True, slots=True)
class Dials:
    """三个旋钮的取值。1..10 闭区间。"""

    variance: int = BASELINE[0]
    motion: int = BASELINE[1]
    density: int = BASELINE[2]

    def as_dict(self) -> dict[str, int]:
        return {
            "DESIGN_VARIANCE": self.variance,
            "MOTION_INTENSITY": self.motion,
            "VISUAL_DENSITY": self.density,
        }

    def to_css_variables(self) -> str:
        return "\n".join(f"--{k.lower().replace('_', '-')}: {v};" for k, v in self.as_dict().items())

    def __str__(self) -> str:
        return f"{self.variance} / {self.motion} / {self.density}"


def clamp(value: int) -> int:
    return max(1, min(10, int(value)))


def normalize(dials: Dials) -> Dials:
    return Dials(clamp(dials.variance), clamp(dials.motion), clamp(dials.density))


def defaults_for(vibe: str, use_case: str = "") -> Dials:
    """先按用例 preset 取值，再用 vibe 区间夹紧。

    上游第 1 节的基线是 8/6/4，design read 覆盖时采用此顺序：预设打底，
    区间夹紧，最后夹在 1..10。
    """
    base = USE_CASE_PRESETS.get(use_case, BASELINE)
    ranges = DIAL_INFERENCE.get(vibe)
    if ranges is None:
        return normalize(Dials(*base))

    picked = []
    for value, (low, high) in zip(base, ranges):
        picked.append(min(max(value, low), high))
    return normalize(Dials(*picked))


def midpoint(rng: tuple[int, int]) -> int:
    low, high = rng
    return (low + high) // 2


def motion_gates(dials: Dials) -> dict[str, bool]:
    """上游第 5 节把若干能力挂在 MOTION_INTENSITY 上。"""
    return {
        "magnetic_micro_physics": dials.motion > 5,
        "perpetual_micro_interactions": dials.motion > 5,
        "page_must_actually_move": dials.motion > 4,
    }


def motion_motivated(dials: Dials) -> bool:
    """MOTION_INTENSITY > 4 时页面必须真的动；反之不许硬塞。"""
    return dials.motion > 4


def adjust_for_redesign(dials: Dials, mode: str) -> Dials:
    """上游第 1.A/1.B 节：preserve 只 +1 motion，overhaul 的 variance/motion 各 +2。"""
    if mode == "preserve":
        return replace(dials, motion=clamp(dials.motion + 1))
    if mode == "overhaul":
        return replace(
            dials, variance=clamp(dials.variance + 2), motion=clamp(dials.motion + 2)
        )
    return dials
