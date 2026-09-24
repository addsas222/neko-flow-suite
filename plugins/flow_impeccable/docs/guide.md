# Flow Impeccable 使用指南

三个入口：`route`、`plan`、`craftfloor`。

## route — 把请求路由到命令

```python
route(request="make my spacing tighter")   # -> layout
route(request="diagnose the performance")  # -> optimize
route(request="teach me the system")       # -> init（别名）
```

命中多个关键词时**不猜**：`ambiguous_with` 带回候选，由调用方只问一次。
完全没命中时走 `shape` 做任务发现。

命令分组：`setup`（init/document/extract）、`new`（shape）、`enhance`
（animate/bolder/colorize/delight/layout/overdrive/quieter/typeset）、`fix`
（audit/critique/clarify/adapt/optimize）、`iterate`（live/generate）。

## plan — 有界验证

```python
plan(scope="web", rounds_used=1)
```

上游的硬规则是：**不要开放式自检循环**。顺序为
`build → inspect → fix → confirm`，最多 2 轮。
`batch_targets` 给出必须一次拍完的目标（web = 桌面 + 移动一起）。
超过上限还带着未修项继续转圈，`policy_violation` 会指出。

## craftfloor — 底线清单

```python
craftfloor(changed_elements="排版,颜色", satisfied="text-scale")
```

返回 `missing` 列；非空即阻断。清单见 `_shared/craftfloor.py` 的 `FLOOR`。

来源：pbakaus/impeccable（Apache-2.0），见 `../SOURCE.md`。
