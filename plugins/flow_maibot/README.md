# MaiBot 工具桥

把 MaiBot 生态插件的 `@Tool` 注册成 N.E.K.O 的原生 LLM 工具。首个适配对象是
AnySearch（多个搜索后端聚合的 MCP 网关），桥上第一个 MaiBot 插件就是
`_shared/maibot_plugins/anysearch_plugin.py` —— 它只用 MaiBot Plugin SDK 的公开
接口书写，真 MaiBot 环境与 NEKO 桥接态共用同一份代码。

Source and its Git repository live at:

```text
N.E.K.O/plugin/plugins/flow_maibot
```

Publish to the plugin market with this GitHub repository name:

```text
n.e.k.o_plugin_flow_maibot
```

From this plugin repository root:

```bash
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uv run neko-plugin check flow_maibot
uv run neko-plugin check -r flow_maibot
```

Python runtime dependencies are declared in `pyproject.toml` and synced into
`vendor/` for packaging. The generated `vendor/` directory is not committed.
This pack deliberately ships with **no third-party dependencies** — everything
is standard library, so `vendor/` stays empty. 唯一的运行时输入是宿主配置、
`ANYSEARCH_API_KEY` 环境变量，以及 `_shared/captured/anysearch_tools.json` 这份
从上游 `tools/list` 原样落盘的捕获凭据。

**不引入 MaiBot SDK 代码。** MaiBot Plugin SDK 是 LGPL-3.0，本插件只按 NOTICE
署名，`_shared/sdk_compat.py` 是按公开接口重写的等价实现，形状一致但不含上游源码。

## Market release

Publish the version declared in `plugin.toml`. By default this pushes the Git
tag, waits for the standard GitHub Release, then notifies the plugin market.

```bash
uv run neko-plugin publish flow_maibot
```

To run only one half explicitly:

```bash
uv run neko-plugin publish github flow_maibot
uv run neko-plugin publish market https://github.com/owner/repo/releases/tag/v0.1.0
```

The generated `.github/workflows/release.yml` builds and uploads
`flow_maibot.neko-plugin`. The market independently verifies that Release
before publishing it.

## Entry

```toml
entry = "plugin.plugins.flow_maibot:FlowMaibotPlugin"
```

## 分层

| 层 | 职责 |
| --- | --- |
| `_shared/settings.py` | 配置解析与校验（含 `[maibot]` 三种等价写法与内置插件别名） |
| `_shared/sdk_compat.py` | MaiBot Plugin SDK 公开接口的重写（`Tool`/`Action`/`ctx`） |
| `_shared/context.py` | `ctx.<capability>.<method>()` -> 网关回调的兼容代理 |
| `_shared/mcp_client.py` | 纯标准库 MCP streamable-http 客户端（transport 可注入） |
| `_shared/anysearch.py` | 参数清洗、结果裁剪、错误归一 |
| `_shared/schemas.py` | 上游 `tools/list` 捕获副本与描述/参数产出 |
| `_shared/bridge.py` | MaiBot 插件加载、`@Tool` 映射、调用分发 |
| `_runtime.py` | 进程内编排：宿主 LLM 工具注册协商 + Hosted UI 状态 |

详细使用说明见 `docs/guide.md`；测试见 `tests/`。
