"""事实验证先于假设（核心原则 #0）。

上游铁律：任何涉及具体产品/技术/事件/人物的存在性、发布状态、版本号、规格
参数的断言，第一步必须检索，禁止凭训练语料断言。这条优先级高于「问 clarifying
questions」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: 看到自己要说这些句式时，立即停下去搜。
BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"我记得.{0,20}(还没|已经|是)", "我记得式断言"),
    (r"(应该|大概|可能|似乎)(还没|已经)?(发布|存在|是)", "模糊猜测式断言"),
    (r"据我所知", "据我所知式断言"),
    (r"目前是\s*v?\d+(\.\d+)*\s*版本", "未经验证的版本号断言"),
    (r"X?\s*这个产品可能不存在", "存在性否定断言"),
    (r"规格是", "未验证规格断言"),
)

#: 正确的替代句式。
SAFE_PATTERNS: tuple[str, ...] = (
    "我检索一下 {subject} 最新状态",
    "检索到的权威来源说 {subject} 是 ...",
)

TRIGGERS: tuple[str, ...] = (
    "提到不熟悉或不确定的具体产品名",
    "涉及发布时间线/版本号/规格参数",
    "内心冒出「我记得」「应该还没发布」「大概在」句式",
    "给某个具体产品/公司做设计物料",
)


@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    subject: str
    violation: str | None

    @property
    def needs_verification(self) -> bool:
        return self.violation is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "subject": self.subject,
            "violation": self.violation,
            "needs_verification": self.needs_verification,
        }


def scan(text: str) -> list[Claim]:
    """扫一段文案，挑出未经验证的事实断言。"""
    claims: list[Claim] = []
    for sentence in re.split(r"[。\n!?？!]", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        for pattern, label in BANNED_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                claims.append(
                    Claim(
                        text=sentence,
                        subject=_extract_subject(sentence),
                        violation=label,
                    )
                )
                break
    return claims


def _extract_subject(sentence: str) -> str:
    match = re.search(r"[A-Za-z][A-Za-z0-9 ._-]{1,30}", sentence)
    return match.group(0).strip() if match else sentence[:24]


def verification_checklist(subject: str) -> list[str]:
    """开工前的硬流程（优先级高于 clarifying questions）。"""
    return [
        f"检索「{subject}」+ 最新时间词（latest / launch date / release / specs）",
        "读 1-3 条权威结果，确认：存在性 / 发布状态 / 最新版本号 / 关键规格",
        f"把事实写进项目的 product-facts.md，不靠记忆",
        "搜不到或结果模糊 → 问用户，而不是自行假设",
    ]


def must_verify(text: str) -> bool:
    return bool(scan(text))
