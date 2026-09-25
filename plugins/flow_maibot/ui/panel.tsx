// Hosted UI 面板：组件与 hook 全部来自 @neko/plugin-ui。
// 不导入 npm 包，不用 class 组件，不用 dangerouslySetInnerHTML。
// ActionForm / ActionButton 自己会调 entry；这里不重复套提交逻辑。
import {
  ActionButton,
  ActionForm,
  Alert,
  Card,
  DataTable,
  EmptyState,
  KeyValue,
  Page,
  RefreshButton,
  Section,
  Stack,
  StatCard,
  Text,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

type Label = {
  title: string;
  subtitle: string;
  attach: string;
  refresh: string;
  tools: string;
  problems: string;
};

function text(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return fallback;
}

export default function MaibotPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const labels: Label = {
    title: text(state.labels?.title, "MaiBot 工具桥"),
    subtitle: text(state.labels?.subtitle, ""),
    attach: text(state.labels?.attach, "载入 / 卸载"),
    refresh: text(state.labels?.refresh, "刷新状态"),
    tools: text(state.labels?.tools, "已注册工具"),
    problems: text(state.labels?.problems, "问题清单"),
  };

  const tools: any[] = Array.isArray(state.tools) ? state.tools : [];
  const problems: any[] = Array.isArray(state.problems) ? state.problems : [];
  const plugins: any[] = Array.isArray(state.plugins) ? state.plugins : [];
  const config: any = state.config || {};
  const attached: boolean = state.attached === true;
  const mechanism: string = text(state.mechanism, "unavailable");
  const count: number = Number(state.tool_count || tools.length || 0);

  const attach = props.actions?.find((item) => item.id === "attach");
  const refresh = props.actions?.find((item) => item.id === "refresh");

  const bridgeFacts: Array<{ key?: string; label?: any; value?: any }> = [
    { key: "attached", label: "attached", value: attached ? "yes" : "no" },
    { key: "mechanism", label: "mechanism", value: mechanism },
    { key: "plugins", label: "plugins", value: String(plugins.length) },
    { key: "endpoint", label: "endpoint", value: text(config.endpoint_host, "") },
    { key: "token_source", label: "token_source", value: text(config.token_source, "") },
    { key: "timeout_seconds", label: "timeout_seconds", value: text(config.timeout_seconds, "") },
    { key: "max_results", label: "max_results", value: text(config.max_results, "") },
  ];

  return (
    <Page title={labels.title}>
      <Text>{labels.subtitle}</Text>

      <Section title="Bridge" actions={<RefreshButton onClick={() => props.api.refresh()} />}>
        <Stack gap={8}>
          <StatCard label="tools" value={String(count)} />
          <StatCard label="mechanism" value={mechanism} />
          <StatCard label="plugins" value={String(plugins.length)} />
        </Stack>
        <KeyValue items={bridgeFacts} />
      </Section>

      <Section title={labels.attach}>
        {attach ? <ActionForm action={attach} submitLabel={labels.attach} /> : null}
        {refresh ? (
          <ActionForm action={refresh} submitLabel={labels.refresh} />
        ) : (
          <RefreshButton label={labels.refresh} />
        )}
        {attached ? (
          <ActionButton action={attach} values={{ action: "unload" }}>
            {labels.attach}（卸载）
          </ActionButton>
        ) : null}
      </Section>

      {state.last_error ? <Alert tone="danger" message={String(state.last_error)} /> : null}

      <Section title={labels.tools}>
        {tools.length === 0 ? (
          <EmptyState title="尚未注册工具" description="载入 MaiBot 插件后，工具会出现在这里。" />
        ) : (
          <DataTable
            data={tools}
            columns={[
              { key: "name", label: "name" },
              { key: "plugin_id", label: "plugin" },
              { key: "description", label: "description" },
            ]}
          />
        )}
      </Section>

      <Section title={labels.problems}>
        {problems.length === 0 ? (
          <Card title="ok">没有待处理问题。</Card>
        ) : (
          <Stack gap={8}>
            {problems.map((item: any, index: number) => (
              <Alert key={index} tone="warning" message={String(item)} />
            ))}
          </Stack>
        )}
      </Section>
    </Page>
  );
}
