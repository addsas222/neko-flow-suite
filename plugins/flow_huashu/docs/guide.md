# Flow Huashu 使用指南

三个入口：`route`、`gate`、`facts`、`roles`。

## route — 一张表定入口

```python
route(task="做个咖啡主题的 PPT")
```

多信号按行序叠加入口链，而不是二选一。命中「任何产出新视觉设计的任务」
这一行时 `gate_required` 必然为 `True`。

## gate — 三方向硬门（上游铁律）

```python
gate(directions="深空暗场版,大白底衬线版,玻璃质感版", chosen=-1)   # 等用户选
gate(directions="…", chosen=1)                                    # 选定后
```

- 少于 3 个方向直接拒绝。
- 未 `chosen` 就调 `enter_production()` 抛 `GateViolation`。
- **指定风格/品牌不豁免**：`style_hint` 只收窄解释空间。

## facts — 事实验证先于假设

```python
facts(text="我记得 Nano Banana Pro 还没发布。", subject="Nano Banana Pro")
```

命中禁止句式（「我记得…」「据我所知…」「目前是 vN 版本」）即列出
`must_verify`，并给出开工前检索清单。这条优先级高于 clarifying questions。

## roles — 工作室角色轮换

```python
roles(medium="animation", roles_done="motion-designer,art-director")
```

媒介决定主导角色：动画 → 动效设计师，幻灯片 → 艺术总监，
App 原型 → 前端工程师。`coverage.missing` 非空即说明角色没做全。

来源：alchaincyf/huashu-design（MIT），见 `../SOURCE.md`。
