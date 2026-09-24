# 极简教练

面向外部 Agent 的过度设计审查：YAGNI 阶梯、删除清单与技术债台账。

Source and its Git repository live at:

```text
N.E.K.O/plugin/plugins/flow_ponytail
```

Publish to the plugin market with this GitHub repository name:

```text
n.e.k.o_plugin_flow_ponytail
```

From this plugin repository root:

```bash
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uv run neko-plugin check flow_ponytail
uv run neko-plugin check -r flow_ponytail
```

Python runtime dependencies are declared in `pyproject.toml` and synced into
`vendor/` for packaging. The generated `vendor/` directory is not committed.
This pack deliberately ships with **no third-party dependencies** — everything
is standard library, so `vendor/` stays empty.

## Market release

Publish the version declared in `plugin.toml`. By default this pushes the Git
tag, waits for the standard GitHub Release, then notifies the plugin market.

```bash
uv run neko-plugin publish flow_ponytail
```

To run only one half explicitly:

```bash
uv run neko-plugin publish github flow_ponytail
uv run neko-plugin publish market https://github.com/owner/repo/releases/tag/v0.1.0
```

The generated `.github/workflows/release.yml` builds and uploads
`flow_ponytail.neko-plugin`. The market independently verifies that Release
before publishing it.

## Entry

```toml
entry = "plugin.plugins.flow_ponytail:FlowPonytailPlugin"
```
