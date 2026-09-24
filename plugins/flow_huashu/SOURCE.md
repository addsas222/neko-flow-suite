<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_huashu · 来源

**上游项目**：[huashu-design](https://github.com/alchaincyf/huashu-design)  
**上游仓库**：`alchaincyf/huashu-design`  
**上游许可证**：MIT  
**基线引用**：`0830494ecb1c117e25b313a8114fe55a6bf2b125`（branch `master`）  
**上游 star 数**：24,431（采集于 2026-09-24）  
**本套件中的形态**：design 组插件，插件 ID `flow_huashu`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

HTML 原生设计 skill：高保真原型/幻灯片/动画，铁律是三方向硬门 + 事实验证先于假设 + 工作室式角色轮换。

## 移植了什么

- _shared/routing.py（任务路由表：多信号按行序叠加成入口链）
- _shared/gate.py（三方向硬门状态机：open/offer/choose，未选定不得进入执行）
- _shared/facts.py（事实断言前必须检索；禁用句式检测）
- _shared/roles.py（艺术总监/品牌研究员/视觉设计师/动效设计师/前端工程师/文案 六角色及失效模式）

## 边界与差异

未复制 assets/ 音频与 jsx 素材；保留其流程铁律。

## 合规

上游以 MIT 发布。本插件的移植代码沿用该许可证；套件自身的编排代码以 MIT 发布。上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
