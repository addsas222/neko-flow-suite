"""flow_atlas 共享层：规格、几何、布局、校验、渲染与 Mermaid 导入。

这一层只依赖 Python 标准库，可以在插件进程之外独立测试。
"""

from .errors import AtlasError, LayoutError, SpecError
from .geometry import Box, Layout, PlacedGroup, PlacedNode, Point, RoutedEdge
from .layout import layout
from .mermaid import parse_mermaid
from .nodes import DIAGRAM_TYPES, Edge, Group, Message, Node, Participant
from .receipt import Issue, Receipt
from .render import render_html
from .spec import Diagram, from_dict
from .validate import validate

__all__ = [
    "AtlasError",
    "Box",
    "DIAGRAM_TYPES",
    "Diagram",
    "Edge",
    "Group",
    "Issue",
    "Layout",
    "LayoutError",
    "Message",
    "Node",
    "Participant",
    "PlacedGroup",
    "PlacedNode",
    "Point",
    "Receipt",
    "RoutedEdge",
    "SpecError",
    "from_dict",
    "layout",
    "parse_mermaid",
    "render_html",
    "validate",
]
