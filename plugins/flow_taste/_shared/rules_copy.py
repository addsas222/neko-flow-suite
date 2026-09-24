"""反默认规则表 · 文案、交付与容器部分（上游 SKILL.md 第 4.9-4.11、3.A）。"""

from __future__ import annotations

from .rules_core import SEVERITY_BLOCK, SEVERITY_WARN, Rule, _rx

RULES_COPY: tuple[Rule, ...] = (
    Rule(
        id="spec-sheet-hairlines",
        severity=SEVERITY_WARN,
        pattern=_rx(r"(divide-y|border-b)[^\"'`]{0,120}(spec|规格)"),
        message="长规格表每行一条 hairline 是 AI 默认做法。",
        fix="3-4 个 hero spec 做成大数字卡片，其余收进 View full specifications。",
    ),
    Rule(
        id="fake-precision",
        severity=SEVERITY_WARN,
        pattern=_rx(r"\b\d+(?:\.\d+)?\s*(?:%|×|x|mm|lb|k)\b"),
        message="疑似伪造的精确实数。",
        fix="数字必须来自真实数据或被显式标注为 mock；否则删掉。",
    ),
    Rule(
        id="lorem-or-placeholder-copy",
        severity=SEVERITY_BLOCK,
        pattern=_rx(r"(lorem ipsum|标题文字|placeholder text|TODO copy|TBD)"),
        message="占位文案不允许交付。",
        fix="每句话都为设计服务；不确定就换成朴素的功能句。",
    ),
    Rule(
        id="google-fonts-link",
        severity=SEVERITY_WARN,
        pattern=_rx(r"fonts\.googleapis\.com"),
        message="生产环境不要用 <link> 引 Google Fonts。",
        fix="用 next/font 或 @font-face 自托管并设 font-display: swap。",
    ),
    Rule(
        id="unbounded-container",
        severity=SEVERITY_WARN,
        pattern=_rx(r"\bmax-w-(?:7xl|full|none)\b"),
        message="页面缺约束宽度。",
        fix="用 max-w-[1400px] mx-auto 收敛阅读宽度。",
    ),
    Rule(
        id="usestate-continuous-value",
        severity=SEVERITY_WARN,
        pattern=_rx(r"useState[^\n]{0,60}(mouse|scroll|pointer)"),
        message="useState 跟踪连续值会在每次变化时重渲染整棵树，移动端直接垮。",
        fix="改用 Motion 的 useMotionValue / useTransform / useScroll，放在渲染周期外。",
    ),
    Rule(
        id="forced-serif-inside-sans-headline",
        severity=SEVERITY_WARN,
        pattern=_rx(r"font-serif[^\"'`]{0,40}(?:and|&amp;|,)\s*[^\"'`]{0,40}font-sans"),
        message="在同一 sans 标题里塞一个衬线词做强调是业余手法。",
        fix="用同一字族的斜体或粗体强调。",
    ),
    Rule(
        id="section-theme-flip",
        severity=SEVERITY_WARN,
        pattern=_rx(r"bg-(?:amber|orange|rose|emerald)-50"),
        message="深色页面中间插入浅色区块会让人以为换了网站。",
        fix="页面只有一个主题；同族深浅可以（bg-zinc-950 配 bg-zinc-900），跨族不行。",
    ),
)
