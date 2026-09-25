"""浏览器运行时装配。产物不请求任何外部资源。"""

from .runtime_part1 import RUNTIME_HEAD
from .runtime_part2 import RUNTIME_TAIL


def render_runtime() -> str:
    return (RUNTIME_HEAD + RUNTIME_TAIL).strip()
