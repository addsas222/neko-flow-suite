"""flow_viking 共享层：viking:// 路径、虚拟文件系统、分层记忆与检索。"""

from .errors import ConflictError, NotFoundError, PathError, VikingError
from .fsstore import VDir, VFile, VNode, VirtualFS
from .layers import L0, L1, L2, CommitResult, LayerRecord, MemoryEntry, demote, promote
from .retrieval import RetrievalHit, find, grep, search
from .vpath import VPath, is_ancestor, join, normalize, parse, resolve

__all__ = [
    "CommitResult",
    "ConflictError",
    "L0",
    "L1",
    "L2",
    "LayerRecord",
    "MemoryEntry",
    "NotFoundError",
    "PathError",
    "RetrievalHit",
    "VDir",
    "VFile",
    "VNode",
    "VPath",
    "VikingError",
    "VirtualFS",
    "demote",
    "find",
    "grep",
    "is_ancestor",
    "join",
    "normalize",
    "parse",
    "promote",
    "resolve",
    "search",
]
