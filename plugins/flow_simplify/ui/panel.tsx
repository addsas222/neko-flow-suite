// Hosted UI 面板：组件与 hook 全部来自 @neko/plugin-ui。
// 不导入 npm 包，不用 class 组件，不用 dangerouslySetInnerHTML。
import {
  ActionForm,
  Card,
  DataTable,
  EmptyState,
  Field,
  InlineError,
  Input,
  JsonView,
  Page,
  RefreshButton,
  Section,
  StatCard,
  Stack,
  Switch,
  Text,
  Textarea,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

function actionById(actions: any[], id: string) {
  return actions.find((item) => item.id === id);
}

export default function SimplifyPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const error = state.last_error || "";
  const last: any = state.last_report || {};

  async function call(actionId: string, args: Record<string, any>) {
    return props.api.call(actionId, args, { userInitiated: true });
  }

  const stats = [
    { label: "files", value: String(last.files ?? "-") },
    { label: "lines", value: String(last.lines ?? "-") },
    { label: "candidates", value: String(last.finding_count ?? "-") },
  ];

  return (
    <Page title={String(state.labels?.title || "Codebase Simplify")}>
      <Text>{String(state.labels?.subtitle || "Prove first, then delete.")}</Text>

      <Section title="Read-only audit">
        <ActionForm
          action={actionById(props.actions, "audit_repo")}
          submitLabel="Audit"
          onSubmit={(values: Record<string, any>) => call("audit_repo", values)}
        />
      </Section>

      <Section title="Plan a cut">
        <Textarea
          value={String(state.draft_record || "")}
          onChange={() => undefined}
          rows={10}
          placeholder='{"subject":"...","location":"path.py:12", ...}'
        />
        <ActionForm
          action={actionById(props.actions, "plan_cut")}
          submitLabel="Plan"
          onSubmit={(values: Record<string, any>) => call("plan_cut", values)}
        />
      </Section>

      <Section title="Apply a cut">
        <Text>Nothing is applied until the proof record is complete and authorised.</Text>
        <ActionForm
          action={actionById(props.actions, "apply_cut")}
          submitLabel="Apply"
          onSubmit={(values: Record<string, any>) => call("apply_cut", values)}
        />
      </Section>

      {error ? <InlineError error={error} /> : null}

      <Section
        title="Coverage"
        actions={<RefreshButton onClick={() => props.api.refresh()} />}
      >
        <Stack>
          {stats.map((item) => (
            <StatCard key={item.label} label={item.label} value={item.value} />
          ))}
        </Stack>
        {last.blind_spots && last.blind_spots.length ? (
          <DataTable
            data={(last.blind_spots as string[]).map((spot, index) => ({
              index: index + 1,
              spot,
            }))}
            columns={[
              { key: "index", label: "#" },
              { key: "spot", label: "blind spot" },
            ]}
          />
        ) : (
          <EmptyState message="Run an audit to see coverage." />
        )}
      </Section>
    </Page>
  );
}
