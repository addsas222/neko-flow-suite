<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_viking · 来源

**上游项目**：[OpenViking](https://github.com/volcengine/OpenViking)  
**上游仓库**：`volcengine/OpenViking`  
**上游许可证**：Apache-2.0  
**基线引用**：`fetched 2026-09-24 via src/ov_README.md`（branch `main`）  
**移植状态**：已移植  
**本套件中的形态**：workflow 组插件，插件 ID `flow_viking`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

面向 Agent 的上下文数据库：文件系统式记忆与检索抽象。

## 移植了什么

- _shared/retrieval.py（记忆检索）、_shared/store.py（本地存储）、_shared/fsstore.py（文件系统式存储）
- routers/memory.py、query.py、fs.py（入口路由）
- ui/panel.tsx、i18n/{zh-CN,en}.json、docs/quickstart.md

## 边界与差异

取其分层记忆思路，不依赖其服务端；Apache-2.0 要求的修改声明已在 NOTICE 中落实。

## 合规

上游以 Apache-2.0 发布。本插件的移植代码沿用该许可证；
套件自身的编排代码以 MIT 发布。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
