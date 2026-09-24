/**
 * Flow Taste 面板：design read + 反默认扫描结果。
 *
 * 只调 action:call 权限内的入口；数据形状见 docs/guide.md。
 */

import { useCallback, useState } from "react";

type Report = {
  verdict: "clean" | "warn" | "blocked";
  counts: { block: number; warn: number; demote: number };
  findings: Array<{
    rule_id: string;
    severity: string;
    line: number;
    column: number;
    message: string;
    fix: string;
  }>;
};

const SEVERITY_ORDER = ["block", "warn", "demote"] as const;

export default function FlowTastePanel({ call }: { call: (id: string, args?: unknown) => Promise<any> }) {
  const [read, setRead] = useState<Record<string, unknown> | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);

  const runRead = useCallback(async () => {
    setBusy(true);
    try {
      const result = await call("read", { page_kind: "landing-saas", vibe: "linear-style" });
      setRead(result.data ?? result);
    } finally {
      setBusy(false);
    }
  }, [call]);

  const runLint = useCallback(async () => {
    setBusy(true);
    try {
      const result = await call("lint", { source });
      setReport((result.data ?? result) as Report);
    } finally {
      setBusy(false);
    }
  }, [call, source]);

  return (
    <section className="p-4 flex flex-col gap-4 text-sm">
      <header className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Flow Taste</h2>
        <button type="button" onClick={runRead} disabled={busy}>
          生成 design read
        </button>
      </header>

      {read ? (
        <pre className="rounded border border-zinc-800 bg-zinc-950 p-3 text-xs leading-relaxed">
          {String((read as { read?: { read?: string } }).read?.read ?? JSON.stringify(read))}
        </pre>
      ) : (
        <p className="text-zinc-500">生成任何代码之前先拿 design read。</p>
      )}

      <textarea
        className="min-h-32 rounded border border-zinc-800 bg-zinc-950 p-2 font-mono text-xs"
        placeholder="粘贴要扫描的 HTML / CSS / TSX"
        value={source}
        onChange={(event) => setSource(event.target.value)}
      />

      <button type="button" onClick={runLint} disabled={busy || !source}>
        扫描
      </button>

      {report ? (
        <div className="flex flex-col gap-2">
          <strong>
            {report.verdict} · block {report.counts.block} / warn {report.counts.warn} / demote{" "}
            {report.counts.demote}
          </strong>
          <ul className="flex flex-col gap-2">
            {report.findings
              .slice()
              .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity as never) - SEVERITY_ORDER.indexOf(b.severity as never))
              .map((finding) => (
                <li key={`${finding.rule_id}-${finding.line}-${finding.column}`} className="rounded border border-zinc-800 p-2">
                  <code className="text-xs">
                    [{finding.severity}] {finding.rule_id} {finding.line}:{finding.column}
                  </code>
                  <p>{finding.message}</p>
                  <p className="text-zinc-500">→ {finding.fix}</p>
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
