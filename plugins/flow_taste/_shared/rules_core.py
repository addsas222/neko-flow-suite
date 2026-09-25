"""反默认规则表 · 类型与版式部分。

上游 taste-skill SKILL.md 第 3 / 4 节。severity 含义：
- block  硬门，命中即不许交付
- demote  降级为「仅在明确覆写条件下可用」
- warn   需要给出理由，不能默认通过
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEVERITY_BLOCK = "block"
SEVERITY_WARN = "warn"
SEVERITY_DEMOTE = "demote"

@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    severity: str
    pattern: re.Pattern[str]
    message: str
    fix: str
    override: str = ""

    def matches(self, text: str) -> list[re.Match[str]]:
        return list(self.pattern.finditer(text))

def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)

RULES_CORE: tuple[Rule, ...] = (
    Rule(
        id="serif-fraunces-default",
        severity=SEVERITY_BLOCK,
        pattern=_rx(r"Fraunces"),
        message="Fraunces 是 LLM 最爱的展示衬线，禁作默认字体。",
        fix="改用 sans display（Geist Display / Cabinet Grotesk Display / PP Neue Montreal）。",
        override="仅当 brief 明确点名衬线，或审美家族确属 editorial/luxury/publication。",
    ),
    Rule(
        id="serif-instrument-default",
        severity=SEVERITY_BLOCK,
        pattern=_rx(r"Instrument[_ ]?Serif"),
        message="Instrument Serif 是第二个 LLM 默认衬线，同样禁作默认。",
        fix="改用 sans display；要强调就用同一字族的斜体或粗体。",
        override="同上，且必须能说清这个衬线为什么配这个品牌。",
    ),
    Rule(
        id="inter-as-default",
        severity=SEVERITY_DEMOTE,
        pattern=_rx(r"\bInter\b"),
        message="Inter 作为默认无衬线被降级。",
        fix="优先 Geist、Outfit、Cabinet Grotesk、Satoshi，或品牌衬线。",
        override="用户明说中性/标准/Linear 风，或 brief 是公共部门/无障碍优先。",
    ),
    Rule(
        id="inter-slate-default-pair",
        severity=SEVERITY_DEMOTE,
        pattern=_rx(r"slate-900"),
        message="Inter + slate-900 是最典型的 LLM 默认搭配。",
        fix="换字族并重定 ink 色阶；先定 canvas/ink 对比再选 token 名。",
        override="同上。",
    ),
    Rule(
        id="h-screen-hero",
        severity=SEVERITY_BLOCK,
        pattern=_rx(r"\bh-screen\b"),
        message="h-screen 在移动端会因地址栏收放导致布局跳动。",
        fix="全高 Hero 一律 min-h-[100dvh]。",
    ),
    Rule(
        id="flex-percentage-math",
        severity=SEVERITY_WARN,
        pattern=_rx(r"calc\(\s*\d+%\s*[-+]"),
        message="复杂 flexbox 百分比运算是懒选择。",
        fix="改用 CSS Grid（grid grid-cols-1 md:grid-cols-3 gap-6）。",
    ),
    Rule(
        id="lucide-default-icon",
        severity=SEVERITY_DEMOTE,
        pattern=_rx(r"lucide-react"),
        message="lucide-react 是默认图标库，被降级。",
        fix="换 Phosphor / Tabler；缺字形就装第二个库，绝不手搓 SVG path。",
        override="用户明确要求，或项目已依赖它。",
    ),
    Rule(
        id="ai-purple-gradient",
        severity=SEVERITY_WARN,
        pattern=_rx(
            r"(from-(?:violet|purple|fuchsia|indigo)-\d{3})[^\"'`]*?(to-(?:violet|purple|fuchsia|indigo)-\d{3})"
        ),
        message="AI 紫渐变是最显眼的 LLM 标记之一。",
        fix="换成从 design read 推出来的品牌色对，先说清这个渐变传达什么。",
    ),
    Rule(
        id="three-equal-cards",
        severity=SEVERITY_WARN,
        pattern=_rx(r"grid-cols-3\b"),
        message="三等分卡片是 LLM 默认版式。",
        fix="改 2 列分组、bento 混排或 scroll-snap pills，让版式承担信息层级。",
    ),
    Rule(
        id="glassmorphism-everywhere",
        severity=SEVERITY_WARN,
        pattern=_rx(r"backdrop-blur"),
        message="无条件玻璃拟态是默认项。",
        fix=(
            "只在 premium/Apple 邻近/媒体叠加场景用；加 1px 内描边 "
            "shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] 与 "
            "prefers-reduced-transparency 回退。"
        ),
    ),
)
