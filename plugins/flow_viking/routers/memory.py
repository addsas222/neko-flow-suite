"""记忆入口：会话提交、事实抽取与技能库。"""

from __future__ import annotations

from plugin.sdk.plugin import Ok, PluginRouter, plugin_entry, ui

from .._shared.errors import VikingError
from .._shared.layers import L0, L1, L2, CommitResult, demote
from .._shared.vpath import parse


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in (text or "").replace("\n", " ").split(".")]
    return [part for part in parts if len(part) >= 12]

class MemoryRouter(PluginRouter):
    """把一次会话提交进记忆系统，并抽取可复用的事实。"""

    def __init__(self) -> None:
        super().__init__(name="memory")

    def _fs(self):
        return self.main_plugin.fs

    def _persist(self) -> bool:
        return self.main_plugin.persist()

    @ui.action(id="viking_commit", label="Commit memory")
    @plugin_entry(
        id="viking_commit",
        name="提交记忆",
        description="把一段内容提交进记忆系统，并抽取可复用事实。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目标文件路径"},
                "content": {"type": "string"},
                "source": {"type": "string", "description": "来源标记"},
                "extract": {"type": "boolean", "default": True},
            },
            "required": ["path", "content"],
        },
        llm_result_fields=["committed", "path", "summary", "extracted"],
    )
    async def viking_commit(
        self, path: str, content: str, source: str = "", extract: bool = True, **_
    ):
        parsed = parse(path)
        existing = ""
        try:
            existing = self._fs().require_file(path).content
        except VikingError:
            existing = ""

        merged = (existing + "\n\n" + content).strip() if existing else content
        node = self._fs().write(
            parsed.to_url(), merged, tags=(source,) if source else ()
        )
        facts = _sentences(content)[:8] if extract else []
        for index, fact in enumerate(facts):
            self._fs().write(
                parse(parsed.parent.to_url()).child(f"fact-{index}").to_url(),
                fact,
                tags=("extracted",),
            )
        self._persist()
        result = CommitResult(
            committed=True,
            path=parsed.to_url(),
            layer=L2,
            summary=node.summary,
            extracted=facts,
            message="committed and extracted; a narrow commit is not user acceptance",
        )
        return Ok(result.to_dict())

    @ui.action(id="viking_skills", label="Skills")
    @plugin_entry(
        id="viking_skills",
        name="技能库",
        description="把可复用技能写进技能子树，或列出已有技能。",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "put"]},
                "name": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["action"],
        },
    )
    async def viking_skills(self, action: str, name: str = "", body: str = "", **_):
        root = "viking://skills"
        self._fs().mkdir(root)
        if action == "list":
            return Ok(
                {
                    "skills": [
                        {"name": parse(node.path).name, "summary": node.summary}
                        for node in self._fs().descendants(root)
                    ]
                }
            )
        if not name or not body:
            return Ok({"error": "name and body are required to put a skill"})

        target = parse(root).child(name)
        node = self._fs().write(target.to_url(), body, tags=("skill",))
        self._persist()
        return Ok({"stored": target.to_url(), "summary": node.summary})

    @ui.action(id="viking_promote", label="Promote")
    @plugin_entry(
        id="viking_promote",
        name="重组层次",
        description="把一份记录的摘要重新压到目标层。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "layer": {"type": "string", "enum": [L0, L1, L2]},
            },
            "required": ["path", "layer"],
        },
    )
    async def viking_promote(self, path: str, layer: str, **_):
        from .._shared.layers import promote

        node = self._fs().require(path)
        record = node.layer(layer)
        promoted = promote(record, target_layer=layer)
        if layer == L2:
            self._fs().write(path, promoted.content, tags=node.tags)
        else:
            node.tags = (*node.tags, f"summary:{layer}")
            node.refresh()
        self._persist()
        return Ok(
            {
                "path": path,
                "layer": layer,
                "summary": demote(promoted.content or promoted.summary, target_layer=layer),
            }
        )

    @ui.action(id="viking_stats", label="Stats")
    @plugin_entry(
        id="viking_stats",
        name="统计",
        description="返回整棵树的文件数与字符数。",
        input_schema={"type": "object", "properties": {}},
    )
    async def viking_stats(self, **_):
        files = self._fs().all_files()
        return Ok(
            {
                "files": len(files),
                "chars": sum(len(file.content or "") for file in files),
                "dirs": len(
                    [n for n in self._fs().descendants("viking://") if hasattr(n, "names")]
                ),
            }
        )
