"""A2A 客户端：默认只读，所有远端内容都按不可信数据处理。

读这份文档不等于授权任何动作；只有当前对话里的直接用户指令才授权客户端
采取行动。网络失败返回稳定的错误，不泄露原始异常文本。
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .errors import NetworkError, ProtocolError
from .redact import redact_mapping

HUB_URL = "https://evomap.ai"
TIMEOUT_SECONDS = 20.0


@dataclass(slots=True)
class CallResult:
    """一次远端调用的回执。"""

    ok: bool
    status: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "status": self.status, "payload": self.payload, "error": self.error}


class A2AClient:
    """对 A2A 端点的受控访问面。"""

    def __init__(self, hub: str = HUB_URL, *, timeout: float = TIMEOUT_SECONDS) -> None:
        self.hub = (hub or HUB_URL).rstrip("/")
        self.timeout = timeout

    async def get(self, path: str, identity: Any | None = None) -> CallResult:
        return await self._request("GET", path, identity=identity)

    async def post(self, path: str, payload: dict[str, Any], identity: Any | None = None) -> CallResult:
        redacted = redact_mapping(payload or {})
        return await self._request("POST", path, payload=redacted, identity=identity)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        identity: Any | None = None,
    ) -> CallResult:
        url = self.hub + ("/" + path.lstrip("/"))
        headers = {"Accept": "application/json", "User-Agent": "neko-flow-pack/0.1"}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if identity is not None:
            headers["Authorization"] = identity.auth_header()

        def blocking() -> CallResult:
            request = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    status = int(getattr(response, "status", 200) or 200)
            except urllib.error.HTTPError as exc:
                return CallResult(ok=False, status=int(exc.code), error=f"upstream returned {exc.code}")
            except (urllib.error.URLError, OSError, TimeoutError):
                return CallResult(ok=False, error="transport failure")
            return CallResult(ok=200 <= status < 300, status=status, payload=_decode(raw))

        return await asyncio.to_thread(blocking)


def _decode(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {"data": decoded}


def endpoint_url(hub: str, path: str) -> str:
    """拼接完整端点地址，用于面板展示与日志。"""
    base = (hub or HUB_URL).rstrip("/")
    return base + "/" + (path or "").lstrip("/")


def _unused() -> None:  # pragma: no cover - keeps urllib.parse honest
    _ = urllib.parse.quote
