"""flow_designmd — DESIGN.md 语料索引与导出。

入口类从 _runtime 导入，_shared/ 是纯标准库索引层。
来源：VoltAgent/awesome-design-md（MIT），见 ./SOURCE.md。
"""

from __future__ import annotations

from ._runtime import FlowDesignMdPlugin

__all__ = ["FlowDesignMdPlugin"]
