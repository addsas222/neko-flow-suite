"""flow_maibot — 把 MaiBot 插件工具暴露成 NEKO 原生 LLM 工具的受控桥。

入口类在 ``_runtime`` 里，``_shared/`` 是可独立测试的纯标准库实现（含 MaiBot
Plugin SDK 公开接口的重写）。上游署名见本目录的 ``SOURCE.md`` 与 ``NOTICE``。
"""

from __future__ import annotations

from ._runtime import FlowMaibotPlugin

__all__ = ["FlowMaibotPlugin"]
