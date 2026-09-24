"""YAGNI 阶梯：每一级都是更贵的答案，先问更便宜的能否成立。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RUNGS: tuple[tuple[str, str, str], ...] = (
    ("nothing", "不写代码", "能不能不改代码解决这个问题"),
    ("one-line", "一行", "一个已经存在的调用能不能解决"),
    ("stdlib", "标准库", "标准库有没有现成的"),
    ("existing-dep", "现有依赖", "已经装了的包能不能解决"),
    ("new-dep", "新依赖", "值得为它引入一个新依赖吗"),
    ("new-service", "新服务", "真的需要新的进程或服务吗"),
    ("framework", "新框架", "真的需要新框架吗"),
)


@dataclass(frozen=True, slots=True)
class LadderRung:
    """阶梯上的一级。"""

    key: str
    label: str
    question: str

    @property
    def index(self) -> int:
        return [rung[0] for rung in RUNGS].index(self.key)

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "question": self.question}


def rungs() -> list[LadderRung]:
    return [LadderRung(*rung) for rung in RUNGS]


def rung_for(key: str) -> LadderRung | None:
    """按 key 取一级；大小写与别名都归一化。"""
    wanted = (key or "").strip().lower().replace("_", "-")
    aliases = {
        "0": "nothing",
        "1": "one-line",
        "2": "stdlib",
        "3": "existing-dep",
        "4": "new-dep",
        "5": "new-service",
        "6": "framework",
    }
    wanted = aliases.get(wanted, wanted)
    for rung in rungs():
        if rung.key == wanted:
            return rung
    return None


def next_rung(key: str) -> LadderRung | None:
    """返回上一级更贵的答案；没有更贵的一级时返回 None。"""
    rung = rung_for(key)
    if rung is None:
        return None
    ordered = rungs()
    index = rung.index
    if index + 1 >= len(ordered):
        return None
    return ordered[index + 1]


def justify(rung: LadderRung | None, reason: str) -> dict[str, Any]:
    """把一次选择固化成可复核的记录。"""
    return {
        "rung": rung.to_dict() if rung else None,
        "reason": reason,
        "rule": "如果更便宜的一级能成立，就用它；否则说明为什么不能。",
    }
