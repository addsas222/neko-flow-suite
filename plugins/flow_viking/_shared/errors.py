"""flow_viking 领域错误。"""

from __future__ import annotations


class VikingError(Exception):
    """flow_viking 领域错误的基类。"""

    code = "VIKING_ERROR"

class PathError(VikingError):
    """viking:// 路径不合法。"""

    code = "PATH_INVALID"

class NotFoundError(VikingError):
    """路径不存在。"""

    code = "NOT_FOUND"

class ConflictError(VikingError):
    """目标已存在，或类型不匹配。"""

    code = "CONFLICT"
