# MaiBot 工具桥 · 使用指南

`flow_maibot` 把 MaiBot 生态的插件加载进宿主持久进程，并把它们的 `@Tool` 注册成 N.E.K.O 的原生 LLM 工具。首个适配对象是 AnySearch（多个搜索后端聚合）。

## 1. 它在做什么

| 层 | 职责 | 失败时的表现 |
| --- | --- | --- |
| `_shared/settings.py` | 校验宿主配置，读 endpoint / key / tools 选择 | `status().problems` 里一条脱敏摘要 |
| `_shared/bridge.py` | 动态导入 MaiBot 插件，喂改造过的 ctx | 同上，不影响宿主启动 |
| `_shared/schemas.py` | 保存上游 `tools/list` 的捕获副本，按模式产出描述/参数 | 该插件跳过，桥保持可用 |
| `_shared/sdk_compat.py` | MaiBot Plugin SDK 公开接口的重写（`Tool` / `Action` / `ctx`） | —— |
| `_shared/context.py` | `ctx.<capability>.<method>()` -> 网关回调的兼容代理 | strict 下未桥接能力抛错 |
| `_shared/mcp_client.py` | 纯标准库 MCP streamable-http 客户端，可注入 transport | 归一成 `McpError` / `NetworkTransportError` |
| `_shared/anysearch.py` | 参数清洗、结果裁剪、错误归一的网关封装 | 密钥绝不进错误文本 |
| `_runtime.py` | 协商宿主 LLM 工具注册入口，注册 / 注销 | 工具只留在桥内，面板给出原因 |

关键约束：

- **进程内运行**：没有 venv、没有子进程、不改 pip / npm 状态。
- **白名单 ctx**：只有 `CAPABILITY_NAMES`（`tool` / `api` / `chat` / …）里的能力会被
  转发给桥的 `capability_handler`，其余一律抛 `CapabilityNotBridgedError`，不会
  静默返回假数据。非 strict 模式下未实现的已知能力记一条日志后返回 `None`。
- **工具描述/参数的取值优先级**：捕获件（`_shared/captured/anysearch_tools.json`）
  -> `@Tool` 装饰器元数据 -> 函数签名推断。任何一步拿不到就往下退一档，绝不提交
  空定义；单个组件坏了只记 `notes`，不影响同插件其他工具。

## 2. 配置

宿主配置（`[maibot]` 段）或 `data/config.json`，两者语义等价，宿主配置优先。`[maibot]` 段下的键有三种等价写法，运行时归一到同一份配置：平铺（`enabled` / `strict_sdk` / `plugins`）、点号键（`anysearch.endpoint`）、以及分小节（`[maibot.sdk]` / `[maibot.anysearch]`）。

| 键（小节写法） | 平铺写法 | 默认 | 说明 |
| --- | --- | --- | --- |
| `sdk.enabled_bridge` | `enabled` | `true` | 关掉后一个插件都不加载，`problems` 记"桥接层已停用" |
| `sdk.strict_sdk` | `strict_sdk` | `false` | `true` 时 ctx 上调到未实现的已知能力直接抛错，而不是降级返回 `None` |
| `sdk.plugins` | `plugins` | 内置 AnySearch | 要加载的 MaiBot 插件；写 `"AnySearch"` / `"AnySearchPlugin"` 这类 ID / 类名会自动补成内置路径，也可以写 `{"path": ..., "class_name": ...}` |
| `anysearch.endpoint` | `anysearch.endpoint` | `https://api.anysearch.com/mcp` | 搜索网关地址，必须以 `http://` 或 `https://` 开头 |
| `anysearch.api_key` | 同左 | 空 | 直连 token；最高优先 |
| `anysearch.api_key_env` | 同左 | `ANYSEARCH_API_KEY` | `api_key` 为空时读这个环境变量 |
| `anysearch.headers` | 同左 | `{}` | 附加请求头（值会归一成字符串） |
| `anysearch.tools` | 同左 | `["search", "batch_search"]` | 暴露给模型的工具白名单；未捕获的工具名会被拒 |
| `anysearch.description_mode` | 同左 | `brief` | 只接受 `brief`（精炼描述）或 `full`（上游原文） |
| `anysearch.timeout_seconds` | 同左 | `60`（1–600） | 单次 MCP 抓取超时 |
| `anysearch.max_chars` | 同左 | `24000`（500–200000） | 单次工具返回的最大字符数，超出即截断 |
| `anysearch.max_results` | 同左 | `10`（1–10） | 每条查询最多保留几条结果 |

配置示例：

```toml
[maibot]
  enabled = true
  plugins = ["AnySearch"]

  [maibot.anysearch]
    api_key_env = "ANYSEARCH_API_KEY"
    description_mode = "brief"
    tools = ["search", "batch_search"]
```

超出范围的数值会被夹到合法区间，不会因为一个键写错就让整个插件起不来。

安全边界：key 只来自配置或环境变量，**绝不写盘、绝不出现在日志、问题摘要或工具定义里**（面板只看得到 `token_source`：`config` / `env:*` / `none`）。

## 3. 动作与状态

- `attach`（`action = "load"` / `"unload"`）：载入并注册，或卸载并撤销注册。
  其他取值一律按 `load` 处理。
- `refresh`：给了宿主配置就整体重载；没给就只补注册漏掉的工具。
- `maibot` 面板上下文：`attached`、`mechanism`（协商到的注册入口）、`tools`、
  `plugins`、`backend`、`config`（脱敏）、`problems`、`last_error`。

宿主没有暴露 LLM 工具注册入口时不会报错：`problems` 里会说明探测过哪些名字，
工具仍然留在桥内，等宿主补齐入口后 `refresh` 就能补上。

`mechanism` 解释：

| 值 | 含义 |
| --- | --- |
| `HostContext.register_llm_tool` 之类 | 已协商到宿主入口，工具已进模型工具表 |
| `unavailable` | 宿主没有可用入口，工具只留在桥内，可查看 `problems` |

## 4. 运行测试

```bash
python tools/run_tests.py flow_maibot
python tools/smoke.py flow_maibot
```

## 5. 归属

MaiBot / AnySearch 的版权与商标归其上游作者所有，本套件不重分发其源码；本插件只含适配与胶水代码。见同目录 `SOURCE.md` 与 `NOTICE`。
