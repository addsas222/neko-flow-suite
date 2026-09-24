<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_taste · 来源

**上游项目**：[taste-skill](https://github.com/Leonxlnx/taste-skill)  
**上游仓库**：`Leonxlnx/taste-skill`  
**上游许可证**：MIT  
**基线引用**：`c184364c58658b2f131b4ae8bd3d206cabb3deee`（branch `main`）  
**上游 star 数**：89,804（采集于 2026-09-24）  
**移植状态**：已移植  
**本套件中的形态**：design 组插件，插件 ID `flow_taste`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

反 AI 味前端 skill：先读 brief 定 design read，再拧三个旋钮，最后按硬规则拦截 LLM 默认审美。

## 移植了什么

- _shared/brief.py（DesignRead 推断与一句话 design read）
- _shared/dials.py（DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY 三旋钮及取值域）
- _shared/lint.py（反默认规则表：Fraunces/Instrument_Serif 禁作默认衬线、Inter 默认降级、h-screen、lucide-react、AI 紫渐变、三等分卡片、Inter+slate-900）
- _shared/gates.py（pre-flight 硬门：viewport 稳定性、grid over flex-math、依赖核查、单字族单图标族）

## 边界与差异

上游 12 个子 skill 中只移植 taste-skill 主线的规则层；启发式来自 skills/taste-skill/SKILL.md 与 research/laziness。

## 合规

上游以 MIT 发布。本插件的移植代码沿用该许可证；
套件自身的编排代码以 MIT 发布。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
