<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_impeccable · 来源

**上游项目**：[impeccable](https://github.com/pbakaus/impeccable)  
**上游仓库**：`pbakaus/impeccable`  
**上游许可证**：Apache-2.0  
**基线引用**：`e0881d2de397d5e9761d7b35ff5017d8f5ebf69b`（branch `main`）  
**上游 star 数**：70,683（采集于 2026-09-24）  
**移植状态**：已移植  
**本套件中的形态**：design 组插件，插件 ID `flow_impeccable`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

设计语言型 skill：一套命令表把设计/重设计/审计/动效/排版/适配/性能路由到对应 playbook，并强制有界验证轮次。

## 移植了什么

- _shared/commands.py（命令表与 route()：shape/audit/critique/animate/bolder/colorize/delight/layout/overdrive/quieter/typeset/adapt/optimize/live/generate + init/document/extract）
- _shared/passes.py（有界验证策略：build fully → inspect once batched → fix in one batch → at most one confirm round → stop）
- _shared/craftfloor.py（craft floor 清单与阻断项判定）

## 边界与差异

未移植其二进制 launcher（scripts/impeccable）；命令路由与轮次策略用纯 Python 复刻。

## 合规

上游以 Apache-2.0 发布。本插件的移植代码沿用该许可证；
套件自身的编排代码以 MIT 发布。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
