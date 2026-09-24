<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_designmd · 来源

**上游项目**：[awesome-design-md](https://github.com/VoltAgent/awesome-design-md)  
**上游仓库**：`VoltAgent/awesome-design-md`  
**上游许可证**：MIT  
**基线引用**：`f6961238d5cddcf8042a74a70fc400ec67181abb`（branch `main`）  
**上游 star 数**：117,682（采集于 2026-09-24）  
**本套件中的形态**：design 组插件，插件 ID `flow_designmd`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

Google Stitch DESIGN.md 语料精选集：把真实品牌设计系统拆成 agent 可读的 markdown token 文件（73 份）。

## 移植了什么

- _shared/entry.py（DesignEntry 模型、分类推断、search/lookup）
- _shared/catalog.py（扫描 design-md/*/DESIGN.md，解析 front matter 的 colors/typography/spacing/radius/motion）
- _shared/emit.py（token 导出为 CSS 自定义属性块与 token 清单）

## 边界与差异

语料版权归各品牌/原分析作者；套件只做索引与导出工具，不重分发 DESIGN.md 正文。

## 合规

上游以 MIT 发布。本插件的移植代码沿用该许可证；套件自身的编排代码以 MIT 发布。上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
