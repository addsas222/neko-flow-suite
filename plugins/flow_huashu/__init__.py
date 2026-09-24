"""flow_huashu — 三方向硬门与 HTML 原生设计铁律。

入口类从 _runtime 导入，_shared/ 是纯标准库规则层。
来源：alchaincyf/huashu-design（MIT），见 ./SOURCE.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _runtime import FlowHuashuPlugin  # noqa: E402

__all__ = ["FlowHuashuPlugin"]
