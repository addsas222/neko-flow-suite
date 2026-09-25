/**
 * Flow Huashu 面板：任务路由 -> 三方向硬门 -> 选定。
 *
 * 组件、hook、类型一律来自 @neko/plugin-ui。surface iframe 不解析 npm 包，
 * 因此禁止 `import ... from "react"`——那会让面板加载失败。
 *
 * 三方向硬门的判定规则在进程外由 _shared/gate.py 负责；面板只收集输入并展示结果。
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

const MIN_DIRECTIONS = 3;

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

export default function FlowHuashuPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const [task, setTask] = useState("");
  const [routed, setRouted] = useState<any>(null);
  const [directions, setDirections] = useState<string[]>(["", "", ""]);
  const [gate, setGate] = useState<any>(null);
  const [claim, setClaim] = useState("");
  const [facts, setFacts] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const routeTask = async () => {
    setBusy(true);
    setError("");
    try {
      setRouted(unwrap(await props.api.call("route", { task }, { userInitiated: true })));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const submitDirections = async (chosen: number) => {
    const cleaned = directions.map((value) => value.trim()).filter(Boolean);
    if (cleaned.length < MIN_DIRECTIONS) {
      setGate({ blocked: `三方向硬门要求至少 ${MIN_DIRECTIONS} 个方向。` });
      return;
    }
    setBusy(true);
    setError("");
    try {
      setGate(
        unwrap(
          await props.api.call(
            "gate",
            { directions: cleaned.join(","), chosen },
            { userInitiated: true },
          ),
        ),
      );
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const runFacts = async () => {
    setBusy(true);
    setError("");
    try {
      setFacts(unwrap(await props.api.call("facts", { text: claim }, { userInitiated: true })));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const entryChain: string[] = (routed && routed.entry_chain) || [];
  const gateBlocked = Boolean(gate && gate.blocked);

  return (
    <Page title="Flow Huashu" subtitle={String(state.labels?.subtitle || "三方向硬门")}>
      <Card title="任务路由">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.route_hint || "先扫路由表，多信号按行序叠加入口链，而不是二选一。",
            )}
          </Text>
          <Textarea
            value={task}
            placeholder="描述任务，例如「做个咖啡主题的 PPT」"
            onChange={(next) => setTask(next)}
          />
          <Button disabled={busy || !task} onClick={routeTask}>
            扫路由表
          </Button>
          {routed ? (
            <Stack gap={8}>
              {routed.gate_required ? <Text>必走三方向硬门</Text> : null}
              {entryChain.length ? <Text>{entryChain.join(" → ")}</Text> : null}
            </Stack>
          ) : (
            <EmptyState title="尚未路由" description="填任务描述后点「扫路由表」。" />
          )}
        </Stack>
      </Card>

      <Card title="三方向硬门">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.gate_hint || "指定风格/品牌不豁免：必须出三个差异化方向，等用户选定才能进入执行。",
            )}
          </Text>
          <Input
            value={directions[0]}
            placeholder="方向一，例如「深空暗场版」"
            onChange={(next) => setDirections((prev) => [next, prev[1], prev[2]])}
          />
          <Input
            value={directions[1]}
            placeholder="方向二，例如「大白底衬线版」"
            onChange={(next) => setDirections((prev) => [prev[0], next, prev[2]])}
          />
          <Input
            value={directions[2]}
            placeholder="方向三，例如「玻璃质感版」"
            onChange={(next) => setDirections((prev) => [prev[0], prev[1], next])}
          />
          <Button
            disabled={
              busy || directions.map((value) => value.trim()).filter(Boolean).length < MIN_DIRECTIONS
            }
            onClick={() => submitDirections(-1)}
          >
            提交候选
          </Button>
          {gateBlocked ? <Text>{String(gate.blocked)}</Text> : null}
          {gate && !gateBlocked ? (
            <Stack gap={8}>
              <Button disabled={busy} onClick={() => submitDirections(0)}>
                选方向一
              </Button>
              <Button disabled={busy} onClick={() => submitDirections(1)}>
                选方向二
              </Button>
              <Button disabled={busy} onClick={() => submitDirections(2)}>
                选方向三
              </Button>
            </Stack>
          ) : null}
          {gate ? <JsonView data={gate} /> : null}
        </Stack>
      </Card>

      <Card title="事实验证">
        <Stack gap={12}>
          <Text>{String(state.labels?.facts_hint || "涉及具体产品/技术的断言，先检索再写，禁止凭训练语料断言。")}</Text>
          <Textarea
            value={claim}
            placeholder="粘贴待检查的断言，例如「我记得 Nano Banana Pro 还没发布。」"
            onChange={(next) => setClaim(next)}
          />
          <Button disabled={busy || !claim} onClick={runFacts}>
            检查断言
          </Button>
          {facts ? <JsonView data={facts} /> : null}
        </Stack>
      </Card>

      {error ? <InlineError error={error} /> : null}
    </Page>
  );
}
