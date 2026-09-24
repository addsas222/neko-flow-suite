/**
 * Flow Impeccable 面板：请求路由 + 有界验证轮次 + craft floor。
 */

import { useState } from "react";

type Command = {
  id: string;
  group: string;
  label: string;
  reference: string;
  summary: string;
  takes_target: boolean;
};

const GROUPS = ["setup", "new", "enhance", "fix", "iterate"] as const;

export default function FlowImpeccablePanel({ call }: { call: (id: string, args?: unknown) => Promise<any> }) {
  const [request, setRequest] = useState("");
  const [route, setRoute] = useState<Record<string, unknown> | null>(null);
  const [commands, setCommands] = useState<Command[] | null>(null);
  const [floor, setFloor] = useState<Record<string, unknown> | null>(null);

  const runRoute = async () => {
    const result = await call("route", { request });
    setRoute(result.data ?? result);
  };

  return (
    <section className="p-4 flex flex-col gap-4 text-sm">
      <h2 className="text-base font-semibold">Flow Impeccable</h2>

      <input
        className="rounded border border-zinc-800 bg-zinc-950 p-2"
        placeholder="描述你的设计请求"
        value={request}
        onChange={(event) => setRequest(event.target.value)}
      />
      <button type="button" onClick={runRoute} disabled={!request}>
        路由
      </button>

      {route ? (
        <pre className="rounded border border-zinc-800 bg-zinc-950 p-3 text-xs">
          {JSON.stringify(route, null, 2)}
        </pre>
      ) : null}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={async () => {
            const result = await call("commands");
            setCommands((result.data ?? result).commands);
          }}
        >
          命令表
        </button>
        <button
          type="button"
          onClick={async () => {
            const result = await call("craftfloor", {
              changed_elements: "排版,颜色,交互,状态",
              satisfied: "",
            });
            setFloor(result.data ?? result);
          }}
        >
          craft floor
        </button>
      </div>

      {commands ? (
        <div className="flex flex-col gap-2">
          {GROUPS.map((group) => (
            <div key={group}>
              <strong>{group}</strong>
              <ul>
                {commands
                  .filter((command) => command.group === group)
                  .map((command) => (
                    <li key={command.id}>
                      <code>{command.id}</code> — {command.summary}
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}

      {floor ? (
        <pre className="rounded border border-amber-700/40 p-3 text-xs">
          {String((floor as { directive?: string }).directive)}
        </pre>
      ) : null}
    </section>
  );
}
