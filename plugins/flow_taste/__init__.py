"""flow_taste — 反 AI 味设计门禁。

入口类从 _runtime 导入，_shared/ 是纯标准库规则层。
来源：Leonxlnx/taste-skill（MIT），见 ./SOURCE.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _runtime import FlowTastePlugin  # noqa: E402

__all__ = ["FlowTastePlugin"]
