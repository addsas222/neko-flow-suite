/**
 * Flow DesignMD 面板：语料检索与 token 导出。
 */

import { useState } from "react";

type Result = {
  slug: string;
  name: string;
  category: string;
  token_count: number;
  description: string;
};

export default function FlowDesignMdPanel({ call }: { call: (id: string, args?: unknown) => Promise<any> }) {
  const [root, setRoot] = useState("design-md");
  const [term, setTerm] = useState("");
  const [results, setResults] = useState<Result[] | null>(null);
  const [css, setCss] = useState("");
  const [selected, setSelected] = useState("");

  const runSearch = async () => {
    const result = await call("search", { term, limit: 20, root });
    setResults((result.data ?? result).results);
  };

  const exportCss = async (slug: string) => {
    setSelected(slug);
    const result = await call("export", { slug, fmt: "css", root });
    setCss((result.data ?? result).css ?? "");
  };

  return (
    <section className="p-4 flex flex-col gap-4 text-sm">
      <h2 className="text-base font-semibold">Flow DesignMD</h2>

      <input
        className="rounded border border-zinc-800 bg-zinc-950 p-2"
        placeholder="design-md 根目录"
        value={root}
        onChange={(event) => setRoot(event.target.value)}
      />
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-zinc-800 bg-zinc-950 p-2"
          placeholder="检索词，如 dark cinematic"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
        />
        <button type="button" onClick={runSearch}>
          检索
        </button>
      </div>

      {results ? (
        <ul className="flex flex-col gap-1">
          {results.map((result) => (
            <li key={result.slug} className="flex items-center justify-between gap-2">
              <span>
                <code>{result.slug}</code> · {result.token_count} tokens · {result.category}
              </span>
              <button type="button" onClick={() => exportCss(result.slug)}>
                导出 CSS
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {css ? (
        <pre className="max-h-64 overflow-auto rounded border border-zinc-800 bg-zinc-950 p-3 text-xs">
          {`/* ${selected} */\n${css}`}
        </pre>
      ) : null}
    </section>
  );
}
