"""有界验证策略。

上游 impeccable 的核心原则之一：不要开放式自检循环。要「完整构建 → 一次性
批量检查 → 一次批量修完 → 最多再确认一轮 → 停」。开放式自检只是花用户的钱
把收尾该做的事做得更差。
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: 一轮检查里必须同时覆盖的目标（网页端桌面 + 移动一起拍）。
WEB_TARGETS: tuple[str, ...] = ("desktop", "mobile")

#: 上限：整个周期只允许这么多轮。
MAX_ROUNDS = 2

@dataclass(frozen=True, slots=True)
class Pass:
    index: int
    name: str
    directive: str

PLAN: tuple[Pass, ...] = (
    Pass(1, "build", "完整构建到可运行状态；不收尾、不半成品。"),
    Pass(2, "inspect", "一次性批量检查：截图 + 缺陷扫描 + 微观编辑一起做。"),
    Pass(3, "fix", "把 inspect 报告的全部问题一次批量修完，不要逐条来回。"),
    Pass(4, "confirm", "最多再跑一轮确认，然后停止打磨。"),
)

@dataclass(slots=True)
class Verification:
    """一个有界验证周期的状态。"""

    targets: tuple[str, ...] = WEB_TARGETS
    rounds_used: int = 0
    findings_fixed: int = 0
    findings_open: list[str] = field(default_factory=list)
    stopped_early: bool = False

    @property
    def rounds_left(self) -> int:
        return max(0, MAX_ROUNDS - self.rounds_used)

    @property
    def must_stop(self) -> bool:
        return self.rounds_used >= MAX_ROUNDS

    def record_round(self, *, fixed: int = 0, open_findings: list[str] | None = None) -> None:
        self.rounds_used += 1
        self.findings_fixed += fixed
        self.findings_open = list(open_findings or [])

    def stop(self) -> None:
        self.stopped_early = True

    def next_pass(self) -> Pass:
        """当前该做哪一步。

        0 轮完成 → build；1 轮完成且有未修项 → fix；1 轮完成且干净 → confirm；
        已到上限 → confirm（然后必须停）。
        """
        if self.rounds_used == 0:
            return PLAN[0]
        if self.must_stop:
            return PLAN[3]
        if not self.findings_open:
            return PLAN[3]
        return PLAN[2]

    def verdict(self) -> str:
        if self.must_stop or self.stopped_early:
            return "stop"
        if not self.findings_open:
            return "pass"
        return "fix"

    def to_dict(self) -> dict[str, object]:
        return {
            "rounds_used": self.rounds_used,
            "rounds_left": self.rounds_left,
            "targets": list(self.targets),
            "next_pass": self.next_pass().name,
            "next_directive": self.next_pass().directive,
            "open_findings": list(self.findings_open),
            "verdict": self.verdict(),
        }

def plan_for(scope: str) -> tuple[Pass, ...]:
    """按工作范围给出轮次计划；scope 只影响第一批检查目标。"""
    if scope == "native":
        return PLAN
    if scope == "component":
        return (PLAN[0], PLAN[1], PLAN[2])
    return PLAN

def batch_targets(scope: str) -> tuple[str, ...]:
    """检查必须一次批量做完的目标集。"""
    if scope == "native":
        return ("phone", "tablet", "desktop")
    if scope == "component":
        return ("default", "dark", "dense")
    return WEB_TARGETS

def violates_bounded_policy(rounds: int, open_findings: int) -> str | None:
    """开放式自检的判定：超过上限还带着未修项继续转圈。"""
    if rounds >= MAX_ROUNDS and open_findings:
        return (
            f"已用 {rounds} 轮仍有 {open_findings} 项未修：停止自检循环，"
            "把剩余项交收尾流程，或明确告知用户范围超纲。"
        )
    return None
