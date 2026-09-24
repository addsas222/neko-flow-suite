# 工作流图谱

把架构、工作流、时序、数据流与生命周期画成可导出的自包含 HTML。

Source and its Git repository live at:

```text
N.E.K.O/plugin/plugins/flow_atlas
```

Publish to the plugin market with this GitHub repository name:

```text
n.e.k.o_plugin_flow_atlas
```

From this plugin repository root:

```bash
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uv run neko-plugin check flow_atlas
uv run neko-plugin check -r flow_atlas
```

Python runtime dependencies are declared in `pyproject.toml` and synced into
`vendor/` for packaging. The generated `vendor/` directory is not committed.
This pack deliberately ships with **no third-party dependencies** — everything
is standard library, so `vendor/` stays empty.

## Market release

Publish the version declared in `plugin.toml`. By default this pushes the Git
tag, waits for the standard GitHub Release, then notifies the plugin market.

```bash
uv run neko-plugin publish flow_atlas
```

To run only one half explicitly:

```bash
uv run neko-plugin publish github flow_atlas
uv run neko-plugin publish market https://github.com/owner/repo/releases/tag/v0.1.0
```

The generated `.github/workflows/release.yml` builds and uploads
`flow_atlas.neko-plugin`. The market independently verifies that Release
before publishing it.

## Entry

```toml
entry = "plugin.plugins.flow_atlas:FlowAtlasPlugin"
```
