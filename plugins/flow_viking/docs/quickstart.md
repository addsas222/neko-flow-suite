# 先扫摘要，再读内容

## 三个层次

| 层 | 内容 | 用途 |
| --- | --- | --- |
| `l0` | 一行摘要 | 先扫描，决定要不要看下去 |
| `l1` | 结构化摘要 | 判断相关性与周边上下文 |
| `l2` | 完整内容 | 确实需要细节时才读 |

每个目录都带一份生成的摘要，因此 Agent 可以先扫摘要，再决定读什么，
而不是把所有内容灌进上下文。

## 基本操作

```text
viking_ls     path=viking://
viking_tree   path=viking://memory  depth=2
viking_read   path=viking://memory/user  layer=l1
viking_write  path=viking://memory/user  content="..."  tags=["user"]
viking_mkdir  path=viking://memory/sessions
viking_rm     path=viking://memory/sessions/old
```

## 检索

```text
viking_grep  pattern="deploy"  path=viking://projects
viking_find  query="部署流程"    path=viking://projects
```

检索在向量排序之前先按目录范围收窄，因此 Agent 能搜索某个项目或记忆子树，
保留它的周边上下文，并在知识演进时重组它。`viking_find` 先扫 `l0`/`l1`
摘要层，摘要层没有命中时才退回内容层。

## 提交记忆

```text
viking_commit  path=viking://memory/sessions/2026-09-24  content="..."  extract=true
```

提交会把内容追加到目标文件，并按句子抽取可复用事实到同目录的
`fact-N` 节点。一次提交通过，不等于运行时、部署或用户验收。

## 技能库

```text
viking_skills  action=put   name="summarise-diff"  body="..."
viking_skills  action=list
```

## 持久化与故障

树保存在 `data/viking.json`；写盘是原子的。`viking_reload` 放弃内存中的
改动，从磁盘重新加载。文件缺失或损坏时回到空树，而不是拒绝启动。
