// Hosted UI 面板：组件与 hook 全部来自 @neko/plugin-ui。
// 不导入 npm 包，不用 class 组件，不用 dangerouslySetInnerHTML。
import {
  Card,
  DataTable,
  EmptyState,
  Field,
  KeyValue,
  Page,
  RefreshButton,
  Section,
  Select,
  StatCard,
  Stack,
  Text,
  Textarea,
  ActionButton,
  ActionForm,
  InlineError,
  JsonView,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

const ACTIONS = ["render_mermaid", "convert_mermaid", "deliver_diagram", "example_spec"];

function actionById(actions: any[], id: string) {
  return actions.find((item) => item.id === id);
}

export default function AtlasPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const saved: any[] = state.saved_specs || [];
  const error = state.last_error || "";

  async function run(actionId: string, args: Record<string, any>) {
    try {
      return await props.api.call(actionId, args, { userInitiated: true });
    } catch (failure: any) {
      throw failure;
    }
  }

  return (
    <Page title={String(state.labels?.title || "Workflow Atlas")}>
      <Text>{String(state.labels?.subtitle || "")}</Text>

      <Section title="Mermaid">
        <ActionForm
          action={actionById(props.actions, "render_mermaid")}
          submitLabel={String(state.labels?.render || "Render")}
          onSubmit={(values: Record<string, any>) => run("render_mermaid", values)}
        />
        <ActionForm
          action={actionById(props.actions, "convert_mermaid")}
          submitLabel={String(state.labels?.mermaid || "Convert")}
          onSubmit={(values: Record<string, any>) => run("convert_mermaid", values)}
        />
      </Section>

      <Section title="Artifact">
        <ActionForm
          action={actionById(props.actions, "deliver_diagram")}
          submitLabel={String(state.labels?.deliver || "Deliver")}
          onSubmit={(values: Record<string, any>) => run("deliver_diagram", values)}
        />
      </Section>

      {error ? <InlineError error={error} /> : null}

      <Section
        title="Saved specs"
        actions={<RefreshButton onClick={() => props.api.refresh()} />}
      >
        {saved.length === 0 ? (
          <EmptyState message="No saved specs yet." />
        ) : (
          <DataTable
            data={saved}
            columns={[
              { key: "name", label: "name" },
              { key: "title", label: "title" },
              { key: "type", label: "type" },
              { key: "nodes", label: "nodes" },
              { key: "edges", label: "edges" },
            ]}
          />
        )}
      </Section>
    </Page>
  );
}
