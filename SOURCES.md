# 来源登记表

> 本文件由 tools/build_sources_doc.py 从 sources.json 生成，请勿手改。

套件仓库：https://github.com/addsas222/neko-flow-suite

每个插件都必须有可追溯的上游来源。移植代码遵循上游许可证；套件自身代码以 MIT 发布，并在 NOTICE 中列明上游作者。

| 插件 | 上游 | 许可证 | 状态 | 基线引用 | star | 汇总 |
|---|---|---|---|---|---|---|
| `flow_taste` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | MIT | 已移植 | `c184364c58658b2f131b4ae8bd3d206cabb3deee` | 89,804 | 反 AI 味前端 skill：先读 brief 定 design read，再拧三个旋钮，最后按硬规则拦截 LLM 默认审美。 |
| `flow_impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 | 已移植 | `e0881d2de397d5e9761d7b35ff5017d8f5ebf69b` | 70,683 | 设计语言型 skill：一套命令表把设计/重设计/审计/动效/排版/适配/性能路由到对应 playbook，并强制有界验证轮次。 |
| `flow_huashu` | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | MIT | 已移植 | `0830494ecb1c117e25b313a8114fe55a6bf2b125` | 24,431 | HTML 原生设计 skill：高保真原型/幻灯片/动画，铁律是三方向硬门 + 事实验证先于假设 + 工作室式角色轮换。 |
| `flow_designmd` | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | MIT | 已移植 | `f6961238d5cddcf8042a74a70fc400ec67181abb` | 117,682 | Google Stitch DESIGN.md 语料精选集：把真实品牌设计系统拆成 agent 可读的 markdown token 文件（73 份）。 |
| `flow_atlas` | [tt-a1i/archify](https://github.com/tt-a1i/archify) | MIT | 已移植 | `fetched 2026-09-24 via src/archify_SKILL.md, src/archify_README.md, src/archify_PRODUCT.md` | — | 规格驱动的交互式图表库：作者写 JSON 规格，排版引擎算几何，渲染器出图。 |
| `flow_simplify` | [tt-a1i/simplify-codebase](https://github.com/tt-a1i/simplify-codebase) | MIT | 已移植 | `fetched 2026-09-24 via src/simplify_README.md, src/simplify_SKILL.md, src/simplify_visual.md` | — | 用可度量的复用度指标替代「感觉重复」的代码简化工作流。 |
| `flow_ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT | 已移植 | `fetched 2026-09-24 via src/ponytail_README.md` | — | 以「最短实现」为目标的剃刀式简化约束集。 |
| `flow_viking` | [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | Apache-2.0 | 已移植 | `fetched 2026-09-24 via src/ov_README.md` | — | 面向 Agent 的上下文数据库：文件系统式记忆与检索抽象。 |
| `flow_evomap` | [EvoMap/evolver](https://github.com/EvoMap/evolver) | GPL-3.0 | 不移植 | `fetched 2026-09-26 via EvoMap/evolver README 与仓库元数据` | — | GEP 驱动的 agent 自演化引擎：用 Gene / Capsule / Event 三种可审计工件记录「候选变更 → 采纳 → 回放」的演化轨迹（evomap.ai）。 |
| `flow_eigenflux` | [phronesis-io/eigenflux](https://github.com/phronesis-io/eigenflux) | NOASSERTION（GitHub 未识别的非标准许可证） | 不移植 | `fetched 2026-09-26 via phronesis-io/eigenflux 仓库元数据` | — | EigenFlux —— 面向 AI agent 的开源通信与广播网络的官方实现（Go，eigenflux.ai）。 |

## 逐条详情

### UI / UX 设计类

#### `flow_taste` — taste-skill

- 上游：[Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`c184364c58658b2f131b4ae8bd3d206cabb3deee`（branch `main`）
- 分组：design

反 AI 味前端 skill：先读 brief 定 design read，再拧三个旋钮，最后按硬规则拦截 LLM 默认审美。

移植清单：

  - _shared/brief.py（DesignRead 推断与一句话 design read）
  - _shared/dials.py（DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY 三旋钮及取值域）
  - _shared/lint.py（反默认规则表：Fraunces/Instrument_Serif 禁作默认衬线、Inter 默认降级、h-screen、lucide-react、AI 紫渐变、三等分卡片、Inter+slate-900）
  - _shared/gates.py（pre-flight 硬门：viewport 稳定性、grid over flex-math、依赖核查、单字族单图标族）

边界与差异：上游 12 个子 skill 中只移植 taste-skill 主线的规则层；启发式来自 skills/taste-skill/SKILL.md 与 research/laziness。

#### `flow_impeccable` — impeccable

- 上游：[pbakaus/impeccable](https://github.com/pbakaus/impeccable)
- 许可证：Apache-2.0
- 移植状态：已移植
- 基线引用：`e0881d2de397d5e9761d7b35ff5017d8f5ebf69b`（branch `main`）
- 分组：design

设计语言型 skill：一套命令表把设计/重设计/审计/动效/排版/适配/性能路由到对应 playbook，并强制有界验证轮次。

移植清单：

  - _shared/commands.py（命令表与 route()：shape/audit/critique/animate/bolder/colorize/delight/layout/overdrive/quieter/typeset/adapt/optimize/live/generate + init/document/extract）
  - _shared/passes.py（有界验证策略：build fully → inspect once batched → fix in one batch → at most one confirm round → stop）
  - _shared/craftfloor.py（craft floor 清单与阻断项判定）

边界与差异：未移植其二进制 launcher（scripts/impeccable）；命令路由与轮次策略用纯 Python 复刻。

#### `flow_huashu` — huashu-design

- 上游：[alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`0830494ecb1c117e25b313a8114fe55a6bf2b125`（branch `master`）
- 分组：design

HTML 原生设计 skill：高保真原型/幻灯片/动画，铁律是三方向硬门 + 事实验证先于假设 + 工作室式角色轮换。

移植清单：

  - _shared/routing.py（任务路由表：多信号按行序叠加成入口链）
  - _shared/gate.py（三方向硬门状态机：open/offer/choose，未选定不得进入执行）
  - _shared/facts.py（事实断言前必须检索；禁用句式检测）
  - _shared/roles.py（艺术总监/品牌研究员/视觉设计师/动效设计师/前端工程师/文案 六角色及失效模式）

边界与差异：未复制 assets/ 音频与 jsx 素材；保留其流程铁律。

#### `flow_designmd` — awesome-design-md

- 上游：[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`f6961238d5cddcf8042a74a70fc400ec67181abb`（branch `main`）
- 分组：design

Google Stitch DESIGN.md 语料精选集：把真实品牌设计系统拆成 agent 可读的 markdown token 文件（73 份）。

移植清单：

  - _shared/entry.py（DesignEntry 模型、分类推断、search/lookup）
  - _shared/catalog.py（扫描 design-md/*/DESIGN.md，解析 front matter 的 colors/typography/spacing/radius/motion）
  - _shared/emit.py（token 导出为 CSS 自定义属性块与 token 清单）

边界与差异：语料版权归各品牌/原分析作者；套件只做索引与导出工具，不重分发 DESIGN.md 正文。

### 工作流类

#### `flow_atlas` — archify

- 上游：[tt-a1i/archify](https://github.com/tt-a1i/archify)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`fetched 2026-09-24 via src/archify_SKILL.md, src/archify_README.md, src/archify_PRODUCT.md`（branch `main`）
- 分组：workflow

规格驱动的交互式图表库：作者写 JSON 规格，排版引擎算几何，渲染器出图。

移植清单：

  - _shared/spec.py（Diagram 规格模型，from_dict/to_dict）
  - _shared/nodes.py（Node/Edge/Group/Participant/Message 与引用完整性检查）
  - _shared/geometry.py（Point/Box/PlacedNode/RoutedEdge/PlacedGroup/Layout）
  - _shared/layered_layout.py、sequence_layout.py、cycle_layout.py（三种版式）
  - _shared/routing.py（正交路由）、layout_checks.py（几何体检）
  - _shared/validate.py、validate_checks.py、receipt.py（校验报告回执）
  - _shared/render.py、_shared/mermaid.py（HTML 渲染与 Mermaid 导入）

边界与差异：移植「规格 → 布局 → 渲染」管道，未复制其前端资源。

#### `flow_simplify` — simplify-codebase

- 上游：[tt-a1i/simplify-codebase](https://github.com/tt-a1i/simplify-codebase)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`fetched 2026-09-24 via src/simplify_README.md, src/simplify_SKILL.md, src/simplify_visual.md`（branch `main`）
- 分组：workflow

用可度量的复用度指标替代「感觉重复」的代码简化工作流。

移植清单：

  - spec.md（README 规则转录）
  - 计划中 _shared/cluster.py、gain.py、plan.py

边界与差异：以度量与门禁替代主观判断。

#### `flow_ponytail` — ponytail

- 上游：[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)
- 许可证：MIT
- 移植状态：已移植
- 基线引用：`fetched 2026-09-24 via src/ponytail_README.md`（branch `main`）
- 分组：workflow

以「最短实现」为目标的剃刀式简化约束集。

移植清单：

  - spec.md（规则转录）
  - 计划中 _shared/bloat.py、budget.py

边界与差异：作为简化类插件的纪律层。

#### `flow_viking` — OpenViking

- 上游：[volcengine/OpenViking](https://github.com/volcengine/OpenViking)
- 许可证：Apache-2.0
- 移植状态：已移植
- 基线引用：`fetched 2026-09-24 via src/ov_README.md`（branch `main`）
- 分组：workflow

面向 Agent 的上下文数据库：文件系统式记忆与检索抽象。

移植清单：

  - spec.md
  - 计划中 _shared/index.py、recall.py

边界与差异：取其分层记忆思路，不依赖其服务端。

#### `flow_evomap` — evomap

- 上游：[EvoMap/evolver](https://github.com/EvoMap/evolver)
- 许可证：GPL-3.0
- 移植状态：不移植 —— GPL-3.0 是强 copyleft：衍生作品必须以同一许可证整体分发，与本套件的 MIT 许可证不兼容。
- 基线引用：`fetched 2026-09-26 via EvoMap/evolver README 与仓库元数据`（branch `main`）
- 分组：workflow

GEP 驱动的 agent 自演化引擎：用 Gene / Capsule / Event 三种可审计工件记录「候选变更 → 采纳 → 回放」的演化轨迹（evomap.ai）。

移植清单：

  - （无。只登记来源与设计说明，不含上游代码。）

边界与差异：仓库与许可证已于 2026-09-26 确认。因 GPL-3.0 与套件 MIT 冲突，本插件不含任何上游移植代码，只登记来源与设计说明。若确需引入，须把 flow_evomap 单独以 GPL-3.0 发布，并从本套件的 MIT 分发中拆出。

#### `flow_eigenflux` — eigenflux

- 上游：[phronesis-io/eigenflux](https://github.com/phronesis-io/eigenflux)
- 许可证：NOASSERTION（GitHub 未识别的非标准许可证）
- 移植状态：不移植 —— 上游 license.key = other、spdx = NOASSERTION，GitHub 无法识别为任何标准开源许可证，因此不能假定允许移植或再分发。
- 基线引用：`fetched 2026-09-26 via phronesis-io/eigenflux 仓库元数据`（branch `main`）
- 分组：workflow

EigenFlux —— 面向 AI agent 的开源通信与广播网络的官方实现（Go，eigenflux.ai）。

移植清单：

  - （无。只登记来源与设计说明，不含上游代码。）

边界与差异：在上游给出可识别的许可证文本之前不移植代码。同族的 eigenflux-claude-plugin / openclaw-eigenflux / codex-eigenflux 只是分发形态，许可证同样未识别。

## 上游许可证要点

- MIT（archify、simplify-codebase、ponytail、taste-skill、huashu-design、
  awesome-design-md）：保留版权声明与许可证声明即可分发与修改。
- Apache-2.0（OpenViking、impeccable）：额外要求声明修改、保留 NOTICE、
  并在改动文件里标注。已在各插件 `NOTICE` 中落实。
- GPL-3.0（evomap / EvoMap/evolver）：强 copyleft，衍生作品必须以 GPL-3.0
  整体分发，与本套件的 MIT 冲突。**不移植**；若要引入须拆为独立 GPL-3.0 仓库，
  并从本套件的 MIT 分发中移除。
- NOASSERTION（eigenflux / phronesis-io/eigenflux）：GitHub 未识别为任何标准
  开源许可证，不能假定允许移植或再分发。**不移植**，待上游给出明确许可证文本后
  再评估。
