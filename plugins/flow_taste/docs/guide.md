# Flow Taste 使用指南

把 taste-skill 的反默认审美规则做成可执行门禁。三个入口：`read`、`lint`、`preflight`。

## read — 先读房间

```python
read(page_kind="landing-saas", vibe="linear-style", audience="b2b-buyer")
```

返回单行 design read 与三旋钮推荐值。**生成任何代码之前先拿这个结果。**
静默约束（`constraints="public-sector,accessibility-first"`）会优先于审美词翻盘。

## lint — 反默认扫描

```python
lint(source='<div className="h-screen">…</div>')
lint(files="ui/hero.tsx,ui/pricing.tsx")
```

规则分三级：

| 严重度 | 含义 |
|---|---|
| `block` | 命中即不许交付（`h-screen`、`Fraunces`、占位文案） |
| `demote` | 仅在明确覆写条件下可用（`Inter`、`lucide-react`、`Inter+slate-900`） |
| `warn` | 需要给出理由（AI 紫渐变、三等分卡片、伪造精度） |

`report.verdict()` 为 `clean` / `warn` / `blocked`。

## preflight — 交付前硬门

```python
preflight(design_read="…", variance=8, motion=7, density=4, page_moves=True)
```

`MOTION_INTENSITY > 4` 时 `page_moves=False` 会直接阻断——上游要求
「motion claimed, motion shown」。

## 规则表

`rules` 入口列全部规则 id；实现见 `_shared/rules_core.py` 与 `_shared/rules_copy.py`。

来源：Leonxlnx/taste-skill（MIT），见 `../SOURCE.md`。
