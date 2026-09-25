# N.E.K.O. flow suite

一批移植到 N.E.K.O. 插件体系里的工作流与设计工具。每个插件都有**可追溯的上游
来源**，规则层是纯 Python 标准库、可以在插件进程之外单独测试。

## 插件

| 插件 | 组 | 上游来源 | 许可证 | 一句话 |
|---|---|---|---|---|
| `flow_atlas` | workflow | [tt-a1i/archify](https://github.com/tt-a1i/archify) | MIT | 规格驱动的图表库：JSON 规格 → 排版 → 自包含 HTML |
| `flow_simplify` | workflow | [tt-a1i/simplify-codebase](https://github.com/tt-a1i/simplify-codebase) | MIT | 用可度量复用度替代「感觉重复」的代码精简 |
| `flow_ponytail` | workflow | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT | 「最短实现」剃刀式简化约束 |
| `flow_viking` | workflow | [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | Apache-2.0 | 面向 Agent 的上下文/记忆分层抽象 |
| `flow_evomap` | workflow | [EvoMap/evolver](https://github.com/EvoMap/evolver) | GPL-3.0（需单独分发） | GEP 驱动的 agent 自演化引擎：Gene / Capsule / Event 三种可审计工件 |
| `flow_eigenflux` | workflow | [phronesis-io/eigenflux](https://github.com/phronesis-io/eigenflux) | NOASSERTION（未移植） | 上游许可证无法识别，只登记来源，入口一律返回不可用 |
| `flow_taste` | design | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | MIT | 反 AI 味设计门禁：design read + 三旋钮 + 硬规则扫描 |
| `flow_impeccable` | design | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 | 设计命令路由 + 有界验证 + craft floor |
| `flow_huashu` | design | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | MIT | 三方向硬门 + 事实验证 + 工作室角色轮换 |
| `flow_designmd` | design | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | MIT | DESIGN.md 语料索引，导出 CSS 自定义属性 |

完整来源登记（含 commit、移植清单、边界说明）见 [SOURCES.md](SOURCES.md)；
每个插件目录下的 `SOURCE.md` 与 `NOTICE` 是它的独立来源标注。

## 目录结构

```text
plugin/
├── sources.json              # 来源单一事实登记表
├── SOURCES.md                # 人类可读的来源总表
├── plugins/
│   ├── flow_atlas/
│   │   ├── plugin.toml       # N.E.K.O. 清单
│   │   ├── __init__.py       # [plugin].entry 指向的插件类
│   │   ├── _shared/          # 纯标准库规则层（可独立测试）
│   │   ├── routers/ ui/ i18n/ docs/ tests/
│   │   ├── SOURCE.md         # 来源标注（生成物）
│   │   └── NOTICE            # 署名（生成物）
│   └── ...                   # 其余插件同构
└── tools/
    ├── sync_sources.py       # sources.json → 各插件 SOURCE.md / NOTICE
    ├── build_categories.py   # 上游 README → flow_designmd 分类映射
    ├── smoke.py              # 逐个导入 _shared 与插件入口类
    └── _stub/                # plugin.sdk 本地桩，供离线冒烟
```

## 开发

```bash
# 冒烟：每个插件的 _shared 层与入口类都能导入
python tools/smoke.py

# 单测（纯标准库，无需 N.E.K.O 宿主）
cd plugins/flow_taste && python -m unittest discover -s tests

# 校验每个插件都有来源标注
python tools/sync_sources.py --check
```

`_shared/` 层只依赖 Python 标准库，因此规则逻辑可以在插件进程外验证；插件入口
才依赖 `plugin.sdk.plugin`。离线跑冒烟检查时 `tools/_stub` 提供最小 SDK 面。

## 来源政策

`plugin/` 下的每个插件都必须有来源。新增上游项目时：

1. 在 `sources.json` 里加一条记录（上游仓库、许可证、commit、移植清单）。
2. 跑 `python tools/sync_sources.py` 生成该插件的 `SOURCE.md` 与 `NOTICE`。
3. 跑 `python tools/sync_sources.py --check` 确认无插件漏标。

移植代码遵循上游许可证；套件自身的编排代码以 MIT 发布。上游的商标、品牌
资产与素材不在本仓库内重分发。
