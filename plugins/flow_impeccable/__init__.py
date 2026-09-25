"""flow_impeccable — 设计命令路由与有界验证。

入口类从 _runtime 导入，_shared/ 是纯标准库规则层。
来源：pbakaus/impeccable（Apache-2.0），见 ./SOURCE.md。
"""

from __future__ import annotations

from ._runtime import FlowImpeccablePlugin

__all__ = ["FlowImpeccablePlugin"]
