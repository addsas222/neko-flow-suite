"""共享异常类型。"""

from __future__ import annotations


class AtlasError(Exception):
    """flow_atlas 领域错误的基类。"""

    code = "ATLAS_ERROR"


class SpecError(AtlasError):
    """规格文档无法解析或不符合类型契约。"""

    code = "SPEC_INVALID"


class LayoutError(AtlasError):
    """布局阶段无法为规格找到可渲染的几何解。"""

    code = "LAYOUT_FAILED"
