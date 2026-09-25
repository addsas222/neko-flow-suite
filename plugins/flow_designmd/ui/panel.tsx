/**
 * Flow DesignMD 面板：DESIGN.md 语料索引与导出。
 *
 * 组件、hook、类型一律来自 @neko/plugin-ui。surface iframe 不解析 npm 包，
 * 因此禁止 `import ... from "react"`——那会让面板加载失败。
 *
 * 语料本身不在本仓库内；此面板只做扫描、检索与导出。
 */
import {
  Button,
  Card,
  EmptyState,
  InlineError,
  Input,
  Page,
  Stack,
  Text,
  Textarea,
  useState,
} from "@neko/plugin-ui";
import type { PluginSurfaceProps } from "@neko/plugin-ui";

type Result = {
  slug: string;
  name: string;
  category: string;
  token_count: number;
  description: string;
};

const DEFAULT_ROOT = "design-md";

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

export default function FlowDesignMdPanel(props: PluginSurfaceProps) {
  const state: any = props.state || {};
  const [root, setRoot] = useState(DEFAULT_ROOT);
  const [stats, setStats] = useState<any>(null);
  const [term, setTerm] = useState("");
  const [results, setResults] = useState<Result[] | null>(null);
  const [slug, setSlug] = useState("");
  const [entry, setEntry] = useState<any>(null);
  const [css, setCss] = useState("");
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
    <Page title="Flow DesignMD" subtitle={String(state.labels?.subtitle || "DESIGN.md 语料索引")}>
      <Card title="语料根目录">
        <Stack gap={12}>
          <Text>
            {String(
              state.labels?.root_hint ||
                "指向 design-md/<slug>/DESIGN.md 布局的根目录；语料不在本仓库内。",
            )}
          </Text>
          <Input value={root} onChange={(next) => setRoot(next)} />
          <Button disabled={busy || !root} onClick={() => call("scan", { root }, setStats)}>
            扫描语料
          </Button>
          {stats ? (
            <Stack gap={4}>
              <Text>{`条目 ${String(stats.count ?? 0)} · token ${String(stats.tokens ?? 0)}`}</Text>
              <Text>{JSON.stringify(stats.categories || {})}</Text>
            </Stack>
          ) : null}
        </Stack>
      </Card>

      <Card title="检索">
        <Stack gap={12}>
          <Text>{String(state.labels?.search_hint || "命中 slug 或名字时加权最高。")}</Text>
          <Input
            value={term}
            placeholder="例如 dark cinematic"
            onChange={(next) => setTerm(next)}
          />
          <Button
            disabled={busy || !term}
            onClick={() => call("search", { term, limit: 20, root }, setResults)}
          >
            检索
          </Button>
          {results ? (
            <Stack gap={12}>
              {results.length === 0 ? (
                <EmptyState title="没有命中" description="换一个检索词试试。" />
              ) : (
                results.map((result) => (
                  <Stack key={result.slug} gap={4}>
                    <Text>
                      {`${result.slug} · ${result.token_count} tokens · ${result.category}`}
                    </Text>
                    <Button
                      disabled={busy}
                      onClick={() =>
                        call(
                          "export",
                          { slug: result.slug, fmt: "css", root },
                          (data) => setCss(String(data.css || "")),
                        )
                      }
                    >
                      导出 CSS
                    </Button>
                  </Stack>
                ))
              )}
            </Stack>
          ) : null}
        </Stack>
      </Card>

      <Card title="导出">
        <Stack gap={12}>
          <Input value={slug} placeholder="slug，例如 claude" onChange={(next) => setSlug(next)} />
          <Button
            disabled={busy || !slug}
            onClick={() => call("lookup", { slug, root }, setEntry)}
          >
            查条目
          </Button>
          <Textarea value={css} onChange={(next) => setCss(next)} />
          {entry ? <Text>{`${String(entry.name)} · ${String(entry.token_count)} tokens`}</Text> : null}
        </Stack>
      </Card>

      {error ? <InlineError error={error} /> : null}
    </Page>
  );
}
