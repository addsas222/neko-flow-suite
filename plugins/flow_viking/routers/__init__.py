"""flow_viking 功能路由器。"""

from .fs import FsRouter
from .memory import MemoryRouter
from .query import QueryRouter

__all__ = ["FsRouter", "MemoryRouter", "QueryRouter"]
