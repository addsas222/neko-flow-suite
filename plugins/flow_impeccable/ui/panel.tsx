/**
 * Flow Impeccable 面板：命令路由 + 有界验证轮次 + craft floor。
 *
 * 组件、hook、类型一律来自 @neko/plugin-ui。surface iframe 不解析 npm 包，
 * 因此禁止 `import ... from "react"`——那会让面板加载失败。
 */
import {
  Button,
  Card,
  EmptyState,
  InlineError,
  Input,
  JsonView,
  Page,
  Stack,
  Text,
  Textarea,
  useState,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

type Command = {
  id: string;
  group: string;
  label: string;
  reference: string;
  summary: string;
  takes_target: boolean;
};

const GROUPS = ["setup", "new", "enhance", "fix", "iterate"] as const;
const DEFAULT_ELEMENTS = "排版,颜色,交互,状态";

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

export default function FlowImpeccablePanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const [request, setRequest] = useState("");
  const [route, setRoute] = useState<any>(null);
  const [commands, setCommands] = useState<Command[] | null>(null);
  const [floor, setFloor] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [elements, setElements] = useState(DEFAULT_ELEMENTS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const call = async (actionId: string, args: Record<string, any>, apply: (data: any) => void) => {
    setBusy(true);
    setError("");
    try {
      apply(unwrap(await props.api.call(actionId, args, { userInitiated: true })));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Flow Impeccable" subtitle={String(state.labels?.subtitle || "设计命令路由")}>
      <Card title="路由请求">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.route_hint ||
                "命中多个关键词时不猜：把候选都带回，只问一次。完全没命中走 shape 做任务发现。",
            )}
          </Text>
          <Textarea
            value={request}
            placeholder="描述你的设计请求，例如「make my spacing tighter」"
            onChange={(next) => setRequest(next)}
          />
          <Button
            disabled={busy || !request}
            onClick={() => call("route", { request }, setRoute)}
          >
            路由
          </Button>
          {route ? (
            <Stack gap={8}>
              <Text>
                {`${String(route.command)} · ${String(route.reason)}`}
              </Text>
              <Text>{String(route.reference)}</Text>
            </Stack>
          ) : (
            <EmptyState title="尚未路由" description="填请求后点「路由」。" />
          )}
        </Stack>
      </Card>

      <Card title="命令表">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.commands_hint ||
                "命令分组：setup / new / enhance / fix / iterate。",
            )}
          </Text>
          <Button disabled={busy} onClick={() => call("commands", {}, setCommands)}>
            载入命令表
          </Button>
          {commands ? (
            <Stack gap={12}>
              {GROUPS.map((group) => {
                const items = commands.filter((command) => command.group === group);
                if (items.length === 0) return null;
                return (
                  <Stack key={group} gap={4}>
                    <Text>{group}</Text>
                    {items.map((command) => (
                      <Text key={command.id}>{`${command.id} — ${command.summary}`}</Text>
                    ))}
                  </Stack>
                );
              })}
            </Stack>
          ) : null}
        </Stack>
      </Card>

      <Card title="Craft floor">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.floor_hint ||
                "先选改动涉及的元素类别，再判定是否踩了底线；非空即阻断。",
            )}
          </Text>
          <Input value={elements} onChange={(next) => setElements(next)} />
          <Button
            disabled={busy}
            onClick={() =>
              call("craftfloor", { changed_elements: elements, satisfied: "" }, setFloor)
            }
          >
            跑 craft floor
          </Button>
          {floor ? (
            <Stack gap={8}>
              <Text>{String(floor.directive)}</Text>
              <Text>{`ok: ${String(floor.ok)}`}</Text>
            </Stack>
          ) : null}
        </Stack>
      </Card>

      <Card title="有界验证">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.plan_hint ||
                "不要开放式自检循环：build → inspect → fix → confirm，最多 2 轮。",
            )}
          </Text>
          <Button disabled={busy} onClick={() => call("plan", { scope: "web" }, setPlan)}>
            生成验证计划
          </Button>
          {plan ? <JsonView data={plan} /> : null}
        </Stack>
      </Card>

      {error ? <InlineError error={error} /> : null}
    </Page>
  );
}
