"""Brief → 设计系统映射（上游 SKILL.md 第 2 节）。

诚实规则：brief 读起来像某个官方系统，就装官方包用它；不要手搓它的 CSS，
也不要导入 token 之后覆盖掉 90%。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemChoice:
    signal: str
    package: str
    why: str

REAL_SYSTEMS: tuple[SystemChoice, ...] = (
    SystemChoice("Microsoft / enterprise SaaS / dashboards", "@fluentui/react-components", "官方 Fluent UI，token 与无障碍都做好了"),
    SystemChoice("Google-ish UI / Material product", "@material/web", "官方 Material 3，可 Theming"),
    SystemChoice("IBM-style B2B / analytics", "@carbon/react", "官方 Carbon，数据密度模式成熟"),
    SystemChoice("Shopify app surfaces", "@shopify/polaris", "Shopify admin UI 必需"),
    SystemChoice("Atlassian / Jira-style product", "@atlaskit/*", "官方 Atlassian DS"),
    SystemChoice("GitHub-style devtool", "@primer/css", "官方 Primer，Brand 变体做营销页"),
    SystemChoice("UK public-sector service", "govuk-frontend", "监管预期如此"),
    SystemChoice("US public-sector / trust-first", "uswds", "监管预期如此"),
    SystemChoice("Fast local-business / agency MVP", "bootstrap@5.3", "无聊、快、能用"),
    SystemChoice("Modern accessible React foundation", "@radix-ui/themes", "Primitives + 打磨过的主题"),
    SystemChoice("Modern SaaS owning the components", "shadcn/ui", "代码归你；绝不许以默认状态交付"),
    SystemChoice("Tailwind-based modern SaaS / AI marketing", "tailwindcss@4", "独立开发者与小团队默认"),
)

AESTHETICS: tuple[tuple[str, str], ...] = (
    ("Glassmorphism / frosted glass", "backdrop-filter + 分层描边 + 高光；给 prefers-reduced-transparency 做实色回退"),
    ("Bento (Apple-style tile grids)", "CSS Grid 混排单元格；没有库拥有它"),
    ("Brutalism", "原生 CSS + 等宽 + 粗边框；没有库"),
    ("Editorial / magazine", "衬线 + 非对称网格 + 大留白；没有库"),
    ("Dark tech / hacker", "等宽 + 单一霓虹强调 + 终端意象；没有库"),
    ("Aurora / mesh gradients", "SVG 或分层 radial-gradient；没有库"),
    ("Kinetic typography", "原生 CSS 动画 + scroll-driven；GSAP 只用于 scroll hijack"),
    ("Apple Liquid Glass", "Apple 只为自家平台文档化；没有官方 liquid-glass.css，网页实现须标注为近似"),
)

@dataclass(slots=True)
class SystemDecision:
    kind: str  # "official" | "aesthetic"
    name: str
    directive: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name, "directive": self.directive}

def choose(signal: str) -> SystemDecision:
    """按信号选系统；命中官方系统就返回它，否则落到美学实现。"""
    needle = signal.strip().lower()
    for choice in REAL_SYSTEMS:
        if needle in choice.signal.lower():
            return SystemDecision("official", choice.package, choice.why)
    for aesthetic, directive in AESTHETICS:
        if needle in aesthetic.lower():
            return SystemDecision("aesthetic", aesthetic, directive)
    return SystemDecision(
        "aesthetic",
        signal or "unspecified",
        "没有官方包：原生 CSS + Tailwind + 一个维护中的组件库，并在注释里写清借用与原创的边界。",
    )

def one_system_rule() -> str:
    return "一个项目一个系统：不要把 Fluent React 和 Carbon 混在同一棵树里。"
