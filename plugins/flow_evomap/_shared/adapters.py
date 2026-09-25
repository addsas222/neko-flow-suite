"""多后端记忆适配：把常见记忆方案接到同一个接口上。

这些后端全部需要使用者自行提供凭据，插件不会自动外发任何内容。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BACKENDS: dict[str, dict[str, str]] = {
    "local": {
        "label": "本地 JSON",
        "endpoint": "",
        "notes": "默认后端，零外部依赖；数据只落在插件自己的 data 目录。",
        "requires_secret": "false",
    },
    "evomap": {
        "label": "EvoMap A2A",
        "endpoint": "https://evomap.ai",
        "notes": "/a2a/memory/{record,recall,status}；需要用户绑定节点。",
        "requires_secret": "true",
    },
    "openviking": {
        "label": "OpenViking",
        "endpoint": "",
        "notes": "由 flow_viking 提供；检索在向量排序前先按目录范围收窄。",
        "requires_secret": "false",
    },
    "mem0": {
        "label": "Mem0",
        "endpoint": "https://api.mem0.ai",
        "notes": "托管记忆层；自行提供 API key。",
        "requires_secret": "true",
    },
    "zep": {
        "label": "Zep / Graphiti",
        "endpoint": "",
        "notes": "时序知识图谱记忆；自托管。",
        "requires_secret": "true",
    },
    "letta": {
        "label": "Letta",
        "endpoint": "",
        "notes": "有状态 Agent 平台，记忆可自改进。",
        "requires_secret": "true",
    },
    "cognee": {
        "label": "Cognee",
        "endpoint": "",
        "notes": "自托管知识图谱引擎。",
        "requires_secret": "true",
    },
    "memos": {
        "label": "MemOS",
        "endpoint": "",
        "notes": "自进化记忆操作系统，混合检索与跨任务技能复用。",
        "requires_secret": "true",
    },
}

@dataclass(frozen=True, slots=True)
class AdapterSpec:
    """一个后端的接入说明。"""

    name: str
    label: str
    endpoint: str
    notes: str
    requires_secret: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "endpoint": self.endpoint,
            "notes": self.notes,
            "requires_secret": self.requires_secret,
        }

def known_backends() -> list[str]:
    return sorted(BACKENDS)

def adapter(name: str) -> AdapterSpec | None:
    spec = BACKENDS.get((name or "").strip().lower())
    if spec is None:
        return None
    return AdapterSpec(
        name=name.strip().lower(),
        label=spec["label"],
        endpoint=spec["endpoint"],
        notes=spec["notes"],
        requires_secret=spec["requires_secret"].lower() == "true",
    )

def describe_all() -> list[dict[str, Any]]:
    return [spec.to_dict() for spec in (adapter(name) for name in known_backends()) if spec]
