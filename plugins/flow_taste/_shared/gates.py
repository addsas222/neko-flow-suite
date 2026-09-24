"""Pre-flight 硬门：交付前的强制自检。

对应上游 SKILL.md 第 3 / 5 节的硬性要求。这里是纯 stdlib 的可判定版本，
供插件入口与本地测试共用。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .dials import Dials, motion_gates


@dataclass(slots=True)
class Gate:
    id: str
    question: str
    severity: str = "block"


GATES: tuple[Gate, ...] = (
    Gate("design-read-declared", "生成任何代码之前是否先输出了单行 design read？"),
    Gate("dials-declared", "三个旋钮是否已按 design read 定值，且没有起别名？"),
    Gate("anti-defaults-cleared", "0.D 的 LLM 默认项是否已被主动绕开？"),
    Gate("one-system", "是否只用一个设计系统，没有混搭 Fluent + Carbon？"),
    Gate("deps-verified", "每个三方依赖是否都核对过 package.json，缺的先给安装命令？"),
    Gate("viewport-stable", "全高区块是否用 min-h-[100dvh] 而非 h-screen？"),
    Gate("grid-over-flex-math", "是否避免了 flexbox 百分比运算，改用 Grid？"),
    Gate("motion-motivated", "每个动画是否能一句话说清它传达什么（层级/叙事/反馈/状态）？"),
    Gate("motion-claims-match", "MOTION_INTENSITY > 4 时页面是否真的在动？"),
    Gate("copy-self-audit", "是否逐句重读过所有可见文案，改掉跑题/病句/AI 味？"),
    Gate("no-fake-precision", "所有数字是否来自真实数据或已标注为 mock？"),
    Gate("theme-locked", "页面是否只有一个主题，没有中途翻面？"),
    Gate("icon-family-single", "图标是否单家族、全局统一 strokeWidth？"),
    Gate("no-handrolled-svg", "是否没有手搓 SVG path？"),
)


@dataclass(slots=True)
class GateResult:
    gate_id: str
    ok: bool
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"gate_id": self.gate_id, "ok": self.ok, "note": self.note}


@dataclass(slots=True)
class GateReport:
    results: list[GateResult] = field(default_factory=list)

    def add(self, gate_id: str, ok: bool, note: str = "") -> None:
        self.results.append(GateResult(gate_id, ok, note))

    @property
    def failed(self) -> list[GateResult]:
        return [result for result in self.results if not result.ok]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "failed": [result.gate_id for result in self.failed],
            "results": [result.to_dict() for result in self.results],
        }


def evaluate(
    *,
    design_read: str,
    dials: Dials,
    declared: dict[str, bool] | None = None,
) -> GateReport:
    """给定已声明的项，跑一遍硬门。

    ``declared`` 的键是 Gate.id；缺省视为未通过。dials 参与 motion 相关门禁判定。
    """
    declared = declared or {}
    report = GateReport()

    for gate in GATES:
        if gate.id == "design-read-declared":
            report.add(gate.id, bool(design_read.strip()), "必须有无歧义的单行 read")
        elif gate.id == "dials-declared":
            report.add(gate.id, bool(declared.get("dials-declared", True)), "三个旋钮都要定值")
        elif gate.id == "motion-claims-match":
            must_move = motion_gates(dials)["page_must_actually_move"]
            ok = (
                declared.get("page_moves", declared.get("motion-claims-match", True))
                if must_move
                else True
            )
            report.add(
                gate.id,
                ok,
                "MOTION_INTENSITY > 4 时页面必须真的动" if must_move else "静态页允许",
            )
        elif gate.id == "motion-motivated":
            report.add(
                gate.id,
                declared.get("motion_reasons", declared.get("motion-motivated", False)),
                "每个动画都要有一句话理由",
            )
        else:
            report.add(gate.id, bool(declared.get(gate.id, False)), gate.question)

    return report
