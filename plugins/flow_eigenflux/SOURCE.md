<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_eigenflux · 来源

**上游项目**：[eigenflux](https://github.com/phronesis-io/eigenflux)  
**上游仓库**：`phronesis-io/eigenflux`  
**上游许可证**：NOASSERTION（GitHub 未识别的非标准许可证）  
**基线引用**：`fetched 2026-09-26 via phronesis-io/eigenflux 仓库元数据`（branch `main`）  
**移植状态**：不移植（原因见下文）  
**本套件中的形态**：workflow 组插件，插件 ID `flow_eigenflux`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

EigenFlux —— 面向 AI agent 的开源通信与广播网络的官方实现（Go，eigenflux.ai）。

## 移植了什么

（无。本插件不含任何上游移植代码。）

## 边界与差异

在上游给出可识别的许可证文本之前不移植代码。同族的 eigenflux-claude-plugin / openclaw-eigenflux / codex-eigenflux 只是分发形态，许可证同样未识别。本目录仍以合法清单 plugin.toml 注册（否则宿主无法加载），但插件被关成 passive = true（不参与 Agent 分派）与 auto_start = false（不随宿主启动）；即便手动启动，唯一入口也只返回 Err 说明不可用。目录内没有任何上游代码。

## 不移植的原因

上游 license.key = other、spdx = NOASSERTION，GitHub 无法识别为任何标准开源许可证，因此不能假定允许移植或再分发。

## 合规

上游以 NOASSERTION（GitHub 未识别的非标准许可证） 发布，该许可证不允许在本套件的 MIT 分发内移植再分发。
本插件因此只登记来源，并以禁用态注册为一个合法插件，不含任何上游代码。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
