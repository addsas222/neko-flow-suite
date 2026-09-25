"""Impeccable 命令表与路由。

对应上游 impeccable SKILL.md 的 Commands 表。上游把「设计 / 重设计 / 审计 /
动效 / 排版 / 适配 / 性能」等请求路由到一份 reference 文档；这里复刻路由本身
（不含其二进制 launcher）。
"""

from __future__ import annotations

from dataclasses import dataclass

GROUPS: tuple[str, ...] = ("setup", "new", "enhance", "fix", "iterate")

@dataclass(frozen=True, slots=True)
class Command:
    id: str
    group: str
    label: str
    takes_target: bool
    reference: str
    summary: str

COMMANDS: tuple[Command, ...] = (
    Command("shape", "new", "Shape", True, "reference/shape.md", "任务发现：把模糊需求收敛成可执行的设计范围"),
    Command("init", "setup", "Init", False, "reference/init.md", "写 PRODUCT.md，记录平台与设计世界"),
    Command("document", "setup", "Document", False, "reference/document.md", "把既有界面沉淀成 DESIGN.md"),
    Command("extract", "setup", "Extract", False, "reference/extract.md", "从现有实现里抽取 token"),
    Command("audit", "fix", "Audit", True, "reference/audit.md", "系统审查，输出缺陷清单"),
    Command("critique", "fix", "Critique", True, "reference/critique.md", "主观评价与判断依据"),
    Command("animate", "enhance", "Animate", True, "reference/animate.md", "加入有目的的动画与运动"),
    Command("bolder", "enhance", "Bolder", True, "reference/bolder.md", "把保守的设计推得更敢"),
    Command("colorize", "enhance", "Colorize", True, "reference/colorize.md", "给单色界面加策略性用色"),
    Command("delight", "enhance", "Delight", True, "reference/delight.md", "加入个性与记忆点"),
    Command("layout", "enhance", "Layout", True, "reference/layout.md", "修间距、节奏与视觉层级"),
    Command("overdrive", "enhance", "Overdrive", True, "reference/overdrive.md", "突破常规上限"),
    Command("quieter", "enhance", "Quieter", True, "reference/quieter.md", "把吵闹的设计收敛下来"),
    Command("typeset", "enhance", "Typeset", True, "reference/typeset.md", "改进字体层级与配字"),
    Command("clarify", "fix", "Clarify", True, "reference/clarify.md", "改进 UX 文案、标签与错误信息"),
    Command("adapt", "fix", "Adapt", True, "reference/adapt.md", "适配不同设备与屏幅"),
    Command("optimize", "fix", "Optimize", True, "reference/optimize.md", "诊断并修 UI 性能"),
    Command("live", "iterate", "Live", False, "reference/live.md", "浏览器里挑元素做视觉变体迭代"),
    Command("generate", "iterate", "Generate", False, "reference/generate.md", "为命名元素生成若干变体供挑选"),
)

_ALIASES: dict[str, str] = {
    "teach": "init",
    "craft": "shape",
}

#: 上游 routing.md 的自然语言关键词 → 命令。
_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("audit", "audit"),
    ("critique", "critique"),
    ("review", "critique"),
    ("animate", "animate"),
    ("motion", "animate"),
    ("bolder", "bolder"),
    ("bold", "bolder"),
    ("colorize", "colorize"),
    ("colour", "colorize"),
    ("color", "colorize"),
    ("delight", "delight"),
    ("layout", "layout"),
    ("spacing", "layout"),
    ("overdrive", "overdrive"),
    ("quieter", "quieter"),
    ("calm", "quieter"),
    ("typeset", "typeset"),
    ("typography", "typeset"),
    ("font", "typeset"),
    ("clarify", "clarify"),
    ("copy", "clarify"),
    ("adapt", "adapt"),
    ("responsive", "adapt"),
    ("optimize", "optimize"),
    ("performance", "optimize"),
    ("document", "document"),
    ("extract", "extract"),
    ("live", "live"),
    ("generate", "generate"),
    ("shape", "shape"),
    ("redesign", "shape"),
    ("design system", "document"),
)

def by_id(command_id: str) -> Command:
    wanted = _ALIASES.get(command_id, command_id)
    for command in COMMANDS:
        if command.id == wanted:
            return command
    raise KeyError(f"unknown impeccable command {command_id!r}")

def ids() -> tuple[str, ...]:
    return tuple(command.id for command in COMMANDS)

def commands_in(group: str) -> tuple[Command, ...]:
    return tuple(command for command in COMMANDS if command.group == group)

@dataclass(frozen=True, slots=True)
class Route:
    command: Command
    reference: str
    reason: str
    ambiguous_with: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command.id,
            "group": self.command.group,
            "reference": self.reference,
            "reason": self.reason,
            "ambiguous_with": list(self.ambiguous_with),
        }

def route(request: str) -> Route:
    """把一句自然语言请求路由到一条命令。

    命中多个关键词且分属不同命令时，不猜：把候选都带回去，让调用方只问一次。
    """
    text = request.strip().lower()
    explicit = text.split()[0] if text else ""

    if explicit in _ALIASES or any(command.id == explicit for command in COMMANDS):
        command = by_id(explicit)
        return Route(command, command.reference, f"显式命令 {command.id}")

    hits: list[str] = []
    for needle, command_id in _KEYWORDS:
        if needle in text and command_id not in hits:
            hits.append(command_id)

    if not hits:
        return Route(
            by_id("shape"),
            "reference/shape.md",
            "未命中命令关键词：当作一般设计工作，走 shape 做任务发现。",
        )

    if len(hits) == 1:
        command = by_id(hits[0])
        return Route(command, command.reference, f"关键词命中 {command.id}")

    command = by_id(hits[0])
    return Route(
        command,
        command.reference,
        f"关键词命中 {hits[0]}，但 {hits[1]} 也可能适用。",
        ambiguous_with=tuple(hits[1:]),
    )
