// Hosted UI 面板：组件与 hook 全部来自 @neko/plugin-ui。
// 不导入 npm 包，不用 class 组件，不用 dangerouslySetInnerHTML。
import {
  ActionForm,
  Card,
  DataTable,
  EmptyState,
  InlineError,
  Input,
  JsonView,
  KeyValue,
  Page,
  RefreshButton,
  Section,
  Select,
  Stack,
  StatCard,
  Text,
  Textarea,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

function actionById(actions: any[], id: string) {
  return actions.find((item) => item.id === id);
}

export default function VikingPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const error = state.last_error || "";
  const tree: any[] = state.tree || [];
  const stats: any = state.stats || {};

  async function call(actionId: string, args: Record<string, any>) {
    return props.api.call(actionId, args, { userInitiated: true });
  }

  return (
    <Page title={String(state.labels?.title || "Context Database")}>
      <Text>{String(state.labels?.subtitle || "")}</Text>

      <Section title="Tree">
        <Stack>
          <StatCard label="files" value={String(stats.files ?? "-")} />
          <StatCard label="chars" value={String(stats.chars ?? "-")} />
        </Stack>
        {tree.length === 0 ? (
          <EmptyState message="The tree is empty. Write one entry first." />
        ) : (
          <DataTable
            data={tree}
            columns={[
              { key: "path", label: "path" },
              { key: "type", label: "type" },
              { key: "summary", label: "summary" },
            ]}
          />
        )}
      </Section>

      <Section title="Write">
        <ActionForm
          action={actionById(props.actions, "viking_write")}
          submitLabel="Write"
          onSubmit={(values: Record<string, any>) => call("viking_write", values)}
        />
      </Section>

      <Section title="Read">
        <ActionForm
          action={actionById(props.actions, "viking_read")}
          submitLabel="Read"
          onSubmit={(values: Record<string, any>) => call("viking_read", values)}
        />
        <KeyValue label="layers" value="l0 one line / l1 structured / l2 full content" />
      </Section>

      <Section title="Query">
        <ActionForm
          action={actionById(props.actions, "viking_grep")}
          submitLabel="Grep"
          onSubmit={(values: Record<string, any>) => call("viking_grep", values)}
        />
        <ActionForm
          action={actionById(props.actions, "viking_find")}
          submitLabel="Find"
          onSubmit={(values: Record<string, any>) => call("viking_find", values)}
        />
        <ActionForm
          action={actionById(props.actions, "viking_commit")}
          submitLabel="Commit memory"
          onSubmit={(values: Record<string, any>) => call("viking_commit", values)}
        />
      </Section>

      <Section
        title="Maintenance"
        actions={<RefreshButton onClick={() => props.api.refresh()} />}
      >
        <ActionForm
          action={actionById(props.actions, "viking_skills")}
          submitLabel="Skills"
          onSubmit={(values: Record<string, any>) => call("viking_skills", values)}
        />
        {error ? <InlineError error={error} /> : null}
      </Section>
    </Page>
  );
}
