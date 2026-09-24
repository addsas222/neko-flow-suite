"""flow_designmd — DESIGN.md 语料索引与导出。

入口类从 _runtime 导入，_shared/ 是纯标准库索引层。
来源：VoltAgent/awesome-design-md（MIT），见 ./SOURCE.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _runtime import FlowDesignMdPlugin  # noqa: E402

__all__ = ["FlowDesignMdPlugin"]
