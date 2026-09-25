"""Brief 推断：先读房间，再动手。

对应上游 taste-skill SKILL.md 第 0 节。核心主张：LLM 设计输出烂，大多数时候
不是因为手艺差，而是因为模型跳到默认审美而没有读需求。所以任何规则都不许
自动触发——先出 design read，再决定拉哪些规则。
"""

from __future__ import annotations

from dataclasses import dataclass

PAGE_KINDS: tuple[str, ...] = (
    "landing-saas",
    "landing-consumer",
    "landing-agency",
    "landing-event",
    "portfolio-dev",
    "portfolio-designer",
    "portfolio-studio",
    "redesign-preserve",
    "redesign-overhaul",
    "editorial",
)

AUDIENCES: tuple[str, ...] = (
    "b2b-buyer",
    "design-consumer",
    "recruiter",
    "procurement",
    "general-public",
)

VIBES: tuple[str, ...] = (
    "minimalist",
    "calm",
    "linear-style",
    "awwwards",
    "brutalist",
    "premium-consumer",
    "apple-y",
    "playful",
    "serious-b2b",
    "editorial",
    "agency-y",
    "glassy",
    "dark-tech",
    "trust-first",
)

QUIET_CONSTRAINTS: tuple[str, ...] = (
    "accessibility-first",
    "public-sector",
    "regulated",
    "trust-first-commerce",
    "kids",
)

#: 静默约束覆盖审美偏好。命中任意一条，vibe 不得翻盘。
OVERRIDES: dict[str, str] = {
    "accessibility-first": "trust-first",
    "public-sector": "trust-first",
    "regulated": "trust-first",
    "trust-first-commerce": "trust-first",
    "kids": "playful",
}

@dataclass(slots=True)
class DesignRead:
    """一句话 design read 的结构化形式。"""

    page_kind: str
    audience: str
    vibe: str
    family: str
    constraints: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()

    def render(self) -> str:
        """上游要求的单行 design read，生成任何代码之前先输出它。"""
        return (
            f"Reading this as: {self.page_kind} for {self.audience}, "
            f"with a {self.vibe} language, leaning toward {self.family}."
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "page_kind": self.page_kind,
            "audience": self.audience,
            "vibe": self.vibe,
            "family": self.family,
            "constraints": list(self.constraints),
            "signals": list(self.signals),
            "read": self.render(),
        }

class BriefAmbiguous(Exception):
    """需求含混到 design read 会分叉时抛出；上游要求只问一个问题。"""

    def __init__(self, question: str) -> None:
        super().__init__(question)
        self.question = question

@dataclass(slots=True)
class Brief:
    """一次任务的输入信号集合。"""

    page_kind: str = ""
    audience: str = ""
    vibe: str = ""
    constraints: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    brand_assets: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()

    def hints(self) -> tuple[str, ...]:
        return (
            self.page_kind,
            self.audience,
            self.vibe,
            *self.constraints,
            *self.references,
        )

def _normalise(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")

def infer(brief: Brief, *, family: str = "") -> DesignRead:
    """从需求推断 design read。

    只在该分叉时问一个问题，且只问一个：调用方捕获 BriefAmbiguous 后把
    它的 question 直接抛给用户。能从上下文推断时不要问。
    """
    page_kind = _normalise(brief.page_kind)
    vibe = _normalise(brief.vibe) or "linear-style"
    audience = _normalise(brief.audience) or "general-public"

    if page_kind and page_kind not in PAGE_KINDS:
        raise ValueError(
            f"unknown page kind {page_kind!r}; expected one of {', '.join(PAGE_KINDS)}"
        )
    if vibe not in VIBES:
        raise ValueError(f"unknown vibe {vibe!r}; expected one of {', '.join(VIBES)}")
    if audience not in AUDIENCES:
        raise ValueError(f"unknown audience {audience!r}; expected one of {', '.join(AUDIENCES)}")

    constraints = tuple(
        sorted({_normalise(c) for c in brief.constraints} & set(QUIET_CONSTRAINTS))
    )

    # 静默约束先翻盘，再看审美词。
    for constraint in constraints:
        forced = OVERRIDES.get(constraint)
        if forced and forced != vibe:
            vibe = forced

    if not page_kind:
        if not brief.signals and not brief.references:
            raise BriefAmbiguous(
                "Should this feel closer to Linear-clean or Awwwards-experimental?"
            )
        page_kind = "landing-saas"

    if not family:
        family = _family_for(page_kind, vibe)

    return DesignRead(
        page_kind=page_kind,
        audience=audience,
        vibe=vibe,
        family=family,
        constraints=constraints,
        signals=tuple(str(s) for s in brief.signals),
    )

def _family_for(page_kind: str, vibe: str) -> str:
    """把 design read 映射到上游第 2 节的落点。"""
    if vibe == "trust-first":
        return "govuk-frontend or uswds"
    if vibe == "brutalist":
        return "native CSS + monospace + raw borders"
    if vibe == "editorial":
        return "native CSS + scroll-driven animation + custom typography"
    if vibe == "premium-consumer" or vibe == "apple-y":
        return "Tailwind v4 utilities + restrained motion"
    if vibe == "dark-tech":
        return "native CSS + mono + single accent neon"
    if vibe == "awwwards" or vibe == "agency-y" or vibe == "playful":
        return "Tailwind v4 + Motion + custom typography"
    if page_kind.startswith("portfolio"):
        return "native CSS + custom typography"
    return "Tailwind v4 utilities + Geist + restrained motion"

#: 上游第 0.D 节的 LLM 默认审美清单，用于自检。
ANTI_DEFAULTS: tuple[str, ...] = (
    "AI-purple gradients",
    "centered hero over dark mesh",
    "three equal feature cards",
    "generic glassmorphism on everything",
    "infinite-loop micro-animations everywhere",
    "Inter + slate-900",
)

def anti_default_report(read: DesignRead) -> list[str]:
    """返回该 design read 下需要主动绕开的默认项。"""
    report = list(ANTI_DEFAULTS)
    if read.vibe == "minimalist" or read.vibe == "calm":
        report.append("Asymmetric layout as novelty: minimal reads as confidence, not emptiness")
    if read.vibe == "trust-first":
        report.append("Any decorative motion that does not communicate state")
    return report
