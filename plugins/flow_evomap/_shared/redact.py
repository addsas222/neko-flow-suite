"""脱敏：把内容收敛到可以安全外发的程度。

默认拒绝而不是静默通过：脱敏后仍像密钥的内容一律按失败处理。
"""

from __future__ import annotations

import re
from typing import Any

from .errors import RedactionError

REDACTED = "[REDACTED]"

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*")),
    ("long_hex", re.compile(r"\b[0-9a-fA-F]{32,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("cn_phone", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("cn_id", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
    ("url_credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("absolute_path", re.compile(r"\b[A-Za-z]:\\[^\s\"']+")),
)

STILL_UNSAFE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})\b"
)

def secrets_found(text: str) -> list[str]:
    """列出命中的秘密类别，不返回内容本身。"""
    return [name for name, pattern in PATTERNS if pattern.search(text or "")]

def redact(text: str, *, strict: bool = True) -> str:
    """脱敏一段文本。strict 下仍像密钥时抛 RedactionError。"""
    if not isinstance(text, str):
        raise RedactionError("redaction needs a string")

    cleaned = text
    for _, pattern in PATTERNS:
        cleaned = pattern.sub(REDACTED, cleaned)

    if strict and STILL_UNSAFE.search(cleaned):
        raise RedactionError("content still looks like a secret after redaction")
    return cleaned

def redact_mapping(payload: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """递归脱敏一个结构，键名本身保持不变。"""
    result: dict[str, Any] = {}
    for key, value in (payload or {}).items():
        result[key] = redact_value(value, strict=strict)
    return result

def redact_value(value: Any, *, strict: bool = True) -> Any:
    if isinstance(value, str):
        return redact(value, strict=strict)
    if isinstance(value, dict):
        return redact_mapping(value, strict=strict)
    if isinstance(value, list):
        return [redact_value(item, strict=strict) for item in value]
    return value
