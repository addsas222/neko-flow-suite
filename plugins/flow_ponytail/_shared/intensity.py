"""强度等级：lite / full / ultra / off。

等级只影响"多用力"，不改变安全边界。off 不是关闭安全护栏。
"""

from __future__ import annotations

from dataclasses import dataclass

LEVELS: tuple[str, ...] = ("off", "lite", "full", "ultra")

DESCRIPTIONS: dict[str, str] = {
    "off": "不加载规则集；安全护栏仍然由宿主负责",
    "lite": "只对明显过度设计的位置提示一次",
    "full": "对每一处新增代码应用完整阶梯与删除清单",
    "ultra": "在 full 之上追加契约面与迁移成本检查",
}

@dataclass(frozen=True, slots=True)
class Intensity:
    """一次会话使用的强度。"""

    level: str = "full"
    source: str = "default"

    @property
    def active(self) -> bool:
        return self.level != "off"

    @property
    def checks_contracts(self) -> bool:
        return self.level == "ultra"

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "source": self.source,
            "description": DESCRIPTIONS.get(self.level, ""),
        }

def normalize_level(value: str) -> str:
    """把任意输入收敛到受支持的等级；无法识别时回落到 full。"""
    wanted = (value or "").strip().lower()
    if wanted in LEVELS:
        return wanted
    aliases = {
        "0": "off",
        "1": "lite",
        "2": "full",
        "3": "ultra",
        "minimal": "lite",
        "maximum": "ultra",
    }
    wanted = aliases.get(wanted, "full")
    return wanted if wanted in LEVELS else "full"

def describe(level: str) -> str:
    return DESCRIPTIONS.get(normalize_level(level), DESCRIPTIONS["full"])
