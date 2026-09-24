// Hosted UI 面板：组件与 hook 全部来自 @neko/plugin-ui。
// 不导入 npm 包，不用 class 组件，不用 dangerouslySetInnerHTML。
import {
  ActionForm,
  Card,
  CodeBlock,
  DataTable,
  EmptyState,
  InlineError,
  JsonView,
  Page,
  RefreshButton,
  Section,
  Select,
  StatCard,
  Stack,
  Text,
  Textarea,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

function actionById(actions: any[], id: string) {
  return actions.find((item) => item.id === id);
}

export default function PonytailPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const error = state.last_error || "";
  const levels: any[] = state.levels || [];

  async function call(actionId: string, args: Record<string, any>) {
    return props.api.call(actionId, args, { userInitiated: true });
  }

  return (
    <Page title={String(state.labels?.title || "Lazy Senior Dev")}>
      <Text>{String(state.labels?.subtitle || "")}</Text>

      <Section title="Ladder">
        <DataTable
          data={levels}
          columns={[
            { key: "level", label: "level" },
            { key: "description", label: "when to use" },
          ]}
        />
      </Section>

      <Section title="Review a diff">
        <Textarea
          value={""}
          onChange={() => undefined}
          rows={8}
          placeholder="paste a unified diff"
        />
        <ActionForm
          action={actionById(props.actions, "review_diff")}
          submitLabel="Review"
          onSubmit={(values: Record<string, any>) => call("review_diff", values)}
        />
      </Section>

      <Section title="Audit a repository">
        <ActionForm
          action={actionById(props.actions, "audit_ponytail")}
          submitLabel="Audit"
          onSubmit={(values: Record<string, any>) => call("audit_ponytail", values)}
        />
        <ActionForm
          action={actionById(props.actions, "ponytail_debt")}
          submitLabel="Harvest debt"
          onSubmit={(values: Record<string, any>) => call("ponytail_debt", values)}
        />
      </Section>

      <Section title="Export for an external agent">
        <ActionForm
          action={actionById(props.actions, "ponytail_ruleset")}
          submitLabel="Ruleset"
          onSubmit={(values: Record<string, any>) => call("ponytail_ruleset", values)}
        />
        <ActionForm
          action={actionById(props.actions, "ponytail_ruleset_for_host")}
          submitLabel="Ruleset for host"
          onSubmit={(values: Record<string, any>) => call("ponytail_ruleset_for_host", values)}
        />
      </Section>

      <Section title="Safety" actions={<RefreshButton onClick={() => props.api.refresh()} />}>
        <Text>
          Deleting keeps every safety guard: authorization, input validation, isolation,
          data-loss prevention, stored-format compatibility, concurrency and cleanup
          ownership, accessibility. Turning one off is its own authorised objective, never
          a side effect.
        </Text>
        {error ? <InlineError error={error} /> : <EmptyState message="Nothing deferred yet." />}
      </Section>
    </Page>
  );
}
