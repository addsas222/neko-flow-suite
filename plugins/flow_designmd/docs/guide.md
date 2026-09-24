# Flow DesignMD 使用指南

把 `DESIGN.md` 语料做成可检索索引。入口：`scan` / `lookup` / `search` /
`export` / `directory`。

## 语料布局

```text
<root>/
├── claude/DESIGN.md
├── airbnb/DESIGN.md
└── …
```

语料取自 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)。
本仓库**不重分发** `DESIGN.md` 正文，只发布解析器、分类映射与导出工具。

## scan / lookup / search

```python
scan(root="/path/to/design-md")                 # 建索引，返回 count / tokens / 分类
lookup(slug="claude", root="…")                 # 取一份完整 token
search(term="dark cinematic", limit=10, root="…")
```

`search` 命中 slug 或名字时加权最高；返回体已用 `llm_result_fields` 收窄，
AI 只看 `count` 与摘要。

## export — 导出 token

```python
export(slug="claude", fmt="css", root="…")   # CSS 自定义属性块
export(slug="claude", fmt="json", root="…")  # 分组 token
export(slug="claude", fmt="markdown", root="…")
```

CSS 产物按 slug 作用域，例如：

```css
:root[data-design="claude"] {
  --claude-colors-primary: #cc785c;
}
```

嵌套 token（`typography.display-xl.fontFamily`）会拍平成
`--claude-typography-display-xl-fontFamily`。

## 分类映射

`data/categories.json` 由 `tools/build_categories.py` 从上游 README 的
Collection 段落生成。上游有更新时重跑并 `--check`。

来源：VoltAgent/awesome-design-md（MIT），见 `../SOURCE.md`。
