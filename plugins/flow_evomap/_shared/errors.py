"""flow_evomap 领域错误。错误消息绝不包含密钥或原始 payload。"""

from __future__ import annotations


class EvoError(Exception):
    """flow_evomap 领域错误的基类。"""

    code = "EVO_ERROR"

class IdentityError(EvoError):
    """身份缺失、格式错误或恢复失败。"""

    code = "IDENTITY_ERROR"

class ProtocolError(EvoError):
    """远端返回了不合规的结构。"""

    code = "PROTOCOL_ERROR"

class NetworkError(EvoError):
    """网络或传输层失败。"""

    code = "NETWORK_ERROR"

class RedactionError(EvoError):
    """内容在脱敏后仍然不安全。"""

    code = "REDACTION_REQUIRED"
