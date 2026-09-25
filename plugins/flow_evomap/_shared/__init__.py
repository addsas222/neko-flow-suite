"""flow_evomap 共享层：身份恢复、A2A 客户端、脱敏与多后端适配。"""

from .adapters import BACKENDS, AdapterSpec, adapter, describe_all, known_backends
from .client import A2AClient, CallResult, endpoint_url
from .errors import EvoError, IdentityError, NetworkError, ProtocolError, RedactionError
from .identity import Identity, credentials_dir, describe_identity, locate_credentials, recover_identity
from .memory import MemoryEntry, MemoryStore, recall, record
from .redact import redact, redact_mapping, secrets_found

__all__ = [
    "A2AClient",
    "BACKENDS",
    "AdapterSpec",
    "CallResult",
    "EvoError",
    "Identity",
    "IdentityError",
    "MemoryEntry",
    "MemoryStore",
    "NetworkError",
    "ProtocolError",
    "RedactionError",
    "adapter",
    "credentials_dir",
    "describe_all",
    "describe_identity",
    "endpoint_url",
    "known_backends",
    "locate_credentials",
    "recall",
    "record",
    "recover_identity",
    "redact",
    "redact_mapping",
    "secrets_found",
]
