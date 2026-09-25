"""flow_simplify 领域错误。"""

from __future__ import annotations


class SimplifyError(Exception):
    """flow_simplify 领域错误的基类。"""

    code = "SIMPLIFY_ERROR"

class ScopeError(SimplifyError):
    """请求的范围不合法，或指向不存在的子系统。"""

    code = "SCOPE_INVALID"

class AuthorityError(SimplifyError):
    """在没有获得明确授权时请求了写操作。"""

    code = "AUTHORITY_REQUIRED"
