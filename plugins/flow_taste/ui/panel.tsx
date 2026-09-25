/**
 * Flow Taste 面板：design read + 反默认扫描结果。
 *
 * 组件、hook、类型一律来自 @neko/plugin-ui。surface iframe 不解析 npm 包，
 * 因此禁止 `import ... from "react"`——那会让面板加载失败。
 *
 * 只调 action:call 权限内的入口；数据形状见 docs/guide.md。
 */
import {
  Button,
  Card,
  EmptyState,
  InlineError,
  Page,
  Stack,
  Text,
  Textarea,
  useState,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

type Finding = {
  rule_id: string;
  severity: string;
  line: number;
  column: number;
  message: string;
  fix: string;
};

type Report = {
  verdict: string;
  counts: { block?: number; warn?: number; demote?: number };
  findings: Finding[];
};

const SEVERITY_ORDER = ["block", "warn", "demote"] as const;

/** 入口返回 Ok(data) 或裸 data 两种形状都可能，统一取 data。 */
function unwrap(result: any): any {
  if (result && typeof result === "object" && "data" in result && result.data !== undefined) {
    return result.data;
  }
  return result;
}

function errorText(err: any): string {
  if (!err) return "";
  if (typeof err === "string") return err;
  if (err.message) return String(err.message);
  if (err.error) return String(err.error);
  return JSON.stringify(err);
}

export default function FlowTastePanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const [read, setRead] = useState<any>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const runRead = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await props.api.call(
        "read",
        { page_kind: "landing-saas", vibe: "linear-style" },
        { userInitiated: true },
      );
      setRead(unwrap(result));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const runLint = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await props.api.call("lint", { source }, { userInitiated: true });
      setReport(unwrap(result) as Report);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const readLine =
    read && read.read && read.read.read ? String(read.read.read) : "";
  const findings = (report && report.findings) || [];

  return (
    <Page title="Flow Taste" subtitle={String(state.labels?.subtitle || "反 AI 味设计门禁")}>
      <Card title="Design read">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.read_hint || "生成任何代码之前先拿 design read：单行 design read + 三旋钮推荐值。",
            )}
          </Text>
          <Button tone="primary" disabled={busy} onClick={runRead}>
            生成 design read
          </Button>
          {readLine ? <Text>{readLine}</Text> : null}
          {error ? <InlineError error={error} /> : null}
        </Stack>
      </Card>

      <Card title="反默认扫描">
        <Stack gap={12}>
          <Textarea
            value={source}
            placeholder="粘贴要扫描的 HTML / CSS / TSX"
            onChange={(next) => setSource(next)}
          />
          <Button disabled={busy || !source} onClick={runLint}>
            扫描
          </Button>

          {report ? (
            <Stack gap={12}>
              <Text>
                {report.verdict || "unknown"} · block {report.counts?.block ?? 0} / warn{" "}
                {report.counts?.warn ?? 0} / demote {report.counts?.demote ?? 0}
              </Text>
              {findings.length === 0 ? (
                <Text>没有命中任何规则。</Text>
              ) : (
                <Stack gap={8}>
                  {findings
                    .slice()
                    .sort(
                      (a, b) =>
                        SEVERITY_ORDER.indexOf(a.severity as any) -
                        SEVERITY_ORDER.indexOf(b.severity as any),
                    )
                    .map((finding) => (
                      <Card
                        key={`${finding.rule_id}-${finding.line}-${finding.column}`}
                        title={`[${finding.severity}] ${finding.rule_id} ${finding.line}:${finding.column}`}
                      >
                        <Text>{finding.message}</Text>
                        <Text>{`→ ${finding.fix}`}</Text>
                      </Card>
                    ))}
                </Stack>
              )}
            </Stack>
          ) : (
            <EmptyState title="尚未扫描" description="粘贴源码后点「扫描」。" />
          )}
        </Stack>
      </Card>

      {state.labels?.rules_count != null ? (
        <Card title="规则表">
          <Text>{`已加载 ${String(state.labels.rules_count)} 条反默认规则。`}</Text>
        </Card>
      ) : null}
    </Page>
  );
}
