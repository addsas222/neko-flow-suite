<!-- 本文件由 tools/sync_sources.py 从 sources.json 生成，请勿手改。 -->

# flow_maibot · 来源

**上游项目**：[AnySearch（MaiBot 插件）]((待确认))  
**上游仓库**：`(待确认)`  
**上游许可证**：LGPL-3.0（MaiBot Plugin SDK，未随附源码）  
**基线引用**：`上游仓库与提交基线待确认：本插件只适配 MaiBot 生态的 AnySearch 插件（把多个搜索后端聚合成一个 MCP 网关），未随附任何上游源码`  
**移植状态**：已适配：只重写公开接口，不含任何上游代码  
**本套件中的形态**：workflow 组插件，插件 ID `flow_maibot`  
**套件仓库**：https://github.com/addsas222/neko-flow-suite  

## 它做什么

MaiBot 生态强在工具端（大量第三方数据源以插件形式沉淀），N.E.K.O. 强在模型端与前端。flow_maibot 做「工具端 → 模型端」的搬运：在宿主持久进程里动态导入 MaiBot 插件，把它们的 @Tool 注册成 N.E.K.O. 的原生 LLM 工具。

## 重写/移植了什么

（以下是本套件自己写的等价实现，不含任何上游源码。）
- _shared/sdk_compat.py（MaiBot Plugin SDK 公开接口的等价实现：Tool/Action/Command/API/EventHandler/HookHandler/MessageGateway/LLMProvider/HomeCard 与 MaiBotPlugin 基类；不含上游代码）
- _shared/context.py（MaiBot PluginContext 兼容代理：ctx.<capability>.<method>() -> 网关回调，白名单外一律拒绝）
- _shared/mcp_client.py（纯标准库 MCP streamable-http 客户端，transport 可注入）
- _shared/anysearch.py（参数清洗、结果裁剪、错误归一；密钥绝不进错误文本）
- _shared/schemas.py（上游 tools/list 捕获副本，按 brief/full 产出描述与参数 schema）
- _shared/bridge.py（动态导入、组件收集、@Tool -> NEKO 工具映射、调用分发与错误收敛）
- _shared/settings.py（配置解析与校验、内置插件别名补全）
- _runtime.py（宿主 LLM 工具注册协商、进程内编排、生命周期与 Hosted UI 状态）

## 边界与差异

重写的是公开接口而非上游实现，因此不构成上游源码的衍生作品；LGPL 的 copyleft 义务不随本套件的 MIT 分发转移。桥只按用户配置从用户本地或远端加载上游 MaiBot 插件，上游源码的许可证义务由加载方自行承担。API key 只从宿主配置或 ANYSEARCH_API_KEY 读取，绝不写盘、绝不进日志与问题摘要。适配刻意限制在 AnySearch 一个插件上，其他 MaiBot 插件先登记为非目标，避免每插件造一个加载器。

## 合规

上游以 LGPL-3.0（MaiBot Plugin SDK，未随附源码） 发布。本插件没有移植任何上游源码，只按公开接口重写等价实现，
因此不构成上游源码的衍生作品，上游许可证的 copyleft 义务不随本套件的 MIT 分发转移。
本插件的适配与编排代码以 MIT 发布。
上游的商标、品牌资产与素材不在本仓库内重分发。

见同目录 `NOTICE` 获取完整署名。
