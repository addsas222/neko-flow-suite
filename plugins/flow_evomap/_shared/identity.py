"""节点身份：先恢复，再决定是否创建新节点。

目标是一个环境一个持久节点，而不是每次新会话都建一个。密钥绝不进日志、
不进对话历史、不进 git 跟踪的文件。
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

NODE_ID_RE = re.compile(r"^node_[A-Za-z0-9_-]{4,64}$")
SECRET_RE = re.compile(r"^[0-9a-fA-F]{64}$")

ID_FILE = "node_id"
SECRET_FILE = "node_secret"

@dataclass(frozen=True, slots=True)
class Identity:
    """一个已绑定的节点身份。"""

    node_id: str
    node_secret: str

    def masked(self) -> dict[str, str]:
        """给日志和回执用的脱敏视图。"""
        return {
            "node_id": self.node_id,
            "node_secret": self.node_secret[:4] + "..." + self.node_secret[-4:],
        }

    def auth_header(self) -> str:
        return f"Bearer {self.node_secret}"

def credentials_dir(override: str = "") -> Path:
    """凭据目录；默认 ~/.evomap。"""
    if override:
        return Path(override).expanduser()
    return Path.home() / ".evomap"

def locate_credentials(directory: Path) -> Identity | None:
    """从目录读取身份；缺失或格式错误时返回 None。"""
    id_path = Path(directory) / ID_FILE
    secret_path = Path(directory) / SECRET_FILE
    try:
        node_id = id_path.read_text(encoding="utf-8").strip()
        node_secret = secret_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if NODE_ID_RE.match(node_id) and SECRET_RE.match(node_secret):
        return Identity(node_id=node_id, node_secret=node_secret)
    return None

def recover_identity(directory: Path | None = None) -> Identity | None:
    """先尝试恢复已有身份；恢复失败前不创建新节点。"""
    base = credentials_dir(str(directory) if directory else "")
    identity = locate_credentials(base)
    if identity is not None:
        return identity
    for candidate in _fallback_dirs(base):
        identity = locate_credentials(candidate)
        if identity is not None:
            return identity
    return None

def store_identity(identity: Identity, directory: Path | None = None) -> Path:
    """把身份写回规范位置，并收紧权限。"""
    base = credentials_dir(str(directory) if directory else "")
    base.mkdir(parents=True, exist_ok=True)
    _chmod(base, 0o700)
    _write_private(base / ID_FILE, identity.node_id)
    _write_private(base / SECRET_FILE, identity.node_secret)
    return base

def describe_identity(identity: Identity | None) -> dict[str, object]:
    """状态描述：绝不包含完整密钥。"""
    if identity is None:
        return {"bound": False, "node_id": None, "next": "run the recovery flow before registering"}
    return {"bound": True, **identity.masked()}

def _fallback_dirs(base: Path) -> list[Path]:
    home = Path.home()
    return [
        base,
        home / ".config" / "evomap",
        home / "evomap",
        Path(os.environ.get("USERPROFILE", str(home))) / ".evomap",
    ]

def _write_private(path: Path, content: str) -> None:
    path.write_text(content + "\n", encoding="utf-8", newline="\n")
    _chmod(path, 0o600)

def _chmod(path: Path, mode: int) -> None:
    if os.name != "posix":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        return

def _unused() -> None:  # pragma: no cover - keeps the stat import honest
    _ = stat.S_IMODE
