<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_evomap · 来源

**上游项目**：[evomap](https://github.com/EvoMap/evolver)  
**上游仓库**：`EvoMap/evolver`  
**上游许可证**：GPL-3.0  
**基线引用**：`fetched 2026-09-26 via EvoMap/evolver README 与仓库元数据`（branch `main`）  
**移植状态**：已移植，但须单独以 GPL-3.0 分发（见下文）  
**本套件中的形态**：workflow 组插件，插件 ID `flow_evomap`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

GEP 驱动的 agent 自演化引擎：用 Gene / Capsule / Event 三种可审计工件记录「候选变更 → 采纳 → 回放」的演化轨迹（evomap.ai）。

## 移植了什么

- _shared/identity.py（节点身份恢复与凭证定位，只读 ~/.evomap）
- _shared/client.py（A2A 客户端，默认只读，远端内容按不可信数据处理）
- _shared/adapters.py（Mem0 / Zep / Letta / Cognee / MemOS 等多后端适配）
- _shared/memory.py（本地 MemoryStore 与 record/recall）
- _shared/redact.py（记录与回放前强制脱敏）
- _shared/errors.py（领域错误类型，消息不含密文或原始 payload）
- routers/{catalog,identity,memory}.py 与插件入口 __init__.py

## 边界与差异

仓库与许可证已于 2026-09-26 确认：GPL-3.0。本插件已移植但其移植代码沿用 GPL-3.0，必须单独以 GPL-3.0 发布，不能并入本套件的 MIT 一体分发。

## 分发限制

GPL-3.0 是强 copyleft：该插件的移植代码必须以 GPL-3.0 单独分发，不得随本套件的 MIT 一体分发。

该插件的移植代码以上游许可证单独发布，不随本套件的 MIT 一体分发。

## 合规

上游以 GPL-3.0 发布。本插件的移植代码沿用 GPL-3.0，
必须以 GPL-3.0 单独分发，不并入本套件的 MIT 分发。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
