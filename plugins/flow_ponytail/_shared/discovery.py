"""ScopeError：范围不合法或目标不可读。"""

from __future__ import annotations


class ScopeError(Exception):
    """范围不合法，或指向一个不可读的路径。"""

    code = "SCOPE_INVALID"
