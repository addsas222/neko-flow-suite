<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_evomap · 来源

**上游项目**：[evomap](https://github.com/EvoMap/evolver)  
**上游仓库**：`EvoMap/evolver`  
**上游许可证**：GPL-3.0  
**基线引用**：`fetched 2026-09-26 via EvoMap/evolver README 与仓库元数据`（branch `main`）  
**移植状态**：不移植（原因见下文）  
**本套件中的形态**：workflow 组插件，插件 ID `flow_evomap`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

GEP 驱动的 agent 自演化引擎：用 Gene / Capsule / Event 三种可审计工件记录「候选变更 → 采纳 → 回放」的演化轨迹（evomap.ai）。

## 移植了什么

（无。本插件不含任何上游移植代码，只登记来源与设计说明。）

## 边界与差异

仓库与许可证已于 2026-09-26 确认。因 GPL-3.0 与套件 MIT 冲突，本插件不含任何上游移植代码，只登记来源与设计说明。若确需引入，须把 flow_evomap 单独以 GPL-3.0 发布，并从本套件的 MIT 分发中拆出。

## 不移植的原因

GPL-3.0 是强 copyleft：衍生作品必须以同一许可证整体分发，与本套件的 MIT 许可证不兼容。

## 合规

上游以 GPL-3.0 发布，该许可证不允许在本套件的 MIT 分发内移植再分发。
本插件因此只登记来源与设计说明，不含任何上游代码。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
