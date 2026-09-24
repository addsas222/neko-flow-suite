/**
 * Flow Huashu 面板：任务路由 -> 三方向硬门 -> 选定。
 *
 * 硬门状态在进程外由 _shared/gate.py 判定；面板只负责收集候选与选定。
 */

import { useState } from "react";

export default function FlowHuashuPanel({ call }: { call: (id: string, args?: unknown) => Promise<any> }) {
  const [task, setTask] = useState("");
  const [routed, setRouted] = useState<Record<string, unknown> | null>(null);
  const [directions, setDirections] = useState<string[]>(["", "", ""]);
  const [gate, setGate] = useState<Record<string, unknown> | null>(null);

  const runRoute = async () => {
    const result = await call("route", { task });
    setRouted(result.data ?? result);
  };

  const submitDirections = async () => {
    const cleaned = directions.map((value) => value.trim()).filter(Boolean);
    if (cleaned.length < 3) {
      setGate({ blocked: "三方向硬门要求至少 3 个方向。" });
      return;
    }
    const result = await call("gate", { directions: cleaned.join(","), chosen: -1 });
    setGate(result.data ?? result);
  };

  const choose = async (index: number) => {
    const cleaned = directions.map((value) => value.trim()).filter(Boolean);
    const result = await call("gate", { directions: cleaned.join(","), chosen: index });
    setGate(result.data ?? result);
  };

  return (
    <section className="p-4 flex flex-col gap-4 text-sm">
      <h2 className="text-base font-semibold">Flow Huashu</h2>

      <textarea
        className="min-h-20 rounded border border-zinc-800 bg-zinc-950 p-2"
        placeholder="描述任务，例如「做个咖啡主题的 PPT」"
        value={task}
        onChange={(event) => setTask(event.target.value)}
      />
      <button type="button" onClick={runRoute} disabled={!task}>
        扫路由表
      </button>

      {routed ? (
        <div className="flex flex-col gap-1 text-xs">
          {Boolean((routed as { gate_required?: boolean }).gate_required) ? (
            <strong className="text-amber-500">必走三方向硬门</strong>
          ) : null}
          <pre className="rounded border border-zinc-800 bg-zinc-950 p-2">
            {JSON.stringify((routed as { entry_chain?: string[] }).entry_chain ?? [], null, 2)}
          </pre>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <span>三个候选方向</span>
        {directions.map((value, index) => (
          <input
            key={index}
            className="rounded border border-zinc-800 bg-zinc-950 p-2"
            value={value}
            onChange={(event) =>
              setDirections((prev) => prev.map((item, i) => (i === index ? event.target.value : item)))
            }
          />
        ))}
        <button type="button" onClick={submitDirections}>
          提交候选
        </button>
      </div>

      {gate && !(gate as { blocked?: string }).blocked ? (
        <div className="flex gap-2">
          {([0, 1, 2] as const).map((index) => (
            <button key={index} type="button" onClick={() => choose(index)}>
              选 {index + 1}
            </button>
          ))}
        </div>
      ) : null}

      {gate ? (
        <pre className="rounded border border-zinc-800 bg-zinc-950 p-3 text-xs">
          {JSON.stringify(gate, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}
