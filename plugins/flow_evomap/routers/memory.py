"""记忆入口：record / recall / status，以及多后端适配查询。"""

from __future__ import annotations

from plugin.sdk.plugin import Err, Ok, PluginRouter, plugin_entry, ui

from .._shared.adapters import BACKENDS, adapter, describe_all
from .._shared.client import A2AClient, endpoint_url
from .._shared.errors import EvoError, RedactionError
from .._shared.identity import recover_identity
from .._shared.memory import MemoryStore
from .._shared.redact import redact, secrets_found


class MemoryRouter(PluginRouter):
    """本地优先的记忆层；远端后端只在用户明确要求时使用。"""

    def __init__(self) -> None:
        super().__init__(name="memory")

    def _store(self) -> MemoryStore:
        return self.main_plugin.store

    def _hub(self, hub: str = "") -> str:
        return (hub or self.main_plugin.hub_url).rstrip("/")

    @ui.action(id="evo_record", label="Record")
    @plugin_entry(
        id="evo_record",
        name="记录记忆",
        description="把一条内容记入本地记忆；外发前强制脱敏。",
        input_schema={
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
                "text": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
            },
            "required": ["entry_id", "text"],
        },
        llm_result_fields=["entry_id", "chars", "redacted_fields"],
    )
    async def evo_record(
        self, entry_id: str, text: str, tags: list | None = None, source: str = "", **_
    ):
        try:
            cleaned = redact(text, strict=False)
        except RedactionError as exc:
            return Err(exc)
        entry = self._store().record(
            entry_id,
            cleaned,
            tags=tuple(t for t in (tags or []) if isinstance(t, str)),
            source=source,
        )
        return Ok(
            {
                "entry_id": entry.entry_id,
                "chars": len(entry.text),
                "redacted_fields": cleaned != text,
                "backend": "local",
            }
        )

    @ui.action(id="evo_recall", label="Recall")
    @plugin_entry(
        id="evo_recall",
        name="召回记忆",
        description="按关键词召回；默认只读本地后端。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
                "backend": {"type": "string", "enum": ["local", "evomap"]},
            },
            "required": ["query"],
        },
        llm_result_fields=["count", "entries"],
    )
    async def evo_recall(self, query: str, limit: int = 10, backend: str = "local", **_):
        if backend == "local":
            entries = self._store().recall(query, limit=limit)
            return Ok({"count": len(entries), "entries": entries, "backend": "local"})

        identity = recover_identity()
        if identity is None:
            return Err(EvoError("no bound node; run evo_recover before using the remote backend"))
        client = A2AClient(self._hub())
        result = await client.post(
            "/a2a/memory/recall",
            {"query": redact(query, strict=False), "limit": limit},
            identity,
        )
        if not result.ok:
            return Err(EvoError(f"remote recall failed with status {result.status}"))
        return Ok({"count": 1, "entries": [result.payload], "backend": "evomap"})
