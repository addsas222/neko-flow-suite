"""产物与规格文件的读写：规格快照、HTML 产物、交付回执。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .errors import SpecError

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def safe_filename(name: str) -> str:
    """把任意标题收敛成安全的文件名主干。"""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name or "diagram").strip("-.")
    return cleaned[:64] or "diagram"


def write_atomic(path: Path, payload: bytes) -> None:
    """原子写入：先写同目录临时文件，再替换目标。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def snapshot_spec(directory: Path, name: str, spec: dict[str, Any]) -> Path:
    """把规格冻结成同目录快照，交付前校验的就是这份字节。"""
    path = directory / f"{safe_filename(name)}.spec.json"
    payload = json.dumps(spec, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    write_atomic(path, payload)
    return path


def write_artifact(directory: Path, name: str, html: str) -> Path:
    path = directory / f"{safe_filename(name)}.html"
    write_atomic(path, html.encode("utf-8"))
    return path


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_spec(path: Path) -> dict[str, Any]:
    """从磁盘读回规格，返回原始 dict（由调用方交给 from_dict）。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path.name} is not valid JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise SpecError(f"{path.name} must contain a JSON object")
    return raw


def require_safe(name: str) -> str:
    if not _SAFE_NAME.match(name or ""):
        raise SpecError(f"unsafe artifact name: {name!r}")
    return name


def list_specs(directory: Path) -> list[dict[str, Any]]:
    """列出已保存的规格及其最近一次校验状态。"""
    found: list[dict[str, Any]] = []
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.spec.json")):
        try:
            spec = load_spec(path)
        except SpecError:
            continue
        found.append(
            {
                "name": path.name[: -len(".spec.json")],
                "title": str(spec.get("title", path.stem)),
                "type": str(spec.get("type", "architecture")),
                "nodes": len(spec.get("nodes", []) or []),
                "edges": len(spec.get("edges", []) or []),
                "path": str(path),
            }
        )
    return found
