<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_atlas · 来源

**上游项目**：[archify](https://github.com/tt-a1i/archify)  
**上游仓库**：`tt-a1i/archify`  
**上游许可证**：MIT  
**基线引用**：`fetched 2026-09-24 via src/archify_SKILL.md, src/archify_README.md, src/archify_PRODUCT.md`（branch `main`）  
**移植状态**：已移植  
**本套件中的形态**：workflow 组插件，插件 ID `flow_atlas`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

规格驱动的交互式图表库：作者写 JSON 规格，排版引擎算几何，渲染器出图。

## 移植了什么

- _shared/spec.py（Diagram 规格模型，from_dict/to_dict）
- _shared/nodes.py（Node/Edge/Group/Participant/Message 与引用完整性检查）
- _shared/geometry.py（Point/Box/PlacedNode/RoutedEdge/PlacedGroup/Layout）
- _shared/layered_layout.py、sequence_layout.py、cycle_layout.py（三种版式）
- _shared/routing.py（正交路由）、layout_checks.py（几何体检）
- _shared/validate.py、validate_checks.py、receipt.py（校验报告回执）
- _shared/render.py、_shared/mermaid.py（HTML 渲染与 Mermaid 导入）

## 边界与差异

移植「规格 → 布局 → 渲染」管道，未复制其前端资源。

## 合规

上游以 MIT 发布。本插件的移植代码沿用该许可证；
套件自身的编排代码以 MIT 发布。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
