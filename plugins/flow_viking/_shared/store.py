"""持久化：把虚拟文件系统写回磁盘，启动时恢复。

viking:// 树保存在 data/viking.json；写盘是原子的，读盘失败时回到空树。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .fsstore import VFile, VirtualFS

STORE_NAME = "viking.json"

def load(path: Path) -> VirtualFS:
    """从磁盘恢复树；文件缺失或损坏时返回空树。"""
    fs = VirtualFS()
    target = Path(path) / STORE_NAME
    if not target.is_file():
        return fs
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fs
    if not isinstance(raw, dict):
        return fs
    for directory in raw.get("dirs", []) or []:
        if isinstance(directory, str):
            fs.try_mkdir(directory)
    entries = raw.get("files")
    if not isinstance(entries, list):
        return fs
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        file_path = entry.get("path")
        content = entry.get("content", "")
        if not isinstance(file_path, str) or not file_path.startswith("viking://"):
            continue
        tags = entry.get("tags", [])
        fs.try_write(
            file_path,
            content if isinstance(content, str) else "",
            tags=tuple(t for t in tags if isinstance(t, str)) if isinstance(tags, list) else (),
        )
    return fs

def save(fs: VirtualFS, path: Path) -> bool:
    """原子写盘。"""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    nodes = fs.descendants("viking://")
    payload = {
        "version": 1,
        "dirs": sorted(node.path for node in nodes if hasattr(node, "names")),
        "files": [_file_payload(file) for file in fs.all_files()],
    }
    target = directory / STORE_NAME
    temporary = directory / (STORE_NAME + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        temporary.replace(target)
    except OSError:
        return False
    return True

def _file_payload(file: VFile) -> dict[str, Any]:
    return {
        "path": file.path,
        "content": file.content,
        "tags": list(file.tags),
        "updated_at": file.updated_at,
    }
