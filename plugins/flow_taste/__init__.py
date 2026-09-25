"""flow_taste — 反 AI 味设计门禁。

入口类从 _runtime 导入，_shared/ 是纯标准库规则层。
来源：Leonxlnx/taste-skill（MIT），见 ./SOURCE.md。
"""

from __future__ import annotations

from ._runtime import FlowTastePlugin

__all__ = ["FlowTastePlugin"]
