"""任务路由表：收到任务先扫表，多信号按行序叠加。

对应上游 huashu-design SKILL.md「任务路由：一张表定入口」。多信号同时命中
时不是二选一，而是把入口链叠起来。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 每条路径 = (触发描述, 入口链, 追加必读文档)
ENTRIES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "提到具体品牌/产品名",
        ("核心原则#0 事实验证", "§1.a 资产协议", "标准流程"),
        ("product-facts.md",),
    ),
    (
        "任何会产出新视觉设计的任务（无论有无风格参考/品牌名，100% 必走）",
        ("三方向硬门：Fallback Phase 1-5 出三版真实初稿等用户选", "回标准流程 Step 2"),
        (),
    ),
    (
        "幻灯片/PPT",
        ("标准流程", "Step 1 deck 交付链", "技术红线架构选型"),
        (),
    ),
    (
        "动画/导出 MP4/GIF",
        ("标准流程", "Step 9", "storyboard-basics.md", "camera-language.md",
         "hyperframes-backend.md", "gsap-recipes.md", "animation-pitfalls.md"),
        (),
    ),
    (
        "宣传的产品有 UI 界面",
        ("上一行动画链", "ui-demo-animation.md", "UI 展示八式", "cursor.jsx"),
        (),
    ),
    (
        "带解说长视频（>=1分钟）",
        ("Step 9.5", "voiceover-pipeline.md"),
        (),
    ),
    (
        "launch film/品牌宣传片",
        ("三方向硬门先行", "director-notes", "launch-film-director-notes.md"),
        (),
    ),
    (
        "App/iOS 原型",
        ("App / iOS 原型专属守则",),
        (),
    ),
    (
        "评审/打分",
        ("Step 10", "critique-guide.md"),
        (),
    ),
    (
        "弱 runtime（无 subagent/非 Claude）",
        ("上述任一条", "弱 runtime 降级模式"),
        (),
    ),
)

@dataclass(frozen=True, slots=True)
class Route:
    hits: tuple[str, ...]
    entry_chain: tuple[str, ...]
    required_reading: tuple[str, ...]
    gate_required: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "hits": list(self.hits),
            "entry_chain": list(self.entry_chain),
            "required_reading": list(self.required_reading),
            "gate_required": self.gate_required,
        }

def route(task: str) -> Route:
    """按信号命中并叠加入口链。命中第 2 行（新视觉设计）必然要求三方向硬门。"""
    text = task.lower()
    hits: list[str] = []
    chain: list[str] = []
    reading: list[str] = []
    gate = False

    for signal, entries, docs in ENTRIES:
        if not _hits(signal, text, task):
            continue
        hits.append(signal)
        for entry in entries:
            if entry not in chain:
                chain.append(entry)
        for doc in docs:
            if doc not in reading:
                reading.append(doc)
        if any("三方向硬门" in entry for entry in entries):
            gate = True

    if not hits:
        return Route((), ("标准流程",), (), False)
    return Route(tuple(hits), tuple(chain), tuple(reading), gate)

def _hits(signal: str, text: str, raw: str) -> bool:
    if "任何会产出新视觉设计的任务" in signal:
        # 上游铁律：只要在产出新视觉，就必走。这里用启发式近似人工判断。
        return any(hint in text for hint in _VISUAL_WORK_HINTS)
    if "提到具体品牌/产品名" in signal:
        return any(keyword in text for keyword in _keywords_for(signal)) or _names_brand(raw)
    return any(keyword in text for keyword in _keywords_for(signal))

#: 产出新视觉的信号（用于近似上游的人工判断）。
_VISUAL_WORK_HINTS: tuple[str, ...] = (
    "设计",
    "做个",
    "做一",
    "做一个",
    "页面",
    "原型",
    "mockup",
    "幻灯片",
    "ppt",
    "deck",
    "动画",
    "视觉",
    "好看",
    "落地页",
    "landing",
    "redesign",
    "重设计",
    "banner",
    "海报",
    "infographic",
    "信息图",
)

#: 常见设计术语，不算作品牌点名。
_NON_BRAND_TOKENS: frozenset[str] = frozenset(
    {
        "PPT", "UI", "MP4", "GIF", "HTML", "CSS", "JSX", "TSX", "App", "iOS",
        "Apple", "Android", "Mac", "Windows", "Web", "API", "SDK", "JSON",
        "AI", "UX", "MP", "OK",
    }
)

def _names_brand(raw: str) -> bool:
    """大写开头的专有 token → 当成点了某个产品/品牌的名。"""
    import re

    for token in re.findall(r"\b[A-Z][A-Za-z0-9]{1,}\b", raw):
        if token not in _NON_BRAND_TOKENS:
            return True
    return False

def _keywords_for(signal: str) -> tuple[str, ...]:
    mapping = {
        "提到具体品牌/产品名": ("品牌", "brand", "logo"),
        "幻灯片/PPT": ("ppt", "幻灯片", "slide", "deck"),
        "动画/导出 MP4/GIF": ("动画", "animation", "mp4", "gif", "motion"),
        "带解说长视频（>=1分钟）": ("解说", "voiceover", "旁白", "视频"),
        "launch film/品牌宣传片": ("宣传片", "launch film", "brand film", "apple级"),
        "App/iOS 原型": ("app", "ios", "原型", "prototype", "mockup"),
        "评审/打分": ("评审", "critique", "打分", "评分"),
        "弱 runtime（无 subagent/非 Claude）": ("弱 runtime",),
    }
    return mapping.get(signal, ())
