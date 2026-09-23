import { useState } from "react";
import { api } from "../lib/api";
import { useAsync } from "./Console";

// Portmanteau drill-down: operations are parsed from the live docstring
// ("- op: description" lines), never hardcoded.
function parseOps(docstring: string): { op: string; desc: string }[] {
  return docstring
    .split("\n")
    .map((l) => l.match(/^\s*-\s*(\w+):\s*(.+)$/))
    .filter((m): m is RegExpMatchArray => !!m)
    .map((m) => ({ op: m[1], desc: m[2] }));
}

export default function Tools() {
  const tools = useAsync(() => api.tools().then((r) => r.data.tools));
  const [open, setOpen] = useState<string | null>("lidar_scan");

  return (
    <div data-testid="tools-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Tools — live from the MCP server</h1>
      {tools.loading && <div className="text-sm text-zinc-300">Eliciting tools…</div>}
      {tools.error && (
        <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">
          Failed: {tools.error}
        </div>
      )}
      {(tools.data ?? []).map((t) => (
        <div
          key={t.name}
          data-testid={`tool-item-${t.name}`}
          className="rounded border border-zinc-800 bg-zinc-900 p-3"
        >
          <button
            onClick={() => setOpen((o) => (o === t.name ? null : t.name))}
            className="flex w-full items-center justify-between text-left"
          >
            <span className="font-mono text-cyan-200">{t.name}</span>
            <span className="text-sm text-zinc-400">
              {t.portmanteau ? "portmanteau" : "solo"} · {t.parameters.length} params
            </span>
          </button>
          <div className="mt-1 text-sm text-zinc-300">{t.summary}</div>
          {open === t.name && (
            <div className="mt-2 space-y-2 text-sm">
              {t.portmanteau && (
                <div>
                  <div className="mb-1 text-zinc-400">Operations (parsed from live docstring):</div>
                  <div className="grid gap-1 md:grid-cols-2">
                    {parseOps(t.docstring).map((o) => (
                      <div key={o.op} className="rounded bg-zinc-800 px-2 py-1">
                        <span className="font-mono text-amber-200">{o.op}</span>
                        <span className="text-zinc-300"> — {o.desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="mb-1 text-zinc-400">Parameters:</div>
                {t.parameters.length === 0 && <span className="text-zinc-400">none</span>}
                {t.parameters.map((p) => (
                  <div key={p.name} className="font-mono text-zinc-300">
                    {p.name} <span className="text-zinc-500">= {p.default ?? "required"}</span>
                  </div>
                ))}
              </div>
              <details>
                <summary className="cursor-pointer text-zinc-400">Full docstring</summary>
                <pre className="mt-1 overflow-x-auto rounded bg-zinc-950 p-2 text-sm">
                  {t.docstring}
                </pre>
              </details>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
